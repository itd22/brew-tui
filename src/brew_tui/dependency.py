"""Unused: no live code path in this package imports from here.

Models Homebrew's dependency-declaration layer (Library/Homebrew/dependency*.rb) —
a formula's declared deps and how to resolve one into its own Formula. Part of the
in-process Formulary/Formula/FormulaInstaller object graph (see formula.py,
formulary.py, installer.py) that this project deliberately did NOT wire up: the
real implementation (RealCellarReader + BrewCLIRunner in db.py/cli_runner.py)
shells out to the actual `brew` executable instead of reimplementing its
dependency resolution in Python. Kept as a structural reference for what that
in-process model would look like.
"""
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
