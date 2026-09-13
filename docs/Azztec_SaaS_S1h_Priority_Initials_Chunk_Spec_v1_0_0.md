# Azztec SaaS — S1h Priority Colour + Initials Chunk Spec

**File:** Azztec_SaaS_S1h_Priority_Initials_Chunk_Spec_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-13 · **Author:** Adriaan
**Status:** Draft — **OD-35, OD-36, OD-37 need 🤙 before anything is built**
**Target path:** `docs/Azztec_SaaS_S1h_Priority_Initials_Chunk_Spec_v1_0_0.md` (+ project knowledge)
**Parent spec:** `Azztec_SaaS_Planner_Port_Spec_v1_0_3.md` §2, §3, §5, §6 (the backend audit), §9
**Source of truth:** `docs/reference/workmate_planner_code_v1_3_1.py` — `initialsOf` 375–384, `_PRIORITY_SQL` 625–629, `fetchPriorities` 699–703
**Closes:** open item **29** (`Priority.Colour` to the badge — backend half) and open item **21** (`initialsOf` on parentheses)
**Signed decisions in force:** OD-10 (`rules.__version__` is the contract's `libVersion`), OD-11 (`Sort_Sequence, Priority_Id` tie-break), OD-14 (envelope), OD-32 **withdrawn** (rank is not priority)

---

## 1. Scope — build exactly seven files, then stop

| Deliverable | Target path | Version | Change |
|---|---|---|---|
| `Azztec_SaaS_app_planner_sql_v1_1_0.py` | `backend/app/planner/sql.py` | 1.0.1 → **1.1.0** | `Colour` in `PRIORITIES` |
| `Azztec_SaaS_app_planner_repo_v1_1_0.py` | `backend/app/planner/repo.py` | 1.0.0 → **1.1.0** | `colour` in the priority dict |
| `Azztec_SaaS_app_planner_schemas_v1_1_0.py` | `backend/app/planner/schemas.py` | 1.0.0 → **1.1.0** | `Priority.colour: str` |
| `Azztec_SaaS_app_planner_rules_v1_1_0.py` | `backend/app/planner/rules.py` | 1.0.0 → **1.1.0** | `initialsOf` + `_nameForInitials` (OD-35) |
| `Azztec_SaaS_app_planner_router_v1_1_0.py` | `backend/app/planner/router.py` | 1.0.1 → **1.1.0** | version line + changelog only (OD-37) |
| `Azztec_SaaS_test_planner_rules_v1_1_0.py` | `backend/tests/test_planner_rules.py` | 1.0.0 → **1.1.0** | pair of `rules.py` |
| `Azztec_SaaS_test_planner_api_v1_1_0.py` | `backend/tests/test_planner_api.py` | 1.0.1 → **1.1.0** | `colour` assertions |

**Nothing writes.** No `UPDATE`, no `INSERT`, no DDL, no migration, no Alembic revision. `DRY_RUN` does not
apply to this slice because there is no write path in it — the only SQL change is one more column in a
`SELECT` list. Item 29's queued `DRY_RUN`-first `UPDATE dbo.Priority SET Colour` is **withdrawn** on the
evidence in §2.1: there is nothing to repair.

**Stop line.** `service.py` is **not** touched — it passes `repo.fetch_priorities(conn)` through at line 112
and needs no knowledge of the new key. The **frontend is not touched at all**: no `openapi-ts` regeneration,
no `WOCard`, no `planner.css`. Painting the badge from `colour` is the *next* slice and is specified in §9.2,
not here. `pnpm test` must still read 155 in 11 files after this slice, untouched.

**Pair rule.** `rules.py` 1.1.0 and `test_planner_rules.py` 1.1.0 ship together or neither ships. Same for the
four API-surface files and `test_planner_api.py` 1.1.0.

## 2. Evidence — read 2026-09-13, both databases, before any 🤙

### 2.1 `dbo.Priority` — the payload is **seven** rows on RST, not fourteen

```
db  Priority_Id  short    title                        seq  colour   Active
RST 1            P2       Priority 2                   1    #FF9F40  1
RST 5            P1       Priority 1                   1    #FF0000  1
RST 9            ST       Stores Items                 1    #808000  0
RST 14           P2S      Small Job <$200 and <2Hrs    1    #FF0000  0
RST 2            P3       Priority 3                   2    #74EE66  1
RST 10           T        Action Today                 2    #808040  0
RST 3            WK-END   Weekend work                 3    #FF0000  0
RST 11           W        Action Weekend               3    #808040  0
RST 12           P5       Priority 5                   3    #C499C1  1
RST 13           P6       Priority 6                   3    #C0C0C0  1
RST 4            P4       Priority 4                   4    #0080FF  1
RST 8            SHUT     Shutdown Work                4    #FF0000  0
RST 6            N/A      Not Applicable               5    #FFFFFF  1
RST 7            REQUEST  Requisition                  6    #FFFF80  0

KT  1            A        Action Today                 1    #FF8000  1
KT  2            B        Action this week             2    #FF8000  1
KT  3            C        Action this month            3    #FF8000  1
KT  4            D        As sched. permits            4    #FF8000  1

db  column  type     max_length  is_nullable
RST Colour  varchar  255         1
KT  Colour  varchar  255         1
```

Four findings, each load-bearing:

1. **`Active` is `1`/`0` on RST and the filter drops half the table.** `PRIORITIES` ends
   `WHERE RTRIM(COALESCE(Active,'')) NOT IN ('0','N')`, so `priorities[]` carries **seven** rows: P2, P1, P3,
   P5, P6, P4, N/A. Confirmed by a second oracle — `sys.dm_exec_query_stats` on that statement reports
   `max_rows` **7** (backend audit, same day). Landmines §E's "fourteen rows" is true of the *table* and wrong
   about the *payload*; §9.1 carries the correction.
2. **Among the seven active rows every colour is distinct** — `#FF9F40 #FF0000 #74EE66 #C499C1 #C0C0C0
   #0080FF #FFFFFF`. All three `#FF0000` duplicates (WK-END, SHUT, P2S) and both `#808040`s are inactive.
   Paint-from-payload is therefore unambiguous on RST, which is the opposite of what the fourteen-row read
   suggested.
3. **Ties survive the filter** — P2 and P1 both at `Sort_Sequence` 1, P5 and P6 both at 3. OD-11's
   `Priority_Id` tie-break still ranks P2 above P1, so rank is still not priority and OD-32 stays withdrawn.
4. **`Colour` is `varchar(255) NULL` on both sites** — free text, no constraint, no guarantee of `#RRGGBB`.
   `RTRIM(COALESCE(...))` gives `''` for NULL; validating the string is the frontend's job (§9.2).

KT is unchanged from log 1.1.0 §5.4: four rows, no ties, `#FF8000` on all four — so on KT the payload colour
carries no information and the letter class is what paints. Both behaviours have to survive in the frontend
slice; neither is the "right" one.

### 2.2 `dbo.Users` — brackets are the rule on RST, not the exception

Every RST name row matching `LIKE '%(%'` was read (roughly 300 rows, both `Active` states). The oracle's
`initialsOf` fails on them in **two** distinct ways, and only one of them is visible:

| shortId | User_Name | oracle gives | why |
|---|---|---|---|
| `JEANP` | `JP Paalvast (TS)` | `J(` | `parts[-1]` is `(TS)`, first char `(` |
| `AARONW` | `Aaron Wilson (Livewires)` | `A(` | same |
| `BIG MOW` | `Big Mow (FORMA)` | `B(` | same |
| `ADAMD` | `Adam Donald (Max Edkins)` | **`AE`** | `parts[-1]` is `Edkins)` — **silently wrong, looks fine** |
| `TERRYHK` | `Terry Herangi-Kingi (Max Edkins)` | **`TE`** | hyphen split then `Edkins)` |
| `SPENCERC` | `Spencer Calvert (Summer Student)` | **`SS`** | `Student)` |
| `GARYCO` | `Gary Colbert ( FORMA )` | `G)` | the bare `)` is its own token |
| `MAXWEB R2` | `Max Webber R2 (Max Edkins` | `ME` | unbalanced `(` — no closing bracket in the data |
| `ANNEL` | `Anne  (No longer in use)` | `AU` | double space, then `use)` |
| `ALLANA` | `Allan Andrewson(Temp)` | `AA` | no space before `(` — correct **by accident** |

**The multi-word class is the dangerous one.** `(Max Edkins)`, `(For Planning)`, `(Night Shift)`,
`(Summer Student)`, `(Lakeland Steel LTD)`, `(no longer in use)` all produce plausible-looking initials for
the wrong person. `(TS)`, `(Livewires)`, `(FORMA)`, `(Agsam)`, `(Richmond)`, `(Boilerhouse)`, `(Lakeland)`,
`(Contractor)`, `(Tradestaff)`, `(Finnco)` produce the visible `X(` break. Landmines §E recorded only the
second; the first has been on the rail unnoticed.

**Not licensed by this evidence:** the trailing role token. `Andrew Hornby R2 (Max Edkins)` becomes `AR` even
after the brackets are gone, because the oracle takes first-and-last. Which tokens are role suffixes
(`R2`, `NS`, `SUP`, `CALLOUT`, `PROJECT`) is a site-specific list and a second judgement call — **new open
item 35**, §9.3. It is not fixed in this slice and its test case asserts the *unfixed* value so the gap is
recorded rather than discovered.

Short ids of 2–4 characters never reach the name path at all (`1 < len(s) <= 4` returns the short id), so
`BINS`, `JIMH`, `LESB`, `MAXE`, `SAMR`, `BOBS`, `TAHI` are all unaffected either way.

## 3. The changes, exactly

### 3.1 `sql.py` → 1.1.0 — one column

`PRIORITIES` gains, after the `Priority_Title` line:

```sql
       RTRIM(COALESCE(Colour, '')) AS Colour,
```

`ORDER BY Sort_Sequence, Priority_Id` is **unchanged** — the note above it stays word for word, it is still
load-bearing, and the ties in §2.1.3 are why. The dialect stays `portable`: `COALESCE` + `RTRIM`, no
`ISNULL`, no `dbo.`-less reference, no MSSQL-only function. Extend the existing `note:` block with the
seven-rows-not-fourteen fact and the `varchar(255)` free-text caveat.

### 3.2 `repo.py` → 1.1.0 — one key

`fetch_priorities` gains `"colour": s_(r["Colour"])` after `"title"`. Key order in the dict is cosmetic;
`s_` is the existing coercion twin and turns `None` into `''` even if the SQL guard is ever dropped.

### 3.3 `schemas.py` → 1.1.0 — one field

```python
class Priority(_Strict):
    id: int
    short: str
    title: str
    colour: str
```

`_Strict` is `extra="forbid"`, so **§3.2 and §3.3 cannot ship apart** — repo returning a key the model does
not declare is a 500 on every `/range`, and the model declaring a key repo does not return is a validation
error. That is the pair rule biting inside one slice; both files or neither.

### 3.4 `rules.py` → 1.1.0 — the bracket strip (OD-35)

New private helper, placed immediately above `initialsOf`:

```python
def _nameForInitials(name):
    """Name with bracketed segments removed. RST stores the employer or a
    status in brackets on nearly every row - 'Adam Donald (Max Edkins)' -
    and first-and-last would take a letter out of the bracket. An unbalanced
    '(' takes the rest of the string with it (RST User_Id 996). A bare ')' at
    depth zero is dropped ('Gary Colbert ( FORMA )'). OD-35."""
    out = []
    depth = 0
    for ch in _s(name):
        if ch == "(":
            depth += 1
        elif ch == ")":
            if depth > 0:
                depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)
```

`initialsOf` changes on **one line** — the `parts` comprehension:

```python
    parts = [p for p in _nameForInitials(name).replace("-", " ").split(" ") if p and p[0].isalpha()]
```

Everything else in the function is untouched: the `EXT-` strip, the `1 < len(s) <= 4` short-id bound, the
`(parts[0][0] + parts[-1][0]).upper()` pick, the `s[:3].upper() if s else '?'` fallback. A name that
brackets-strip to fewer than two tokens falls through to that fallback exactly as the oracle does —
`Anne  (No longer in use)` with short id `ANNEL` gives `ANN`, not a guess at the name.

`__version__` → `"1.1.0"`. `PORTED_FROM` stays `"workmate.planner 1.3.1"` — the lineage is still 1.3.1, this
is a departure from it, and OD-35 is the record of that. Add the OD-35 paragraph to the header block.

### 3.5 `router.py` → 1.1.0 — version line only (OD-37)

No logic change. `__version__ = "1.1.0"` plus a changelog line, because `data["apiVersion"] = __version__`
(line 58) is the only signal a generated client has that the payload gained a field.

## 4. Traps

1. **`extra="forbid"` cuts both ways** — §3.3 above. The two files are one change.
2. **`libVersion` is read, never restated.** `test_planner_api` asserts `body["libVersion"] ==
   rules.__version__`; it keeps passing without edit. Do not hard-code `"1.1.0"` in any test.
3. **`isalpha()` is Unicode-aware in Python 3** and would not have been on Jython 2.7 bytes. Macronised
   names (`Ā`, `ō`) pass it correctly here. This is a deliberate consequence of the port, not a bug.
4. **Do not "fix" the role suffix while in the file.** Item 35 is unsigned; a helpful extra token filter is
   exactly the kind of thing Ways of Working §1 forbids smuggling into a build slice.
5. **Do not touch `ORDER BY`, `Active`, or the tie-break** while adding a column to the same statement.
6. **Ruff.** camelCase survives in `rules.py` (`_nameForInitials`, `initialsOf`) — pep8-naming is not enabled;
   confirmed in `pyproject.toml`. Let no `SIM` autofix collapse the `if/elif/elif` depth walk into a
   comprehension: the `depth == 0` guard is behaviour.
7. **Two numbering series both sit at 34.** `OD-35` (a signed decision) and open **item 35** (the role
   suffix) are different things created in the same session. Always carry the `OD-` prefix.

## 5. Test plan

### 5.1 `tests/test_planner_rules.py` → 1.1.0, zero DB

New class, direct on `initialsOf` — the current suite only reaches it through `buildWorkers`:

| shortId | name | asserts | why |
|---|---|---|---|
| `JEANP` | `JP Paalvast (TS)` | `JP` | the item-21 case, single-word bracket |
| `AARONW` | `Aaron Wilson (Livewires)` | `AW` | single-word bracket |
| `ADAMD` | `Adam Donald (Max Edkins)` | `AD` | **multi-word bracket — was `AE`** |
| `TERRYHK` | `Terry Herangi-Kingi (Max Edkins)` | `TK` | hyphen + multi-word bracket |
| `SPENCERC` | `Spencer Calvert (Summer Student)` | `SC` | multi-word bracket |
| `GARYCO` | `Gary Colbert ( FORMA )` | `GC` | padded bracket, bare `)` |
| `MAXWEB R2` | `Max Webber R2 (Max Edkins` | **`MR`** | unbalanced bracket; documents item 35 unfixed |
| `ALLANA` | `Allan Andrewson(Temp)` | `AA` | no space before `(` — must not move |
| `ANNEL` | `Anne  (No longer in use)` | `ANN` | one token left → short-id fallback |
| `BIG MOW` | `Big Mow (FORMA)` | `BM` | space inside a short id |

Must-not-move cases, all already green today and re-asserted directly:
`EXT-AMET` / `Aiden - MetalForm` → `AMET` · `KF` / `Ken Fisher` → `KF` (short-id path, length 2) ·
`LH` / `Liaanna Hay` → `LH` · `''` / `''` → `?` · a one-character short id falls to the name path.

`_nameForInitials` gets its own cases: nested `a (b (c) d) e` → `a  e`, unbalanced → prefix only, bare `)` →
dropped, no brackets → unchanged string.

**`test_initials` at line 201 does not change** — `byid[88]` is `AMET` from the `EXT-` short-id path and
`byid[7]` is `KF` from a 2-character short id. No fixture name in the file contains a bracket, verified.

### 5.2 `tests/test_planner_api.py` → 1.1.0, live on RST

- every entry in `priorities[]` has a `colour` key and it is a `str`
- at least one `colour` is non-empty — proves the column is read, not defaulted to `''` by a typo
- `Priority` rejects an unknown key and accepts `colour` (model-level, no HTTP)
- contract order still `Sort_Sequence, Priority_Id` — assert `short` sequence is not sorted alphabetically,
  which is what a dropped `ORDER BY` would silently produce

**No assertion on the row count.** Seven is today's `Active` state on one database, not a contract; a row
flipped active at KT next month must not turn the suite red. `test_range_pin_table_false_on_rst` is the
precedent for an RST-shaped assertion and it earns that by being about a missing table, not a data count.

### 5.3 Counts

125 backend tests today. After the slice it is 125 + the new cases — **read the number off the run, never
guess it**, and gate on `$LASTEXITCODE`. Frontend stays 155 in 11 files, untouched.

## 6. Open decisions — 🤙 required

| ID | Question | Proposal |
|---|---|---|
| **OD-35** | `initialsOf` is byte-1:1 with the oracle (Port Spec §5). Fixing brackets is a deliberate departure, and `parity_range.py` (item 26) compares this API against the live Ignition oracle — `workers[].initials` will then diff on roughly 300 RST names. | **Depart, and register the diff.** The oracle is wrong: `J(` is visible on KT's own rail and `AE` for Adam Donald is worse — a wrong name on a work order is an operational error, not a cosmetic one. `parity_range.py` carries `workers[].initials` as an **expected** diff with this spec cited, and the Ignition-side fix is a separate carry-back (item 34). The alternative — hold the fix until Ignition moves — keeps a known-wrong rail for the sake of a parity script that does not exist yet. |
| **OD-36** | What does `Priority.colour` carry when the column is NULL or not a hex string? `varchar(255)`, nullable, free text on both sites. | **The API ships the string as stored, `''` for NULL, and validates nothing.** `RTRIM(COALESCE(...))` in SQL, `s_()` in the mapper. The API's job is to report what the column holds; deciding whether `#FF9F40` is paintable is the renderer's job (§9.2). No enum, no hex validator, no default colour in the backend — a backend default would be indistinguishable from real data downstream. |
| **OD-37** | Does `router.__version__` (and therefore the payload's `apiVersion`) bump for a field added inside a sub-model, when `router.py` has no logic change? Ways of Working §2: patch = fix, minor = new field. | **Yes — `router.py` 1.1.0, version line and changelog only.** `apiVersion` is the only contract signal a generated client sees, and a field appeared. The cost is a one-line edit; the cost of the alternative is a client pinned to `apiVersion` 1.0.1 receiving two different payload shapes. Same reasoning makes `rules.py` **1.1.0** rather than 1.0.1 under the strict patch reading: the *value* of a contract field changes on most rows and the parity oracle now expects a diff — that is more than a fix. |

## 7. Smoke

```
cd C:\dev\workmate-saas\backend
uv run ruff check app/planner/sql.py app/planner/repo.py app/planner/schemas.py app/planner/rules.py app/planner/router.py tests/test_planner_rules.py tests/test_planner_api.py
uv run pytest tests/test_planner_rules.py
uv run pytest tests/test_planner_api.py
uv run pytest
"backend exit $LASTEXITCODE"
```

Then the live payload, API already up, read-only — the evidence that the wire actually changed:

```powershell
$r = Invoke-RestMethod "http://127.0.0.1:8000/api/v1/planner/range?from=2026-09-14&to=2026-09-20"
$r.priorities | Format-Table id, short, title, colour -AutoSize
"apiVersion $($r.apiVersion)  libVersion $($r.libVersion)"
$r.workers | Where-Object { $_.name -match '\(' } | Select-Object -First 12 name, initials | Format-Table -AutoSize
($r.workers | Where-Object { $_.initials -match '[()]' }).Count
```

Expected: seven priority rows with distinct colours, `apiVersion 1.1.0`, `libVersion 1.1.0`, bracketed names
showing real initials, and the last line **0**.

## 8. Acceptance

- Seven files in §1, no eighth. `service.py`, the frontend and the generated client untouched.
- Backend green, exit 0, count read from the run; frontend still 155 in 11.
- Every §5.1 row asserted, including `MR` for the unfixed role suffix.
- Nothing in the run wrote to `dbWorkmate`.
- `git commit -m "planner priority colour + initialsOf brackets 1.1.0 — S1h"`, tag the versions that shipped:
  `s1h-priority-initials-1.1.0`.
- Raw log entry carries the §2 tables, the seven-rows correction, and open items 35–38.

## 9. Consequences

### 9.1 Doc corrections for the next compiled set

- **Landmines §E:** the `dbo.Priority` bullet says fourteen rows; add that the payload is **seven** on RST
  (`Active` `1`/`0`), that the active seven have **distinct** colours, and that both `#FF0000` triples are
  inactive. The `initials` bullet gains the multi-word class (`AE` for `Adam Donald`) — the entry currently
  records only `J(` and so understates the defect.
- **Port Spec §5:** the `initialsOf` line moves from "byte-1:1, a fix needs an OD" to "OD-35, departs".
- **Index §6 / Port Spec §9:** item 29 closed (read-only, no `UPDATE`), item 21 closed, item 30 recorded as
  not reproducible with its protocol, items 35–38 opened.

### 9.2 The frontend slice this unblocks (not built here)

Paint from `colour` when it is usable, letter class when it is not. Three constraints already known:
`varchar(255)` free text must pass `^#[0-9A-Fa-f]{6}$` before it goes anywhere near a style attribute;
`N/A` is `#FFFFFF` and the base `.pri` rule sets `color:#2b2b2b`, so light backgrounds read and dark ones
need a luminance check; KT's four identical `#FF8000` rows mean payload colour must **not** win outright or
KT loses its A–D distinction. Needs the `openapi-ts` regen and its own 🤙.

### 9.3 New open items

- **35** — trailing role tokens (`R2`, `NS`, `SUP`, `CALLOUT`, `PROJECT`) still skew initials after OD-35:
  `Andrew Hornby R2 (Max Edkins)` → `AR`. Needs a decision on a site-specific token list; asserted unfixed
  in §5.1 so it cannot be forgotten.
- **36** — `Priority.Colour` is unvalidated `varchar(255)`; the renderer must guard (§9.2).
- **37** — the WO `/range` select goes parallel for 3221 rows and spends most of its wait in exchange
  (`CXSYNC_PORT`, `CXCONSUMER`, `LATCH_EX`); 47k logical reads per execution from five per-row correlated
  subqueries. `OPTION (MAXDOP 1)` would likely beat it but is MSSQL-only against the portability rule — needs
  a portable shape (rewrite the correlated subqueries as joins) and its own measurement.
- **38** — dependency drift in the backend suite: Starlette wants `httpx2` for `TestClient`, and
  `anyio.abc.BlockingPortal` is a deprecated alias. Two warnings, nothing red.

## 10. Changelog

- 1.0.0 (2026-09-13) Initial. Written from the backend audit: `dbo.Priority` and every bracketed `Users.name`
  read on both databases first (§2), `sql.py` / `repo.py` / `schemas.py` / `rules.py` / `router.py` /
  `service.py` and both test files read in full. Closes items 29 and 21, withdraws item 29's `UPDATE`, raises
  OD-35…OD-37 and items 35–38.
