# brew-tui — v0.0.1

Domain model + docs for `brew-tui`, an interactive front-end over Homebrew's real
Cellar/lock/`brew` executable, extending the base Homebrew entity model with:

- **`Status`** — checks the real per-formula Homebrew lock file and tells you whether
  it's live or stale.
- **`BrewTUI`** — the `brew-tui` entry point; uses `Status` to refuse or proceed with
  `install`/`uninstall` depending on whether an install is already in progress.

## Contents

- `model.md` — full domain model (Python, structure only) including `Status` and `BrewTUI`.
- `docs/FLOW.md` — step-by-step entity flow for `brew-tui`, `brew-tui install ripgrep`,
  and `brew-tui uninstall ripgrep`.

## Quick example

```
$ brew-tui install ripgrep
ripgrep: not installed — running real `brew install ripgrep`
...
$ brew-tui install ripgrep     # run again while the first is mid-flight
ripgrep: install/uninstall already in progress (lock held by pid=12345), aborting
$ brew-tui uninstall ripgrep
ripgrep: installed (version 14.1.0) — running real `brew uninstall ripgrep`
...
```
