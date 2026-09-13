# Azztec SaaS — Raw session log 2026-09-13 (docs + the KT database)

**File:** Azztec_SaaS_Raw_Log_2026-09-13_v1_1_0.md · **Version:** 1.1.0 · **Date:** 2026-09-13 · **Author:** Adriaan
**Append-only.** Supersedes §7 (applied), §8 (open list) and §9 (next slice) of `Azztec_SaaS_Raw_Log_2026-09-13_v1_0_0.md`; that log's §1–§6 (the S1g record) still stand.
**Session:** the second of 2026-09-13. The compiled doc set from 1.0.0 §7, then the **KT production database arrived** and was scoped against RST. No build, no slice, nothing written to any database.
**Ended at:** HEAD `c4e17f9`, tree clean. Backend **125 passed** (exit 0), frontend **155 passed in 11 files** (exit 0) — both re-verified on the box this session.

---

## 1. Decisions signed this session

**None.** No OD was signed and no build ran. Everything the KT copy produced is *audit input*, deliberately: §4.1 of the 1.0.0 log made a decision about data unsignable without reading the table, and most of what arrived today is exactly that kind of decision. Two things are now **evidenced but unsigned** — the `Priority.Colour` design (item 29, §5.4) and the KT uplift (item 32, §8).

## 2. Shipped and committed

| Commit | Content |
|---|---|
| **`23c90ea`** | the compiled set from log 1.0.0 §7 — Index **1.4.0**, Landmines **1.4.0**, Ways of Working **1.3.1**, Architecture **1.0.3**, Planner Port Spec **1.0.2**. 5 files, 903 insertions |
| **`c4e17f9`** | `Azztec_SaaS_KT_Schema_Delta_v1_0_0.md`, 162 insertions — the scope/compare Adriaan asked for |
| pending | four oracle reference files into `docs/reference/` (`workmate_pm_engine_code_v2_5_0.py` 65,249 · `workmate_identity_code_v1_1_1.py` 7,892 · `TipBadge_2026-09-10_view.json` 4,953 · `TipPopup_2026-09-10_view.json` 6,972) + this log |

All five compiled docs and the delta report are in project knowledge. The five superseded versions (Index 1.3.0, Landmines 1.3.0, WoW 1.3.0, Architecture 1.0.2, Port Spec 1.0.1) still need removing by hand.

## 3. Suite state

Backend `uv run pytest`: **125 passed, 2 warnings in 5.09 s**, exit 0. Frontend `pnpm test`: **155 passed in 11 files, 2.42 s**, exit 0 — `rules` 55, `PlannerGrid` 14, `WorkerPanel` 11, `WOCard` 10, `FiltersRow` 10, `PlannerView` 10, `CapacityBar` 8, `usePlannerRange` 8, `DayDialog` 7, `SelectedWOCard` 6, `dates` 16. Matches Index §3.5 and Port Spec §8 exactly. Box at the time: 15.8 GB free, no Docker, `sqlservr` below 0.55 GB with `dbWorkmate_KT` attached.

## 4. Mistakes caught this session

### 4.1 The docs were committed before the counts they assert were verified

Index 1.4.0 §3.5 and Port Spec 1.0.2 §8 state 125 and 155. The plan was suites → commit, with "if the counts match, commit" written into the step. The suite block returned **nothing** (§4.2) and the commit ran anyway. The numbers turned out right — they came from the 1.0.0 log, which had verified them — so nothing is false, but for twenty minutes the repo asserted today's state on yesterday's evidence. **A gate you write and don't enforce is not a gate.** Verify first, commit second, and when the verification returns nothing, that is a failed gate, not a passed one.

### 4.2 A `Select-String` filter that matches nothing looks exactly like a suite that ran clean

