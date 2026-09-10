# Workmate SaaS — CLAUDE.md
<!-- Azztec_SaaS_CLAUDE_md_v1_0_0.md → repo root CLAUDE.md · Version 1.0.0 · 2026-09-10 · Adriaan
     Keep this short. Detail lives in docs/ and .claude/rules/. Bump the version line when you change it. -->

## What this is
Workmate Standalone Edition: a CMMS/ERP for manufacturing plants. FastAPI backend (`backend/`, uv) + React SPA (`web/`, pnpm).
Dev database = SQL Server `dbWorkmate` restored from the Red Stag Timber (RST) backup: **real data, ~20 years — treat as live**.
Target database = PostgreSQL. First module = the Planner, a 1:1 port of the Ignition planner in `docs/reference/`.

## Read first
- `docs/Azztec_SaaS_Project_Knowledge_Index_v*.md` (entry point), then Architecture, Landmines, Data Layer, Planner Port Spec.
- Ignition sources being ported: `docs/reference/workmate_planner_*.py` — same function names, same dict keys.

## Commands
- Backend: `cd backend && uv sync` · `uv run fastapi dev app/main.py` (http://localhost:8000/docs) · `uv run pytest -q` · `uv run ruff format . && uv run ruff check --fix .` · `uv run alembic upgrade head`
- Frontend: `cd web && pnpm install` · `pnpm dev` (http://localhost:5173, proxies /api → 8000) · `pnpm test` · `pnpm build` · `pnpm gen:api` (regenerate the typed client — backend must be running)
- Health: `GET /api/v1/health` must show `db: ok` before any DB work.

## Non-negotiables
1. Spec → 🤙 in the chat → one slice → tests → commit. Never build past the slice you were given.
2. Every function that writes to the DB defaults to `dry_run=True`; never run with `dry_run=False` against `dbWorkmate` unless the prompt says the 🤙 was given for that exact script and version.
3. SQL is dialect-portable: `COALESCE` not `ISNULL`, `CURRENT_TIMESTAMP` not `GETDATE()`, `CONCAT()` not `+`, `OFFSET/FETCH` not `TOP`, always `dbo.`; anything MSSQL-only gets `-- PG-CONVERT:`; no `:colon` in SQL comments; `RTRIM()` every legacy `char` column. SQL lives only in `app/<module>/sql.py`.
4. DB I/O only in plain `def` routes/services (sync SQLAlchemy Core). Never in `async def`.
5. Never `alembic revision --autogenerate`. Migrations are hand-written and only create Workmate-added tables.
6. Never edit `web/src/api/client/**` (generated). Never rename planner JSON keys (Ignition `rangeData` contract = parity test).
7. Pair rule: a library slice ships with its `tests/test_*.py`; pure rules test with no DB; DB tests run inside a rolled-back transaction.
8. Versions: bump `__version__` + header changelog in every changed module; commit message names module + version + slice; tag slice completions `s<n>-<thing>-<version>`.
9. Dates: civil-day arithmetic only (`civil_days`, `date-fns differenceInCalendarDays`); NZ DST 27 Sep 2026 is a test case. `tzdata` stays in deps.
10. Diagnostics: every route outcome logs one `[F]`/`[G]`/`[E]` line through `app/core/diag.py`; keep the Ignition message texts.

## Style
Python 3.13, 4-space, type hints, Ruff. TypeScript strict, Prettier, Tailwind v4 + shadcn/ui, TanStack Router/Query, Zustand, @dnd-kit/core.
Short, direct comms. Report: what changed, what was run, the exact output, what's next. No summaries of files you didn't touch.
