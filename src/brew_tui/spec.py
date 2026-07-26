"""Unused: no live code path in this package imports from here (only formula.py,
itself unused, references it).

Models Homebrew's download/spec layer (Library/Homebrew/software_spec.rb,
resource.rb, download_strategy.rb) — a formula's stable spec (source URL,
checksum, bottle SHAs per platform, declared deps) plus the strategy that would
fetch it (curl, git, ...). The real implementation never downloads or verifies
source itself; the real `brew` executable (BrewCLIRunner in cli_runner.py) does
all of that. Kept as a structural reference for what an in-process fetch layer
would look like.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from .dependency import Dependency


# --- Download layer: Library/Homebrew/software_spec.rb, resource.rb, download_strategy.rb ---

@dataclass
class Resource:
    url: str
    sha256: str
    mirrors: list[str] = field(default_factory=list)


@dataclass
class BottleSpecification:
    rebuild: int
    root_url: str
    sha256_by_platform: dict[str, str] = field(default_factory=dict)


@dataclass
class SoftwareSpec:
    """A stable/head version spec: url, checksum, resources, patches, options."""
    resource: Resource
    bottle: BottleSpecification | None = None
    dependencies: list[Dependency] = field(default_factory=list)


class DownloadStrategy(ABC):
    """Base for CurlDownloadStrategy, GitDownloadStrategy, etc."""

    @abstractmethod
    def fetch(self, resource: Resource) -> Path:
        ...
