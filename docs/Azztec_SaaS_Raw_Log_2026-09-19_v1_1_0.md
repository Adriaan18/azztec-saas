# Azztec SaaS — Raw Log 2026-09-19

**File:** Azztec_SaaS_Raw_Log_2026-09-19_v1_1_0.md · **Version:** 1.1.0 · **Date:** 2026-09-19 · **Author:** Adriaan
**Status:** Session record, append-only. The session opened 2026-09-16 and closed the S1k build on 2026-09-19; both dates appear on cards, which is why the shell cards carry 09-16 and the two test re-cuts carry 09-19. **1.1.0 adds D1a** — specced, gated, built, smoked and tagged the same day (§2, §4b, §6). The doc set (§8) is still the one thing not cut.
**Target path:** `docs/Azztec_SaaS_Raw_Log_2026-09-19_v1_1_0.md` (+ project knowledge; replaces 1.0.0)
**Parent:** log 2026-09-15 1.0.0 (its doc-correction queue is **still unapplied** — §8 carries it forward with today's additions).

---

## 1. Decisions this session

| ID | What | State |
|---|---|---|
| **OD-50** | The shell is a port on the oracle's own CSS: `features/shell/`, `data-name` = the oracle's `meta.name`, styles scoped `.wm-shell`, glyphs inline, mounted in `__root.tsx`. No shadcn, no lucide, no Tailwind classes, no `pnpm add` | Taken on "go" (09-16) as **delegated**, built, then **accepted on review** at the smoke (09-19, "this looks perfect"). No separate 🤙 |
| **OD-51** | Only Plannex navigates. Every other control draws as the oracle draws it and does nothing: `cursor: default`, `aria-disabled`, `title="arrives with … (OD-51)"`. Live as well: the clock, `fsBtn` (Fullscreen API), rail Print (`window.print()`) | as above |
| **OD-52** | Gated items: VisualX, the search pill and the Users button are not rendered; logout and the tips toggle are drawn inert | as above |
| **OD-53** | Brand is the constant `AZZTEC`; **WORKMATE mode cut** — its logo PNG never arrived | as above |
| **OD-54** | The day dialog is contained: `.wm-planner{position:relative}`, `.ovl{position:absolute}` | as above, and **verified by measurement** (§5) |
| **OD-47** | How the SaaS fills `Diag_Log` | still recorded, not signed. The D1 audit proposes closing it as **OD-55** |
| **OD-55…OD-61** | The D1a forensic-persist decisions — the `Diag_Log` fill, Azzmax (21) as the dev actor, one writer thread with a bounded queue, redaction, the volume rule, the in-app purge at 60 days, dev-only trail routes | **🤙 signed 2026-09-19** on `Azztec_SaaS_D1a_Persist_Chunk_Spec_v1_0_0.md` §6. OD-47 closed by OD-55 |

**Stated by Adriaan, to be confirmed at the D1a gate:**
1. **The dev actor becomes Azzmax** — Andrew's own login, full administrator rights. His changes are meant to carry his name: "he should be able to go in and make changes, hence why the audit trail is important, so it shows what was fixed, for now and future diagnostics." One consequence recorded in the audit: one login per person, so on Redstag's server everyone signs in as themselves or the trail cannot separate Andrew's fixes from ours. That makes sign-in a condition of the install.
2. **`Diag_Log` retention is 60 days**, from `System_Configuration` key `DIAG_RETENTION_DAYS`, defaulting to 60 when absent.
3. **The trail-read rule** (§7) — Ways of Working gains it in the next doc set.

## 2. Shipped and committed

| Commit | What |
|---|---|
| **`d17bac6`**, tag **`s1k-shell-1.0.0`** | S1k shell — 17 files, 4,501 insertions, 17 deletions: `features/shell/` (rules, icons, HeaderToolbar, SideMenu, AppShell, their four test files, `shell.css`), `routes/__root.tsx` 1.0.0 (first version we own), `planner.css` 1.1.2, `lib/dates.ts` + test 1.2.0, the spec `S1k_Shell_Chunk_Spec_v1_0_1.md`, and the two oracle views byte-for-byte in `docs/reference/` |
| **`c7de038`**, tag **`d1a-persist-1.0.0`** | D1a — 14 files, 1,562 insertions, 93 deletions: `diag.py` 1.2.0, `deps.py` 1.1.0, `config.py` 1.2.0, `main.py` (card 1.0.6, app version unchanged at 0.4.0 — the OpenAPI document did not move), `app/diag/{sql,repo,router}.py` 1.0.0/1.0.0/1.0.1 plus `__init__.py`, `test_diag_persist.py` 1.0.0 (14), `test_diag_trail.py` 1.0.1 (10), `test_kt_uplift.py` 1.0.2, `.env.example` 1.1.0, `scripts/Show-DiagTrail.ps1` 1.0.1, the D1a spec |
| **`95f0359`** | docs — `WOMaint_Audit_Brief_v1_0_0.md`, `D1_Forensic_Trail_Audit_v1_0_1.md`, `workmate_workorder_code_v1_8_1.py` and `WO_Named_Queries_2026-09-16.md` (52 queries, byte-for-byte) in `docs/reference/` |

Tree clean after both. Previous HEAD `8a71eaf`.

**Cards superseded the same day, before anything was dropped:** the S1k spec 1.0.0 → 1.0.1 (§6), the D1 audit 1.0.0 → 1.0.1 (§6), and after the first lint/test pass `rules.test` 1.0.0 → 1.0.1 and `SideMenu.test` 1.0.0 → 1.0.1 (§6).

## 3. Suite state

| | Before | After |
|---|---|---|
| Frontend | 170 passed in 11 files | **205 passed in 15 files** — shell `rules.test` 12, `HeaderToolbar` 8, `SideMenu` 6, `AppShell` 6, and `dates.test` 16 → 19 |
| Backend | 194 passed, 2 skipped | **218 passed, 2 skipped** after D1a (+14 persist, +10 trail; the four DB-gated trail cases run on this box inside a rolled-back transaction). Predicted 218, read 218 |
| Lint | clean | clean (after the two 1.0.1 re-cuts) |
| Build | 503 modules, `index-*.js` 391,750 B, css 21.39 kB | 509 modules, `index-*.js` **424,253 B** (+32.5 kB for the shell, the 22 glyphs and the 16,706-character logo URI), css **25.70 kB**; `planner-*.js` 236 B and `routes-*.js` 358 B **unchanged** — the planner chunk is still split (spec §4 trap 6) |

The prediction in the spec was 205 in 15 and 194 / 2. Both landed exactly; the only miss was one assertion inside them (§6).

## 4. Evidence read this session

- **The two navigation views**, in full: `HeaderToolbar` v16.47 (72,315 B) and `SideMenu` v4.20 (38,363 B), now in `docs/reference/`. Both are the source of every value in `rules.ts` and `shell.css`.
- **`Workmate_Material_Icons_Library_v1_0_0.svg`** — 191 icons, geometry from Google's Material baseline through react-icons, **not** the gateway's own `material.svg`. All 22 the two views name are present and paths-only; copied into `icons.tsx` by script and proven equal path-for-path. Four library icons are **not** paths-only — `category`, `content_cut`, `group_add`, `people_alt` — and WOMaint uses `group_add`, so W1's `Glyph` needs more than `<path>` (§9, item 48).
- **The full project export** (13:07, 32.8 MB): page config — every Workmate page docks the header top (50) and the rail left (50) with `cornerPriority: top-bottom`, so the header owns the corner; `Text/SubHeader` = Verdana / 12 px / bold; stylesheet v2.69 carries **no** rule for `psc-toolbar-btn`, `psc-menubar-item`, `wm-brand-azztec-gold` or `wm-brand-a-glow` and **no `:hover`** for any of them; session props seed `wmBrandMode: AZZTEC` and `showTips: true`.
- **The live KT screenshots** — Plannex (09-16) and WOMaint (09-19). The clock reads `Sep 19` / `07:06:37`, which is `MMM d` and `HH:mm:ss` as ported. On the WOMaint page **no rail item is lit and no menu is underlined**, and on the Plannex page **Home** was lit: `session.custom.activePage` is only set by clicking a nav control, so the oracle's own lighting is stale unless you arrived by button. Our port derives it from the router path — a deliberate difference, recorded in the spec.
- **The WOMaint screenshot** adds what the view JSON could not: the action bar (Link WO · Clone · Delete · Email WOs · New PO · print · edit · help), status and progress as two picture-button rows, the list panel's WO/CP/PM/All chips and coloured id badges, the six audit stamps on Details, and the Resources money line. It belongs in `docs/reference/` when W1 is cut.
- **`workmate.nightshift` 1.3.2 and the `NightShift` schedule** (`cron 0 5 * * *`): the packs run, then the planner's nightly proposal, then an Outlook-safe HTML **morning report** e-mailed to one address — verdict, per-pack table, every FAIL with detail, `Diag_Log` `[E]` rows of the last 24 h, planner health and a needs-attention list. `Diag_NightShift` is already on RST from `0001`. This is the oracle for the morning e-mail Adriaan asked for.

## 4b. D1a — the smoke, measured

- **Rows reach `dbo.Diag_Log` with the person on them.** `Show-DiagTrail.ps1 -UserId 21` returned every planner row as `21 | Azzmax logon`; the startup lines carry `-` (NULL), never 0. The middleware outcome line carries the actor too (`deps.py` 1.1.0 on `request.state`) — the S1k gap closed, seen on `GET /api/v1/planner/range 200 117ms actor 21`.
- **The self-test reads its marker back:** `persisted: true`, `diagId 53` then `82`, `actor 21`. It takes ~1.3 s because `flush()` waits out the batch window — expected.
- **The counters are honest:** `written` matched the row-by-row count every time; a row logged in the same second as the health call showed as not yet written, which is the one-second batch, not a loss. `failed: 0`, `dropped: 0` throughout.
- **OD-59 on its first slow request:** a 5,022 ms cold `range` at 11:22 persisted its outcome line; every fast one did not. Eleven distinct windows in forty seconds persisted eleven rows — distinct facts, no de-dupe, correct.
- **OD-60 unprompted:** `[S] diag purge 0 of 0 rows older than 60 days` at 11:36:16, five minutes after that boot. The route's dry run: `cutoffDays 60, rows 0, deleted 0`; with `days=1`, still `rows 0` — every row in the table is from today.
- **`Diag_Log` row count:** 0 before the drop; the first four rows were written at ~07:5x by the S1k dev server, which `watchfiles` reloaded onto the D1a code mid-drop. Rows from the orphaned process (§6) and the earlier 422s stay: real diagnostics from real processes, and this log says which.
- **Rows written in one batch share `Logged_At`** — `CURRENT_TIMESTAMP` is the statement's clock, so six rows carried `11:32:15.153`. `Diag_Id` is emission order; the script sorts by both from 1.0.1. The database clock stays, as signed (OD-55).

## 5. Facts verified this session

- **The shell matches the oracle at rest, measured not eyeballed.** On `/planner` the Plannex underline is a 2 px green bar (rows 33–34, ~80 px wide) and on `/` there is none; the header gradient reads `#242E30` at the left and within two units of `#004063` at the right; the rail is `#242E30` and nothing is lit on either page, exactly as KT behaves.
- **OD-54 holds.** With the day dialog open: header right `(0, 63, 97)` and rail `(36, 46, 48)` are untouched while the planner behind the dialog reads `(19, 22, 24)` — the bare `(36, 40, 44)` under the 55 % dim. The dim stops at the planner's edge.
- **Plannex navigates client-side.** The trail shows `GET /` and then, fifteen seconds later, only `GET /api/v1/planner/range` with no second document request.
- **The planner is healthy on RST data through the shell:** 1,191 WOs, 1,152 labour rows, 363 workers, 509 ms cold and 237 ms warm.
- **`fastapi dev` imports the app twice** — two `[F] diag wired` boot lines, as Landmines §A says.
- **The devtools plugin strips devtools from `__root.tsx` in the production build** (`[@tanstack/devtools-vite] Removed devtools code from: /src/routes/__root.tsx`), so keeping the CLI's panel costs nothing in `dist/`.
- **Environment:** vitest 5.0.0, vite 8.3.0.

## 6. Mistakes caught this session

1. **The first audit missed log 2026-09-15**, which sits in project knowledge above the Index I read. Two consequences, both caught before anything was built: the spec numbered its decisions OD-48…OD-52 when **OD-48 and OD-49 were already signed for weekno**, and it carried the 09-14 baseline (169 / 2, HEAD `6968c54`). Fixed by reissuing the spec as 1.0.1 with OD-50…OD-54 and the 09-15 state. *Read the newest log first, then the Index.*
2. **The glyph assertion demanded an absolute moveto.** `expect(d.startsWith('M'))` failed on `build`, because four of the 22 — `build`, `construction`, `handyman`, `insights` — open with the relative `m`. The data was right and the claim was wrong; `rules.test` 1.0.1 asserts a path command letter.
3. **An unnecessary type assertion.** `Array.from(container.querySelectorAll('…')) as Array<HTMLElement>` — TypeScript infers the element type **from** the assertion, so the assertion changes nothing and the rule was right. `SideMenu.test` 1.0.1 passes the type as a generic instead.
4. **The trail prediction said "actor 1 on every line".** It is 1 on the planner's own `[F] range` line and **0 on the middleware outcome line**, which never sees the resolved actor. That is the gap D1a closes, now on record from a real run.
5. **The drop aborted on two missing files** — the reference views had never been downloaded. The Test-Path-first rule did its job: nothing was copied, and the rerun (with a normalised-name fallback) landed all 21.
6. The audit counted eight header message handlers; there are **seven**.
7. **The suite would have written to RST.** With the real `.env`, `test_smoke`'s lifespan and every TestClient would have persisted the self-test marker and every `[G]` they provoke into `Diag_Log` on each `pytest` run. Caught by `test_kt_uplift`'s Marker Law case going red on four rows the dev server had written. `main.py` 1.0.6: persistence never switches on under `WORKMATE_ENV=test`; `test_kt_uplift` 1.0.2 names `Diag_Log` as written by design.
8. **Killing the uvicorn reloader orphans the server child on Windows.** The child keeps the inherited port-8000 socket and keeps serving with its cached settings; Windows let a second server bind alongside it, so requests split between two processes — which is how a fresh boot with `.env` at 21 answered `actor: 1`. Stop the child (the `Started server process [pid]` line) or close the window, and prove exactly one PID listens before trusting anything.
9. **`POST /_diag/purge` was a 422 as documented** — `days` defaulted to 0 under `ge=1`. Router 1.0.1: optional, absent means the retention setting.
10. **A downloaded `.ps1` carries Mark-of-the-Web** and RemoteSigned refuses it. `Unblock-File` once; the drop block does it for every `.ps1` from here.
11. **The commit ran ahead of the smoke's last step.** Block D1a-9 was run before D1a-8 had read as predicted (the server was down). The suites were green, so the tag stands; the purge proof came ten minutes later on a fresh boot and passed. Recorded, not hidden: the order is smoke *then* commit.
12. **Spec-versus-code:** the spec promised the purge task's first run on an install is a dry run; the task runs live from its first run. On RST it found zero rows. Item 50.

## 7. Patterns confirmed

- **Predict, then read.** 205 in 15 and 194 / 2 were both written down before the run; the one mismatch inside them pointed straight at a wrong assertion rather than a wrong port.
- **Copy by script, never by hand.** The 22 glyph tables were generated from the library and then proven equal path-for-path; the one glyph typed from memory (`logout`, its gateway file never arrived) is flagged in the card's header as the exception.
- **Mechanical checks before anything runs:** filename version against the header against the `VERSION` constant, on every card, inside the drop block.
- **Measure the screenshot.** Sampling pixels settled the underline, the gradient, the rail state and the dialog dim in seconds, where "looks right" would have carried an opinion.
- **The trail rule, first use.** The smoke ended by reading the console trail against a predicted trail. It caught mistake 4 and proved the Plannex click. **Second use, from the table:** `Show-DiagTrail.ps1` after D1a caught the batch-timestamp ordering, the orphaned process, and the 422. Wait two seconds after the last action before reading — the writer batches for one.

## 8. Doc-correction queue — still unapplied, now larger

The five files queued on 09-15 have **not** been cut. They now also carry S1k §9.1 and the two audits:

- **Index → 1.9.0**: §1 state (HEAD `95f0359`, tag `s1k-shell-1.0.0`, 205 / 15 and 194 / 2), §3.4b the ten `features/shell/` files and `__root.tsx`, §3.7 the two views plus the WO reference extracts, §6 next = D1a, the item list at §9.
- **Landmines → 1.9.0**: `fastapi dev` boots the app twice (already there — confirm); four Material glyphs open with a relative `m`; `querySelectorAll` infers its element type from a following assertion, which makes the assertion an error; the devtools plugin strips `__root.tsx` in the build; the middleware outcome line carries no actor; the 60 s planner poll's row cost once persist is on; the console-tee recipe (`PYTHONUNBUFFERED=1` and a `Tee-Object` pipe) ; `sp_helptext` for routine bodies because `-y 0` cannot be combined with `-h -1`.
- **Ways of Working → 1.3.6**: the trail-read rule (with the two-second wait); the drop block's normalised-name fallback and `Unblock-File` for `.ps1`; stop the server child, not the reloader, and prove one listener before a boot; smoke then commit, never the reverse.
- **Port Spec → 1.0.7**: the S1k row, the planner inside the shell's main cell, OD-50…OD-54, and OD-5 still open until W1.
- **Architecture → 1.0.8**: `features/shell/` in the tree, `__root.tsx` owned, `planner.css` 1.1.2; `app/diag/` in the tree; D-8 is now persist ON — the writer, the fill (OD-55), the volume rule (OD-59), the in-app purge (OD-60), dev-only reads (OD-61); D-5: the dev actor is 21 (OD-56).
- **Landmines** also gains from D1a: `sys.columns.max_length` is bytes; three NOT NULL columns a writer must bind; read `request.state.actor` after `call_next`; the suite must never persist (env=test); the orphaned reloader child; rows in one batch share `Logged_At`; Mark-of-the-Web on downloaded scripts.
- **Index**: §1 state (HEAD `c7de038`, tag `d1a-persist-1.0.0`, 218 / 2, 205 / 15), §3 the D1a files, §6 next = W1, D1b after, OD series at 61, items at 52.

## 9. Open items (52)

Carried from 09-15: 1–45, of which the live ones are 17 (Docker/PG), 24 (hidden-tab poll), 26 (`parity_range.py`), 28 (browser diag route — **now owned by D1b**), 30 (SQL memory), 33 (tips + the first non-port component), 34 (KT carry-backs), 35 (trailing role tokens), 44–45.

**Added to item 34's KT carry-back list:** `meta.classes` and flex `justifyContent` are set on both navigation views but map to nothing in Perspective; three onClick scripts are empty at KT (Invoicex, Labour, PM Wizard); SideMenu v4.20's comment credits a `pathKey` watcher that HeaderToolbar v16.47 does not contain; the view's saved `activePage` default is a stale `"partsetup"`.

| # | New this session |
|---|---|
| **46** | Chrome polish: `favicon.ico` 404s on every page and the tab title is still the CLI's `web`. The Azztec logo already lives in `icons.tsx` as a data URI and can serve both |
| **47** | WORKMATE brand mode is **cut** (OD-53) — it needs `Workmate_Logo_48_Rev.png` and, with it, the brand read from `System_Configuration` |
| **48** | Byte-exact glyphs: the gateway's own `material.svg` and `logout_24dp_1F1F1F.svg` would replace the library geometry and the one typed path. Also: four library icons are not paths-only, and WOMaint uses one of them (`group_add`), so W1's `Glyph` must handle more than `<path>` |
| **49** | Fonts deferred by decision ("sort the font sizes later"): the shell ships the planner's stack, and KT's theme font and sizes are not pinned |
| **50** | The daily purge task runs live from its first run; the spec said the first run on an install is dry. One flag in `main.py`'s task — D1b, or the deploy slice, whichever lands first |
| **51** | `/_diag/self-test`'s own outcome line carries actor 0 because the route reads `dev_user_id` directly instead of `get_current_actor`; every route that means a person should take the dependency (D1b) |
| **52** | A validation failure (422) is FastAPI's default body, not the flat OD-15 shape with `rid` — `RequestValidationError` needs the same handler as `HTTPException` (with W3, the first slice that posts bodies) |

## 10. Next

1. ~~D1a~~ — done, tagged `d1a-persist-1.0.0`.
2. **W1** — WOMaint read: the API and a read-only record, which closes OD-5 and lights `MenuItem_WOMaint`.
3. **Auth** — a condition of the Redstag install, not an option (§1).
4. **W2 / W3**, then **S2b / S2c**, then **D1b**, then deploy.
5. **The morning report** — the Night Shift port, after D1a. Blocked on one answer: which mail the box may send through.
6. The doc set (§8) at the close of this session.

## 11. Changelog

- 1.1.0 (2026-09-19) D1a added: OD-55…OD-61 signed; commit `c7de038` and its tag; 218 / 2; §4b the measured smoke; mistakes 7–12; items 50–52; the doc queue's D1a lines.
- 1.0.0 (2026-09-19) The S1k session: shell built, smoked, committed and tagged; the WOMaint and D1 audits written; four uploads read; items 46–49 raised; the 09-15 doc queue still open and now larger.
