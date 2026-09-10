# Azztec SaaS — Data Layer and the RST Development Database

**File:** Azztec_SaaS_Data_Layer_and_RST_DB_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-10 · **Author:** Adriaan
**Status:** Draft — §8 probes to be run and pasted before S1 starts
**Companions:** `Workmate_PG_Forward_Compat_v1_0.md` (rules), `All_Tables_InDetail.csv` (227 legacy tables), `All_Stored_Procedures_and_Views.csv` (1 091 procs, 19 views)

---

## 1. Purpose

Define how the new backend talks to a database, and pin down the development database: **`dbWorkmate` on the local SQL Server,
restored from the Red Stag Timber (RST) Workmate backup — the legacy .NET schema with ~20 years of work orders, PMs, labour,
parts and purchasing.** It is the richest planner dataset available and the parity oracle for the port.

## 2. The RST database

| Fact | Value / rule |
|------|--------------|
| Schema | the legacy .NET Workmate schema (`dbo`, 227 tables) — same as KT before Ignition-era additions |
| Age | ~20 years of data → expect `char(n)` padding everywhere, NULL-heavy optional columns, dropped-feature residue, triggers |
| Name on dev | restore as **`dbWorkmate`** (the KT dev copy moves to `dbWorkmate_KT` first) — `.env` `WORKMATE_DB_NAME` decides; nothing hard-coded |
| Compatibility level | restored DBs keep their source level; minimum on a modern instance is 100 (SQL 2008). Set `ALTER DATABASE dbWorkmate SET COMPATIBILITY_LEVEL = 160` (or the instance max) after restore and re-run the probes |
| Login | SQL login `svc_workmate` → `db_datareader`, `db_datawriter`, **`db_ddladmin` on dev only** (Alembic creates tables). Live parity with the Ignition rule (reader/writer only) is restored before any client deployment |
| Real data | treat as live: `DRY_RUN=True` first, Marker Law, transaction-rollback tests. Never `TRUNCATE`, never autogenerate migrations against it |
| No PM engine | RST has no Ignition PM engine (`pm_engine`) and no `WO_N_Plan` — `engineOwned()` semantics need OD-1 in the port spec |

## 3. Connection

`WORKMATE_DB_URL` selects the dialect; everything else is derived.

```
# MSSQL (dev) — odbc_connect form, built by app/core/db.py from the parts below
WORKMATE_DB_KIND=mssql
WORKMATE_DB_SERVER=localhost            # or HOST\INSTANCE, or tcp:host,1433
WORKMATE_DB_NAME=dbWorkmate
WORKMATE_DB_USER=svc_workmate
WORKMATE_DB_PASSWORD=...
WORKMATE_DB_TRUST_CERT=true             # ODBC 18 default Encrypt=yes → self-signed cert needs this on dev

# PostgreSQL (target)
WORKMATE_DB_KIND=postgresql
WORKMATE_DB_URL=postgresql+psycopg://workmate:workmate@localhost:5432/workmate
```

`db.py` produces `mssql+pyodbc:///?odbc_connect=<quoted>` with `Driver={ODBC Driver 18 for SQL Server};Server=…;Database=…;UID=…;PWD=…;Encrypt=yes;TrustServerCertificate=yes;`,
sets `pyodbc.pooling = False`, `fast_executemany=True`, `pool_pre_ping=True`. One engine per tenant (D-12), created at startup in the lifespan.

## 4. Access layer contract (`app/core/db.py`)

