from abc import ABC, abstractmethod

from .formula import Formula


# --- Formulary: Library/Homebrew/formulary.rb (factory/loader) ---

class Formulary(ABC):
    """Loads/resolves a formula name to a Formula, via a Tap or the API cache."""

    @staticmethod
    @abstractmethod
    def factory(name: str, force_bottle: bool = False) -> Formula:
        ...
