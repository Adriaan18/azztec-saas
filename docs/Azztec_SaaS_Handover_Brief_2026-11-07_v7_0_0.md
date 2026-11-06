# Azztec SaaS — Handover Brief

**File:** Azztec_SaaS_Handover_Brief_2026-11-07_v7_0_0.md · **Version:** 7.0.0 · **Date:** 2026-11-07 · **Author:** Adriaan
**For:** the first message of the next chat. Paste this whole file. Supersedes 6.1.0 (2026-09-19); the W1b session (09-20) and the RST PM-repair chat (09-23 → 09-30) left no brief.
**Target path:** `docs/Azztec_SaaS_Handover_Brief_2026-11-07_v7_0_0.md` (replaces 6.1.0 there) + project knowledge (5.0.0, 6.0.0 and 6.1.0 leave PK)

---

## A. State (read once, then work the steps)

**The Redstag test drop is wanted Monday 2026-11-09**: the Planner with moves, sign-in from Workmate's own users and rights, a schema script their DBA re-runs after every restore, a deploy kit. A test laptop over the weekend, then Andrew for final approval.

Session 2026-11-06 → 11-07 shipped three of the four drop slices:

| Tag | Commit | What |
|---|---|---|
| `dp1-schema-1.0.0` | `06618ae` | `deploy/sql/azztec_schema.sql`, generated from the migrations by `scripts/deploy_sql.py` 1.0.1 (OD-90…OD-95) |
| `dp2a-auth-1.0.0` | `1bc2f0a` | sign-in and rights, backend: `app/auth/`, sessions, lockout, `Auth_Event`, gates; app **0.6.0** (OD-96…OD-103) |
| `dp2b-signin-1.0.0` | `1eaf3de` | sign-in, web: the sign-in page, the session gate, the name, "view only" and Sign out in the shell |

**HEAD is the docs commit for this set** (`docs: session close 2026-11-07 …`) on top of `1eaf3de`, tree clean, pushed to `Adriaan18/azztec-saas`. Repo: **`C:\Users\Azzte\Dropbox\azztec-saas`**.

Suites bare: backend **401 passed, 2 skipped** · web **461 tests in 28 files** · `ruff check` and `ruff format --check` clean · eslint clean. Contract `docs/api/openapi_0_6_0.json`. Migration head **`0002`**; dev `dbWorkmate` is still at **`0001`**, and everything behind sign-in runs on **`dbWorkmate_DP1_Test`** (a pristine RST restore at `0002`; throwaway test password on users **21** (AZZ, Azzmax logon, administrator) and **1084** (STORESWM, WM Read Only)). OD series at **103**. **Next: DP3, Planner moves.**

---

## B. The steps

### Step 1 — Read, in this order. Nothing else first.

