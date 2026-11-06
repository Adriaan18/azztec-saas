# Azztec SaaS — DP1 Deploy Schema Script — Chunk Spec

**File:** Azztec_SaaS_DP1_Deploy_Schema_Script_Chunk_Spec_v1_0_1.md · **Version:** 1.0.1 · **Date:** 2026-11-06 · **Author:** Adriaan
**Status:** Signed 🤙 2026-11-06 (OD-90…OD-95). 1.0.1 is the smoke re-cut: the rehearsal targets corrected (§3.3), the first real run recorded (§3.5), review hardening inside OD-91/OD-93/OD-94 (§5). **No OD changed.**
**Slice:** DP1, the first of four for the Redstag test drop (DP1 schema script · DP2 sign-in + rights · DP3 Planner moves · DP4 deploy kit).
**Target path:** `docs/` (+ project knowledge: add 1.0.1, drop 1.0.0)
**Sits on:** HEAD `aa4a394` on `main` (pushed), tag `w1b-page-1.0.0`, backend 319 passed / 2 skipped, frontend 384 in 23 files, migration head `0001`.

---

## 1. Why this slice exists

Redstag test in a **test environment their IT installs**, on **Windows Server with SQL Server on the same box**. Their cycle is test, drop the database, restore the latest production backup, test again. Every restore wipes everything the SaaS added to the schema, because production never had it.

So the SaaS needs a script their **DBA runs in SSMS after every restore** that puts the SaaS's tables and columns back. It has to be safe on a fresh restore, safe to run twice, safe on a database that already has some of it, and impossible to run in the wrong database by accident.

The objects already exist in one place: migration `0001_kt_parity_additive`, generated from KT's catalog (S1j, OD-42…OD-46). This slice **generates** a standalone T-SQL script from that migration's own step list. Nothing is retyped.

## 2. Scope

**In:**
- `scripts/deploy_sql.py` **1.0.1**. It reads every migration under `backend/alembic/versions/`, follows the `down_revision` chain to the head, and renders one standalone T-SQL script from each migration's `MSSQL` step list.
- `deploy/sql/azztec_schema.sql` is the generated script, committed static (the OD-43 precedent: what runs at a client site is a reviewed file).
- `backend/tests/test_deploy_sql.py` **1.0.1** holds pure tests, 24 cases. One asserts the committed script equals a fresh render.

**Out:**
- PostgreSQL. Redstag is SQL Server; the PG rendering stays in the migrations, untouched.
- The auth tables. DP2 adds its own migration in the same step-list shape, and this generator picks it up on a re-render (OD-95). DP1 does not wait on DP2.
- The server login itself. Creating a login is the DBA's one-off job and survives a restore. The **database user** does not, so the script re-creates that (OD-93).
- Seeds and data. `0001` writes no data and neither does this script, apart from its own `alembic_version` row.

## 3. Evidence

### 3.1 What the migration holds

`0001`'s `MSSQL` list is an ordered list of plain dicts, `{"kind", "table", "name", "sql"}`, with exactly three kinds, guarded in the migration by the inspector:

| kind | count | migration guard | T-SQL guard in this script |
|---|---|---|---|
| `table` | 12 | `insp.has_table(table)` | `OBJECT_ID(N'dbo.<table>', N'U') IS NULL` |
| `column` | 15 | column name in `get_columns`, case-folded | `COL_LENGTH(N'dbo.<table>', N'<column>') IS NULL` |
| `index` | 15 | index name in `get_indexes`, case-folded | `NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.<table>') AND name = N'<index>')` |

42 steps in all. The counts line from S1j: `tables=12 columns=15 pks=12 uqs=2 fks=4 checks=3 indexes=15 (skipped 1)`. Keys, FKs and checks are inline in the `CREATE TABLE` text, so they need no separate guard. No index is filtered (`kt_uplift_ddl.py` renders `CREATE [UNIQUE] INDEX … (cols) [INCLUDE (…)]` and nothing else).

The step `sql` strings contain single quotes (`DEFAULT 'N'`, the `CK_Action_Header_Status` check), so they are doubled when wrapped in `EXEC(N'...')`.

### 3.2 Why `alembic upgrade head --sql` is not the answer

