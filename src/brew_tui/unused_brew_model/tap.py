"""Unused: no live code path in this package imports from here (only formula.py
and model.py, both themselves unused, reference it).

Models Homebrew's Tap (Library/Homebrew/tap.rb) — a formula repository (user,
repo, remote git URL, local clone path), the unit `brew tap`/`brew untap`
operate on. The real implementation only ever reads a formula's tap name as a
plain string off an existing INSTALL_RECEIPT.json (InstalledPackageInfo.tap in
db.py); it never clones, updates, or otherwise operates on a tap itself. Kept
as a structural reference for what modeling a tap as its own object would
look like.
"""
from dataclasses import dataclass
from pathlib import Path


# --- Tap: Library/Homebrew/tap.rb ---

@dataclass
class Tap:
    user: str
    repo: str
    remote_url: str
    path: Path

    @property
    def full_name(self) -> str:
        ...
