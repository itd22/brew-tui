"""Regression test for:

    <frozen runpy>:130: RuntimeWarning: 'brew_tui.tui' found in sys.modules after
    import of package 'brew_tui', but prior to execution of 'brew_tui.tui'; this
    may result in unpredictable behaviour

Caused by `python3 -m brew_tui.tui` (or `uv run python -m brew_tui.tui`, etc.):
`brew_tui/__init__.py` used to do `from .tui import BrewTUI, BrewTUIApp` eagerly at
package-import time, so by the time runpy went to execute `brew_tui.tui` as
`__main__`, it was already sitting in `sys.modules` under its normal name. The same
bug independently existed for `python -m brew_tui.e2e` (`__init__.py` also did
`from .e2e import BrewE2E` eagerly) — caught while testing 0.0.20's `BrewE2E(cellar=
Cellar.default())` change, fixed the same way.

Fixed at the actual source: `__init__.py` now imports `.tui` AND `.e2e` lazily via a
PEP 562 module `__getattr__`, so importing the `brew_tui` package doesn't touch
either at all — `python -m brew_tui.tui` (the exact command from the bug report) and
`python -m brew_tui.e2e` both now run clean. `brew_tui/__main__.py` (added in 0.0.12)
still exists too, so `python -m brew_tui` also works, but it was never the fix for
this — the lazy import is.
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


def test_lazy_imports_still_expose_brewtui_brewtuiapp_brewe2e():
    """`from brew_tui import BrewTUI, BrewTUIApp, BrewE2E` must still work —
    __getattr__ should import `.tui`/`.e2e` lazily on first access, not remove
    the names."""
    result = subprocess.run(
        [sys.executable, "-c", "from brew_tui import BrewTUI, BrewTUIApp, BrewE2E"],
        capture_output=True, text=True, timeout=30,
        env={"PYTHONPATH": str(REPO_ROOT / "src")},
    )
    assert result.returncode == 0, result.stdout + result.stderr