Offline mode emits every step **unguarded** (`if offline or not _exists(step)`). That render is the migration's DRY_RUN, not a re-runnable script. Run twice, it fails on the first `CREATE TABLE`.

### 3.3 The rehearsal targets (corrected in 1.0.1)

1.0.0 assumed `dbWorkmate_RST_Test` was a pristine RST restore. **It is not.** msdb's restore history (2026-11-06) shows:

| restored into | when | from | backup taken | file |
|---|---|---|---|---|
| `dbWorkmate` (dev) | 2026-09-10 21:39 | **RSTSQL01/dbWorkmate** | 2026-08-26 19:26 | `C:\dev\backups\RST_Workmate.bak` — on disk |
| `dbWorkmate_RST_Test` | 2026-09-23 20:30 | RSTSQL01/dbWorkmate_QL (the Query_Log sidecar, since renamed `dbWorkmate_QL_RST_Test`) | 2026-09-14 08:33 | `C:\SQLBackups\dbworkmate_ql-14-09-26.bak` |
| `dbWorkmate_RST_Test` | 2026-09-24 06:22 | **AzztecDev/dbWorkmate** (our dev database) | 2026-09-24 06:10 | `C:\SQLBackups\dbWorkmate_dev_copy_20260924.bak` |

The 13 objects in `dbWorkmate_RST_Test` were created **2026-09-14 17:54:11**, which is S1j's `alembic upgrade head` on dev. They came along when dev was copied. Two conclusions follow:

