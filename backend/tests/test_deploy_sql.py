"""
Azztec_SaaS_backend_tests_test_deploy_sql_v1_0_2.py  ->  backend/tests/test_deploy_sql.py
Version:  1.0.2
Author:   Adriaan
Spec:     Azztec_SaaS_DP1_Deploy_Schema_Script_Chunk_Spec_v1_0_1.md s5.3 (OD-90..OD-95)
Pair of:  scripts/deploy_sql.py 1.0.1

Zero-DB. Most cases drive the generator with hand-built Migration objects; the last block reads the
real backend/alembic/versions/ (one import of each migration, no connection) and pins the committed
deploy/sql/azztec_schema.sql to a fresh render, so a hand edit to the client script is a red test
(the S1j precedent, OD-95).

Changelog:
  1.0.2  DP2a: migration 0002_auth_sessions is the head - two tables and three indexes, so the real
         chain is 0001 -> 0002 with 14 tables, 15 columns, 18 indexes, 47 steps. Nothing else changed.
  1.0.1  24 cases. New - the header's Version line is the one Invoke-RstTestSql reads; the preflight
         sets the session options and resets the app-user outcome; the app-user ladder (sysadmin
         runner, missing login, sysadmin login, database owner, a user that belongs to another login,
         every change re-checked, outcome handed to verify). Changed - every step prints NOT CREATED
         when its guard still says absent after the EXEC; verify needs the app user ok or skipped; the
         committed-script case reads the date off the Version line.
  1.0.0  Initial DP1. 21 cases.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("deploy_sql", ROOT / "scripts" / "deploy_sql.py")
assert _spec is not None and _spec.loader is not None
deploy_sql = importlib.util.module_from_spec(_spec)
sys.modules["deploy_sql"] = deploy_sql
_spec.loader.exec_module(deploy_sql)

Migration = deploy_sql.Migration
VERSIONS = ROOT / "backend" / "alembic" / "versions"
COMMITTED = ROOT / "deploy" / "sql" / "azztec_schema.sql"
DAY = "2026-11-06"
# Invoke-RstTestSql.ps1 1.0.6 logs the first line matching this as the file's version
RUNNER_VERSION_LINE = re.compile(r"(?m)^\s*Version\s*[:=].*$")


def _step(kind: str, table: str, name: str, sql: str) -> dict[str, str]:
    return {"kind": kind, "table": table, "name": name, "sql": sql}


def _mig(rev: str, down: str | None, *steps: dict[str, str]) -> Migration:
    return Migration(revision=rev, down_revision=down, steps=tuple(steps), source=f"{rev}_x.py")


def _between(text: str, start: str, end: str) -> str:
    return text[text.index(start) : text.index(end)]


T1 = _step(
    "table",
    "Action_Header",
    "Action_Header",
    "CREATE TABLE dbo.Action_Header (\n    Id int NOT NULL,\n    Status char(1) NOT NULL DEFAULT 'N',\n"
    "    CONSTRAINT CK_Action_Header_Status CHECK (Status='G' OR Status='D')\n)",
)
C1 = _step("column", "Supplier", "Email_2", "ALTER TABLE dbo.Supplier ADD Email_2 varchar(255) NULL")
I1 = _step(
    "index",
    "Action_Header",
    "IX_Action_Header_Status",
    "CREATE INDEX IX_Action_Header_Status ON dbo.Action_Header (Status)",
)
ONE = [_mig("0001", None, T1, C1, I1)]


# ---------------------------------------------------------------------------
# loading and ordering
# ---------------------------------------------------------------------------


def test_chain_orders_root_to_head_whatever_the_input_order():
    a, b, c = _mig("0001", None), _mig("0002", "0001"), _mig("0003", "0002")
    assert [m.revision for m in deploy_sql.chain([c, a, b])] == ["0001", "0002", "0003"]


def test_chain_refuses_a_branch():
    with pytest.raises(ValueError, match="branch"):
        deploy_sql.chain([_mig("0001", None), _mig("0002", "0001"), _mig("0003", "0001")])


def test_chain_refuses_a_gap_and_a_missing_root():
    with pytest.raises(ValueError, match="gap"):
        deploy_sql.chain([_mig("0001", None), _mig("0003", "0002")])
    with pytest.raises(ValueError, match="no root"):
        deploy_sql.chain([_mig("0002", "0001")])


def test_a_migration_without_an_mssql_list_is_refused():
    with pytest.raises(ValueError, match="OD-95"):
        deploy_sql.migration_from_module(SimpleNamespace(revision="0002", down_revision="0001"), "0002_x.py")


def test_a_step_with_an_unknown_kind_or_a_non_identifier_is_refused():
    with pytest.raises(ValueError, match="unknown step kind"):
        deploy_sql.validate_step(_step("view", "V", "V", "CREATE VIEW dbo.V AS SELECT 1"), "x")
    with pytest.raises(ValueError, match="plain identifier"):
        deploy_sql.validate_step(_step("table", "Bad; DROP", "Bad", "CREATE TABLE x (a int)"), "x")


# ---------------------------------------------------------------------------
# guards and quoting
# ---------------------------------------------------------------------------


def test_guards_are_the_three_spec_texts():
    assert deploy_sql.guard(T1) == "OBJECT_ID(N'dbo.Action_Header', N'U') IS NULL"
    assert deploy_sql.guard(C1) == "COL_LENGTH(N'dbo.Supplier', N'Email_2') IS NULL"
    assert deploy_sql.guard(I1) == (
        "NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.Action_Header') "
        "AND name = N'IX_Action_Header_Status')"
    )
    with pytest.raises(ValueError):
        deploy_sql.guard({**T1, "kind": "view"})


def test_quote_doubles_single_quotes_and_round_trips_the_check_constraint():
    q = deploy_sql.quote(T1["sql"])
    assert "DEFAULT ''N''" in q and "Status=''G''" in q
    assert q.replace("''", "'") == T1["sql"]


def test_quote_refuses_a_standalone_go_line():
    with pytest.raises(ValueError, match="GO"):
        deploy_sql.quote("CREATE TABLE a (x int)\nGO\nCREATE TABLE b (y int)")
    assert deploy_sql.quote("CREATE TABLE dbo.GoLive (x int)")  # GO inside a word is fine


# ---------------------------------------------------------------------------
# the rendered script
# ---------------------------------------------------------------------------


def test_header_carries_the_version_line_the_runner_logs():
    text = deploy_sql.render(ONE, DAY)
    header = text[: text.index("*/")]
    m = RUNNER_VERSION_LINE.search(text)
    assert m and m.start() < len(header), "the first Version line must be the header's"
    assert f"schema 0001 - generated on {DAY} by scripts/deploy_sql.py {deploy_sql.__version__}" in m.group(0)
    assert "SQL Server 2016 or later" in header and "DO NOT HAND-EDIT" in header


def test_one_batch_per_step_in_migration_order_each_with_created_not_created_and_present():
    text = deploy_sql.render(ONE, DAY)
    labels = re.findall(r"PRINT 'created (\w+ dbo\.[\w.]+)'", text)
    assert labels[:3] == [
        "table dbo.Action_Header",
        "column dbo.Supplier.Email_2",
        "index dbo.Action_Header.IX_Action_Header_Status",
    ]
    for label in labels[:3]:
        assert f"PRINT 'NOT CREATED {label} - read the error above';" in text
        assert f"ELSE PRINT 'present {label}';" in text
    steps = _between(text, "-- Steps", "-- Version stamp")
    for s in (T1, C1, I1):
        assert steps.count(deploy_sql.guard(s)) == 2  # once before the EXEC, once after it
    assert text.count("EXEC(N'") == 3 + 1  # three steps + the alembic_version table


def test_preflight_sets_the_session_options_and_resets_the_app_user_outcome():
    text = deploy_sql.render(ONE, DAY)
    pre = text[: text.index("-- Steps")]
    opts = "SET ANSI_PADDING, ANSI_WARNINGS, CONCAT_NULL_YIELDS_NULL, ARITHABORT, QUOTED_IDENTIFIER, ANSI_NULLS ON;"
    assert "SET NUMERIC_ROUNDABORT OFF;" in pre and opts in pre
    assert pre.index(opts) < pre.index("DECLARE @AppLogin")
    assert "EXEC sp_set_session_context @key = N'azztec_app_user', @value = NULL;" in pre


def test_preflight_refuses_system_databases_and_non_workmate_databases_by_noexec():
    text = deploy_sql.render(ONE, DAY)
    pre = text[: text.index("-- Steps")]
    for db in ("master", "model", "msdb", "tempdb"):
        assert f"N'{db}'" in pre
    assert "OBJECT_ID(N'dbo.Users', N'U') IS NULL" in pre
    assert "OBJECT_ID(N'dbo.WO_N_Header', N'U') IS NULL" in pre
    assert "SET NOEXEC ON;" in pre
    assert text.rstrip().endswith("SET NOEXEC OFF;\nGO")


def test_version_stamp_names_the_head_and_knows_the_whole_chain():
    two = [
        ONE[0],
        _mig(
            "0002", "0001", _step("table", "Auth_Login", "Auth_Login", "CREATE TABLE dbo.Auth_Login (a int)")
        ),
    ]
    text = deploy_sql.render(two, DAY)
    assert "VALUES ('0002')" in text
    assert "@cur IN ('0001', '0002')" in text
    assert "NOT STAMPED" in text
    assert "PRINT 'NOT CREATED table dbo.alembic_version - read the error above';" in text


def test_app_login_is_a_plain_literal_the_runner_can_set():
    # Invoke-RstTestSql.ps1 -Set rewrites DECLARE @Name type = '<literal>'; - an N'' prefix is not matched
    text = deploy_sql.render(ONE, DAY)
    assert re.search(r"(?m)^DECLARE @AppLogin sysname = '';$", text)


def test_app_user_block_quotes_names_and_grants_exactly_reader_and_writer():
    text = deploy_sql.render(ONE, DAY)
    block = _between(text, "-- App user", "-- Verify")
    assert "QUOTENAME(@login)" in block and "QUOTENAME(@user)" in block
    assert set(re.findall(r"ALTER ROLE (\w+) ADD MEMBER", block)) == {"db_datareader", "db_datawriter"}
    assert "db_owner" not in text and "db_ddladmin" not in text
    assert "skipped app user" in block and "REFUSED app user" in block


def test_app_user_ladder_runs_in_order_and_never_takes_another_logins_user():
    block = _between(deploy_sql.render(ONE, DAY), "-- App user", "-- Verify")
    rungs = [
        "'skipped app user - @AppLogin is empty'",  # nothing asked
        "IS_SRVROLEMEMBER(N'sysadmin'), 0) <> 1",  # the runner must be a sysadmin
        "does not exist on this server",  # the login must exist
        "IS_SRVROLEMEMBER(N'sysadmin', @login) = 1",  # a sysadmin login needs no user
        "@user = N'dbo'",  # the owner maps to dbo - nothing to grant
        "belongs to login ', @owner",  # someone else's user is left alone
        "N'ALTER USER '",  # an orphan is remapped
        "N'CREATE USER '",  # otherwise created
    ]
    at = [block.index(r) for r in rungs]
    assert at == sorted(at)
    assert "nothing to grant" in block and "Left alone." in block
    # every change is checked after it is made
    assert block.count("SELECT @user = name FROM sys.database_principals WHERE sid = SUSER_SID(@login);") == 2
    assert "NOT DONE app user" in block
    for role in ("db_datareader", "db_datawriter"):
        assert block.count(f"WHERE r.name = N'{role}' AND m.name = @user)") == 2
        assert f"NOT DONE {role} for " in block
    assert block.rstrip().endswith(
        "EXEC sp_set_session_context @key = N'azztec_app_user', @value = @state;\nGO"
    )


def test_verify_counts_every_step_and_needs_the_app_user_ok_or_skipped():
    text = deploy_sql.render(ONE, DAY)
    block = text[text.index("-- Verify") :]
    assert (
        block.count("SET @t += 1") == 1
        and block.count("SET @c += 1") == 1
        and block.count("SET @i += 1") == 1
    )
    assert "'/1  columns '" in block and "AZZTEC SCHEMA OK" in block and "AZZTEC SCHEMA INCOMPLETE" in block
    assert "CAST(SESSION_CONTEXT(N'azztec_app_user') AS varchar(10))" in block
    assert "AND @app IN ('ok', 'skipped')" in block
    assert "'  app user ', COALESCE(@app, 'not run')" in block


def test_no_use_ascii_only_and_no_colon_in_any_comment():
    text = deploy_sql.render(ONE, DAY)
    assert not re.search(r"(?im)^\s*USE\s", text)
    text.encode("ascii")
    comments = re.findall(r"(?m)--.*$", text) + re.findall(r"(?s)/\*.*?\*/", text)
    assert not [c for c in comments if ":" in c]


def test_no_message_starts_with_error_so_only_a_real_sql_error_trips_the_runner():
    text = deploy_sql.render(ONE, DAY)
    assert not re.findall(r"PRINT\s+(?:CONCAT\()?'ERROR", text)


def test_render_is_deterministic_and_validates_its_date():
    assert deploy_sql.render(ONE, DAY) == deploy_sql.render(ONE, DAY)
    with pytest.raises(ValueError):
        deploy_sql.render(ONE, "6/11/2026")


def test_counts_line():
    assert deploy_sql.counts_line(ONE) == "migrations=1 head=0001 tables=1 columns=1 indexes=1 steps=3"


# ---------------------------------------------------------------------------
# the real migrations and the committed script
# ---------------------------------------------------------------------------


def test_the_real_migrations_load_to_head_0002_with_47_steps():
    migs = deploy_sql.load_migrations(VERSIONS)
    assert [m.revision for m in migs] == ["0001", "0002"]
    c = deploy_sql.counts(migs)
    assert (c["tables"], c["columns"], c["indexes"], c["steps"]) == (14, 15, 18, 47)


def test_every_real_step_quotes_cleanly():
    for s in deploy_sql.all_steps(deploy_sql.load_migrations(VERSIONS)):
        assert deploy_sql.quote(s["sql"]).replace("''", "'") == s["sql"]


def test_the_committed_script_equals_a_fresh_render():
    assert COMMITTED.exists(), "run scripts/deploy_sql.py --write first"
    text = COMMITTED.read_text(encoding="ascii")
    m = re.search(r"generated on\s+(\d{4}-\d{2}-\d{2})", text)
    assert m, "the committed script has no 'generated on' date in its Version line"
    assert text == deploy_sql.render(deploy_sql.load_migrations(VERSIONS), m.group(1))
