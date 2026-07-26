from dataclasses import dataclass
from pathlib import Path


# --- Cellar: Library/Homebrew/keg.rb ---
#
# Live: this is the (path,) wrapper every module in this package constructs and
# passes around (db.py, e2e.py, tui.py, commands.py). The rest of keg.rb's real
# object model — Keg, Tab — lives in unused_brew_model/keg_model.py instead;
# nothing here instantiates or subclasses either of those. RealCellarReader
# (db.py) reads the same on-disk data (a formula's version dir + its
# INSTALL_RECEIPT.json) directly into a plain InstalledPackageInfo dataclass.

@dataclass
class Cellar:
    path: Path

    def rack_for(self, name: str) -> Path:
        ...
