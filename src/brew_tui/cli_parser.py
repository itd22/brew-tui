from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# --- bin/brew + Homebrew::CLI::Parser -> cmd/install.rb, cmd/uninstall.rb, cmd/update.rb ---
#
# All three of these are live: every command in commands.py extends `Command`;
# `BrewE2E` (e2e.py) extends `CLIParser`, implementing `parse()` as the same
# argv-splitting logic that used to live inline in its `run()`. `BrewTUI.run()`
# (tui.py) still does its own small inline `command_name, *rest = argv` split
# rather than going through a `CLIParser` — it dispatches straight to
# install()/uninstall()/list_installed() and never builds a `ParsedArgs` at all,
# so adopting `CLIParser` there would mean also adopting the `Command`/
# `ParsedArgs` object model, not just extracting a parse step.

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
