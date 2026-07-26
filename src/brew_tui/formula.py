"""Unused: no live code path in this package imports from here (only other
unused files — formulary.py, installer.py, keg.py's TYPE_CHECKING-only import —
reference it).

Models Homebrew's Formula base class (Library/Homebrew/formula.rb) — the
abstract type every generated formula (e.g. a `Meld` class) would inherit from
in an in-process implementation: name, tap, version, license, and the
install()/recursive_dependencies() a concrete formula must define. The actual
implementation never instantiates formulas in-process; it reads
INSTALL_RECEIPT.json off disk (RealCellarReader in db.py) and shells out to the
real `brew` executable (BrewCLIRunner in cli_runner.py) instead. Kept as a
structural reference for what an in-process model would look like.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from .tap import Tap
from .spec import SoftwareSpec
from .dependency import Dependency


# --- Formula: Library/Homebrew/formula.rb (abstract base for every *.rb formula file) ---

@dataclass
class PkgVersion:
    version: str
    revision: int = 0


class Formula(ABC):
    """Abstract base every generated Formula subclass (e.g. `Meld`) inherits."""

    name: str
    tap: Tap
    stable: SoftwareSpec
    pkg_version: PkgVersion
    license: str | None = None
    homepage: str = ""

    @property
    @abstractmethod
    def prefix(self) -> Path:
        ...

    @abstractmethod
    def install(self) -> None:
        """The formula-authored build/install recipe (e.g. Meld#install)."""
        ...

    @abstractmethod
    def recursive_dependencies(self) -> list[Dependency]:
        ...
