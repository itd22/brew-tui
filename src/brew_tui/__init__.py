"""brew-tui: interactive front-end over a real Homebrew installation.

Structure mirrors Homebrew/brew's own entities (Tap, Formulary, Formula,
FormulaInstaller, Keg/Cellar, Tab) plus two additions for this project:

- `Status`  — reads Homebrew's real per-formula lock file and reports whether
  it is live or stale.
- `BrewTUI` — the `brew-tui` entry point, which consults `Status` before every
  install/uninstall so concurrent runs can't race a real in-progress operation.
"""

from .enums import PackageState
from .status import LockInfo, Status
from .tui import BrewTUI
from .e2e import BrewE2E

__version__ = "0.0.5"

__all__ = [
    "PackageState",
    "LockInfo",
    "Status",
    "BrewTUI",
    "BrewE2E",
    "__version__",
]
