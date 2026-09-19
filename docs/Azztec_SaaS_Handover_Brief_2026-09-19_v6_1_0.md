# Azztec SaaS — Handover Brief

**File:** Azztec_SaaS_Handover_Brief_2026-09-19_v6_1_0.md · **Version:** 6.1.0 · **Date:** 2026-09-19 · **Author:** Adriaan
**For:** the first message of the next chat. Paste this whole file. Supersedes 6.0.0 (same day — restructured into steps, HEAD corrected after the brief's own commit).
**Target path:** `docs/Azztec_SaaS_Handover_Brief_2026-09-19_v6_1_0.md` (+ project knowledge; 5.0.0 and 6.0.0 can leave PK)

---

## A. State (read once, then work the steps)

HEAD **`d53267e`**, tree clean. Session 2026-09-16 → 09-19 shipped three slices:

| Tag | Commit | What |
|---|---|---|
| `s1k-shell-1.0.0` | `d17bac6` | the KT navigation shell (`web/src/features/shell/`) |
| `d1a-persist-1.0.0` | `c7de038` | diagnostics persisting to `dbo.Diag_Log`, the actor on every row |
| `w1a-api-1.0.0` | `797948a` | the WOMaint **read** API — six `GET`s under `/api/v1/workorders`, 26 paths |

Suites bare: backend **319 passed, 2 skipped** · frontend **205 passed in 15 files** · `ruff check` **and `ruff format --check`** clean · eslint clean · all exit 0. App **0.5.0**, contract `docs/api/openapi_0_5_0.json` (one contract file on disk, ever). OD series at **71**, open items at **55**. Dev actor **21 — `Azzmax logon`**. **The doc set is current** (Index 1.10.0, Landmines 1.10.0, WoW 1.4.0, Port Spec 1.0.8, Architecture 1.0.9) — nothing queued, first time since 09-15. **Next slice: W1b, the WOMaint page.**

---

## B. The steps

### Step 1 — Read, in this order. Nothing else first.

1. this brief
2. `Azztec_SaaS_Raw_Log_2026-09-19_v1_2_0.md` — §9 the 55 open items · §10 next · §4c W1a's smoke measured · §6 the seventeen mistakes · §5 the RST facts the WOMaint audit turned up
3. `Azztec_SaaS_Project_Knowledge_Index_v1_10_0.md` §1 and §6
4. `Azztec_SaaS_Ways_of_Working_v1_4_0.md` · `Azztec_SaaS_Platform_Landmines_v1_10_0.md` **§E before any WOMaint work**

The doc set is current, so audit from the docs, not the log.

### Step 2 — Block 1: the box and the suites. Paste verbatim, wait for the prompt.

```powershell
cd C:\dev\workmate-saas
git log --oneline -3; git status --short
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object OwningProcess | Format-Table
Get-CimInstance Win32_OperatingSystem | Select-Object @{n='FreeGB';e={[math]::Round($_.FreePhysicalMemory/1MB,1)}} | Format-Table
cd backend; uv run alembic current; uv run ruff check .; uv run ruff format --check .; uv run pytest; "$LASTEXITCODE"
cd ..\web; pnpm test; "$LASTEXITCODE"
```

Expect: HEAD `d53267e`, clean tree, **no listener** on 8000, `0001 (head)`, both ruff gates clean, **319 passed, 2 skipped** and **205 passed in 15 files**, exit 0 both. Anything else means the tree moved since this brief.

*If a listener is there:* stop the **server child**, not the reloader, then prove exactly one — or zero — PID listens (Landmines §A).

### Step 3 — Upload the live WOMaint screenshot.

The pixel reference for W1b, and the last input the audit is missing. It goes into `docs/reference/` when the slice is cut. Everything else W1b needs is already on disk: the `WOMaint` view v16.28.3 and the four symbols in `docs/reference/`, stylesheet v2.69 on the box, the generated client in `web/src/api/client/`.

### Step 4 — W1b audit → spec → 🤙 → build → smoke → trail → log.

**Scope, from the W1a spec §1 "Not in this slice":** the list panel (four type chips, two mode chips, the coloured id badges), the record on the oracle's CSS, the four read-only tabs (Linked · Event History · Query/Notes · POs), `MenuItem_WOMaint` live, `activeKeyFor` gaining `['/workorders','womaint']`. **Closes OD-5 in full.** No writes — those are W2/W3.

**Two open items are W1b's to settle:** **53** read speed on RST (`search` 851 ms, `includeArchive=2` 1,167 ms, against the record's 122 ms) · **54** `wm-seg-9px` has no rule in stylesheet v2.69.

