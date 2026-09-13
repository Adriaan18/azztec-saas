# Azztec SaaS — Ways of Working

**File:** Azztec_SaaS_Ways_of_Working_v1_3_1.md · **Version:** 1.3.1 · **Date:** 2026-09-13 · **Author:** Adriaan
**Status:** Active
**Lineage:** `Workmate_Working_Method_v1_2.md` + `Workmate_Deliverable_Format_Standard_v1_0_0.md`, adapted for a git repo.

---

## 1. The build cycle (unchanged)

```
audit → spec → 🤙 → build ONE slice → versioned raw file(s) → smoke-test → raw log → 🤙 → next slice
```

- Spec before code for anything structural. The chunk specs (`S1a`…`S1g`) are the template.
- One slice at a time. A slice is done when its smoke passes **on the RST dev DB** and the test half is green.
- 🤙 is the only gate. "Looks good" is not 🤙.
- **The audit may cut the scope it was handed.** A proposal in a raw log's "next slice" section is an input to the audit, not a decision. Say plainly what is being dropped and why, and where it goes instead.
- **An unsigned decision cannot be smuggled inside a build slice.** If a proposed slice depends on something that has never had a 🤙, that dependency is the first line of the next audit — not a step in this build.
- **A decision about data is blocked on reading the table, not on 🤙** (§5). An OD whose correctness depends on what a table holds carries the pasted rows in the spec before it is signed.

## 2. What a deliverable looks like now

The repo is git-versioned, but the chat still hands over **files**, not diffs:

| Rule | Detail |
|------|--------|
| One file per Download card | delivered via `present_files`; never inline; never zipped |
| Versioned filename | `Azztec_SaaS_<thing>_vX_Y_Z.<ext>` for docs/scripts; backend code delivered as `Azztec_SaaS_app_<path>_vX_Y_Z.py`, frontend code as `Azztec_SaaS_web_<path>_vX_Y_Z.ts` / `.tsx` / `.js` (`Azztec_SaaS_web_lib_dates_v1_0_0.ts` → `web/src/lib/dates.ts`), each dropped into the canonical repo path |
| Version inside the file | Python: `__version__ = "X.Y.Z"` + header comment; TS/TSX/JS: `export const VERSION = "X.Y.Z"` + header (config files too — an extra named export is harmless to ESLint, Vitest and hey-api). **Exception: `src/routes/*.tsx` carry the version in the header comment only** — any export other than `Route` defeats code-splitting (Landmines §C); SQL/MD/PS1: header block, **PS1 ASCII-only** (Landmines §A) |
| Never overwrite | a change is a new version; the previous file stays in the chat history; git keeps the repo history |
| Header block | file, version, target path, author, spec reference, changelog newest-first |
| Bump rules | patch = fix, no contract change · minor = new function/route/field · major = contract break (route shape, JSON key rename, DB DDL) |
| The `__version__` constant is bumped with the header | or `/api/v1/health` lies — and it must **read** those constants, never restate them as literals |
| **Every delivered file is marked PK or not** | the card says whether it goes into project knowledge, and which version it supersedes |

