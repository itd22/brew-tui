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
from .tui import BrewTUI, BrewTUIApp
from .e2e import BrewE2E

__version__ = "0.0.11"

__all__ = [
    "PackageState",
    "LockInfo",
    "Status",
    "BrewTUI",
    "BrewTUIApp",
    "BrewE2E",
    "__version__",
]
