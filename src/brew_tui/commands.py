from dataclasses import dataclass

from .cli_parser import Command, ParsedArgs
from .enums import PackageState
from .keg import Cellar
from .installer import (
    InstallPolicy, NoBottleError, BottleAvailabilityChecker, PolicyEnforcedInstaller,
    make_formula_installer,
)
from .db import BrewDB, RealCellarReader, dedupe_infos_by_name
from .cli_runner import BrewCLIRunner


# --- User-facing report ---

@dataclass
class OperationResult:
    command: str
    package_name: str
    success: bool
    state_before: PackageState
    state_after: PackageState
    message: str = ""


class InstallCommand(Command):
    """`brew install [--force-bottle | --build-from-source] <name>`.

    Unused: nothing constructs this. It models installing via the in-process
    Formulary/FormulaInstaller object graph (formula.py, formulary.py,
    installer.py) rather than shelling out to real `brew`; that graph is never
    wired up (see those files' module docstrings). The command that's actually
    used for `install` is RealInstallCommand below, which just calls the real
    `brew` executable. Kept as a worked example of what a fully in-process
    (non-shell-out) implementation would look like.
    """

    name = "install"

    def __init__(self, formulary_lookup, checker: BottleAvailabilityChecker,
                 db: "BrewDB | None" = None) -> None:
        self.formulary_lookup = formulary_lookup  # Formulary.factory
        self.checker = checker
        self.db = db

    def _resolve_policy(self, args: ParsedArgs) -> InstallPolicy:
        if args.options.get("force-bottle"):
            return InstallPolicy.FORCE_BOTTLE
        if args.options.get("build-from-source"):
            return InstallPolicy.BUILD_FROM_SOURCE
        return InstallPolicy.AUTO

    def run(self, args: ParsedArgs) -> int:
        policy = self._resolve_policy(args)
        for name in args.named_args:
            formula = self.formulary_lookup(name)
            installer = PolicyEnforcedInstaller(make_formula_installer(formula), self.checker)
            try:
                installer.install(formula, policy)
            except NoBottleError as e:
                print(str(e))
                return 1
            if self.db is not None:
                if not self.db.exists():
                    self.db.create_schema()
                self.db.upsert_package(name=formula.name, version=formula.pkg_version.version,
                                        revision=formula.pkg_version.revision)
        return 0


class ListCommand(Command):
    """`brew list` with no arguments: prints installed formula names from the Cellar.

    Unused: nothing constructs this. It only lists directory names under the
    Cellar path; RealListCommand below is what's actually used for `list` — it
    also parses each INSTALL_RECEIPT.json for version/tap/method and syncs BrewDB.
    Kept as the minimal version of "what's installed" for reference.
    """

    name = "list"

    def __init__(self, cellar: Cellar) -> None:
        self.cellar = cellar

    def _installed_formula_names(self) -> list[str]:
        if not self.cellar.path.exists():
            return []
        return sorted(
            p.name for p in self.cellar.path.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        )

    def run(self, args: ParsedArgs) -> int:
        for name in self._installed_formula_names():
            print(name)
        return 0


class RealCellarCommand(Command):
    """Base for every command that operates against the real Cellar + BrewDB.

    StoreDbCommand, RealListCommand, RealInstallCommand, and ListCompareCommand
    all took the identical (reader, db) constructor pair — pulling it up here
    means they now inherit it instead of each repeating the same __init__.
    """

    def __init__(self, reader: RealCellarReader, db: BrewDB) -> None:
        self.reader = reader
        self.db = db


class StoreDbCommand(RealCellarCommand):
    """`BrewE2E store-db`: creates the DB if missing, syncs it from real INSTALL_RECEIPT.json files."""

    name = "store-db"

    def run(self, args: ParsedArgs) -> int:
        if not self.db.exists():
            print(f"Creating database at {self.db.db_path}")
        self.db.create_schema()
        added, updated, removed = self.db.sync_from_cellar(self.reader.scan())
        print(f"added={added} updated={updated} removed={removed}")
        return 0


class RealListCommand(RealCellarCommand):
    """`BrewE2E list`: reads real INSTALL_RECEIPT.json files, prints them, and syncs the DB
    (adds new packages, updates changed ones, marks vanished ones 'removed' but keeps the row)."""

    name = "list"

    def run(self, args: ParsedArgs) -> int:
        infos = dedupe_infos_by_name(self.reader.scan())
        if not self.db.exists():
            self.db.create_schema()
        added, updated, removed = self.db.sync_from_cellar(infos)

        for info in infos:
            print(f"{info.name} {info.version} [{info.method}] tap={info.tap}")
        if added:
            print(f"new: {added}")
        if updated:
            print(f"updated: {updated}")
        if removed:
            print(f"removed (kept in db): {removed}")
        return 0


class RealInstallCommand(RealCellarCommand):
    """`BrewE2E install <name>`: checks the DB, then real Cellar jsons, then — only if
    genuinely not installed — calls the real `brew install <name>` executable."""

    name = "install"

    def __init__(self, reader: RealCellarReader, db: BrewDB, cli: BrewCLIRunner,
                 on_brew_output=None) -> None:
        super().__init__(reader, db)
        self.cli = cli
        self.on_brew_output = on_brew_output  # optional sink for live `brew` output (e.g. TUI pane)

    def run(self, args: ParsedArgs) -> int:
        if not self.db.exists():
            self.db.create_schema()
        for name in args.named_args:
            record = next((r for r in self.db.all_packages()
                           if r.name == name and r.status == "installed"), None)
            if record is not None:
                print(f"{name}: already installed per DB (version {record.version})")
                continue

            info = self.reader.find(name)
            if info is not None:
                print(f"{name}: already installed per real Cellar json (version {info.version})")
                self.db.sync_from_cellar(self.reader.scan())
                continue

            print(f"{name}: not installed — running real `brew install {name}`")
            output = self.cli.install(name, on_line=self.on_brew_output)
            if output is None:
                message = f"`brew` executable not available; cannot install '{name}'."
                print(message)
                self.db.mark_error(name, message)
            else:
                self.db.sync_from_cellar(self.reader.scan())
        return 0


class ListCompareCommand(RealCellarCommand):
    """`BrewE2E list_compare`: compares DB vs real INSTALL_RECEIPT.json vs actual `brew list`."""

    name = "list_compare"

    def __init__(self, reader: RealCellarReader, db: BrewDB, cli: BrewCLIRunner) -> None:
        super().__init__(reader, db)
        self.cli = cli

    def run(self, args: ParsedArgs) -> int:
        db_names = sorted(r.name for r in self.db.all_packages() if r.status == "installed")
        json_names = sorted(info.name for info in self.reader.scan())
        brew_names = self.cli.list_packages()  # None if `brew` isn't on PATH

        print(f"database:        {db_names}")
        print(f"cellar jsons:    {json_names}")
        print(f"brew list (cli): {brew_names if brew_names is not None else 'unavailable'}")

        all_names = set(db_names) | set(json_names) | set(brew_names or [])
        mismatches = []
        for name in sorted(all_names):
            in_db, in_json = name in db_names, name in json_names
            in_brew = None if brew_names is None else name in brew_names
            agree = (in_db == in_json) if in_brew is None else (in_db == in_json == in_brew)
            if not agree:
                mismatches.append((name, in_db, in_json, in_brew))

        if mismatches:
            print("mismatches (name, in_db, in_json, in_brew):")
            for m in mismatches:
                print(f"  {m}")
        else:
            print("all available sources agree")
        return 0
