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
