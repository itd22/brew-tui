from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from .formula import PkgVersion


# --- Cellar / Keg: Library/Homebrew/keg.rb ---
#
# `Cellar` below is live — it's the (path,) wrapper every module in this package
# constructs and passes around. `Keg` and `Tab` further down are NOT: nothing
# instantiates or subclasses them. RealCellarReader (db.py) reads the same
# on-disk data (a formula's version dir + its INSTALL_RECEIPT.json) directly
# into a plain InstalledPackageInfo dataclass instead of these Homebrew-shaped
# Keg/Tab types. Kept as a structural reference for what a closer-to-Homebrew
# in-process model would look like.

@dataclass
class Cellar:
    path: Path

    def rack_for(self, name: str) -> Path:
        ...


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
