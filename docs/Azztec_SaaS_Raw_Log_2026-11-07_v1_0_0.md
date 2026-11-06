# Azztec SaaS — Raw Log 2026-11-07

**File:** Azztec_SaaS_Raw_Log_2026-11-07_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-11-07 · **Author:** Adriaan
**Status:** Session record, append-only. Session 2026-11-06 → 11-07, the first build session since 09-20. Three slices toward the Redstag test drop on **Monday 2026-11-09**: **DP1** (the client schema script), **DP2a** (sign-in and rights, backend) and **DP2b** (sign-in, web). Each was specced, signed, built, smoked on a fresh RST restore, committed, tagged and pushed. The doc set is cut at close (§8).
**Target path:** `docs/Azztec_SaaS_Raw_Log_2026-11-07_v1_0_0.md` (+ project knowledge: add)
**Parent:** log 2026-09-20 1.1.0. In between: the RST PM-repair work of 09-23 → 09-30 (its scripts are in PK; it left no raw log here) and the October move of the repo into Dropbox.

---

## 0. The brief (Adriaan, 2026-11-06)

- Redstag are still the first customer. They want to test **the Planner, with moves** (not read-only), on their test server; the drop is wanted **Monday 2026-11-09**.
- Their test environment: Windows Server, SQL Server on the same box, internet. Their IT installs. They test, then drop the database and restore the latest production backup. So the SaaS needs **a schema script their DBA re-runs in SSMS after every restore**.
- A deployment kit for that environment. A test laptop over the weekend, then **Andrew** for final testing and approval.
- People sign in. **The user and role data already in the database decides what each person may do.**
- After the drop: carry on building the SaaS by reverse-engineering the Ignition code.

That brief closed the item that blocked auth since 09-16: **Andrew's user list is no longer needed.** Workmate's own users, groups and passwords are the identity (OD-96), so handover 6.1.0 §D item 1 is closed and D-5's `App_User` + argon2 waits for phase 2.

The cut: **DP1** schema script → **DP2** sign-in and rights (DP2a backend, DP2b web) → **DP3** Planner moves → **DP4** deploy kit.

## 1. Decisions this session

