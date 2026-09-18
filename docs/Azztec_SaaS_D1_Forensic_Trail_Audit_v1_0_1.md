# Azztec SaaS — D1 Forensic Trail Audit

**File:** Azztec_SaaS_D1_Forensic_Trail_Audit_v1_0_1.md · **Version:** 1.0.1 · **Date:** 2026-09-16 · **Author:** Adriaan
**Status:** Audit — **nothing signed.** Three things Adriaan **stated** this session are recorded as decisions to confirm at the D1a gate (§5): the test identity, 60-day retention, the trail-read rule. Seven ODs are proposed (**OD-55…OD-61**, §7). The D1a chunk spec follows once Block D1-E (§8) is pasted, and only after S1k closes — never build past the current slice. **1.0.1, the same day, records Adriaan's answer on Azzmax:** it is Andrew's own login with full administrator rights, and his changes are meant to carry his name (§5, OD-56). 1.0.0 had asked for the opposite to be confirmed.
**Target path:** `docs/Azztec_SaaS_D1_Forensic_Trail_Audit_v1_0_1.md` (+ project knowledge; replaces 1.0.0)
**Parent:** Architecture D-8 (diagnostics) and D-5 (identity); OD-47 (recorded, not signed — D-8: "persist mode does not ship before that OD is signed"); item 28 (the browser route); log 09-15 §9; the Redstag first drop.
**Numbering hazard:** slice **D1** is not architecture decision **D-1**, and not `workmate.workorder`'s KT decision "D1" (PO clone deferred). Always write "slice D1", "D1a", "D1b".
**Read 2026-09-16.** Ignition, from the 13:07 export: `workmate.diag` 1.3.0 (in full); the named queries `Workmate/Diag/Diag_LogInsert`, `Diag_Trail` 1.0.1, `Diag_UsersList` and `Diag_Purge` (in full); `Workmate/Debug/DiagViewer` (filters, table binding, Support Toolkit text); `DiagnosticsConsole` and `DebugConsole` (handlers, controls); the `DiagRetentionPurge` schedule; `planner_api` 1.8.3's `_diag` family. SaaS, from the PK cards: `diag.py` 1.1.1 (in full); `main.py` 1.0.4 (middleware, health, self-test); `deps.py` 1.0.0; `config.py` 1.1.0; `db.py` 1.0.0 (helpers); `.env.example` 1.0.1; `planner/router.py` 1.1.1; `usePlannerRange` 1.0.0; `PlannerView` 1.1.0; Architecture D-5/D-8; KT Schema Delta §4.1; S1j §2.5 and OD-47. **Not yet read (owed, §8):** the `Users` row for Azzmax, `Diag_Log` as `0001` landed it on RST, and the bodies of KT's three diag routines.

---

## 1. The ask

Adriaan, 2026-09-16: RST is a big company with many users. Before Planner and WOMaint functions go to them, **every person's activity must be logged the way Workmate Ignition's forensic diagnostics are**, so when something goes wrong it is found and sorted fast. Stated with it:
- use **Azzmax** — Andrew's login, full administrator rights — as the identity for testing. Andrew "should be able to go in and make changes, hence why the audit trail is important, so it shows what was fixed, for now and future diagnostics";
- keep **60 days**;
- **after every test, read the trail and check the outcome is as designed** — a standing rule.

## 2. The oracle — Workmate Ignition, as read

**The writer, `workmate.diag` 1.3.0.** Four calls. Each persists asynchronously to `dbo.Diag_Log` through `Workmate/Diag/Diag_LogInsert` and streams to the live console (`debug-log`):

| Call | Tier | `Msg_Level` | Use |
|---|---|---|---|
| `log(source, message, level, session=)` | `S` | as given | standard lines — saves, state changes |
| `forensic(session, source, message)` | `F` | `info` | what happened — clicks, branches; always on since 1.2.1 |
| `guard(session, source, message)` | `G` | `warn` | why it was blocked — "the support gold" |
| `error(session, source, message, detail=)` | `E` | `error` | crashes; the traceback goes into `Detail` automatically |

