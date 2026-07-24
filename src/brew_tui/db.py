import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, Column, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base, Session

from .keg import Cellar

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


def dedupe_infos_by_name(infos: list[InstalledPackageInfo]) -> list[InstalledPackageInfo]:
    """Collapses scan results to one entry per formula name (last one wins).

    A formula can (briefly) have more than one version directory in the real
    Cellar — e.g. right after an upgrade, before `brew cleanup` removes the old
    keg — so RealCellarReader.scan() can return two InstalledPackageInfo with the
    same `name`. Any caller that keys off `name` (sync_from_cellar's DB upsert,
    the TUI's package table rows, ...) needs this first, or it'll fail on the
    duplicate: sync_from_cellar would try to INSERT the same primary key twice
    (sqlite IntegrityError), and the TUI's DataTable would try to add_row() the
    same row key twice (Textual DuplicateKey).
    """
    by_name: dict[str, InstalledPackageInfo] = {}
    for info in infos:
        by_name[info.name] = info
    return list(by_name.values())




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
        infos = dedupe_infos_by_name(infos)
        current_names = {info.name for info in infos}
        added, updated, removed = [], [], []

        with Session(self.engine) as session:
            existing = {r.name: r for r in session.query(PackageRecord).all()}

            for info in infos:
                record = existing.get(info.name)
                if record is None:
                    record = PackageRecord(name=info.name, first_seen_at=now)
                    session.add(record)
                    existing[info.name] = record
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
