# Azztec SaaS — S1e Web Chunk Spec (the web toolchain, the generated client, the capped hook)

**File:** Azztec_SaaS_S1e_Web_Chunk_Spec_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-11 · **Author:** Adriaan
**Status:** Draft — awaiting 🤙 before the build
**Slice:** S1e — `web/` scaffold · generated TS client · `lib/dates.ts` · `usePlannerRange` with the window cap · their Vitest files
**Sits on:** backend at tag `s1d-diag-1.1.1`, HEAD `c2fc624` — `main.py` 0.3.0 · `router.py` 1.0.1 · `schemas.py` 1.0.0 · `diag.py` 1.1.1 · suite 125 green
**Parent spec:** `Azztec_SaaS_Planner_Port_Spec_v1_0_0.md` §6 (S1), §7 (UI) · Architecture D-1, D-6, §3.2 · Ways of Working §3, §4
**Source:** `Azztec_SaaS_Raw_Log_2026-09-11_v1_2_0.md` §8.1 (the restored open item), §9 and its four carry-ins
**Naming:** a/b/c/d/e is the session chunking convention, not a port-spec row (log 1.2.0 §7). S1f is created by this spec's scope cut.

---

## 1. Scope

Frontend only, plus one re-run of the backend suite because `dist/` appearing changes backend behaviour (§8). **Nothing writes to the database.** No route changes, no schema changes, no backend source delivered.

**In:** the scaffold, the toolchain, TanStack Query, Vitest, the generated client from the committed OpenAPI document, the civil-date twin, and the one hook that fetches `/range` behind a hard window cap — each library file with its test file (pair rule).

**Out:**

- **`PlannerGrid`, `DayCell`, `WOCard`, `CapacityBar`, the workers rail, shadcn/ui, dnd-kit → S1f.** Cut at this audit gate. They depend on OD-23/24/25 being signed *and* on the client existing, and one smoke covering a new toolchain, a code generator and a drawn UI is three failure surfaces sharing one green light. §11 records this so it is not re-proposed.
- `scripts/parity_range.py` — blocked on the KT dev copy (log 1.2.0 §8.2), unchanged.
- The six-month planner view — see §6.3. Needs an API change; unsigned; new open item.
- The SPA html-fallback under `/api/` — still **S7**, and §8.3 explains why a built `dist/` does not force it forward now.
- `Azztec_SaaS_Scaffold_Repo` v1.0.2. §5.1 says why a new web-only script ships instead.

## 2. Decisions carried in

| ID | Signed | What it means here |
|----|--------|--------------------|
| D-1 | 2026-09-10 | monorepo; `web/` is a pnpm project beside `backend/`; the generated client lives next to the API that defines it |
| D-6 | 2026-09-10 | SPA served by `app.frontend()` from `web/dist`; API under `/api/v1`; dev = Vite 5173 proxying to 8000 |
| D-9 | 2026-09-10 | camelCase JSON keys exactly as the Ignition contract — the UI layer does not rename either |
| OD-19 | 2026-09-11 | the SPA mount is conditional on `dist/index.html`; this slice is the first time that branch goes the other way |

### 2.1 Decisions signed at this gate (2026-09-11)

Five, all from the S1e audit. OD-21 is the item that was raised 2026-09-10, fell out of log 1.1.0 §8 entirely, and was restored in 1.2.0 §8.1.

**OD-21 — web toolchain: `eslint`, via `@tanstack/cli`.**

```
pnpm dlx @tanstack/cli@latest create web --router-only --toolchain eslint --no-examples --package-manager pnpm --no-git -y
```

