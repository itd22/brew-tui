"""Unused: no live code path in this package imports from here.

Models Homebrew's Formulary (Library/Homebrew/formulary.rb) — the factory that
resolves a formula name string to a loaded Formula object, normally by reading
its Ruby DSL file from a Tap or the API cache. In this project that resolution
step doesn't exist: RealCellarReader (db.py) reads already-installed formulae
straight from INSTALL_RECEIPT.json, and installing/uninstalling a not-yet-known
formula is delegated entirely to the real `brew` executable (BrewCLIRunner in
cli_runner.py), so nothing ever needs to load formula *definitions* in-process.
Kept as a structural reference for what that resolution step would look like.
"""
from abc import ABC, abstractmethod

from ..formula import Formula


# --- Formulary: Library/Homebrew/formulary.rb (factory/loader) ---

class Formulary(ABC):
    """Loads/resolves a formula name to a Formula, via a Tap or the API cache."""

    @staticmethod
    @abstractmethod
    def factory(name: str, force_bottle: bool = False) -> Formula:
        ...
