import os
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

    @classmethod
    def default(cls) -> "Cellar":
        """Resolves the real Homebrew/Linuxbrew Cellar: $HOMEBREW_CELLAR if set,
        else the first of the usual install locations that exists on disk, else
        the Linuxbrew default. Both BrewE2E.__init__ and BrewTUI.default() (tui.py)
        call this directly, so it lives here rather than on either of them."""
        env = os.environ.get("HOMEBREW_CELLAR")
        if env:
            return cls(Path(env))
        for candidate in (
            Path("/home/linuxbrew/.linuxbrew/Cellar"),
            Path("/opt/homebrew/Cellar"),
            Path("/usr/local/Cellar"),
        ):
            if candidate.exists():
                return cls(candidate)
        return cls(Path("/home/linuxbrew/.linuxbrew/Cellar"))