- `create-tsrouter-app` is deprecated (log 1.0.0 §8 recorded the deprecation notice from the box itself). `@tanstack/cli` is the live entry point; `tanstack create --router-only` is what its own quick-start publishes for a Router-only SPA. [verified 2026-09-11]
- `eslint` over `biome`: every compiled doc, `CLAUDE.md`, the scaffold's `.vscode/settings.json` and Landmines §C (`.gitattributes` + Prettier `endOfLine: lf`) already assume eslint+prettier. Biome is one tool instead of two and would be defensible on a fresh project; here it is a four-document stack change that buys nothing at one-developer scale. `@hey-api/openapi-ts` post-formats with either.
- **Two flag facts that change the old scaffold line** [verified 2026-09-11 against the TanStack CLI reference]: `--router-only` **disables `--add-ons`, `--deployment` and `--template`**, so `shadcn,tanstack-query` cannot ride along and are installed afterwards; and `--tailwind` is now a deprecated compatibility flag, not a switch.
- **Open fact, resolved by §4 step 1, not by assumption:** the old CLI's toolchain id was `eslint+prettier` and it wrote `eslint.config.js` + `prettier.config.js` + `.prettierignore`; the current CLI advertises the id as `eslint`. Whether that id still brings Prettier is what `--addon-details` answers. If it does not, §5.1 adds Prettier by hand — which is what Architecture §3.2 already specifies anyway.

**OD-22 — generator: `@hey-api/openapi-ts`.** Architecture §3.2 stands; `openapi-typescript` is closed as rejected. It emits types only, so we would hand-write the fetch layer and the query options — more code, and a hand-written layer is exactly where a `from` alias regression hides. Three corrections to the S0 scaffold's `gen:api` line:

1. `@hey-api/client-fetch` as a standalone package is **deprecated — bundled inside `@hey-api/openapi-ts` since 0.73** [verified 2026-09-11]. It is not installed; it is named as a plugin. The old `-c @hey-api/client-fetch` flag goes.
2. Config moves from a CLI one-liner to `web/openapi-ts.config.ts`, because the plugin list is not expressible as flags.
3. **`input` is the committed `docs/api/openapi_0_3_0.json`, not `http://localhost:8000/openapi.json`.** Deterministic, needs no running backend, and it makes "regenerate" mean "the contract changed" rather than "the server was up at the time".

**OD-23 — the window cap: `MAX_WINDOW_DAYS = 42`, client-side, refused before fetch.** The oracle decides this, not a guess: `windowFor()` in `Planner_v1_8_1.html` requests week = 7 days, twoweek = 14, month = `rows*7 - 1` ≤ 42, six-month ≈ 27 weeks. 42 is the widest window the ported UI will ever ask for. Month worst case ≈ 1.8 MB per 60 s poll against 293 KB for a week — fine on a plant LAN, and two orders below the 21 MB the API will still happily serve at 400 days. The 400-day maximum stays an API capability; the API is unchanged.

**OD-24 — the workers rail: internal by default, contractors behind a toggle.** Measured on the standing window 2026-09-14..2026-09-20, this session: **363 workers = 179 internal + 184 contractors, of which 46 internal have attributed hours.** The oracle lists every worker with contractors tagged, and computes the capacity strip from internal only (`capacityWorkers()` filters `internal`). Default to internal; `workerWeeks` is keyed by user id so filtering is a client-side concern. The API stays as-is — log 1.2.0 §8.5 remains open, not closed by this. **No rail is drawn in S1e**; the decision is signed now because S1f needs it signed, and the 179/46 split is a fact worth recording while the server is up.

**OD-25 — capacity rendering: port the oracle exactly, do not tune.** `width: min(100, pct)%`; class from `barClass(pct)` (over > 100, ok ≥ 80, neutral below); tooltip `planned / capacity h (pct%)`, degrading to `planned h` when capacity is 0. So a 1000% worker shows a full bar and an honest 1000% in the label, and the colour comes from the API's own `flag`. **No 1.0-placeholder heuristic.** Landmines §E: the arithmetic is right, the input is wrong, and the real fix is the capacity edit (`POST ./capacity`, S4). A UI that quietly clamps placeholder data hides the thing the site needs to fix. This also disposes of open item 9: a worker with `capacity 0.0` and 74 planned hours renders `74 h`, so nothing is concealed.

## 3. Environment facts this slice depends on

| Thing | Value | Source |
|-------|-------|--------|
| node | v24.19.0 | Index §5, verified 2026-09-11 |
| pnpm | 12.3.4 **on the box**; Architecture §3.2 still says 10.x | Index §5 — doc drift, queued §12 |
| backend | tag `s1d-diag-1.1.1`, HEAD `c2fc624`, suite 125 green | log 1.2.0 §2, §3 |
| OpenAPI document | `docs/api/openapi_0_3_0.json`, generated and committed, never hand-edited | Index §3.7 |
| `frontend_dist` | `../web/dist` relative to `backend/` | `config.py` 1.1.0 |

