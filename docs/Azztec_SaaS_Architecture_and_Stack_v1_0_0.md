# Azztec SaaS — Architecture and Stack

**File:** Azztec_SaaS_Architecture_and_Stack_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-10 · **Author:** Adriaan
**Status:** Draft — decisions D-1…D-12 awaiting 🤙
**Verified:** every version below was checked against the vendor's release page on **2026-09-10**.

---

## 1. Purpose

Answer "FastAPI + React + what else?" with one opinionated, verified stack, the decisions behind it, the repo layout, and the
version pins — so the new chat builds instead of researching.

## 2. The shape

```
 Browser ──────────────► React SPA (Vite build)  ──── served by FastAPI app.frontend() in prod
                                │                      (Vite dev server + /api proxy in dev)
                                │ fetch /api/v1/...   (typed client generated from OpenAPI)
                                ▼
 FastAPI (uvicorn) ── routers ── services ── repos ── SQLAlchemy Core (sync) ── pyodbc ──► SQL Server  (dev: dbWorkmate = RST)
        │                │                            └────────────────────── psycopg 3 ─► PostgreSQL  (target)
        │                └── pure rules (planner/rules.py) — zero I/O, ported 1:1 from Ignition
        ├── /api/v1/ai/chat ──► workmate-ai (Layer 2 contract; same FastAPI service, own router)
        ├── diag middleware ──► stdout JSON + dbo.Diag_Log
        └── CLI (typer): `workmate nightshift`, `workmate planner nightly`  ← Task Scheduler / cron
```

Single process, single origin. No CORS in prod, no iframe, no HMAC `sid|uid` gate — a JWT session is the actor.

## 3. The stack — what, which version, why

### 3.1 Backend (Python)

| Layer | Choice | Version (2026-09-10) | Why | Rejected |
|-------|--------|----------------------|-----|----------|
| Python | CPython **3.13** via `uv python install 3.13` | 3.13.x (3.14 is current; uv now defaults new envs to 3.14) | widest wheel coverage today (pyodbc, ortools, psycopg); bump to 3.14 when `uv lock` resolves clean | 3.14 now — verify wheels first |
| Package/project manager | **uv** (Astral) | 0.12.10 | replaces pip/venv/pyenv/poetry; FastAPI docs now use uv projects by default; `uv lock` reproducible; `uvx` for tools | poetry, pip-tools |
| Web framework | **FastAPI[standard]** | 0.141.1 (2026-07-29) | typed routes → OpenAPI → generated TS client; `fastapi dev`; `app.frontend()` serves the SPA; native SSE/JSON-lines streaming; official agent skill via library-skills | Django/DRF (heavier), Litestar (smaller ecosystem) |
| Validation/settings | **Pydantic v2** + **pydantic-settings** | 2.x | Pydantic v2 is what FastAPI 0.100+ runs on; settings from `.env` | — |
| DB toolkit | **SQLAlchemy 2.0 Core (sync)** | 2.0.52 (2026-08-11); 2.1 is at rc1 (2026-08-31) | one `text()`/Core codebase runs on MSSQL and PG; sync avoids the pyodbc-async trap; upgrade to 2.1 when final | ORM-heavy models over a 227-table legacy schema; SQLModel |
| MSSQL driver | **pyodbc** + **Microsoft ODBC Driver 18** | pyodbc 5.3.0 / ODBC 18.6.2.1 | the well-trodden SQLAlchemy path; ODBC 18 is what Ignition/SSMS already use on the box | `mssql-python` (Microsoft, GA, faster, bundled driver — but its SQLAlchemy dialect only ships in 2.1; swap in when 2.1 is final: D-2 note) |
| PG driver | **psycopg 3** (`psycopg[binary]`) | 3.2.x | the modern libpq driver; sync and async in one package | asyncpg (async-only) |
| Migrations | **Alembic** | 1.16.x | only for Workmate-added tables; `version_table` in `dbo` | — |
| Auth | **PyJWT** + **pwdlib[argon2]** | current | what the official full-stack template uses; cookie or bearer | fastapi-users (too opinionated for the legacy Users table), Keycloak (later, OIDC) |
| HTTP client | **httpx** | 0.28.x | tests (`TestClient`), calls to workmate-ai | requests |
| Scheduler | **Typer CLI** + OS scheduler (Task Scheduler / cron) | Typer 0.26+ | matches the Night Shift pattern; APScheduler 3.x in-process is optional; APScheduler 4 is still pre-release | Celery/Redis (overkill for one plant) |
| Lint/format | **Ruff** | 0.13.x | one tool, format-on-save | black+flake8 |
| Type check | **ty** (Astral, preview) or Pyright | — | FastAPI itself added `ty` configs in 0.137.2; run in CI when stable | mypy |
| Tests | **pytest** + **pytest-cov** + `TestClient` | 8.x | pair rule; dependency overrides for the DB | — |
| Optimisation | **OR-Tools CP-SAT** | 9.x (later, Planner Tier 2/3) | the 80/20 rule: CP-SAT plans, the LLM explains | — |
| Time zones | stdlib `zoneinfo` + **tzdata** package on Windows | — | `ZoneInfo("Pacific/Auckland")`; Windows has no system tz database → `tzdata` wheel is mandatory | pytz |

