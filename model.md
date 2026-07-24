# Homebrew Domain Model — v0.0.1 (adds `Status` + `BrewTUI`)

Flow for `brew install meld`: **CLI parser → Tap → Formulary → Formula → FormulaInstaller → Resource/SoftwareSpec (download) → Keg/Cellar → Tab (receipt) → link**.

New in this version:

- **`Status`** — reads Homebrew's real per-formula lock files (`$(brew --prefix)/var/homebrew/locks/<name>.formula.lock`), reports whether a lock is held, and decides whether a held lock is **stale** (owning PID is dead, or the lock has aged past a threshold with no PID recorded).
- **`BrewTUI`** — the `brew-tui` entry point. Before running `install`/`uninstall`, it asks `Status` whether that formula is currently mid-install; it refuses to proceed on a live lock, auto-clears a stale one, and only then delegates to `BrewCLIRunner`/`RealCellarReader`/`BrewDB` the same way `RealInstallCommand` does.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
import json
import os
import subprocess
import sys

from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime
from sqlalchemy.orm import declarative_base, Session


class PackageState(Enum):
    NOT_INSTALLED = auto()
    INSTALLED = auto()
    OUTDATED = auto()
    PINNED = auto()
    BROKEN = auto()
    KEG_ONLY = auto()


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


# --- Formulary: Library/Homebrew/formulary.rb (factory/loader) ---

class Formulary(ABC):
    """Loads/resolves a formula name to a Formula, via a Tap or the API cache."""

    @staticmethod
    @abstractmethod
    def factory(name: str, force_bottle: bool = False) -> "Formula":
        ...


# --- Dependency resolution: Library/Homebrew/dependency*.rb ---

@dataclass
class Dependency:
    name: str
    tags: list[str] = field(default_factory=list)  # e.g. ":build", ":optional"

    def to_formula(self) -> "Formula":
        ...


class DependencyCollector(ABC):
    """Builds a formula's declared Dependency list from its DSL body."""

    @abstractmethod
    def add(self, spec) -> Dependency:
        ...


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


# --- Formula: Library/Homebrew/formula.rb (abstract base for every *.rb formula file) ---

@dataclass
class PkgVersion:
    version: str
    revision: int = 0


class Formula(ABC):
    """Abstract base every generated Formula subclass (e.g. `Meld`) inherits."""

    name: str
    tap: Tap
    stable: SoftwareSpec
    pkg_version: PkgVersion
    license: str | None = None
    homepage: str = ""

    @property
    @abstractmethod
    def prefix(self) -> Path:
        ...

    @abstractmethod
    def install(self) -> None:
        """The formula-authored build/install recipe (e.g. Meld#install)."""
        ...

    @abstractmethod
    def recursive_dependencies(self) -> list[Dependency]:
        ...


# --- Cellar / Keg: Library/Homebrew/keg.rb ---

@dataclass
class Cellar:
    path: Path

    def rack_for(self, name: str) -> Path:
        ...


class Keg(ABC):
    """A single installed version of a Formula living in the Cellar."""

    path: Path
    formula_name: str
    version: PkgVersion

    @abstractmethod
    def link(self, overwrite: bool = False) -> list[Path]:
        ...

    @abstractmethod
    def unlink(self) -> list[Path]:
        ...

    @abstractmethod
    def uninstall(self) -> None:
        ...


# --- Tab: Library/Homebrew/tab.rb (the install receipt, INSTALL_RECEIPT.json) ---

@dataclass
class Tab:
    used_options: list[str] = field(default_factory=list)
    installed_as_dependency: bool = False
    installed_on_request: bool = True
    poured_from_bottle: bool = False
    tap: str = "homebrew/core"
    time: int | None = None

    @staticmethod
    def for_keg(keg: Keg) -> "Tab":
        ...


# --- FormulaInstaller: Library/Homebrew/formula_installer.rb (orchestrator) ---

class FormulaInstaller(ABC):
    """Coordinates deps, fetch, pour/build, keg creation, Tab, and linking."""

    formula: Formula
    installed_as_dependency: bool = False
    installed_on_request: bool = False
    ignore_deps: bool = False
    force_bottle: bool = False

    @abstractmethod
    def fetch(self) -> None:
        ...

    @abstractmethod
    def install(self) -> None:
        ...

    @abstractmethod
    def finish(self) -> None:
        """Writes the Tab and links the Keg."""
        ...