`uv run pytest | Select-String "passed|failed"` and `pnpm test 2>&1 | Select-String "Test Files|Tests "` both printed blank and returned to the prompt. Run bare, both were green and loud. `pnpm test`'s summary is box-drawn and ANSI-coloured, so the literal pattern never matched. Same family as the `pytest -q` trap in 1.0.0 §4.3: **the filter was wrong, not the run.** Rule: run the suites bare, read the count with your eyes, gate on `$LASTEXITCODE`. Pipe only when the exact output text is already known.

### 4.3 Two sqlcmd flag clashes, both mine

`-W` with `-y 0` → *mutually exclusive*; then `-h -1` with `-y 0` → same. The whole batch aborts before the file is read, so it reads like a query failure and isn't one. `-W` (trim) and `-y 0` (don't truncate long values) cannot ride together: trimmed columns for catalog output, a separate `-y 0` call for a `definition`.

### 4.4 `OBJECT_DEFINITION()` resolved in the wrong database and returned NULL

`SELECT OBJECT_DEFINITION(OBJECT_ID('dbWorkmate_KT.dbo.GetWeekNoAndYear'))` came back NULL and briefly looked like an encrypted module. `OBJECT_ID()` resolves the three-part name fine; **`OBJECT_DEFINITION()` then looks that id up in the current database** — `master` — and finds nothing. Same for `SCHEMA_NAME()`/`OBJECT_NAME()`. Join the remote `sys.*` views instead; `SELECT DB_NAME()` at the top of a cross-database batch makes the trap visible.

### 4.5 The `.bak` was unreadable to the engine, twice, for two different reasons

`sqlcmd -E` authenticates *you*; the backup file is opened by the **service process**. From `C:\Users\Azzte\Downloads`: OS error **5**, access denied, with sysadmin rights and `Test-Path True`. The error code is the diagnosis — **2 = path, 5 = ACL**. Then moving it to `C:\SQLBackups\` and granting on the *folder* changed nothing: **a move within a volume carries the file's original ACL**; only a copy inherits from the destination. `icacls <file> /reset` then grant on the file.

### 4.6 A verification line that silently verified nothing

`Get-CimInstance … | Select-Object Name, StartName` and `Get-Item $bak | Select-Object Name, Length, LastWriteTime` in one block: PowerShell rendered the second object type using the **first one's table format**, so `Length` was dropped without a word and the "is the download intact" check produced no answer. `Format-List` the verification line, or run it in its own block.

### 4.7 Downloads ate the doc cards again

The five compiled-doc cards were presented, then the laptop rebooted before they were saved. Caught only because a Downloads screenshot arrived and the alphabetical gaps were visible. **Second session running that Downloads has destroyed a deliverable** (1.0.0 §4.4 was the S1g spec). The cards were re-presented and saved.

### 4.8 Pasting over a running command

A block pasted while the previous output was still scrolling produced an input echo interleaved with result rows. The file on disk was correct and the re-run was clean, but the paste record was unreadable. Wait for the prompt.

## 5. Verified this session

### 5.1 The KT copy is genuine and is now on the box

`RESTORE HEADERONLY`: server **`KTSQL02`**, SQL Server 2022 (16.0.4275), backup by `TMCLIMITED\SQLServiceAccount`, full, uncompressed, 78,731,776 bytes, taken 2026-09-13 00:32:36–38 in 2 seconds. Files `D:\SQLData\dbWorkmate.mdf` (95 MB) and `E:\SQLLogs\dbTLL_log.ldf` (16 MB), compat level 100, created 2026-02-13. Restored as **`dbWorkmate_KT`** `WITH MOVE` to the instance defaults, 9,457 pages in 0.08 s, then **`SET READ_ONLY`**. `dbWorkmate` (RST) untouched at compat 170.

**One-way door:** the restore upgraded the physical version **957 → 998**. Nothing from AzztecDev (SQL 2025) can ever be restored onto KTSQL02 (SQL 2022). Relevant to any future "push a fix back to KT" idea.

### 5.2 The delta, in full

Recorded in `Azztec_SaaS_KT_Schema_Delta_v1_0_0.md`, not repeated here. Headline: KT 280 tables / 24 views / 1099 procs against RST 255 / 67 / 1121. **46 KT-only tables → 21 real** (5 the port needs, 2 that shape identity and tips, 7 belonging to other modules, 6 KT-specific, 1 orphan) and **25 junk** (6 `sqlth_*` historian, 16 in a personal `TMCLIMITED\PrinslooA` schema, 3 May repair backups). **10 real column additions**, 47 more on `TEMP_*` staging that are not ours. RST's extra 48 views / 27 procs / 17 functions are its own site reporting layer — a constraint on the uplift (don't rename or retype under them), not scope.

Method worth keeping: **the database says what exists, the gateway export says what is used.** Every candidate was grepped against the 2026-09-10 project export (1,986 views, 1,700 named queries, 382 scripts). That is what exposed `Ignition_Tip_Definitions` as an orphan and confirmed the other twenty are live.

### 5.3 `WO_N_Plan` read, not invented

Nine columns (`WO_ID numeric(18,0)` PK clustered, `Pinned char(1) NOT NULL DEFAULT 'N'`, `Pinned_By`, `Pinned_On`, `Prev_Start`, `Note varchar(255)`, `Server_Name varchar(50)`, `Entry_Date NOT NULL DEFAULT getdate()`, `Last_Save_Date`). All four KT rows are `Pinned = 'N'` with `Prev_Start` at the engine date and `Note = 'Planner move 2026-09-07 -> 2026-09-08'`: the row persists, the flag flips, `Prev_Start` is undo's target. `Server_Name = 'Perspective'` — OD-3's swap confirmed as real. **Pinning is barely used at KT: 4 rows.** S3's migration 0002 is now a transcription.

### 5.4 Item 29 has evidence on both sides

KT `dbo.Priority`: **A / B / C / D at `Sort_Sequence` 1–4, no ties, `#FF8000` on all four** — so the oracle's badge colour comes from the **letter class in CSS**, and `Colour` carries nothing usable there. RST: fourteen rows, four tied at sequence 1, `Colour` populated and varied. The Landmines claim carried since 2026-09-11 is now verified against the table rather than remembered. Implied design, for the audit to sign: paint from the payload where the colours vary, leave `.pri.A–D` to carry the oracle's colouring where every row matches.

