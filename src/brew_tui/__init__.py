"""brew-tui: interactive front-end over a real Homebrew installation.

Structure mirrors Homebrew/brew's own entities (Tap, Formulary, Formula,
FormulaInstaller, Keg/Cellar, Tab) plus two additions for this project:

- `Status`  — reads Homebrew's real per-formula lock file and reports whether
  it is live or stale.
- `BrewTUI` — the `brew-tui` business logic, which consults `Status` before every
  install/uninstall so concurrent runs can't race a real in-progress operation.
- `BrewTUIApp` — the full-screen, interactive `brew-tui` front-end, built on the
  Textual TUI framework (https://textual.textualize.io/).
"""

from .enums import PackageState
from .status import LockInfo, Status

__version__ = "0.0.20"

__all__ = [
    "PackageState",
    "LockInfo",
    "Status",
    "BrewTUI",
    "BrewTUIApp",
    "BrewE2E",
    "__version__",
]


def __getattr__(name):
    # BrewTUI/BrewTUIApp/BrewE2E are lazily imported (PEP 562) instead of
    # imported eagerly above. Importing `.tui` or `.e2e` at package-import time
    # would put 'brew_tui.tui'/'brew_tui.e2e' in sys.modules before
    # `python -m brew_tui.tui` / `python -m brew_tui.e2e` gets a chance to
    # execute it as `__main__`, which is exactly what triggers:
    #   RuntimeWarning: 'brew_tui.tui' found in sys.modules after import of
    #   package 'brew_tui', but prior to execution of 'brew_tui.tui'
    # `from brew_tui import BrewTUI` / `BrewE2E` still works — it just imports
    # the submodule here, on first access, instead of during `import brew_tui`.
    if name in ("BrewTUI", "BrewTUIApp"):
        from . import tui
        value = getattr(tui, name)
        globals()[name] = value  # cache: subsequent lookups skip __getattr__
        return value
    if name == "BrewE2E":
        from .e2e import BrewE2E
        globals()[name] = BrewE2E
        return BrewE2E
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
