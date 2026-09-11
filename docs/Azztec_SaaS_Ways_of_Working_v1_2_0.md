# Azztec SaaS — Ways of Working

**File:** Azztec_SaaS_Ways_of_Working_v1_2_0.md · **Version:** 1.2.0 · **Date:** 2026-09-12 · **Author:** Adriaan
**Status:** Active
**Lineage:** `Workmate_Working_Method_v1_2.md` + `Workmate_Deliverable_Format_Standard_v1_0_0.md`, adapted for a git repo.

---

## 1. The build cycle (unchanged)

```
audit → spec → 🤙 → build ONE slice → versioned raw file(s) → smoke-test → raw log → 🤙 → next slice
```

- Spec before code for anything structural. The chunk specs (`S1a`…`S1e`) are the template.
- One slice at a time. A slice is done when its smoke passes **on the RST dev DB** and the test half is green.
- 🤙 is the only gate. "Looks good" is not 🤙.
- **The audit may cut the scope it was handed.** A proposal in a raw log's "next slice" section is an input to the audit, not a decision. Say plainly what is being dropped and why, and where it goes instead.
- **An unsigned decision cannot be smuggled inside a build slice.** If a proposed slice depends on something that has never had a 🤙, that dependency is the first line of the next audit — not a step in this build.

## 2. What a deliverable looks like now

The repo is git-versioned, but the chat still hands over **files**, not diffs:

| Rule | Detail |
|------|--------|
| One file per Download card | delivered via `present_files`; never inline; never zipped |
| Versioned filename | `Azztec_SaaS_<thing>_vX_Y_Z.<ext>` for docs/scripts; backend code delivered as `Azztec_SaaS_app_<path>_vX_Y_Z.py`, frontend code as `Azztec_SaaS_web_<path>_vX_Y_Z.ts` / `.tsx` / `.js` (`Azztec_SaaS_web_lib_dates_v1_0_0.ts` → `web/src/lib/dates.ts`), each dropped into the canonical repo path |
| Version inside the file | Python: `__version__ = "X.Y.Z"` + header comment; TS/TSX/JS: `export const VERSION = "X.Y.Z"` + header (config files too — an extra named export is harmless to ESLint, Vitest and hey-api); SQL/MD/PS1: header block, **PS1 ASCII-only** (Landmines §A) |
| Never overwrite | a change is a new version; the previous file stays in the chat history; git keeps the repo history |
| Header block | file, version, target path, author, spec reference, changelog newest-first |
| Bump rules | patch = fix, no contract change · minor = new function/route/field · major = contract break (route shape, JSON key rename, DB DDL) |
| The `__version__` constant is bumped with the header | or `/api/v1/health` lies — and it must **read** those constants, never restate them as literals |
| **Every delivered file is marked PK or not** | the card says whether it goes into project knowledge, and which version it supersedes |

**Git mapping.** After the smoke passes: `git add -A && git commit -m "planner rules 1.1.0 — S2 moveRules"` and tag slice completions `git tag s2-move-1.1.0`. **Tag the version that shipped, not the version the spec predicted** — a mid-slice patch bump changes the tag. One commit per delivered file set. Never rewrite pushed history.

**Dropping files is a step that can fail.** `Unblock-File` in `Downloads` is not a copy. After every drop, check `Length` and `LastWriteTime` on the **target**, and grep `^__version__` before running anything. A smoke that reproduces the previous failure byte-for-byte is evidence the drop failed, not that the fix failed.

## 3. File types

| Kind | Format | Notes |
|------|--------|-------|
| Backend code | `.py` — 4-space indent, Ruff-formatted, type-hinted | f-strings only (UP031) and `Annotated[T, Depends(...)]` only (B008), from the first draft |
| SQL | lives **inside** `backend/app/<module>/sql.py` as `text()` constants | carries the NQ-style header: name, dialect line, PG-CONVERT tags. The CI gate greps the **whole file** — describe banned tokens, never spell them. A standalone `.sql` only for DDL run in SSMS |
| Migrations | `backend/alembic/versions/*.py` | only for tables Workmate adds (WO_N_Plan, Diag_Log, …) — never autogenerate against the legacy 227 tables |
| Frontend code | `.ts` / `.tsx`, strict TypeScript, Prettier, `@tanstack/eslint-config` | generated API client (`src/api/client/**`) is never hand-edited **and never linted** — `eslint.config.js` ignores it, and the generator post-processes with Prettier only |
| Tests | `backend/tests/test_<module>_<slice>.py` (pytest), `web/src/**/*.test.tsx` (Vitest), `web/e2e/*.spec.ts` (Playwright) | pair rule: a library slice ships with its test file |
| Docs | `.md` in `docs/` and in project knowledge | raw logs append-only |
| Scripts | `.ps1` (Windows dev), `.sh` (appliance/Linux) | idempotent, print what they did |

## 4. The pair rule, with teeth

- `rules.py` (pure) → `test_planner_rules.py` runs with **no database** (plain dicts).
- `repo.py` / `service.py` (DB) → tests run inside a transaction that is **rolled back** (`conn.begin()` … `rollback()`), so the RST data is never mutated by a test. Marker Law still applies to anything that commits.
- Every write function keeps the Ignition signature idea: `dry_run: bool = True` default, `expect_start_iso` optimistic lock, returns a dict/model, never raises past the service boundary.
- **A test written zero-DB must actually be zero-DB.** Check the dependency graph, not just the assertion: a route that resolves `Depends(db.get_conn)` opens a connection before the handler runs.

## 5. Fact-check before build

