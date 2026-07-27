import os
import sys
from pathlib import Path

from .cli_parser import CLIParser, Command, ParsedArgs
from .keg import Cellar
from .db import BrewDB, RealCellarReader
from .cli_runner import BrewCLIRunner
from .commands import RealListCommand, StoreDbCommand, RealInstallCommand, ListCompareCommand


class BrewE2E(CLIParser):
    """Real, scriptable entry point, backed by the actual Homebrew/Linuxbrew Cellar on disk.

    Also fills the `CLIParser` role (cli_parser.py) — its argv-splitting logic used
    to live inline in `run()`; `parse()` below is that same logic, just extracted
    to satisfy `CLIParser`'s one abstract method.
    """

    def __init__(self, cellar: Cellar | None = None, db_path: Path | None = None) -> None:
        self.cellar = cellar or Cellar.default()
        self.reader = RealCellarReader(self.cellar)
        self.db = BrewDB(db_path or self.default_db_path())
        if not self.db.exists():
            print(f"No database found at {self.db.db_path}, creating it")
            self.db.create_schema()
        self.commands: dict[str, Command] = {
            "list": RealListCommand(self.reader, self.db),
            "store-db": StoreDbCommand(self.reader, self.db),
            "install": RealInstallCommand(self.reader, self.db, BrewCLIRunner()),
            "list_compare": ListCompareCommand(self.reader, self.db, BrewCLIRunner()),
        }

    @staticmethod
    def default_db_path() -> Path:
        env = os.environ.get("HOMEBREW_DB_PATH")
        return Path(env) if env else Path.home() / ".brew_e2e" / "brew.db"

    def parse(self, argv: list[str]) -> ParsedArgs:
        """Splits `argv` into a command name + its remaining args. Caller must
        ensure `argv` is non-empty (see the `if not argv` guard in `run()`)."""
        command_name, *rest = argv
        return ParsedArgs(command_name=command_name, named_args=rest)

    def run(self, argv: list[str]) -> int:
        if not argv:
            print("usage: BrewE2E <command> [args...]")
            return 1
        parsed = self.parse(argv)
        command = self.commands.get(parsed.command_name)
        if command is None:
            print(f"Unknown command: {parsed.command_name}")
            return 1
        return command.run(parsed)


# Lets this file double as a standalone script (`python3 -m brew_tui.e2e install
# ripgrep`) as well as being imported normally (`from .e2e import BrewE2E`, used
# by tui.py and __init__.py) — the block below only runs in the former case.
if __name__ == "__main__":
    sys.exit(BrewE2E().run(sys.argv[1:]))