`web/` does not exist. The S0 scaffold deleted it before the CLI failed (log 1.0.0 §8), so there is nothing to preserve and nothing to merge.

## 4. Build order

Six steps. Steps 1 and 2 are fact-checks that must be pasted before step 3 runs — Ways of Working §5.

1. **Toolchain fact-check.** `pnpm dlx @tanstack/cli@latest create --list-add-ons --framework React --json` and `--addon-details eslint --framework React --json`. Settles: the toolchain add-on ids available to `--router-only`, whether `eslint` brings Prettier, and whether Tailwind is present in a router-only tree. Nothing is assumed from a README.
2. **Scaffold** with `scripts/scaffold-web.ps1` (§5.1), which runs the CLI, adds the libraries, writes the config files, and prints what it did.
3. **Generate the client**: `pnpm gen:api` → `web/src/api/client/**`. Committed, never hand-edited.
4. **`lib/dates.ts` + its tests** (§6.1). Zero network by construction.
5. **`usePlannerRange` + its tests** (§6.2). The cap test must be zero-network and prove it.
6. **`pnpm build`**, then the backend re-run (§8) because `dist/` now exists.

Step 3 cannot run before step 2 and step 6 cannot run before step 5. If step 1 contradicts OD-21's command line, stop and say so — a scaffold flag that does not exist is how S0 lost `web/` in the first place.

## 5. Scripts and config

### 5.1 `scripts/scaffold-web.ps1` 1.0.0 — new, web only

`Azztec_SaaS_Scaffold_Repo` is **not** reissued as v1.0.2 in this slice, for two reasons:

- **1.0.1 is the version on the box and it is not in project knowledge.** Ways of Working §5: never re-emit a file you have not read. Reconstructing 1.0.1 from 1.0.0 plus a log line would silently revert the `Split-Path` fix it carries (log 1.0.0 §8).
- **`-SkipBackend` would not have been safe anyway.** Scaffold_Repo steps 3 and 4 `Set-Content` `.gitignore`, `.vscode/settings.json`, `.claude/settings.json` and `.claude/rules/*.md` unconditionally, outside the `$SkipWeb` guard. Run against a live repo it overwrites all of them, including the `.gitignore` that open item 11 is waiting to fix. A switch that skips the backend does not make the script idempotent against everything else it writes.

`scaffold-web.ps1` therefore touches `web/` only, and is idempotent: it skips the CLI if `web/package.json` exists, skips `pnpm add` for packages already present, and never writes outside `web/`. It prints every action. Scaffold_Repo's web section is replaced for fresh clones in a later slice, once 1.0.1 is in project knowledge to read.

What it does:

1. guard: refuse to run unless `backend/app/main.py` and `docs/api/openapi_0_3_0.json` both exist — wrong-directory protection
2. CLI per OD-21, only when `web/package.json` is absent
3. `pnpm add @tanstack/react-query` — **`--router-only` disables add-ons, so Query is not in the scaffold**
4. `pnpm add date-fns @date-fns/tz zustand zod`
5. `pnpm add -D @hey-api/openapi-ts @tanstack/react-query-devtools vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/dom`
6. patch `vite.config.ts` with the `/api`, `/docs`, `/openapi.json` proxy to 8000 and the Vitest `test` block (`environment: 'jsdom'`), applied with node so the TS stays valid — the S0 pattern, kept
7. `package.json` scripts: `gen:api`, `test`, `lint`
8. check for the duplicate Tailwind deps Landmines §C warns about and **report** them; do not silently remove
9. print `pnpm-lock.yaml` status and the installed versions of node, pnpm, `@hey-api/openapi-ts`

`@dnd-kit/core`, `@dnd-kit/utilities`, `lucide-react` and shadcn/ui are **not** installed here. They belong to the slice that draws something (S1f); installing them now would put unused dependencies in the lock file for a slice that cannot exercise them.

### 5.2 `web/openapi-ts.config.ts` 1.0.0