- **RST production (as at 26 Aug) carries none of them.** Dev was restored from Redstag's own backup on 09-10, and the objects did not exist until 09-14. That is exactly what the script assumes.
- The rehearsal needs **two targets**:
  - **Already at head**: `dbWorkmate_RST_Test`. Alembic built it, so the script must create nothing there. `Invoke-RstTestSql.ps1` 1.0.6 is pinned to it and supports `-Set`, so the app-user cases that write nothing run there too.
  - **Fresh**: `C:\dev\backups\RST_Workmate.bak` restored as **`dbWorkmate_DP1_Test`** with `Restore-RstTest.ps1` 1.0.5 (`-Bak` explicit, since its default is the QL file; `-ExpectDbName dbWorkmate` by default). The runner is pinned, so this copy runs through **plain `sqlcmd` without `-b`**, which carries on after an error the way SSMS does. Output is logged under `logs\rst_test\dp1\`.

**Landmine:** `C:\dev\backups\RST_Workmate.bak` is the **only pristine RST backup on the box**. When the retired repo `C:\dev\workmate-saas_RETIRED` is deleted, delete that folder only, never `C:\dev`.

### 3.4 The database user does not survive a restore

A database user lives inside the database. Redstag restore from **production**, which has no user for the SaaS's login, so after every restore the SaaS cannot connect until the user is re-created. The DBA would have to remember that every time. The script does it instead (OD-93).

### 3.5 What the first real run showed (1.0.0, 2026-11-06 16:51)

Generator, gates and the already-at-head run, all as predicted:

- `deploy_sql 1.0.0 migrations=1 head=0001 tables=12 columns=15 indexes=15 steps=42`. Both ruff gates clean. **340 passed, 2 skipped.**
- On `dbWorkmate_RST_Test`: sqlcmd exit 0 in 0.6 s, **0 created, 44 present** (42 steps, the version table, the version row), `present version 0001`, `skipped app user`, `tables 12/12  columns 15/15  indexes 15/15  version 0001`, **`AZZTEC SCHEMA OK`**.
- The runner logged `no Version line (unversioned file)`. It looks for `Version :` / `Version =`, and the script's header had neither.

Reading the generated T-SQL against the cases the smoke was about to run turned up four things 1.0.1 fixes:

1. **App user (OD-93):**
   - A login that **owns the database** maps to `dbo`. 1.0.0 then ran `ALTER ROLE … ADD MEMBER [dbo]`, which SQL Server refuses.
   - A **sysadmin** login (`sa`, or the DBA's own) is either `dbo` too, or a `CREATE USER` SQL Server refuses for `sa`.
   - A refused app user still ended **`AZZTEC SCHEMA OK`**, so a mistyped login would pass the DBA's one check and the service would fail to connect afterwards.
2. **Steps (OD-91):** a statement-level error inside `EXEC()` does not stop the batch, so 1.0.0 printed `created` after a failed `CREATE`.
3. **Session options:** `sqlcmd` starts with `QUOTED_IDENTIFIER OFF` (SSMS with ON). No current step needs it, but a filtered index in a later migration would fail under `sqlcmd`. Setting the options also keeps script-built objects identical to alembic-built ones.
4. **Header:** no `Version =` line, so the runner's log could not say which script ran.

## 4. Decisions (signed 🤙 2026-11-06)

| OD | Decision | Why |
|---|---|---|
| **OD-90** | Redstag's schema is applied by **one standalone, idempotent T-SQL script**, `deploy/sql/azztec_schema.sql`, generated from the migrations and committed static. Their DBA runs it in SSMS after every restore. **The app never runs migrations at a client site.** | Their DBA owns their database. A plain `.sql` file is what they can read, review and run. Alembic on their server would need Python, our venv and DDL rights for the app account. |
| **OD-91** | Every step is guarded by the same test the migration uses (§3.1), runs in its own batch, and prints `created` or `present`. **No wrapping transaction**: a failure stops at that step, and re-running is the recovery. | DDL batches with `GO` can't share one transaction cleanly. An idempotent script whose recovery is "run it again" is simpler and easier for a DBA to trust. |
| **OD-92** | The script creates `dbo.alembic_version` if missing and stamps it to the **head revision**, so any copy can say which schema it carries. | The same question `alembic current` answers on our box, answered on theirs with one `SELECT`. |
| **OD-93** | The script re-creates the app's **database user** from one variable at the top, `@AppLogin`. Empty means skip. When set: the login must already exist on the server, the user is created if missing, and it is added to **`db_datareader` and `db_datawriter` only**. | A restore from production drops the user; without this the app is down after every reload. Reader and writer are all the SaaS needs. No DDL rights, no `db_owner`. |
| **OD-94** | The script **refuses to run** in a system database or in any database without `dbo.Users` and `dbo.WO_N_Header`. It uses `SET NOEXEC ON` so every later batch compiles but nothing executes, and prints why. | A DBA in SSMS can be connected to `master` without noticing. NOEXEC is the only refusal that holds across `GO` batches. |
| **OD-95** | Every future migration exposes an `MSSQL` step list in the same shape (`kind` ∈ table / column / index). The generator **refuses** a migration without one. Re-rendering is the only way the script changes, and a test fails if the committed file differs from a fresh render. | DP2's auth tables flow in by re-running one command, never by hand-editing a client-facing script. |

**OD-93 as 1.0.1 implements it.** These are readings of the signed decision, not new ones:
- A **sysadmin** login gets no user and is reported `skipped` (it already has every right; the message says the service should not run as one).
- A login that **owns the database** is reported `present user dbo`, with nothing granted.
- A same-named user that **belongs to another live login** is refused and left alone. The script never takes over someone else's user.
- Setting `@AppLogin` needs the script to be **run by a sysadmin**, because `sys.server_principals` is filtered for anyone else. A non-sysadmin gets a clear refusal, never a false "login does not exist".
- A refused or failed app user ends **`AZZTEC SCHEMA INCOMPLETE`**.

## 5. The changes, exactly

### 5.1 `scripts/deploy_sql.py` 1.0.1, card 1

Run from `backend/` so the venv is in play. Pure below the file-reading edge, so the test drives it with hand-built step lists.

- `load_migrations(versions_dir) -> list[Migration]` imports each `*.py` with `importlib.util.spec_from_file_location` and reads `revision`, `down_revision`, `MSSQL`. It follows `down_revision` from `None` to the head and refuses a branch, a gap, a duplicate or a migration with no `MSSQL` list (OD-95).
- `guard(step) -> str` returns the §3.1 guard for the step's kind; any other kind raises.
- `quote(sql) -> str` doubles single quotes and refuses a step `sql` containing `GO` on a line of its own.
- `render(migrations, generated_on) -> str` builds the whole script (§5.2). It is deterministic: same input, byte-identical output, with the date only in the header.
- `main()`: `--write` writes `deploy/sql/azztec_schema.sql` and refuses to overwrite without `--force`. The default prints the counts line `migrations=1 head=0001 tables=12 columns=15 indexes=15 steps=42` and the render, and writes nothing.

ASCII only. No colon inside a SQL comment (Landmines §A).

### 5.2 `deploy/sql/azztec_schema.sql`, generated

1. **Header comment** covers:
   - `Version = schema 0001 - generated on <date> by scripts/deploy_sql.py 1.0.1`, the line `Invoke-RstTestSql` logs.
   - `DO NOT HAND-EDIT` and the migrations it was rendered from.
   - `Needs SQL Server 2016 or later` (for `SESSION_CONTEXT`; RST runs 2022, compat 160).
   - When and how to run it, and what it adds, by name.
   - What it never does: no data in a Workmate table, no existing column changed, no view, procedure or trigger touched, nothing granted beyond reader and writer.
2. **Session options:** `SET NUMERIC_ROUNDABORT OFF;` and `SET ANSI_PADDING, ANSI_WARNINGS, CONCAT_NULL_YIELDS_NULL, ARITHABORT, QUOTED_IDENTIFIER, ANSI_NULLS ON;`.
3. **Settings:** `DECLARE @AppLogin sysname = '';` uses a plain literal, not `N''`, because `Invoke-RstTestSql -Set` only rewrites a plain one. The value is carried past `GO` in `SESSION_CONTEXT` (`azztec_app_login`). The app-user outcome key (`azztec_app_user`) is reset to NULL here.
4. **Preflight:** prints `DB_NAME()`, `@@SERVERNAME`, `SUSER_SNAME()` and the time. It refuses (OD-94) with `RAISERROR … 16` and `SET NOEXEC ON` when:
   - `DB_NAME()` is a system database, or
   - `dbo.Users` or `dbo.WO_N_Header` is missing.
5. **One batch per step, in migration order:**
   `IF <guard> BEGIN EXEC(N'<sql>'); IF <guard> PRINT 'NOT CREATED <label> - read the error above' ELSE PRINT 'created <label>' END ELSE PRINT 'present <label>'`
6. **Version stamp (OD-92):**
   - `dbo.alembic_version` is created if missing, using the same create-then-ask-again pattern.
   - If the table holds no rows, or one row this chain knows, it is set to the head: `stamped version 0001 (was none)`.
   - One row equal to the head prints `present version 0001`.
   - Anything else prints `NOT STAMPED … Left alone.`
7. **App user (OD-93):** reads `@AppLogin` back from session context and walks this ladder, top to bottom:
   - empty → `skipped`
   - runner not a sysadmin → `REFUSED`
   - login missing → `REFUSED`
   - login is a sysadmin → `skipped`
   - login maps to `dbo` → `present user dbo … nothing to grant`
   - same-named user owned by another live login → `REFUSED … Left alone.`
   - user mapped already → `present user`
   - same-named orphan → `ALTER USER … WITH LOGIN` (`remapped`)
   - otherwise → `CREATE USER … FOR LOGIN` (`created`)

   After every `CREATE` / `ALTER` it re-reads the SID mapping. It then adds `db_datareader` and `db_datawriter` if missing, re-checking each (`granted` / `present` / `NOT DONE`). `QUOTENAME` is used throughout. The outcome (`ok` / `skipped` / `refused` / `failed`) goes to session context.
8. **Verify:** counts the expected objects actually present, from the same guards, and prints `tables 12/12  columns 15/15  indexes 15/15  version 0001  app user <outcome>`. It ends **`AZZTEC SCHEMA OK`** only when all counts match, the version is the head and the app user is `ok` or `skipped`. Otherwise it ends `AZZTEC SCHEMA INCOMPLETE - read the lines above`.
9. **`SET NOEXEC OFF`** is the last batch, so a refused run doesn't leave the DBA's SSMS session silently not executing.

No `USE` statement anywhere: the script runs where the DBA is connected, and the preflight proves where that is.

### 5.3 `backend/tests/test_deploy_sql.py` 1.0.1, card 2

Zero-DB, 24 cases (1.0.0 had 21):

- **Loading:** `load_migrations` on the real `versions/` gives one migration, head `0001`, 12/15/15/42. It refuses a migration with no `MSSQL` list, a branch, a gap, a missing root, an unknown kind and a non-identifier.
- **Guards and quoting:**
  - `guard` produces the exact §3.1 text for each kind.
  - `quote` doubles quotes and round-trips the check constraint, and it refuses a standalone `GO` line.
  - Every real step quotes cleanly.
- **Header:** the first line matching the runner's `^\s*Version\s*[:=]` is the header's, names the schema, the date and the generator version, and the header states the SQL Server floor.
- **Steps:** one batch per step in migration order, each with its guard twice (before and after the `EXEC`) and with `created`, `NOT CREATED` and `present`.
- **Preflight:**
  - Session options are set before `@AppLogin`, and the outcome key is reset.
  - It names all four system databases and both required tables.
  - `SET NOEXEC ON` is in it, and the script ends `SET NOEXEC OFF`.
- **Version stamp:** names the head and knows the whole chain (two-migration case), and keeps `NOT STAMPED`.
- **`@AppLogin`:** a plain `''` literal.
- **App user:**
  - `QUOTENAME`, exactly reader and writer, no `db_owner` / `db_ddladmin` anywhere.
  - The ladder rungs in order.
  - The SID re-read twice, a `NOT DONE` for the user and each role.
  - The block ends by handing its outcome to session context.
- **Verify:** one count per step, and `OK` needs the app user `ok` or `skipped`.
- **Output hygiene:** no `USE`, ASCII only, no colon in a comment, no PRINT starting `ERROR`, deterministic render, date validated, counts line.
- **The committed `deploy/sql/azztec_schema.sql` equals a fresh render**, with the date read off its `Version` line.

## 6. Traps

1. **`EXEC` text runs in its own scope.** A step can't see a variable from the batch around it. None of the 42 needs one; the app-user block is built as dynamic SQL on purpose.
2. **A variable dies at `GO`.** `@AppLogin` and the app-user outcome travel through `SESSION_CONTEXT`, never re-declared.
3. **`NOEXEC` doesn't stop a `PRINT` from compiling**, only from running. A refused run prints the refusal and nothing else, which the smoke checks.
4. **`COL_LENGTH` returns NULL for a missing table as well as a missing column.** Column steps run after table steps, and all 15 columns are on legacy tables that always exist. Noted, not handled.
5. **`Invoke-RstTestSql.ps1` treats any output line starting `ERROR` as a failure.** The script's own messages say `REFUSED`, `NOT CREATED`, `NOT DONE`, `NOT STAMPED` and `INCOMPLETE`, never `ERROR`, so a real SQL error stays the only thing that trips it.
6. **SSMS needs no SQLCMD mode.** Nothing in the script uses `:setvar` or `:r`.
7. **A statement-level error does not stop a batch** (1.0.1). That is why every step and every app-user change asks again before it reports success.
8. **`sqlcmd` without `-b` exits 0 after an error** (SSMS-like). The DP1 smoke gates plain-`sqlcmd` runs on `Msg NNNN` lines and the final line, never on the exit code alone.
9. **`IS_SRVROLEMEMBER` and `sys.server_principals` only tell the truth to a sysadmin** (1.0.1). That is why the app-user step refuses a non-sysadmin runner up front.
10. **The pristine backup is a single file** (§3.3).

## 7. Smoke

Run from the repo root at `C:\Users\Azzte\Dropbox\azztec-saas`. Diag_Log on dev before the smoke: **178** rows.

| # | Step | Expect | Status |
|---|---|---|---|
| 1 | Generate 1.0.0, gates, run on `dbWorkmate_RST_Test` | counts line; ruff 0/0; 340/2; 0 created, 44 present, OK | ✅ 16:51 |
| 2 | Find a pristine RST backup (msdb restore history) | the 26 Aug RSTSQL01 `.bak` on disk | ✅ `C:\dev\backups\RST_Workmate.bak` |
| 3 | Drop 1.0.1, `--write --force`, gates | `deploy_sql 1.0.1 …steps=42`; ruff 0/0; **343 passed, 2 skipped** | |
| 4 | 1.0.1 on `dbWorkmate_RST_Test`, `@AppLogin` empty | 0 created, 44 present, `app user skipped`, OK; runner logs the `Version =` line | |
| 5 | same, `-Set '@AppLogin=no_such_login_dp1'` | `REFUSED app user - login no_such_login_dp1 does not exist…`, `app user refused`, **INCOMPLETE**; no Msg | |
| 6 | same, `-Set '@AppLogin=AzztecDev\Azzte'` (a sysadmin) | `skipped app user - login AzztecDev\Azzte is a sysadmin…`, `app user skipped`, OK | |
| 7 | `Restore-RstTest.ps1 -Bak C:\dev\backups\RST_Workmate.bak -DbName dbWorkmate_DP1_Test`, dry run | header `dbWorkmate` / `RSTSQL01` / 2026-08-26, VERIFYONLY valid, nothing created | |
| 8 | the same with `-Write` | `dbWorkmate_DP1_Test` on the instance, compat as the backup carried it | |
| 9 | Snapshot DP1_Test, then run 1 (plain `sqlcmd`, no `-b`) | **43 created** (42 + `alembic_version`), 0 present, 0 NOT, `stamped version 0001 (was none)`, OK, no Msg | |
| 10 | Snapshot again and diff | removed or changed **0**; every addition is one of the 13 tables or 15 columns; modules and row counts of every existing table unchanged | |
| 11 | Run 2 on DP1_Test | 0 created, **44 present**, OK | |
| 12 | Catalog diff, `dbWorkmate` (alembic) vs DP1_Test (script) | the 13 tables, 15 columns, keys, FKs, checks, defaults, indexes: **0 differences**, system-generated names excluded | |
| 13 | Refusal in `master`, with `-b` then without | REFUSED + Msg 50000 only; no created / present / tables / AZZTEC line; `master` holds none of the 13 tables before or after | |
| 14 | App user on DP1_Test, `@AppLogin = svc_workmate` | `created user svc_workmate…`, two `granted`, `app user ok`, OK; again → `present` ×3, OK; roles = exactly reader + writer | |
| 15 | Diag_Log on dev | 178, unchanged | |
| 16 | Commit, tag `dp1-schema-1.0.0`, push | | |

Not exercised on the box: the orphan **remap** (Redstag's production has no app user, so their path is `created`; remap is the go-live path, when production carries the user) and the **owner-is-dbo** rung. Both are text-tested.

## 8. Acceptance

- 43 created then 44 present on the fresh copy, both `AZZTEC SCHEMA OK`; 0 created / 44 present on the already-at-head copy.
- The before/after snapshot shows additions only, all of them expected.
- Zero catalog differences between the alembic-built and script-built schemas.
- The refusal holds in `master` under both `sqlcmd` modes.
- The app user is created once, granted reader and writer only, and left alone on a re-run. A missing login ends `INCOMPLETE`; a sysadmin login is skipped.
- Suites green, both ruff gates clean, the committed script equal to a fresh render.

## 9. What this hands DP2 and DP4

- **DP2** writes migration `0002` in the `MSSQL` step-list shape. One `--write --force` re-render puts its tables in the script, and the committed-equals-render test proves it.
- **DP4** ships `deploy/sql/azztec_schema.sql` in the kit with a one-page DBA note: restore, run this file as a sysadmin with `@AppLogin` set to the service's login, look for `AZZTEC SCHEMA OK`. Decide there which login the service uses:
  - a SQL login, or
  - a Windows virtual account such as `NT SERVICE\<name>`, which needs no password in `.env`.

  Decide also whether the kit carries a copy of the script with `@AppLogin` pre-filled.

## 10. Changelog

- 1.0.1 (2026-11-06) Smoke re-cut, no OD change.
  - §3.3: rewritten. `dbWorkmate_RST_Test` is a 09-24 dev copy at head, not an RST restore; the fresh target is `RST_Workmate.bak` as `dbWorkmate_DP1_Test`.
  - §3.5: new. The first real run, and four review findings.
  - §4: OD-93's 1.0.1 reading.
  - §5: session options, the step re-check, the app-user ladder, the outcome reaching verify, the `Version =` header line, `@AppLogin` as a plain `''`, 24 test cases.
  - §6: traps 7–10.
  - §7: rewritten with both targets and the snapshot, catalog and refusal checks.
  - §8: 43 created then 44 present.
  - §9: DP4 login choice.
- 1.0.0 (2026-11-06) Draft for 🤙. Written after reading `scripts/kt_uplift_ddl.py` 1.0.1 (the migration's step shape and guards), `Restore-RstTest.ps1` 1.0.5 and `Invoke-RstTestSql.ps1` 1.0.6 (the rehearsal harness), and Redstag's reload cycle as Adriaan described it on 2026-11-06.