| ID | What | State |
|---|---|---|
| **OD-90** | One standalone, idempotent T-SQL script, `deploy/sql/azztec_schema.sql`, generated from the migrations and committed static; their DBA runs it after every restore. The app never migrates a client database | 🤙 2026-11-06 |
| **OD-91** | Every step guarded by the migration's own test, one batch each, prints `created` / `present`. No wrapping transaction; the recovery is "run it again" | 🤙 2026-11-06 |
| **OD-92** | The script creates `dbo.alembic_version` if missing and stamps the head | 🤙 2026-11-06 |
| **OD-93** | The script re-creates the app's database user from `@AppLogin`, `db_datareader` + `db_datawriter` only. 1.0.1's reading: a sysadmin login is skipped, the owner's login is `dbo` with nothing granted, another live login's user is refused, the runner must be a sysadmin, and any refusal ends `INCOMPLETE` | 🤙 2026-11-06 |
| **OD-94** | The script refuses system databases and anything without `dbo.Users` and `dbo.WO_N_Header`, through `SET NOEXEC ON` | 🤙 2026-11-06 |
| **OD-95** | Every migration exposes an `MSSQL` step list; the generator refuses one without; a test fails if the committed script differs from a fresh render | 🤙 2026-11-06 |
| **OD-96** | Sign in with the Workmate.NET login and password, verified (MD5-20) and never copied. **Revises D-5:** `App_User` + argon2 waits until the SaaS owns passwords | 🤙 2026-11-06 |
| **OD-97** | A server-side session in an `HttpOnly; Secure; SameSite=Strict` cookie, only its SHA-256 stored; 12 h absolute, 4 h idle; `X-Azztec-Request: 1` on every non-GET. **Revises D-5's JWT** | 🤙 2026-11-06 |
| **OD-98** | Who may sign in, in order: one active user; the password verifies; not `SYS_USER`; not a default password (`wm`, `sys_user`, the login id); in a group; no reset due. One generic message for the first two, a specific one after the password is proved | 🤙 2026-11-06 |
| **OD-99** | Lockout from `Auth_Event`: 5 failures per login, 20 per address, in 15 minutes → 423 | 🤙 2026-11-06 (as built, the window's edge is bound from Python; spec 1.0.2 §11.1) |
| **OD-100** | Rights = the Ignition model as pure rules; Planner gated on Schedulex (**Option A**, view RO+, move RW+), WOMaint on Order Maintenance; enforced server-side on every route; `Active` every request, rights cached 60 s | 🤙 2026-11-06 |
| **OD-101** | Every attempt, refusal, lock, sign-out and expiry is one `Auth_Event` row, written synchronously, never a password | 🤙 2026-11-06 |
| **OD-102** | Migration `0002_auth_sessions` in the step-list shape; the client script re-rendered to head `0002` | 🤙 2026-11-06 |
| **OD-103** | `WORKMATE_DEV_USER_ID` is no identity on the HTTP path; DP2's smoke uses `dbWorkmate_DP1_Test` only, never `dbWorkmate` or a real password | 🤙 2026-11-06 |
| **DP2b** | "View only" in the header; NA handled once in the root route; `useSession`; sign-out and a stray 401 both set the session to `null`; `/` left to DP4; smoked through `vite preview` | Taken at the build from the web audit and told before the cards were written. Recorded in DP2 spec 1.0.2 §11.2 |
| **numbering** | **OD-80…OD-89** belong to the RST PM-repair chat of 2026-09-23/24 (`Invoke-RstTestSql.ps1` 1.0.6 cites OD-83/84). That chat left no raw log in PK, so their text is not in this doc set. **OD-90 onward are this session's** | note |

## 2. Shipped and committed

| Commit | Tag | What |
|---|---|---|
| `06618ae` | `dp1-schema-1.0.0` | **DP1.** 4 paths, 2,000 insertions: `scripts/deploy_sql.py` 1.0.1, `backend/tests/test_deploy_sql.py` 1.0.1, the generated `deploy/sql/azztec_schema.sql` (head `0001`, 42 steps), the DP1 spec 1.0.1 |
| `1bc2f0a` | `dp2a-auth-1.0.0` | **DP2a.** 26 paths, 3,044 insertions: `app/auth/` (`rules` `sql` `repo` `service` `schemas` `router` 1.0.0 + `__init__`), `core/deps.py` 1.2.0, `core/config.py` 1.3.0, `main.py` card 1.0.9 (**app 0.6.0**), migration `0002_auth_sessions` 1.0.0, `.env.example` 1.2.0, `openapi-ts.config.ts` 1.0.4, six test files, `openapi_0_5_0.json` → **`openapi_0_6_0.json`** (an 88 % rename, 12 paths), the client regenerated, the script re-rendered to head `0002` (47 steps), the DP2 spec 1.0.1 |
| `1eaf3de` | `dp2b-signin-1.0.0` | **DP2b.** 21 paths, 1,746 insertions: `features/auth/` (12 new: `rules` `session` `session.fixture` `SessionGate` `SignInPage` `NoAccess` `auth.css` + five tests), `routes/signin.tsx` 1.0.0, `routes/__root.tsx` 1.1.0, `main.tsx` 1.1.0, the shell's `HeaderToolbar` / `AppShell` / `shell.css` 1.1.0 with both tests, `routeTree.gen.ts` |

All pushed to `Adriaan18/azztec-saas`. **HEAD `1eaf3de`, tree clean.** The session opened on `aa4a394` (log 09-20 1.1.0), with `bc582af` (the S1e spec, untracked until then) under it and W1b's `330c0c7` below that.

**Cards cut: 46**, every one delivered as its own card with its PK line. Superseded before the repo saw them: DP1 spec 1.0.0, `deploy_sql` 1.0.0, `test_deploy_sql` 1.0.0, DP2 spec 1.0.0. Superseded in the repo by a later card this session: `test_deploy_sql` 1.0.1 (1.0.2 in DP2a). Plus this set's six docs.

## 3. Suite state

| | Session open | After DP1 | After DP2a | After DP2b |
|---|---|---|---|---|
| Backend | 319 passed, 2 skipped | **343 / 2** (predicted 343) | **401 / 2** | 401 / 2 (untouched) |
| Frontend | 384 in 23 files | 384 / 23 | 384 / 23 (the client regenerated) | **461 in 28** (predicted 384 + 77 in 28; every per-file count matched) |
| ruff check / format | 0 / 0 | 0 / 0 | 0 / 0 | n/a |
| eslint | 0 | n/a | 0 | 0 |
| `tsc --noEmit` | not run | n/a | n/a | exit 2, **14 errors, none in DP2b's files**. Informational: nothing in the gates runs `tsc` (§9) |

DP2a added 58 backend tests: auth rules 33, auth API 18 (15 functions, no database), contract +5, one 403 gate test each for Planner and WOMaint. DP2b added 77 web tests: auth rules 34, session 19, SessionGate 7, SignInPage 8, NoAccess 3, header +4, shell +2.

**Build after DP2b:** `signin-*.js` 1.91 kB is its own chunk; the `planner-*.js` and `workorders.index-*.js` stubs survived; `index-*.js` 339.31 kB (107.67 kB gzip).

## 4. Evidence and smokes

### 4a. The audit (2026-11-06)

- **RST's `Users` and security tables, counts and structure only.** `Users` 1,120 rows (`AD_Login_ID char(20)`, `AD_Password char(20)`, `Active`, `Reset_Pwd_flag`, `Last_PW_Reset_Date`); `Security_Group` 17, `User_Security_Group` 421, `System_Menu_Security_Group` 464, `User_Password_History` 455; `INT_USERS` carries an `AD_Password` column and 0 rows. No login, audit or session table of Workmate.NET's own (`WO_Event_History` is the nearest audit, `Diag_Log` is ours).
- **Workmate.NET's sign-in, read in its source** (`Workmate_Without_Reports.zip`): `frmLogin.cs` 160–227, `clsGeneralOperation.cs` 1377–1389, `clsUser.cs` 220–245 and 523. MD5-20, the inactive-before-password leak, no lockout, the ADMIN auto-join (Landmines §E). Read as evidence of behaviour, not as a template (Adriaan: *do not blindly copy the .NET build*).
- **The Ignition port's rights model**, `workmate.security` 1.9.0 and `workmate.identity` 1.1.2: the lowest group level, the page tag, the more restrictive of the two, administrator = level exactly 1. Live at KT since June; this is what DP2 ports.
- **Three security findings** Adriaan asked to keep and to tell Redstag about at the hand-over: six active accounts still on `wm`; `SYS_USER` active on `sys_user`; 29 active users with no group, each of whom Workmate.NET would make ADMIN at their next login.
- **A usage count:** 173 people wrote something in the 12 months to the 26 Aug backup (Landmines §E).

### 4b. DP1 smoke (2026-11-06, spec 1.0.1 §7)

- **1.0.0 on `dbWorkmate_RST_Test`** (16:51): 0 created, 44 present, `AZZTEC SCHEMA OK`, 340 / 2. The runner logged `no Version line (unversioned file)`. Reading the generated T-SQL against the cases the smoke was about to run then found four faults before any of them ran (§6).
- **msdb's restore history** showed `dbWorkmate_RST_Test` is not an RST restore: it was restored from the QL sidecar on 09-23, then over the top from a **dev copy at head** on 09-24. The fresh target had to be `C:\dev\backups\RST_Workmate.bak`.
- **1.0.1 on `dbWorkmate_RST_Test`:** `@AppLogin` empty → `skipped`, OK; `no_such_login_dp1` → `REFUSED`, `INCOMPLETE`; `AzztecDev\Azzte` (a sysadmin) → `skipped`, OK.
- **`RST_Workmate.bak` → `dbWorkmate_DP1_Test`** with `Restore-RstTest.ps1` 1.0.5: header `dbWorkmate` / `RSTSQL01` / taken 2026-08-26 19:26 by `RSTIMBER\svcWAREHOUSE`; 904,695,808 B compressed (5.16 GB); restored in 82.4 s, upgraded to physical version 998; compat 160, `SIMPLE`. `WO_N_Header` 169,678, `WO_C_Header` 453,133, the same as dev.
- **Run 1:** 43 created, `stamped version 0001 (was none)`, OK, no `Msg`. Snapshot: 6,515 facts before, 6,760 after; **0 gone or changed, 245 added, 0 unexpected**; 15 columns on existing tables.
- **Run 2:** 0 created, 44 present, OK.
- **Catalog diff** against the alembic-built `dbWorkmate`: 201 fingerprint lines each side (T 13, C 151, K 15, F 4, X 3, I 15), **0 differences**.
- **Refusal in `master`:** with `-b` exit 1, without `-b` exit 0; both print `REFUSED` and `Msg 50000` and nothing else; `master` holds 0 of the 13 names before and after.
- **App user `svc_workmate`:** created plus two grants, `app user ok`, OK; again: `present` ×3, OK; roles exactly reader and writer; three facts added, nothing else.
- Backend 343 / 2; `Diag_Log` on dev **178 → 178**.

### 4c. Block DP2-E (2026-11-06 18:12, `dbWorkmate_DP1_Test`, counts only)

P1–P7 as in DP2 spec 1.0.2 §3.4: 443 active, every one MD5-20 with a login id, no duplicates, **112 with an inner space**; reset policy off; 17 groups, nobody in two; Schedulex rows for two groups only; Planner **RWD 24 · RW 389 · RO 1 · NA 29**; **59 refused**, of which **25 because the password is the login id**, a finding the spec took in before it was signed (OD-98 rule 4); Andrew (21, AZZ) RWD everywhere, administrator.

### 4d. DP2a smoke (2026-11-07 04:18, 25 PASS / 0 FAIL)

The API on `127.0.0.1:8010` with `WORKMATE_DB_NAME=dbWorkmate_DP1_Test` for that process only; `.env` untouched.

- **Schema to `0002`:** run 1: 5 created, 43 present, `stamped version 0002 (was 0001)`, `tables 14/14 columns 15/15 indexes 18/18`, OK; run 2: 49 present, OK.
- **Test accounts, dry run then the write, on the copy only:** admin 21; non-admin 1084 (READ ONLY, level 4); no-group 224; user 4 set to `wm`; `SYS_USER` 1 — `ids|1084|4|224|4|1|rows|4|1` both times.
- **Health:** db ok, `dbWorkmate_DP1_Test`, app 0.6.0, deps 1.2.0, auth 1.0.0.
- **Sign-in:** no header → 403 `CSRF`; a wrong password and a made-up login → the same 401 body; admin → 200, RWD/RWD, administrator, expiry sign-in + 12 h; cookie 43 characters, every flag; `/me` 200 with it, 401 `NO_IDENTITY` without; `SYS_USER`, `DEFAULT_PASSWORD`, `NO_GROUP` → 403 with their own lines; five 401s, then 423 `LOCKED`.
- **Rights:** admin: Planner 200 (4 WOs, actor 21), workorders 200, `_diag/users` 200. User 1084: RO/RO, not an administrator; Planner 200, `_diag/users` 403 `NO_RIGHT`. No cookie: 401 on both.
- **Sessions:** after 61 s last-seen moved (`15:18:34.999` → `15:19:37.597` UTC); sign-out 200 and the cookie cleared; the old cookie replayed → 401; sign-out again → 200.
- **Trail:** `Auth_Event` `LOCKED` 1 · `SIGNIN_FAIL BAD_PASSWORD` 1 · `NO_USER` 6 · `SIGNIN_OK` 2 · `SIGNIN_REFUSED DEFAULT_PASSWORD` 1 · `NO_GROUP` 1 · `SYS_USER` 1 · `SIGNOUT` 2, one row per attempt. `Auth_Session` `sess|2|64|1|0|0` (two rows, 64-character hashes, the cookie found by its SHA-256 only, none live). `Diag_Log` from auth: F 4, G 13.
- **Never shown:** the test password in no table (`pw|0|0`) and not in the API's output; the cookie not in the output; no `[E]` line; dev `Diag_Log` 178 → 178.

### 4e. DP2b smoke: run 1 failed, run 2 15 PASS / 0 FAIL (2026-11-07)

**Run 1 (05:54), Vite's dev server on :3000:** 9 PASS / 3 FAIL. Adriaan answered **y** to steps 1–6; the page was blank. The server had seen **0 sessions and 0 events**. Vite printed `EBUSY` renaming `node_modules\.vite\deps_temp_*` to `deps` (Dropbox holds the folder; Landmines §F), and my stderr check counted those five lines and passed them. Nothing was wrong in the code; the dev server could not serve the app.

**Run 2 (06:11–06:20), the production build through `vite preview` on :3000, the API on :8000 against `dbWorkmate_DP1_Test`:**
- `pnpm build` exit 0; health; `/planner` 200, **its script `/assets/index-C4jnPi5W.js` 200**, `/signin` 200; through the preview proxy: health 200 on `dbWorkmate_DP1_Test`, `/auth/me` without a cookie 401.
- Steps 1–6 (Edge InPrivate): `/planner` → `/signin?next=/planner`; a wrong password → the server's line, the password box emptied; AZZ → back on the Planner as **Azzmax logon**; `/workorders` typed in the address bar → open without asking (the cookie held across a full reload); sign-out → sign-in with `next=/workorders`; STORESWM → WO Maint as **WM Read Only** with the gold **view only**. **The server saw it:** `BAD_PASSWORD` 1, `SIGNIN_OK` 3, `SIGNOUT` 2 (one sign-in more than the script's minimum, a step repeated by hand; the checks are "at least").
- Step 4 on the server: the read-only session's expiry set a second back → `expired 1`.
- Steps 7–8: a click on a work order → sign-in with `next` naming it → AZZ → back on that record (3CL-260826-007, id 662697).
- **Trail:** `EXPIRED expired` 1 · `BAD_PASSWORD` 1 · `SIGNIN_OK` 4 · `SIGNOUT` 2; no refusal, no lock; `sess|4|1`; `Diag_Log` from auth F 3, G 2.
- The test password in no table and not in either server's output; no `[E]`; no error line from the preview server; dev `Diag_Log` 178 → 178.
- Two screenshots kept by Adriaan: the Planner month view, signed in as Azzmax logon, caught at `LOADING`; the WO Maint record 3CL-260826-007.

