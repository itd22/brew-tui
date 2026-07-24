from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# --- bin/brew + Homebrew::CLI::Parser -> cmd/install.rb, cmd/uninstall.rb, cmd/update.rb ---

class CLIParser(ABC):
    """Mirrors Homebrew::CLI::Parser: parses argv into a command + flags."""

    @abstractmethod
    def parse(self, argv: list[str]) -> "ParsedArgs":
        ...


@dataclass
class ParsedArgs:
    command_name: str
    named_args: list[str] = field(default_factory=list)
    options: dict[str, bool | str] = field(default_factory=dict)


class Command(ABC):
    """Base for Library/Homebrew/cmd/*.rb (install, uninstall, update, doctor)."""

    name: str

    @abstractmethod
    def run(self, args: ParsedArgs) -> int:
        ...
