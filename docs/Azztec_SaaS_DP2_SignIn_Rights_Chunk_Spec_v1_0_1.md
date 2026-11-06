# Azztec SaaS — DP2 Sign-in and Rights — Chunk Spec

**File:** Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md · **Version:** 1.0.1 · **Date:** 2026-11-06 · **Author:** Adriaan
**Status:** Draft with Block DP2-E's numbers in (§3.4, 2026-11-06 18:12). Needs 🤙 on OD-96…OD-103.
**Slice:** DP2, the second of four for the Redstag test drop. It builds as two slices:
- **DP2a** (backend: migration 0002, sign-in, sessions, rights, gates)
- **DP2b** (web: sign-in page, guard, sign-out, rights-aware screens)

DP3 (Planner moves) needs DP2a only.
**Target path:** `docs/` (+ project knowledge: add 1.0.1; 1.0.0 never goes in)
**Sits on:** `06618ae`, tag `dp1-schema-1.0.0` (DP1 smoke green 2026-11-06, pushed), migration head `0001`, backend 343 passed / 2 skipped, frontend 384 in 23 files.

---

## 1. Why this slice exists

Redstag's people will use the SaaS on their test server, and Andrew signs off on it. Adriaan's brief (2026-11-06):
- They sign in with their **user name and password**.
- **The user and role data already in the database decides what each person may do.**
- The Planner must let them **move WOs**, so writes need a real, provable actor.

Today every request runs as `.env`'s `WORKMATE_DEV_USER_ID` (`deps.py` 1.1.0, OD-12/OD-56). That seam was always meant to be "swapped wholesale in the auth slice". This is that slice.

## 2. Scope

