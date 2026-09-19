# Azztec SaaS — Handover Brief

**File:** Azztec_SaaS_Handover_Brief_2026-09-19_v5_0_0.md · **Version:** 5.0.0 · **Date:** 2026-09-19 · **Author:** Adriaan
**For:** the next session's first read, before the Index. Written at the close of the S1k + D1a session (2026-09-16 → 09-19). Supersedes the 2026-09-15 v4.0.0 brief.
**Target path:** `docs/Azztec_SaaS_Handover_Brief_2026-09-19_v5_0_0.md` (+ project knowledge; the 09-15 brief can leave PK)

---

## 1. State in one paragraph

HEAD **`d13819c`** (after the five-doc commit that follows this brief it moves once more), tree clean. Tags this session: **`s1k-shell-1.0.0`** at `d17bac6` (the KT navigation shell, 17 paths) and **`d1a-persist-1.0.0`** at `c7de038` (diagnostics persisting to `dbo.Diag_Log`, 14 paths). Suites bare: backend **218 passed, 2 skipped**, frontend **205 passed in 15 files**, ruff and eslint clean, all exit 0. OD series at **61** (OD-50…54 delegated and accepted; OD-55…61 signed). Open-item series at **52** (46–52 raised this session). The dev actor is **21 — `Azzmax logon`**. `Diag_Log` holds real rows from real processes; the trail-read rule now reads them.

## 2. What shipped, and why it matters for the next slice

| | What | Why it matters next |
|---|---|---|
| **S1k** | `web/src/features/shell/` — header + rail ported from `HeaderToolbar` v16.47 / `SideMenu` v4.20 on the oracle's CSS; `__root.tsx` 1.0.0 owned; only Plannex navigates; active key from the router path | **W1 lights `MenuItem_WOMaint` with one row** in `activeKeyFor` and `live: true`; the WO record renders in the shell's main cell like the planner |
| **D1a** | `diag.py` 1.2.0 writes to `Diag_Log` (one writer, bounded queue, batches); `deps.py` 1.1.0 puts the actor on `request.state`; `app/diag/` trail routes dev-only; purge in-app at 60 days; `Show-DiagTrail.ps1` | **Every write W2/S2b makes is traceable from the day it lands.** Read the trail after every test (Ways of Working §6.1) |
| Audits | `WOMaint_Audit_Brief_v1_0_0.md` (scope, W1–W4 cut, nine ODs to sign, the RST evidence to paste) · `D1_Forensic_Trail_Audit_v1_0_1.md` | W1's spec starts from the brief's §5 and §6 |
| Reference | the two navigation views, `workmate_workorder_code_v1_8_1.py`, `WO_Named_Queries_2026-09-16.md` in `docs/reference/` | W1–W4's oracle is on disk and in PK |

## 3. Decisions taken this session that the next session inherits

- **Azzmax (21) is the test identity** — Andrew's administrator login; his changes are meant to carry his name. Consequence: **one login per person, so sign-in is a condition of the Redstag install**, not an option. Andrew is its first administrator. The password is never used by the SaaS and never written anywhere.
- **`Diag_Log` retention is 60 days**, `System_Configuration` key `DIAG_RETENTION_DAYS`, absent → 60 (it is absent on RST today).
- **The trail-read rule** is standing (Ways of Working §6.1): predict the trail in the spec, read it after the test with `scripts\Show-DiagTrail.ps1 -UserId 21 -Minutes 15`, wait two seconds first.
- **The morning report** is KT's Night Shift (`workmate.nightshift` 1.3.2 — 05:00, test packs, HTML e-mail with verdict, failures, last-24 h `[E]`s, planner health). Its port is its own slice after D1a. **Still owed from Adriaan: which mail the box may send through.**
- **Doc set is current** as of this commit: Index 1.9.0, Landmines 1.9.0, Ways of Working 1.3.6, Port Spec 1.0.7, Architecture 1.0.8. Nothing queued.

## 4. Rules learned the hard way this session (all in Landmines 1.9.0 / WoW 1.3.6)

1. **Read the newest raw log before the Index.** Missing log 09-15 on 09-16 cost two wrong OD numbers and a stale baseline — caught before the build, but it should not have needed catching.
2. **Stop the server before a drop.** `fastapi dev` reloaded onto D1a's files as they landed and wrote the first four `Diag_Log` rows before the suite ran.
3. **Killing the uvicorn reloader orphans the server child on Windows.** It keeps the port and its cached settings; prove exactly one PID listens on 8000 before believing any response.
4. **`pytest` must never write to RST.** Persistence is off under `WORKMATE_ENV=test`; `test_kt_uplift` names the tables written by design.
5. **Smoke, then commit.** D1a's commit went in one step early. The tag stood only because the suites were green and the proof came ten minutes later.
6. **Download every card before the drop block**, and `Unblock-File` every `.ps1`.
7. **Measure the screenshot**, don't eyeball it — pixel samples settled the underline, the gradient, the dialog dim and the rail state in seconds.

