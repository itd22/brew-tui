"""brew-tui: interactive front-end over a real Homebrew installation.

Structure mirrors Homebrew/brew's own entities (Tap, Formulary, Formula,
FormulaInstaller, Keg/Cellar, Tab) plus two additions for this project:

- `Status`  — reads Homebrew's real per-formula lock file and reports whether
  it is live or stale.
- `BrewTUI` — the `brew-tui` business logic, which consults `Status` before every
  install/uninstall so concurrent runs can't race a real in-progress operation.
- `BrewTUIApp` — the full-screen, interactive `brew-tui` front-end, built on the
  Textual TUI framework (https://textual.textualize.io/).

`BrewTUI`/`BrewTUIApp`/`BrewE2E` are deliberately NOT re-exported here (no
`from .tui import ...` / `from .e2e import ...`, lazy or otherwise) — import
them from their own submodules instead: `from brew_tui.tui import BrewTUI,
BrewTUIApp` / `from brew_tui.e2e import BrewE2E`. Re-exporting either at
package level, even lazily, ties this file to `.tui`/`.e2e`'s existence; not
importing them here at all is what actually keeps `python -m brew_tui.tui`
and `python -m brew_tui.e2e` warning-free (see e2e.py's and tui.py's own
`if __name__ == "__main__":` comments), with no import-time trickery needed
to get there.
"""

from .enums import PackageState
from .status import LockInfo, Status

__version__ = "0.0.21"

__all__ = [
    "PackageState",
    "LockInfo",
    "Status",
    "__version__",
]