```ts
input: '../docs/api/openapi_0_3_0.json',
output: { path: 'src/api/client', format: 'prettier', lint: 'eslint' },
plugins: ['@hey-api/client-fetch', '@tanstack/react-query'],
```

`@hey-api/typescript` and `@hey-api/sdk` are defaults and are not listed. The `@tanstack/react-query` plugin emits `…Options()` functions for `useQuery` — §6.2 wraps one rather than hand-writing query options.

**If step 1 reports no Prettier**, `format: 'prettier'` fails and the output is emitted unformatted; drop the key and let ESLint alone handle it. Recorded here so the failure is diagnosed in one step instead of being blamed on the generator.

### 5.3 What the generator is expected to emit, and what is pinned

`from` is a **legal TypeScript property name** — the Python keyword collision does not exist in TS — so the expected shape is `query: { from: string; to: string }`, which is the third occurrence resolving harmlessly. Expected but **not** asserted by inspection: the SDK function name will be FastAPI's default operationId, `getRangeApiV1PlannerRangeGet`. Ugly. Cosmetic. The backend is not touched in this slice to pretty it up; a `generate_unique_id_function` change is a contract-surface change and belongs in its own slice with its own contract test.

The pin is behavioural, not a name match: §6.2's test asserts the URL the client builds carries `from=` and never `from_=`. A generated symbol renaming is a compile error; a silently wrong query string is the failure that would otherwise surface as a 422 a slice later, far from its cause.

## 6. Source files

### 6.1 `web/src/lib/dates.ts` 1.0.0 — the civil-date twin

Port Spec §7: `civilDays`, `weekStart`, `iso`, `addDays`, built on `date-fns` `differenceInCalendarDays` and `startOfWeek({ weekStartsOn: 1 })`. **The only module in `web/` allowed to touch `Date`** (Landmines §C, `.claude/rules/frontend.md`).

Never `new Date("2026-09-18")` — it parses as UTC midnight and lands on the wrong civil day in NZ. `parseISO()` everywhere.

Tests (`dates.test.ts`, zero network, plain values):

1. `civilDays` 2026-09-17 → 2026-09-29 = **12**, and the reverse = **−12**. The DST asymmetry that is a real Ignition bug and must not be reproduced.
2. `civilDays` is symmetric across the 2026-09-27 transition in both directions
3. `weekStart` returns Monday for every day of a week, Monday included
4. `iso` round-trips `yyyy-MM-dd` with no timezone shift
5. `addDays` across the DST boundary keeps the civil day count
6. `parseISO('2026-02-31')` is rejected, matching the backend's calendar-strict `date.fromisoformat` (Landmines §D) — the two halves of the contract agree on what a bad date is

### 6.2 `web/src/features/planner/usePlannerRange.ts` 1.0.0 — the capped hook

Two exports, deliberately split so the cap is testable without React:

```ts
export const MAX_WINDOW_DAYS = 42;                     // OD-23
export function checkWindow(from: string, to: string): WindowCheck   // pure
export function usePlannerRange(from: string, to: string)            // the hook
```

`checkWindow` returns `{ ok: true }` or `{ ok: false, code: 'BAD_WINDOW' | 'WINDOW_TOO_WIDE', message }`, using `civilDays` from §6.1 — inclusive, so `from == to` is 1 day and 42 days is `civilDays === 41`. `BAD_WINDOW` mirrors the backend's own code (`service.WindowError`, router 1.0.1) so the two layers name the same failure the same way.

The hook wraps the generated `…Options()` with: `enabled: checkWindow(...).ok`, `staleTime` 30 s, `refetchInterval` 60 s, `refetchIntervalInBackground: false` (Landmines §C — the 60 s poll pauses in a hidden tab). When the window is refused the query is disabled and the hook returns the `checkWindow` error, so a caller has one error channel, not two.

**Query key:** whatever the `@tanstack/react-query` plugin generates. Landmines §C still specifies a hand-rolled `['planner','range',from,to]` array — that entry predates OD-22 and is now wrong; queued in §12. Not worth overriding the generator to match a doc line.

Tests (`usePlannerRange.test.tsx`):