## 5. The two-week cut (three days used — install target ~2026-09-30)

Done: S1k, D1a. Remaining, in order: **W1** (WOMaint read — the API and a read-only record; closes OD-5; ~1 session) → **auth minimal** (`App_User`, argon2, sign-in; a condition of the install; needs Andrew's user list — raise with Redstag now) → **W2 + W3** (WOMaint writes: create / edit / status / progress; `dry_run=True` first — the first WO written to RST) → **S2b + S2c** (planner move / undo / estimate) → **D1b** (the Diagnostics Viewer page, browser errors) → **deploy**. After the first drop: W4 (delete / clone / linked), S2d (drag-and-drop), activity actuals, attachments, POs, tips, the brand read, rights, the morning report.

## 6. The next session, step by step

1. Read this brief, then **`Azztec_SaaS_Raw_Log_2026-09-19_v1_1_0.md`** (§9 the 52 items, §6 the twelve mistakes, §4b D1a measured), then Index 1.9.0 §1 and §6.
2. **Block 1 — the box and the suites** (paste verbatim):
   ```powershell
   cd C:\dev\workmate-saas
   git log --oneline -3; git status --short
   Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object OwningProcess
   cd backend; uv run pytest; "$LASTEXITCODE"
   cd ..\web; pnpm test; "$LASTEXITCODE"
   ```
   Expect: HEAD on the docs commit, clean tree, **no listener** (or stop it), **218 / 2** and **205 / 15**.
3. **Block W1-E — read-only evidence for the W1 spec** (the WOMaint brief §6, "Evidence to paste"):
   ```powershell
   sqlcmd -S localhost -E -C -d dbWorkmate -W -s "|" -Q "SET NOCOUNT ON; SELECT DB_NAME() AS db; SELECT 'WO_N_Header' t, COUNT(*) n FROM dbo.WO_N_Header UNION ALL SELECT 'WO_N_Details', COUNT(*) FROM dbo.WO_N_Details UNION ALL SELECT 'WO_Status', COUNT(*) FROM dbo.WO_Status UNION ALL SELECT 'WO_Short_IDs', COUNT(*) FROM dbo.WO_Short_IDs UNION ALL SELECT 'WO_Event_History', COUNT(*) FROM dbo.WO_Event_History UNION ALL SELECT 'WO_N_Resource', COUNT(*) FROM dbo.WO_N_Resource UNION ALL SELECT 'WO_N_Activity', COUNT(*) FROM dbo.WO_N_Activity UNION ALL SELECT 'WO_C_Header', COUNT(*) FROM dbo.WO_C_Header; SELECT LEFT(RTRIM(Short_WO_Id), 3) AS prefix, COUNT(*) AS n FROM dbo.WO_N_Header GROUP BY LEFT(RTRIM(Short_WO_Id), 3) ORDER BY n DESC;"
   sqlcmd -S localhost -E -C -d dbWorkmate -W -s "|" -Q "SET NOCOUNT ON; SELECT TOP 5 WO_ID, RTRIM(Short_WO_Id) AS Short_WO_Id, RTRIM(WO_Title) AS WO_Title, RTRIM(Status) AS Status, Progress, Request_Start_Date, Last_Save_Date FROM dbo.WO_N_Header ORDER BY WO_ID DESC;"
   sqlcmd -S localhost -E -C -d dbWorkmate -W -h -1 -Q "SET NOCOUNT ON; EXEC sp_helptext 'dbo.wmsp_WO_StatusInsert'; EXEC sp_helptext 'dbo.wmsp_WO_N_HeaderInsert'; EXEC sp_helptext 'dbo.wmsp_WO_N_DetailsInsert'; EXEC sp_helptext 'dbo.wmsp_WO_N_DetailsInsertUpdate'; EXEC sp_helptext 'dbo.wmsp_WO_StatusDelete';"
   ```
   If a table name in the first query does not exist on RST, the error names it — paste it, don't fix it; the audit needs to know.
4. Upload for the W1 audit: the WOMaint screenshot (09-19) and, from the box, `MainSCADA_Timberlands_2026-09-16_1307.zip` (the WOMaint view, `WOActivityPanel`, the popups) — extracted as versioned cards, never carried as a zip.
5. **W1 audit → W1 spec → 🤙 → build**, one slice, the trail read at the end.

## 7. Open questions for Adriaan (none blocking W1)

- Which mail may the box send through for the morning report — the KT mail server the Night Shift uses now, Microsoft 365, or something else?
- Andrew's user list for RST (OD-2 / D-5) — the auth slice cannot start without it.
- Redstag should be told what the trail keeps, why, and for how long (Privacy Act 2020; D1 audit §9) before their test users start.

## 8. Changelog

- 5.0.0 (2026-09-19) After S1k + D1a. Replaces 4.0.0 (2026-09-15).