| Function | Behaviour |
|----------|-----------|
| `get_engine(tenant="default")` | cached SQLAlchemy engine for the tenant |
| `connect()` / `begin()` | FastAPI dependencies: `def get_conn()` yields a connection; writes use `with engine.begin() as conn:` inside the service |
| `rows(conn, sql, **params) -> list[dict]` | `text(sql)` + named binds → `result.mappings()` → dicts with **stripped strings, Decimal→float, int-like numerics→int** (the `_s/_i/_f` twins live here) |
| `scalar(conn, sql, **params)` | first column of first row |
| `execute(conn, sql, **params) -> int` | rowcount |
| `insert_returning_id(conn, sql, **params) -> int` | MSSQL: runs `sql` then `SELECT SCOPE_IDENTITY()` in the same connection; PG: appends `RETURNING <id_col>` — the only place SCOPE_IDENTITY/RETURNING appear in the codebase |
| `config_value(conn, key, default="")` | `SELECT RTRIM(System_ConfigVal) FROM dbo.System_Configuration WHERE RTRIM(System_ConfigCol) = :key` |
| `table_exists(conn, name)` | INFORMATION_SCHEMA check, cached per engine — the `pinTableExists()` twin |
| `db_error(e)` | walks `e.orig` for the driver message (the `_err()` twin) |

Module SQL lives in `app/<module>/sql.py` as named `text()` constants with an NQ-style header:

```python
# name:    planner.wo_range
# dialect: MSSQL-specific — see PG-CONVERT tags (1)
# params:  from_d, to_d (datetime, to_d exclusive)
WO_RANGE = """
SELECT h.WO_ID, RTRIM(COALESCE(h.Short_WO_Id, '')) AS Short_WO_Id, ...
-- PG-CONVERT: TOP 1 -> LIMIT 1 in the pin subselects
...
"""
```

## 5. Dialect rules (from the forward-compat standard, now enforced)

1. `COALESCE` not `ISNULL` · 2. `CURRENT_TIMESTAMP` not `GETDATE()` · 3. `CONCAT()` not `+` · 4. `OFFSET/FETCH` not `TOP` (with `ORDER BY`) · 5. always `dbo.` prefix · 6. no bracket-quoted identifiers in new SQL · 7. multi-value params as `= ANY(...)`-ready lists (SQLAlchemy `bindparam(expanding=True)` renders `IN (:x_1, :x_2)` on both engines — use it) · 8. tag anything else MSSQL-only with `-- PG-CONVERT:`.

**CI gate:** `grep -rn "ISNULL\|GETDATE()\|SELECT TOP\|\[dbo\]" backend/app --include=sql.py` must return only lines that also carry `PG-CONVERT`.
The Ignition planner SQL uses `ISNULL`/`GETDATE()`/`TOP 1` throughout — the port rewrites them on the way in.

**PostgreSQL side (D-3):** tables are created lowercase (`dbo.wo_n_header`, column `wo_id`), and SQL never quotes identifiers, so the same
mixed-case text runs on both engines. The one exception is any legacy column that needs brackets today (`[CC_Disable ]`) — rename at migration.

## 6. Tables the port must add (migrations, hand-written)

The legacy schema CSV has **no** `WO_N_Plan`, `WO_Event_History`, `Diag_Log`, `Module_Settings` — they are Ignition-era or later additions.
Verify on RST with `table_exists()`; create what is missing. Column sets below are exactly what the planner code reads/writes:

| Table | Columns (from `workmate_planner_code_v1_3_1.py`) | Migration |
|-------|--------------------------------------------------|-----------|
| `dbo.WO_N_Plan` | `WO_ID numeric PK`, `Pinned char(1)`, `Pinned_By numeric`, `Pinned_On datetime`, `Prev_Start datetime`, `Note varchar(255)`, `Server_Name varchar(50)`, `Last_Save_Date datetime` | `0002_wo_n_plan` |
| `dbo.WO_Event_History` | `WO_ID`, `User_Id_Edited_By`, `Edited_Date`, `Event_Name`, `event_details varchar(1000)`, `server_name`, `Source_Form` (+ identity PK) — **check RST first: the .NET app may already have it under this name** | `0003_wo_event_history` (conditional) |
| `dbo.Diag_Log` | per `Workmate_Forensic_Diagnostics_Standard_v1_1_0.md` (level, source, message, detail, actor, session/request id, created) | `0004_diag_log` |
| `dbo.App_User` (new) | `App_User_Id identity PK`, `User_Id → Users.User_Id`, `Email`, `Password_Hash`, `Is_Active`, `Roles`, `Created`, `Last_Login` | `0001_app_user` |
| `dbo.System_Configuration` | **exists in the legacy schema** — seed `PLANNER_*` rows only if absent | seed script, DRY_RUN first |