**Git mapping.** After the smoke passes: `git add -A && git commit -m "planner rules 1.1.0 — S2 moveRules"` and tag slice completions `git tag s2-move-1.1.0`. **Tag the version that shipped, not the version the spec predicted** — a mid-slice patch bump changes the tag (S1g's spec said `planner.css` 1.1.0; 1.1.1 shipped; the tag is `s1g-readonly-1.1.1`). One commit per delivered file set. Never rewrite pushed history.

**Dropping files is a step that can fail.** `Unblock-File` in `Downloads` is not a copy. Every drop block lists the exact filenames it expects, and after the drop `Test-Path` each target **by that exact name** — a wrong name has the right `Length` (`range.fictures.ts` was the one hand-typed name out of 22 and only the failing import caught it). Then check `Length` and `LastWriteTime` on the **target**, and grep `^__version__` before running anything. A smoke that reproduces the previous failure byte-for-byte is evidence the drop failed, not that the fix failed. **The verification line is the evidence, not the copy's silence:** a drop block re-run after its sources had been moved out of Downloads copied nothing and said nothing; only `Test-Path`/`Length` on the targets showed the files were already on disk. **And Downloads is not a staging area:** a card is on disk only once it has been saved — the S1g spec was presented at the audit and saved hours later, so the docs copy in the commit block silently missed it and `git add -A` committed the slice without its spec (fixed in `0cb41b8`). Save every card before the block that copies it runs.

## 3. File types

| Kind | Format | Notes |
|------|--------|-------|
| Backend code | `.py` — 4-space indent, Ruff-formatted, type-hinted | f-strings only (UP031) and `Annotated[T, Depends(...)]` only (B008), from the first draft |
| SQL | lives **inside** `backend/app/<module>/sql.py` as `text()` constants | carries the NQ-style header: name, dialect line, PG-CONVERT tags. The CI gate greps the **whole file** — describe banned tokens, never spell them. A standalone `.sql` only for DDL run in SSMS or `sqlcmd` |
| Migrations | `backend/alembic/versions/*.py` | only for tables Workmate adds (WO_N_Plan, Diag_Log, …) — never autogenerate against the legacy 227 tables |
| Frontend code | `.ts` / `.tsx`, strict TypeScript, Prettier, `@tanstack/eslint-config` | generated API client (`src/api/client/**`) is never hand-edited **and never linted** — `eslint.config.js` ignores it, and the generator post-processes with Prettier only |
| Tests | `backend/tests/test_<module>_<slice>.py` (pytest), `web/src/**/*.test.tsx` (Vitest), `web/e2e/*.spec.ts` (Playwright) | pair rule: a library slice ships with its test file |
| Docs | `.md` in `docs/` and in project knowledge | raw logs append-only |
| Scripts | `.ps1` (Windows dev), `.sh` (appliance/Linux) | idempotent, print what they did |

## 4. The pair rule, with teeth

- `rules.py` (pure) → `test_planner_rules.py` runs with **no database** (plain dicts).
- `repo.py` / `service.py` (DB) → tests run inside a transaction that is **rolled back** (`conn.begin()` … `rollback()`), so the RST data is never mutated by a test. Marker Law still applies to anything that commits.
- Every write function keeps the Ignition signature idea: `dry_run: bool = True` default, `expect_start_iso` optimistic lock, returns a dict/model, never raises past the service boundary.
- **A test written zero-DB must actually be zero-DB.** Check the dependency graph, not just the assertion: a route that resolves `Depends(db.get_conn)` opens a connection before the handler runs. Zero-network means the stubbed `fetch` is asserted never called.

## 5. Fact-check before build

- A CLI flag is verified on the box before a script relies on it — `pnpm dlx @tanstack/cli@latest create --list-add-ons … --json` and `--addon-details <id>` pasted, not a README remembered. S0 lost `web/` to a flag that had stopped existing; S1e checked first and lost nothing.
- A scaffold or script that deletes must fail before it deletes, never after. Guard on the target existing, run the risky command, check `$LASTEXITCODE`, and only then touch anything else.
- Column names, status codes, flag domains, FK targets: verify against `All_Tables_InDetail.csv` and the RST DB itself (`SELECT TOP 5 …` via `sqlcmd -C` or SSMS, pasted). The RST DB is the same legacy schema but **its data domains may differ from KT** — probe, don't assume (Data Layer doc §5).
- **A decision about data is blocked on reading the table, not on 🤙.** OD-32 (priority badge colour by rank) was proposed from a chip screenshot, signed, built, shipped and withdrawn the same day: five minutes of `SELECT` on `dbo.Priority` — fourteen rows, four tied at `Sort_Sequence` 1, so the tie-break ranks P2 ahead of P1 — would have killed it at the audit. Any OD whose correctness depends on a table's contents carries the pasted rows in the spec before it is signed. One build cycle, once.
- **Say "the API doesn't send it", never "it isn't there".** Absence from an API shape is not absence from the database: `/range` sends `{id, short, title}` for priorities while RST's `Priority.Colour` is populated and varied. The honest sentence names the layer that omits the thing.
- Anything the Ignition planner computes is the parity oracle: same window, same DB → same `counts`.
- **Never re-emit a file you have not read.** Reconstructing a shipped module from its spec silently reverts whatever the spec did not describe. Ask for the current source; the cost of asking is one paste. This includes files a CLI wrote: read `eslint.config.js` before replacing it, and read the generated client's `^export` lines before writing anything that imports them. **It includes the oracle's strings:** `rules.test.ts` 1.0.0 asserted `Monday 14 Sep 2026` from memory in four places where the oracle's `fmtLong` builds `Mon` from the abbreviated DOW. Strings are parity surface — read the oracle line, then pin it. **And it includes column names:** `Short`/`Title` cost a round trip on 2026-09-13 when `Short_Priority_Id`/`Priority_Title` were in `sql.py` 201–204 — a file already in project knowledge and already read that session. A column list from memory is a file from memory, priced at one round trip instead of one build.
- **Check the box before the code.** Before diagnosing any latency, paste free memory and the top-5 processes by working set (`Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 5 Name,@{n='GB';e={[math]::Round($_.WorkingSet64/1GB,2)}}`) — verbatim, before the first hypothesis. Four hours went into DMVs and request timing while Docker Desktop held 45 GB of a 32 GB box (Landmines §F). A smoke on a starved box measures the box, not the slice. When the box *is* clean and it is still slow, that is a backend finding with its own evidence trail — wait types during a slow request (item 30) — not a reason to doubt the box check.

## 6. Smoke-testing

Every slice has a written smoke line in the spec. Minimum, **in this order**:

```
uv run ruff format .                          # load-bearing: cards are not format-clean on arrival
uv run ruff check .
uv run pytest                                 # backend green — plain, NO -q (pyproject already sets addopts="-q")
uv run fastapi dev app/main.py                # boots, /api/v1/health returns version + db ok
curl "http://localhost:8000/api/v1/planner/range?from=2026-09-14&to=2026-09-20"
pnpm --dir web test && pnpm --dir web build   # frontend green + builds
```

Frontend order when the slice touches `web/`: `pnpm gen:api` → `pnpm lint` → `pnpm test` → `pnpm build`, then `gci web\dist\index.html`. `pnpm lint` is **ESLint only** — `prettier --check` (the CLI's `check` script) is not in the smoke yet; add it to this order or say why not (open item 25). **Any slice that creates or changes `web/dist` re-runs the backend suite and the dev-server request set with `dist/` present** — the mount flips behaviour without a backend file changing (Landmines §A).

**Three windows.** Backend, Vite and the command shell are three PowerShell windows. Any block that starts a server does it with `Start-Process powershell -ArgumentList '-NoExit','-Command','cd C:\dev\workmate-saas\backend; uv run fastapi dev app/main.py'` (same shape for `pnpm --dir web dev`) so it cannot land in the window the other server lives in — S1f lost twenty minutes and three false "it's broken" readings to servers trading places. Vite is on **`:3000`**, the backend on `:8000`; a port check tries both `::1` and `127.0.0.1` (Landmines §C). Close stale browser tabs before judging a fix by the Vite console — a `[Client]`-prefixed warning is a tab talking, not the server. **One browser tab during a smoke** — two planner tabs both poll `/range` every 60 s, which doubles the load and makes the timing lines in the dev-server log useless (log 2026-09-13 §4.5).

**Before the smoke, the box.** If the machine shares RAM with Docker Desktop, free memory first (§5, Landmines §F). A `/range` over 2 s is the box until proven otherwise — and a clean box that is still slow is open item 30, not a reason to skip the check.

Console output is pasted verbatim into the chat before the next step. **The dev-server terminal is part of the smoke, not decoration** — the `[F]`/`[G]` lines are where a slice proves it did what it claimed, and the `[F] range …` lines that complete after the user has clicked away are OD-30 working, not a leak.

Count tests from the run, never from the previous raw log; the number drifts as files gain cases. **Run plain `uv run pytest`** — `pyproject.toml` already sets `addopts = "-q"`, and a second `-q` on the command line deletes the `N passed` summary line (three sessions blamed the pipe — `-Last 3`, `-Last 6`, `Tee-Object`; Landmines §A). To keep one line, pipe to `Select-String "passed|failed"`. The exit code gates the commit either way, but a commit whose log cannot show the count is a commit with a hole in it.

## 7. Diagnostics discipline

`Workmate_Forensic_Diagnostics_Standard_v1_1_0.md` carries over. Implementation: `app/core/diag.py` — one `log(level, message, detail, actor)` that writes structured JSON to stdout **and** persists to `dbo.Diag_Log` (async, never blocks, never raises), wired by `diag.configure()` from the app factory. Every route outcome is one [F]/[G]/[E] line with the request id. `/api/v1/_diag/self-test` replaces `/planner/_echo`.

**The instrument law.** A diagnostics test that asserts the **return value** of `diag.log()` is not a diagnostics test — it proves the function was called, not that anything was emitted. The same goes for a health field that reports where records *would* persist. Both of those passed for three slices while every `[F]` and `[G]` line was being discarded at the logger's level check.

- Assert **emission**, at the stream, with `capfd`. Not `caplog` (its handler is on root and it proves the call, not the write). Not `capsys` (it swaps `sys.stdout` at the Python level).
- A wiring check tests the specific handler by name — never `hasHandlers()`, which any test harness satisfies.
- Report wiring and persistence as two separate facts (`diagWired` and `diag`).
- Generalise: when a test and the real path disagree, assume the real path is right and the test is the thing that is wrong.

## 8. Comms

- Short, direct, NZ-casual. Surgical steps. No preamble.
- Shell blocks are complete and copy-pasteable, never hand-typed: each starts with `cd C:\dev\workmate-saas…` (a fresh window opens in `system32`, Landmines §A), names the exact files it expects to find, and is ASCII-only when it is a `.ps1`.
- Paste console output; screenshots for UI review; defects fixed immediately.
- Decisions get an ID (D-n in architecture, OD-n open decisions in specs) and a date. A decision that is withdrawn keeps its ID, struck through, with the reason — OD-32 is the precedent; the number is never reused.
- Close a session with `Azztec_SaaS_Raw_Log_YYYY-MM-DD_vX_Y_Z.md`: decisions, mistakes caught, patterns confirmed, facts verified — dated one-liners. **A superseding log must carry forward every open item it does not close.** An item that silently drops out of the open list is worse than an item left open: 1.0.0 §8.1 named the web-toolchain decision "the oldest open item" and 1.1.0 lost it entirely.

## 9. Knowledge maintenance

Two layers as before: **raw** (dated logs, schema CSVs, the Ignition sources, `.NET` manuals — never rewritten) and **compiled** (this set — versioned, edited, kept sharp). Four writing rules: one lesson per section; update, don't duplicate; delete what's wrong (note it in the changelog); never touch raw. Platform claims carry a verified date; anything older than a major version bump of that platform is re-verified before being relied on.

**Project knowledge is a third obligation, not an afterthought.** The chat surface cannot read the repo — only project knowledge. Every delivered file therefore goes into project knowledge at its current version, and the superseded version comes out. When it doesn't, the next audit reconstructs from a spec instead of reading the code, and reconstruction reverts whatever the spec didn't describe.

- Each card states **PK: add / replaces `<old version>`**.
- At session close, the raw log ships **with** the doc updates it implies — Landmines, this file, the Index. The next session's first task is that doc set, applied before any audit, each file read in full before it is re-emitted; the audit then reads the docs, not the log.
- The Index §3 file table is the inventory: if a file is live in the repo and absent from that table, it is missing from project knowledge. The reverse holds too: a superseded version still sitting in project knowledge is the one the next audit reads by mistake — the Index §6.2 names what to remove, and the first task of a session is to check that list against the project files, not against the log.

## 10. Changelog

- 1.3.1 (2026-09-13) From the S1g session (log 2026-09-13 1.0.0 §7). §1 template list gains S1g and the table-before-🤙 rule. §2: tag-what-shipped gains the S1g example; the drop rule gains "the verification line is the evidence, not the copy's silence" and "Downloads is not a staging area — save the card before the block runs". §3 SQL row admits `sqlcmd`. §4 zero-network wording. §5 gains "a decision about data is blocked on reading the table" (OD-32), "say *the API doesn't send it*, never *it isn't there*", column names under read-before-re-emit, and the clean-box clause on memory-first. §6: the smoke block and the count paragraph replace `pytest -q` and the `-Last 6` trimming rule with plain `uv run pytest` + `Select-String`; one browser tab during a smoke; the OD-30 late `[F] range` lines named as expected. §8: withdrawn decisions keep their ID. §9: the doc set is the next session's first task.
- 1.3.0 (2026-09-13) From the S1f session (log 2026-09-12 1.1.0). §1 template list gains S1f. §2: route files carry the version in the header only (code-splitting), and the drop rule gains the exact-filename list + `Test-Path` check. §5 gains memory-first ("check the box before the code") and extends read-before-re-emit to the oracle's strings (the `Mon`/`Monday` catch). §6 gains the three-windows rule with `Start-Process`, port 3000 and the two-stack port check, stale tabs, the box-before-smoke rule, the `-Last 6` count-line rule, and notes `prettier --check` is not in the smoke. §8 gains the shell-block rule. §9 gains the superseded-out check.
- 1.2.0 (2026-09-12) §1 template list gains S1e. §2 names the frontend delivered-filename form and the PS1 ASCII rule. §3 frontend row: generated client is never linted. §5 gains the verify-the-flag and fail-before-delete rules, and extends read-before-re-emit to CLI-written and generated files. §6 gains the frontend smoke order and the `dist/`-present backend re-run. From the S1e session.
- 1.1.0 (2026-09-11) §1 gains the scope-cut and unsigned-dependency rules. §2 gains the PK marker, tag-what-shipped, and the drop-verification rule. §5 gains "never re-emit a file you have not read". §6 fixes the smoke ordering and the test-count rule. §7 rewritten around the instrument law. §8 gains the carry-forward rule for open items. §9 gains the project-knowledge obligation. All from the S1c/S1d sessions.
- 1.0.0 (2026-09-10) Initial.
