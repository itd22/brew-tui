import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


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
