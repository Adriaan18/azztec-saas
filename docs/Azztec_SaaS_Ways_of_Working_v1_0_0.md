# Azztec SaaS — Ways of Working

**File:** Azztec_SaaS_Ways_of_Working_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-10 · **Author:** Adriaan
**Status:** Active from first use
**Lineage:** `Workmate_Working_Method_v1_2.md` + `Workmate_Deliverable_Format_Standard_v1_0_0.md`, adapted for a git repo.

---

## 1. The build cycle (unchanged)

```
audit → spec → 🤙 → build ONE slice → versioned raw file(s) → smoke-test → raw log → 🤙 → next slice
```

- Spec before code for anything structural. The Planner port spec is the template.
- One slice at a time. A slice is done when its smoke passes **on the RST dev DB** and the test half is green.
- 🤙 is the only gate. "Looks good" is not 🤙.

## 2. What a deliverable looks like now

The repo is git-versioned, but the chat still hands over **files**, not diffs:

| Rule | Detail |
|------|--------|
| One file per Download card | delivered via `present_files`; never inline; never zipped |
| Versioned filename | `Azztec_SaaS_<thing>_vX_Y_Z.<ext>` for docs/scripts; code files delivered as `<module>_vX_Y_Z.py` and dropped into the canonical repo path (`backend/app/planner/rules.py`) |
| Version inside the file | Python: `__version__ = "X.Y.Z"` + header comment; TS/TSX: `export const VERSION = "X.Y.Z"` + header; SQL/MD/PS1: header block |
| Never overwrite | a change is a new version; the previous file stays in the chat history; git keeps the repo history |
| Header block | file, version, target path, author, spec reference, changelog newest-first |
| Bump rules | patch = fix, no contract change · minor = new function/route/field · major = contract break (route shape, JSON key rename, DB DDL) |
| The `__version__` constant is bumped with the header | or `/api/v1/health` lies |

**Git mapping.** After the smoke passes: `git add -A && git commit -m "planner rules 1.1.0 — S2 moveRules"` and tag slice
completions `git tag s2-move-1.1.0`. One commit per delivered file set. Never rewrite pushed history.

## 3. File types

| Kind | Format | Notes |
|------|--------|-------|
| Backend code | `.py` — 4-space indent, Ruff-formatted, type-hinted | no `# coding` line needed any more (that was an Ignition landmine); keep it out anyway |
| SQL | lives **inside** `backend/app/<module>/sql.py` as `text()` constants | still carries the NQ-style header: name, dialect line, PG-CONVERT tags. A standalone `.sql` only for DDL run in SSMS |
| Migrations | `backend/alembic/versions/*.py` | only for tables Workmate adds (WO_N_Plan, Diag_Log, …) — never autogenerate against the legacy 227 tables |
| Frontend code | `.ts` / `.tsx`, strict TypeScript, Prettier | generated API client is never hand-edited |
| Tests | `backend/tests/test_<module>_<slice>.py` (pytest), `web/src/**/*.test.tsx` (Vitest), `web/e2e/*.spec.ts` (Playwright) | pair rule: a library slice ships with its test file |
| Docs | `.md` in `docs/` and in project knowledge | raw logs append-only |
| Scripts | `.ps1` (Windows dev), `.sh` (appliance/Linux) | idempotent, print what they did |

## 4. The pair rule, with teeth

- `rules.py` (pure) → `test_planner_rules.py` runs with **no database** (plain dicts, like `Test_workmate_planner` did).
- `repo.py` / `service.py` (DB) → tests run inside a transaction that is **rolled back** (`conn.begin()` … `rollback()`), so
  the RST data is never mutated by a test. Marker Law still applies to anything that commits.
- Every write function keeps the Ignition signature idea: `dry_run: bool = True` default, `expect_start_iso` optimistic lock,
  returns a dict/model, never raises past the service boundary.

## 5. Fact-check before build

- Column names, status codes, flag domains, FK targets: verify against `All_Tables_InDetail.csv` and the RST DB itself
  (`SELECT TOP 5 …` in SSMS, pasted). The RST DB is the same legacy schema but **its data domains may differ from KT**
  (Active flags, Internal_Dept, LRStd) — probe, don't assume (Data Layer doc §5).
- Anything the Ignition planner computes is the parity oracle: same window, same DB → same `counts`.

## 6. Smoke-testing

Every slice has a written smoke line in the spec. Minimum:

```
uv run pytest -q                              # backend green
uv run fastapi dev                            # boots, /api/v1/health returns version + db ok
curl "http://localhost:8000/api/v1/planner/range?from=2026-09-14&to=2026-09-20"
pnpm --dir web test && pnpm --dir web build   # frontend green + builds
```

Console output is pasted verbatim into the chat before the next step.

## 7. Diagnostics discipline

`Workmate_Forensic_Diagnostics_Standard_v1_1_0.md` carries over. Implementation: `app/core/diag.py` — one `log(level, message, detail, actor)`
that writes structured JSON to stdout **and** persists to `dbo.Diag_Log` (async, never blocks, never raises). Every route
outcome is one [F]/[G]/[E] line with the request id. `/api/v1/_diag/self-test` replaces `/planner/_echo`.

## 8. Comms

- Short, direct, NZ-casual. Surgical steps. No preamble.
- Paste console output; screenshots for UI review; defects fixed immediately.
- Decisions get an ID (D-n in architecture, OD-n open decisions in specs) and a date.
- Close a session with `Azztec_SaaS_Raw_Log_YYYY-MM-DD_vX_Y_Z.md`: decisions, mistakes caught, patterns confirmed, facts verified — dated one-liners.

## 9. Knowledge maintenance

Two layers as before: **raw** (dated logs, schema CSVs, the Ignition sources, `.NET` manuals — never rewritten) and
**compiled** (this set — versioned, edited, kept sharp). Four writing rules: one lesson per section; update, don't duplicate;
delete what's wrong (note it in the changelog); never touch raw. Platform claims carry a verified date; anything older than a
major version bump of that platform is re-verified before being relied on.

## 10. Changelog

- 1.0.0 (2026-09-10) Initial.
