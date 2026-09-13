# Azztec SaaS — Architecture and Stack

**File:** Azztec_SaaS_Architecture_and_Stack_v1_0_4.md · **Version:** 1.0.4 · **Date:** 2026-09-13 · **Author:** Adriaan
**Status:** Active — D-1…D-12 carried as signed 2026-09-10 in every chunk spec since (S1c §2 onward); D-5, D-8 and D-12 now carry KT evidence that the uplift audit (open item 32) decides on
**Verified:** every version below was checked against the vendor's release page on **2026-09-10**; §3.2 rows marked ★ re-verified **on the box** 2026-09-12 (logs 2026-09-12 1.0.0 §5.2 and 1.1.0 §5.1, S1f spec §3) and unchanged through S1g and the KT-database session 2026-09-13 (no `pnpm add`, no `uv add`)

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
 FastAPI (uvicorn) ── routers ── services ── repos ── SQLAlchemy Core (sync) ── pyodbc ──► SQL Server  (dev: dbWorkmate = RST; dbWorkmate_KT = the KT oracle, read-only)
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
| Migrations | **Alembic** | 1.16.x | only for Workmate-added tables; `version_table` in `dbo`. The first migrations are the KT uplift (item 32, scripted from `dbWorkmate_KT`'s catalog) and S3's `WO_N_Plan` — how they number against each other is uplift-audit question 2 | — |
| Auth | **PyJWT** + **pwdlib[argon2]** | current | what the official full-stack template uses; cookie or bearer | fastapi-users (too opinionated for the legacy Users table), Keycloak (later, OIDC) |
| HTTP client | **httpx** | 0.28.x | tests (`TestClient`), calls to workmate-ai | requests |
| Scheduler | **Typer CLI** + OS scheduler (Task Scheduler / cron) | Typer 0.26+ | matches the Night Shift pattern; APScheduler 3.x in-process is optional; APScheduler 4 is still pre-release | Celery/Redis (overkill for one plant) |
| Lint/format | **Ruff** | 0.13.x | one tool, format-on-save | black+flake8 |
| Type check | **ty** (Astral, preview) or Pyright | — | FastAPI itself added `ty` configs in 0.137.2; run in CI when stable | mypy |
| Tests | **pytest** + **pytest-cov** + `TestClient` | 8.x | pair rule; dependency overrides for the DB. `pyproject` sets `addopts = "-q"` — run plain `uv run pytest`, bare, never add a second `-q`, gate on the exit code (Landmines §A) | — |
| Optimisation | **OR-Tools CP-SAT** | 9.x (later, Planner Tier 2/3) | the 80/20 rule: CP-SAT plans, the LLM explains | — |
| Time zones | stdlib `zoneinfo` + **tzdata** package on Windows | — | `ZoneInfo("Pacific/Auckland")`; Windows has no system tz database → `tzdata` wheel is mandatory | pytz |

### 3.2 Frontend (TypeScript)

| Layer | Choice | Version (2026-09-10) | Why | Rejected |
|-------|--------|----------------------|-----|----------|
| Runtime | **Node.js 24 LTS "Krypton"** | 24.x (Active LTS until 2026-10-20 maintenance; EOL 2028-04-30) | production line today; Node 26 enters LTS 2026-10-28 — move then | Node 26 now (Current) |
| Package manager | **pnpm** ★ | **12.3.4** on the box (doc said 10.x) | fast, strict, disk-cheap; `pnpm dlx` for one-offs. **pnpm ≥10 blocks postinstall scripts**: approvals live in `pnpm-workspace.yaml → allowBuilds`, written by `pnpm approve-builds` and committed (Landmines §C) | npm (fine), yarn |
| Build | **Vite 8** (Rolldown) ★ | 8.3.0 on the box | Rust bundler, 10–30× faster builds, plugin-compatible; dev server on **port 3000** (the scaffold's `dev` script is `vite dev --port 3000` — not 5173), proxying `/api`, `/docs`, `/openapi.json` to 8000; `tanstackRouter({ autoCodeSplitting: true })` — a route file exports `Route` only (Landmines §C) | webpack, RSBuild |
| UI library | **React 19.3** ★ | 19.3.0 on the box | View Transitions + Fragment refs stable; React Compiler 1.0 stable (opt-in via `@vitejs/plugin-react` preset) | — |
| React plugin | **@vitejs/plugin-react** | 6.1.1 | Oxc-based, no Babel; `reactCompilerPreset` optional | plugin-react-swc |
| Language | **TypeScript 6.x** strict ★ (**OD-28**, 2026-09-12) | 6.0.3 on the box — what the CLI and typescript-eslint resolved; compiles clean; the 5.9.x pin in 1.0.0/1.0.1 was the doc lagging the scaffold. **TypeScript 7.0.2 (the native compiler) is published and deliberately not taken.** TS 6's `lib.dom` is narrower than 5.9 habits assume — `as HTMLButtonElement` and `textContent ?? ''` are lint errors (Landmines §C) | generated client types end-to-end; `tsconfig` `strict`, `noUnusedLocals`, `noUnusedParameters`, `verbatimModuleSyntax`, paths `@/*` and `#/*` | TS 7 now |
| Routing | **TanStack Router** (file-based) ★ | 1.170.35 on the box, scaffolded by `@tanstack/cli create --router-only` | fully typed params/search; `routeTree.gen.ts` committed | React Router v7/v8 (fine, less typed), Next.js (SSR not wanted) |
| Server state | **TanStack Query v5** ★ | 5.102.8 on the box — added by hand, `--router-only` disables the add-on | caching, `refetchInterval` (the 60 s planner poll), optimistic updates for drag/drop; query options generated by the hey-api plugin, whose `queryFn` forwards `signal` so a superseded `/range` aborts in the browser (**OD-30**) | SWR, Redux Toolkit Query |
| Client state | **Zustand** ★ | 5.0.15 on the box | `features/planner/store.ts` 1.1.0 (S1f + S1g): cats, selected, railOpen, contractors, loadedOnly, **filters** (team / workers / priority / unassigned / search), **dayOpen** — not persisted; the URL carries `mode` + `anchor` only (**OD-29**) | Redux |
| Tables/lists | **TanStack Table v8** | 8.21+ (not installed yet) | headless, sort/filter/virtualise — when a list needs it | AG Grid (later if needed) |
| Styling | **Tailwind CSS v4** ★ | 4.3.3 on the box via `@tailwindcss/vite` (no duplicate postcss dep) | CSS-first; the CLI's `styles.css` is untouched. **OD-27:** the planner *port* ships the oracle's CSS as `features/planner/planner.css` (1.1.1 after S1g), same tokens and class names as `wm-ui.css`, scoped under `.wm-planner`; Tailwind/shadcn adoption is decided at the first component that is **not** a port — which, as of 2026-09-13, is the tips ⓘ (open item 33) | CSS modules |
| Components | **shadcn/ui** (+ Radix/Base UI primitives, lucide-react) | **not installed** — **OD-31 (2026-09-13):** S1g's day dialog (`showDay`) and worker menu (`.wsel`) were ports on the oracle's CSS, so shadcn did not arrive with them; it arrives with the first component that is *not* a port, by hand (`--router-only` disabled `--add-ons`) | copied-in, owned components; dialog/popover/command palette when a non-port surface needs one. S1f's lock/pin glyphs are the oracle's two inline SVGs, not icons | MUI, Mantine, Chakra |
| Drag & drop | **@dnd-kit/core** (v6, classic) | 6.3.x — **not installed** (S2) | headless, accessible, multi-container (WO card → day cell); `@dnd-kit/react` 0.5 is the rewrite — adopt later | react-beautiful-dnd (deprecated), FullCalendar (licence for resource views) |
| Dates | **date-fns v4** ★ (+ `@date-fns/tz` later) | 4.4.0 on the box | pure calendar arithmetic (`differenceInCalendarDays` = `civilDays()`); `lib/dates.ts` 1.1.0 is the **only** module that touches `Date` — `windowFor`, `navAnchor`, `todayIso` live there, `features/planner/rules.ts` has no `Date` and no DOM (still true at 1.1.0) | moment, dayjs |
| Validation | **Zod v4** ★ | 4.6.1 on the box | forms + settings; matches generated types. Not on the planner route — `validateSearch` is a plain function on `parseIso` (OD-29), no zod adapter | yup |
| API client | **@hey-api/openapi-ts** ★ (OD-22) | 0.99.0 on the box | `pnpm gen:api` regenerates from the **committed** `docs/api/openapi_<ver>.json` — no backend needed; fetch client bundled (named in `plugins`, not installed); `@tanstack/react-query` plugin emits `…Options()`; `postProcess: ['prettier']` only; output committed, never edited, never linted | hand-written fetch; `openapi-typescript` (types only — rejected 2026-09-11) |
| Unit tests | **Vitest** + Testing Library ★ | 5.0.0 / RTL 16.3.3 / jsdom 30.0.1 on the box; `vitest.config.ts` merges `./vite.config.ts` | Vite-native; `fetch` stubbed for hook/wire tests, client `baseUrl` absolute under Node. **No `setupFiles`, no `globals`:** explicit `cleanup()` in `afterEach`, no jest-dom, assertions on `className` / `style.width` / `textContent` (Landmines §C). 96 tests in 8 files after S1f; **155 in 11 files after S1g** — run `pnpm test` bare, its box-drawn summary defeats a literal `Select-String` (Landmines §A) | Jest |
| E2E | **Playwright** | 1.5x (not installed — S6) | drag/drop smoke on the real UI | Cypress |
| Lint/format | **ESLint 10** (flat, `@tanstack/eslint-config` 0.4.0) + **Prettier 3** ★ (OD-21, **OD-28**) | eslint 10.10.0 (the CLI's `eslint` add-on pinned 9.39.5 with an EOL warning; `@tanstack/eslint-config` peers `^9 \|\| ^10`, bumped 2026-09-12 before the first `.tsx`, lint silent before and after) / prettier 3.9.6 | `eslint.config.js` ignores `src/api/client/**`, `src/routeTree.gen.ts`, `dist/**`. `pnpm lint` is ESLint only — `prettier --check` is not in the smoke (open item 25) | biome (one tool, four-doc stack change — rejected 2026-09-11) |

### 3.3 Data and infrastructure

| Thing | Choice | Version | Notes |
|-------|--------|---------|-------|
| Dev DB | **SQL Server** local instance, `dbWorkmate` restored from the RST backup (compat 170) | existing instance (Standard Developer Edition 64-bit 17.0.1000.7); SQL Server 2025 Developer 17.0 if a fresh one is needed (`winget install -e --id Microsoft.SQLServer.2025.Developer`) | mixed-mode auth, TCP/IP on, login `svc_workmate`; `max server memory` **8192 MB** since 2026-09-13 (Landmines §F) |
| The KT oracle copy | **`dbWorkmate_KT`** on the same instance — KT's production `dbWorkmate` from `KTSQL02` (SQL Server 2022 16.0.4275, compat 100), restored 2026-09-13 `WITH MOVE` to the instance defaults and **`SET READ_ONLY`** | backup 2026-09-13 00:32, full, 78.7 MB; physical version 957 → 998 on restore | **Read-only, always.** Every comparison against RST is three-part-name SQL (`dbWorkmate_KT.dbo.…`) and a cross-database batch starts with `SELECT DB_NAME()` (Landmines §B). `svc_workmate` has no user in it yet — a read-write flip, create, flip back, only when `scripts/parity_range.py` runs (open item 26). The restore is a **one-way door**: nothing from AzztecDev (2025) can ever go back onto KTSQL02 (2022). Together with the Ignition project export (`MainSCADA_Timberlands_2026-09-10_1900.zip`, on the box, not in PK) it is the two-sided parity oracle: **the database says what exists, the export says what is used** — `Azztec_SaaS_KT_Schema_Delta_v1_0_0.md` is the scope/compare, input to the uplift audit (item 32) |
| DB tooling | `sqlcmd -S localhost -E -C` under the Windows login for anything `svc_workmate` cannot do; SSMS 21/22 or the VS Code **MSSQL** extension (Azure Data Studio is retired into it) optional | — | ODBC 18 needs `-C` for the local self-signed cert; `-W` and `-y 0` are mutually exclusive, so are `-h -1` and `-y 0`; the engine opens a `.bak` as `NT Service\MSSQLSERVER` (error 2 = path, 5 = ACL) — Landmines §B; DBeaver optional |
| Target DB | **PostgreSQL 18** | 18.6 (2026-08-13) | Docker Compose on dev; native EDB installer or the appliance later; PG 19 is in beta |
| Containers | **Docker Desktop** + Compose | current | Postgres + Adminer on dev; the appliance is Docker Compose on Ubuntu 24.04. **On the dev box Docker now has a cap** — `.wslconfig` `[wsl2] memory=8GB swap=2GB` written 2026-09-13 — after it took 45 GB of a 32 GB machine and starved SQL Server (Landmines §F). It has stayed down since; its first clean start under the cap closes open item 17 and un-parks the compose file |
| Prod serving | uvicorn behind a reverse proxy (Caddy on Linux/appliance, IIS ARR or Caddy on Windows) with TLS; SPA served by `app.frontend()` | — | Windows service via NSSM; Linux systemd |
| Repo | one git repo `workmate-saas` (GitHub, private) | — | CI: GitHub Actions (ruff, pytest, vitest, build, PG-CONVERT grep gate) |
| Editor / agent | VS Code + **Claude Code** in the repo | native installer | reads `CLAUDE.md`, `.claude/rules/*.md`, `.claude/skills/` (FastAPI skill via `uvx library-skills --claude`); see `Azztec_SaaS_Claude_Code_Workflow_v1_0_0.md` |

## 4. Decisions

| ID | Decision | Rationale / consequence |
|----|----------|--------------------------|
| **D-1** | Monorepo `workmate-saas/` with `backend/` (uv project) and `web/` (pnpm project); one version tag per slice | one PR = one slice; the generated client lives next to the API that defines it |
| **D-2** | **Sync SQLAlchemy Core + `def` endpoints** (FastAPI threadpool) for phase 1; async only once PG-only | pyodbc is sync; `aioodbc` is fragile; a plant CMMS is tens of users; same Core code runs on both dialects; `def` endpoints run in anyio's threadpool (default 40 threads) — never do DB I/O in `async def`. When SQLAlchemy 2.1 is final, `mssql+mssqlpython://` becomes a URL change. Consequence recorded 2026-09-13 (OD-30): a request the browser has aborted still runs to completion on the server — nothing on this stack can cancel it |
| **D-3** | **Dialect-portable SQL in `sql.py` modules** with `text()` + named binds; the five habits (COALESCE, CURRENT_TIMESTAMP, CONCAT, OFFSET-FETCH, `dbo.`); `-- PG-CONVERT:` tags; `db.insert_returning_id()` hides SCOPE_IDENTITY vs RETURNING; PG tables created **lowercase** so unquoted identifiers work on both | migration = grep, as the forward-compat standard intended. The KT uplift (item 32) is the first DDL through this rule: `getdate()` defaults → `CURRENT_TIMESTAMP`, `bit` → boolean on PG, lowercase names on PG, every statement `IF NOT EXISTS`-guarded, scripted from the KT catalog and never typed |
| **D-4** | Module layout per domain: `rules.py` (pure) · `sql.py` (text) · `repo.py` (fetch → dicts) · `service.py` (transactions, writes, audit) · `schemas.py` (Pydantic) · `router.py` (FastAPI) · `tests/` | mirrors the Ignition split (planner = rules+data, planner_api = routing); Planner is the reference implementation |
| **D-5** | Identity: JWT (HS256, short-lived access token in an HttpOnly cookie, refresh later) whose `sub` is the legacy `Users.User_Id`; new table `dbo.App_User` (user_id FK, email, argon2 hash, is_active, roles) added by migration; OIDC (Entra ID) via Authlib in phase 2 | the actor for every write is `User_Id`, exactly as Ignition's `workmate.identity.resolve`; `PLANNER_DEV_USER_ID` survives as a dev-only override. **KT's precedent, read 2026-09-13:** `dbo.Ignition_User_Map` — `Ignition_Username nvarchar(100)` UQ → `Workmate_User_ID numeric(18,0)` **FK to `Users.User_Id`**, `Active char(1)`, created/modified stamps — with `identity` 1.1.1 resolving it and self-healing the row (`docs/reference/`). `App_User` should *inherit that shape* (login → `Users.User_Id` FK, `Active`, stamps) rather than carry the table: the SaaS keys on its own logins, not Ignition usernames. Uplift-audit question 5; OD-2 in the Port Spec |
| **D-6** | Serve the built SPA with `app.frontend("/", directory="../web/dist")` — mounted only when `dist/index.html` exists (OD-19); API under `/api/v1/*`; dev = Vite on **3000** (the scaffold's `dev` script; 5173 in 1.0.0/1.0.1 was wrong — log 2026-09-12 1.1.0 §5.6) proxying `/api`, `/docs`, `/openapi.json` to 8000 | single origin, no CORS in prod; `fastapi dev` sets `FASTAPI_ENV=development` so a missing `dist/` is only a warning; the html fallback is `Accept: text/html`-gated (Landmines §A) |
| **D-7** | Scheduled work = Typer CLI commands run by Task Scheduler (Windows) / cron (appliance); in-process APScheduler 3.x only if a client box has no scheduler | Night Shift and nightly proposal keep their shape; one process, one log. KT's `dbo.Module_Settings` (`Is_Enabled`, `Run_Token`/`Run_Started`/`Run_Host` — the scheduled-run lock) is the table shape the CLI jobs inherit (KT Schema Delta §4.1, S5) |
| **D-8** | Diagnostics: request-id middleware + `diag.log()` → stdout JSON + `dbo.Diag_Log`; `/api/v1/_diag/self-test`; browser `window.onerror` → `POST /api/v1/_diag/client` (route not yet built — deferred past S1g, open item 28) | forensic standard preserved; the middleware is scoped to `/api` (Landmines §A). **The persist target now has a contract:** KT's `dbo.Diag_Log` as read 2026-09-13 (KT Schema Delta §4.1) — `Diag_Id int identity` PK · `Logged_At datetime2(3)` · `Session_Id varchar(64)` · `Source varchar(64)` · `Tier char(1)` · `Msg_Level varchar(8)` · `Message nvarchar(1000)`, all **NOT NULL** · `Wm_User_Id int` · `Site_Code varchar(8)` · `Detail nvarchar(max)` · indexes on `Logged_At` and `(Wm_User_Id, Logged_At)`; companions `fn_Diag_UserTrail`, `vw_Diag_Problems`, `vw_Diag_WhoIsOn`. What fills `Session_Id` (request id? JWT `sub`?), `Source`, `Tier` and `Msg_Level` from the `[F]/[G]/[E]` seam is uplift-audit question 4 — persist mode does not ship before it is answered. KT's 69,656 rows are real staff activity incl. email addresses: never copied, never pasted; the SaaS starts empty |
| **D-9** | API conventions: `/api/v1/<module>/<action>`; JSON keys **camelCase exactly as the Ignition contract** (`rangeData` keys unchanged); errors flat `{ok:false, code, message, rid}` app-wide (OD-15) with HTTP 200 for rule refusals that carry a preview (`CONFIRM`), 400 `BAD_WINDOW`, 409 `STALE`, 422 rule refusals, 401/403 identity; OpenAPI tags per module | the existing `Planner_v1_8_1.html` can be pointed at the new API as a parity smoke — the `/range` envelope keeps `ok`, `apiVersion`, `actor`, `ms` for it (OD-14) |
| **D-10** | Tests: pure rules = no DB; repo/service = transaction rolled back; HTTP = `TestClient` with dependency overrides; UI = Vitest; E2E = Playwright against `fastapi dev` + Vite | pair rule enforced in CI |
| **D-11** | Runtime switches stay in `dbo.System_Configuration` (`PLANNER_*` keys) read through one `config_value(key, default)`; deploy config in `.env` via pydantic-settings (`WORKMATE_DB_URL` selects the dialect) | same operational knobs as today; nothing hard-coded |
| **D-12** | Tenancy: one database per client (as today: `dbWorkmate`, `dbWorkmate_Bakels`, `dbWorkmate_QL`); the engine factory takes a tenant → URL map; schema `dbo` kept on PG (`CREATE SCHEMA dbo` + `search_path`) | multi-tenant routing is a header/host → engine lookup later, not a data-model rewrite. **One wrinkle, read 2026-09-13:** KT carries a second schema, `forecast` (the VolumeMatrix module — `shift_matrix`, `month_parameters`, `site_parameters`, `audit_log`, with `CHECK (site IN ('KPP','MLD'))` baked into three tables). It stays KT-specific unless a forecast module ships, and then with the site domain lifted out of the DDL — uplift-audit question 6. D-12's "`dbo` only" holds for the product |

## 5. Repo layout

```
workmate-saas/
├── README.md
├── .gitattributes                 # * text=auto eol=lf
├── .github/workflows/ci.yml       # ruff · pytest · vitest · build · PG-CONVERT grep gate
├── docker-compose.yml             # postgres:18 + adminer (PG track — waits for Docker's first clean start under the cap)
├── scripts/
│   ├── bootstrap-windows.ps1      # ← Azztec_SaaS_Bootstrap_Windows
│   ├── scaffold.ps1               # ← Azztec_SaaS_Scaffold_Repo (fresh clones; its web section is stale — see scaffold-web)
│   ├── scaffold-web.ps1           # ← Azztec_SaaS_Scaffold_Web: web/ only, idempotent, never writes outside web/
│   ├── restore_rst.sql            # RESTORE … WITH MOVE template (dbWorkmate_KT was restored by hand with sqlcmd -E -C, then SET READ_ONLY)
│   └── parity_range.py            # (S6 / open item 26 — unbuilt) /range vs the Ignition planner on dbWorkmate_KT
├── backend/                       # uv project
│   ├── pyproject.toml  uv.lock  .python-version  .env.example  alembic.ini
│   ├── app/
│   │   ├── main.py                # app factory, lifespan, routers, app.frontend()
│   │   ├── core/  config.py  db.py  diag.py  security.py  deps.py
│   │   ├── planner/  rules.py  sql.py  repo.py  service.py  schemas.py  router.py
│   │   ├── planner_ai/  (S5)   planner_chat/  (S5b)
│   │   ├── auth/  router.py  service.py
│   │   └── cli.py                 # typer: `uv run python -m app.cli nightshift | planner nightly` (console script once app is a package)
│   ├── alembic/versions/          # empty — the KT uplift (item 32) and S3's WO_N_Plan are numbered by the uplift audit
│   └── tests/  conftest.py  test_smoke.py  test_planner_rules.py …
├── web/                           # pnpm project (@tanstack/cli create --router-only --toolchain eslint); dev on :3000
│   ├── package.json  pnpm-workspace.yaml (allowBuilds)  vite.config.ts (+proxy, tsconfigPaths, autoCodeSplitting)  vitest.config.ts (no setupFiles, no globals)  openapi-ts.config.ts
│   ├── eslint.config.js  prettier.config.js  tsconfig.json  tsr.config.json  .cta.json   — no components.json: shadcn not installed (OD-31)
│   ├── src/
│   │   ├── main.tsx               # the CLI's file + QueryClientProvider + Query devtools (S1f); builds its own createRouter — router.tsx was dead and is deleted (S1g, 449f19d)
│   │   ├── routeTree.gen.ts       # generated by the router plugin, committed
│   │   ├── styles.css             # the CLI's `@import "tailwindcss"` + resets, untouched; planner.css rides on the route
│   │   ├── routes/  __root.tsx  index.tsx (CTA welcome page — CLI-written, not in PK; a /planner link waits for the file to be pasted, S2)  planner.tsx (thin URL wrapper: mode + anchor search params, OD-29; exports Route only)
│   │   ├── features/planner/  usePlannerRange.ts (S1e, 42-day cap) · rules.ts 1.1.0 (pure, no Date, no DOM — filter precedence, capacity precedence, rank map, dialog/card rows)  store.ts 1.1.0 (cats, selected, railOpen, contractors, loadedOnly, filters, dayOpen)  planner.css 1.1.1 (the oracle's CSS under .wm-planner)  range.fixture.ts 1.1.0
│   │   │                        WOCard.tsx  DayCell.tsx  CapacityBar.tsx (+WeekStrip)  PlannerGrid.tsx  PlannerHeader.tsx  WorkerPanel.tsx  PlannerView.tsx (props-driven whole view + document keyboard) — S1f, patched in S1g
│   │   │                        FiltersRow.tsx  SelectedWOCard.tsx  DayDialog.tsx — S1g, plain components on the oracle's CSS (OD-31); + *.test.tsx (155 in 11 files)
│   │   │                        dnd + ConfirmMoveDialog + UndoToast (S2)
│   │   ├── components/ui/  (shadcn — arrives with the first non-port component, OD-27/OD-31; not present)
│   │   ├── api/  client/ (generated — never edit, never lint; @tanstack/react-query.gen.ts holds the query helpers; its queryFn forwards `signal`, OD-30)
│   │   └── lib/  dates.ts (1.1.0: civilDays/weekStart/parseIso/iso twins + windowFor/navAnchor/todayIso — the only module that touches Date)
│   └── e2e/  planner.spec.ts (S6)
└── docs/                          # compiled knowledge + raw logs (mirror of project knowledge); docs/api/openapi_<ver>.json committed
    ├── Azztec_SaaS_KT_Schema_Delta_v1_0_0.md   # the KT vs RST scope/compare (c4e17f9)
    └── reference/                 # oracle sources extracted from the 2026-09-10 export, 2026-09-13: workmate_pm_engine_code_v2_5_0.py (S2 weekno)
                                   # workmate_identity_code_v1_1_1.py (OD-2 / D-5)  TipBadge_2026-09-10_view.json  TipPopup_2026-09-10_view.json (item 33)
```

## 6. Request flow (Planner `/range`)

0. `routes/planner.tsx` validates `mode` (`week | twoweek | month`, default `month`) and `anchor` (default today) from the URL (OD-29); `windowFor(mode, anchor)` in `lib/dates.ts` derives `from`/`to` — so a link can only name a window the mode can draw, which keeps every request inside the cap. `from`/`to` never appear in the URL.
1. React `usePlannerRange(from,to)` → `checkWindow()` refuses anything over **42 inclusive days before fetching** (OD-23) → the generated `getRangeApiV1PlannerRangeGetOptions({query:{from,to}})` (its key carries the params), `staleTime` 30 s, `refetchInterval` 60 s (`refetchIntervalInBackground: false` — the hidden-tab pause is untested, open item 24).
2. Generated client → `GET /api/v1/planner/range?from=&to=` (never `from_=` — pinned at the wire by `PlannerView.test.tsx`) with the session cookie.
3. Router validates (`from<=to`, ≤ 400 days; `service.WindowError` → 400 `BAD_WINDOW`, OD-16) → `service.range_data()` → `repo.fetch_wos/labour/skill_rows/priorities` (four `text()` selects) → `rules.*` pure assembly → Pydantic `RangeData` response: the Ignition keys plus the flat envelope `ok`, `apiVersion`, `actor`, `ms` (OD-14/OD-15). `priorities[]` is `{id, short, title}` — `Colour` is not on the wire yet (open item 29, now evidenced on both databases: RST's fourteen rows carry a varied `Colour`, KT's four A–D rows all carry `#FF8000` and are coloured by the letter class in CSS).
4. Diag middleware writes `[F] range 2026-09-14..2026-09-20 rows=… labour=… workers=…` with the request id. Healthy: 70–700 ms on RST (singles 0.12–0.65 s measured 2026-09-13); over 2 s is the box (Landmines §F) — **unless the box is clean**, in which case it is open item 30: the same window alternating ~1.2 s / ~8–10 s on the 60 s poll and degrading under concurrency, a backend question for the next audit with DMV wait types as its first evidence. The Ignition planner's own line for the same shape sits in KT's `Diag_Log` — `[F] range … workers=36 pinTable=True in 147 ms` — the oracle's timing for `parity_range.py`.
5. **Cancellation (OD-30, closed 2026-09-13):** the generated `queryFn` forwards TanStack's `signal`, so when the window changes the superseded `/range` query loses its last observer and its fetch **aborts in the browser** — pinned by `PlannerView.test.tsx`. On the server the query **runs to completion** (sync `def` + pyodbc, D-2) and still logs `[F] range …` after the user has clicked away — expected, recorded, not a leak. No nav debounce; pool 5+10 unchanged.

## 7. AI layering (unchanged from `Workmate_AI_Architecture_v1_2.md`)

- Layer 2 (chat surface) = the React chat widget (and Azzmax, only via `POST /ai/chat`).
- Layers 3–8 = `workmate-ai` (FastAPI). Standalone Edition: `app/ai/` router in the same process, tool handlers call the
  same `planner.service` functions the HTTP routes use. `planner_chat.parse()` is the deterministic stand-in the LLM replaces.
- Layer 1 homes: Azure AI Foundry (customer tenant) or the Azztec AI Appliance (vLLM, OpenAI-compatible) — a `LLMClient` config change.

## 8. Version pins (copy into `pyproject.toml` / `package.json`)

Backend (`pyproject.toml`, see `Azztec_SaaS_pyproject_v1_0_0.toml`): `fastapi[standard]>=0.141,<0.142`, `pydantic>=2.11`,
`pydantic-settings>=2.10`, `sqlalchemy>=2.0.52,<2.1`, `pyodbc>=5.3`, `psycopg[binary]>=3.2`, `alembic>=1.16`, `pyjwt>=2.10`,
`pwdlib[argon2]>=0.2`, `httpx>=0.28`, `typer>=0.26`, `tzdata`, `python-multipart`. Dev: `pytest`, `pytest-cov`, `ruff`.

Frontend, on the box after S1f (verified 2026-09-12; unchanged by S1g — no `pnpm add`, OD-31 — and by the 2026-09-13 KT session): `react@19.3`, `react-dom@19.3`, `vite@8`, `@vitejs/plugin-react@6`,
`@tanstack/react-router@1` (+ `router-plugin`, `router-cli`, `react-router-devtools`), `@tanstack/react-query@5` (+ devtools), `tailwindcss@4` + `@tailwindcss/vite`,
`zustand@5`, `zod@4`, `date-fns@4`, `@hey-api/openapi-ts` (dev — the fetch client is bundled, do not add `@hey-api/client-fetch`),
`vitest@5`, `@testing-library/react`, `jsdom`, **`typescript@6`** (OD-28), **`eslint@10`** + `@tanstack/eslint-config`, `prettier@3`.

Planned, not yet installed: `@tanstack/react-table@8`, `@date-fns/tz`, shadcn/ui + `lucide-react` (the first non-port component — OD-31; the tips ⓘ, item 33, is the candidate), `@dnd-kit/core@6` + `@dnd-kit/utilities@3` (S2), `@playwright/test` (S6). Adding any of them is a slice step, recorded in that slice's spec.

Lock files (`uv.lock`, `pnpm-lock.yaml`) are committed. Upgrades are a deliberate slice, never a side effect — TypeScript 7 is the standing example: published, not taken.

## 9. Alternatives considered (so they are not re-litigated)

- **Next.js / SSR** — a plant CMMS is an authenticated SPA; SSR buys nothing and complicates on-prem hosting.
- **SQLModel / full ORM** — 227 legacy tables with `char(n)` keys and stored-proc write paths; Core + `text()` keeps the SQL greppable and dialect-tagged.
- **Async everything** — blocked by pyodbc; revisit at PG-only with `psycopg` async or `asyncpg`. The cost is visible now (OD-30): the server cannot cancel a request the browser has abandoned.
- **Celery/Redis** — no queue workload yet; Typer + Task Scheduler is enough.
- **FullCalendar** — resource-timeline views need the premium licence; the planner grid is custom anyway (as it is in `Planner_v1_8_1.html`, and now in `PlannerGrid.tsx`).
- **Keycloak/Authentik now** — phase 2; the legacy `Users` table is the identity source of truth until then.
- **Carrying KT's Ignition-era tables verbatim** — `Ignition_User_Map` and `Ignition_Onboarding_Prefs` are keyed on Ignition usernames; the SaaS keys on its own logins, so the *shape* crosses (D-5) and the tables do not (KT Schema Delta §4.2). The 25 junk tables, the orphans and the `forecast` schema never cross.

## 10. Changelog

- 1.0.4 (2026-09-13) After the KT-database session (log 2026-09-13 1.1.0 §6), read in full before editing. Status and Verified lines: D-5/D-8/D-12 carry KT evidence for the uplift audit; pins unchanged through the session. §2 diagram names `dbWorkmate_KT`. §3.1: Migrations row names the uplift and the numbering question; tests row says bare + exit code. §3.2: Styling row names the tips ⓘ as the first non-port candidate; Vitest row notes the box-drawn summary. §3.3: new row for the KT oracle copy (read-only, three-part names, no `svc_workmate` user, the one-way door, the two-sided oracle and the delta); DB tooling row gains the `sqlcmd` flag exclusions and the `.bak` service-account rule. §4: D-3 names the uplift as the first DDL through the portability rule; D-5 gains the `Ignition_User_Map` precedent (question 5); D-7 the `Module_Settings` shape; D-8 the `Diag_Log` contract with its NOT NULL columns (question 4) and the never-copy rule; D-12 the `forecast` schema (question 6). §5: `restore_rst.sql` note, `parity_range.py` placed as unbuilt, `alembic/versions/` marked empty pending the numbering decision, `docs/` gains the delta and `docs/reference/`. §6: step 3 notes item 29's both-sides evidence; step 4 the oracle's own `[F] range` timing in KT's `Diag_Log`. §8: unchanged pins re-dated; shadcn candidate named. §9: the KT-tables-verbatim alternative recorded as rejected.
- 1.0.3 (2026-09-13) After S1g (log 2026-09-13 1.0.0 §7). Verified line: pins unchanged through S1g. §3.1 tests row: plain `uv run pytest`. §3.2: TypeScript row notes the TS 6 `lib.dom` narrowing; Query row records OD-30 on the generated `queryFn`; Zustand row → `store.ts` 1.1.0 with filters and `dayOpen`; Styling row → `planner.css` 1.1.1; Components row → shadcn moved from "S1g's day dialog" to "the first non-port component" (OD-31); Vitest row → 155 in 11 files. §3.3: SQL edition and the 8192 MB cap on the Dev DB row; DB tooling leads with `sqlcmd -E -C`; Docker row → cap written, first clean start pending. §4: D-2 and D-8 gain their 2026-09-13 consequences (OD-30, item 28). §5: `router.tsx` line removed; `components.json` recorded as absent; `index.tsx` marked CLI-written/not in PK; the S1g feature files (`rules.ts` 1.1.0, `store.ts` 1.1.0, `planner.css` 1.1.1, `range.fixture.ts` 1.1.0, `FiltersRow`, `SelectedWOCard`, `DayDialog`) placed as shipped; `components/ui/` deferred per OD-31; the generated client's `signal` noted; compose file parked. §6: step 3 notes `Colour` off the wire (item 29); step 4 gains the item-30 caveat; step 5 closed to "aborted in the browser, runs to completion on the server (OD-30)". §8: frontend pins unchanged by S1g; shadcn/lucide re-homed. §9: async line names the OD-30 cost.
- 1.0.2 (2026-09-13) After S1f (log 2026-09-12 1.1.0 §7). §3.2: TypeScript **6.x** settled by OD-28 (was "5.9, open"), TypeScript 7.0.2 published and not taken; ESLint **10** (10.10.0) + Prettier 3.9.6; Vite dev on **3000**; Zustand 5.0.15 / Tailwind 4.3.3 / date-fns 4.4.0 / zod 4.6.1 marked ★ from the box; OD-27 (the port ships the oracle's CSS) and OD-29 (URL = `mode` + `anchor`) recorded on their rows; shadcn, dnd-kit, Table, Playwright marked not installed with the slice that brings each. §3.3 Docker stays off until capped. §4 D-6 corrected to port 3000 and the conditional mount (OD-19); D-8 notes the client diag route is not built. §5 layout is the tree on disk: `main.tsx`/`router.tsx` (dead)/`styles.css`, the S1f feature files, S1g/S2 markers, `components.json` moved to S1g; `http.ts` and `colours.ts` deleted from the plan — never built, the generated client and the payload's `colours` key cover them. §6 flow gains step 0 (URL → `windowFor`), the OD-14/15/16 envelope, and the open cancellation gap. §8 pins split into on-the-box vs planned. §9 FullCalendar line names 1.8.1.
- 1.0.1 (2026-09-12) Status: D-1…D-12 recorded as carried-signed. §3.2 frontend rows re-verified on the box after the S1e scaffold (★): pnpm 12, Vite 8.3, TS 6.0.3, Router 1.170, Query 5.102, hey-api 0.99 with the OD-22 shape, Vitest 5, ESLint 9 + Prettier via the CLI's `eslint` add-on (OD-21). The `create-tsrouter-app` / `eslint+prettier` correction queued since 2026-09-10 §8 finally applied. §5 layout gains `scaffold-web.ps1`, `pnpm-workspace.yaml`, `vitest.config.ts`, `openapi-ts.config.ts`, and marks S1e vs S1f files. §6 step 1 carries the OD-23 cap. §8 pins corrected.
- 1.0.0 (2026-09-10) Initial.