Attribution comes from the Perspective session:
- `Session_Id` = `session.props.id`
- `Wm_User_Id` = `session.custom.wmUserId`, NULL when ≤ 0
- `Site_Code` = `session.custom.siteCode`

A call made without `session=` persists with no user.

**Its own history is the first trap.** The 1.3.0 changelog records that the live gateway's `Diag_Log` stayed **empty**, because the deployed module was a different lineage with no persistence. Every persist path swallows its errors by design ("diagnostics must never break the app"), so nothing said the log was off.

**The reader, `Workmate/Debug/DiagViewer`.**
- **Filters:** a user dropdown (`Diag_UsersList`: active users plus "All users"); range buttons 5m · 30m · 1h · 12h · 36h · 1w · 1mo (default 30 min); **Problems only** (`Tier IN ('E','G')`); Refresh; auto-refresh every 10 s.
- **Table:** the newest **500** rows (`Diag_Trail` 1.0.1, `TOP 500`, newest first). Columns: Logged_At · User (`Name (id)`) · Source · Tier · Msg_Level · Message · Detail · Session_Id.
- **Support Toolkit panel — the playbook:** pick the user and tick Problems only. `[G]` means blocked, and the Message says why. `[E]` means a crash, with the traceback in Detail. If nothing shows, widen the range and read the `[F]` trail around the action.
- **Support Toolkit panel — snippets** to copy into SSMS (`fn_Diag_UserTrail('Pam', 60)`, `vw_Diag_Problems`, `vw_Diag_WhoIsOn`) and into the Script Console.

**The live consoles** — `DebugConsole` v1.2.0 (the shared bottom dock, shown on demand) and `DiagnosticsConsole` v1.0. They show the `debug-log` stream with Pause, Auto-scroll, Clear and Export. The SaaS already has the equivalent: the backend window prints every line as one JSON object.

**Retention** — the gateway schedule `DiagRetentionPurge` sets `RETENTION_DAYS = 30`. `Diag_Purge` deletes `Logged_At < DATEADD(day, -:days, CURRENT_TIMESTAMP)`.

**What KT's table holds** (S1j §2.5, codes only):
- 69,656 rows across 429 sessions;
- `PurchaseOrder` `[F]` alone is 40,009 rows;
- **18,406 rows (26 %) carry no user** — library calls that never passed `session=`;
- `Site_Code` is NULL on every row;
- the rows are real staff activity including email addresses — never copied, never pasted.

**The planner API's version** (`planner_api` 1.3.0+):
- every request outcome is persisted with the *verified* actor;
- each write outcome gets one line carrying prev → new (`_diagWrite`);
- `POST /_diag` lets the browser file its own `[E]`/`[F]` rows under the same attribution.

## 3. The SaaS today, as read

| Piece | State |
|---|---|
| `dbo.Diag_Log` | On RST since `0001` (2026-09-14), **empty**. The contract is KT's DDL: `Diag_Id` identity · `Logged_At datetime2(3)` · `Session_Id varchar(64)` · `Source varchar(64)` · `Tier char(1)` · `Msg_Level varchar(8)` · `Message nvarchar(1000)` — all NOT NULL · `Wm_User_Id int` · `Site_Code varchar(8)` · `Detail nvarchar(max)` · indexes on `Logged_At` and `(Wm_User_Id, Logged_At)`. KT's routines did not cross (OD-42) |
| `diag.py` 1.1.1 | `log(level, message, detail, actor, source, request_id, persist)` always prints one JSON line to stdout. **`PERSIST_SQL = None`**, so nothing reaches the table. If it were set, `_persist` binds `level, source, message[:990], detail, actor, rid`, which means: **no `Session_Id`, `Tier` or `Msg_Level`** (all NOT NULL); actor `0` lands as `0`, not NULL; **one new thread per row**; every exception swallowed. Its comment still says the table arrives with "S0 migration 0004" — stale since `0001` |
| Request middleware (`main.py` 1.0.4) | Request id = `X-Request-Id` or 12 hex characters. An exception logs `[E] … crashed`. Each `/api` call gets one outcome line tagged by status (`F` below 400, `G` below 500, else `E`) with **no actor** and `persist=False`. Every response carries `X-Request-Id`, and OD-15 error bodies carry `rid` |
| Actor (`deps.py` 1.0.0) | `WORKMATE_ENV=dev` with `WORKMATE_DEV_USER_ID > 0` → that id; otherwise `[G] no identity` and a 401. `.env.example` says **`1` = `SYS_USER`, deliberately not a real person** (logs 09-11) |
| `/api/v1/_diag/self-test` | Logs one `[F]` and returns persist mode, wired, and a DB ping — **no read-back** |
| `/api/v1/health` | `diag` (persist mode) and `diagWired` |
| Planner | Logs `[G] range refused` or `[F] range … rows= labour= workers= pinTable= in N ms` with the actor. The web polls `/range` **every 60 s** while the tab is in front (`usePlannerRange`). With persist switched on as written, that is one row per open planner per minute, all day |
| Web | **No card reads `rid`**. `PlannerView` shows `String(query.error)`, so a user has nothing to read out to support |
| Browser errors | Not built — item 28 |
| Viewer, purge | Not built |