# --- User-facing report ---

@dataclass
class OperationResult:
    command: str
    package_name: str
    success: bool
    state_before: PackageState
    state_after: PackageState
    message: str = ""


# --- Install policy (bottle-only vs allow-compile) ---

class InstallPolicy(Enum):
    AUTO = auto()               # default: prefer bottle, fall back to compiling
    FORCE_BOTTLE = auto()       # --force-bottle: bottle required, fail otherwise
    BUILD_FROM_SOURCE = auto()  # --build-from-source: always compile, ignore bottle


class NoBottleError(Exception):
    def __init__(self, formula_name: str, needs_compile: list[str]) -> None:
        self.formula_name = formula_name
        self.needs_compile = needs_compile
        super().__init__(
            f"{formula_name}: no bottle available for: {', '.join(needs_compile)}. "
            f"Try `brew install --build-from-source {formula_name}`."
        )


class BottleAvailabilityChecker:
    """Concrete: mirrors the bottle-check logic added in brew PR #10788."""

    def __init__(self, current_platform: str) -> None:
        self.current_platform = current_platform

    def has_bottle_for_current_platform(self, formula: Formula) -> bool:
        bottle = formula.stable.bottle
        if bottle is None:
            return False
        return self.current_platform in bottle.sha256_by_platform

    def find_unbottled(self, formula: Formula) -> list[str]:
        """Walks formula + recursive_dependencies, returns names lacking a bottle."""
        unbottled: list[str] = []
        if not self.has_bottle_for_current_platform(formula):
            unbottled.append(formula.name)
        for dep in formula.recursive_dependencies():
            dep_formula = dep.to_formula()
            if not self.has_bottle_for_current_platform(dep_formula):
                unbottled.append(dep_formula.name)
        return unbottled


class PolicyEnforcedInstaller:
    """Concrete: wraps FormulaInstaller, applying InstallPolicy before fetch/install."""

    def __init__(self, installer: FormulaInstaller, checker: BottleAvailabilityChecker) -> None:
        self.installer = installer
        self.checker = checker

    def install(self, formula: Formula, policy: InstallPolicy) -> None:
        if policy is InstallPolicy.FORCE_BOTTLE:
            unbottled = self.checker.find_unbottled(formula)
            if unbottled:
                raise NoBottleError(formula.name, unbottled)
            self._pour_bottle(formula)

        elif policy is InstallPolicy.BUILD_FROM_SOURCE:
            self._compile_from_source(formula)

        else:  # AUTO
            if self.checker.has_bottle_for_current_platform(formula):
                self._pour_bottle(formula)
            else:
                self._compile_from_source(formula)

    def _pour_bottle(self, formula: Formula) -> None:
        self.installer.formula = formula
        self.installer.force_bottle = True
        self.installer.fetch()
        self.installer.install()
        self.installer.finish()

    def _compile_from_source(self, formula: Formula) -> None:
        self.installer.formula = formula
        self.installer.force_bottle = False
        self.installer.fetch()
        self.installer.install()   # runs formula.install() build recipe
        self.installer.finish()


def make_formula_installer(formula: Formula) -> FormulaInstaller:
    """Factory producing a concrete FormulaInstaller for `formula` (impl-specific)."""
    ...


class InstallCommand(Command):
    """`brew install [--force-bottle | --build-from-source] <name>`."""

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
    """`brew list` with no arguments: prints installed formula names from the Cellar."""

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


# --- store-db: persist installed package info in SQLite via SQLAlchemy ---

DbBase = declarative_base()


class PackageRecord(DbBase):
    """SQLAlchemy model: persistent history, survives real removal from the Cellar."""

    __tablename__ = "packages"

    name = Column(String, primary_key=True)
    version = Column(String, nullable=False)
    tap = Column(String, default="homebrew/core")
    installed_as_dependency = Column(Boolean, default=False)
    installed_on_request = Column(Boolean, default=True)
    method = Column(String, default="bottle")     # "bottle" | "compilation" | None
    status = Column(String, default="installed")  # "installed" | "removed" | "error"
    last_error = Column(String, nullable=True)
    first_seen_at = Column(DateTime)
    updated_at = Column(DateTime)


