"""
Azztec_SaaS_scripts_deploy_sql_v1_0_1.py  ->  scripts/deploy_sql.py
Version:  1.0.1
Author:   Adriaan
Spec:     Azztec_SaaS_DP1_Deploy_Schema_Script_Chunk_Spec_v1_0_1.md (OD-90..OD-95, signed 2026-11-06)
Pair of:  backend/tests/test_deploy_sql.py 1.0.1

Renders the client-site schema script from the migrations. A client's DBA runs the output in SSMS
after every database restore (OD-90); the app never runs migrations at a client site.

    backend/alembic/versions/*.py   ->   deploy/sql/azztec_schema.sql

Every migration exposes an `MSSQL` list of steps, each a plain dict
    {"kind": "table" | "column" | "index", "table": ..., "name": ..., "sql": ...}
(the shape scripts/kt_uplift_ddl.py renders). A migration without one is refused (OD-95): the client
script is only ever a render of the migrations, never a hand edit.

Run from backend/ so the venv is in play (the migrations import alembic):
    uv run python ..\\scripts\\deploy_sql.py                  dry run (default): counts line + the script on stdout
    uv run python ..\\scripts\\deploy_sql.py --write          writes deploy/sql/azztec_schema.sql; refuses to overwrite
    uv run python ..\\scripts\\deploy_sql.py --write --force  overwrites (after a new migration)

The script it writes (spec s5.2):
    preflight  sets the session options the migration ran under (sqlcmd starts with QUOTED_IDENTIFIER
               OFF, SSMS with ON); refuses a system database or a database without dbo.Users /
               dbo.WO_N_Header, by SET NOEXEC ON so no later batch executes (OD-94)
    steps      one batch per step, guarded the way the migration guards it; the guard is asked again
               after the EXEC, so a step that failed prints NOT CREATED, never created (OD-91)
    version    dbo.alembic_version created if missing and stamped to the head (OD-92); a version this
               script does not know is left alone and reported
    app user   from @AppLogin, db_datareader + db_datawriter only, every change re-checked; empty skips;
               a sysadmin login and the database owner need nothing; a same-named user that belongs to
               another login is left alone (OD-93). The outcome travels to verify in SESSION_CONTEXT.
    verify     counts what is actually present and ends AZZTEC SCHEMA OK / AZZTEC SCHEMA INCOMPLETE;
               a refused or failed app user is INCOMPLETE too
    last       SET NOEXEC OFF, so a refused run does not leave the SSMS session silently not executing

Output is ASCII, uses no USE, no SQLCMD-mode commands, and keeps colons out of comments (Landmines sA).
No transaction wraps it: a failure stops at that step and re-running is the recovery (OD-91).

Changelog:
  1.0.1  Smoke-review hardening before the first fresh-restore run (2026-11-06), no OD change.
         App user (OD-93): a sysadmin login is skipped (CREATE USER for sa is refused); a login that owns
         the database maps to dbo and gets no grants (ALTER ROLE ... ADD MEMBER dbo is refused); a
         same-named user that belongs to another live login is refused and left alone; the step needs a
         sysadmin to run it (sys.server_principals is filtered for anyone else); every CREATE / ALTER /
         grant is re-checked; the outcome reaches verify, so a refused app user no longer ends OK.
         Steps (OD-91): the guard is asked again after the EXEC - a failed CREATE no longer prints
         created. Preflight: NUMERIC_ROUNDABORT OFF and ANSI_PADDING, ANSI_WARNINGS,
         CONCAT_NULL_YIELDS_NULL, ARITHABORT, QUOTED_IDENTIFIER, ANSI_NULLS ON, whatever the client
         tool starts with. Header: a "Version = schema ..." line (Invoke-RstTestSql logs it) and the
         SQL Server floor (2016, for SESSION_CONTEXT).
  1.0.0  Initial DP1.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
import textwrap
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

__version__ = "1.0.1"

SCHEMA = "dbo"
OUT_RELATIVE = Path("deploy") / "sql" / "azztec_schema.sql"
SYSTEM_DBS: tuple[str, ...] = ("master", "model", "msdb", "tempdb")
REQUIRED_TABLES: tuple[str, ...] = ("Users", "WO_N_Header")
KINDS: tuple[str, ...] = ("table", "column", "index")
APP_ROLES: tuple[str, ...] = ("db_datareader", "db_datawriter")
SESSION_KEY = "azztec_app_login"  # @AppLogin, carried across GO
STATE_KEY = "azztec_app_user"  # ok | skipped | refused | failed, read by verify

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_GO_LINE = re.compile(r"(?im)^\s*GO\s*$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class Migration:
    revision: str
    down_revision: str | None
    steps: tuple[dict[str, str], ...]
    source: str


# ---------------------------------------------------------------------------
# I/O edge: load the migrations
# ---------------------------------------------------------------------------


def _load_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(f"_azztec_migration_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"{path.name}: cannot be loaded as a module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def migration_from_module(mod: Any, source: str) -> Migration:
    """Read revision, down_revision and the MSSQL step list off a loaded migration (OD-95)."""
    rev = getattr(mod, "revision", None)
    if not isinstance(rev, str) or not rev:
        raise ValueError(f"{source}: no revision")
    down = getattr(mod, "down_revision", None)
    if down is not None and not isinstance(down, str):
        raise ValueError(f"{source}: down_revision must be one revision or None (no merges)")
    steps = getattr(mod, "MSSQL", None)
    if not isinstance(steps, (list, tuple)):
        raise ValueError(f"{source}: no MSSQL step list (OD-95) - every migration must expose one")
    checked = tuple(validate_step(s, source) for s in steps)
    return Migration(revision=rev, down_revision=down, steps=checked, source=source)


def load_migrations(versions_dir: Path) -> list[Migration]:
    """Every migration under versions_dir, in revision order from the root to the head."""
    if not versions_dir.is_dir():
        raise ValueError(f"{versions_dir}: not a directory")
    migs = []
    for path in sorted(versions_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        migs.append(migration_from_module(_load_module(path), path.name))
    return chain(migs)


# ---------------------------------------------------------------------------
# pure: order, validation, rendering
# ---------------------------------------------------------------------------


def validate_step(step: Any, source: str) -> dict[str, str]:
    if not isinstance(step, dict):
        raise ValueError(f"{source}: a step is not a dict")
    for key in ("kind", "table", "name", "sql"):
        if not isinstance(step.get(key), str) or not step[key]:
            raise ValueError(f"{source}: a step has no {key}")
    if step["kind"] not in KINDS:
        raise ValueError(f"{source}: unknown step kind {step['kind']!r} (one of {', '.join(KINDS)})")
    for key in ("table", "name"):
        if not _IDENT.match(step[key]):
            raise ValueError(f"{source}: {key} {step[key]!r} is not a plain identifier")
    return {k: step[k] for k in ("kind", "table", "name", "sql")}


def chain(migs: list[Migration]) -> list[Migration]:
    """Order by down_revision from the single root. Refuses a branch, a gap, two roots, a duplicate."""
    if not migs:
        raise ValueError("no migrations found")
    by_rev: dict[str, Migration] = {}
    for m in migs:
        if m.revision in by_rev:
            raise ValueError(f"revision {m.revision} appears twice ({by_rev[m.revision].source}, {m.source})")
        by_rev[m.revision] = m
    by_down: dict[str | None, Migration] = {}
    for m in migs:
        if m.down_revision in by_down:
            other = by_down[m.down_revision]
            raise ValueError(f"branch: {other.source} and {m.source} both follow {m.down_revision}")
        by_down[m.down_revision] = m
    if None not in by_down:
        raise ValueError("no root migration (down_revision None)")
    ordered: list[Migration] = []
    cur: Migration | None = by_down[None]
    while cur is not None:
        ordered.append(cur)
        cur = by_down.get(cur.revision)
    if len(ordered) != len(migs):
        missing = sorted(m.source for m in migs if m not in ordered)
        raise ValueError(f"gap: not reachable from the root - {', '.join(missing)}")
    return ordered


def guard(step: dict[str, str]) -> str:
    """True when the object is ABSENT - the same test the migration's _exists() makes (spec s3.1)."""
    t, n = step["table"], step["name"]
    if step["kind"] == "table":
        return f"OBJECT_ID(N'{SCHEMA}.{t}', N'U') IS NULL"
    if step["kind"] == "column":
        return f"COL_LENGTH(N'{SCHEMA}.{t}', N'{n}') IS NULL"
    if step["kind"] == "index":
        return (
            f"NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'{SCHEMA}.{t}') "
            f"AND name = N'{n}')"
        )
    raise ValueError(f"unknown step kind {step['kind']!r}")