1–4. `checkWindow`: 7 days ok · 42 days ok · 43 days `WINDOW_TOO_WIDE` · reversed dates `BAD_WINDOW`. Pure, zero network, no React.
5. **The zero-network proof:** with a stubbed `fetch` and a 43-day window, render the hook and assert `fetch` was **not called**. Asserting only the returned error would pass even if the request went out — the Ways of Working §4 lesson, translated: a test that claims zero-network must prove the network was not touched, not merely that the return value looked right.
6. **The `from` pin:** with a stubbed `fetch` and a valid window, assert the requested URL contains `from=2026-09-14` and **does not contain `from_`**. Third occurrence, closed.
7. `refetchIntervalInBackground` is false on the built options.

### 6.3 Not built: the six-month view

The oracle's fourth mode requests ~27 weeks. At RST scale that is roughly 8 MB per poll, every 60 s — it exceeds OD-23 by design, and no client-side cap fixes it. It needs a summary response shape (`weeks` + `workerWeeks` only, no `wos`/`labour`), which is an API change and unsigned. **New open item**, carried into the raw log. Week, twoweek and month all fit under 42 days and are unaffected.

## 7. Repo hygiene

- `web/src/api/client/**` is **committed** — generated, never edited, regenerated on contract change (Landmines §C).
- `routeTree.gen.ts` is **committed** — a missing gen file is the classic "routes not found" on a fresh clone.
- `.gitattributes` already carries `* text=auto eol=lf`; Prettier `endOfLine: "lf"` if Prettier lands in step 1. Otherwise ESLint and git fight on every file on Windows.
- `.gitignore` is **not** edited by this slice. `web/node_modules/` and `web/dist/` are already ignored. Open item 11 (the `.claude/skills` symlinks) stays open and is not smuggled in here.

## 8. What changes on the backend when `dist/` appears

No backend file is delivered. Behaviour still changes, and the slice is not done until the backend suite is re-run with `dist/` present.

1. **Boot:** `[G] frontend not built dist=…` stops appearing; the mount branch flips (`main.py` 0.3.0 §5.2). The pre-state is on record in log 1.2.0 §5.
2. **`/health`:** `frontend` goes `"missing"` → `"built"`.
3. **`test_root_matches_the_frontend_state`** (test_smoke 1.1.0) asserts the *coupling*, so it was written to survive this: with `frontend == "built"` it requires `GET /` → 200. If `app.frontend()` declines TestClient's `Accept: */*` on `/`, that test reds. **If it does, the test's assumption is the thing that is wrong, not the mount** (Ways of Working §7) — patch the test in this slice, at a patch bump, and record why.
4. `test_api_404_is_json_not_spa` sends `Accept: */*` and must stay green — the S7 html-fallback residual (log 1.2.0 §8.6) is exactly about `text/html`, and a built `dist/` does not force it forward. Confirm, do not fix.

## 9. Smoke (paste verbatim)

Fact-check first:

```powershell
cd C:\dev\workmate-saas
pnpm dlx @tanstack/cli@latest create --list-add-ons --framework React --json
pnpm dlx @tanstack/cli@latest create --addon-details eslint --framework React --json
```

Then:

```powershell
.\scripts\scaffold-web.ps1
cd web
pnpm gen:api
Get-ChildItem src\api\client
Select-String -Path src\api\client\*.ts -Pattern "from_" ; Select-String -Path src\api\client\*.ts -Pattern "'from'"
pnpm lint
pnpm test
pnpm build
Get-ChildItem dist\index.html | Select-Object Name, Length, LastWriteTime
```

The `Select-String` pair is the generator's answer on the `from` alias, in one line, before any test interprets it. Expect a hit on `from` and nothing on `from_`.

Then the backend, because `dist/` now exists:

```powershell
cd ..\backend
uv run ruff format . ; uv run ruff check .
uv run pytest -q
uv run fastapi dev app/main.py
```

and in a second terminal:

```powershell
curl.exe "http://localhost:8000/api/v1/health"
curl.exe -i "http://localhost:8000/"
curl.exe -i "http://localhost:8000/api/v1/does-not-exist"
```

**Paste the dev-server terminal too.** The absence of `[G] frontend not built` is a deliverable of this slice, and an absence is only evidence if the whole boot sequence is visible.