## 4. The gaps against the ask

1. **Nothing persists.** Persist is off, and as written it cannot be switched on: three NOT NULL columns are unbound.
2. **Nobody is anybody.** Every row would say user 1 until sign-in exists, and the per-request line has no user at all.
3. **A silent log is KT's own recorded failure.** Persist errors are swallowed, nothing reports them, and the self-test never reads back.
4. **Scale.** At RST's size, a thread per row competes with requests for pooled connections, and the 60 s poll alone costs about one row per user per minute.
5. **No way to read it.** There is no trail query, no viewer and no purge, and KT's helper routines are not on RST.
6. **The browser is invisible.** The browser's own errors never arrive (item 28), and a user cannot quote a request id.
7. **`Detail` takes whatever it is handed.** No rule keeps secrets out.

## 5. Stated by Adriaan this session — recorded, confirmed at the D1a gate

- **The test identity is Azzmax** — Andrew's own login, with full administrator rights.
  - `WORKMATE_DEV_USER_ID` becomes Azzmax's `Users.User_Id` (§8, E2). It is a `.env` hand step with no code.
  - It supersedes `SYS_USER` as the dev actor for **interactive** testing. Background jobs, such as the purge, persist with no user, as KT's do.
  - From the swap, every write through the dev override stamps Azzmax: `WO_Event_History`, `WO_N_Plan`, `Created_By`, and every `Diag_Log` row. **That is intended.** Andrew administers RST's Workmate and makes fixes, and the trail must show what was fixed and by whom, now and for later diagnostics.
  - **One identity per person, or the trail lies.** Anything done under Azzmax reads as Andrew's, including our own testing. On the dev box, a local RST copy nobody else reads, that is acceptable. On Redstag's test server every person signs in as themselves — the auth slice — or the trail cannot tell Andrew's fixes from anyone else's. That makes auth a condition of the install, not an option.
  - **The SaaS does not use the password at all** until the auth slice, and even then not the legacy one. D-5 stores an argon2 hash in `App_User`, set interactively. The password never goes on a command line, in `.env`, in a file, a log, a card or memory.
  - A two-letter password is acceptable nowhere network-reachable; the auth slice sets a minimum length.
- **Retention is 60 days.**
  - It is read from the `System_Configuration` key `DIAG_RETENTION_DAYS`; if the key is absent, 60 applies.
  - The app reads the key and never writes it. A DBA sets it with the snippet in the D1a spec.
- **The trail-read rule** (Ways of Working, next doc set).
  - The rule: *every test ends with the trail — the test identity's rows over the test window, pasted verbatim — compared line by line with the predicted trail in the spec's smoke section. An unpredicted `[G]` or `[E]`, a missing `[F]`, or a row with no user is a finding before the commit.*
  - Until D1a ships, the trail is the backend window's JSON lines, tee'd to a file by the smoke's boot block with `PYTHONUNBUFFERED=1`. From D1a on, `scripts\Show-DiagTrail.ps1` reads the table.
  - It applies from the **S1k smoke**. The trail predicted there: the two `[F] diag wired` boot lines, then for each planner load one `[F] range …` and one `[F] GET /api/v1/planner/range 200 …ms`, and no `[G]` or `[E]`.

