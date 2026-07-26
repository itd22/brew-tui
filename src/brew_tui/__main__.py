"""Entry point for `python3 -m brew_tui`.

Deliberately a separate module from `tui.py`: `brew_tui/__init__.py` already does
`from .tui import BrewTUI, BrewTUIApp` at package-import time, so running
`python3 -m brew_tui.tui` makes runpy import the package first (which imports
`brew_tui.tui` as an ordinary module), then try to execute that same module again
as `__main__` — Python detects `brew_tui.tui` already sitting in `sys.modules` and
raises:

    RuntimeWarning: 'brew_tui.tui' found in sys.modules after import of package
    'brew_tui', but prior to execution of 'brew_tui.tui'; this may result in
    unpredictable behaviour

`python3 -m brew_tui` avoids that: this module has no other name to collide with.
"""
from .tui import main

# Only runs when this module is executed directly (`python3 -m brew_tui`, per the
# module docstring above) — not when `brew_tui` is merely imported as a package.
if __name__ == "__main__":
    raise SystemExit(main())