@dataclass
class InstalledPackageInfo:
    """Parsed from a real INSTALL_RECEIPT.json (Homebrew's actual on-disk schema)."""
    name: str
    version: str
    tap: str = "homebrew/core"
    poured_from_bottle: bool = False
    built_as_bottle: bool = False
    installed_as_dependency: bool = False
    installed_on_request: bool = True
    used_options: list[str] = field(default_factory=list)

    @property
    def method(self) -> str:
        return "bottle" if self.poured_from_bottle else "compilation"


class RealCellarReader:
    """Reads actual Homebrew/Linuxbrew INSTALL_RECEIPT.json files from the Cellar."""

    def __init__(self, cellar: Cellar) -> None:
        self.cellar = cellar

    def scan(self) -> list[InstalledPackageInfo]:
        infos: list[InstalledPackageInfo] = []
        if not self.cellar.path.exists():
            return infos
        for formula_dir in sorted(self.cellar.path.iterdir()):
            if not formula_dir.is_dir():
                continue
            for version_dir in sorted(formula_dir.iterdir()):
                receipt = version_dir / "INSTALL_RECEIPT.json"
                if not receipt.is_file():
                    continue
                try:
                    data = json.loads(receipt.read_text())
                except (json.JSONDecodeError, OSError):
                    continue
                source = data.get("source", {}) or {}
                infos.append(InstalledPackageInfo(
                    name=formula_dir.name,
                    version=version_dir.name,
                    tap=source.get("tap", "homebrew/core"),
                    poured_from_bottle=bool(data.get("poured_from_bottle")),
                    built_as_bottle=bool(data.get("built_as_bottle")),
                    installed_as_dependency=bool(data.get("installed_as_dependency")),
                    installed_on_request=data.get("installed_on_request") is not False,
                    used_options=data.get("used_options", []) or [],
                ))
        return infos

    def find(self, name: str) -> InstalledPackageInfo | None:
        for info in self.scan():
            if info.name == name:
                return info
        return None


class BrewDB:
    """Owns the sqlite engine/schema; brew checks `exists()` before creating it."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")

    def exists(self) -> bool:
        return self.db_path.exists()

    def create_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        DbBase.metadata.create_all(self.engine)

    def sync_from_cellar(self, infos: list[InstalledPackageInfo]) -> tuple[list[str], list[str], list[str]]:
        """Reconciles the DB with real Cellar state. Removed packages KEEP their row
        (status='removed'); nothing is ever deleted from the table."""
        now = datetime.now(timezone.utc)
        current_names = {info.name for info in infos}
        added, updated, removed = [], [], []

        with Session(self.engine) as session:
            existing = {r.name: r for r in session.query(PackageRecord).all()}

            for info in infos:
                record = existing.get(info.name)
                if record is None:
                    record = PackageRecord(name=info.name, first_seen_at=now)
                    session.add(record)
                    added.append(info.name)
                elif record.status != "installed" or record.version != info.version:
                    updated.append(info.name)
                record.version = info.version
                record.tap = info.tap
                record.installed_as_dependency = info.installed_as_dependency
                record.installed_on_request = info.installed_on_request
                record.method = info.method
                record.status = "installed"
                record.last_error = None
                record.updated_at = now

            for name, record in existing.items():
                if name not in current_names and record.status == "installed":
                    record.status = "removed"
                    record.updated_at = now
                    removed.append(name)

            session.commit()
        return added, updated, removed

    def mark_error(self, name: str, message: str) -> None:
        now = datetime.now(timezone.utc)
        with Session(self.engine) as session:
            record = session.get(PackageRecord, name)
            if record is None:
                record = PackageRecord(name=name, version="unknown", status="error",
                                        method=None, first_seen_at=now)
                session.add(record)
            record.status = "error"
            record.last_error = message
            record.updated_at = now
            session.commit()

    def all_packages(self) -> list[PackageRecord]:
        with Session(self.engine) as session:
            return session.query(PackageRecord).order_by(PackageRecord.name).all()


# --- Status: Library/Homebrew/lock_file.rb equivalent — reads real brew lock files ---

@dataclass
class LockInfo:
    """Snapshot of a single formula's real lock file, if any."""
    formula_name: str
    path: Path
    exists: bool
    pid: int | None = None
    locked_at: datetime | None = None