**In:**
- Sign-in with the Workmate.NET login and password, verified, never copied (OD-96).
- A server-side session in a cookie (OD-97).
- The refusal rules (OD-98) and lockout (OD-99).
- Rights from Workmate's own security tables for the two pages that exist, Planner and WOMaint (OD-100).
- An auth audit table (OD-101).
- Migration `0002` and the re-rendered client script (OD-102).
- The `_diag` routes behind the administrator level (OD-61's hand-over).
- **DP2b:** a sign-in page, a route guard, the user's name and Sign out in the shell, and screens that hide what the backend would refuse.

**Out:**
- Changing a password. That stays in Workmate.NET and the SaaS never writes `Users`.
- User or group administration.
- OIDC / Entra (phase 2, D-5).
- Rights for pages that don't exist yet.
- The Planner write routes themselves (DP3).
- HTTPS for a LAN server (DP4).

## 3. Evidence

### 3.1 How Workmate.NET signs a person in (read 2026-11-06, `frmLogin.cs` 160–227, `clsGeneralOperation.cs` 1377–1389, `clsUser.cs` 220–245, 523)

1. The typed login is looked up as `Users.AD_Login_ID` (`wmsp_UserSelectLoginInfo`, so the comparison is case-insensitive under RST's CI collation).
2. A user whose `Active <> 'Y'` is told so, *before* the password is checked. That tells a stranger the account exists; we do not copy it (OD-98).
3. The password check is `AD_Password == MD5(ASCII bytes of the typed text) as uppercase hex, first 20 characters`:
   - unsalted
   - the stored value trimmed, the typed one not
   - non-ASCII characters become `?` (`Encoding.ASCII`)
4. Its own reset policy:
   - `PW_Sec_Level > 1` with `Reset_Pwd_flag` in (`1`, empty), or
   - `PW_RESET_PERIOD` months since `Last_PW_Reset_Date`

   Either one forces a change before entry. `SYS_USER` is exempt.
5. If `Security_Group` is empty it creates group 1 ADMIN. A user with **no** `User_Security_Group` row is **inserted into group 1 (ADMIN)** at that login. That is a hole, and the Ignition port already refuses it (D5).

### 3.2 How the Ignition port decides rights (`workmate.security` 1.9.0, `workmate.identity` 1.1.2)

- **Level:** the user's **lowest** `Security_Group.Sec_Group_Access_Level` across memberships, ties to the lowest group id. 1–2 → RWD, 3 → RW, 4 → RO, anything else → NA. No membership → NA (D5).
- **Page right:** that same group's `System_Menu_Security_Group.Menu_Access_Level` for the page's legacy `System_Menu.Menu_Tag`. **No row → RWD** (the .NET seed default); an unreadable value → RWD.
- **Effective:** the more restrictive of the two (D6-A, a deliberate deviation from .NET, where the tag can re-show what the level hid).
- **Administrator:** level **exactly 1** (`isAdminLevel`). Level 2 (Manager, CFO) is RWD but not admin.
- **Gates:**
  - Planner = `workmateSchedulexToolStripMenuItem` (**Option A, chosen 2026-11-06**: view RO+, move RW+)
  - WOMaint = `workmateOrderMaintananceToolStripMenuItem` (view RO+)

This model has been reviewed and has been in production at KT since June. It is the thing ported, not the .NET code (Adriaan, 2026-11-06: *do not blindly copy the .NET build*).

### 3.3 What RST's data already showed (2026-11-06, counts only, no password or hash value selected)

| Finding | Count | What it means for the SaaS |
|---|---|---|
| Active accounts whose password is Workmate.NET's default `wm` | **6** | refused until changed (OD-98) |
| `SYS_USER` active, password `sys_user` | **1** | never signs in (OD-98) |
| Active users in **no** security group | **29** | refused here; Workmate.NET would make each one ADMIN at their next login |
| Active accounts whose password **is their own login id** (exact, lower or upper case) | **25** | refused until changed (OD-98, from P6) |
| Active accounts / with a login id | 443 / 443 | |

All of these go into DP4's security notice for Redstag (Adriaan, 2026-11-06). Altogether **59 of 443** active accounts would be refused today (P6, overlaps counted once).

### 3.4 Block DP2-E (2026-11-06 18:12, `dbWorkmate_DP1_Test`, counts only)

| Probe | Result | What it settles |
|---|---|---|
| P1 identifier | 443 active, **all** with a login id, **no duplicates** (case-insensitive). Longest 20 characters. **112 contain a space inside** (e.g. a first name and an initial). | OD-96's "exactly one" never refuses anyone at RST. Trap 9: trim the ends, never the inside. |
| P1 stored password | all 443 are 20 hex characters; none blank. | Every active account is in Workmate.NET's MD5-20 form; the verify path covers everyone. |
| P2 reset policy | `PW_RESET_PERIOD = 0`, `PW_Sec_Level = 1`, so **0** people are due a reset under Workmate.NET's rule. | OD-98 rule 6 refuses nobody at RST today; it is kept so a client who turns the policy on is honoured. |
| P3 groups | 17 groups. Level 1: ADMIN (18), CO-ORD PLUS PM (4), WM Administrator (0). Level 2: Projects + Attachments (2). Level 4: READ ONLY (1). Everything else level 3: Operator 110, Contractor 102, Co-ordinator 59, Fitter 44, Electrician 40, and smaller groups. **Nobody is in two groups.** | The lowest-level tie-break never matters at RST. |
| P4 page tags | Schedulex (menu 23) has rows for **2 groups only**: PLANNER RWD, READ ONLY RO. WOMaint (menu 26) has 8: RWD for seven groups, READ ONLY RO. | Every other group has no row, so it gets RWD on the tag and its **level** decides. |
| P5 effective rights | Planner: RWD 24, **RW 389**, RO 1, NA 29. WOMaint the same. Administrators (level 1) 22, level 2 two. | **413 of 443 could move WOs.** That is what RST's own configuration says, and what Workmate.NET's Schedulex already allows them. See OD-100's note. |
| P6 refusals | SYS_USER 1, default password 7, **password = login id 25**, no group 29: **59** in all. | OD-98 rule 4 includes "password = login id". |
| P7 Andrew (user 21, AZZ) | group 1 ADMIN, level RWD; Planner RWD; WOMaint RWD; administrator. | He can test everything, including `_diag`. |

## 4. Decisions (🤙 required)

| OD | Decision | Why |
|---|---|---|
| **OD-96** | **Sign in with the Workmate.NET login and password, verified, never copied.** The login is `Users.AD_Login_ID` (trimmed, case-insensitive), matching **exactly one** active user. The password is checked with Workmate.NET's algorithm (§3.1 point 3) and compared in constant time. The SaaS reads `AD_Password` only into that compare. It never writes `Users`, never stores or logs a password, and never shows one. **Revises D-5:** the `App_User` table with argon2 waits until the SaaS owns passwords (phase 2, with OIDC). | One password per person, no second credential store for Redstag to manage, and the brief's own words. The legacy hash is weak (unsalted MD5), but it is Workmate.NET's store; verifying against it weakens nothing. OD-98/99 add what Workmate.NET lacks. |
| **OD-97** | **A server-side session, not a JWT** (revises D-5's token choice).<br>• **Token:** 256 random bits in an `HttpOnly; Secure; SameSite=Strict; Path=/` cookie `azztec_session`.<br>• **Storage:** the database keeps only its SHA-256, in `dbo.Auth_Session` (user, created / last-seen / expires / revoked, IP, user agent).<br>• **Lifetime:** **12 h absolute, 4 h idle.** Last-seen is refreshed at most once a minute.<br>• **Ending it:** Sign out revokes the row. A user turned `Active = 'N'` in Workmate.NET is out on their next request.<br>• **CSRF:** every non-GET, sign-in included, must carry `X-Azztec-Request: 1`, which a cross-site form cannot set. | One box, one process: revocation is the deciding property. A JWT cannot be withdrawn at sign-out or deactivation without a deny-list, which is a session table by another name. No signing key to manage at the client either. |
| **OD-98** | **Who may sign in, checked in this order:**<br>(1) the login matches one active user;<br>(2) the password verifies;<br>(3) not `SYS_USER` (`Short_User_Id`);<br>(4) the password is not a known default — `wm`, `sys_user`, or **the person's own login id** in any case (P6: 25 accounts);<br>(5) the user is in a security group;<br>(6) Workmate.NET's own reset policy (`System_Details`) would not force a reset today. P2: refuses nobody at RST, kept so a client who turns the policy on is honoured.<br>**Rules 1–2 fail with one generic message** ("Sign-in failed. Check your user name and password."), so the screen never says whether an account exists. Rules 3–6 are only reached **after** the password is proved, and they say exactly why and what to do ("change it in Workmate.NET first", "ask your Workmate administrator"). | Adriaan's hard rules (2026-11-06). The generic message fixes the account-existence leak in §3.1 point 2. A reason given after the password is proved tells the owner, not a stranger. |
| **OD-99** | **Lockout from the audit table, not memory:**<br>• **Per login:** 5 failures in 15 minutes locks that login for 15 minutes; a correct password is refused meanwhile, with its own `LOCKED` message.<br>• **Per IP:** 20 failures in 15 minutes blocks that address the same way.<br>• Counted per login *as typed*, so a made-up name locks too and the message leaks nothing.<br>• The window query is `DATEADD`, tagged `-- PG-CONVERT: interval` (the OD-60 precedent). | Survives a restart; no state in the process. Workmate.NET has no lockout at all. |
| **OD-100** | **Rights = the Ignition model (§3.2), re-implemented as pure rules.**<br>• **Pages:** `planner` and `womaint` with their tags. Planner range RO+, Planner move and undo RW+ (DP3 uses it), WOMaint reads RO+, `_diag` routes administrator (level 1).<br>• **Enforcement:** in the backend on every route, by a `require(page, right)` dependency answering 403 `NO_RIGHT`. The web only mirrors it.<br>• **Freshness:** `Active` is checked on every request. A user's rights are cached at most 60 s, so a change in Workmate.NET bites within a minute. | The model is already reviewed, approved (Option A) and live at KT. Enforcing server-side means a hidden button is a convenience, never the security. **At RST this gives 413 of 443 people move rights (P5)**, because RST has Schedulex rows for two groups only. That matches Workmate.NET's Schedulex today. If Redstag want fewer, they add Schedulex rows in Workmate.NET's security setup (e.g. Operator → RO); the SaaS follows within a minute, with no code change. |
| **OD-101** | **Every sign-in attempt and sign-out is one row in `dbo.Auth_Event`.** It records time, the login as typed (trimmed, ≤ 100), the user id when known, the event (`SIGNIN_OK` / `SIGNIN_FAIL` / `SIGNIN_REFUSED` / `LOCKED` / `SIGNOUT` / `EXPIRED`), the reason, IP, user agent (≤ 200) and request id. It is written **synchronously**, not through Diag_Log's queue (which may drop under load). Never a password. No purge in DP2; DP4's notice says so. Diag_Log still gets its normal `[F]`/`[G]` line (OD-58 redaction stands). | It is what Redstag's IT will ask for, it feeds OD-99, and it must not be lossy. |
| **OD-102** | **Migration `0002_auth_sessions`** adds `Auth_Session` and `Auth_Event` with their indexes, in the OD-95 step-list shape (MSSQL and PG lists, guarded like `0001`). `deploy/sql/azztec_schema.sql` is re-rendered to head `0002`: 14 tables, 15 columns, and N indexes counted from the card. The app user keeps reader and writer only. | DP1's machinery, used as designed. Redstag's DBA runs one file, as before. |
| **OD-103** | **The dev identity seam leaves the HTTP path.** No request is ever acted for by `WORKMATE_DEV_USER_ID` again; tests override the dependency as they do now. Dev signs in like everyone else. DP2's smoke points the dev backend at `dbWorkmate_DP1_Test` with a known test password on one account there, and **never touches `dbWorkmate` or any real password**. | A fallback identity on the HTTP path would hide every auth bug in dev. A throwaway copy keeps the rule that the dev database's people and passwords are not ours to change. |

## 5. DP2a — backend (cards counted at the build, versions read from the files then)

1. `backend/alembic/versions/0002_auth_sessions.py`:
   - **`Auth_Session`:** `Session_Hash char(64)` PK, `User_ID numeric(18,0)`, `Created_At`, `Last_Seen_At`, `Expires_At` (`datetime2(3)`), `Revoked_At` NULL, `Client_IP varchar(45)`, `User_Agent nvarchar(200)`. Index (`User_ID`, `Expires_At`).
   - **`Auth_Event`:** `Auth_Event_ID bigint IDENTITY` PK, `Event_At datetime2(3) DEFAULT CURRENT_TIMESTAMP`, `Login_Typed nvarchar(100)`, `User_ID numeric(18,0)` NULL, `Event varchar(20)`, `Reason varchar(40)` NULL, `Client_IP varchar(45)`, `User_Agent nvarchar(200)`, `Request_Id varchar(36)`. Indexes (`Login_Typed`, `Event_At`), (`Client_IP`, `Event_At`).
   - No FK to `Users`, as at KT (delta §5).
2. `backend/app/auth/` per D-4:
   - **`rules.py` (pure):** `md5_20(text)`, `password_matches(stored, typed)`, `normalise_login`, `refusal(...)` (OD-98 order), `level_right`, `page_right`, `effective`, `is_admin`, `lockout(...)` (OD-99).
   - **`sql.py`:** the statements.
   - **`repo.py`:** the user by login, groups and menu rights, session read / write, events, failure counts.
   - **`service.py`:** `sign_in`, `sign_out`, `session_actor`.
   - **`schemas.py`** and **`router.py`:**
     - `POST /api/v1/auth/signin {login, password}`: 200 with `{user, rights, isAdmin, expiresAt}` and the cookie; 401 `SIGNIN_FAILED`; 403 `REFUSED` with `reason`; 423 `LOCKED`.
     - `POST /api/v1/auth/signout`: 204.
     - `GET /api/v1/auth/me`: 200 / 401 `NO_SESSION`.
3. `backend/app/core/deps.py` **1.2.0**:
   - `get_current_actor` reads the cookie session, with no dev fallback (OD-103).
   - `require(page, right)` and `require_admin`.
   - The CSRF header check for non-GET.
   - `request.state.actor` is still set on both paths (D1a).
4. **Gates added** to the planner `range` route, the workorders routes and the four `_diag` routes. `/health` and the SPA stay public.
5. `backend/app/core/config.py` gets the cookie name, the 12 h / 4 h lifetimes, `WORKMATE_COOKIE_SECURE` (default true), and the lockout numbers.
6. **Tests, pure and HTTP:**
   - `md5_20` against known vectors (`wm`, `sys_user`, a non-ASCII case)
   - the level × tag table, with every OD-98 rule in order
   - generic versus specific messages, lockout edges
   - cookie flags, CSRF refusal, idle / absolute expiry, revoked, `Active = 'N'` mid-session
   - `NO_RIGHT` on each gated route, and the admin-only `_diag`
7. **Generated on the box:**
   - the OpenAPI document (contract change)
   - `deploy/sql/azztec_schema.sql` (`--write --force`)

## 6. DP2b — web

- `routes/signin.tsx` and `features/auth/`:
  - `SignInPage`: user name and password; one message line; the generic failure text; the OD-98 reasons in plain words.
  - `useMe`: TanStack Query on `/auth/me`.
  - sign-in and sign-out calls through the generated client.
- `__root.tsx`: a guard. No session → `/signin?next=<path>`; after sign-in → `next`.
- **AppShell:** the person's name, and Sign out.
- **Client fetch:** `X-Azztec-Request: 1` on every non-GET; a 401 anywhere drops `me` and returns to sign-in.
- **PlannerView:** RO → no drag handles, no move controls, a quiet "view only" marker. NA → a no-access page.
- **WOMaint:** NA → the same no-access page.

## 7. Traps

1. **The typed password is not trimmed** (Workmate.NET hashes it as typed); the stored one is. Trimming the typed one would lock out anyone whose password ends in a space.
2. **ASCII, not UTF-8.** `Encoding.ASCII` turns every non-ASCII character into `?`; `str.encode('ascii', 'replace')` does the same.
3. **`char(20)` padding:** `RTRIM` the stored value, compare uppercase.
4. **A Secure cookie works on `http://localhost`, not on `http://<lan-name>`.** The dev box and a laptop-local browser are fine; a LAN server needs HTTPS (DP4).
5. **SameSite=Strict and the Vite proxy:** the dev UI on :3000 and the API on :8000 are one site to the browser (same host, cookies ignore ports). Nothing changes there.
6. **The generic message must be the same body and status for "no such login" and "wrong password"**, and roughly the same time: verify against a dummy hash when the login is unknown.
7. **Lockout counts the login as typed**, normalised the same way as the lookup; otherwise `ADRIAAN` and `adriaan` are two counters.
8. **The 60 s rights cache is per process** and is dropped on sign-out.
9. **112 RST login ids have a space inside** (P1). Normalising trims the ends and lowercases for the comparison only. It never collapses or strips an inner space, and the lookup and the lockout counter use the same normalisation.

## 8. Smoke (outline; exact blocks at the build)

1. **Gates:** ruff 0/0, backend N passed, web N passed.
2. **Schema:** re-render to head `0002`, then run it on `dbWorkmate_DP1_Test`. Expect:
   - 0001's 44 present
   - 0002's tables and indexes created
   - `stamped version 0002 (was 0001)`
   - `AZZTEC SCHEMA OK`
   - a second run all present
3. **Test password:** one account on `dbWorkmate_DP1_Test` gets a known test password. That is the only write to a legacy table in DP2, and only on the throwaway copy, dry run first. The `.env` points at that copy; the backend restarts.
4. **Sign-in and the hard rules** on that copy:
   - right and wrong passwords
   - a made-up login (same message as a wrong password)
   - five failures, then the lock
   - one of the 6 `wm` accounts, `SYS_USER`, and a no-group user (each needs a known password on the copy, set the same way)
   - each refusal with its own message
5. **Rights:** `NO_RIGHT` and the hidden controls for an RO account; the Planner and WOMaint open for Andrew; `_diag` refused for a non-admin.
6. **Trail:**
   - `Auth_Event` rows for every attempt above, with no password anywhere: grep the logs and `Diag_Log.Detail` for the test password, expect 0.
   - The dev `dbWorkmate` Diag_Log count unchanged.
7. **Commit and tag** `dp2a-auth-1.0.0` and `dp2b-signin-1.0.0`.

## 9. Acceptance

- Only a verified, active, grouped, non-SYS, non-default account gets a session.
- The screen never reveals whether a login exists.
- Five failures lock a login for 15 minutes.
- Every attempt is in `Auth_Event`, and no password is stored, logged or shown.
- Sign out and deactivation end the session on the next request.
- Every gated route refuses without the right, whatever the web shows.
- The client script reaches head `0002` on a fresh restore with `AZZTEC SCHEMA OK`.

## 10. What this hands DP3 and DP4

- **DP3:** a real actor on every write, and `require('planner', 'RW')` for move and undo.
- **DP4:**
  - the service's login and `@AppLogin`
  - HTTPS for a LAN server (or the laptop-local browser)
  - the security notice: the four §3.3 findings (59 accounts refused today), the auth table, no purge yet, passwords still Workmate.NET's

## 11. Changelog

- 1.0.1 (2026-11-06) Block DP2-E's numbers in.
  - §3.3: the password = login id finding (25) and the 59-account total.
  - §3.4: rewritten as results.
  - OD-98: rule 4 includes the login id; rule 6 kept (0 at RST).
  - OD-100: the 413-movers note.
  - Trap 9: inner spaces.
  - §10: the notice carries four findings.
- 1.0.0 (2026-11-06) Draft. Written after reading:
  - Workmate.NET's login (`frmLogin.cs`, `clsGeneralOperation.cs`, `clsUser.cs`)
  - Ignition `workmate.security` 1.9.0 and `workmate.identity` 1.1.2
  - `deps.py` 1.1.0
  - Architecture D-5
  - the 2026-11-06 counts in §3.3
