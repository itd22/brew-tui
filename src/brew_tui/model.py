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