The throwaway test password stays on users 21 and 1084 in `dbWorkmate_DP1_Test` only. `dbWorkmate` was never written by any DP block.

## 5. Facts verified this session

- **Workmate.NET's sign-in and RST's people**, counted: Landmines §E (two lines).
- **Workmate.NET logs every write into `<db>_QL.Query_Log`**, found 09-23 for `Restore-RstTest.ps1` 1.0.4 and carried here because DP3 is the first SaaS write a Workmate.NET user could look for there (Landmines §E; §10).
- **The test databases on the box** (msdb, 2026-11-06): `dbWorkmate` (dev) from RSTSQL01 2026-08-26, still at `0001` (no DP block wrote to it); `dbWorkmate_RST_Test`, a 09-24 dev copy at `0001`; `dbWorkmate_QL_RST_Test`, the QL sidecar kept as evidence; **`dbWorkmate_DP1_Test`**, a pristine RST restore, now at **`0002`**, carrying the smokes' test passwords, `Auth_*` rows and the `svc_workmate` user; `dbWorkmate_KT` (read-only oracle) and `dbWorkmate_KT_RFID` unchanged.
- **The schema script at head `0002`:** 47 steps; 14 tables, 15 columns, 18 indexes; `present 49` on a second run (47 steps, the version table, the version row).
- **SQL Server versions:** AzztecDev is 17.0.1000.7 (2025, physical version 998); RST is 2022 (16.0.1160, version 957). A restore here upgrades on the way in; nothing goes back the other way.
- **A `Secure` cookie works over `http://localhost`** in Edge, and **.NET's cmdlets won't send one** to an `http://` address (Landmines §A).
- **`vite preview` keeps the `/api` proxy** (Landmines §C).
- **The contract:** app 0.6.0, `docs/api/openapi_0_6_0.json`, 12 paths (the three auth routes new).

