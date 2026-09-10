# Azztec SaaS — Claude Code Workflow (git is the shared memory)

**File:** Azztec_SaaS_Claude_Code_Workflow_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-10 · **Author:** Adriaan
**Status:** Active from the first commit
**Verified:** Claude Code install/config facts checked against code.claude.com docs and current guides on 2026-09-10.

---

## 1. Why this changes the way we work

On Ignition the only way to ship was copy-paste into Designer, so every deliverable was a Download card. With the SaaS repo in
**git**, there is a second surface: **Claude Code runs inside the repo**, edits the real files, runs the tests, and commits.
The chat (this claude.ai Project) and Claude Code then share one memory — the repository — and every session, on either
surface, starts from the same state.

| Surface | Job | Reads | Writes |
|---------|-----|-------|--------|
| **claude.ai Project chat** (this) | think: research, specs, decisions, reviewing pasted output, knowledge docs, raw logs | project knowledge | Download cards (docs, specs, scripts, occasional files) |
| **Claude Code** (terminal / VS Code, inside `workmate-saas/`) | do: implement a signed-off slice, run `uv run pytest` / `pnpm test`, migrations, scaffolding, git commits | `CLAUDE.md`, `.claude/rules/*.md`, `docs/`, `.claude/skills/`, the code | the repo (in-place edits), commits, tags |

**Two laws that make the pair work**

1. Nothing gets built in Claude Code without a spec section + 🤙 in the chat (the chat is where decisions live).
2. Nothing decided in the chat is real until it is in the repo (`docs/` mirror + raw log committed) — Claude Code cannot see project knowledge.

## 2. Repo = single source of truth

```
workmate-saas/
├── CLAUDE.md                       # ← Azztec_SaaS_CLAUDE_md_v1_0_0.md: short, points at docs/ and rules
├── .claude/
│   ├── settings.json               # committed: permissions allow/deny, env, hooks (team baseline)
│   ├── settings.local.json         # NOT committed: personal overrides (auto-gitignored)
│   ├── rules/                      # path-scoped rules Claude Code loads automatically
│   │   ├── sql.md                  #   dialect rules for **/sql.py (COALESCE, PG-CONVERT, RTRIM…)
│   │   ├── tests.md                #   pair rule, rollback fixtures, no writes to RST
│   │   └── frontend.md             #   generated client is read-only, dates via lib/dates.ts, dnd-kit rules
│   ├── skills/                     # `uvx library-skills --claude` puts the official FastAPI (and SQLModel) skills here
│   └── agents/                     # optional later: reviewer subagent that checks the dialect gate
├── docs/                           # mirror of project knowledge — compiled docs + raw logs, committed
│   ├── Azztec_SaaS_*.md            #   this set
│   ├── raw/Azztec_SaaS_Raw_Log_*.md
│   └── reference/                  #   the Ignition planner sources, PG forward-compat, prompts doc
└── … backend/ web/
```

Facts (verified 2026-09-10): Claude Code reads `CLAUDE.md` every session; `settings.json` holds permissions/hooks/env; `settings.local.json` is for personal
overrides and stays out of git; `.claude/rules/*.md` are loaded automatically; `skills/<name>/SKILL.md` are invoked with `/name`; `.mcp.json` connects MCP servers (project scope). Docs: https://code.claude.com/docs/en/claude-directory

## 3. Install (Windows, once)

```powershell
irm https://claude.ai/install.ps1 | iex        # native installer — no Node.js needed, auto-updates
claude --version                                 # new terminal first
cd C:\dev\workmate-saas
claude                                           # first run: browser OAuth with the Claude subscription
```

`winget install Anthropic.ClaudeCode` also works but does not auto-update. The old `npm install -g @anthropic-ai/claude-code` path is deprecated.
Git for Windows (installed by the bootstrap script) gives Claude Code its Bash tool; without it, it falls back to PowerShell.
Optional: the Claude Code extension in VS Code (open the repo, sign in, same config files).

Then, inside the repo, once:

