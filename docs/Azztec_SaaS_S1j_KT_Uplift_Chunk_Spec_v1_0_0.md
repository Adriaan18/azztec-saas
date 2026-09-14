# Azztec SaaS — S1j KT Uplift Chunk Spec

**File:** Azztec_SaaS_S1j_KT_Uplift_Chunk_Spec_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-14 · **Author:** Adriaan
**Status:** Draft — **OD-42, OD-43, OD-44, OD-45, OD-46 need 🤙 before anything is built.** OD-47 is recorded as evidence for the diag persist slice, not signed here.
**Target path:** `docs/Azztec_SaaS_S1j_KT_Uplift_Chunk_Spec_v1_0_0.md` (+ project knowledge)
**Parent spec:** `Azztec_SaaS_Planner_Port_Spec_v1_0_5.md` §6 (the uplift audit, between S1i and S2), §9 (OD-1); `Azztec_SaaS_KT_Schema_Delta_v1_0_0.md` §8 (the nine questions)
**Source of truth:** `dbWorkmate_KT` (the read-only oracle) — its catalog, read at build time; the delta for what is used; `repo.py` 1.1.0 / `sql.py` 1.1.0 / `test_planner_repo.py` 1.0.2 / `test_planner_api.py` 1.1.0 for what flips
**Closes:** open item **32**. Flips OD-1 into its intended end state. Raises nothing frontend.
**Signed decisions in force:** D-3 (portable DDL, PG lowercase, `getdate()` → `CURRENT_TIMESTAMP`), D-8 (`Diag_Log` is the persist target), D-12 (`dbo` only on PG), OD-1 (no RST branch in `engineOwned`; a migration makes PMs movable-with-pin), OD-3 (`Server_Name = 'SaaS'` when S2 writes), Ways of Working §3 (never `--autogenerate`; scripted from the KT catalog, never typed), §5 (`DRY_RUN` first; Marker Law), the carry-back rule (item 40: anything that must reach KT is a DDL script, never a file)

---

## 1. Scope — six cards and two generated files, then stop

| # | Deliverable | Target path | Version | Change |
|---|---|---|---|---|
| 1 | `Azztec_SaaS_alembic_ini_v1_0_0.ini` | `backend/alembic.ini` | **new** | `script_location = alembic`, `prepend_sys_path = .`, **no `sqlalchemy.url`** — `env.py` builds it |
| 2 | `Azztec_SaaS_alembic_env_v1_0_0.py` | `backend/alembic/env.py` | **new** | URL from `db.build_url(get_settings())`; `version_table = "alembic_version"`, `version_table_schema = "dbo"`; online mode via `engine.begin()`; offline mode (`--sql`) kept — it is the migration's `DRY_RUN` |
| 3 | `Azztec_SaaS_alembic_script_mako_v1_0_0.mako` | `backend/alembic/script.py.mako` | **new** | the standard template with the project header block |
| 4 | `Azztec_SaaS_scripts_kt_uplift_ddl_v1_0_0.py` | `scripts/kt_uplift_ddl.py` | **new** | the generator (§3.2): reads the KT catalog, renders the migration + a manifest; `--dry-run` is the default and prints only |
| 5 | `Azztec_SaaS_test_kt_uplift_v1_0_0.py` | `backend/tests/test_kt_uplift.py` | **new** | pair of 4 (§5.1–5.3) |
| 6 | `Azztec_SaaS_test_planner_api_v1_2_0.py` | `backend/tests/test_planner_api.py` | 1.1.0 → **1.2.0** | the OD-1 trip-wire flipped on purpose (§3.4) |

**Generated at build time, committed, reviewed in the smoke, never cards:** `backend/alembic/versions/0001_kt_parity_additive.py` (the migration — its body is what the generator rendered from the catalog) and `docs/kt_uplift_manifest_0001.json` (what the catalog said: every table, column, key, index and check that crossed, with the KT type and the PG rendering). The manifest is the diff target for §5.2 and the carry-back record for item 34.

**Untouched:** every `app/planner/*` module, `sql.py` (its two pin variants already exist — `WO_RANGE_PINNED` becomes the live one), `service.py`, the whole frontend (170 stays 170), `test_planner_repo.py` 1.0.2 (its two OD-1 tests skip themselves — that is what they were written to do), `dbWorkmate_KT` (read-only, read only), `dbWorkmate_KT_RFID`.

