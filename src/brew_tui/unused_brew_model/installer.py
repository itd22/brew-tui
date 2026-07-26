"""Unused: no live code path in this package imports from here. (Previously also
referenced by commands.py's InstallCommand, which has since been removed —
nothing anywhere constructs it now.)

Models Homebrew's FormulaInstaller (Library/Homebrew/formula_installer.rb) and
the bottle-vs-compile decision it makes (PR #10788): given a resolved Formula,
fetch it, then either pour a prebuilt bottle or compile from source, then link
the Keg and write its Tab. In this project that whole orchestration is replaced
by one subprocess call to the real `brew install <name>` (BrewCLIRunner in
cli_runner.py) — `brew` itself makes the bottle-vs-compile decision, so nothing
here needs reimplementing it. Kept as a structural reference for what an
in-process installer + policy layer would look like.
"""
from abc import ABC, abstractmethod
from enum import Enum, auto

from ..formula import Formula


# --- FormulaInstaller: Library/Homebrew/formula_installer.rb (orchestrator) ---

class FormulaInstaller(ABC):
    """Coordinates deps, fetch, pour/build, keg creation, Tab, and linking."""

    formula: Formula
    installed_as_dependency: bool = False
    installed_on_request: bool = False
    ignore_deps: bool = False
    force_bottle: bool = False

    @abstractmethod
    def fetch(self) -> None:
        ...

    @abstractmethod
    def install(self) -> None:
        ...

    @abstractmethod
    def finish(self) -> None:
        """Writes the Tab and links the Keg."""
        ...


# --- Install policy (bottle-only vs allow-compile) ---

class InstallPolicy(Enum):
    AUTO = auto()               # default: prefer bottle, fall back to compiling
    FORCE_BOTTLE = auto()       # --force-bottle: bottle required, fail otherwise
    BUILD_FROM_SOURCE = auto()  # --build-from-source: always compile, ignore bottle


class NoBottleError(Exception):
    def __init__(self, formula_name: str, needs_compile: list[str]) -> None:
        self.formula_name = formula_name
        self.needs_compile = needs_compile
        super().__init__(
            f"{formula_name}: no bottle available for: {', '.join(needs_compile)}. "
            f"Try `brew install --build-from-source {formula_name}`."
        )


class BottleAvailabilityChecker:
    """Concrete: mirrors the bottle-check logic added in brew PR #10788."""

    def __init__(self, current_platform: str) -> None:
        self.current_platform = current_platform

    def has_bottle_for_current_platform(self, formula: Formula) -> bool:
        bottle = formula.stable.bottle
        if bottle is None:
            return False
        return self.current_platform in bottle.sha256_by_platform

    def find_unbottled(self, formula: Formula) -> list[str]:
        """Walks formula + recursive_dependencies, returns names lacking a bottle."""
        unbottled: list[str] = []
        if not self.has_bottle_for_current_platform(formula):
            unbottled.append(formula.name)
        for dep in formula.recursive_dependencies():
            dep_formula = dep.to_formula()
            if not self.has_bottle_for_current_platform(dep_formula):
                unbottled.append(dep_formula.name)
        return unbottled


class PolicyEnforcedInstaller:
    """Concrete: wraps FormulaInstaller, applying InstallPolicy before fetch/install."""

    def __init__(self, installer: FormulaInstaller, checker: BottleAvailabilityChecker) -> None:
        self.installer = installer
        self.checker = checker

    def install(self, formula: Formula, policy: InstallPolicy) -> None:
        if policy is InstallPolicy.FORCE_BOTTLE:
            unbottled = self.checker.find_unbottled(formula)
            if unbottled:
                raise NoBottleError(formula.name, unbottled)
            self._pour_bottle(formula)

        elif policy is InstallPolicy.BUILD_FROM_SOURCE:
            self._compile_from_source(formula)

        else:  # AUTO
            if self.checker.has_bottle_for_current_platform(formula):
                self._pour_bottle(formula)
            else:
                self._compile_from_source(formula)

    def _pour_bottle(self, formula: Formula) -> None:
        self.installer.formula = formula
        self.installer.force_bottle = True
        self.installer.fetch()
        self.installer.install()
        self.installer.finish()

    def _compile_from_source(self, formula: Formula) -> None:
        self.installer.formula = formula
        self.installer.force_bottle = False
        self.installer.fetch()
        self.installer.install()   # runs formula.install() build recipe
        self.installer.finish()


def make_formula_installer(formula: Formula) -> FormulaInstaller:
    """Factory producing a concrete FormulaInstaller for `formula` (impl-specific)."""
    ...
