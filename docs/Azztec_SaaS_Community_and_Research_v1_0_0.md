# Azztec SaaS — Community, References and Tricks

**File:** Azztec_SaaS_Community_and_Research_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-10 · **Author:** Adriaan
**Status:** Active. Links verified 2026-09-10; re-verify anything older than a major version.

---

## 1. Where to ask (ranked, per stack)

### FastAPI / Python

| Rank | Channel | Use it for | Note |
|------|---------|------------|------|
| 1 | **GitHub Discussions → Questions** https://github.com/fastapi/fastapi/discussions/new?category=questions | any FastAPI question or bug report | the maintainers' own advice: ask here, not in chat — the template forces a minimal reproducible example and answers are searchable |
| 2 | FastAPI Discord https://discord.com/invite/VQjSZaeJmf | general conversation, not Q&A | tiangolo: "Don't use the chat for questions" |
| 3 | r/FastAPI | patterns, project structure debates, "how do you…" | search first — most structure questions are answered |
| 4 | Stack Overflow `[fastapi]` `[sqlalchemy]` `[pyodbc]` | long-tail errors | pyodbc/ODBC error strings are best searched verbatim |
| 5 | SQLAlchemy GitHub Discussions https://github.com/sqlalchemy/sqlalchemy/discussions | Core/dialect questions (mssql, psycopg) | zzzeek answers personally; include the SQL SQLAlchemy emitted (`echo=True`) |
| 6 | pyodbc GitHub (wiki + issues) https://github.com/mkleehammer/pyodbc | driver behaviour, connection strings | the wiki's "Connecting to SQL Server from Windows" page is canonical |
| 7 | Astral Discord / GitHub Discussions (uv, ruff, ty) | tooling | |
| 8 | Microsoft Q&A (SQL Server), dba.stackexchange.com, SQLServerCentral | restore/compat/permissions questions | |
| 9 | microsoft/mssql-python GitHub | when we swap drivers at SQLAlchemy 2.1 | |

Stay current: FastAPI newsletter https://fastapi.tiangolo.com/newsletter/, watch `fastapi/fastapi` **Releases only**, @fastapi on X/Bluesky, FastAPI Conf '26 (Amsterdam, 2026-10-28).

### React / TypeScript

| Rank | Channel | Use it for |
|------|---------|------------|
| 1 | **Reactiflux Discord** https://www.reactiflux.com/ (200k+ members; #help-react, #tanstack, #tailwind channels) | live help; the largest React community |
| 2 | r/reactjs (450k) | patterns, library choices, migration stories |
| 3 | TanStack Discord + GitHub Discussions (Router, Query, Table) https://github.com/TanStack | Router/Query specifics; TkDodo answers Query questions |
| 4 | Stack Overflow `[reactjs]` `[tanstack-query]` `[vite]` | errors |
| 5 | Vite Discord (VoidZero) + GitHub Discussions https://github.com/vitejs/vite/discussions | Vite 8 / Rolldown plugin issues |
| 6 | shadcn/ui GitHub Discussions, Tailwind GitHub Discussions | component and v4 questions |
| 7 | dnd-kit GitHub Discussions https://github.com/clauderic/dnd-kit | drag/drop edge cases (multi-container, sensors) |
| 8 | react.dev/community | the official list of communities and meetups |

### Still relevant

- Inductive Automation forum https://forum.inductiveautomation.com — the Ignition Edition keeps running at KT; parity questions may need it.
- PostgreSQL: pgsql-general list, r/PostgreSQL, Postgres Slack; PG 18 release notes for the AIO subsystem.

## 2. Reading list (in this order, first week)

