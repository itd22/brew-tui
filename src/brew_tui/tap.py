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
