# Azztec SaaS — Platform Landmines

**File:** Azztec_SaaS_Platform_Landmines_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-10 · **Author:** Adriaan
**Status:** Active. One lesson per line; verified date in brackets; platform claims older than a major version bump get re-verified.
**Lineage:** the Ignition-era `Workmate_Knowledge_Journal` / `Workmate_Perspective_Rules` landmines that still bite are carried in §E.

---

## A. Python / FastAPI

- **Never do DB I/O inside `async def`.** pyodbc is synchronous; a blocking call in an `async def` route stalls the whole event loop. Use plain `def` routes (FastAPI runs them in anyio's threadpool, default 40 threads) or `run_in_threadpool`. Async comes back only at PG-only with `psycopg` async. [2026-09-10]
- **Dependencies with `yield` and BackgroundTasks:** the post-`yield` lifecycle has changed across releases (0.106, later 0.118-era refinements). Rule: a background task opens its **own** connection; never reuse the request's yielded session in a task. [2026-09-10]
- **FastAPI 0.137.0 refactored routers** — `router.routes` is now a tree of intermediate objects, not a flat list. Anything that iterates `router.routes` (custom OpenAPI hacks, route listing) breaks. Use `app.openapi()` or `iter_route_contexts()` instead. [2026-09-10]
- **`app.frontend()` fallback** serves `index.html` only for `GET`/`HEAD` with `Accept: text/html`; missing JS/CSS still 404; `POST` to an SPA path is 404. Keep the API under `/api/v1` so SPA routes never collide with path operations (path operations always win anyway). `check_dir="auto"` errors on a missing `dist/` unless `FASTAPI_ENV=development` (`fastapi dev` sets it). [2026-09-10]
- **`fastapi[standard]` pulls in `fastapi-cloud-cli`**; use `fastapi[standard-no-fastapi-cloud-cli]` if you don't want the `fastapi login/deploy` commands. [2026-09-10]
- **Pydantic v2 serialises `Decimal` as a JSON string.** MSSQL `numeric` columns arrive as `Decimal` from pyodbc → the planner contract expects numbers → coerce with the `_i()`/`_f()` twins in the row mapper before building models, or declare fields `float`. [2026-09-10]
- **Naive datetimes.** MSSQL `datetime` comes back naive; the contract wants `yyyy-MM-dd` strings (`iso()`) and `HH:mm` (`timeOf()`). Format explicitly in the mapper; never let Pydantic emit `2026-09-18T00:00:00`. [2026-09-10]
- **Windows has no tz database.** `ZoneInfo("Pacific/Auckland")` raises `ZoneInfoNotFoundError` unless the `tzdata` wheel is installed. It is in the pyproject; don't remove it. [2026-09-10]
- **DST day arithmetic:** the Ignition bug (`system.date.daysBetween` asymmetric across 27 Sep 2026) is reproducible in Python if you subtract aware datetimes. `civil_days()` = `(date_b - date_a).days` on `datetime.date` objects only. Test 17→29 Sep = 12 and 29→17 Sep = −12. [2026-09-10]
- **`round()` is banker's rounding in Python 3** (`round(2.5) == 2`); Jython 2.7 rounded half away from zero. `pct = int(round(100.0 * planned / capacity))` can differ by 1 at exact .5 — decide (D: keep Python 3 semantics, note in parity test). [2026-09-10]
- **uv on Windows:** install via the standalone installer or winget, then open a **new** terminal (PATH). `uv run` always uses the project venv — never `pip install` into it by hand. `uvx` = `uv tool run`. [2026-09-10]
- **`uv` defaults new interpreters to 3.14** now; this project pins `.python-version` = 3.13 until wheels are verified. [2026-09-10]
- **Delivered `.py` files no longer pass through a markdown renderer** (that was the Ignition Script Console path) — bare URLs and backslashes are safe again. But files are still delivered as raw source, never inline. [2026-09-10]

## B. SQLAlchemy / pyodbc / MSSQL / PostgreSQL

- **ODBC Driver 18 defaults to `Encrypt=yes`** and rejects the local instance's self-signed certificate: `SSL Provider: The certificate chain was issued by an authority that is not trusted`. Dev fix: `TrustServerCertificate=yes` in the connection string (already in `.env.example`). Prod: a real cert or `Encrypt=strict` with a trusted CA. [2026-09-10]
- **URL-encode the ODBC string:** build with `urllib.parse.quote_plus(...)` and `mssql+pyodbc:///?odbc_connect=…`. A raw `Driver={ODBC Driver 18 for SQL Server}` in the URL breaks on the braces/spaces. `db.py` does this. [2026-09-10]
- **Double pooling:** pyodbc pools connections itself; SQLAlchemy pools too. Set `pyodbc.pooling = False` **before** `create_engine` (SQLAlchemy's own recommendation for the mssql dialect). `db.py` does this. [2026-09-10]
- **`fast_executemany=True`** on the engine for bulk inserts; `pool_pre_ping=True` to survive idle-connection drops. [2026-09-10]
- **`char(n)` padding:** every legacy `char` column (`Short_WO_Id char(25)`, `Status char(1)`, `WO_Title char(70)`, `Users.Active char(1)`…) comes back space-padded. `RTRIM()` in SQL as the Ignition code does **and** `.strip()` in the mapper; compare with `RTRIM(x) = 'Y'`, never `x = 'Y'` unless you know the column is `varchar`. [2026-09-10]
- **`:name` in a SQL comment is a bind parameter** for SQLAlchemy `text()` too (regex-based, comments are not stripped) — the Ignition COLON-IN-COMMENT landmine survives. No colons in SQL comments; escape a literal colon as `\:`. [2026-09-10]
- **`OFFSET … FETCH` needs `ORDER BY`** on MSSQL. `TOP 1` in correlated subqueries (the pin select) is MSSQL-only → `-- PG-CONVERT: TOP 1 -> LIMIT 1`. [2026-09-10]
- **`SCOPE_IDENTITY()` vs `RETURNING`:** never write either in module SQL; call `db.insert_returning_id(conn, sql, params)`. Avoid `OUTPUT INSERTED.*` — it fails on tables with triggers, and a 20-year-old DB has triggers. [2026-09-10]
- **MSSQL `datetime` precision is 3.33 ms** and `Request_Start_Date` carries a time of day on ~half the rows (probed at KT 2026-09-04; re-probe on RST). Key days on the DATE part; shift datetimes with wall-clock `timedelta(days=n)` (DST-safe because naive). [2026-09-10]
- **Legacy stored procedures return row counts** that confuse `fetchall()`; when calling a `wmsp_*` proc prefix `SET NOCOUNT ON;` in the same batch. Prefer plain SQL over procs except where the .NET write path is the contract (`wmsp_WO_N_HeaderInsertUpdate`). [2026-09-10]
- **Windows auth vs SQL auth:** `Trusted_Connection=yes` only works in-process as the logged-in Windows user. Services and Docker use the SQL login `svc_workmate`. [2026-09-10]
- **Alembic vs legacy schema:** never `alembic revision --autogenerate` against the 227 legacy tables (it will try to "fix" them). Migrations are hand-written and only create Workmate-added tables; `version_table_schema="dbo"`. [2026-09-10]
- **PostgreSQL folds unquoted identifiers to lowercase.** `SELECT WO_ID FROM dbo.WO_N_Header` works on PG only if the table was created lowercase (`wo_n_header`, `wo_id`) and the SQL never quotes identifiers. Rule (D-3): PG DDL is lowercase; SQL stays unquoted and mixed-case as today → portable without edits. [2026-09-10]
- **Booleans:** legacy `'Y'/'N'` and `'1'/'0'` char flags are data values; they migrate unchanged; never "fix" them in flight. [2026-09-10]
- **SQLAlchemy 2.1 is rc1** (2026-08-31); the `mssql+mssqlpython` dialect and `greenlet`-optional asyncio land there. Pin `<2.1` until final, then a deliberate upgrade slice. [2026-09-10]

## C. React / Vite / TypeScript

- **`new Date("2026-09-18")` parses as UTC midnight** → NZ shows 17 Sep 12:00 after 27 Sep? No — it shows the wrong calendar day in negative-offset zones and the wrong hour in NZ. Always `parseISO()` / `differenceInCalendarDays()` from date-fns; never do day math on `Date` objects across the 27 Sep 2026 DST change. `lib/dates.ts` is the only place that touches `Date`. [2026-09-10]
- **Vite env vars must be `VITE_`-prefixed** to reach the browser (`import.meta.env.VITE_API_BASE`). [2026-09-10]
- **Vite 8 = Rolldown.** `@vitejs/plugin-react` 6 dropped Babel; Vite ≤7 is unsupported by it. Plugins that shipped Babel transforms need their Oxc/Rolldown equivalents. [2026-09-10]
- **React 19:** `ref` is a plain prop (`forwardRef` deprecated); StrictMode double-invokes effects in dev — a naive `setInterval` poll fires twice; use TanStack Query `refetchInterval` instead of hand-rolled polling. React Compiler is opt-in through the plugin preset; don't hand-memoise around it. [2026-09-10]
- **React 19.3** (2026-09-09): View Transitions and Fragment refs are stable; useful for the drag/drop card animation later — not in S1. [2026-09-10]
- **TanStack Router file routes** generate `src/routeTree.gen.ts`; the Vite plugin regenerates it on dev/build. Commit it (or generate in CI) — a missing gen file is the classic "routes not found" on a fresh clone. [2026-09-10]
- **TanStack Query:** array query keys (`['planner','range',from,to]`); `staleTime` > 0 or every mount refetches; `refetchIntervalInBackground: false` to pause the 60 s poll in hidden tabs; optimistic update + rollback in `onMutate/onError` for the drag move; `invalidateQueries` on success. [2026-09-10]
- **Tailwind v4 is CSS-first:** `@import "tailwindcss";` + `@theme {}` in `index.css`; no `tailwind.config.js` by default; dark mode via `@custom-variant dark`. shadcn/ui components assume v4 (`components.json` "style"). The scaffold's `--tailwind` + `--add-ons shadcn` has produced duplicate Tailwind deps in the past — check `package.json` for both `@tailwindcss/vite` and `@tailwindcss/postcss` and keep only `@tailwindcss/vite`. [2026-09-10]
- **shadcn/ui is copied source**, not a dependency. Updating a component = re-running `pnpm dlx shadcn@latest add <name>` and diffing. [2026-09-10]
- **dnd-kit:** wrap the grid in one `DndContext`; `PointerSensor` with `activationConstraint: {distance: 6}` so a click still opens the WO card; one `useDroppable` per day cell with the ISO date as id; `useDraggable` per WO with `wo-<id>`; `DragOverlay` for the moving card; `pointerWithin` collision for grid cells. Classic `@dnd-kit/core` v6 is the stable line; `@dnd-kit/react` 0.5 is the rewrite — later. [2026-09-10]
- **Generated API client** (`@hey-api/openapi-ts`) is never hand-edited; `pnpm gen:api` after every backend contract change; commit the output. [2026-09-10]
- **Node 24 vs 26:** stay on 24 LTS until 26 enters LTS (2026-10-28). Corepack is no longer bundled with newer Node lines → install pnpm with winget (`pnpm.pnpm`) or `npm i -g pnpm`, not `corepack enable`. [2026-09-10]
- **Windows line endings:** `.gitattributes` with `* text=auto eol=lf`, Prettier `endOfLine: "lf"`; otherwise ESLint/Prettier fight on every file. [2026-09-10]

## D. Jython 2.7 → Python 3.13 translation traps (porting `workmate.planner*`)

- **Integer division:** Jython `/` on two ints is floor division. Every `/` in the source was audited to use floats explicitly (`float(dayOfYear - num4) / 7.0`) — keep the `float()`, or use `//` where floor is intended. [2026-09-10]
- **`round()` semantics** differ (§A). [2026-09-10]
- **`isinstance(v, str)` no longer lies** — DB strings are `str`, not `unicode`; `basestring` is gone. The `'%s' % v` coercion habit can stay (`_s()`). [2026-09-10]
- **`except:` bare** → `except Exception:`; NQ errors as `java.lang.Exception` are gone; SQLAlchemy raises `sqlalchemy.exc.*` (walk `e.orig` for the pyodbc error, `e.orig.args[1]` has the SQL Server message — the `_err()` twin). [2026-09-10]
- **`system.date.*` → `datetime`/`date`/`zoneinfo`**: `addDays` → `+ timedelta(days=n)`; `isAfter` → `>`; `format(d,'yyyy-MM-dd')` → `d.strftime('%Y-%m-%d')`; `getDayOfYear` → `d.timetuple().tm_yday`; `.NET DayOfWeek` (Sunday=0) → `(d.weekday() + 1) % 7`. [2026-09-10]
- **`system.db.runPrepQuery(sql, params)` → `conn.execute(text(sql), {name: value})`** with named binds; the `?` positional style becomes `:from_d`/`:to_d`. `_rows(ds, cols)` → `[dict(r) for r in result.mappings()]`. [2026-09-10]
- **`system.db.beginTransaction`** → `with engine.begin() as conn:`; the `_tx=None` "caller-owned transaction" pattern becomes a `conn` parameter (tests pass a rolled-back connection). [2026-09-10]
- **Tabs → 4 spaces** (Ruff reformats); keep the function names and dict keys identical so the parity tests map 1:1. [2026-09-10]
- **`dict.items()` sorting** with `key=lambda kv: (-kv[1], kv[0])` still works; `cmp=` does not exist. `sorted(set(...), reverse=…)` fine. [2026-09-10]
- **Module globals as caches** (`_hoursUom`, `_ENGINE_FROZEN`) — fine in one process; with multiple uvicorn workers each worker caches independently (harmless for read-only lookups). [2026-09-10]
- **Gateway-side session dict with 2 h TTL** (planner_chat context) → per-process dict is fine for one worker; multi-worker needs a table or Redis — not in phase 1. [2026-09-10]

## E. Legacy Workmate data truths (carried over — verify on RST before relying)

- WO status codes: R=Request, H=Planned, P=Pending, K=Acknowledged, A=Approved, V=Active, C=Closed, D=Cancelled, F=Deferred; Open = NOT IN ('C','D'). Planner: locked = C/D, confirm = V, engine-frozen = V/C/D.
- PO status codes: P Pending, W Waiting, A Approved, I Issued, R Received, T Part Received, C Completed, X Exported, Q RFQ, D Cancelled.
- `WO_N_Header` (uppercase H): `WO_ID`, `Status`, `Request_Start_Date`/`Request_End_Date` (datetime — full-day span), `Week_No` (numeric `YYYY.WW`), `WO_Type_Flag` ('M' = PM), `Purchase_Order_Flag`; `Priority_Id`, `Progress_Id`, `Duration_In_Hours`, `User_ID_Responsibility` live on `WO_N_Details`; no `User_Id_Assigned` on the header; write proc `wmsp_WO_N_HeaderInsertUpdate`.
- `WO_Status` owns the WO_ID sequence and gates the header — companion row first.
- Completed PMs archive to `WO_C_*`, not `WO_N_*`; labour history = `Trx_Type 'L'` rows in `WO_N_Activity` ∪ `WO_C_Activity`.
- Progress FK rejects 0: None=1, Wait=2, 25%=3, 50%=4, 75%=5, 100%=6.
- `Asset` uses `Direct_Location`, not `Location_Id`.
- `Week_No` is the .NET algorithm (`_netWeekNoAndYear`: Sunday=0 weekday, 8-num2 offset, 53-week rule) — port it exactly, unit-test against known KT values.
- Active domains: `Users.Active` 'Y'/'N'; `User_Skill.Active` '1'/'0' — exclude both '0' and 'N'. Assignable worker = active user with ≥ 1 active skill row.
- `Priority.Colour` is `#FF8000` on every row → priority is a LETTER badge (`Short_Priority_Id`).
- Internal team = modal supplier among active skill rows OR `Supplier.Internal_Dept IN ('1','Y')` — never a hard-coded supplier id (KT's happened to be 11).
- Labour UOM = `Unit_of_Measure.LRStd = 'Y'` row resolved at runtime — never a hard-coded 9.
- `WO_N_Resource` labour row: `Resource_Type 'L'`, `Res_Id = MAX+1 in-tx`, `Res_Date` = the legacy "User Planned Date", `Supplier_Id` from the person's skill row, `Planned_Qty` hours, `Planned_Unit_Cost` rate.
- `WO_Event_History.event_details` is varchar(1000) → cap at 990; `Source_Form 'Planner'`, `server_name 'Perspective'` today → decide `'SaaS'` (OD-3 in the port spec).
- `System_Configuration` (`System_ConfigCol char(40)`, `System_ConfigVal char(255)`) holds the `PLANNER_*` switches — RTRIM both.

## F. Changelog

- 1.0.0 (2026-09-10) Initial.