def quote(sql: str) -> str:
    """The step text for EXEC(N'...'): single quotes doubled. A standalone GO line would split the batch."""
    if _GO_LINE.search(sql):
        raise ValueError("a step contains a GO line - it would break the batch")
    return sql.replace("'", "''")


def _label(step: dict[str, str]) -> str:
    if step["kind"] == "table":
        return f"table {SCHEMA}.{step['table']}"
    return f"{step['kind']} {SCHEMA}.{step['table']}.{step['name']}"


def all_steps(migs: list[Migration]) -> list[dict[str, str]]:
    return [s for m in migs for s in m.steps]


def counts(migs: list[Migration]) -> dict[str, int]:
    steps = all_steps(migs)
    return {
        "migrations": len(migs),
        "tables": sum(1 for s in steps if s["kind"] == "table"),
        "columns": sum(1 for s in steps if s["kind"] == "column"),
        "indexes": sum(1 for s in steps if s["kind"] == "index"),
        "steps": len(steps),
    }


def counts_line(migs: list[Migration]) -> str:
    c = counts(migs)
    return (
        f"migrations={c['migrations']} head={migs[-1].revision} tables={c['tables']} "
        f"columns={c['columns']} indexes={c['indexes']} steps={c['steps']}"
    )


def _header(migs: list[Migration], generated_on: str) -> str:
    head = migs[-1].revision
    steps = all_steps(migs)
    names = {k: sorted({_label(s) for s in steps if s["kind"] == k}) for k in KINDS}
    lines = [
        "/* ============================================================================",
        "   Azztec SaaS - client schema script",
        f"   Version          = schema {head} - generated on {generated_on} by scripts/deploy_sql.py {__version__}",
        "   DO NOT HAND-EDIT   it is re-rendered from the migrations whenever they change",
        f"   Migrations       {', '.join(m.revision for m in migs)}",
        "   Needs            SQL Server 2016 or later",
        "",
        "   WHEN    After every restore of the Workmate database, before the Azztec service starts.",
        "   HOW     In SSMS, open a query window CONNECTED TO THE RESTORED WORKMATE DATABASE and run",
        "           this whole file. It needs no SQLCMD mode. It contains no USE statement - it works",
        "           on the database the window is connected to, and its first lines print which one.",
        "   SAFE    Every step checks first and only creates what is missing, so running it twice,",
        "           or on a database that already has part of it, changes nothing twice.",
        "   CHECK   The last line printed must be AZZTEC SCHEMA OK.",
        "",
        "   OPTIONAL   Set @AppLogin below to the login the Azztec service connects as. The",
        "              script then re-creates that login's user in this database (a restore drops",
        "              it) with db_datareader and db_datawriter only. Leave it empty to skip.",
        "              When it is set, run the script as a sysadmin - the step reads the server's",
        "              logins, which other accounts cannot see.",
        "",
        "   WHAT IT ADDS - nothing else is touched",
        f"     {len(names['table'])} tables, {len(names['column'])} columns on existing tables, "
        f"{len(names['index'])} indexes, and dbo.alembic_version",
    ]
    for k in KINDS:
        for n in names[k]:
            lines.append(f"       {n}")
    lines += [
        "",
        "   WHAT IT NEVER DOES",
        "     writes or changes data in a Workmate table, changes an existing column, touches a",
        "     view, a procedure or a trigger, or grants more than db_datareader and db_datawriter",
        "   ============================================================================ */",
    ]
    return "\n".join(lines)


