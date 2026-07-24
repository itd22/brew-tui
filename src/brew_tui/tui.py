"""`brew-tui`: the interactive terminal front-end, built on Textual
(https://textual.textualize.io/).

Two things live in this module:

- `BrewTUI` — the plain business-logic controller. Before running install/uninstall
  it always calls `Status.is_installing(name)` first:
    - a real, live lock  -> refuse and tell the user an install is already in progress
    - a stale lock       -> clear it automatically, then proceed
    - no lock            -> proceed straight away
  Delegates the actual work to the same collaborators `BrewE2E` uses
  (`RealCellarReader`, `BrewDB`, `BrewCLIRunner`), so the Textual app and the
  scriptable `BrewE2E` CLI stay consistent with each other. It also still supports
  the old one-shot, scripted invocation (`BrewTUI().run(["install", "name"])`), so
  existing automation (docker/CI, `run-brewe2e.sh`, etc.) keeps working unchanged.

- `BrewTUIApp` — the full-screen Textual application: a table of installed
  formulae, a formula-name input with Install/Uninstall/Refresh buttons, and a live
  log pane that streams real `brew` output while the operation runs in a background
  worker thread (so the UI never blocks on a slow install).

Running `brew-tui` with no arguments launches `BrewTUIApp`; running it with
arguments (e.g. `brew-tui install ripgrep`) keeps the old non-interactive,
scriptable behaviour.
"""
import sys
from functools import partial

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, RichLog, Static

from .db import BrewDB, RealCellarReader
from .cli_runner import BrewCLIRunner
from .status import Status
from .keg import Cellar
from .e2e import BrewE2E


class BrewTUI:
    """`brew-tui`'s business logic, independent of any particular front-end
    (the Textual app and the scripted CLI mode both drive this class)."""

    def __init__(self, reader: RealCellarReader, db: BrewDB, cli: BrewCLIRunner,
                 status: Status, on_output=None, quiet: bool = False) -> None:
        self.reader = reader
        self.db = db
        self.cli = cli
        self.status = status
        self.on_output = on_output  # optional sink for streamed `brew` output (TUI pane)
        self.quiet = quiet          # when True, suppress print() (Textual owns the screen)

    def _print(self, line: str) -> None:
        if not self.quiet:
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
    def default(cls, **kwargs) -> "BrewTUI":
        """Wires up real collaborators the same way `BrewE2E()` does."""
        cellar = Cellar(path=BrewE2E._default_cellar_path())
        reader = RealCellarReader(cellar)
        db = BrewDB(BrewE2E._default_db_path())
        if not db.exists():
            db.create_schema()
        return cls(reader=reader, db=db, cli=BrewCLIRunner(), status=Status(), **kwargs)

    def run(self, argv: list[str]) -> int:
        """Old one-shot, scripted entry point: `brew-tui <install|uninstall|list> [name]`.
        Kept for automation (docker/CI) that shells out to `brew-tui` non-interactively."""
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