```powershell
cd backend; uvx library-skills --claude; cd ..          # official FastAPI skill → .claude/skills/, version-synced with the installed FastAPI
```

Do **not** run `/init` over the delivered `CLAUDE.md` — it explores the repo and writes a generic one. Keep ours.

## 4. The slice loop across both surfaces

```
chat:        spec section → OD answers → 🤙
claude code: claude → "Read CLAUDE.md, docs/Azztec_SaaS_Planner_Port_Spec_v1_0_0.md §S1. Plan first."   (plan mode: Shift+Tab)
             review the plan → approve → it edits, runs `uv run pytest`, `pnpm test`, `pnpm build`
             `git add -A && git commit -m "planner: S1 read-only range 1.0.0"` ; `git tag s1-range-1.0.0`
chat:        paste `git log -1 --stat` + the smoke output → 🤙 → next slice; close with a raw log (goes to docs/raw/ AND project knowledge)
```

- One slice per Claude Code session; `/clear` between slices so context stays sharp.
- Claude Code never edits `docs/` compiled files except to add the raw log you dictate; compiled docs are edited in the chat and dropped in.
- Versioning inside Claude Code: files are edited **in place** (git is the history) but the `__version__` constant and header changelog are still bumped per the bump rules, and the commit message names the version. The "one Download card per file, never overwrite" rule applies to **chat** deliverables only.

## 5. Guardrails (settings.json baseline — commit it)

```json
{
  "permissions": {
    "allow": [
      "Bash(uv run *)", "Bash(uv sync*)", "Bash(uv lock*)", "Bash(uvx library-skills*)",
      "Bash(pnpm *)", "Bash(git status*)", "Bash(git diff*)", "Bash(git log*)", "Bash(git add *)", "Bash(git commit *)", "Bash(git tag *)",
      "Bash(ruff *)", "Bash(pytest*)"
    ],
    "deny": [
      "Bash(git push --force*)", "Bash(rm -rf *)", "Bash(Remove-Item * -Recurse*)",
      "Read(**/.env)", "Read(**/.env.*)", "Read(**/*.bak)",
      "Bash(uv run alembic downgrade*)", "Bash(sqlcmd *)"
    ]
  }
}
```

Plus `.claude/rules/tests.md`: "Any function that writes to the database keeps `dry_run=True` as its default; tests run inside a rolled-back transaction; never run a script against `dbWorkmate` (the RST data) with `dry_run=False` unless the prompt says the 🤙 was given for that exact script and version."

## 6. Prompts that work here

- "Read CLAUDE.md. Implement spec §S1 only: `app/planner/rules.py` + `tests/test_planner_rules.py`, porting `docs/reference/workmate_planner_code_v1_3_1.py` functions category/engineOwned/hoursFor/assignedFor/classifyTeams/buildWorkers/initialsOf/workerLoad/capacityByWeek/workerWeeks/civilDays/weekStart 1:1 with the same names and dict keys. No DB. Run pytest. Stop before router work."
- "Run the PG-CONVERT grep gate from docs/…Data_Layer §5 and list violations; don't fix yet."
- "Compare `/api/v1/planner/range` output for 2026-09-14..2026-09-20 with this Ignition JSON (pasted) and list every key that differs."
- "Bump `__version__` in app/planner/rules.py to 1.1.0, add the changelog line, commit as `planner: rules 1.1.0 — S2 moveRules`, tag `s2-move-1.1.0`."

## 7. What Claude Code must never do here

- Run `alembic revision --autogenerate` (227 legacy tables — it will try to "fix" them).
- Edit `web/src/api/client/**` (generated) — regenerate with `pnpm gen:api`.
- Change JSON keys of the planner contract (they are the Ignition `rangeData` keys — parity is the test).
- Write dialect-specific SQL without a `-- PG-CONVERT:` tag (CI grep gate).
- Commit `.env`, `*.bak`, or `settings.local.json`.
- Touch `docs/raw/*` (append-only) except appending the session's log when asked.

## 8. Changelog

- 1.0.0 (2026-09-10) Initial.