### 3.2 Frontend (TypeScript)

| Layer | Choice | Version (2026-09-10) | Why | Rejected |
|-------|--------|----------------------|-----|----------|
| Runtime | **Node.js 24 LTS "Krypton"** | 24.x (Active LTS until 2026-10-20 maintenance; EOL 2028-04-30) | production line today; Node 26 enters LTS 2026-10-28 — move then | Node 26 now (Current) |
| Package manager | **pnpm** | 10.x | fast, strict, disk-cheap; `pnpm dlx` for one-offs | npm (fine), yarn |
| Build | **Vite 8** (Rolldown) | 8.0.x (GA 2026-03-12) | Rust bundler, 10–30× faster builds, plugin-compatible | webpack, RSBuild |
| UI library | **React 19.3** | 19.3.0 (2026-09-09) | View Transitions + Fragment refs stable; React Compiler 1.0 stable (opt-in via `@vitejs/plugin-react` preset) | — |
| React plugin | **@vitejs/plugin-react** | 6.1.1 | Oxc-based, no Babel; `reactCompilerPreset` optional | plugin-react-swc |
| Language | **TypeScript** strict | 5.9.x | generated client types end-to-end | — |
| Routing | **TanStack Router** (file-based) | 1.x | fully typed params/search; `routeTree.gen.ts` | React Router v7/v8 (fine, less typed), Next.js (SSR not wanted) |
| Server state | **TanStack Query v5** | 5.9x | caching, `refetchInterval` (the 60 s planner poll), optimistic updates for drag/drop | SWR, Redux Toolkit Query |
| Client state | **Zustand** | 5.x | selection/filters/UI state, tiny | Redux |
| Tables/lists | **TanStack Table v8** | 8.21+ | headless, sort/filter/virtualise | AG Grid (later if needed) |
| Styling | **Tailwind CSS v4** | 4.1.x | CSS-first config; what shadcn/ui expects | CSS modules |
| Components | **shadcn/ui** (+ Radix/Base UI primitives, lucide-react) | current | copied-in, owned components; dialog/popover/command palette for the planner | MUI, Mantine, Chakra |
| Drag & drop | **@dnd-kit/core** (v6, classic) | 6.3.x | headless, accessible, multi-container (WO card → day cell); `@dnd-kit/react` 0.5 is the rewrite — adopt later | react-beautiful-dnd (deprecated), FullCalendar (licence for resource views) |
| Dates | **date-fns v4** + `@date-fns/tz` | 4.x | pure calendar arithmetic (`differenceInCalendarDays` = `civilDays()`), tz-aware | moment, dayjs |
| Validation | **Zod v4** | 4.x | forms + settings; matches generated types | yup |
| API client | **@hey-api/openapi-ts** | current | `pnpm gen:api` regenerates a typed client from `/openapi.json` | hand-written fetch |
| Unit tests | **Vitest** + Testing Library | 4.x | Vite-native | Jest |
| E2E | **Playwright** | 1.5x | drag/drop smoke on the real UI | Cypress |
| Lint/format | **ESLint 10** (flat) + **Prettier** (or oxlint/oxfmt) | — | scaffolded by the TanStack CLI `--toolchain eslint+prettier` | — |