def _preflight(head: str) -> str:
    sysdbs = ", ".join(f"N'{d}'" for d in SYSTEM_DBS)
    need = " OR ".join(f"OBJECT_ID(N'{SCHEMA}.{t}', N'U') IS NULL" for t in REQUIRED_TABLES)
    return f"""SET NOCOUNT ON;
-- Session options as the migration ran them. sqlcmd starts with QUOTED_IDENTIFIER OFF, SSMS with ON.
SET NUMERIC_ROUNDABORT OFF;
SET ANSI_PADDING, ANSI_WARNINGS, CONCAT_NULL_YIELDS_NULL, ARITHABORT, QUOTED_IDENTIFIER, ANSI_NULLS ON;

-- Settings. Set the login the Azztec service uses, or leave empty to skip the app user step.
DECLARE @AppLogin sysname = '';

EXEC sp_set_session_context @key = N'{SESSION_KEY}', @value = @AppLogin;
EXEC sp_set_session_context @key = N'{STATE_KEY}', @value = NULL;
PRINT CONCAT('azztec_schema {head} - db=', DB_NAME(), ' server=', @@SERVERNAME, ' login=', SUSER_SNAME(),
             ' at=', CONVERT(varchar(19), GETDATE(), 120));
IF DB_NAME() IN ({sysdbs}) OR {need}
BEGIN
    PRINT CONCAT('REFUSED - ', DB_NAME(), ' is not a Workmate database. Nothing was changed. ',
                 'Connect the query window to the restored Workmate database and run again.');
    RAISERROR('azztec_schema REFUSED - not a Workmate database', 16, 1);
    SET NOEXEC ON;
END
GO"""