### 5.5 Identity, diagnostics, tips

`Ignition_User_Map` — `Ignition_Username nvarchar(100)` UQ → `Workmate_User_ID numeric(18,0)` **FK to `Users.User_Id`**, `Active`, stamps; read by `identity` 1.1.1 with a self-healing auto-insert. That is OD-2's precedent and the shape `App_User` (D-5) should inherit. `Diag_Log` — the table `diag.py` already names, with `Session_Id`/`Source`/`Tier`/`Msg_Level` **NOT NULL**, which the SaaS must decide how to fill before persist mode. Tips — content lives in each view's JSON (`TipBadge`/`TipPopup` render it), state in `Ignition_Onboarding_Prefs` via four one-line named queries; the 19-row definitions table is a seed nobody reads.

### 5.6 Orphans

Gateway references **and** DB dependencies both zero for `GetWeekNoAndYear`, `wmsp_GetNextWOId`, `wmsp_GenerateShortWOId`, `vw_SchedulexCount`, and no module anywhere mentions `PO_Header.Status_Pre_Archive`. `GetWeekNoAndYear` is still worth keeping as a **reference** — with `pm_engine` 2.5.0's verbatim `GetWeekNoANDYear` port and KT's own `Week_No` data, S2's `test_weekno.py` gets three independent sources. Its body (T8) is the one query still outstanding; it blocks nothing.

## 6. Doc-correction queue

**Apply before the next audit** (one docs commit):

