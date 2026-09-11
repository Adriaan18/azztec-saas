# Azztec SaaS — Raw Log 2026-09-12 (S1e)

**File:** Azztec_SaaS_Raw_Log_2026-09-12_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-12 · **Author:** Adriaan
**Supersedes:** `Azztec_SaaS_Raw_Log_2026-09-11_v1_2_0.md` §8 and §9 (everything else there stands)
**Session:** 2026-09-11 evening → 2026-09-12 morning. S1e audit → five decisions signed → spec → build → web smoke → backend re-run with `dist/` present → commit + tag.
**Status:** append-only ground truth. Corrections go in a later dated log, not by editing this one.
**Goes to:** `docs/raw/` in the repo AND project knowledge.

---

## 1. Decisions signed this session

All five at the S1e audit gate, 2026-09-11. OD-21 is the item that fell out of log 1.1.0 §8 and was restored in 1.2.0 §8.1.

| ID | Decision | Why |
|----|----------|-----|
| **OD-21** | Web toolchain: `@tanstack/cli create web --router-only --toolchain eslint --no-examples --package-manager pnpm --no-git -y`. | `create-tsrouter-app` is deprecated; the `eslint` add-on is "ESLint + Prettier toolchain support" (verified on the box, §5.1). Every compiled doc, CLAUDE.md and the VS Code settings already assume eslint+prettier; biome is a four-doc stack change for nothing at one-dev scale. |
| **OD-22** | Generator: `@hey-api/openapi-ts`, bundled fetch client named as a plugin, `@tanstack/react-query` plugin, **input = the committed `docs/api/openapi_0_3_0.json`**, Prettier-only post-processing. `openapi-typescript` closed as rejected. | Types-only would put a hand-written fetch layer exactly where a `from` regression hides. Committed input makes "regenerate" mean "the contract changed", no backend needed. |
| **OD-23** | Window cap `MAX_WINDOW_DAYS = 42` inclusive, client-side, in `usePlannerRange`; refused windows never fetch. API unchanged. | The oracle decides it: Planner 1.8.1 `windowFor('month')` is at most 6×7 = 42 days. Month worst case ≈ 1.8 MB per 60 s poll. Six-month mode (~27 weeks, ~8 MB) is out of S1 and needs an API summary shape (§8.5). |
| **OD-24** | Workers rail: internal by default, contractors behind a toggle. API unchanged. | Measured: **363 workers = 179 internal + 184 contractors; 46 internal with hours** on the standing window (§5.4). Oracle lists all with contractors tagged; capacity strip is internal-only. Not drawn in S1e; signed now because S1f needs it. |
| **OD-25** | Capacity bar: port the oracle exactly — `width: min(100, pct)%`, class from `barClass(pct)`, tooltip `planned / capacity h (pct%)` degrading to `planned h` at capacity 0. **No 1.0-placeholder heuristic.** | Landmines §E: arithmetic right, input wrong; the fix is the capacity edit (S4), not a rendering rule that hides it. Disposes of 1.2.0 §8.9 at the UI: 74 planned / 0 capacity renders "74 h". |

**Scope cut at the audit gate.** 1.2.0 §9 proposed scaffold + build + client + `PlannerGrid` + `parity_range.py`. `PlannerGrid` and everything that draws → **S1f** (needs OD-23/24/25 signed and the client shipped; one smoke over a toolchain, a generator and a drawn UI is three failure surfaces on one green light). `parity_range.py` stays on the KT copy. **Scaffold_Repo v1.0.2 `-SkipBackend` replaced by a web-only script** — 1.0.1 is not in project knowledge to read, and Scaffold_Repo steps 3–4 `Set-Content` `.gitignore`/`.vscode`/`.claude` outside the `-SkipWeb` guard, so on a live repo the switch would still clobber them.

OD-1, OD-6…OD-20 unchanged. Don't re-litigate.

## 2. Shipped and tagged