def _created_or_not(absent: str, label: str, indent: str) -> str:
    """After an EXEC, ask the guard again: a statement-level error does not stop the batch."""
    return (
        f"{indent}IF {absent}\n"
        f"{indent}    PRINT 'NOT CREATED {label} - read the error above';\n"
        f"{indent}ELSE\n"
        f"{indent}    PRINT 'created {label}';\n"
    )


def _step_batch(step: dict[str, str]) -> str:
    label = _label(step)
    absent = guard(step)
    return (
        f"IF {absent}\n"
        "BEGIN\n"
        f"    EXEC(N'{quote(step['sql'])}');\n"
        f"{_created_or_not(absent, label, '    ')}"
        "END\n"
        f"ELSE PRINT 'present {label}';\n"
        "GO"
    )


def _version(migs: list[Migration]) -> str:
    head = migs[-1].revision
    known = ", ".join(f"'{m.revision}'" for m in migs)
    absent = f"OBJECT_ID(N'{SCHEMA}.alembic_version', N'U') IS NULL"
    return f"""IF {absent}
BEGIN
    EXEC(N'CREATE TABLE {SCHEMA}.alembic_version (version_num varchar(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))');
{_created_or_not(absent, f"table {SCHEMA}.alembic_version", "    ")}END
ELSE PRINT 'present table {SCHEMA}.alembic_version';
GO
DECLARE @cur varchar(32), @rows int;
SELECT @rows = COUNT(*), @cur = MAX(version_num) FROM {SCHEMA}.alembic_version;
IF @rows = 1 AND @cur = '{head}'
    PRINT 'present version {head}';
ELSE IF @rows = 0 OR (@rows = 1 AND @cur IN ({known}))
BEGIN
    DELETE FROM {SCHEMA}.alembic_version;
    INSERT INTO {SCHEMA}.alembic_version (version_num) VALUES ('{head}');
    PRINT CONCAT('stamped version {head} (was ', COALESCE(@cur, 'none'), ')');
END
ELSE
    PRINT CONCAT('NOT STAMPED - the database carries ', @rows, ' version row(s), latest ', COALESCE(@cur, 'none'),
                 ', which this script does not know. A newer script may have been run here. Left alone.');
GO"""


