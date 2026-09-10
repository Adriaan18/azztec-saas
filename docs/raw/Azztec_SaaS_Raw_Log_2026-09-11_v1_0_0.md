# Azztec SaaS — Raw Log 2026-09-11

**File:** Azztec_SaaS_Raw_Log_2026-09-11_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-11 · **Author:** Adriaan
**Session:** S1a (planner rules) and S1b (planner sql + repo) — first two code chunks of the Planner port
**Status:** append-only ground truth. Corrections go in a later dated log, not by editing this one.
**Supersedes:** nothing. Continues `Azztec_SaaS_Raw_Log_2026-09-10_v1_0_0.md`; that log's §9 open list is updated in §8 below.
**Goes to:** `docs/raw/` in the repo AND project knowledge.

---

## 1. Decisions signed this session (🤙)

- **S1 split 🤙** Port spec §6 listed S1 as one slice (rules + sql + repo + service + schemas + router + the whole React
  grid) — four pair-rule boundaries that cannot smoke as a unit. Split: **S1a** rules · **S1b** sql+repo · **S1c**
  service+schemas+router(`/range`) · **S1d** `/preview` (folded into S2, see OD-13) · **S1e** React. S1a and S1b shipped.
- **OD-7 🤙 (raised open 2026-09-10)** The six `PLANNER_*` keys are not one kind of thing. The four operational knobs
  (`PLANNER_AUTOPILOT`, `_MAX_MOVES`, `_MAX_WEEKS`, `PLANNER_NIGHTLY_WEEKS`) **stay table-with-code-defaults — no seed, no
  migration, nothing written to RST**; `config_value(key, default)` already falls through, which is what D-11 intends.
  `PLANNER_DEV_USER_ID` is not a knob but dev deploy config pointing at one `Users` row in one database, so it moves to
  `.env` as **`WORKMATE_DEV_USER_ID`** alongside the DB password. `PLANNER_AUTOPILOT_USER_ID` stays in the table and is
  decided in S5 when autopilot is actually built. Consequence: port spec §2's mapping row needs a dated correction.
- **OD-8 🤙** `round()` keeps Python 3 half-to-even (Jython rounded half away from zero). Exposure is ≤1 on `pct` values;
  `counts` — the S1 parity oracle — cannot be touched by rounding. Pinned as `test_od8_rounding_documented`: capacity 8.0 /
  planned 1.0 gives **12 here, 13 in Ignition 1.3.1**. Documented, not patched.
- **OD-9 🤙** `labourRules` returns `resDate` as a `datetime.date`, 1:1 with the source. The S4 service formats it. No
  `resDateIso` twin — one shape, one source of truth.
- **OD-10 🤙** `rules.py` starts a new version lineage at **1.0.0** with `PORTED_FROM = "workmate.planner 1.3.1"`. The
  contract's `libVersion` reports `__version__`. The S6 port of `t_versions` asserts `PORTED_FROM`, not `>= '1.3.1'`.
- **OD-11 🤙** `UOM_MODAL` gains the `, UOM_Id` tie-break the Ignition source lacked (src 547 was
  `GROUP BY UOM_Id ORDER BY COUNT(*) DESC` with no second key, and the answer is cached for the process lifetime). Latent
  on RST — `LRStd` resolves cleanly — but real on any database without an `LRStd` row. Same fix `_PRIORITY_SQL` carries.
- **OD-12 🤙** `app/auth/` (D-5: JWT, `App_User`, argon2) appears in **no slice S0–S7** — a spec gap, not an oversight in
  the build. S1c ships `deps.get_current_actor()` returning the dev user id when `WORKMATE_ENV=dev` and 401 otherwise; one
  seam, swapped for the real JWT dependency in S2. `/range` is read-only so this is not yet a security decision.