class Status:
    """Reads Homebrew's actual per-formula lock files from
    `$(brew --prefix)/var/homebrew/locks/<name>.formula.lock` (the same directory
    `Homebrew::LockFile` writes to during a real install/uninstall) and decides
    whether a held lock is still live or stale.

    Staleness rule:
      - if the lock file contains a PID, the lock is stale iff that process is dead
      - if no PID is recorded, fall back to an age threshold (mtime vs. now)
    """

    STALE_AGE_SECONDS = 300  # 5 minutes, used only when no PID is present

    def __init__(self, locks_dir: Path | None = None) -> None:
        self.locks_dir = locks_dir or self._default_locks_dir()

    @staticmethod
    def _default_locks_dir() -> Path:
        env = os.environ.get("HOMEBREW_LOCKS")
        if env:
            return Path(env)
        for candidate in (
            Path("/home/linuxbrew/.linuxbrew/var/homebrew/locks"),
            Path("/opt/homebrew/var/homebrew/locks"),
            Path("/usr/local/var/homebrew/locks"),
        ):
            if candidate.exists():
                return candidate
        return Path("/home/linuxbrew/.linuxbrew/var/homebrew/locks")

    def lock_path_for(self, formula_name: str) -> Path:
        return self.locks_dir / f"{formula_name}.formula.lock"

    def check(self, formula_name: str) -> LockInfo:
        """Reads the real lock file for `formula_name`, if present."""
        path = self.lock_path_for(formula_name)
        if not path.is_file():
            return LockInfo(formula_name=formula_name, path=path, exists=False)
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return LockInfo(formula_name=formula_name, path=path, exists=False)
        return LockInfo(
            formula_name=formula_name,
            path=path,
            exists=True,
            pid=self._read_pid(path),
            locked_at=datetime.fromtimestamp(mtime, tz=timezone.utc),
        )

    def _read_pid(self, path: Path) -> int | None:
        try:
            content = path.read_text().strip()
        except OSError:
            return None
        return int(content) if content.isdigit() else None

    def _pid_is_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # process exists, just owned by someone else
        return True

    def is_stale(self, lock: LockInfo) -> bool:
        if not lock.exists:
            return False
        if lock.pid is not None:
            return not self._pid_is_alive(lock.pid)
        if lock.locked_at is None:
            return False
        age = (datetime.now(timezone.utc) - lock.locked_at).total_seconds()
        return age > self.STALE_AGE_SECONDS

    def is_installing(self, formula_name: str) -> bool:
        """True iff a real, currently-live lock is held for `formula_name`."""
        lock = self.check(formula_name)
        return lock.exists and not self.is_stale(lock)

    def clear_stale(self, formula_name: str) -> bool:
        """Removes the lock file iff it exists and is stale. Returns True if removed."""
        lock = self.check(formula_name)
        if lock.exists and self.is_stale(lock):
            try:
                lock.path.unlink()
                return True
            except OSError:
                return False
        return False


class StoreDbCommand(Command):
    """`BrewE2E store-db`: creates the DB if missing, syncs it from real INSTALL_RECEIPT.json files."""

    name = "store-db"

    def __init__(self, reader: RealCellarReader, db: BrewDB) -> None:
        self.reader = reader
        self.db = db

    def run(self, args: ParsedArgs) -> int:
        if not self.db.exists():
            print(f"Creating database at {self.db.db_path}")
        self.db.create_schema()
        added, updated, removed = self.db.sync_from_cellar(self.reader.scan())
        print(f"added={added} updated={updated} removed={removed}")
        return 0


class RealListCommand(Command):
    """`BrewE2E list`: reads real INSTALL_RECEIPT.json files, prints them, and syncs the DB
    (adds new packages, updates changed ones, marks vanished ones 'removed' but keeps the row)."""

    name = "list"

    def __init__(self, reader: RealCellarReader, db: BrewDB) -> None:
        self.reader = reader
        self.db = db

    def run(self, args: ParsedArgs) -> int:
        infos = self.reader.scan()
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


class RealInstallCommand(Command):
    """`BrewE2E install <name>`: checks the DB, then real Cellar jsons, then — only if
    genuinely not installed — calls the real `brew install <name>` executable."""

    name = "install"

    def __init__(self, reader: RealCellarReader, db: BrewDB, cli: "BrewCLIRunner",
                 on_brew_output=None) -> None:
        self.reader = reader
        self.db = db
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