## 6. The proposed cut

### 6.1 D1a — persist and read (backend only)

D1a runs after S1k closes and before any slice writes data (W2, S2b). About one session.

| Card (predicted) | Change |
|---|---|
| `app/core/diag.py` 1.1.1 → **1.2.0** | The OD-55 fill; `PERSIST_SQL` set; one writer thread with a bounded queue and batching, plus counters and a rate-limited stdout `[E]` when persisting fails (OD-57); `redact()` on `Detail` (OD-58); the read de-dupe (OD-59); `flush()` for shutdown; the stale "0004" comment corrected |
| `app/diag/sql.py` **1.0.0** | Portable SQL for the insert, the trail (the `Diag_Trail` port), problems, who-is-on, the users list and the batched purge — using `dbo.`, `CURRENT_TIMESTAMP`, `COALESCE`, `OFFSET … FETCH` and `-- PG-CONVERT:` tags. KT's routines are ported as queries, not routines (OD-42) |
| `app/diag/repo.py` **1.0.0** · `app/diag/router.py` **1.0.0** | `GET /api/v1/_diag/trail?userId&minutesBack&problemsOnly`, `GET /_diag/whoison`, `GET /_diag/users` and `POST /_diag/purge?dry_run=true`. All dev-only and `include_in_schema=False`, so no contract change until D1b (OD-61) |
| `app/core/deps.py` 1.0.0 → **1.1.0** | The resolved actor also lands on `request.state.actor` |
| `app/main.py` 1.0.4 → **1.1.0** | The outcome line carries the actor and persists under the OD-59 policy. The lifespan starts the writer and the daily purge (OD-60) and flushes on shutdown. The self-test writes a marker and **reads it back by rid**. `/health` gains `diagPersist {mode, queued, written, failed, dropped, lastOkAt, lastError}` |
| `app/core/config.py` 1.1.0 → **1.2.0** · `.env.example` → **1.1.0** | Adds `WORKMATE_DIAG_PERSIST` (default true) and `WORKMATE_DIAG_PURGE` (default true; set false on every worker but one). The dev-user comment names Azzmax |
| `scripts/Show-DiagTrail.ps1` **1.0.0** | The rule's reader: `-UserId -Minutes [-ProblemsOnly]`, running `sqlcmd` straight at the table so it works even when the app will not boot; ASCII only |
| Tests | `test_diag_persist.py` **1.0.0**. Zero-DB: the fill mapping, redaction, de-dupe, queue overflow and counters. DB-gated: marker insert → read-back → purge `dry_run` count, with the marker cleaned up by `Diag_Id`. `test_diag_wiring` and `test_smoke` are bumped only where `/health` changes shape |

### 6.2 D1b — the viewer and the browser (frontend)

D1b runs before the deploy. About one session.

- **A Diagnostics Viewer page**, `/diagnostics`, inside the shell. It ports DiagViewer: user, ranges, Problems only, 10 s refresh, newest 500, expandable `Detail`, and the Support Toolkit with the portable snippets. It is dev-only until rights exist and is reached by URL, so the shell does not change.
- **Browser errors:** `POST /api/v1/_diag/client` fed by `window.onerror`, `unhandledrejection` and a React error boundary, rate-limited per session. Item 28 closes.
- **The request id on every error the user sees** ("ref a1b2c3d4e5f6") — the one thing a user can read out to support.

## 7. Open decisions for the D1a gate — proposals, none signed