- **OD-13 🤙** `loadWO`, `movePreview` and `GET /preview` move out of S1 and into **S2**. `loadWO` returns `startDate`,
  `endDate` and `engineDateValue` as raw `datetime` objects for the S2 writer to shift — non-JSON-safe values with no
  consumer in a read-only slice.
- OD-2, OD-3, OD-4, OD-5 — still open. None block S1c.

## 2. What shipped

| Chunk | Files | Tests | Commit / tag |
|-------|-------|-------|--------------|
| **S1a** | `app/planner/rules.py` 1.0.0 · `tests/test_planner_rules.py` 1.0.0 | 44 pass | `e26a89f` · `s1a-rules-1.0.0` |
| **S1b** | `app/planner/sql.py` 1.0.1 · `app/planner/repo.py` 1.0.0 · `tests/test_planner_repo.py` 1.0.1 | 33 pass | `6bd4319` · `s1b-data-1.0.0` |

Specs written first, both gated: `Azztec_SaaS_S1a_Rules_Chunk_Spec_v1_0_0.md`, `Azztec_SaaS_S1b_Data_Chunk_Spec_v1_0_0.md`.

Full-suite state observed at 07:41 (before the 1.0.1 patches): **79 tests, 78 passed, 1 failed**. The repo file has since
gained one test, so the expected full run is 80 / 79 passed / 1 failed. The one red is
`test_api_404_is_json_not_spa`, carried from 2026-09-10 §7 and still gated on the missing web app.

## 3. Environment and tooling facts (this box, verified)

- **The `web\dist` failure is an HTTP 500, not a 404.** The `[E]` diag line names it exactly:
  `RuntimeError("StaticFiles directory 'C:\dev\workmate-saas\web\dist' does not exist.")`. The 2026-09-10 §7 note that
  `main.py` 1.0.0 has no explicit API 404 handler is now **observed rather than suspected**: an `/api/...` miss depends on
  the SPA mount being healthy. Clears with `pnpm build`, but the handler is a real robustness gap.
- **`git add -A` from the repo root committed the FastAPI skill symlinks** — `backend/.claude/skills/fastapi` and
  `backend/.agents/skills/fastapi`, both `mode 120000`, both pointing into the gitignored `.venv`. A fresh clone gets
  dangling links, and Windows needs `core.symlinks=true` to materialise them at all. They belong in `.gitignore`, not the
  repo. Not yet fixed.
