# `brew-tui` — Command Flow Between Entities (v0.0.1)

## Entities involved

| Entity | Role |
|---|---|
| `BrewTUI` | Entry point for `brew-tui`. Parses argv, guards every install/uninstall through `Status` first. |
| `Status` | Reads the **real** Homebrew lock file for a formula and decides if it's live or stale. |
| `RealCellarReader` | Reads real `INSTALL_RECEIPT.json` files from the Cellar to see what's actually installed. |
| `BrewDB` | SQLite-backed history of packages (`installed` / `removed` / `error`), synced from the Cellar. |
| `BrewCLIRunner` | Shells out to the real `brew install` / `brew uninstall` executable and streams its output. |

## `brew-tui` (no args)

```
BrewTUI.run([])
  -> prints usage, returns 1
```

No other entity is touched — argv is empty, so `BrewTUI` exits before consulting `Status`, `BrewDB`, or the Cellar.

## `brew-tui install ripgrep`

```
1. BrewTUI.run(["install", "ripgrep"])
2. BrewTUI.install("ripgrep")
3. BrewTUI._guard("ripgrep")
     -> Status.check("ripgrep")
          reads $(brew --prefix)/var/homebrew/locks/ripgrep.formula.lock
     -> case: lock does not exist            -> guard passes, continue
     -> case: lock exists and is stale       -> Status.clear_stale("ripgrep") deletes it, continue
     -> case: lock exists and is live        -> abort, return 1 ("already in progress")
4. BrewDB.exists() / create_schema()          -- ensure the sqlite db is there
5. BrewDB.all_packages()                      -- is "ripgrep" already status="installed"?
     -> yes: print "already installed per DB", return 0
6. RealCellarReader.find("ripgrep")           -- double-check the real Cellar json
     -> found: print "already installed per real Cellar json",
               BrewDB.sync_from_cellar(...), return 0
7. BrewCLIRunner.install("ripgrep", on_line=self._print)
     -> runs the real `brew install ripgrep`, streaming stdout/stderr line by line
     -> on success: BrewDB.sync_from_cellar(RealCellarReader.scan()) updates/adds the row
     -> on failure (`brew` missing): BrewDB.mark_error("ripgrep", message), return 1
```

## `brew-tui uninstall ripgrep`

```
1. BrewTUI.run(["uninstall", "ripgrep"])
2. BrewTUI.uninstall("ripgrep")
3. BrewTUI._guard("ripgrep")                  -- identical Status check as install
     -> live lock -> abort, return 1
     -> stale lock -> Status.clear_stale("ripgrep"), continue
     -> no lock -> continue
4. BrewDB.exists() / create_schema()
5. RealCellarReader.find("ripgrep")
     -> not found: print "not installed, nothing to uninstall", return 0
6. BrewCLIRunner.uninstall("ripgrep", on_line=self._print)
     -> runs the real `brew uninstall ripgrep`, streaming output
     -> on success: BrewDB.sync_from_cellar(RealCellarReader.scan())
          "ripgrep" is no longer in the Cellar scan, so its row flips to status="removed"
          (the row itself is never deleted, per BrewDB.sync_from_cellar)
     -> on failure (`brew` missing): BrewDB.mark_error("ripgrep", message), return 1
```

## Why `Status` sits in front of both commands

Homebrew itself takes a real lock file per formula while it installs/uninstalls/upgrades
(`Library/Homebrew/lock_file.rb`, one file per formula under
`$(brew --prefix)/var/homebrew/locks/`). If a previous `brew-tui` run — or a plain
`brew install` run in another terminal — died without cleaning up, that lock file can be
left behind ("stale"). `Status` is the single place that:

1. Locates that lock file for a given formula name.
2. Reads an optional PID out of it and checks with `os.kill(pid, 0)` whether the owning
   process is still alive.
3. Falls back to a file-age threshold (`STALE_AGE_SECONDS`, default 300s) when no PID is
   recorded.
4. Exposes `is_installing()` (true only for a live lock) and `clear_stale()` (deletes a
   confirmed-stale lock).

`BrewTUI._guard()` is the only caller of `Status` — every `install`/`uninstall` path
passes through it before touching `BrewDB`, `RealCellarReader`, or `BrewCLIRunner`, so a
genuinely in-progress operation can never be raced by a second `brew-tui` invocation.