- A CLI flag is verified on the box before a script relies on it — `pnpm dlx @tanstack/cli@latest create --list-add-ons … --json` and `--addon-details <id>` pasted, not a README remembered. S0 lost `web/` to a flag that had stopped existing; S1e checked first and lost nothing.
- A scaffold or script that deletes must fail before it deletes, never after. Guard on the target existing, run the risky command, check `$LASTEXITCODE`, and only then touch anything else.
- Column names, status codes, flag domains, FK targets: verify against `All_Tables_InDetail.csv` and the RST DB itself (`SELECT TOP 5 …` in SSMS, pasted). The RST DB is the same legacy schema but **its data domains may differ from KT** — probe, don't assume (Data Layer doc §5).
- Anything the Ignition planner computes is the parity oracle: same window, same DB → same `counts`.
- **Never re-emit a file you have not read.** Reconstructing a shipped module from its spec silently reverts whatever the spec did not describe. Ask for the current source; the cost of asking is one paste. This includes files a CLI wrote: read `eslint.config.js` before replacing it, and read the generated client's `^export` lines before writing anything that imports them.

## 6. Smoke-testing

Every slice has a written smoke line in the spec. Minimum, **in this order**:

```
uv run ruff format .                          # load-bearing: cards are not format-clean on arrival
uv run ruff check .
uv run pytest -q                              # backend green
uv run fastapi dev app/main.py                # boots, /api/v1/health returns version + db ok
curl "http://localhost:8000/api/v1/planner/range?from=2026-09-14&to=2026-09-20"
pnpm --dir web test && pnpm --dir web build   # frontend green + builds
```

Frontend order when the slice touches `web/`: `pnpm gen:api` → `pnpm lint` → `pnpm test` → `pnpm build`, then `gci web\dist\index.html`. **Any slice that creates or changes `web/dist` re-runs the backend suite and the dev-server request set with `dist/` present** — the mount flips behaviour without a backend file changing (Landmines §A).

Console output is pasted verbatim into the chat before the next step. **The dev-server terminal is part of the smoke, not decoration** — the `[F]`/`[G]` lines are where a slice proves it did what it claimed.

Count tests from the run, never from the previous raw log; the number drifts as files gain cases.

## 7. Diagnostics discipline

`Workmate_Forensic_Diagnostics_Standard_v1_1_0.md` carries over. Implementation: `app/core/diag.py` — one `log(level, message, detail, actor)` that writes structured JSON to stdout **and** persists to `dbo.Diag_Log` (async, never blocks, never raises), wired by `diag.configure()` from the app factory. Every route outcome is one [F]/[G]/[E] line with the request id. `/api/v1/_diag/self-test` replaces `/planner/_echo`.

**The instrument law.** A diagnostics test that asserts the **return value** of `diag.log()` is not a diagnostics test — it proves the function was called, not that anything was emitted. The same goes for a health field that reports where records *would* persist. Both of those passed for three slices while every `[F]` and `[G]` line was being discarded at the logger's level check.

- Assert **emission**, at the stream, with `capfd`. Not `caplog` (its handler is on root and it proves the call, not the write). Not `capsys` (it swaps `sys.stdout` at the Python level).
- A wiring check tests the specific handler by name — never `hasHandlers()`, which any test harness satisfies.
- Report wiring and persistence as two separate facts (`diagWired` and `diag`).
- Generalise: when a test and the real path disagree, assume the real path is right and the test is the thing that is wrong.

## 8. Comms

- Short, direct, NZ-casual. Surgical steps. No preamble.
- Paste console output; screenshots for UI review; defects fixed immediately.
- Decisions get an ID (D-n in architecture, OD-n open decisions in specs) and a date.
- Close a session with `Azztec_SaaS_Raw_Log_YYYY-MM-DD_vX_Y_Z.md`: decisions, mistakes caught, patterns confirmed, facts verified — dated one-liners. **A superseding log must carry forward every open item it does not close.** An item that silently drops out of the open list is worse than an item left open: 1.0.0 §8.1 named the web-toolchain decision "the oldest open item" and 1.1.0 lost it entirely.

## 9. Knowledge maintenance

Two layers as before: **raw** (dated logs, schema CSVs, the Ignition sources, `.NET` manuals — never rewritten) and **compiled** (this set — versioned, edited, kept sharp). Four writing rules: one lesson per section; update, don't duplicate; delete what's wrong (note it in the changelog); never touch raw. Platform claims carry a verified date; anything older than a major version bump of that platform is re-verified before being relied on.

**Project knowledge is a third obligation, not an afterthought.** The chat surface cannot read the repo — only project knowledge. Every delivered file therefore goes into project knowledge at its current version, and the superseded version comes out. When it doesn't, the next audit reconstructs from a spec instead of reading the code, and reconstruction reverts whatever the spec didn't describe.

- Each card states **PK: add / replaces `<old version>`**.
- At session close, the raw log ships **with** the doc updates it implies — Landmines, this file, the Index.
- The Index §3 file table is the inventory: if a file is live in the repo and absent from that table, it is missing from project knowledge.

## 10. Changelog

- 1.2.0 (2026-09-12) §1 template list gains S1e. §2 names the frontend delivered-filename form and the PS1 ASCII rule. §3 frontend row: generated client is never linted. §5 gains the verify-the-flag and fail-before-delete rules, and extends read-before-re-emit to CLI-written and generated files. §6 gains the frontend smoke order and the `dist/`-present backend re-run. From the S1e session.
- 1.1.0 (2026-09-11) §1 gains the scope-cut and unsigned-dependency rules. §2 gains the PK marker, tag-what-shipped, and the drop-verification rule. §5 gains "never re-emit a file you have not read". §6 fixes the smoke ordering and the test-count rule. §7 rewritten around the instrument law. §8 gains the carry-forward rule for open items. §9 gains the project-knowledge obligation. All from the S1c/S1d sessions.
- 1.0.0 (2026-09-10) Initial.