### 3.3 Data and infrastructure

| Thing | Choice | Version | Notes |
|-------|--------|---------|-------|
| Dev DB | **SQL Server** local instance, `dbWorkmate` restored from the RST backup | existing instance; SQL Server 2025 Developer 17.0 if a fresh one is needed (`winget install -e --id Microsoft.SQLServer.2025.Developer`) | mixed-mode auth, TCP/IP on, login `svc_workmate` |
| DB tooling | SSMS 21/22, or VS Code **MSSQL** extension (Azure Data Studio is retired into it) | — | DBeaver optional |
| Target DB | **PostgreSQL 18** | 18.6 (2026-08-13) | Docker Compose on dev; native EDB installer or the appliance later; PG 19 is in beta |
| Containers | **Docker Desktop** + Compose | current | Postgres + Adminer on dev; the appliance is Docker Compose on Ubuntu 24.04 |
| Prod serving | uvicorn behind a reverse proxy (Caddy on Linux/appliance, IIS ARR or Caddy on Windows) with TLS; SPA served by `app.frontend()` | — | Windows service via NSSM; Linux systemd |
| Repo | one git repo `workmate-saas` (GitHub, private) | — | CI: GitHub Actions (ruff, pytest, vitest, build, PG-CONVERT grep gate) |
| Editor / agent | VS Code + **Claude Code** in the repo | native installer | reads `CLAUDE.md`, `.claude/rules/*.md`, `.claude/skills/` (FastAPI skill via `uvx library-skills --claude`); see `Azztec_SaaS_Claude_Code_Workflow_v1_0_0.md` |

## 4. Decisions