| ID | Question | Proposal |
|---|---|---|
| **OD-55** | How the SaaS fills `Diag_Log` | **OD-47 as recorded, signed here:** `Tier` = the tag (`F`/`G`/`E`; `S` for background jobs) · `Msg_Level` = `F→info`, `G→warn`, `E→error`, `S→info` · `Source` = the emitting module (`http`, `planner`, `workorder`, `diag`; `web` from D1b) · `Session_Id` = the request id now, `<session>:<rid>` once sign-in issues sessions (≤ 45 of 64) · `Wm_User_Id` = the actor, **NULL when 0** · `Site_Code` NULL · `Logged_At` = `CURRENT_TIMESTAMP`, the database clock, as at KT · `Message` ≤ 1,000 · `Detail` = redacted JSON ≤ 8,000 characters. **Every field is cut to its column before queueing**, so no single row can fail a batch on length |
| **OD-56** | The dev actor | **Azzmax, as stated — Andrew's own login, full administrator rights** (§5). `.env` only, swapped in D1a's smoke so the change carries its evidence. Background jobs use NULL. Stamps under Azzmax are Andrew's by design; on Redstag's server each person signs in as themselves (the auth slice), and Andrew is its first administrator. `SYS_USER` stays the documented fallback on any install with no agreed login |
| **OD-57** | Writing at RST's scale, and noticing a dead log | **One daemon writer and one bounded queue (10,000), writing in batches of ≤ 100 rows or ≤ 1 s,** never blocking a request. Overflow drops the newest row and counts it; the next written row states the count. A failed batch is counted, printed once as a stdout `[E]` (then every 100th), retried once, then dropped. `/health` shows the counters, and the self-test proves the path by reading its own marker back. Rejected: a thread per row (as in 1.1.1) — each takes a pooled connection |
| **OD-58** | What `Detail` may carry | **Never secrets:** any key matching `password`, `passwd`, `pwd`, `secret`, `token`, `authorization`, `cookie` or `api_key` becomes `"***"` at any depth, before the row is queued. Writes log **field-level summaries** (ids, old → new), never raw request bodies |
| **OD-59** | Volume | **Everything that matters, once:** every `[G]` and `[E]` persists. Every write (non-GET) outcome persists. A read's `[F]` persists once per actor, per distinct window, per 15 minutes, so the 60 s poll stops costing 480 rows per user per 8-hour day. The per-request outcome line persists only at status ≥ 400 or ≥ 2,000 ms ("over 2 s is the box"). The console still prints every line |
| **OD-60** | The nightly purge | **Run it in the app:** a lifespan task, first run 5 minutes after boot and then every 24 h, only where `WORKMATE_DIAG_PURGE=true`. Days come from `DIAG_RETENTION_DAYS` (absent → **60**). The cutoff is the database clock minus the days, computed in Python — portable, no `DATEADD`. Deletes run in batches of ≤ 5,000 rows, with one `[S]` row per run carrying the count, and `dry_run=True` on the first run of any new install. Rejected: SQL Agent (MSSQL-only, and missing on Express) and Windows Task Scheduler (another deploy step to forget) |
| **OD-61** | Who may read the trail | **Dev-only until rights exist:** the `_diag` read and purge routes and the D1b viewer answer only when `WORKMATE_ENV=dev` and return **404** otherwise. The routes stay out of the OpenAPI contract until D1b needs them. The auth slice replaces `is_dev` with an admin role, because the trail is personal information (§9) |

## 8. Evidence owed before the D1a spec — Block D1-E (read-only)

Paste it after Blocks 1 and 2, verbatim, and wait for the prompt between blocks. Nothing selects a password column.