`alembic.ini` → `version_table_schema = dbo`; each migration checks `inspector.has_table()` before creating (idempotent on both KT and RST).

## 7. What the Planner touches

| Table | Read | Write | Columns used |
|-------|:---:|:---:|--------------|
| `WO_N_Header` | ✓ | ✓ (move) | `WO_ID, Short_WO_Id, WO_Title, Status, WO_Type_Flag, Request_Start_Date, Request_End_Date, Week_No, Asset_ID, Location_Id, Purchase_Order_Flag` |
| `WO_N_Details` | ✓ | ✓ (estimate) | `Progress_Id, Priority_Id, Duration_In_Hours, User_ID_Responsibility` |
| `WO_N_Subtasks` | ✓ | ✓ (move shifts `Req_Start_Date`, `Week_No`) | `WO_ID, Task_ID, Req_Start_Date, Week_No` |
| `WO_N_Resource` | ✓ | ✓ (labour rows, `Res_Date` shift) | `Res_Id, WO_Id, User_Id, Planned_Qty, Planned_Unit_Cost, Resource_Note, Res_Date, Skill_Id, UOM_Id, Supplier_Id, Resource_Type` |
| `WO_N_Plan` | ✓ | ✓ (pin/unpin) | §6 |
| `WO_Event_History` | | ✓ (audit rows) | §6 |
| `WO_N_Activity`, `WO_C_Activity` (+ headers) | ✓ (history, `Trx_Type 'L'`, last 730 days) | | `WO_ID, User_ID, Skill_Id, Quantity, Activity_Date, Asset_Id` |
| `Users` | ✓ | | `User_Id, Short_User_Id, User_Name, Active` |
| `User_Skill` | ✓ | ✓ (capacity `Hrs_Per_Week`) | `Sys_User_Skill_Id, User_ID, Skill_ID, UOM_ID, Hrs_Per_Week, Supplier_ID, Active, Rate` |
| `Skill` | ✓ | | `Skill_ID, Skill_Title` |
| `Supplier` | ✓ | | `Supplier_ID, Short_Supplier_Id, Company_Name, Internal_Dept` |
| `Priority` | ✓ | | `Priority_Id, Short_Priority_Id, Priority_Title, Sort_Sequence, Active` |
| `Asset`, `Location` | ✓ | | `Short_asset_Id, Asset_Title, Short_Location_ID, Location_Title` |
| `PO_Header`, `PO_Details` | ✓ (`HasPO`) | | `WO_Id` |
| `Unit_of_Measure` | ✓ | | `UOM_Id, LRStd` |
| `System_Configuration` | ✓ | ✓ (`POST /settings`) | `System_ConfigCol, System_ConfigVal, System_ConfigDesc` |
| `Diag_Log` | | ✓ | §6 |

## 8. First probes on RST (run in SSMS, paste the output into the chat before S1)

