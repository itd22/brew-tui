"""Runs install_brew / copy_tui / brew_tui_install / brew_tui_list against a real
docker instance (see tests/conftest.py). Each test runs its command as `tester`
inside the container and checks the real, on-disk effect:

  - install_brew        -> a real `brew` executable now exists and reports a version
  - copy_tui             -> ~tester/BrewE2E/src/brew_tui was actually replaced
  - brew_tui_install     -> the formula lands in the real Cellar AND in brew-tui's DB
  - brew_tui_list        -> `brew-tui list` reports the formula that was just installed

Tests run in file order (plain pytest, no ordering plugin needed) against the same
session-scoped container, so state built up by earlier tests is visible to later ones.

    pytest --run-docker tests/test_docker_workflow.py
    pytest --run-docker --formula=jq tests/test_docker_workflow.py
"""
import shlex
import sqlite3
import subprocess

import pytest

from conftest import exec_in

pytestmark = pytest.mark.docker


def _copy_db_out(container: str, dest) -> None:
    result = subprocess.run(
        ["docker", "cp", f"{container}:/home/tester/BrewTuiData/brew.db", str(dest)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"could not copy DB out of container:\n{result.stderr}"


def test_install_brew(container):
    """`install_brew`: runs ~tester/install-homebrew.sh inside the instance and checks
    that a real `brew` executable now exists and reports a version."""
    result = exec_in(container, "bash", "-lc", "./install-homebrew.sh", timeout=900)
    assert result.returncode == 0, result.stdout + result.stderr

    check = exec_in(
        container, "bash", "-lc",
        'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)" && brew --version',
    )
    assert check.returncode == 0, check.stdout + check.stderr
    assert "Homebrew" in check.stdout


def test_copy_tui(container, tmp_path):
    """`copy_tui`: mirrors infrastructure/scripts/install-brewe2e.sh — removes the
    current ~tester/BrewE2E/src and copies a fresh brew_tui source tree in, then
    checks the new files actually landed inside the container."""
    from conftest import REPO_ROOT

    staged = tmp_path / "new_brewe2e_src"
    staged.mkdir()
    subprocess.run(
        ["cp", "-r", str(REPO_ROOT / "src" / "brew_tui"), str(staged / "brew_tui")],
        check=True,
    )
    # marker file proves the *new* tree is what ends up in the container, not a stale one
    (staged / "brew_tui" / "_pytest_marker.py").write_text("MARKER = 'copy_tui-ran'\n")

    remove = exec_in(container, "rm", "-rf", "/home/tester/BrewE2E/src")
    assert remove.returncode == 0, remove.stderr

    mkdir = exec_in(container, "mkdir", "-p", "/home/tester/BrewE2E/src")
    assert mkdir.returncode == 0, mkdir.stderr

    cp = subprocess.run(
        ["docker", "cp", f"{staged}/.", f"{container}:/home/tester/BrewE2E/src/"],
        capture_output=True, text=True, timeout=60,
    )
    assert cp.returncode == 0, cp.stdout + cp.stderr

    check = exec_in(container, "test", "-f", "/home/tester/BrewE2E/src/brew_tui/_pytest_marker.py")
    assert check.returncode == 0, "new brew_tui source did not land in the container"


def test_brew_tui_install(container, tmp_path, request):
    """`brew_tui_install`: runs `./run-brewe2e.sh install <formula>` inside the
    instance, then checks BOTH that real `brew` actually installed it into the
    Cellar and that brew-tui's sqlite DB has a matching 'installed' row."""
    formula = request.config.getoption("--formula")

    result = exec_in(
        container, "bash", "-lc", f"./run-brewe2e.sh install {shlex.quote(formula)}", timeout=900,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    cellar_check = exec_in(
        container, "bash", "-lc",
        f'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)" && test -d "$(brew --cellar)/{formula}"',
    )
    assert cellar_check.returncode == 0, f"'{formula}' not found in the real Cellar after install"

    db_copy = tmp_path / "brew.db"
    _copy_db_out(container, db_copy)
    conn = sqlite3.connect(db_copy)
    try:
        row = conn.execute(
            "SELECT name, status FROM packages WHERE name = ?", (formula,)
        ).fetchone()
    finally:
        conn.close()
    assert row is not None, f"'{formula}' missing from brew-tui's DB after install"
    assert row[1] == "installed", f"'{formula}' DB status is '{row[1]}', expected 'installed'"


def test_brew_tui_list(container, request):
    """`brew_tui_list`: runs `./run-brewe2e.sh list` inside the instance and checks
    the formula installed by test_brew_tui_install shows up in the output."""
    formula = request.config.getoption("--formula")

    result = exec_in(container, "bash", "-lc", "./run-brewe2e.sh list")
    assert result.returncode == 0, result.stdout + result.stderr
    assert formula in result.stdout, f"'{formula}' not listed by brew-tui list:\n{result.stdout}"
