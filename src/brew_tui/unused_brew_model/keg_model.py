"""Unused: no live code path in this package imports from here.

Models the rest of Homebrew's Keg/Tab layer (Library/Homebrew/keg.rb,
tab.rb) — the part of keg.rb that isn't the plain `Cellar` path wrapper
(that half stayed live, in keg.py at the package root): `Keg`, a single
installed version of a `Formula` with link()/unlink()/uninstall(), and
`Tab`, the in-process representation of a formula's INSTALL_RECEIPT.json.

The real implementation (RealCellarReader in db.py) reads that same
INSTALL_RECEIPT.json straight into a plain `InstalledPackageInfo` dataclass
instead of a `Tab`, and never builds a `Keg` object at all — linking,
unlinking, and uninstalling are all just the real `brew` executable
(BrewCLIRunner in cli_runner.py). Kept as a structural reference for what
that closer-to-Homebrew in-process model would look like.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from .formula import PkgVersion


class Keg(ABC):
    """A single installed version of a Formula living in the Cellar."""

    path: Path
    formula_name: str
    version: PkgVersion

    @abstractmethod
    def link(self, overwrite: bool = False) -> list[Path]:
        ...

    @abstractmethod
    def unlink(self) -> list[Path]:
        ...

    @abstractmethod
    def uninstall(self) -> None:
        ...


# --- Tab: Library/Homebrew/tab.rb (the install receipt, INSTALL_RECEIPT.json) ---

@dataclass
class Tab:
    used_options: list[str] = field(default_factory=list)
    installed_as_dependency: bool = False
    installed_on_request: bool = True
    poured_from_bottle: bool = False
    tap: str = "homebrew/core"
    time: int | None = None

    @staticmethod
    def for_keg(keg: Keg) -> "Tab":
        ...
