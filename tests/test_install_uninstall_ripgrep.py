"""Docker-backed tests exercising brew-tui's scripted install/uninstall against a
real `ripgrep` formula (see tests/conftest.py for the container/image fixtures).

Each test runs `./run-brewe2e.sh install|uninstall ripgrep` as `tester` inside the
container (the same entry point `brew-tui install|uninstall <name>` uses) and checks
the real, on-disk effect: the actual Homebrew Cellar directory, and brew-tui's own
sqlite DB row.

    pytest --run-docker tests/test_install_uninstall_ripgrep.py

Tests run in file order against the same session-scoped container from
tests/conftest.py, so `test_uninstall_ripgrep` relies on `test_install_ripgrep`
(or `test_install_then_uninstall_ripgrep_roundtrip`) having already installed it.
That last test is self-contained: it installs and uninstalls on its own, so it also
covers a full install+uninstall cycle regardless of what ran before it.
"""
import sqlite3
import subprocess

import pytest

from conftest import exec_in

pytestmark = pytest.mark.docker

FORMULA = "ripgrep"


def _copy_db_out(container: str, dest) -> None:
    result = subprocess.run(
        ["docker", "cp", f"{container}:/home/tester/BrewTuiData/brew.db", str(dest)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"could not copy DB out of container:\n{result.stderr}"


def _cellar_has(container: str) -> bool:
    check = exec_in(
        container, "bash", "-lc",
        f'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)" && test -d "$(brew --cellar)/{FORMULA}"',
    )
    return check.returncode == 0


def _db_status(container: str, tmp_path) -> str | None:
    db_copy = tmp_path / "brew.db"
    _copy_db_out(container, db_copy)
    conn = sqlite3.connect(db_copy)
    try:
        row = conn.execute(
            "SELECT status FROM packages WHERE name = ?", (FORMULA,)
        ).fetchone()
    finally:
        conn.close()
    return row[0] if row is not None else None


def test_install_ripgrep(container):
    """`brew-tui install ripgrep`: real `brew` actually installs it into the Cellar."""
    result = exec_in(
        container, "bash", "-lc", f"./run-brewe2e.sh install {FORMULA}", timeout=900,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert _cellar_has(container), f"'{FORMULA}' not found in the real Cellar after install"


def test_install_ripgrep_db_row(container, tmp_path):
    """After `test_install_ripgrep`, brew-tui's DB has a matching 'installed' row."""
    status = _db_status(container, tmp_path)
    assert status == "installed", f"'{FORMULA}' DB status is {status!r}, expected 'installed'"


def test_uninstall_ripgrep(container):
    """`brew-tui uninstall ripgrep`: real `brew` actually removes it from the Cellar."""
    result = exec_in(
        container, "bash", "-lc", f"./run-brewe2e.sh uninstall {FORMULA}", timeout=900,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not _cellar_has(container), f"'{FORMULA}' still in the real Cellar after uninstall"


def test_uninstall_ripgrep_db_row(container, tmp_path):
    """After `test_uninstall_ripgrep`, brew-tui's DB row flips to 'removed'
    (rows are never deleted, only marked, per BrewDB.sync_from_cellar)."""
    status = _db_status(container, tmp_path)
    assert status == "removed", f"'{FORMULA}' DB status is {status!r}, expected 'removed'"


def test_install_then_uninstall_ripgrep_roundtrip(container, tmp_path):
    """Self-contained install+uninstall case: installs ripgrep, confirms it landed
    in the real Cellar and DB, uninstalls it, and confirms both cleared — independent
    of whatever order the tests above ran in."""
    install = exec_in(
        container, "bash", "-lc", f"./run-brewe2e.sh install {FORMULA}", timeout=900,
    )
    assert install.returncode == 0, install.stdout + install.stderr
    assert _cellar_has(container), f"'{FORMULA}' not found in the real Cellar after install"
    assert _db_status(container, tmp_path) == "installed"

    uninstall = exec_in(
        container, "bash", "-lc", f"./run-brewe2e.sh uninstall {FORMULA}", timeout=900,
    )
    assert uninstall.returncode == 0, uninstall.stdout + uninstall.stderr
    assert not _cellar_has(container), f"'{FORMULA}' still in the real Cellar after uninstall"
    assert _db_status(container, tmp_path) == "removed"
