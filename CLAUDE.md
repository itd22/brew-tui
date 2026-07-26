# Project: brew-tui

## Stack
- Python 3.x
- Package manager: pip / uv (confirm which)
- Test: `pytest`
- Lint/format: `ruff check .`
- Run locally: `<confirm entry point — e.g. python -m brew_tui, or a console_scripts entry point>`

## Layout
- `src/` (or `brew_tui/`, confirm which — .gitignore doesn't disambiguate) — application code
- `<fill in other top-level dirs and what they hold, one line each>`

## Working conventions
- Don't run a full workspace scan for small edits — go straight to the
  file(s) named in the request; only widen search if something's missing.
- Match existing formatting/lint config; run `ruff` before proposing a diff.
- Flag new dependencies before adding them.
- No test scaffolding unless explicitly asked (matches the Copilot prompt
  files in `.github/prompts/` — keep both tools' defaults consistent).

## Out of bounds unless explicitly asked
- `/dist`, `/build`, `/.venv`, `__pycache__/`, lock files — build
  artifacts, not source; regenerate via the package manager.
- Anything under `docs/archive/` (if present) — historical, not current
  behavior.

## Using this file on claude.ai web
Claude.ai's web "Add from GitHub" feature is a manual file-browser add per
chat/project — there is no first-party connector that auto-loads this file
the way Claude Code does. To get the same effect on the web:
1. Click "+" → Add from GitHub → select this repo.
2. Add `CLAUDE.md` itself plus only the specific files/folders relevant to
   the task — not the whole repo. Anthropic's own guidance is to stay
   within token limits by being selective.
3. Re-sync ("Sync now") before a new session if the repo has moved on;
   stale synced content otherwise silently informs answers.

<!--
  This file is read automatically at the start of every Claude Code
  session in this repo — that's the real token saving there. On
  claude.ai web it only helps if you manually add it each time; it does
  not auto-load. Keep it factual and short either way — a bloated
  CLAUDE.md costs tokens every time it's loaded, automatically or not.
-->