**Not in this slice:** routines of any kind (§6 OD-42), `App_User` (D-5 — its own slice; §9), diag persist mode (§9, OD-47 evidence), the `forecast` schema, Bucket 2 / Bucket 4 / orphans / junk, `parity_range.py` (item 26), the `MP_Downtime_*` pair, PG execution (the PG rendering is emitted and committed, not run — Docker is down, item 17).

**The cut available at the gate:** Bucket 1 only (5 tables, `WO_N_Plan` + the four Diag/Module tables) and defer Bucket 3 + the §5 columns to their modules. **Not recommended** — every object is empty and nullable, the guard is per-object, the generator does the work either way, and the delta's reason for all-at-once stands: the dev DB stops surprising the port. If the count is the problem the honest cut is the whole slice, not half a parity.

## 2. Evidence — read 2026-09-14 (second session), before any 🤙

### 2.1 The repo has no Alembic scaffold

```
alembic.ini: False
backend\alembic\versions           (directory, empty)
alembic 1.19.2                     (uv run alembic --version)
pyproject: "alembic>=1.16" · [tool.ruff] extend-exclude = ["alembic/versions"]
```

Architecture 1.0.6 §5 shows `alembic.ini` in the tree and Data Layer 1.0.0 says `alembic.ini → version_table_schema = dbo`. Neither is on disk — the docs described the plan. The scaffold is three small files we own (cards 1–3); `alembic init` is not run, because its template `env.py` would be replaced on the spot and a file we replace is a file we author.

### 2.2 RST: nothing collides, the rights are there

```
db          ddladmin  datawriter
dbWorkmate  1         1

already_on_rst        (12 target tables + alembic_version)  → 0 rows
col_already_on_rst    (6 target column names on 9 target tables)
  WO_C_header  User_Id_Created_By     ← not a target column on that table
  WO_N_Header  User_Id_Created_By     ← same
  PO_Details   User_ID_Created_By     ← same; note the casing drift Id / ID across legacy tables
referenced_legacy_table               → all 12 present: Account, Location_Attachment, Part_Attachment,
  PO_Attachment, PO_Details, Supplier, Users, WO_Attachment, WO_C_header, WO_M_Attachment, WO_N_Header, Work_Code
```

The three column hits are legacy stamps on tables where the uplift adds *other* columns (`Source_Action_ID`, `Invoice_Ref`); the five `*_Attachment` targets have no `User_id_Created_By` today. On MSSQL the comparison is case-insensitive; on PG everything is lowercase — no collision either way, but the generator's "already exists" check is **case-insensitive by construction**, never `==`.

### 2.3 KT: the 12 tables, measured

```
tbl                  idx  pk  uq       fks (Action_Event, Account_WorkCode, External_Contractor)  4
Account_WorkCode     2    1   0        checks (Action_Header, Home_View)                            3
Action_Event         2    1   0
Action_Header        7    1   1        CK_Action_Progress        ([Progress_ID]>=(1) AND [Progress_ID]<=(6))
Diag_Log             3    1   0        CK_Action_Header_Status   ([Status]='G' OR 'D' OR 'C' OR 'V' OR 'A' OR 'K' OR 'P' OR 'H' OR 'R')
Diag_NightShift      2    1   0
Diag_PM_Engine_Run   2    1   0
Email_Automation     2    1   1
External_Contractor  2    1   0
Home_View            2    1   0
Module_Settings      1    1   0
PO_Email_Log         4    1   0        ← PK + IX_PO_Email_Log_PO_Id + IX_PO_Email_Log_PO (duplicate pair) + 1
WO_N_Plan            1    1   0
```

30 index ids on the twelve tables: 12 PKs, 2 unique constraints, **16 plain indexes of which one is the duplicate** — **15 cross**. Column shapes are in the delta §4.1–4.3 and §5; the generator re-reads them from `sys.columns` at build time (§3.2) — this spec does not retype them.

### 2.4 KT: `Action_Header.Status = 'G'` (delta question 7)

```
Status  n            Action_ID  Short_Action_Id  Status  Progress_ID  Promoted_WO_ID  Promoted_Date
A       2            1          A-260515-001     G       6            NULL            NULL
C       38           93         A-260802-001     G       1            514             NULL
D       3            95         A-260812-001     G       1            551             NULL
G       7            115        A-260818-001     G       1            567             NULL
H       1            123        A-260823-001     G       1            598             NULL
K       6            129        A-260831-001     G       1            639             NULL
R       30           130        A-260903-001     G       1            669             NULL
V       11
```