- Git author on this box: `AzztecEnterprise <azztecdev@gmail.com>`.
- Download cards land at `%USERPROFILE%\Downloads\` under the exact versioned filename — no renaming by the browser.
- Mark-of-the-Web rule from 2026-09-10 §2 still holds: `Unblock-File` after every drop.
- Ruff config confirmed safe for the port's camelCase: `pyproject.toml` selects `E, F, I, B, UP, SIM`; **pep8-naming (`N`)
  is not enabled**, so `engineOwned`, `hrsPerWeek` and friends port without a single suppression.

## 4. Mistakes caught this session

1. **`rules.py` was never copied.** The first `Copy-Item` did not run. Ruff said `E902 The system cannot find the file
   specified` and pytest raised `ImportError: cannot import name 'rules' from 'app.planner'`. Diagnosed by listing the
   target folder (only `__init__.py`, 0 bytes) and `Downloads` (the file, 21,804 bytes, untouched). **Lesson: check
   `Length` on the target after every drop, not just that the command was pasted.**
2. **`rules.py` got committed twice.** Commit `7b3c2b5` carried 9 files including a stray
   `C:\dev\workmate-saas\app\planner\rules.py` at the **repo root**, outside `backend\`. Nothing runs it, but Claude Code
   launched from the repo root would find it and it would drift. Removed with `git rm -r --cached app` + `Remove-Item` +
   `--amend` → `e26a89f`, 8 files, one `rules.py`. Amend was legal: nothing pushed.
3. **`sql.py` 1.0.0 tripped the CI dialect gate on its own docstring.** Lines 16/17/19/24 documented the rewrites by
   spelling the banned tokens (`ISNULL(x, y) -> COALESCE(x, y)` etc.). Every statement was clean; the prose was not. The
   unit test scanned only `ALL_STATEMENTS` while CI greps the whole file — **the test and the gate disagreed and the gate
   was right.** Fixed in 1.0.1 by describing the four tokens instead of spelling them, and `test_sql_module_source_is_gate_clean`
   now reads exactly what CI reads. Verified the new test fails against 1.0.0 at precisely those four lines. SQL is
   byte-identical between 1.0.0 and 1.0.1.
4. **Ruff `I001`** on `test_planner_repo.py` 1.0.0: `from app.planner import repo, sql as psql` must be two lines. Fixed
   in 1.0.1.
5. **Spec defect, caught at build.** S1b spec §3.1 specified `CAST(NULL AS datetime)` for the no-pin columns. Wrong:
   `datetime` is not a PostgreSQL type name and MSSQL's `timestamp` is rowversion, so the cast would have been
   dialect-specific for no gain. Shipped as bare `NULL` — the value is always `None` and `repo.py` only ever tests it
   against `None`.

## 5. RST facts confirmed by the S1b run (33 tests, **zero skips**)

Every skip guard written into the suite stayed shut, so these are verified against live RST rows, not assumed:

- **The canonical window 2026-09-14..2026-09-20 is dense enough to be the standing test window.** Adopted as such.
- **OD-1 verified on real data.** Engine-owned PMs exist in that window and every one came back `locked=True`,
  `movable=False` — identical to the S1a fixture behaviour. The decision works on 20 years of real CMMS data.
- **The `to_d` boundary was genuinely exercised.** A WO starts exactly on 2026-09-20 and the returned count matched an
  independent control query, so the inclusive-API / exclusive-SQL `+1 day` in `repo._exclusive_end` is right.
- **`Sort_Sequence` ties are real on active priorities** (8.2f confirmed live) — `ORDER BY Sort_Sequence, Priority_Id` is
  load-bearing, not defensive.
- **`hours_uom_id` matches its independent control query and caches.** (RST value is 12 LABOUR HOURS per 2026-09-10 §5
  8.2d; the test asserts the resolution logic, not the number, so it survives a swap to the KT dev copy.)
- **`WO_N_Plan` still absent** → pin defaults hold for every row: `pinned` False, `engineDate` `''`, `pinnedOn` `''`.
- No `Status = 'D'` row survives the filter; closed and cancelled are never `movable`.
- **The S1a/S1b seam holds**: real RST rows through `buildWorkers()` and `hoursFor()` with no coercion surprises —
  `Decimal` → float, `char(n)` padding, naive datetimes, `Week_No` staying a float.

## 6. Deliberate deviations from the Ignition source (all documented in-file)

- **`parseIso` is calendar-strict.** `'2026-02-31'` → `None` → `BAD_DATE`, where Java's lenient `SimpleDateFormat` rolled
  it to 3 March. `_civil()` was already strict in 1.3.1, so the module now agrees with itself. Pinned by
  `test_parse_iso_strict_calendar`.
- **`weekStart` uses Python `weekday()` 0=Monday** in place of Ignition `getDayOfWeek` 1=Sunday (OD-6). Both send a Sunday
  back 6 days; all seven weekdays are tested so a `(weekday()+1) % 7` "fix" cannot sneak back in.
- `round()` half-to-even (OD-8) · `UOM_MODAL` tie-break (OD-11) · bare `NULL` not `CAST(NULL AS datetime)` (§4.5).
- **`hours_uom_id` caches per `Engine` object, not per URL string.** The MSSQL `odbc_connect` URL carries the password in
  its query string and SQLAlchemy's `hide_password` does not mask it — a URL-keyed cache would have parked
  `svc_workmate`'s password in a module global.
- **`# ruff: noqa: UP031` file-wide on `rules.py`.** `UP` is selected and would rewrite every ported `'%s' %` message to an
  f-string — exactly the rewrite the parity contract forbids. Alternative (pyproject `per-file-ignores`) not taken.