**Inherited and not re-litigated:** OD-64 paging with `more` and no total · OD-67 `progressAll` drives the picture row (RST has eight active rows; 2,750 open WOs sit at 7/8, which the oracle's six cards would leave dark) · OD-68 an archived id is a named 404 · OD-71 `filtersFor` tells the page which list the record belongs to.

### Step 5 — Close the session properly.

Raw log → the doc updates it implies → the next handover brief. Carry forward every open item not closed.

### Step 6 — Project knowledge housekeeping.

**Add the pack** in §C below. **Remove** what Index 1.10.0 §6.2 lists — the list is four sessions deep, and a superseded version left in PK is the one the next audit reads by mistake. Raw logs are the exception: every version stays.

### Step 7 — Chase Andrew's user list.

It is the only thing on the critical path to the Redstag install that nothing else can move: auth (`App_User`, argon2, sign-in) is a **condition** of the install, not an option, and it cannot start without the list. Everything else in §D is nice-to-have.

---

## C. The project-knowledge pack for this session

| File | PK |
|---|---|
| `Azztec_SaaS_Handover_Brief_2026-09-19_v6_1_0.md` | add — replaces 5.0.0 and 6.0.0 |
| `Azztec_SaaS_Project_Knowledge_Index_v1_10_0.md` | add — replaces 1.9.0 |
| `Azztec_SaaS_Ways_of_Working_v1_4_0.md` | add — replaces 1.3.6 |
| `Azztec_SaaS_Platform_Landmines_v1_10_0.md` | add — replaces 1.9.0 |
| `Azztec_SaaS_Architecture_and_Stack_v1_0_9.md` | add — replaces 1.0.8 |
| `Azztec_SaaS_Planner_Port_Spec_v1_0_8.md` | add — replaces 1.0.7 |
| `Azztec_SaaS_Raw_Log_2026-09-19_v1_2_0.md` | add — replaces 1.1.0 |
| `Azztec_SaaS_W1a_WOMaint_Read_Api_Chunk_Spec_v1_0_1.md` | add — replaces 1.0.0 |

The W1a code cards (`app/workorders/*` 1.0.0, the three test files, `main.py` 1.0.8, `test_openapi_contract` 1.1.1, `openapi-ts.config.ts` 1.0.3) and the six `docs/reference/` cards are already in PK at their shipped versions — leave them.

---

## D. Still owed from Adriaan

1. **Andrew's user list for RST** (OD-2 / D-5) — blocks the auth slice, which is a condition of the install. Step 7.
2. The live WOMaint screenshot — Step 3.
3. Which mail the box may send through for the morning report (the KT mail server the Night Shift uses, Microsoft 365, or something else).
4. Redstag to be told what the trail keeps, why, and for how long (Privacy Act 2020; D1 audit §9) before their test users start.

---

## E. The cut (four days used — install target ~2026-09-30)

Done: S1k, D1a, W1a. Then: **W1b** → **auth minimal** → **W2 + W3** (WOMaint writes; `dry_run=True` first — the first WO written to RST; the five legacy procs are in the W1a spec §2.4) → **S2b + S2c** (planner move / undo / estimate) → **D1b** (Diagnostics Viewer, browser errors) → **deploy**. After the first drop: W4, S2d, activity actuals, attachments, POs, tips, the brand read, rights, the morning report.

---

## F. Rules this session added (all in Landmines 1.10.0 / WoW 1.4.0 — don't relearn them)

1. **`ruff format --check` is its own gate, repo-wide, every slice.** It found five reflows in `main.py` that shipped three days earlier — `ruff check` can never see them (E501 is ignored). Second occurrence.
2. **A spec's test counts are read from the cards before the drop**, and a count that moved is a spec re-cut, not a note in the log.
3. **Cross-check a card against itself by script** — repo keys against SQL aliases, repo keys against schema fields.
4. **Export the module, not the project** — fourteen small Designer exports beat a 33 MB zip; prove the overlap byte-identical before trusting either.
5. **Predict what must *not* be in the trail**, not just what must.
6. **"`Diag_Log` unchanged" is unprovable with a server up** — the claim is "no row from the suite", and every difference is accounted for by name.
7. **The drop block catches a `(1)` double download.**

## G. Changelog

- 6.1.0 (2026-09-19) Restructured as numbered steps; HEAD corrected to `d53267e` (6.0.0's own commit moved it); the PK pack listed in §C; §D makes Andrew's user list the one critical-path item.
- 6.0.0 (2026-09-19) After W1a and the doc set. Replaced 5.0.0 (same day).
- 5.0.0 (2026-09-19) After S1k + D1a. Replaced 4.0.0 (2026-09-15).
