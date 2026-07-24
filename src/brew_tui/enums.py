from enum import Enum, auto


class PackageState(Enum):
    NOT_INSTALLED = auto()
    INSTALLED = auto()
    OUTDATED = auto()
    PINNED = auto()
    BROKEN = auto()
    KEG_ONLY = auto()
