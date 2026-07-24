"""Regression test for:

    <frozen runpy>:130: RuntimeWarning: 'brew_tui.tui' found in sys.modules after
    import of package 'brew_tui', but prior to execution of 'brew_tui.tui'; this
    may result in unpredictable behaviour

Caused by `python3 -m brew_tui.tui` (or `uv run python -m brew_tui.tui`, etc.):
`brew_tui/__init__.py` used to do `from .tui import BrewTUI, BrewTUIApp` eagerly at
package-import time, so by the time runpy went to execute `brew_tui.tui` as
`__main__`, it was already sitting in `sys.modules` under its normal name.

Fixed at the actual source: `__init__.py` now imports `.tui` lazily via a PEP 562
module `__getattr__`, so importing the `brew_tui` package no longer touches `.tui`
at all — `python -m brew_tui.tui` (the exact command from the bug report) now runs
clean. `brew_tui/__main__.py` (added in 0.0.12) still exists too, so `python -m
brew_tui` also works, but it was never the fix for this — the lazy import is.
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


def test_python_dash_m_brew_tui_does_not_warn():
    """The package-level form also stays warning-free."""
    result = _run_module("brew_tui")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "RuntimeWarning" not in result.stderr


def test_lazy_tui_import_still_exposes_brewtui_and_brewtuiapp():
    """`from brew_tui import BrewTUI, BrewTUIApp` must still work — __getattr__
    should import `.tui` lazily on first access, not remove the names."""
    result = subprocess.run(
        [sys.executable, "-c", "from brew_tui import BrewTUI, BrewTUIApp"],
        capture_output=True, text=True, timeout=30,
        env={"PYTHONPATH": str(REPO_ROOT / "src")},
    )
    assert result.returncode == 0, result.stdout + result.stderr