## 6. Mistakes caught this session

1. **DP1 1.0.0 trusted a database's name.** `dbWorkmate_RST_Test` sounded like an RST restore; msdb said it was a dev copy at head. Caught before the fresh-restore half of the smoke, by reading the restore history rather than the name.
2. **DP1 1.0.0's app-user step would have failed on its own test cases:** `ALTER ROLE … ADD MEMBER [dbo]` for the owner's login, `CREATE USER` for `sa`, and a refused user still ending `AZZTEC SCHEMA OK`. Caught by reading the generated T-SQL against the smoke's cases before running them.
3. **DP1 1.0.0 printed `created` after a failed `CREATE`**, because an error inside `EXEC()` doesn't stop the batch. Same read.
4. **DP1 1.0.0's header had no `Version =` line**, so the runner logged an unversioned file.
5. **Block 3's third run overwrote its second run's log** (`Invoke-RstTestSql` names logs to the second). Noticed in Block 4's opening lines.
6. **DP2a: a second sign-out wrote a second `SIGNOUT` row.** The sandbox harness caught it before the cards went out; `sign_out` now writes only when the revoke changed a row.
7. **DP2a: `require_admin` was missing** against the signed OD-100 (`_diag` for administrators). Caught at review before delivery; added behind the dev-only check.
8. **DP2a: `test_auth_api` assumed the box's `.env`.** A changed session length would have turned it red. Its settings are pinned now.
9. **DP2b run 1: a blank page passed as "y".** The person confirmed six steps on a screen that rendered nothing; my stderr check passed five `EBUSY` lines as noise; the server's own count (0 sessions, 0 events) was the only honest witness, and it was checked once, after step 4. The rework: smoke the production build; fetch the script the HTML names; ask the server after each manual block and stop on zero; any `error`, `EBUSY` or `EPERM` line from either server is a FAIL.
10. **DP2b review, before release:** `safeNext` let `/SignIn` past its `/signin` check (the router matches case-insensitively), and `session.ts` assumed a result always carries `response`. Both fixed in the cards as shipped.
11. **DP2b Block 1 showed no test count:** an anchored filter against Vitest's coloured summary. Block 3 counted from Vitest's JSON reporter.

