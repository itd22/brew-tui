from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .formula import Formula


# --- Dependency resolution: Library/Homebrew/dependency*.rb ---

@dataclass
class Dependency:
    name: str
    tags: list[str] = field(default_factory=list)  # e.g. ":build", ":optional"

    def to_formula(self) -> "Formula":
        ...


class DependencyCollector(ABC):
    """Builds a formula's declared Dependency list from its DSL body."""

    @abstractmethod
    def add(self, spec) -> Dependency:
        ...