class BrewCLIRunner:
    """Runs the real `brew` executable, if one is on PATH."""

    def list_packages(self) -> list[str] | None:
        try:
            result = subprocess.run(
                ["brew", "list", "--formula"],
                capture_output=True, text=True, timeout=30,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            return None
        if result.returncode != 0:
            return None
        return sorted(line.strip() for line in result.stdout.splitlines() if line.strip())

    def install(self, name: str, on_line=None) -> str | None:
        """Runs `brew install <name>` for real, streaming each output line to on_line."""
        try:
            proc = subprocess.Popen(
                ["brew", "install", name],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
            )
        except (FileNotFoundError, OSError):
            return None
        lines: list[str] = []
        for raw_line in proc.stdout:
            line = raw_line.rstrip("\n")
            lines.append(line)
            if on_line is not None:
                on_line(line)
        proc.wait()
        return "\n".join(lines)

    def uninstall(self, name: str, on_line=None) -> str | None:
        """Runs `brew uninstall <name>` for real, streaming each output line to on_line."""
        try:
            proc = subprocess.Popen(
                ["brew", "uninstall", name],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
            )
        except (FileNotFoundError, OSError):
            return None
        lines: list[str] = []
        for raw_line in proc.stdout:
            line = raw_line.rstrip("\n")
            lines.append(line)
            if on_line is not None:
                on_line(line)
        proc.wait()
        return "\n".join(lines)


class ListCompareCommand(Command):
    """`BrewE2E list_compare`: compares DB vs real INSTALL_RECEIPT.json vs actual `brew list`."""

    name = "list_compare"

    def __init__(self, reader: RealCellarReader, db: BrewDB, cli: BrewCLIRunner) -> None:
        self.reader = reader
        self.db = db
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


class BrewE2E:
    """Real entry point, backed by the actual Homebrew/Linuxbrew Cellar on disk."""

    def __init__(self, cellar_path: Path | None = None, db_path: Path | None = None) -> None:
        self.cellar = Cellar(path=cellar_path or self._default_cellar_path())
        self.reader = RealCellarReader(self.cellar)
        self.db = BrewDB(db_path or self._default_db_path())
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
    def _default_db_path() -> Path:
        env = os.environ.get("HOMEBREW_DB_PATH")
        return Path(env) if env else Path.home() / ".brew_e2e" / "brew.db"

    @staticmethod
    def _default_cellar_path() -> Path:
        env = os.environ.get("HOMEBREW_CELLAR")
        if env:
            return Path(env)
        for candidate in (
            Path("/home/linuxbrew/.linuxbrew/Cellar"),
            Path("/opt/homebrew/Cellar"),
            Path("/usr/local/Cellar"),
        ):
            if candidate.exists():
                return candidate
        return Path("/home/linuxbrew/.linuxbrew/Cellar")

    def run(self, argv: list[str]) -> int:
        if not argv:
            print("usage: BrewE2E <command> [args...]")
            return 1
        command_name, *rest = argv
        command = self.commands.get(command_name)
        if command is None:
            print(f"Unknown command: {command_name}")
            return 1
        return command.run(ParsedArgs(command_name=command_name, named_args=rest))


# --- BrewTUI: `brew-tui` entry point — interactive front-end guarded by Status ---

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
            self._print("usage: brew-tui <install|uninstall> <name>")
            return 1
        command_name, *rest = argv
        if command_name == "install" and rest:
            return self.install(rest[0])
        if command_name == "uninstall" and rest:
            return self.uninstall(rest[0])
        self._print(f"Unknown command: {' '.join(argv)}")
        return 1


if __name__ == "__main__":
    sys.exit(BrewTUI.default().run(sys.argv[1:]))


class BrewModel:
    """Facade: `brew install`, `brew remove`, `brew update`.

    install(name):  Formulary.factory -> FormulaInstaller(formula).fetch()/install()/finish()
    remove(name):   Formulary.factory -> Keg.uninstall()
    update():       Tap.each -> git pull, refreshes Formulary's cache
    """

    def __init__(self, cellar: Cellar, taps: list[Tap]) -> None:
        self.cellar = cellar
        self.taps = taps

    def install(self, name: str) -> OperationResult:
        ...

    def remove(self, name: str) -> OperationResult:
        ...

    def update(self) -> OperationResult:
        ...
```
