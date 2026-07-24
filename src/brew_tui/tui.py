import sys

from .db import BrewDB, RealCellarReader
from .cli_runner import BrewCLIRunner
from .status import Status
from .keg import Cellar
from .e2e import BrewE2E


class BrewTUI:
    """`brew-tui`: the interactive terminal front-end.

    Before running install/uninstall it always calls `Status.is_installing(name)` first:
      - a real, live lock  -> refuse and tell the user an install is already in progress
      - a stale lock       -> clear it automatically, then proceed
      - no lock            -> proceed straight away

    Delegates the actual work to the same collaborators `BrewE2E` uses
    (`RealCellarReader`, `BrewDB`, `BrewCLIRunner`), so `brew-tui` and the
    scriptable `BrewE2E` CLI stay consistent with each other.
    """

    def __init__(self, reader: RealCellarReader, db: BrewDB, cli: BrewCLIRunner,
                 status: Status, on_output=None) -> None:
        self.reader = reader
        self.db = db
        self.cli = cli
        self.status = status
        self.on_output = on_output  # optional sink for streamed `brew` output (TUI pane)

    def _print(self, line: str) -> None:
        print(line)
        if self.on_output is not None:
            self.on_output(line)

    def _guard(self, name: str) -> bool:
        """Returns True if it's safe to proceed; handles stale-lock cleanup itself."""
        lock = self.status.check(name)
        if not lock.exists:
            return True
        if self.status.is_stale(lock):
            self._print(f"{name}: found stale lock at {lock.path} (pid={lock.pid}), clearing")
            self.status.clear_stale(name)
            return True
        self._print(f"{name}: install/uninstall already in progress (lock held by pid={lock.pid}), aborting")
        return False

    def install(self, name: str) -> int:
        if not self._guard(name):
            return 1
        if not self.db.exists():
            self.db.create_schema()

        record = next((r for r in self.db.all_packages()
                        if r.name == name and r.status == "installed"), None)
        if record is not None:
            self._print(f"{name}: already installed per DB (version {record.version})")
            return 0

        info = self.reader.find(name)
        if info is not None:
            self._print(f"{name}: already installed per real Cellar json (version {info.version})")
            self.db.sync_from_cellar(self.reader.scan())
            return 0

        self._print(f"{name}: not installed — running real `brew install {name}`")
        output = self.cli.install(name, on_line=self._print)
        if output is None:
            message = f"`brew` executable not available; cannot install '{name}'."
            self._print(message)
            self.db.mark_error(name, message)
            return 1
        self.db.sync_from_cellar(self.reader.scan())
        return 0

    def uninstall(self, name: str) -> int:
        if not self._guard(name):
            return 1
        if not self.db.exists():
            self.db.create_schema()

        info = self.reader.find(name)
        if info is None:
            self._print(f"{name}: not installed, nothing to uninstall")
            return 0

        self._print(f"{name}: installed (version {info.version}) — running real `brew uninstall {name}`")
        output = self.cli.uninstall(name, on_line=self._print)
        if output is None:
            message = f"`brew` executable not available; cannot uninstall '{name}'."
            self._print(message)
            self.db.mark_error(name, message)
            return 1
        self.db.sync_from_cellar(self.reader.scan())
        return 0

    def list_installed(self) -> int:
        """`brew-tui list`: syncs the DB from the real Cellar, then prints installed
        formulae. Read-only, so it does not go through `Status`/`_guard`."""
        if not self.db.exists():
            self.db.create_schema()
        infos = self.reader.scan()
        self.db.sync_from_cellar(infos)
        for info in infos:
            self._print(f"{info.name} {info.version} [{info.method}] tap={info.tap}")
        return 0

    @classmethod
    def default(cls) -> "BrewTUI":
        """Wires up real collaborators the same way `BrewE2E()` does."""
        cellar = Cellar(path=BrewE2E._default_cellar_path())
        reader = RealCellarReader(cellar)
        db = BrewDB(BrewE2E._default_db_path())
        if not db.exists():
            db.create_schema()
        return cls(reader=reader, db=db, cli=BrewCLIRunner(), status=Status())

    def run(self, argv: list[str]) -> int:
        if not argv:
            self._print("usage: brew-tui <install|uninstall|list> [name]")
            return 1
        command_name, *rest = argv
        if command_name == "install" and rest:
            return self.install(rest[0])
        if command_name == "uninstall" and rest:
            return self.uninstall(rest[0])
        if command_name == "list":
            return self.list_installed()
        self._print(f"Unknown command: {' '.join(argv)}")
        return 1


def main() -> int:
    return BrewTUI.default().run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