def _is_member(role: str) -> str:
    return (
        "EXISTS (SELECT 1 FROM sys.database_role_members rm "
        "JOIN sys.database_principals r ON r.principal_id = rm.role_principal_id "
        "JOIN sys.database_principals m ON m.principal_id = rm.member_principal_id "
        f"WHERE r.name = N'{role}' AND m.name = @user)"
    )


def _grant(role: str) -> str:
    member = _is_member(role)
    block = f"""IF {member}
    PRINT CONCAT('present {role} for ', @user);
ELSE
BEGIN
    SET @sql = N'ALTER ROLE {role} ADD MEMBER ' + QUOTENAME(@user);
    EXEC sp_executesql @sql;
    IF {member}
        PRINT CONCAT('granted {role} to ', @user);
    ELSE
    BEGIN
        SET @state = 'failed';
        PRINT CONCAT('NOT DONE {role} for ', @user, ' - read the error above');
    END
END
"""
    return textwrap.indent(block, " " * 12)


def _app_user() -> str:
    grants = "".join(_grant(r) for r in APP_ROLES)
    principal = "type IN ('S', 'U', 'G')"
    return f"""DECLARE @login sysname = CAST(SESSION_CONTEXT(N'{SESSION_KEY}') AS sysname);
DECLARE @user sysname, @owner sysname, @sql nvarchar(max), @state varchar(10) = 'refused';
IF COALESCE(@login, N'') = N''
BEGIN
    SET @state = 'skipped';
    PRINT 'skipped app user - @AppLogin is empty';
END
ELSE IF COALESCE(IS_SRVROLEMEMBER(N'sysadmin'), 0) <> 1
    PRINT CONCAT('REFUSED app user - setting up the user for ', @login, ' needs a sysadmin. ',
                 'Run this script again as one.');
ELSE IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = @login)
    PRINT CONCAT('REFUSED app user - login ', @login, ' does not exist on this server. ',
                 'Create the login, then run this script again.');
ELSE IF IS_SRVROLEMEMBER(N'sysadmin', @login) = 1
BEGIN
    SET @state = 'skipped';
    PRINT CONCAT('skipped app user - login ', @login, ' is a sysadmin, which already has every right here ',
                 '(the service should not run as one)');
END
ELSE
BEGIN
    SELECT @user = name FROM sys.database_principals WHERE sid = SUSER_SID(@login);
    SELECT @owner = sp.name
      FROM sys.database_principals dp
      JOIN sys.server_principals sp ON sp.sid = dp.sid
     WHERE dp.name = @login AND dp.{principal};
    IF @user = N'dbo'
    BEGIN
        SET @state = 'ok';
        PRINT CONCAT('present user dbo for login ', @login, ' - it owns this database, nothing to grant');
    END
    ELSE IF @user IS NULL AND @owner IS NOT NULL
        PRINT CONCAT('REFUSED app user - user ', @login, ' in this database belongs to login ', @owner,
                     '. Left alone.');
    ELSE
    BEGIN
        IF @user IS NOT NULL
            PRINT CONCAT('present user ', @user, ' for login ', @login);
        ELSE
        BEGIN
            IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = @login AND {principal})
                SET @sql = N'ALTER USER ' + QUOTENAME(@login) + N' WITH LOGIN = ' + QUOTENAME(@login);
            ELSE
                SET @sql = N'CREATE USER ' + QUOTENAME(@login) + N' FOR LOGIN ' + QUOTENAME(@login);
            EXEC sp_executesql @sql;
            SELECT @user = name FROM sys.database_principals WHERE sid = SUSER_SID(@login);
            IF @user IS NULL
                PRINT CONCAT('NOT DONE app user - ', @sql, ' did not take, read the error above');
            ELSE IF @sql LIKE N'ALTER USER%'
                PRINT CONCAT('remapped user ', @user, ' to login ', @login, ' (orphaned by the restore)');
            ELSE
                PRINT CONCAT('created user ', @user, ' for login ', @login);
        END
        IF @user IS NULL
            SET @state = 'failed';
        ELSE
        BEGIN
            SET @state = 'ok';
{grants}        END
    END
END
EXEC sp_set_session_context @key = N'{STATE_KEY}', @value = @state;
GO"""


