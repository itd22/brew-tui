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