- `repo.py` imports `rules._LOCKED_STATUSES`, a module-private, rather than duplicating the constant. Ruff does not flag it
  (`SLF` not selected) and one source of truth beats one underscore.

## 7. Doc corrections queued (apply as dated changes in the next versions)

- **Port spec §2:** `PLANNER_DEV_USER_ID` is no longer a `System_Configuration` key → `.env` `WORKMATE_DEV_USER_ID` (OD-7).
- **Port spec §6:** S1 splits into S1a–S1e; `/preview` moves to S2 (OD-13).
- **Port spec §9:** OD-1, OD-6 signed 2026-09-10; OD-7…OD-13 signed 2026-09-11.
- **Architecture / port spec §6:** `app/auth/` (D-5) appears in no slice — add it as a slice, or record the S1c actor stub
  as the interim (OD-12).
- **S1b spec §3.1:** `CAST(NULL AS datetime)` → bare `NULL`.
- **Landmines §A:** add — the CI dialect gate greps the whole `sql.py` file, docstrings and comments included; a banned
  token in prose fails CI while a statement-only unit test passes.
- **Landmines §E** (carried from 2026-09-10, still unapplied): `Priority.Colour` "always `#FF8000`" is KT-only;
  `WO_C_Activity` labour can be empty; triggers are PO-only on RST.
- **`.gitignore`:** add `backend/.claude/skills/` and `backend/.agents/skills/` — symlinks into `.venv` must not be
  committed (§3).
- **`main.py`:** explicit API 404 handler so an `/api/...` miss does not depend on the SPA mount (§3).
- **Install doc / Bootstrap script:** the 2026-09-10 §8 corrections are still unapplied.

## 8. Open items carried forward

1. 🤙 web toolchain (`eslint` vs `biome`) and CLI (`create-tsrouter-app` vs `@tanstack/cli`) → then scaffold v1.0.2 with
   `-SkipBackend`. **Still the oldest open item, and the only thing standing between the suite and all-green.**
2. **KT dev copy** for the S1 parity oracle — source and delivery. Gates S1 acceptance, not the build.
3. Planner UI reference: 1.7.1 vs 1.8.1 — which is live at KT.
4. Copy `Planner_*.html` / `wm-ui.*` into `docs/reference/`; locate `Workmate_PG_Forward_Compat` and
   `Workmate_Planner_Assistant_Prompts`.
5. Verify Claude Code sees `backend\.claude\skills\fastapi`; junction from root if not.
6. OD-2 / OD-3 / OD-4 / OD-5.
7. `.gitignore` the skill symlinks (§3); API 404 handler (§3).

## 9. Next build step (unblocked)

**S1c:** `app/planner/service.py` (`range_data` only) + `schemas.py` + `router.py` (`GET /api/v1/planner/range`) +
`tests/test_planner_api.py`. Unblocked now OD-7 and OD-12 are signed. Audit first, then spec, then 🤙.

Three things the audit must carry in:

- **`rangeData` is where the time zone lives.** `today` is `iso(system.date.now())` (src 732) — the single OD-6 point,
  becoming `datetime.now(ZoneInfo(settings.tz)).date()` with `WORKMATE_TZ` defaulting to `Pacific/Auckland`. Windows has no
  system tz database, so the `tzdata` wheel is load-bearing (Landmines §A).
- **`load` keys are stringified in the service, not the repo.** `workerLoad()` returns int keys including `0`;
  `rangeData` does `dict([(str(k), v) for k, v in ...])` (src 738). `workerWeeks` already emits `str` keys itself.
- **The window guard raises, and the router turns it into a 400**: bad ISO, `from > to`, or a span over 400 days
  (src 715–718).

## 10. Changelog

- 1.0.0 (2026-09-11) Initial.