Six of seven `G` rows carry a `Promoted_WO_ID` and `Promoted_Date` is NULL on all seven — consistent with "promoted / generated a WO", not proven by the database. The Action module is not in the SaaS yet; the CHECK crosses **verbatim** (parity), and what `G` means is the Action module audit's first line. **`WO_N_Header` has no `G`** — the WO status domain in Landmines §E does not change.

### 2.5 KT: `Diag_Log` code columns (delta question 4) — codes only, no messages, no rows

```
Source (top 12 of 40)   Tier  Msg_Level  n        rows_  sessions  minlen  maxlen  null_user
PurchaseOrder           F     info       40009    69656  429       0       36      18406
workmate.actions        S     info       4981
WOMaint                 F     info       3113     Site_Code: NULL on all 69656
AttachmentPanel         F     info       2955
workmate.pm_engine      S     info       2882     Tier domain seen: F, S, G, E
workmate.planner        S     info       1254     Msg_Level domain seen: info, warn, error
Planner                 F     info       1319     Source: a view name (Tier F) or a module name (Tier S)
PurchaseOrder           G     warn       146
PurchaseOrder           E     error      129
workmate.diag           S     error      127
Diag                    E     error      60
workmate.planner_api    S     error      76
```

So at KT: `Tier` **is** the diag tag letter, with `S` for gateway scripts; `Msg_Level` is the logging level word; `Source` is the emitting view or module; `Session_Id` is optional (min length 0) and never longer than 36; `Site_Code` is unused. The SaaS mapping falls straight out of `diag.log(level, message, detail, actor)` and the request id — OD-47 (§6) records it for the persist slice. The table crosses **as read**; the fill is not this slice's.

### 2.6 What already flips in the port (read from the PK cards, not remembered)

- `repo.py` 1.1.0 line 84–87: `pin_table_exists()` → `db.table_exists(conn, "WO_N_Plan")` (`inspect().has_table`, lowercase on PG). Line 146–147: the statement switches to `WO_RANGE_PINNED`. Line 102: `locked = eo and not pinned and not pin_table`; `movable = (not locked) and st not in _LOCKED_STATUSES`. With the table present and **empty**, every engine-owned PM becomes `locked: False, movable: True, pinned: False, engineDate: '', pinnedOn: ''`.
- `sql.py` 1.1.0 `_PIN_COLS` (82–96): three correlated selects on `dbo.WO_N_Plan` with `OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY` — the statement that has never run against real data (item 37 named it). It runs for the first time in this slice's smoke.
- `test_planner_repo.py` 1.0.2: `test_all_statements_compile` stops skipping `WO_RANGE_PINNED`; `test_pin_columns_default_off` and `test_od1_engine_owned_pms_are_locked` `pytest.skip` when the table exists — **2 passes become 2 skips**, by design.
- `test_planner_api.py` 1.1.0 line 187–190 `test_range_pin_table_false_on_rst`: `assert body["pinTable"] is False` — the trip-wire its docstring says to update "when the migration lands". Card 6.
- `rules.py` 1.1.0 line 553–559: `moveRules` refuses `ENGINE_OWNED` only when `not pinTable`; line 617: `willPin = eo and not pinned and pinTable` — S2's move will pin. Untouched.

## 3. The changes, exactly

### 3.1 The Alembic scaffold (cards 1–3)

`alembic.ini`: `[alembic] script_location = alembic`, `prepend_sys_path = .`, `file_template = %%(rev)s_%%(slug)s`, no URL, logging section minimal. `env.py`: `from app.core.config import get_settings` / `from app.core.db import build_url`; `context.configure(connection=…, target_metadata=None, version_table="alembic_version", version_table_schema="dbo", literal_binds=True in offline)`. `target_metadata` is **None** on purpose — there is no metadata to autogenerate from and there never will be against the legacy 227 tables. `script.py.mako` is the stock template plus the header block Ways of Working §2 requires.

### 3.2 The generator — `scripts/kt_uplift_ddl.py` 1.0.0