| ID | Decision | Rationale / consequence |
|----|----------|--------------------------|
| **D-1** | Monorepo `workmate-saas/` with `backend/` (uv project) and `web/` (pnpm project); one version tag per slice | one PR = one slice; the generated client lives next to the API that defines it |
| **D-2** | **Sync SQLAlchemy Core + `def` endpoints** (FastAPI threadpool) for phase 1; async only once PG-only | pyodbc is sync; `aioodbc` is fragile; a plant CMMS is tens of users; same Core code runs on both dialects; `def` endpoints run in anyio's threadpool (default 40 threads) — never do DB I/O in `async def`. When SQLAlchemy 2.1 is final, `mssql+mssqlpython://` becomes a URL change |
| **D-3** | **Dialect-portable SQL in `sql.py` modules** with `text()` + named binds; the five habits (COALESCE, CURRENT_TIMESTAMP, CONCAT, OFFSET-FETCH, `dbo.`); `-- PG-CONVERT:` tags; `db.insert_returning_id()` hides SCOPE_IDENTITY vs RETURNING; PG tables created **lowercase** so unquoted identifiers work on both | migration = grep, as the forward-compat standard intended |
| **D-4** | Module layout per domain: `rules.py` (pure) · `sql.py` (text) · `repo.py` (fetch → dicts) · `service.py` (transactions, writes, audit) · `schemas.py` (Pydantic) · `router.py` (FastAPI) · `tests/` | mirrors the Ignition split (planner = rules+data, planner_api = routing); Planner is the reference implementation |
| **D-5** | Identity: JWT (HS256, short-lived access token in an HttpOnly cookie, refresh later) whose `sub` is the legacy `Users.User_Id`; new table `dbo.App_User` (user_id FK, email, argon2 hash, is_active, roles) added by migration; OIDC (Entra ID) via Authlib in phase 2 | the actor for every write is `User_Id`, exactly as Ignition's `workmate.identity.resolve`; `PLANNER_DEV_USER_ID` survives as a dev-only override |
| **D-6** | Serve the built SPA with `app.frontend("/", directory="../web/dist")`; API under `/api/v1/*`; dev = Vite on 5173 proxying `/api` and `/docs` to 8000 | single origin, no CORS in prod; `fastapi dev` sets `FASTAPI_ENV=development` so a missing `dist/` is only a warning |
| **D-7** | Scheduled work = Typer CLI commands run by Task Scheduler (Windows) / cron (appliance); in-process APScheduler 3.x only if a client box has no scheduler | Night Shift and nightly proposal keep their shape; one process, one log |
| **D-8** | Diagnostics: request-id middleware + `diag.log()` → stdout JSON + `dbo.Diag_Log`; `/api/v1/_diag/self-test`; browser `window.onerror` → `POST /api/v1/_diag/client` | forensic standard preserved |
| **D-9** | API conventions: `/api/v1/<module>/<action>`; JSON keys **camelCase exactly as the Ignition contract** (`rangeData` keys unchanged); errors `{ok:false, code, message}` with HTTP 200 for rule refusals that carry a preview (`CONFIRM`), 409 `STALE`, 422 rule refusals, 401/403 identity; OpenAPI tags per module | the existing `Planner_v1_7_1.html` can be pointed at the new API as a parity smoke |
| **D-10** | Tests: pure rules = no DB; repo/service = transaction rolled back; HTTP = `TestClient` with dependency overrides; UI = Vitest; E2E = Playwright against `fastapi dev` + Vite | pair rule enforced in CI |
| **D-11** | Runtime switches stay in `dbo.System_Configuration` (`PLANNER_*` keys) read through one `config_value(key, default)`; deploy config in `.env` via pydantic-settings (`WORKMATE_DB_URL` selects the dialect) | same operational knobs as today; nothing hard-coded |
| **D-12** | Tenancy: one database per client (as today: `dbWorkmate`, `dbWorkmate_Bakels`, `dbWorkmate_QL`); the engine factory takes a tenant → URL map; schema `dbo` kept on PG (`CREATE SCHEMA dbo` + `search_path`) | multi-tenant routing is a header/host → engine lookup later, not a data-model rewrite |

## 5. Repo layout

```
workmate-saas/
├── README.md
├── .gitattributes                 # * text=auto eol=lf
├── .github/workflows/ci.yml       # ruff · pytest · vitest · build · PG-CONVERT grep gate
├── docker-compose.yml             # postgres:18 + adminer (PG track)
├── scripts/
│   ├── bootstrap-windows.ps1      # ← Azztec_SaaS_Bootstrap_Windows
│   ├── scaffold.ps1               # ← Azztec_SaaS_Scaffold_Repo
│   └── restore_rst.sql            # RESTORE … WITH MOVE template
├── backend/                       # uv project
│   ├── pyproject.toml  uv.lock  .python-version  .env.example  alembic.ini
│   ├── app/
│   │   ├── main.py                # app factory, lifespan, routers, app.frontend()
│   │   ├── core/  config.py  db.py  diag.py  security.py  deps.py
│   │   ├── planner/  rules.py  sql.py  repo.py  service.py  schemas.py  router.py
│   │   ├── planner_ai/  (S5)   planner_chat/  (S5b)
│   │   ├── auth/  router.py  service.py
│   │   └── cli.py                 # typer: `uv run python -m app.cli nightshift | planner nightly` (console script once app is a package)
│   ├── alembic/versions/
│   └── tests/  conftest.py  test_smoke.py  test_planner_rules.py …
├── web/                           # pnpm project (TanStack CLI scaffold)
│   ├── package.json  vite.config.ts  tsconfig.json  components.json (shadcn)
│   ├── src/
│   │   ├── routes/  __root.tsx  index.tsx  planner.tsx
│   │   ├── features/planner/  PlannerGrid.tsx  DayCell.tsx  WOCard.tsx  CapacityBar.tsx  usePlannerRange.ts  store.ts
│   │   ├── components/ui/  (shadcn)
│   │   ├── api/  client/ (generated — never edit)  http.ts
│   │   └── lib/  dates.ts (civilDays twin)  colours.ts
│   └── e2e/  planner.spec.ts
└── docs/                          # compiled knowledge + raw logs (mirror of project knowledge)
```