def _verify(migs: list[Migration]) -> str:
    head = migs[-1].revision
    c = counts(migs)
    lines = [
        "DECLARE @t int = 0, @c int = 0, @i int = 0, @v varchar(32);",
        f"DECLARE @app varchar(10) = CAST(SESSION_CONTEXT(N'{STATE_KEY}') AS varchar(10));",
    ]
    var = {"table": "@t", "column": "@c", "index": "@i"}
    for s in all_steps(migs):
        lines.append(f"IF NOT ({guard(s)}) SET {var[s['kind']]} += 1;")
    lines += [
        f"IF OBJECT_ID(N'{SCHEMA}.alembic_version', N'U') IS NOT NULL",
        f"    SELECT @v = MAX(version_num) FROM {SCHEMA}.alembic_version;",
        f"PRINT CONCAT('tables ', @t, '/{c['tables']}  columns ', @c, '/{c['columns']}  indexes ', @i, "
        f"'/{c['indexes']}  version ', COALESCE(@v, 'none'), '  app user ', COALESCE(@app, 'not run'));",
        f"IF @t = {c['tables']} AND @c = {c['columns']} AND @i = {c['indexes']} AND @v = '{head}' "
        "AND @app IN ('ok', 'skipped')",
        "    PRINT 'AZZTEC SCHEMA OK';",
        "ELSE",
        "    PRINT 'AZZTEC SCHEMA INCOMPLETE - read the lines above';",
        "GO",
    ]
    return "\n".join(lines)


def render(migs: list[Migration], generated_on: str) -> str:
    """The whole client script. Deterministic: same migrations and date, byte-identical output."""
    if not _DATE.match(generated_on):
        raise ValueError(f"generated_on {generated_on!r} is not yyyy-mm-dd")
    head = migs[-1].revision
    parts = [
        _header(migs, generated_on),
        _preflight(head),
        "-- Steps, in migration order. Each one checks first and creates only what is missing.",
    ]
    parts += [_step_batch(s) for s in all_steps(migs)]
    parts += [
        "-- Version stamp",
        _version(migs),
        "-- App user",
        _app_user(),
        "-- Verify",
        _verify(migs),
        "SET NOEXEC OFF;\nGO",
    ]
    text = "\n\n".join(parts) + "\n"
    try:
        text.encode("ascii")
    except UnicodeEncodeError as e:
        raise ValueError(f"render is not ASCII at position {e.start}") from e
    return text


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render the client schema script from the migrations (DP1).")
    ap.add_argument(
        "--write", action="store_true", help="write deploy/sql/azztec_schema.sql (default: dry run)"
    )
    ap.add_argument("--force", action="store_true", help="overwrite an existing script")
    a = ap.parse_args(argv)

    root = repo_root()
    migs = load_migrations(root / "backend" / "alembic" / "versions")
    print(f"deploy_sql {__version__} {counts_line(migs)}")
    text = render(migs, date.today().isoformat())

    if not a.write:
        print("-- DRY RUN: nothing written. The script follows.")
        print(text)
        return 0

    out = root / OUT_RELATIVE
    if out.exists() and not a.force:
        print(f"REFUSED: {out} exists (use --force)")
        return 2
    if a.force and out.exists():
        print("--force: overwriting")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="ascii", newline="\n")
    print(f"wrote {out.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