- **Landmines → 1.5.0:** the seven entries in delta §9 — §A the PowerShell format-table hijack and the Downloads repeat; §B the `.bak` service-account ACL rule (error 2 vs 5), move-keeps-ACL, the `OBJECT_DEFINITION` cross-database trap, the `sqlcmd` flag exclusions, the restore-upgrades-the-version one-way door; §C nothing new; §F nothing new.
- **Ways of Working → 1.3.2:** §6 — run the suites **bare** and gate on the exit code, never on a `Select-String` whose pattern is a guess (§4.2); §2 — verify before you commit, and a verification that returns nothing is a failure (§4.1).
- **Index → 1.5.0:** §3.1 gains the delta report; §3.7 gains the four `docs/reference/` files; §5 gains the `dbWorkmate_KT` row; §6 the reordered queue; §6.2 the five superseded docs still to remove.
- **Port Spec → 1.0.3:** §9 item 26 reclassified (copy obtained, `parity_range.py` still unbuilt); the OD-1 and OD-3 evidence from §5.3; item 29's evidence from §5.4.
- **Architecture → 1.0.4:** §3.3 the `dbWorkmate_KT` oracle copy; D-8 the `Diag_Log` contract; D-12 the `forecast` schema question.
- Still carried, still unapplied (fifth session): Install doc, Bootstrap, `.gitignore` symlinks, Scaffold_Repo 1.0.2, the two `.vscode` files.

## 7. Open list

**Reclassified: 26** — the KT dev copy is **obtained and restored**; what remains is `scripts/parity_range.py` itself, plus a `svc_workmate` user inside `dbWorkmate_KT` (read-write flip, create, flip back). No longer blocked, still open.

Carried: **4** (six-month summary shape), **17** (Docker's first clean start under the cap), **21** (`initialsOf` on parentheses), **24** (hidden-tab poll untested), **25** (prettier not in the smoke), **27** (`WeekStrip` / `CapacityBar` 1.0.1 `nWorkers`), **28** (`/_diag/client` and `?debug=1`), **29** (`Priority.Colour` — now evidenced both sides, §5.4), **30** (alternating `/range` latency, DMV wait types first), **31** (the Forensics pack, set aside).

New:

- **32 — the KT uplift.** One additive, hand-written migration scripted from `dbWorkmate_KT`'s catalog, never typed. Nine questions in delta §8 decide its scope; the sharp ones are whether `WO_N_Plan` lands on RST now (which flips `pinTable` true and makes 2,364 engine-owned PMs pin-movable — OD-1's intended end state, but it changes what the S1 screenshots showed), how the migrations are numbered against S3's 0002, and what fills `Diag_Log`'s NOT NULL columns.
- **33 — the tips ⓘ, Planner first.** Adriaan's idea; KT built the pattern and the Planner never got a tip. It is the **first non-port component**, so it carries the Tailwind/shadcn decision OD-27/OD-31 parked. Its own audit; blocks nothing.
- **34 — carry-backs to KT** (not the SaaS's work, but write them down): the duplicate `PO_Email_Log` index, the 25 junk tables, the four orphan routines, `Status_Pre_Archive`, and `.chip{flex:none}` from Landmines §C.

## 8. Next

Unchanged in shape, longer by one: **backend audit** (30 latency with DMV evidence, 29 `Priority.Colour`, 21 `initialsOf`) → **uplift audit** (32) → **S2** (move / undo / estimate — the first slice that writes to RST, `dry_run=True` first). Tips (33) is its own audit whenever Adriaan wants it.

Before any of them: §6's doc set. The next audit reads the docs, not this log.

## 9. Changelog

- 1.1.0 (2026-09-13) Second session of the day. The 1.0.0 §7 doc set applied and committed (`23c90ea`); the KT production database (`KTSQL02`, 2026-09-13 00:32) restored read-only as `dbWorkmate_KT` and scoped against RST; `Azztec_SaaS_KT_Schema_Delta_v1_0_0.md` written and committed (`c4e17f9`); four oracle reference files extracted from the 2026-09-10 project export; both suites re-verified green. No OD signed, no build, nothing written to any database. Item 26 reclassified; items 32, 33, 34 opened. Eight mistakes recorded, seven of them new landmines.