## 6. Request flow (Planner `/range`)

1. React `usePlannerRange(from,to)` → TanStack Query key `['planner','range',from,to]`, `staleTime` 30 s, `refetchInterval` 60 s (paused when the tab is hidden).
2. Generated client → `GET /api/v1/planner/range?from=&to=` with the session cookie.
3. Router validates (`from<=to`, ≤ 400 days) → `service.range_data()` → `repo.fetch_wos/labour/skill_rows/priorities` (four `text()` selects) → `rules.*` pure assembly → Pydantic `RangeData` response (same keys as Ignition).
4. Diag middleware writes `[F] range 2026-09-14..2026-09-20 rows=… labour=… workers=…` with the request id.

## 7. AI layering (unchanged from `Workmate_AI_Architecture_v1_2.md`)

- Layer 2 (chat surface) = the React chat widget (and Azzmax, only via `POST /ai/chat`).
- Layers 3–8 = `workmate-ai` (FastAPI). Standalone Edition: `app/ai/` router in the same process, tool handlers call the
  same `planner.service` functions the HTTP routes use. `planner_chat.parse()` is the deterministic stand-in the LLM replaces.
- Layer 1 homes: Azure AI Foundry (customer tenant) or the Azztec AI Appliance (vLLM, OpenAI-compatible) — a `LLMClient` config change.

## 8. Version pins (copy into `pyproject.toml` / `package.json`)

Backend (`pyproject.toml`, see `Azztec_SaaS_pyproject_v1_0_0.toml`): `fastapi[standard]>=0.141,<0.142`, `pydantic>=2.11`,
`pydantic-settings>=2.10`, `sqlalchemy>=2.0.52,<2.1`, `pyodbc>=5.3`, `psycopg[binary]>=3.2`, `alembic>=1.16`, `pyjwt>=2.10`,
`pwdlib[argon2]>=0.2`, `httpx>=0.28`, `typer>=0.26`, `tzdata`, `python-multipart`. Dev: `pytest`, `pytest-cov`, `ruff`.

Frontend (scaffold pins the current majors): `react@19.3`, `react-dom@19.3`, `vite@8`, `@vitejs/plugin-react@6`,
`@tanstack/react-router@1`, `@tanstack/react-query@5`, `@tanstack/react-table@8`, `tailwindcss@4`, `zustand@5`, `zod@4`,
`@dnd-kit/core@6`, `@dnd-kit/utilities@3`, `date-fns@4`, `@date-fns/tz`, `lucide-react`, `@hey-api/openapi-ts` (dev),
`vitest@4`, `@playwright/test`, `typescript@5`.

Lock files (`uv.lock`, `pnpm-lock.yaml`) are committed. Upgrades are a deliberate slice, never a side effect.

## 9. Alternatives considered (so they are not re-litigated)

- **Next.js / SSR** — a plant CMMS is an authenticated SPA; SSR buys nothing and complicates on-prem hosting.
- **SQLModel / full ORM** — 227 legacy tables with `char(n)` keys and stored-proc write paths; Core + `text()` keeps the SQL greppable and dialect-tagged.
- **Async everything** — blocked by pyodbc; revisit at PG-only with `psycopg` async or `asyncpg`.
- **Celery/Redis** — no queue workload yet; Typer + Task Scheduler is enough.
- **FullCalendar** — resource-timeline views need the premium licence; the planner grid is custom anyway (as it is in `Planner_v1_7_1.html`).
- **Keycloak/Authentik now** — phase 2; the legacy `Users` table is the identity source of truth until then.

## 10. Changelog

- 1.0.0 (2026-09-10) Initial.
