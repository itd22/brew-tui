https://claude.ai/chat/cbd83a61-f980-4e9b-920e-3eadb266923b
# AI tooling config for brew-tui — v0.2


## What changed from v0.1

1. **Fixed a real bug**: `.github/prompts/*.md` → `.github/prompts/*.prompt.md`.
   Copilot Chat only recognizes the `.prompt.md` extension as an invokable
   `/name` slash command (VS Code, Visual Studio, JetBrains — not Copilot
   CLI). The v0.1 files were inert; renaming is what actually makes
   `/add-feature`, `/refactor-python`, `/api-design`, `/explain-code` work.
2. Added minimal YAML frontmatter (`description:`) to each prompt file —
   required for it to show up properly in the chat's prompt picker.
3. Filled in the `<fill in>` placeholders in `copilot-instructions.md` and
   `CLAUDE.md` with Python specifics, inferred from your `.gitignore`
   (pytest, ruff, `.venv`). Confirm the exact entry point and package
   manager — I could not read the repo's actual source to verify these.
4. Added a section to `CLAUDE.md` on using it with claude.ai's web GitHub
   integration, since that's a materially different mechanism from
   Claude Code (see below).
5. `.vscode/settings.json` now also excludes `.ruff_cache`, `.pytest_cache`,
   `.mypy_cache` from search/file trees.

## The honest state of "optimization" for each surface

| Surface | What actually reduces tokens | What doesn't |
|---|---|---|
| Copilot Chat (VS Code/JetBrains) | `.gitignore`, `.vscode/settings.json` excludes, terse `copilot-instructions.md` | `.copilotignore` (non-functional), a verbose instructions file |
| Copilot prompt files | Reusing a `/name` command instead of retyping instructions each time | Prompt files with the wrong extension (silently do nothing) |
| Claude Code | `.gitignore` (real), `CLAUDE.md` (real, auto-loaded) | `.claudeignore` (advisory, enforcement gaps reported) |
| claude.ai web + GitHub | Manually selecting specific files/folders per chat, keeping `CLAUDE.md` short and re-adding it deliberately | Assuming any file auto-loads — nothing does on web |

No file in this repo makes claude.ai's web GitHub integration auto-load
context. That integration is manual-selection by design (confirmed via
Anthropic's own docs on it) — the closest to "optimization" there is
discipline about what you select, not a config file.