```powershell
cd C:\dev\workmate-saas
Select-String -Path backend\.env -Pattern '^WORKMATE_ENV=','^WORKMATE_DEV_USER_ID='
sqlcmd -S localhost -E -C -d dbWorkmate -W -s "|" -Q "SET NOCOUNT ON; SELECT DB_NAME() AS db; SELECT User_Id, RTRIM(User_Name) AS User_Name, RTRIM(Short_User_Id) AS Short_Id, RTRIM(COALESCE(AD_Login_ID,'')) AS AD_Login, Active FROM dbo.Users WHERE UPPER(COALESCE(Short_User_Id,'')) LIKE '%AZZMAX%' OR UPPER(COALESCE(User_Name,'')) LIKE '%AZZMAX%' OR UPPER(COALESCE(AD_Login_ID,'')) LIKE '%AZZMAX%';"
sqlcmd -S localhost -E -C -d dbWorkmate -W -s "|" -Q "SET NOCOUNT ON; SELECT DB_NAME() AS db; SELECT c.name, t.name AS type_name, c.max_length, c.is_nullable, c.is_identity FROM sys.columns c JOIN sys.types t ON t.user_type_id = c.user_type_id WHERE c.object_id = OBJECT_ID('dbo.Diag_Log') ORDER BY c.column_id; SELECT name, type_desc FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.Diag_Log') AND name IS NOT NULL; SELECT COUNT(*) AS diag_rows FROM dbo.Diag_Log; SELECT RTRIM(System_ConfigCol) AS cfg, RTRIM(System_ConfigVal) AS val FROM dbo.System_Configuration WHERE System_ConfigCol LIKE 'DIAG%';"
sqlcmd -S localhost -E -C -d dbWorkmate_KT -W -h -1 -Q "SET NOCOUNT ON; SELECT DB_NAME(); EXEC sp_helptext 'dbo.fn_Diag_UserTrail'; EXEC sp_helptext 'dbo.vw_Diag_Problems'; EXEC sp_helptext 'dbo.vw_Diag_WhoIsOn';"
```

What it settles:
- **E1** — the current dev actor and env.
- **E2** — Azzmax's `User_Id` and `Active` (OD-56).
- **E3** — `Diag_Log` as it landed on RST: the insert's columns and types (OD-55), plus its row count (0 expected).
- **E4** — whether any `DIAG%` config row exists (OD-60).
- **E5** — KT's three routines, to be ported as portable queries (§6.1). `sp_helptext` is used because `-y 0` cannot be combined with `-h -1`.

## 9. Privacy, in one paragraph

Per-person activity logs are personal information under the Privacy Act 2020. D1 keeps only the minimum support needs: who, when, what screen, what was blocked or broke, and old → new. It keeps no secrets (OD-58), holds rows for 60 days (§5), and is readable by developers only until an admin role exists (OD-61). Tell Redstag what is kept, why, and for how long before their test users start. For the test server, a line in the install notes is enough.

## 10. Where it sits in the two-week cut

S1k smoke → **D1a** → W1 read → auth → W2 / W3 → S2b / S2c → **D1b** → deploy.

D1 adds two slices to a list that was already nine to twelve. Auth before the install is now a condition, not a preference (§5: one identity per person). The morning report Adriaan asked for is KT's Night Shift (`workmate.nightshift` 1.3.2: 05:00, test packs, an Outlook-safe HTML e-mail with the verdict, every FAIL, `Diag_Log` `[E]` of the last 24 h, planner health, a needs-attention list) — its port reads D1a's table, so it follows D1a as its own audited slice. It earns them back in every smoke after S1k, where the trail replaces describing what happened, and again on RST's first support call. W4, S2d and the rest stay after the first drop.

## 11. Consequences for the next doc set

- **Architecture:** D-8 gets persist on, the writer, the fill (OD-55), the volume rule (OD-59) and the purge (OD-60). D-5 notes that the dev actor is Azzmax (OD-56), with `SYS_USER` as the fallback.
- **Landmines:** a persist path that swallows errors needs a counter and a read-back (KT `diag` 1.3.0); the 60 s poll's row cost; use `sp_helptext` for routine bodies (`-y 0` cannot be combined with `-h -1`).
- **Ways of Working:** the trail-read rule (§5).
- **Port Spec:** OD-47 is closed by OD-55; item 28 closes with D1b.
- **Index:** slices D1a / D1b, OD-55…OD-61, and the numbering note (slice D1 ≠ D-1).

## 12. Changelog

- 1.0.1 (2026-09-16) Same day, before any gate. Adriaan's answer recorded: Azzmax is Andrew's own login with full administrator rights, and stamps under it are intended (§1, §5, OD-56); one identity per person makes auth a condition of the Redstag install (§5, §10); the morning report named as the Night Shift port after D1a (§10). Nothing else changed.
- 1.0.0 (2026-09-16) Initial. Built from the Ignition export (the `diag` module, its four queries, the viewer, the consoles, the purge schedule) and the SaaS cards. Adriaan's three statements recorded (§5); OD-55…OD-61 proposed; Block D1-E owed. Nothing signed.