class BrewTUIApp(App):
    """The full-screen, interactive `brew-tui` experience."""

    TITLE = "brew-tui"
    SUB_TITLE = "interactive front-end over a real Homebrew Cellar"

    CSS = """
    #controls {
        height: 3;
        padding: 0 1;
    }
    #formula-input {
        width: 1fr;
        margin-right: 1;
    }
    #package-table {
        height: 1fr;
        border: solid $accent;
    }
    #output-label {
        height: 1;
        padding-left: 1;
        color: $text-muted;
    }
    #output-log {
        height: 12;
        border: solid $accent;
    }
    #busy-indicator {
        width: auto;
        padding: 0 1;
        color: $text-muted;
    }
    #busy-indicator.-busy {
        color: $warning;
        text-style: bold;
    }
    """

    # busy-indicator poll interval (seconds) while a real lock is confirmed held;
    # configurable per instance, clamped to this range
    BUSY_POLL_INTERVAL_MIN = 1.0
    BUSY_POLL_INTERVAL_MAX = 5.0
    BUSY_POLL_INTERVAL_DEFAULT = 2.0

    BINDINGS = [
        Binding("i", "focus_install", "Install"),
        Binding("u", "focus_uninstall", "Uninstall"),
        Binding("r", "refresh_packages", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, controller: "BrewTUI | None" = None,
                 busy_poll_interval: float = BUSY_POLL_INTERVAL_DEFAULT) -> None:
        super().__init__()
        self.controller = controller or BrewTUI.default(quiet=True)
        self.controller.quiet = True
        self.controller.on_output = self._threadsafe_log
        self.busy_poll_interval = self._clamp_poll_interval(busy_poll_interval)
        self._busy_timer = None  # Timer | None — only ever runs while a lock is held

    @classmethod
    def _clamp_poll_interval(cls, seconds: float) -> float:
        return min(max(seconds, cls.BUSY_POLL_INTERVAL_MIN), cls.BUSY_POLL_INTERVAL_MAX)

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="root"):
            with Horizontal(id="controls"):
                yield Input(placeholder="formula name (e.g. ripgrep)", id="formula-input")
                yield Button("Install", id="install-btn", variant="success")
                yield Button("Uninstall", id="uninstall-btn", variant="error")
                yield Button("Refresh", id="refresh-btn", variant="primary")
                yield Static("● idle", id="busy-indicator")
            yield DataTable(id="package-table")
            yield Static("Output", id="output-label")
            yield RichLog(id="output-log", wrap=True, markup=True, max_lines=2000)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#package-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Name", "Version", "Method", "Tap", "Status")
        self.action_refresh_packages()
        # No continuous polling here: the busy indicator only checks the real lock
        # file when the user starts typing a formula name, and self-schedules
        # polling only for as long as that lock is actually held (see below).

    # --- package table ---

    def _synced_packages(self):
        if not self.controller.db.exists():
            self.controller.db.create_schema()
        infos = self.controller.reader.scan()
        self.controller.db.sync_from_cellar(infos)
        return infos

    def action_refresh_packages(self) -> None:
        table = self.query_one("#package-table", DataTable)
        table.clear()
        for info in self._synced_packages():
            status_text = "busy" if self.controller.status.is_installing(info.name) else "installed"
            table.add_row(info.name, info.version, info.method, info.tap, status_text, key=info.name)
        self._log(f"refreshed: {table.row_count} package(s) in the Cellar")
        # A refresh isn't "starting to type a command", so just reflect the
        # currently-typed name (if any) once, without starting a poll loop.
        typed = self.query_one("#formula-input", Input).value.strip()
        self._set_busy_indicator(self._check_busy(typed), typed)

    # --- busy indicator: reflects the real Homebrew per-formula lock file ---
    #
    # Design: no background polling by default. A real lock-file check only
    # happens (a) when the user starts typing a formula name, and (b) right
    # before a command is actually sent to `brew`. If that check finds a live
    # lock, a short-lived timer keeps re-checking (at `busy_poll_interval`,
    # clamped 1s-5s) until the lock clears, then stops itself. If the check
    # finds nothing locked, no polling happens at all.

    def _set_busy_indicator(self, busy: bool, name: str = "") -> None:
        indicator = self.query_one("#busy-indicator", Static)
        if busy:
            indicator.update(f"● busy ({name})" if name else "● busy")
            indicator.add_class("-busy")
        else:
            indicator.update("● idle")
            indicator.remove_class("-busy")

    def _start_busy_polling(self) -> None:
        if self._busy_timer is None:
            self._busy_timer = self.set_interval(self.busy_poll_interval, self._poll_busy)

    def _stop_busy_polling(self) -> None:
        if self._busy_timer is not None:
            self._busy_timer.stop()
            self._busy_timer = None

    def _check_busy(self, name: str) -> bool:
        """One real lock-file check for `name`. Never schedules polling itself."""
        return bool(name) and self.controller.status.is_installing(name)

    def _refresh_busy_indicator(self, name: str) -> bool:
        """Checks `name` once, updates the indicator, and starts/stops the poll
        timer to match. Returns whether `name` is currently busy."""
        busy = self._check_busy(name)
        self._set_busy_indicator(busy, name)
        if busy:
            self._start_busy_polling()
        else:
            self._stop_busy_polling()
        return busy

    def _poll_busy(self) -> None:
        """Only fires while `_busy_timer` is running, i.e. a lock was last seen
        held. Stops itself the moment the lock clears."""
        name = self.query_one("#formula-input", Input).value.strip()
        if not self._check_busy(name):
            self._set_busy_indicator(False)
            self._stop_busy_polling()
            return
        self._set_busy_indicator(True, name)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Kicks off the busy check as soon as the user starts typing a formula
        name; clears/stops polling once the field is emptied again."""
        if event.input.id != "formula-input":
            return
        name = event.value.strip()
        if not name:
            self._stop_busy_polling()
            self._set_busy_indicator(False)
            return
        self._refresh_busy_indicator(name)

    def action_focus_install(self) -> None:
        self.query_one("#formula-input", Input).focus()

    action_focus_uninstall = action_focus_install

    # --- logging ---

    def _log(self, line: str) -> None:
        self.query_one("#output-log", RichLog).write(line)

    def _threadsafe_log(self, line: str) -> None:
        # `install`/`uninstall` run in a worker thread; hop back onto the Textual
        # event loop before touching any widget.
        try:
            self.call_from_thread(self._log, line)
        except RuntimeError:
            pass  # app already stopped

    # --- install / uninstall ---

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh-btn":
            self.action_refresh_packages()
            return

        name = self.query_one("#formula-input", Input).value.strip()
        if not name:
            self._log("[bold red]enter a formula name first[/bold red]")
            return

        # Check-before-send: one last real lock-file check right as the command
        # is about to go out, so the indicator (and any brief poll it kicks off)
        # is accurate even if nothing was typed slowly enough to trigger it above.
        if self._refresh_busy_indicator(name):
            self._log(f"[bold yellow]{name}: a lock is currently held — brew-tui will wait for it to clear[/bold yellow]")

        if event.button.id == "install-btn":
            self._log(f"--- install {name} ---")
            self.run_worker(partial(self._run_operation, "install", name), thread=True)
        elif event.button.id == "uninstall-btn":
            self._log(f"--- uninstall {name} ---")
            self.run_worker(partial(self._run_operation, "uninstall", name), thread=True)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.query_one("#install-btn", Button).press()

    def _run_operation(self, verb: str, name: str) -> None:
        """Runs on a worker thread; only touches widgets via call_from_thread."""
        code = self.controller.install(name) if verb == "install" else self.controller.uninstall(name)
        self.call_from_thread(self._on_operation_done, verb, name, code)

    def _on_operation_done(self, verb: str, name: str, code: int) -> None:
        outcome = "ok" if code == 0 else "FAILED"
        self._log(f"--- {verb} {name}: {outcome} (exit={code}) ---")
        self.action_refresh_packages()


def main() -> int:
    argv = sys.argv[1:]
    if argv:
        # scripted mode, unchanged: `brew-tui install <name>` / `uninstall <name>` / `list`
        return BrewTUI.default().run(argv)
    BrewTUIApp().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