1. this brief
2. `Azztec_SaaS_Raw_Log_2026-11-07_v1_0_0.md`: §0 the brief, §9 open items, §10 next (DP3's first questions), §4 every smoke, §6 the eleven mistakes
3. `Azztec_SaaS_Project_Knowledge_Index_v1_11_0.md` §1 and §6
4. `Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_2.md` §11 (as built) · `Azztec_SaaS_Platform_Landmines_v1_11_0.md` **§B before any SQL a client runs, §F before `pnpm dev`** · `Azztec_SaaS_Ways_of_Working_v1_4_0.md`
5. For DP3: `Azztec_SaaS_Planner_Port_Spec_v1_0_8.md` §6 (the S2 audit it inherits), `Azztec_SaaS_S2a_Weekno_Chunk_Spec_v1_0_0.md`, then the oracle: `workmate_planner_code_v1_3_1.py` and `workmate_planner_api_code_v1_8_3.py`

### Step 2 — Block 1: the box and the suites. Paste verbatim, wait for the prompt.

```powershell
cd C:\Users\Azzte\Dropbox\azztec-saas
& {
$ErrorActionPreference = 'Continue'
git log --oneline --decorate -4; git status --short
Get-NetTCPConnection -LocalPort 8000,3000 -State Listen -ErrorAction SilentlyContinue | Select-Object LocalPort, OwningProcess | Format-Table
Get-CimInstance Win32_OperatingSystem | Select-Object @{n='FreeGB';e={[math]::Round($_.FreePhysicalMemory/1MB,1)}} | Format-Table
Push-Location backend
try {
  uv run alembic current; "alembic exit: $LASTEXITCODE"
  uv run ruff check .; "ruff check exit: $LASTEXITCODE"
  uv run ruff format --check .; "ruff format exit: $LASTEXITCODE"
  uv run pytest; "pytest exit: $LASTEXITCODE"
} finally { Pop-Location }
Push-Location web
try {
  $vj = Join-Path $env:TEMP 'azztec_vitest.json'
  Remove-Item -LiteralPath $vj -ErrorAction SilentlyContinue
  pnpm lint | Select-Object -Last 5; "lint exit: $LASTEXITCODE"
  $null = @(pnpm exec vitest run --reporter=json "--outputFile=$vj"); "test exit: $LASTEXITCODE"
  if (Test-Path -LiteralPath $vj) {
    $r = Get-Content -Raw -LiteralPath $vj | ConvertFrom-Json
    "web tests: {0} files, {1} tests - {2} passed, {3} failed" -f @($r.testResults).Count, $r.numTotalTests, $r.numPassedTests, $r.numFailedTests
  } else { "no vitest JSON was written - read the run above" }
} finally { Pop-Location }
}
```

Expect: the docs commit on top of `1eaf3de`, `1bc2f0a`, `06618ae`; a clean tree; **no listener** on 8000 or 3000; `alembic current` → **`0001`** (dev, not head; that's expected); both ruff gates `0`; **401 passed, 2 skipped**; lint `0`; **28 files, 461 tests, 461 passed, 0 failed**. If HEAD is `1eaf3de`, the six docs never reached `docs/`: copy them from Downloads and commit before anything else. Anything else means the tree moved since this brief.

### Step 3 — Project knowledge housekeeping (§C).

**Remove first, then add.** PK sits at about 1.40 MB of its 2.00 MB limit; the removals free roughly 0.8 MB and the adds take roughly 0.7 MB.

### Step 4 — DP3: audit → spec → 🤙 → build → smoke → trail → log.

**Scope:** the Planner moves Redstag test, ported from the Ignition planner (the oracle in Step 1.5), never from the .NET code. The raw log's §10 lists the audit's first questions: which moves (a WO's day by drag, undo, the preview / confirm of OD-13, the estimate); the write itself (the dates, `Week_No` through S2a's `weekno.py`, the pin in `WO_N_Plan`, the `WO_Event_History` row); whether a move must also reach `dbWorkmate_QL.Query_Log` the way every Workmate.NET write does.

**Inherited, not re-litigated:** the actor is the signed-in person; move and undo take `require('planner', 'RW')` (413 of RST's 443 active people can move under RST's own Schedulex rows, OD-100); PlannerView hides its move controls at RO; `dry_run=True` first; every write smoke runs on `dbWorkmate_DP1_Test` as AZZ (moves) and STORESWM (refused), with dev's `Diag_Log` read before and after (178 at the close of 11-07).

**Web smokes go through the production build** (`pnpm build`, then `pnpm preview --port 3000 --strictPort`): Vite's dev server can't rename its dependency cache inside Dropbox (Landmines §F).

### Step 5 — DP4: the deploy kit.

HTTPS for a LAN server; the service's login and `@AppLogin`; the security notice (the four findings, **59 of 443** refused today, `Auth_Event` with no purge yet, passwords stay in Workmate.NET); the DBA one-pager (restore, run the script as a sysadmin with `@AppLogin` set, look for `AZZTEC SCHEMA OK`); `/` landing on `/planner`; whether the self-test stays public. Then the laptop, then Andrew.

### Step 6 — Close the session properly.

Raw log → the doc updates it implies (WoW 1.5.0 is the oldest debt: log 11-07 §8) → the next handover brief. Carry forward every open item not closed.

---

## C. The project-knowledge pack for this session

**Remove first.**

| Remove | Why |
|---|---|
| `Azztec_SaaS_Project_Knowledge_Index_v1_10_0.md` (**both copies**), `Azztec_SaaS_Platform_Landmines_v1_10_0.md` (**both**), `Azztec_SaaS_Architecture_and_Stack_v1_0_9.md` (**both**) | replaced by this set |
| `Azztec_SaaS_Handover_Brief_2026-09-19_v5_0_0.md`, `…_v6_0_0.md`, `…_v6_1_0.md` | replaced by this brief |
| one copy each of: `Ways_of_Working_v1_4_0`, `Planner_Port_Spec_v1_0_8`, `Raw_Log_2026-09-19_v1_2_0`, `Raw_Log_2026-09-15_v1_0_0`, `W1a_WOMaint_Read_Api_Chunk_Spec_v1_0_1`, `S1e_Web_Chunk_Spec_v1_0_0`, `S1c_Api_Chunk_Spec_v1_0_0`, `web_workorders_useWorkorders_v1_0_0`, `web_workorders_useWorkorders_test_v1_0_1` | uploaded twice; keep the newer copy |
| `app_main_v1_0_8`, `app_core_config_v1_2_0`, `app_core_deps_v1_1_0`, `dotenv_example_v1_1_0`, `test_openapi_contract_v1_1_1`, `test_planner_api_v1_2_0`, `test_workorders_api_v1_0_0`, `web_openapi_ts_config_v1_0_3` | superseded by DP2a |
| `web_main_v1_0_0`, `web_routes_root_v1_0_0`, `web_shell_HeaderToolbar_v1_0_0`, `web_shell_HeaderToolbar_test_v1_0_0`, `web_shell_AppShell_v1_0_0`, `web_shell_AppShell_test_v1_0_0`, `web_shell_css_v1_0_0` | superseded by DP2b |
| `web_routes_workorders_v1_0_0.tsx` | W1b's dead layout route; the repo has `workorders.index.tsx` (Landmines §C) |

**Then add.** Every file below was delivered as its own card (`Azztec_SaaS_` prefix omitted).

| Add | From |
|---|---|
| `Handover_Brief_2026-11-07_v7_0_0.md`, `Project_Knowledge_Index_v1_11_0.md`, `Platform_Landmines_v1_11_0.md`, `Architecture_and_Stack_v1_0_10.md`, `Raw_Log_2026-11-07_v1_0_0.md`, `DP2_SignIn_Rights_Chunk_Spec_v1_0_2.md` | this set |
| `DP1_Deploy_Schema_Script_Chunk_Spec_v1_0_1.md`, `scripts_deploy_sql_v1_0_1.py` | DP1 |
| `app_auth_rules`, `_sql`, `_repo`, `_service`, `_schemas`, `_router` (all `v1_0_0.py`), `app_core_deps_v1_2_0.py`, `app_core_config_v1_3_0.py`, `app_main_v1_0_9.py`, `alembic_0002_auth_sessions_v1_0_0.py`, `dotenv_example_v1_2_0.txt`, `web_openapi_ts_config_v1_0_4.ts` | DP2a |
| `backend_tests_test_auth_rules_v1_0_0.py`, `backend_tests_test_auth_api_v1_0_0.py`, `backend_tests_test_deploy_sql_v1_0_2.py`, `test_openapi_contract_v1_2_0.py`, `test_planner_api_v1_3_0.py`, `test_workorders_api_v1_1_0.py` | DP2a tests |
| `web_auth_rules`, `_rules_test`, `_session`, `_session_test`, `_session_fixture`, `_SessionGate`, `_SessionGate_test`, `_SignInPage`, `_SignInPage_test`, `_NoAccess`, `_NoAccess_test`, `_css` (all 1.0.0), `web_routes_signin_v1_0_0.tsx`, `web_routes_root_v1_1_0.tsx`, `web_main_v1_1_0.tsx`, `web_shell_HeaderToolbar`, `_HeaderToolbar_test`, `_AppShell`, `_AppShell_test`, `_css` (all 1.1.0) | DP2b |
| `Raw_Log_2026-09-20_v1_1_0.md`, `web_workorders_WoMaintView_test_v1_0_1.tsx`, `web_planner_SelectedWOCard_test_v1_1_2.tsx`, `web_planner_PlannerView_test_v1_2_1.tsx` | W1b's, shipped 09-20, never reached PK (re-sent with this set) |

**Never in PK:** DP1 spec 1.0.0, DP2 spec 1.0.0 and 1.0.1, `deploy_sql` 1.0.0, `test_deploy_sql` 1.0.0 and 1.0.1 (superseded before or inside the session). `deploy/sql/azztec_schema.sql` and `openapi_0_6_0.json` are generated and committed, never cards.

---

## D. Still owed from Adriaan

1. **For DP4:** which login the service runs as at Redstag (a SQL login, or a Windows virtual account `NT SERVICE\<name>` with no password in `.env`), and whether the kit carries a copy of the script with `@AppLogin` filled in. Their IT may decide this.
2. **The laptop:** what it runs (Windows version, SQL Server edition) and which database copy goes on it for the weekend test.
3. **Optional, 2 minutes:** mark `web\node_modules` ignored by Dropbox (Landmines §F) so `pnpm dev` works again.
4. Carried from 6.1.0: the mail route for the morning report.

---

## E. The cut (Monday 2026-11-09)

Done: DP1, DP2a, DP2b. Then **DP3** (Planner moves) → **DP4** (the kit, the notice, the DBA note) → the laptop over the weekend → **Andrew's approval** → Redstag's test server. After the drop: W1c, W2 / W3 (WOMaint writes), D1b, and on into the Ignition code.

---

## F. Rules this session added (Landmines 1.11.0; WoW 1.5.0 still owed)

1. **The server is the witness.** After every manual smoke step comes the server-side check that proves it (sessions, events, rows); zero is a STOP, whatever the person typed.
2. **Read msdb's restore history before trusting a test database's name.** `dbWorkmate_RST_Test` is a dev copy; `dbWorkmate_DP1_Test` is the pristine one.
3. **A client-facing SQL script is smoked the way their DBA runs it:** plain `sqlcmd` without `-b`, gated on `Msg` lines and the script's last line.
4. **Count tests from Vitest's JSON reporter**, never its coloured console.
5. **Web smokes use the production build** while the repo is in Dropbox, and they fetch the script `index.html` names.
6. **Every write smoke runs on `dbWorkmate_DP1_Test`**, dry run first, with dev's `Diag_Log` counted before and after.
7. **PowerShell 5.1:** no `2>&1` on pnpm; native calls under `Continue`, gated on `$LASTEXITCODE`; `curl.exe` with a hand-set `Cookie:` for HTTP smokes; a test password typed with `Read-Host -AsSecureString` and handed to SQL through a temp file that is deleted after.
8. **Credential queries return counts and structure only**, never a password or hash value.

## G. Changelog

- 7.0.0 (2026-11-07) After DP1 + DP2 (log 2026-11-07 1.0.0). The Redstag drop's state and cut; DP3 as the next slice with the audit's first questions; Block 1 counts web tests from Vitest's JSON; the PK pack, remove-first because PK is near its limit; four W1b cards that never reached PK. Replaces 6.1.0.
- 6.1.0 (2026-09-19) Restructured as numbered steps; HEAD corrected to `d53267e` (6.0.0's own commit moved it); the PK pack listed in §C; §D makes Andrew's user list the one critical-path item.
- 6.0.0 (2026-09-19) After W1a and the doc set. Replaced 5.0.0 (same day).
- 5.0.0 (2026-09-19) After S1k + D1a. Replaced 4.0.0 (2026-09-15).