Run from `backend/` so it sees the venv: `uv run python ..\scripts\kt_uplift_ddl.py [--write]`. Pure functions first, I/O at the edge:

- `read_catalog(conn, tables) -> Catalog` — one pass over `sys.tables / sys.columns / sys.types / sys.default_constraints / sys.key_constraints / sys.index_columns / sys.indexes / sys.foreign_keys / sys.foreign_key_columns / sys.check_constraints` in `dbWorkmate_KT`, plus `sys.columns` for the fifteen §5 columns on their nine tables. Read-only, three-part names not needed — the connection's database *is* `dbWorkmate_KT` (OD-45). The scope list (12 tables, 15 columns) is a constant in the script, with the delta bucket each came from as a comment.
- `render_mssql(cat) -> list[str]` and `render_pg(cat) -> list[str]` — plain dicts in, DDL strings out, no DB. Normalisation on the way: `[brackets]` stripped, `((0))` → `0`, `(getdate())` → `CURRENT_TIMESTAMP`, `('N')` → `'N'`; MSSQL keeps `IDENTITY(1,1)`, `datetime2(3)`, `nvarchar(max)`, `bit`; PG gets the OD-46 map. Index names, constraint names and column names are carried **as read**; PG names are lowercased by the renderer, never by hand. The duplicate `IX_PO_Email_Log_PO` is dropped by an explicit `SKIP_INDEXES` constant with the reason next to it (delta §4.3).
- `render_migration(cat, rev="0001", slug="kt_parity_additive") -> str` — the migration file text: two lists `MSSQL = [...]` / `PG = [...]`, `upgrade()` walks the list for `conn.dialect.name` and runs each statement only if its guard says the object is absent (`inspect(conn).has_table`, `get_columns` name set case-folded, `get_indexes` names, `get_foreign_keys` names, `get_check_constraints` names); `downgrade()` drops in reverse, guarded the same way, **columns last and tables first** so a half-applied dev state unwinds. Nothing in the migration is typed — every DDL line is a rendered string, and the file says so in its header.
- `render_manifest(cat) -> dict` — the JSON.
- `main()` — `--dry-run` (default) prints the counts line and both renderings to stdout and writes nothing; `--write` writes `backend/alembic/versions/0001_kt_parity_additive.py` and `docs/kt_uplift_manifest_0001.json`, refusing if either exists (`--force` to overwrite — a dev-only flag, printed when used).

The counts line the smoke pastes: `tables=12 columns=15 pks=12 uqs=2 fks=4 checks=3 indexes=15 (skipped 1)`.

### 3.3 The migration — `0001_kt_parity_additive`

Rendered, not typed (§3.2). Its `upgrade()` on MSSQL creates, in dependency order: `Action_Header` → `Action_Event`; `Account_WorkCode` (FK `Account`, `Work_Code`); `External_Contractor` (FK `Supplier`); then `WO_N_Plan`, `Diag_Log`, `Module_Settings`, `Diag_NightShift`, `Diag_PM_Engine_Run`, `Home_View`, `Email_Automation`, `PO_Email_Log`; then the fifteen `ALTER TABLE … ADD` column statements on the nine legacy tables (all nullable, no defaults — as at KT, delta §5); then the 15 indexes. `alembic_version` lands in `dbo` (a 13th table on RST, expected). No data is written. The RST views over `Supplier`, `PO_Details`, `WO_N_Header` are untouched — a nullable column added beneath a view is safe, and none of them selects the new columns (delta §3).

### 3.4 `test_planner_api.py` → 1.2.0 (card 6)

`test_range_pin_table_false_on_rst` becomes `test_range_pin_table_true_after_0001` with the docstring naming the database it assumes (Ways of Working §6): `assert body["pinTable"] is True`; every `wos[]` row still `pinned is False`, `engineDate == ""`, `pinnedOn == ""` (the table is empty); and the new assertion OD-1's end state needs — every `engineOwned` row is `locked is False` and `movable is True` unless its status is in the locked set. The `[F] range … pinTable=True` diag line is already asserted by shape (line 279). Everything else in the file is untouched; header `Pair of` line follows.

## 4. Traps

