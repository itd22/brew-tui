"""Regression test for:

    <frozen runpy>:130: RuntimeWarning: 'brew_tui.tui' found in sys.modules after
    import of package 'brew_tui', but prior to execution of 'brew_tui.tui'; this
    may result in unpredictable behaviour

Caused by `python3 -m brew_tui.tui` (or `uv run python -m brew_tui.tui`, etc.):
`brew_tui/__init__.py` used to do `from .tui import BrewTUI, BrewTUIApp` eagerly at
package-import time, so by the time runpy went to execute `brew_tui.tui` as
`__main__`, it was already sitting in `sys.modules` under its normal name. The same
bug independently existed for `python -m brew_tui.e2e` (`__init__.py` also did
`from .e2e import BrewE2E` eagerly).

Fixed at the actual source, without any lazy-import trickery: `__init__.py` simply
doesn't import from `.tui` or `.e2e` at all anymore (no eager import, no PEP 562
`__getattr__` either) — so importing the `brew_tui` package never touches either
module, and `python -m brew_tui.tui` / `python -m brew_tui.e2e` both run clean.
`BrewTUI`/`BrewTUIApp`/`BrewE2E` are no longer package-level names; import them from
their own submodules (`from brew_tui.tui import BrewTUI, BrewTUIApp`, `from
brew_tui.e2e import BrewE2E`). `brew_tui/__main__.py` (added in 0.0.12) still exists
too, so `python -m brew_tui` also works, but it was never the fix for this.
"""
import subprocess
import sys

from conftest import REPO_ROOT


def _run_module(module: str) -> subprocess.CompletedProcess:
    env = {"PYTHONPATH": str(REPO_ROOT / "src")}
    args = [sys.executable, "-W", "error::RuntimeWarning", "-m", module, "list"]
    return subprocess.run(args, capture_output=True, text=True, timeout=30, env=env)


def test_python_dash_m_brew_tui_dot_tui_does_not_warn():
    """The exact command from the bug report: `python -m brew_tui.tui`."""
    result = _run_module("brew_tui.tui")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "RuntimeWarning" not in result.stderr


def test_python_dash_m_brew_tui_dot_e2e_does_not_warn():
    """Same bug, independently present for `python -m brew_tui.e2e`."""
    result = _run_module("brew_tui.e2e")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "RuntimeWarning" not in result.stderr


def test_python_dash_m_brew_tui_does_not_warn():
    """The package-level form also stays warning-free."""
    result = _run_module("brew_tui")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "RuntimeWarning" not in result.stderr


def test_brewtui_brewtuiapp_brewe2e_importable_from_their_own_submodules():
    """No longer re-exported at package level — must be imported directly from
    `brew_tui.tui` / `brew_tui.e2e`."""
    result = subprocess.run(
        [sys.executable, "-c",
         "from brew_tui.tui import BrewTUI, BrewTUIApp; from brew_tui.e2e import BrewE2E"],
        capture_output=True, text=True, timeout=30,
        env={"PYTHONPATH": str(REPO_ROOT / "src")},
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_brewtui_brewe2e_not_package_level_names():
    """Confirms __init__.py really doesn't import .tui/.e2e at all anymore —
    not even lazily."""
    result = subprocess.run(
        [sys.executable, "-c",
         "import brew_tui; assert not hasattr(brew_tui, 'BrewTUI'); "
         "assert not hasattr(brew_tui, 'BrewE2E')"],
        capture_output=True, text=True, timeout=30,
        env={"PYTHONPATH": str(REPO_ROOT / "src")},
    )
    assert result.returncode == 0, result.stdout + result.stderr