Ordering law, unchanged: `ruff format` → `ruff check` → `pytest`. The format step is load-bearing (log 1.2.0 §4.4).

## 10. Acceptance

- `web/` exists; `pnpm build` writes `web/dist/index.html`.
- `pnpm gen:api` emits `src/api/client/**` from the committed OpenAPI document, with no backend running; output committed, unedited.
- The generated client issues `from=`, never `from_=` — proved by the grep **and** by §6.2 test 6.
- `pnpm test` green, including the DST ±12 pair and the zero-network cap proof.
- A 43-day window is refused client-side with no request made.
- Backend suite still green with `dist/` present — expect **125**, counted from the run, never from this spec (log 1.2.0 §3).
- `/health` reports `frontend: "built"`; `[G] frontend not built` gone from boot; `/api/v1/does-not-exist` still JSON 404; `POST /api/v1/planner/range` still 405.

No parity claim. Ignition parity still needs the KT dev copy and still gates S1 acceptance, not this build.

## 11. Deliverables (one Download card each, on 🤙)

| # | File | Version | Target | PK |
|---|------|---------|--------|-----|
| 1 | `Azztec_SaaS_Scaffold_Web_v1_0_0.ps1` | 1.0.0 | `scripts/scaffold-web.ps1` | add |
| 2 | `Azztec_SaaS_web_openapi_ts_config_v1_0_0.ts` | 1.0.0 | `web/openapi-ts.config.ts` | add |
| 3 | `Azztec_SaaS_web_lib_dates_v1_0_0.ts` | 1.0.0 | `web/src/lib/dates.ts` | add |
| 4 | `Azztec_SaaS_web_lib_dates_test_v1_0_0.ts` | 1.0.0 | `web/src/lib/dates.test.ts` | add |
| 5 | `Azztec_SaaS_web_usePlannerRange_v1_0_0.ts` | 1.0.0 | `web/src/features/planner/usePlannerRange.ts` | add |
| 6 | `Azztec_SaaS_web_usePlannerRange_test_v1_0_0.tsx` | 1.0.0 | `web/src/features/planner/usePlannerRange.test.tsx` | add |

Every TS file carries `export const VERSION = "X.Y.Z"` and the header block (Ways of Working §2). The generated client is **not** a Download card — it is generated on the box and committed.

Tag the version that ships, not the one this spec predicts: `s1e-web-<shipped>`. Commit message `web scaffold + client + capped hook — S1e`.

Mark-of-the-Web: `Unblock-File` after the drop, then check `Length` and `LastWriteTime` on the **target**, matching by wildcard and newest mtime — a re-downloaded card arrives with a browser `(n)` suffix.

## 12. Doc corrections this slice queues

- **Architecture §3.2:** `create-tsrouter-app` → `@tanstack/cli create --router-only`; `--toolchain eslint+prettier` → `eslint`; `--router-only` disables `--add-ons`; `--tailwind` deprecated. The 2026-09-10 §8 correction, finally actionable.
- **Architecture §3.2:** pnpm pin says 10.x; the box runs 12.3.4.
- **Architecture §3.2 / Landmines §C:** `@hey-api/client-fetch` is bundled into `@hey-api/openapi-ts` since 0.73 — named as a plugin, not installed, no `-c` flag.
- **Landmines §C:** the TanStack Query key entry (`['planner','range',from,to]`) predates OD-22; the generated plugin owns the key shape now.
- **Landmines §C:** new entry — a client-side window cap belongs in the hook, with the number taken from the oracle's own `windowFor()`, not invented.
- **Install doc §7:** the scaffold command line, and the 2026-09-10 §8 corrections still unapplied.
- **Port Spec §6:** S1 splits S1a–S1f now, not S1a–S1e.
- Everything queued in log 1.2.0 §7 is unchanged and unapplied.

## 13. Changelog

- 1.0.0 (2026-09-11) Initial. OD-21…OD-25 signed at the audit gate, OD-21 being the item restored to the open list in log 1.2.0 §8.1 after falling out of 1.1.0. Scope cut: `PlannerGrid` and everything that draws → S1f. Scaffold_Repo v1.0.2 replaced by a web-only script, with the reason recorded. Six-month view raised as a new open item.