1. **`alembic init` writes an `env.py` we would replace on the spot.** Ship ours (card 2) instead; never re-emit a file you have not read — and a file you overwrite unread is the same thing.
2. **`svc_workmate` has no user in `dbWorkmate_KT`.** The generator cannot read the oracle through `build_url()`. It takes `--source-url` defaulting to a **Windows-auth** ODBC string to `dbWorkmate_KT` (`Trusted_Connection=yes`, in-process as the logged-in user — Landmines §B says that works exactly there) — OD-45. The oracle is never flipped read-write for this.
3. **`Trusted_Connection=yes` plus `Encrypt=yes` still needs `TrustServerCertificate=yes`** on the local self-signed cert (Landmines §B) — the default source URL carries both.
4. **Case.** `User_Id_Created_By` / `User_ID_Created_By` / `User_id_Created_By` all exist somewhere in the legacy schema. Every "already exists" check case-folds; on PG the renderer lowercases; the generator asserts no two PG names collide *within one table*.
5. **`sys.check_constraints.definition` is bracketed T-SQL** (`[Status]='G' OR …`). Strip the brackets and carry the expression; PG accepts the result as-is for these three. Do not rewrite it into `IN (...)` — parity keeps KT's spelling.
6. **Identity columns on PG** are `GENERATED BY DEFAULT AS IDENTITY`, not `SERIAL`; PKs on identity columns keep their KT constraint names.
7. **`inspect().get_check_constraints()` on MSSQL returns names**; on PG too — guard by name. `get_indexes()` excludes the PK — guard PKs via `get_pk_constraint()`.
8. **The migration runs as `svc_workmate` through `build_url()`** — `ddladmin` verified `1` on RST (§2.2). If a client site's app user lacks it, the migration is run by a DBA from the same file: that is the whole reason it is a static, reviewable file.
9. **`WO_RANGE_PINNED` has never executed on data.** The smoke pastes `/range` timing before and after; item 37's three correlated subqueries now hit a real (empty) table. If the standing week moves out of the 70–700 ms band, that is a finding for item 37, not a reason to revert — record it.
10. **`test_planner_repo.py`'s two OD-1 tests must show as `skipped`, not `passed`.** Read the summary: predicted `… passed, 2 skipped`. A run that still says 156 passed with no skips means the table did not land in the database the suite is pointed at.
11. **`--write` is the only thing that touches the tree, `alembic upgrade head` the only thing that touches RST.** `alembic upgrade head --sql` first (offline render to stdout — the migration's `DRY_RUN`), read it, then the real run. Marker Law after: every crossed table `COUNT(*) = 0`.
12. **Docker is down (item 17)** — the PG rendering is committed and pinned by §5.1, not executed. Say so in the log; the first PG run is its own smoke.
13. **`Session_Id` is `varchar(64)` but KT never exceeds 36** — a request id fits; nothing to widen. Do not "improve" the DDL.

## 5. Test plan

### 5.1 `test_kt_uplift.py` — the generator's pure half, zero DB

- `render_mssql` / `render_pg` on a hand-built two-table `Catalog` dict (one identity PK, one `char(1) DEFAULT 'N'`, one `datetime DEFAULT getdate()`, one `bit DEFAULT 1`, one `nvarchar(max)`, one FK, one CHECK, one duplicate index in `SKIP_INDEXES`): the MSSQL rendering carries `IDENTITY(1,1)` / `CURRENT_TIMESTAMP` / `'N'` and no `getdate` / no `[`; the PG rendering carries `GENERATED BY DEFAULT AS IDENTITY` / `boolean` / `text` / lowercase names / `CURRENT_TIMESTAMP`; the skipped index appears in neither; dependency order puts the referenced table first.
- `render_migration` output: parses (`ast.parse`), defines `upgrade` and `downgrade`, contains both lists, and every statement in the lists is guarded (one guard call per statement — counted).
- Normalisation cases: `((0))`, `('N')`, `(getdate())`, `((1))`, `[Progress_ID]>=(1)`.

### 5.2 The catalog gate — needs `dbWorkmate_KT`, skips by name when it is unreachable

`test_committed_migration_matches_the_kt_catalog`: re-read the catalog through the same source URL the generator used, re-render, and assert the committed `0001_kt_parity_additive.py` and `kt_uplift_manifest_0001.json` are byte-equal to the rendering. The docstring names the oracle. Skips (not passes) when the source URL cannot connect — a skip is visible in the summary; a silent pass would not be.

### 5.3 The RST gate — rolled-back connection, runs after `alembic upgrade head`

- `pin_table_exists(conn) is True`; all 12 tables present; all 15 columns present (case-folded); `alembic_version` holds `0001`.
- Marker Law: `COUNT(*) = 0` on each crossed table.
- `WO_RANGE_PINNED` executes on the standing week and returns the same row count as `WO_RANGE_NOPIN` (273 on the fixed window `test_planner_repo` already uses).

### 5.4 Counts, predicted

Backend: 156 today. Card 6 changes one test's name, not the count. `test_planner_repo.py` moves 2 → skipped. `test_kt_uplift.py` adds **N** new cases — the spec's figure at the gate is the file's own `def test_` count, read before the run. **Predicted summary: `(154 + N) passed, 2 skipped`**, exit 0. Frontend **170 in 11 files**, untouched. Both bare, both counts read from the run.

## 6. Open decisions — 🤙 required

| ID | Question (delta §8) | Proposal |
|---|---|---|
| **OD-42** | Q1 scope, Q7, Q9 | **All additive, now, tables + columns + keys + checks + indexes — and no routines, ever, from this migration.** Bucket 1 (5) + Bucket 3 (7) + the 15 §5 columns, 12 PKs, 2 UQs, 4 FKs, 3 CHECKs (`CK_Action_Header_Status` verbatim, `G` included), 15 of 16 plain indexes. `fn_Diag_UserTrail`, `vw_Diag_Problems`, `vw_Diag_WhoIsOn`, `wmsp_External_ContractorInsertUpdate` stay KT's: T-SQL bodies are not portable, the SaaS reads none of them, and a view over an empty table is decoration. Bucket 2, Bucket 4, the orphans and the 25 junk tables never cross. Q9's carry-backs (the duplicate index, the junk, the two orphans, `Status_Pre_Archive`) go into item 34's list as a note to KT — not this build's work. The alternative (Bucket 1 now, Bucket 3 per module) buys nothing on empty tables and keeps the "does not exist on RST" surprise alive for four more modules. |
| **OD-43** | Q2 numbering | **One migration, `0001_kt_parity_additive`; S3's `0002_wo_n_plan` never exists — S3 inherits the table.** `alembic_version` in `dbo` (Data Layer §98 as planned). The migration file is generated by `scripts/kt_uplift_ddl.py` and committed static: what runs at a client site is a reviewed file, never a live read of a KT database that is not there. |
| **OD-44** | Q3 `WO_N_Plan` on RST before S3 | **Yes.** `pinTable` flips `True` on RST; 2,364 engine-owned PMs read `locked: False, movable: True` while the table is empty — OD-1's intended end state, and what makes S2 testable on real data. The S1 screenshots' lock glyphs go; that is the decision working. The trip-wire test is flipped deliberately as card 6, not left to go red. |
| **OD-45** | how the generator reads the oracle | **A `--source-url` defaulting to a Windows-auth ODBC URL to `dbWorkmate_KT`** (`Trusted_Connection=yes; TrustServerCertificate=yes`, in-process as the logged-in user). The oracle stays `READ_ONLY`; `svc_workmate` gets no user in it (that remains item 26's read-write-flip-create-flip-back, for `parity_range.py`). The generator opens the connection, reads `sys.*`, closes; it never issues anything but `SELECT`. The alternative — flip the oracle to add a user — mutates the thing item 26 depends on being unmutated. |
| **OD-46** | Q8 type parity + the PG rendering | **Types carried as read on MSSQL; the PG rendering is emitted next to it in the same migration, chosen by `conn.dialect.name`, not by `-- PG-CONVERT:` tags.** The tag convention is for `sql.py` statements the CI gate greps; a migration is two renderings of one catalog. Map: `bigint`→`bigint`, `int`→`integer`, `numeric(18,0)`→`numeric(18,0)`, `identity`→`GENERATED BY DEFAULT AS IDENTITY`, `datetime`→`timestamp`, `datetime2(3)`→`timestamp(3)`, `nvarchar(n)`/`varchar(n)`→`varchar(n)`, `nvarchar(max)`/`varchar(max)`→`text`, `char(n)`→`char(n)`, `bit`→`boolean` (`1`→`true`), `getdate()`→`CURRENT_TIMESTAMP`, names lowercase (D-3). `bigint`/`int` ids that point at legacy `numeric(18,0)` keys stay `bigint`/`int` with no FK, exactly as at KT (delta §5 type note) — the mapper's `_i()` already absorbs it. Nothing is aligned "on the way over". PG is rendered and pinned (§5.1), **not executed** — Docker is down (item 17). |

**OD-47 — recorded, not signed (the diag persist slice's decision).** From §2.5, the SaaS fill of `Diag_Log`'s NOT NULL columns falls out of the existing seam: `Tier` = the tag letter (`F`/`G`/`E`; KT also uses `S` for gateway scripts — the SaaS backend would be `S` on that reading, and the browser route `F`), `Msg_Level` = `info`/`warn`/`error`, `Source` = the logger name (`workmate.diag`, or the route/module), `Session_Id` = the request id (≤ 36 chars; `''` is legal at KT), `Wm_User_Id` = the actor (NULL when there is none, as at KT), `Site_Code` NULL. `Logged_At` = `CURRENT_TIMESTAMP` default. Delta question 4 is answered by evidence; it becomes an OD in the persist slice's spec, with `fn_Diag_UserTrail` / `vw_Diag_*` re-considered there if reporting wants them.

Q5 (`App_User` inherits `Ignition_User_Map`'s shape) and Q6 (`forecast`: never for the product unless a forecast module ships, and then with the site domain lifted) are **not this slice's** — Q5 is the D-5 auth audit's first line, Q6 is already D-12's text. Q7 is evidence (§2.4), carried by OD-42. Q9 is a note (OD-42).

## 7. Smoke

Nothing below touches `dbWorkmate_KT` or `dbWorkmate_KT_RFID`. Cards 1–6 dropped and `Test-Path`-verified first, in their own block. **Before:** `/range` on the standing week from the running backend, one tab, the `ms` and `pinTable` noted.

```
cd C:\dev\workmate-saas\backend
uv run ruff format .
uv run ruff check .
uv run python ..\scripts\kt_uplift_ddl.py                       # dry run: counts line + both renderings, writes nothing
"generator exit $LASTEXITCODE"
```

Read the counts line against `tables=12 columns=15 pks=12 uqs=2 fks=4 checks=3 indexes=15 (skipped 1)`. Then:

```
cd C:\dev\workmate-saas\backend
uv run python ..\scripts\kt_uplift_ddl.py --write
git -C .. status --short                                        # expect: 2 untracked — the migration and the manifest
uv run alembic upgrade head --sql                               # offline render = DRY_RUN: read it, nothing runs
"offline exit $LASTEXITCODE"
```

```
cd C:\dev\workmate-saas\backend
uv run alembic upgrade head                                     # the one write to RST
"upgrade exit $LASTEXITCODE"
uv run alembic current
uv run pytest                                                   # predicted: (154 + N) passed, 2 skipped, exit 0 — read it
"pytest exit $LASTEXITCODE"
```

```
sqlcmd -S localhost -E -C -d dbWorkmate -W -w 300 -Q "SET NOCOUNT ON; SELECT DB_NAME() AS db; SELECT version_num FROM dbo.alembic_version; SELECT t.name AS tbl, p.rows FROM sys.tables t JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0,1) WHERE t.name IN ('WO_N_Plan','Diag_Log','Module_Settings','Diag_NightShift','Diag_PM_Engine_Run','Action_Header','Action_Event','Home_View','Account_WorkCode','Email_Automation','PO_Email_Log','External_Contractor') ORDER BY t.name; SELECT COUNT(*) AS new_cols FROM sys.columns WHERE name IN ('Source_Action_ID','Email_2','Email_3','Invoice_Ref','Creation_Date','User_id_Created_By') AND OBJECT_NAME(object_id) IN ('WO_N_Header','WO_C_header','Supplier','PO_Details','WO_Attachment','WO_M_Attachment','PO_Attachment','Part_Attachment','Location_Attachment');"
```

Expect `0001`, twelve rows all `rows = 0`, `new_cols 15`. Then the backend restarted in its own window, one tab: `/range` on the standing week → `pinTable: true`, `counts` unchanged (`273 / 273 PM`), `ms` inside the band, and the dev-server line `[F] range … pinTable=True`. In the browser: PM chips no longer carry the lock glyph; hover still `chipTitle` (OD-33); the day dialog on 14 Sep still 106 PMs. Screenshot. `pnpm test` untouched — 170.

Then commit: the six cards + the two generated files, **predicted 8 staged paths, 0 deletions**; tag `s1j-kt-uplift-1.0.0` (the generator's version — the headline that shipped).

## 8. Acceptance

- Six cards in §1, no seventh; two generated files committed with them. Every backend planner module and every frontend file untouched.
- `dbWorkmate_KT` still `is_read_only 1`; `dbWorkmate_KT_RFID` untouched.
- Counts line as predicted; `alembic current` = `0001`; twelve tables at 0 rows; 15 new columns; `alembic_version` in `dbo`.
- Backend `(154 + N) passed, 2 skipped`, exit 0, read from the run; frontend 170, exit 0.
- `/range` `pinTable: true`, counts unchanged, timing recorded before and after (item 37 evidence either way).
- §5.2 gate green against the oracle; §5.1 pins both renderings.
- Nothing wrote data; nothing typed DDL.

## 9. Consequences

### 9.1 Doc corrections for the next compiled set

- **Architecture §5**: `alembic.ini` / `env.py` / `script.py.mako` as shipped (they were not on disk before this slice); `alembic/versions/` gains `0001_kt_parity_additive.py`; `docs/` gains the manifest; §3.1 Migrations row → the numbering decided (OD-43), the generator named; §4 D-3 → the first DDL through the rule shipped as two renderings (OD-46); D-8 → OD-47's mapping recorded as evidence.
- **Port Spec §3** `pinTable` → `True` on RST since S1j; §5 `moveRules` line → the pin path is live; §6 → the S1j row and "between S1j and S2 sits the S2 audit"; S3 row → inherits the table; §8 → `test_planner_api` 1.2.0 and the two skips; §9 → OD-42…OD-46 recorded, OD-47 as evidence, item 32 closed, OD-1's landing date filled in.
- **Landmines §B**: the Windows-auth catalog read; `alembic init`'s replaceable `env.py`; bracketed `check_constraints.definition`; PG identity syntax. **§E**: the `WO_N_Plan` line → exists on RST since 0001, empty; the WO status line → `G` is Action-only with the promotion evidence; the `Users.User_Id` line gains the `Id`/`ID`/`id` casing drift.
- **Ways of Working §3** Migrations row → "generated by `scripts/kt_uplift_ddl.py`, committed static, diffed against the catalog by a test".
- **Index** §1 state, §3 the new files, §5 `/range` row (`pinTable: true`, the post-0001 timing), §6 next → the S2 audit.

### 9.2 What this unblocks

The **S2 audit** with a pin table under it: `move_wo` pins for real, `undo_move` has a `Prev_Start` to read, `test_weekno.py` still needs its three references (the `GetWeekNoAndYear` body is still the outstanding query). `Diag_Log` exists for the persist slice. `Module_Settings` exists for S5.

### 9.3 New open items

- **41** — item 37 gets its first real number: `WO_RANGE_PINNED` timing on the standing week with an empty `WO_N_Plan`, recorded in the log either way.
- **42** — the PG rendering is committed and pinned but has never executed; its first run is a smoke on its own when Docker's first clean start closes item 17.
- **43** — carry-backs to KT from this audit (into item 34's list): drop `IX_PO_Email_Log_PO`, the 25 junk tables, the two orphan procs + `vw_SchedulexCount`, `PO_Header.Status_Pre_Archive`, `Ignition_Tip_Definitions` — a note, as DDL scripts if ever acted on (item 40).

**Numbering hazard, still live:** the OD series moves to 47, the open-item series to 43. `OD-42`/`OD-43` and items 42/43 are different things created in the same session — carry the `OD-` prefix.

## 10. Changelog

- 1.0.0 (2026-09-14) Initial. Written from the uplift audit: the KT Schema Delta read in full; the Alembic scaffold state, RST collision/rights checks, KT index/key/check counts, the `Action_Header` `'G'` rows and CHECK definitions, and `Diag_Log`'s code-column domains read on the box (§2); `repo.py` 1.1.0, `sql.py` 1.1.0, `db.py` 1.0.0, `rules.py` 1.1.0, `test_planner_repo.py` 1.0.2 and `test_planner_api.py` 1.1.0 read from project knowledge for what flips (§2.6). Raises OD-42…OD-46, records OD-47 as evidence, and open items 41–43.
