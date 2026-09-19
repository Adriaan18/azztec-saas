# Azztec SaaS — Handover Brief

**File:** Azztec_SaaS_Handover_Brief_2026-09-19_v6_0_0.md · **Version:** 6.0.0 · **Date:** 2026-09-19 · **Author:** Adriaan
**For:** the next session's first read, before the Index. Written at the close of the S1k + D1a + **W1a** session (2026-09-16 → 09-19). Supersedes the 5.0.0 brief of the same day.
**Target path:** `docs/Azztec_SaaS_Handover_Brief_2026-09-19_v6_0_0.md` (+ project knowledge; the 5.0.0 brief can leave PK)

---

## 1. State in one paragraph

HEAD **`14c340c`**, tree clean. Three tags this session: **`s1k-shell-1.0.0`** at `d17bac6` (the KT navigation shell), **`d1a-persist-1.0.0`** at `c7de038` (diagnostics persisting to `dbo.Diag_Log`), **`w1a-api-1.0.0`** at `797948a` (the WOMaint read API — 26 paths). Suites bare: backend **319 passed, 2 skipped**, frontend **205 passed in 15 files**, `ruff check` **and `ruff format --check`** clean, eslint clean, all exit 0. App version **0.5.0**, contract `docs/api/openapi_0_5_0.json` (one contract file on disk, ever). OD series at **71**, open items at **55**. The dev actor is **21 — `Azzmax logon`**. **The doc set is current** — Index 1.10.0, Landmines 1.10.0, Ways of Working 1.4.0, Port Spec 1.0.8, Architecture 1.0.9, all committed in `14c340c`; nothing is queued, for the first time since 09-15.

## 2. What shipped, and why it matters for the next slice

