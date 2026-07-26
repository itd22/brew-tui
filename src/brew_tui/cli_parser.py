from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# --- bin/brew + Homebrew::CLI::Parser -> cmd/install.rb, cmd/uninstall.rb, cmd/update.rb ---
#
# `ParsedArgs` and `Command` below are live — every command in commands.py
# extends `Command`, and `BrewTUI.run()`/`BrewE2E.run()` build a `ParsedArgs`
# by hand from argv. `CLIParser` itself is NOT: nothing subclasses it. Real argv
# parsing is a few lines of manual `command_name, *rest = argv` splitting in
# tui.py/e2e.py rather than a dedicated parser class. Kept as a structural
# reference for what a real flag/option parser would plug in as.

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