| File | Version | Path |
|------|---------|------|
| `Azztec_SaaS_S1e_Web_Chunk_Spec_v1_0_0.md` | 1.0.0 | `docs/` |
| `Azztec_SaaS_Scaffold_Web_v1_0_1.ps1` | 1.0.1 | `scripts/scaffold-web.ps1` |
| `Azztec_SaaS_web_openapi_ts_config_v1_0_1.ts` | 1.0.1 | `web/openapi-ts.config.ts` |
| `Azztec_SaaS_web_eslint_config_v1_0_0.js` | 1.0.0 | `web/eslint.config.js` (the CLI's file + three ignores — **seventh deliverable, not in spec §11**) |
| `Azztec_SaaS_web_lib_dates_v1_0_0.ts` | 1.0.0 | `web/src/lib/dates.ts` |
| `Azztec_SaaS_web_lib_dates_test_v1_0_0.ts` | 1.0.0 | `web/src/lib/dates.test.ts` |
| `Azztec_SaaS_web_usePlannerRange_v1_0_0.ts` | 1.0.0 | `web/src/features/planner/usePlannerRange.ts` |
| `Azztec_SaaS_web_usePlannerRange_test_v1_0_0.tsx` | 1.0.0 | `web/src/features/planner/usePlannerRange.test.tsx` |

Generated on the box and committed, never a card: `web/src/api/client/**` (17 files, openapi-ts 0.99.0 from `openapi_0_3_0.json`), `web/src/routeTree.gen.ts`. CLI-written and committed as-is: `.cta.json`, `.gitignore`, `.vscode/settings.json`, `README.md`, `index.html`, `package.json`, `pnpm-lock.yaml`, `prettier.config.js`, `.prettierignore` (+2 lines by the script), `src/main.tsx`, `src/router.tsx`, `src/routes/__root.tsx`, `src/routes/index.tsx`, `src/styles.css`, `tsconfig.json`, `tsr.config.json`, `vite.config.ts` (+proxy by the script), `vitest.config.ts` (script-written). Written by pnpm: `pnpm-workspace.yaml`.

Commit **`963fcca`**, tag **`s1e-web-1.0.1`** — 44 files, 8,735 insertions. Tag carries 1.0.1: the scaffold and the generator config both patched mid-slice (§4.3, §4.5, §4.6), same reason as `s1c-api-1.0.1` and `s1d-diag-1.1.1`.

No backend source touched. Backend stays at `main.py` 0.3.0 / `diag.py` 1.1.1 / `config.py` 1.1.0 / planner 1.0.1.

## 3. Suite state

**Backend: 125 tests, all green, zero red, zero skips** — re-run with `web/dist/` present (spec §8). `test_root_matches_the_frontend_state` took its `built` branch and passed: `app.frontend()` serves `/` to TestClient's `Accept: */*`. The §8.3 contingency did not fire.

**Frontend: 15 tests, all green** — `dates.test.ts` 7, `usePlannerRange.test.tsx` 8 (the spec said 7; the version/constant check is the eighth). Count from the run. `pnpm lint` silent, `pnpm build` 2.18 s.

Ruff: `24 files left unchanged`, `All checks passed!`.

## 4. Mistakes caught this session

### 4.1 `--router-only` disables `--add-ons` — caught from the docs, before the box

The S0 scaffold's `--add-ons shadcn,tanstack-query` cannot ride with `--router-only` (CLI reference, verified 2026-09-11). Query was added by hand in the script; shadcn deferred to S1f. `--tailwind` is a deprecated compatibility flag now. Nothing was lost because the check was done before writing the command, not after running it — the S0 failure was the reverse.

### 4.2 pnpm 12 blocks build scripts and the CLI template pre-approves them in the wrong place

`pnpm add` succeeded (five packages in) and **then** exited non-zero: `ERR_PNPM_IGNORED_BUILDS: unrs-resolver@1.12.2`. The CTA template puts `pnpm.onlyBuiltDependencies: ["esbuild","lightningcss"]` in `package.json`; pnpm 12 prints "no longer read" on every invocation and ignores it. That is also why the CLI's own `pnpm install` "did not run successfully". Fix was pnpm's own tool: `pnpm approve-builds` wrote `web/pnpm-workspace.yaml` with `allowBuilds: {esbuild, lightningcss, unrs-resolver}` — pnpm 12's shape. Committed. The dead `package.json` field removed by scaffold 1.0.1.

**Lesson:** a non-zero exit after a package manager prints its additions is a policy failure, not an install failure. Read the output before re-running.

### 4.3 hey-api's ESLint post-processor ran the house config over vendor code — 47 errors, failed generation

openapi-ts 0.99.0 generated all 20 files, then `output.lint: 'eslint'` ran `@tanstack/eslint-config` over them: type-parameter naming (`ThrowOnError` must be `TXxx`), `no-unnecessary-condition`, `no-shadow`. Also: `output.format`/`output.lint` are deprecated in 0.99 → `postProcess: [...]`. Fix: config 1.0.1 with `postProcess: ['prettier']` only, and `eslint.config.js` ignores `src/api/client/**`, `src/routeTree.gen.ts`, `dist/**`. Generated code is never edited, so it is never linted. Nothing of ours was in the 47.

### 4.4 My `'from'` grep needed quotes the generator doesn't emit — half a proof

`from_` absent (the important half) but the positive `'from'` pattern matched nothing because the property is bare `from: string;`. Replaced by reading the two type blocks (`RangeData` line 136, `GetRangeApiV1PlannerRangeGetData` line 575 — both `from: string`) and by the wire test. **Third occurrence of the `from` alias closed**: the URL the generated client builds carries `from=2026-09-14`, never `from_=`, pinned by `usePlannerRange.test.tsx` test 6.

### 4.5 Windows PowerShell 5.1 read the BOM-less UTF-8 `.ps1` as ANSI

`§` rendered as `Â§` in scaffold 1.0.0's banner. 1.0.1 is ASCII-only. Rule: `.ps1` files carry no non-ASCII, or carry a BOM.

### 4.6 `vitest.config.ts` imported `./vite.config` without the extension

Vite's native config loader warns and will refuse in a future major. 1.0.1 writes `./vite.config.ts` and patches an existing file.

### 4.7 A fresh shell opened in `C:\windows\system32`

Four commands failed on path before anything ran. No damage — every failure was "cannot find path". Every pasted block now starts with `cd C:\dev\workmate-saas…`.

### 4.8 The `pnpm-workspace.yaml` and `.prettierignore` the CLI wrote covered lockfiles only

`prettier --check .` would have walked `dist/` after the first build. Scaffold 1.0.1 appends `dist` and `src/routeTree.gen.ts`.

## 5. Verified this session

### 5.1 The toolchain (2026-09-12, `@tanstack/cli 0.71.0`)

`--list-add-ons --framework React --json`: two toolchains only, `biome` and `eslint`, both `type: toolchain`, both `file-router`. **No `oxlint`.** `--addon-details eslint`: description "ESLint + Prettier toolchain support"; writes `eslint.config.js`, `prettier.config.js`, `_dot_prettierignore`; adds `@tanstack/eslint-config latest`, `eslint ^9.20.0`, `prettier ^3.8.1`; scripts `lint: eslint`, `format`, `check`. **`eslint@9.39.5` prints an EOL deprecation on install** — Architecture §3.2 says ESLint 10; the add-on pins 9.

The CLI run itself: created `web/`, "Installed dependencies", `tsr generate` (with a cosmetic `replaceRouteChunk` circular-dependency warning), then two errors — `pnpm install` and `pnpm dlx @tanstack/intent install` "did not run successfully" (§4.2). No `AGENTS.md`/`CLAUDE.md` was written under `web/`; the CLI's "wired up" message referred to the failed Intent step.

### 5.2 Versions on the box after the scaffold

node v24.19.0 · pnpm 12.3.4 · react 19.3.0 · @tanstack/react-router 1.170.35 · @tanstack/react-query 5.102.8 · vite 8.3.0 · **typescript 6.0.3** (Architecture pins 5.9.x — the scaffold chose the major) · vitest 5.0.0 · jsdom 30.0.1 · @testing-library/react 16.3.3 · @hey-api/openapi-ts 0.99.0 · date-fns 4.4.0 · @date-fns/tz 1.5.0 · zod 4.6.1 · zustand 5.0.15. Tailwind present in the router-only tree; no duplicate `@tailwindcss/postcss`.

### 5.3 The generated client

20 files under `src/api/client/` (17 `.ts` committed + 3 dirs): `client.gen.ts`, `index.ts`, `sdk.gen.ts`, `types.gen.ts`, `@tanstack/react-query.gen.ts`, `client/{client,index,types,utils}`, `core/{auth,bodySerializer,params,pathSerializer,queryKeySerializer,serverSentEvents,types,utils}`. SDK function `getRangeApiV1PlannerRangeGet` (FastAPI's default operationId — cosmetic, §8.15); query helpers `getRangeApiV1PlannerRangeGetOptions` / `…QueryKey`; types `RangeData`, `GetRangeApiV1PlannerRangeGetData` with `query: { from: string; to: string }`. `index.ts` re-exports the SDK and types; the react-query helpers are imported from `./@tanstack/react-query.gen`.

### 5.4 Worker counts, standing window 2026-09-14..2026-09-20

`workers=363 internal=179 contractors=184`, `internal with hours=46` (from `load`). The input to OD-24.

### 5.5 Web smoke

`pnpm gen:api` → "Running Prettier · 5 files · 97ms" (Prettier's count, not the file count). `pnpm lint` silent. `pnpm test` 15/15. `pnpm build` → `dist/index.html` 0.38 kB, `assets/index-*.js` 297.70 kB (95.43 gzip), `assets/index-*.css` 5.68 kB, 113 modules, 2.18 s. `dist/index.html` 388 bytes at 07:04:07.

### 5.6 Backend with `dist/` present

Boot, in order: `[F] diag wired …` (twice — the known double boot, 1.2.0 §5.1), `[F] startup db=ok dialect=mssql`, `[F] startup tz=Pacific/Auckland`. **`[G] frontend not built` is gone.** Nothing positive replaces it — the mount branch is silent (§8.13).

| Call | Result | Console |
|------|--------|---------|
| `/health` | 200, **`frontend: "built"`**, `diagWired: true`, versions db 1.0.0 / diag 1.1.1 / config 1.1.0 / planner 1.0.1 | `[F] … 200 4ms` |
| `GET /` | **200** `index.html`, 388 bytes, etag, `x-request-id` present | uvicorn access line only — **no diag line** (§8.14) |
| `/api/v1/does-not-exist` | 404 JSON `NOT_FOUND`, flat | `[G] … 404 1ms` |
| same with `Accept: text/html` | **200 `index.html`** — the S7 residual, now real | **`[F] GET /api/v1/does-not-exist 200 5ms`** — an API miss logged as a hit (§8.6) |
| `POST /range` | 405 `METHOD_NOT_ALLOWED` | `[G] … 405 0ms` |

`rid` matches across router and middleware on every request. New cosmetic warning in the suite: anyio `BlockingPortal` alias deprecation, next to the known `httpx2` one.

### 5.7 Commit

`git add -A` staged 44 files; git warned LF→CRLF on `scripts/scaffold-web.ps1` (`.gitattributes` says `*.ps1 eol=crlf`) and CRLF→LF on `web/.prettierignore` and `web/vitest.config.ts` (script-written on Windows). Normalised on commit, warnings only.

## 6. Why the S1e scope was cut

Recorded so it is not re-proposed. `PlannerGrid` → S1f (§1). `parity_range.py` → still the KT copy. Scaffold_Repo 1.0.2 → a web-only script (§1); Scaffold_Repo's own web section is replaced later, for fresh clones, once 1.0.1 is uploaded to project knowledge. shadcn/ui, `@dnd-kit/*`, `lucide-react` deliberately **not installed** — they belong to the slice that draws something; unused deps in the lock file for a slice that cannot exercise them is noise.

## 7. Doc-correction queue

Applied this session: **Index 1.2.0**, **Landmines 1.2.0**, **Ways of Working 1.2.0**, **Architecture 1.0.1** (§3.2 frontend rows, §5 layout, §6 flow, §8 pins). Spec §12 items covered by those.

Still queued, unapplied — carried from 1.2.0 §7, plus new:

- **Port Spec** §2 (`WORKMATE_DEV_USER_ID`), §3 (OD-14 envelope), §6 (S1 splits S1a–**S1f**; `/preview` to S2), §8 (`get_current_actor`), §9 (OD-1…OD-25 dates). Not read in full this project — re-emitting it from grep would be exactly the reconstruction rule forbids. Upload it or accept a partial read next session.
- **Landmines §E:** `Priority.Colour` KT-only (applied 1.1.0? — verify on next read), `WO_C_Activity` empty, triggers PO-only — carried.
- **Install doc / Bootstrap script:** the 2026-09-10 §8 corrections; the web scaffold command line. Not read.
- **`.gitignore`:** `backend/.claude/skills/`, `backend/.agents/skills/` symlinks — carried, unchanged.
- **Scaffold_Repo:** 1.0.1 → project knowledge; then 1.0.2 pointing its web section at `scripts/scaffold-web.ps1`.
- **`web/.vscode/settings.json`** (CLI-written) vs root `.vscode/settings.json` (scaffold-written) — reconcile; one must win.

## 8. Open list

Carried forward in full from 1.2.0 §8; numbering restarts.

1. ~~🤙 the web toolchain~~ **Closed — OD-21, signed 2026-09-11, shipped 2026-09-12.**
2. **KT dev copy** for genuine Ignition parity. `scripts/parity_range.py` blocked on it. S1e claims contract correctness at the wire, not parity.
3. **OD-2 open:** which `Users` rows map to logins. Dev actor `1` (SYS_USER).
4. **Unexplained:** under pytest, `workmate.diag` records still reach a root handler despite `propagate=False` (1.2.0 §4.6). `tests/conftest.py` never reviewed in chat. Blocks nothing.
5. **Six-month planner view** — the oracle's fourth mode, ~27 weeks, ~8 MB per poll at RST scale. Blows through OD-23 by design; needs a summary response shape (`weeks` + `workerWeeks`, no `wos`/`labour`). API change, unsigned. Replaces 1.2.0 §8.5 — the UI half of that item is done.
6. **SPA html-fallback under `/api/` — now observed, and the instrument lies about it.** `GET /api/v1/nope` with `Accept: text/html` returns `index.html` **and the middleware logs `[F] … 200`**. Still S7, with a sharper reason.
7. **Double boot lines** under `fastapi dev` — revisit before migration 0004 sets `PERSIST_SQL`.
8. **Cosmetic:** `[F] diag self-test` logs `actor: 0`. S2 with the real JWT.
9. **Parity oracle, not to fix:** `capacity 0.0` + real planned hours → `pct 0, flag "ok"`. OD-25 renders "74 h" so the UI hides nothing; whether Ignition computes the same still needs the KT copy.
10. `TestClient` `StarletteDeprecationWarning` → `httpx2`; **plus** anyio `BlockingPortal` alias deprecation. Next dependency bump.
11. `.gitignore` symlink fix — carried, unchanged.
12. **Project-knowledge gaps** (Index §3 lists them, project files lack them): `rules_v1_0_0.py`, `sql_v1_0_1.py`, `repo_v1_0_0.py`, `test_planner_rules_v1_0_0.py`, `test_planner_repo_v1_0_1.py`, S1a and S1b chunk specs, raw log 2026-09-11 **1.1.0**, Scaffold_Repo 1.0.1. Superseded still present: `app_main_v1_0_2`, `test_smoke_v1_0_0`, `test_planner_api_v1_0_0`. Blocks the next **backend** audit, not S1f.
13. **The mount branch emits nothing.** With `dist/` present the only boot-time evidence is the absence of `[G] frontend not built`. A `[F] frontend mounted dist=…` line is one statement in the next `main.py` patch.
14. **Diag middleware is scoped to `/api`** — `GET /` produced no diag line while `/api/v1/…` misses do. Looks deliberate; confirm against `main.py` and write it down either way.
15. **operationId cosmetic:** `getRangeApiV1PlannerRangeGet`. A `generate_unique_id_function` is a contract-surface change with its own contract test; only if the names ever matter.
16. **TypeScript 6.0.3 on the box vs 5.9.x pinned.** Compiles clean today. Decide: accept and re-pin, or pin down. Same for ESLint 9 (EOL warning) vs Architecture's 10.
17. **`web/.vscode/settings.json`** vs root — reconcile (§7).
18. **Scaffold_Repo 1.0.1 → PK, then 1.0.2** (§7).

## 9. Next slice

**S1f — `PlannerGrid`, read-only.** Opens with an audit, not a build. What it draws, from the oracle: `windowFor(mode, anchor)` ported into `dates.ts` (1.1.0) for week / twoweek / month — six-month excluded (§8.5); a route `routes/planner.tsx` with `mode`/`anchor` as search params; `PlannerGrid` → `DayCell` → `WOCard` (category dots, priority letter badge, locked/movable state — 2,364 locked PMs on RST is OD-1 working, not a bug); the week capacity strip and `CapacityBar` per OD-25; the workers rail per OD-24. shadcn/ui installed then, not before. **No drag** — `@dnd-kit` and `/move` are S2.

**Carry-ins for the S1f audit:**

1. **OD-24's numbers:** 179 internal is still a long rail. Decide whether "internal with hours" (46) is the default and "all internal" the first toggle — measured, not guessed (§5.4).
2. **Use 2026-06-01..2026-06-07 (12/42/604/658)** for anything needing category variety; the standing window is 273/273 PM.
3. **The rendered 1000%** — OD-25 is signed; the S1f smoke must show a screenshot of it, not a description.
4. **`typescript 6.0.3`** (§8.16) — settle before the first `.tsx` component lands, so the pin is a choice and not a scaffold accident.
5. **shadcn init on a router-only tree** — `--add-ons` was disabled, so `pnpm dlx shadcn@latest init` runs by hand; watch for the duplicate Tailwind dep (Landmines §C).

Also carrying: Ignition parity is still blocked on the KT copy; S1e claims wire-level contract correctness (`from=`, JSON keys, `RangeData` typed end-to-end), not parity.

## 10. Changelog

- 1.0.0 (2026-09-12) S1e shipped and tagged `s1e-web-1.0.1`, HEAD `963fcca`. OD-21…OD-25 signed. `web/` exists: TanStack Router (file-based) + Query, Vite 8, Vitest 5, generated hey-api client from the committed OpenAPI, `dates.ts` twin, `usePlannerRange` with the 42-day cap. 15 frontend tests, 125 backend tests, all green with `dist/` present. `PlannerGrid` cut to S1f. Eight mistakes caught, three of them pnpm/CLI drift the docs had not caught up with.