## 7. Patterns confirmed

- **Read the artefact against the cases before you run the cases.** DP1's four faults came from reading the generated T-SQL beside the smoke plan, not from the smoke.
- **The server is the witness.** A person's "y" is a claim about a screen; sessions and events are what happened. Every manual step in a smoke is now followed by the server-side check that would prove it.
- **A throwaway restore makes a destructive smoke safe.** Test passwords, a forced expiry, a locked login, two schema runs, a created database user: all on `dbWorkmate_DP1_Test`. Dev's `Diag_Log` read 178 at the start and end of every block.
- **Probe before 🤙.** Block DP2-E's numbers went into the spec before it was signed, and one of them (25 accounts whose password is their login id) changed a rule.
- **Count from machine-readable output:** Vitest's JSON, the API's JSON, `sqlcmd`'s marker lines. Never a coloured console.
- **Predict, then read:** 343 for DP1; 461 in 28 for DP2b, every per-file count as predicted.

## 8. Doc-correction queue

**Applied by this session's set:**
- `Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec` **1.0.2**: signed; as built (§11): the six DP2a differences with reasons, the DP2b decisions, the hand-over to DP3 and DP4.
- `Azztec_SaaS_Platform_Landmines` **1.11.0**: this session's lines in §A, §B, §C, §E and §F, and the 09-20 queue's three §C lines.
- `Azztec_SaaS_Architecture_and_Stack` **1.0.10**: D-5 rewritten to the sign-in as built; §5 the tree as on disk (`azztec-saas`, `app/auth/`, `deploy/`, `features/auth/`, W1b's `features/workorders/`); a new §6c, the sign-in flow.
- `Azztec_SaaS_Project_Knowledge_Index` **1.11.0**: state, read order, inventory (W1b, DP1, DP2), environment, pick-up, OD-72…OD-103, the PK housekeeping list.
- `Azztec_SaaS_Handover_Brief_2026-11-07` **7.0.0**.

**Still queued, carried:**
- **Ways of Working 1.5.0** (none of this is new as practice; it is new as text): a manual smoke step is confirmed by the server, not the person; count from machine-readable output; read the generated artefact against the smoke's cases before running it; smoke the web through `vite preview` while the repo is in Dropbox. From 09-20: "stop the server" means `GET /api/v1/health` failing, not a listener count of zero; the `docs/` retention rule.
- **W1b spec 1.0.1** (log 09-20 §8): real counts (384 in 23), the 25th card, OD-79's seven controls, the smoke-fix revisions.
- **W1a spec 1.0.2:** `WOStatus` has eight cards, not nine (log 09-20 §8).
- **Planner Port Spec 1.0.9:** the S2 move work is now DP3; OD-12's JWT seam is replaced by OD-97's session; move and undo take `require('planner', 'RW')`.
- **Data Layer doc:** the auth tables, `0002`, and the test databases above.
- **Dev Environment Install:** the Dropbox path, `vite preview` for smokes, and its six-session-old corrections.

## 9. Open items

The 09-20 log listed new items without numbers, so the numbered series stays at 55; this list names its items.

**New this session:**
- **DP3, Planner moves.** Next (§10).
- **DP4, the deploy kit.** HTTPS for a LAN server (the `Secure` cookie); the service's login and `@AppLogin` (a SQL login, or `NT SERVICE\<name>` with no password in `.env`); the security notice (the four findings, **59 of 443** refused today, `Auth_Event` with no purge yet, passwords staying in Workmate.NET); the DBA one-pager; `/` landing on `/planner` instead of the CLI placeholder; whether `/api/v1/_diag/self-test` stays public at a client site.
- **No type-check gate.** `tsc --noEmit` reports 14 errors in files DP2b didn't touch. List them, fix them, then make `tsc` a gate.
- **Vite dev in Dropbox.** Mark `web\node_modules` ignored by Dropbox (Landmines §F) and prove `pnpm dev` renders, or keep smoking through `vite preview`.
- **Dev `dbWorkmate` is at `0001`, head is `0002`.** Anything behind sign-in runs on `dbWorkmate_DP1_Test` until dev gets `0002` (DDL, dry run first), and nobody can sign in on dev without a real password (OD-103). Decide which database DP3 develops against; DP1_Test is the answer so far.
- **The Planner's `actor #` label.** The screenshot caught it at `actor #0` while the range was still loading; the API returned actor 21 in DP2a's smoke. Confirm it reads 21 once loaded, in DP3's smoke.
- **`Query_Log` parity.** Workmate.NET writes every change into `dbWorkmate_QL.Query_Log`. Does a SaaS move need to land there too, or is `WO_Event_History` plus our own trail enough? DP3's audit asks. Redstag's test server may not even carry the QL database.
- **The rights cache is per process** (60 s). Fine with one worker; a multi-worker deployment needs a shared invalidation or a shorter TTL.
- **The RST PM-repair chat (09-23 → 09-30) has no raw log in PK**, so OD-80…OD-89 and its R-slices have no text in the doc set. Its scripts are in PK: `01`–`04_*_WO_M_Task_StartDate` 1.0.1, `R3_Print_Attachment_Probe` 1.0.1, `R3b_QL_Attachment_History` 1.0.0, `Restore-RstTest` 1.0.5, `Invoke-RstTestSql` 1.0.6.

**Closed:**
- **Andrew's user list** (handover 6.1.0 §D 1, OD-2 / D-5's blocker): not needed; Workmate's own users are the identity (OD-96).
- **Auth, a condition of the Redstag install:** DP2a + DP2b shipped.
- **The `/workorders` dev actor 21:** gone from the HTTP path (OD-103). Every write DP3 makes carries the signed-in person.