| | What | Why it matters next |
|---|---|---|
| **S1k** | `web/src/features/shell/` — header + rail on the oracle's CSS; only Plannex navigates; the active key comes from the router path | **W1b lights `MenuItem_WOMaint`**: one row in `activeKeyFor` (`/workorders` → `womaint`) and the rail item goes live; the record renders in the shell's main cell like the planner |
| **D1a** | `diag.py` 1.2.0 writes `Diag_Log`; the actor on every row; trail routes dev-only; the in-app purge at 60 days | Every write W2/W3 makes is traceable from the day it lands. The purge has now proved itself twice, unprompted, five minutes after a boot |
| **W1a** | `app/workorders/` — six `GET`s: the list (`Search` v12's two arms as three statements, paged), the record (23 joins, labels resolved, `filtersFor`), and the Linked / Events / Queries / POs tabs. `main.py` 0.5.0, client regenerated | **W1b consumes it whole** — every read is one generated hook away, and `web/src` was untouched, so the page starts from a clean frontend |
| Reference | six W1a cards in `docs/reference/`: the `WOMaint` view v16.28.3 (588 KB), the four symbols, the NQ addendum | W1b's oracle is on disk. Still owed: **the live WOMaint screenshot** |

## 3. Decisions this session hands on

- **OD-62…OD-71 are delegated, not signed** (answered one by one at the W1a gate, the OD-50…54 precedent). A 🤙 on `Azztec_SaaS_W1a_WOMaint_Read_Api_Chunk_Spec_v1_0_1.md` converts all ten. The ones W1b inherits directly: paging with `more` and no total (OD-64), a named 404 for an archived id (OD-68), `progressAll` driven by `dbo.Progress` rather than the six-card picture row (OD-67), `filtersFor` on the record (OD-71).
- **OD-5 is half-closed.** The record reads; the `/workorders/$id` route and the `Open in WO Maintenance` button arrive with W1b.
- **`refs` waits for W3** (OD-66) — a read resolves its own labels regardless of `Active`; the thirteen `…/Dropdown` reads are for editing.
- **Read lines print, they do not persist** (OD-69). The trail stays for writes and failures.
- **Azzmax (21) is the test identity**, so one login per person is a condition of the Redstag install. Andrew is its first administrator.

## 4. Rules learned the hard way this session (all in Landmines 1.10.0 / WoW 1.4.0)

1. **`ruff format --check` is its own gate, repo-wide, every slice.** It caught five reflows in `main.py` that had shipped three days earlier in D1a's cards — `ruff check` can never see them, because E501 is ignored. Second occurrence of the same lesson.
2. **A spec's test counts are read from the cards before the drop.** W1a's draft said 307; the cards totalled 319. The spec was reissued as 1.0.1 the same day rather than left describing something that no longer existed.
3. **Cross-check a card against itself by script** — repo keys against SQL aliases, repo keys against schema fields. Nothing came back at the smoke.
4. **Export the module, not the project.** Fourteen small Designer exports beat a 33 MB zip; the 48 named queries shared with the earlier export were proven byte-identical by script, so only the eight new ones needed a card.
5. **Predict what must *not* be in the trail.** Five `[G]`s and no `[F]` from a 200 was the prediction; reading exactly that is what proved OD-69.
6. **"`Diag_Log` unchanged" is unprovable with a dev server up.** The claim is "no row from the suite" — count before and after and account for every difference by name. The two unexplained rows were a 404 doing its job and the purge task.
7. **The drop block should catch a `(1)` double download** — one landed in `docs/reference/` and was renamed before the commit.

## 5. The cut (four days used — install target ~2026-09-30)

Done: S1k, D1a, W1a. Remaining, in order: **W1b** (the WOMaint page; closes OD-5 in full; ~1 session) → **auth minimal** (`App_User`, argon2, sign-in; a condition of the install; **blocked on Andrew's user list**) → **W2 + W3** (WOMaint writes; `dry_run=True` first — the first WO written to RST; the five legacy procs are in the W1a spec §2.4) → **S2b + S2c** (planner move / undo / estimate) → **D1b** (the Diagnostics Viewer, browser errors) → **deploy**. After the first drop: W4, S2d, activity actuals, attachments, POs, tips, the brand read, rights, the morning report.

## 6. The next session, step by step

1. Read this brief, then **`Azztec_SaaS_Raw_Log_2026-09-19_v1_2_0.md`** (§9 the 55 items, §6 the seventeen mistakes, §4c W1a measured), then Index **1.10.0** §1 and §6. The doc set is current — audit from the docs, not the log.
2. **Block 1 — the box and the suites** (paste verbatim):
   ```powershell
   cd C:\dev\workmate-saas
   git log --oneline -3; git status --short
   Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object OwningProcess | Format-Table
   Get-CimInstance Win32_OperatingSystem | Select-Object @{n='FreeGB';e={[math]::Round($_.FreePhysicalMemory/1MB,1)}} | Format-Table
   cd backend; uv run alembic current; uv run ruff check .; uv run ruff format --check .; uv run pytest; "$LASTEXITCODE"
   cd ..\web; pnpm test; "$LASTEXITCODE"
   ```
   Expect: HEAD `14c340c`, clean tree, **no listener** (or stop it — the child, not the reloader), `0001 (head)`, both ruff gates clean, **319 / 2** and **205 / 15**.
3. **Upload for the W1b audit:** the **live WOMaint screenshot** (the pixel reference — it belongs in `docs/reference/` when the slice is cut). Everything else W1b needs is already on disk: the `WOMaint` view and the four symbols in `docs/reference/`, the stylesheet v2.69 on the box, the generated client.
4. **W1b audit → spec → 🤙 → build**, one slice, the trail read at the end. Two open items are its to settle: **53** (read speed on RST — the search at 851 ms and the archive arm at 1,167 ms) and **54** (`wm-seg-9px` has no rule in stylesheet v2.69).
5. **Project knowledge:** add this brief and the five compiled docs; work Index 1.10.0 §6.2's removal list — it is four sessions deep and it is the list that decides what the *next* audit reads by mistake.

## 7. Open questions for Adriaan (none blocking W1b)

- **Andrew's user list for RST** (OD-2 / D-5) — the auth slice cannot start without it, and auth is a condition of the install. This is the one item nothing else can unblock.
- Which mail may the box send through for the morning report — the KT mail server the Night Shift uses now, Microsoft 365, or something else?
- Redstag should be told what the trail keeps, why, and for how long (Privacy Act 2020; D1 audit §9) before their test users start.

## 8. Changelog

- 6.0.0 (2026-09-19) After W1a and the doc set. Replaces 5.0.0 (same day): HEAD, tags, 319 / 2, app 0.5.0, OD-71 / item 55, the doc set current, next is W1b.
- 5.0.0 (2026-09-19) After S1k + D1a. Replaced 4.0.0 (2026-09-15).