**Backend**
1. FastAPI tutorial: *Bigger Applications*, *Dependencies with yield*, *SQL (Relational) Databases*, *Settings and Environment Variables*, *Frontend* (`app.frontend`), *Testing a Database*, *Behind a Proxy*, *FastAPI CLI* (`FASTAPI_ENV`).
2. Official reference repo: **full-stack-fastapi-template** https://github.com/fastapi/full-stack-fastapi-template — FastAPI + SQLModel + React/Vite + Tailwind v4 + shadcn/ui + TanStack Router/Query + generated client + Playwright, SPA served by FastAPI. Read its `backend/app/core/security.py` (PyJWT + pwdlib) and `frontend/src/client` generation script.
3. **fastapi-best-practices** https://github.com/zhanymkanov/fastapi-best-practices — the project-structure/async/pydantic conventions most teams converge on.
4. SQLAlchemy 2.0: *Unified Tutorial* (Core half), *Working with Engines and Connections*, the **mssql dialect page** (pyodbc pooling, `fast_executemany`, `odbc_connect`), *Asyncio* (to know what we're deferring).
5. Pydantic v2 *Serialization* (Decimal, datetime) and *Settings management*.
6. uv docs: *Projects*, *Python versions*, *Tools (`uvx`)*.

**Frontend**
1. TanStack Router: *File-Based Routing*, *Search Params*, *Data Loading*; TanStack Query: *Important Defaults*, *Optimistic Updates*, *Query Invalidation*; TkDodo's *Practical React Query* series.
2. Vite 8 announcement (Rolldown) https://vite.dev/blog/announcing-vite8 and the migration guide; `@vitejs/plugin-react` 6 changelog (no Babel).
3. React 19.3 blog https://react.dev/blog/2026/09/09/react-19-3 and the React 19 upgrade guide (`ref` as prop, Compiler).
4. Tailwind v4 *Upgrade guide* (CSS-first `@theme`), shadcn/ui *Tailwind v4* + *Installation → Vite*.
5. dnd-kit docs: *Multiple containers* example, *Sensors → activation constraints*, *DragOverlay*.
6. date-fns v4 + `@date-fns/tz` docs (time zones without moment).

**Data**
- `Workmate_PG_Forward_Compat_v1_0.md` (ours), PostgreSQL *Identifiers and Key Words* (case folding), pgloader MSSQL chapter (later).

## 3. Tricks that save days

| Trick | What it does |
|-------|--------------|
| `uvx library-skills --claude` (run inside `backend/`) | installs the **official FastAPI agent skill** (bundled with the package, version-synced) into `.claude/skills` for Claude Code; `npx library-skills` does the same for JS libs that ship one |
| `uvx fastapi-new <name>` | tiangolo's one-command uv-configured FastAPI project (we scaffold our own, but it's the reference layout) |
| `uv run fastapi dev app/main.py` | reload + `FASTAPI_ENV=development` (missing `dist/` is a warning, not an error) |
| `app.frontend("/", directory="../web/dist")` | serve the SPA from FastAPI — one origin, no CORS, SPA fallback only for browser navigations |
| `pnpm gen:api` → `@hey-api/openapi-ts -i http://localhost:8000/openapi.json -o src/api/client` | typed TS client + Zod-compatible types from the live OpenAPI; regenerate after every contract change |
| TanStack Query devtools in dev (`@tanstack/react-query-devtools`) | see the 60 s poll, stale/fresh, mutation state |
| `SQLALCHEMY_ECHO=1` (our `.env` flag) | prints every SQL statement with binds — the fastest way to see what pyodbc actually sent |
| `bindparam("ids", expanding=True)` | portable `IN (:ids_1, :ids_2, …)` on both engines — no XML-split, no `string_to_array` |
| `uv run pytest -q -x --lf` | stop on first failure, rerun only last failures |
| `uv run ruff format . && uv run ruff check --fix .` | format + lint in one go; also on save in VS Code |
| `pnpm exec playwright codegen http://localhost:5173/planner` | records a drag/drop test skeleton |
| VS Code MSSQL extension (`ms-mssql.mssql`) | query the RST DB without leaving the editor; Azure Data Studio is retired into it |
| `sqlcmd -C` | trust the self-signed cert on the command line, same as `TrustServerCertificate=yes` |
| `git tag s<slice>-<thing>-<version>` | slice completion markers for both the chat and Claude Code |
| `docker compose up -d && open http://localhost:8080` | Adminer on the Postgres track |
| `python -X dev` / `PYTHONWARNINGS=default` | surfaces ResourceWarnings (unclosed connections) early |
| SSE is built into FastAPI now (`EventSourceResponse`) | live planner updates later without WebSockets |
| `@tanstack/react-router` search params as state | shareable planner URLs (`/planner?from=…&to=…&view=week`) for free |

## 4. How to ask a question that gets answered

1. Version block: `uv run python -c "import fastapi,sqlalchemy,pyodbc;print(fastapi.__version__,sqlalchemy.__version__,pyodbc.version)"`, `node -v`, `pnpm -v`, driver version, OS.
2. Minimal reproducible example — one file, no Workmate tables (use a temp table), the exact error text.
3. What you expected vs what happened; what you already tried (with the `echo=True` SQL where relevant).
4. Post in GitHub Discussions (FastAPI/SQLAlchemy/TanStack) or Reactiflux; link the discussion in the raw log so the answer isn't lost.

## 5. Reference repos worth cloning next to ours

- `fastapi/full-stack-fastapi-template` — the official shape (auth, generated client, Playwright, Compose).
- `fastapi/fastapi-new` — minimal uv project generator.
- `mantle-bearer/fullstack-fastapi-template` — app-owned auth + RBAC + `app.frontend()` serving a committed `dist/`.
- `timbomckay/openapi-tanstack-starter` — Vite + TanStack Router/Query/Form/Table + shadcn + Hey API client, i.e. our frontend recipe.
- `tiangolo/library-skills` — how library skills are found and installed.

## 6. Changelog

- 1.0.0 (2026-09-10) Initial.