```sql
-- 8.1 shape
SELECT compatibility_level, collation_name FROM sys.databases WHERE name = DB_NAME();
SELECT (SELECT COUNT(*) FROM dbo.WO_N_Header) AS wo_open_tbl, (SELECT COUNT(*) FROM dbo.WO_C_Header) AS wo_closed_tbl,
       (SELECT MIN(Request_Start_Date) FROM dbo.WO_N_Header) AS first_start, (SELECT MAX(Request_Start_Date) FROM dbo.WO_N_Header) AS last_start;
-- 8.2 domains the rules depend on
SELECT RTRIM(Status) AS s, RTRIM(WO_Type_Flag) AS t, COUNT(*) FROM dbo.WO_N_Header GROUP BY RTRIM(Status), RTRIM(WO_Type_Flag) ORDER BY 3 DESC;
SELECT RTRIM(Active) a, COUNT(*) FROM dbo.Users GROUP BY RTRIM(Active);
SELECT RTRIM(Active) a, COUNT(*) FROM dbo.User_Skill GROUP BY RTRIM(Active);
SELECT UOM_Id, RTRIM(UOM_Title), RTRIM(LRStd) FROM dbo.Unit_of_Measure WHERE RTRIM(LRStd) IN ('Y','1');
SELECT Supplier_ID, RTRIM(Short_Supplier_Id), RTRIM(Internal_Dept) FROM dbo.Supplier WHERE RTRIM(Internal_Dept) IN ('1','Y');
SELECT Priority_Id, RTRIM(Short_Priority_Id), RTRIM(Colour), Sort_Sequence FROM dbo.Priority;
-- 8.3 time-of-day share on Request_Start_Date (KT was ~50%)
SELECT SUM(CASE WHEN CAST(Request_Start_Date AS time) <> '00:00:00' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS pct_with_time
FROM dbo.WO_N_Header WHERE Request_Start_Date IS NOT NULL;
-- 8.4 Ignition-era tables present?
SELECT name FROM sys.tables WHERE name IN ('WO_N_Plan','WO_Event_History','Diag_Log','Module_Settings','App_User');
SELECT RTRIM(System_ConfigCol), RTRIM(System_ConfigVal) FROM dbo.System_Configuration WHERE System_ConfigCol LIKE 'PLANNER%';
-- 8.5 labour history depth for planner_ai (730-day window)
SELECT COUNT(*) rows_l, SUM(Quantity) hrs, COUNT(DISTINCT User_ID) people FROM dbo.WO_N_Activity WHERE RTRIM(Trx_Type) = 'L' AND Activity_Date >= DATEADD(day,-730,CURRENT_TIMESTAMP);
SELECT COUNT(*) rows_l, SUM(Quantity) hrs, COUNT(DISTINCT User_ID) people FROM dbo.WO_C_Activity WHERE RTRIM(Trx_Type) = 'L' AND Activity_Date >= DATEADD(day,-730,CURRENT_TIMESTAMP);
-- 8.6 triggers (OUTPUT clause hazard)
SELECT OBJECT_NAME(parent_id) tbl, name FROM sys.triggers WHERE parent_id <> 0 ORDER BY 1;
```

Anything that differs from the KT facts in Landmines §E becomes a dated line in the raw log and, if it changes a rule, an OD in the port spec.

## 9. Postgres migration path (later slice, not phase 1)

1. Convert DDL: script reads `All_Tables_InDetail.csv` → lowercase `CREATE TABLE dbo.<table>` with the type map below; primary keys/indexes from `sys.indexes` export.
2. Move data: `pgloader` (Linux/Docker: `dimitri/pgloader`) MSSQL→PG with the casting rules, or a Python ETL (`rows()` in batches → psycopg `COPY`) when pgloader chokes on legacy types.
3. Run the `PG-CONVERT` grep, hand-edit the tagged lines, run the parity tests against both engines.

| MSSQL | PostgreSQL | Note |
|-------|------------|------|
| `char(n)` | `varchar(n)` (values `RTRIM`med on load) | padding is the biggest data cleanup |
| `varchar(-1)` (max) | `text` | |
| `numeric(p,s)` | `numeric(p,s)` | ids used as `numeric(18,0)` → keep, or `bigint` (decision at migration) |
| `datetime` | `timestamp` (no tz) | keep naive; app layer is NZ-local by convention |
| `date` / `time` | `date` / `time` | |
| `bit` | `boolean` | few; flags are mostly `char(1)` |
| `int`/`tinyint`/`smallint` | `integer`/`smallint` | |
| identity | `generated by default as identity` | `insert_returning_id()` swaps to `RETURNING` |

## 10. Changelog

- 1.0.0 (2026-09-10) Initial.
