# `brew-tui` — UML Flow Diagrams

Diagrams below are standard UML (sequence + class) expressed in Mermaid syntax.

> As of 0.0.17, `brew-tui` (no args) launches `BrewTUIApp`, a full-screen interactive
> front-end built on [Textual](https://textual.textualize.io/). `BrewTUIApp` is a thin
> widget layer (package table, formula input, Install/Uninstall/Refresh buttons, a
> live output log) that drives the `BrewTUI` class documented below — the business
> logic and its `Status`/`RealCellarReader`/`BrewDB`/`BrewCLIRunner` collaborators are
> unchanged. `BrewTUI().run(argv)` still works standalone for scripted/CI use
> (`brew-tui install <name>`, `uninstall <name>`, `list`).

## Class diagram — entities involved in install/uninstall

```mermaid
classDiagram
    class BrewTUI {
        -RealCellarReader reader
        -BrewDB db
        -BrewCLIRunner cli
        -Status status
        +install(name) int
        +uninstall(name) int
        +run(argv) int
        -_guard(name) bool
    }

    class Status {
        -Path locks_dir
        +STALE_AGE_SECONDS int
        +check(formula_name) LockInfo
        +is_stale(lock) bool
        +is_installing(formula_name) bool
        +clear_stale(formula_name) bool
    }

    class LockInfo {
        +str formula_name
        +Path path
        +bool exists
        +int pid
        +datetime locked_at
    }

    class RealCellarReader {
        -Cellar cellar
        +scan() List~InstalledPackageInfo~
        +find(name) InstalledPackageInfo
    }

    class BrewDB {
        -Path db_path
        +exists() bool
        +create_schema()
        +sync_from_cellar(infos) tuple
        +mark_error(name, message)
        +all_packages() List~PackageRecord~
    }

    class BrewCLIRunner {
        +install(name, on_line) str
        +uninstall(name, on_line) str
        +list_packages() List~str~
    }

    class InstalledPackageInfo {
        +str name
        +str version
        +bool poured_from_bottle
        +method() str
    }

    class PackageRecord {
        +str name
        +str version
        +str status
        +str last_error
    }

    BrewTUI --> Status : guards every call
    BrewTUI --> RealCellarReader : checks real Cellar
    BrewTUI --> BrewDB : reads/syncs history
    BrewTUI --> BrewCLIRunner : shells out to real brew
    Status --> LockInfo : produces
    RealCellarReader --> InstalledPackageInfo : produces
    BrewDB --> PackageRecord : persists
```

## Sequence diagram — `brew-tui` (no args)

```mermaid
sequenceDiagram
    actor User
    participant TUI as BrewTUI

    User->>TUI: run([])
    TUI-->>User: "usage: brew-tui <install|uninstall> <name>"
    Note over TUI: argv empty, Status/DB/Cellar/CLI never touched
```

## Sequence diagram — `brew-tui install ripgrep`

```mermaid
sequenceDiagram
    actor User
    participant TUI as BrewTUI
    participant ST as Status
    participant DB as BrewDB
    participant CR as RealCellarReader
    participant CLI as BrewCLIRunner
    participant Brew as brew (real executable)

    User->>TUI: run(["install", "ripgrep"])
    TUI->>TUI: install("ripgrep")

    Note over TUI,ST: Group G1 — Lock guard
    TUI->>ST: check("ripgrep")
    ST-->>TUI: LockInfo(exists=?, pid=?, locked_at=?)

    alt T1: lock live — exists=True and pid is a running process
        TUI-->>User: "already in progress (pid=...)"
        Note over TUI: return 1, stop
    else T2: lock stale — exists=True but pid is dead, or file older than STALE_AGE_SECONDS
        TUI->>ST: clear_stale("ripgrep")
        ST-->>TUI: True (lock file deleted)
    else T3: no lock — exists=False
        Note over TUI: continue
    end

    Note over TUI,DB: Group G2 — DB lookup
    TUI->>DB: exists() / create_schema()
    TUI->>DB: all_packages()
    DB-->>TUI: records

    alt T4: already installed per DB — record status == "installed"
        TUI-->>User: "already installed per DB"
    else T5: not in DB — no "installed" record for "ripgrep"
        Note over TUI,CR: Group G3 — Cellar fallback check
        TUI->>CR: find("ripgrep")
        CR-->>TUI: InstalledPackageInfo or None

        alt T6: found in real Cellar json — receipt exists on disk despite DB gap
            TUI->>DB: sync_from_cellar(scan())
            TUI-->>User: "already installed per real Cellar json"
        else T7: not installed anywhere — no DB record and no Cellar receipt
            Note over TUI,Brew: Group G4 — Real brew install execution
            TUI->>CLI: install("ripgrep", on_line=_print)
            CLI->>Brew: subprocess `brew install ripgrep`
            Brew-->>CLI: streamed stdout/stderr lines
            CLI-->>TUI: full output or None

            alt T8: brew executable missing — subprocess raised FileNotFoundError
                TUI->>DB: mark_error("ripgrep", message)
                TUI-->>User: error, return 1
            else T9: success — brew exited 0
                TUI->>DB: sync_from_cellar(scan())
                TUI-->>User: return 0
            end
        end
    end
```

## Sequence diagram — `brew-tui uninstall ripgrep`

```mermaid
sequenceDiagram
    actor User
    participant TUI as BrewTUI
    participant ST as Status
    participant DB as BrewDB
    participant CR as RealCellarReader
    participant CLI as BrewCLIRunner
    participant Brew as brew (real executable)

    User->>TUI: run(["uninstall", "ripgrep"])
    TUI->>TUI: uninstall("ripgrep")

    Note over TUI,ST: Group G1 — Lock guard
    TUI->>ST: check("ripgrep")
    ST-->>TUI: LockInfo(exists=?, pid=?, locked_at=?)

    alt lock exists and is live
        TUI-->>User: "already in progress (pid=...)"
        Note over TUI: return 1, stop
    else lock exists and is stale
        TUI->>ST: clear_stale("ripgrep")
        ST-->>TUI: True (lock file deleted)
    else no lock
        Note over TUI: continue
    end

    Note over TUI,CR: Group G2 — Cellar lookup
    TUI->>DB: exists() / create_schema()
    TUI->>CR: find("ripgrep")
    CR-->>TUI: InstalledPackageInfo or None

    alt not installed
        TUI-->>User: "not installed, nothing to uninstall"
        Note over TUI: return 0
    else installed
        Note over TUI,Brew: Group G3 — Real brew uninstall execution
        TUI->>CLI: uninstall("ripgrep", on_line=_print)
        CLI->>Brew: subprocess `brew uninstall ripgrep`
        Brew-->>CLI: streamed stdout/stderr lines
        CLI-->>TUI: full output or None

        alt brew executable missing
            TUI->>DB: mark_error("ripgrep", message)
            TUI-->>User: error, return 1
        else success
            TUI->>DB: sync_from_cellar(scan())
            Note over DB: "ripgrep" absent from scan -> status flips to "removed" (row kept, never deleted)
            TUI-->>User: return 0
        end
    end
```

## Why `Status` sits in front of both commands

Homebrew itself takes a real lock file per formula while it installs/uninstalls/upgrades
(`Library/Homebrew/lock_file.rb`, one file per formula under
`$(brew --prefix)/var/homebrew/locks/`). If a previous `brew-tui` run — or a plain
`brew install` run in another terminal — died without cleaning up, that lock file can be
left behind ("stale"). `Status` is the single place that:

1. Locates the lock file for a given formula name.
2. Reads an optional PID out of it and checks with `os.kill(pid, 0)` whether the owning
   process is still alive.
3. Falls back to a file-age threshold (`STALE_AGE_SECONDS`, default 300s) when no PID is
   recorded.
4. Exposes `is_installing()` (true only for a live lock) and `clear_stale()` (deletes a
   confirmed-stale lock).

`BrewTUI._guard()` is the only caller of `Status` — every `install`/`uninstall` path goes
through it before touching `BrewDB`, `RealCellarReader`, or `BrewCLIRunner`, so a genuinely
in-progress operation can never be raced by a second `brew-tui` invocation.