**Carried, unchanged:** item 38, Starlette's two deprecation warnings (`httpx` → `httpx2`, `BlockingPortal`), still the suite's only two. From 09-20: the four KT `meta.classes` carry-backs; `F` has no status card (W3); `//workorders/662704` resolves; the eight live reference shots for `docs/reference/`; the Create WO path has no slice; the Assessment card; `WO_Query` `N`/`A` codes (item 55); the `Summary` toggle; windowing beyond Load more. Handover 6.1.0 §D 3 (the mail route for the morning report) and §D 4 (Redstag told what the trail keeps; the DP4 notice now carries it).

## 10. Next

1. **Close this set:** the six docs into `docs/` and PK (handover 7.0.0 §B).
2. **DP3, Planner moves**, audit → spec → 🤙 → build → smoke on `dbWorkmate_DP1_Test`. Its audit's first questions:
   - which moves Redstag test first: a WO's day by drag, and undo; the preview / confirm (OD-13) and the estimate;
   - the write itself, ported from `workmate_planner_code_v1_3_1.py` and `workmate_planner_api_code_v1_8_3.py`, not from the .NET code: the date fields, `Week_No` (S2a's `weekno.py` is ready), the pin in `WO_N_Plan`, the `WO_Event_History` row;
   - `require('planner', 'RW')` on move and undo; PlannerView's move controls hidden at RO; `dry_run=True` first;
   - `Query_Log` parity (§9);
   - what the smoke proves: a move by AZZ, a refusal for 1084, undo, the event row, the trail, and dev untouched.
3. **DP4, the deploy kit** (§9's list), then the laptop over the weekend and Andrew's approval.
4. After the drop: W1c, W2/W3 (WOMaint writes), D1b, and on into the Ignition code.

## 11. Changelog

- 1.0.0 (2026-11-07) Session 2026-11-06 → 11-07: the Redstag drop's brief; DP1 (OD-90…OD-95, `06618ae`, `dp1-schema-1.0.0`); DP2 (OD-96…OD-103) as DP2a (`1bc2f0a`, `dp2a-auth-1.0.0`) and DP2b (`1eaf3de`, `dp2b-signin-1.0.0`); 343 → 401 / 2 backend, 384 → 461 in 28 web; every smoke on `dbWorkmate_DP1_Test`, dev's `Diag_Log` 178 throughout; eleven mistakes; the doc set cut.
