"""Unused: no live code path in this package imports from here.

A proposed top-level facade (`BrewModel.install/remove/update`) that would sit
in front of the in-process Formulary/FormulaInstaller/Keg object graph (see
formula.py, formulary.py, installer.py, keg.py) the way `BrewTUI` (tui.py) sits
in front of the real implementation. Every method here is an unimplemented stub
(`...`) — this file predates `BrewTUI`/`BrewE2E`, which is what actually plays
this facade role today, calling out to the real `brew` executable instead of an
in-process formula graph. Kept as a sketch of the alternative, fully in-process
design this project chose not to pursue.
"""
from .keg import Cellar
from .tap import Tap
from .commands import OperationResult


class BrewModel:
    """Facade: `brew install`, `brew remove`, `brew update`.

    install(name):  Formulary.factory -> FormulaInstaller(formula).fetch()/install()/finish()
    remove(name):   Formulary.factory -> Keg.uninstall()
    update():       Tap.each -> git pull, refreshes Formulary's cache
    """

    def __init__(self, cellar: Cellar, taps: list[Tap]) -> None:
        self.cellar = cellar
        self.taps = taps

    def install(self, name: str) -> OperationResult:
        ...

    def remove(self, name: str) -> OperationResult:
        ...

    def update(self) -> OperationResult:
        ...
