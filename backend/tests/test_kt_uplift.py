"""
Azztec_SaaS_test_kt_uplift_v1_0_3.py  ->  backend/tests/test_kt_uplift.py
Version:  1.0.3
Author:   Adriaan
Spec:     Azztec_SaaS_S1j_KT_Uplift_Chunk_Spec_v1_0_0.md §5
Pair of:  scripts/kt_uplift_ddl.py 1.0.1 (+ the generated 0001_kt_parity_additive.py / kt_uplift_manifest_0001.json)

Three halves:
  §5.1  no DB - the generator's pure functions on a hand-built catalog: type map, normalisation,
        both renderings, the skip list, dependency order, and that the rendered migration parses and
        guards every step.
  §5.2  dbWorkmate_KT (the read-only oracle, Windows auth - OD-45): the committed migration and
        manifest are byte-equal to a fresh rendering of the catalog. SKIPS by name when the oracle
        is unreachable - a skip is visible in the summary; a silent pass would not be.
  §5.3  dbWorkmate (RST), rolled-back connection, after `alembic upgrade head`: the twelve tables and
        fifteen columns exist, every crossed table is empty (Marker Law), alembic_version is 0001, and
        WO_RANGE_PINNED - which had never executed on data before S1j - runs and agrees with NOPIN.
        SKIPS when RST is unreachable; FAILS (red, on purpose) when RST is reachable and 0001 has not
        been applied - that is the state the smoke exists to change.

Fifteen tests, none parametrised, so the file's own `def test_` count is the number the run must show.

Changelog:
  1.0.3  DP3a (2026-11-07). WO_N_Plan joins WRITTEN_BY_DESIGN, as 1.0.2 said it would when the first
         move shipped: a move pins an engine-owned PM (OD-114), so the pin table may hold rows wherever a
         planner has moved one. It still has to exist. Fifteen tests still; nothing else changed.
  1.0.2  D1a (2026-09-19). Diag_Log is the table the app WRITES BY DESIGN from D1a on, so the Marker Law
         case excludes it by name (WRITTEN_BY_DESIGN) and asserts the others are still empty. The first
         four rows on RST were written by the S1k dev server, which watchfiles reloaded onto the D1a
         code mid-drop - the feature working, not a test writing. WO_N_Plan joins the set when S2b
         ships the first move; Diag_NightShift when the night shift port does. Fifteen tests still.
  1.0.1  Pair of generator 1.0.1: system-named constraints render unnamed, numeric identity is bigint
         on PG - one test each. SIM300 on the SKIP_INDEXES assertion (ruff reads the name as a constant).
  1.0.0  Initial. S1j.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("WORKMATE_ENV", "test")

from app.core import db  # noqa: E402 - after env is set

# Tables the product fills on purpose. Add one here in the slice that starts writing it, never before.
WRITTEN_BY_DESIGN = {"Diag_Log", "WO_N_Plan"}  # D1a, OD-55; DP3, OD-114
from app.planner import repo  # noqa: E402
from app.planner import sql as psql  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
GEN_PATH = ROOT / "scripts" / "kt_uplift_ddl.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("kt_uplift_ddl", GEN_PATH)
    assert spec and spec.loader, GEN_PATH
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gen = _load_generator()

FROM_D, TO_D = date(2026, 9, 14), date(2026, 9, 20)  # the standing window (Raw Log 2026-09-11 §5)


# ---------------------------------------------------------------------------
# §5.1 - hand-built catalog, no database
# ---------------------------------------------------------------------------


def _col(name: str, typ: str, *, nullable=True, identity=False, default=None) -> dict[str, Any]:
    return {"name": name, "type": typ, "nullable": nullable, "identity": identity, "default": default}


def _catalog() -> dict[str, Any]:
    """Two tables that between them carry every shape the twelve real ones do: an identity PK, a
    char(1) default, a getdate() default, a bit default, nvarchar(max), datetime2(3), a unique
    constraint, an index with INCLUDE, a skipped duplicate index, an FK to the other in-scope table
    and a bracketed CHECK - plus one added column on a legacy table."""
    return {
        "source": "dbWorkmate_KT",
        "tables": [
            {
                "name": "Action_Header",
                "columns": [
                    _col("Action_ID", "bigint", nullable=False, identity=True),
                    _col("Status", "char(1)", nullable=False, default=gen.normalise_default("('R')")),
                    _col("Crt_Date", "datetime", default=gen.normalise_default("(getdate())")),
                    _col("ShowTips", "bit", nullable=False, default=gen.normalise_default("((1))")),
                    _col("Detail", "nvarchar(max)"),
                    _col("Logged_At", "datetime2(3)", nullable=False),
                ],
                "pk": {"name": "PK_Action_Header", "cols": ["Action_ID"]},
                "uniques": [{"name": "UQ_Action_Status", "cols": ["Status"]}],
                "indexes": [{"name": "IX_A", "unique": False, "cols": ["Crt_Date"], "include": ["Status"]}],
                "skipped_indexes": ["IX_PO_Email_Log_PO"],
                "fks": [],
                "checks": [
                    {
                        "name": "CK_S",
                        "definition": gen.normalise_check("([Status]='G' OR [Status]='R')"),
                    }
                ],
            },
            {
                "name": "Action_Event",
                "columns": [
                    _col("Event_ID", "bigint", nullable=False, identity=True),
                    _col("Action_ID", "bigint", nullable=False),
                ],
                "pk": {"name": "PK_Action_Event", "cols": ["Event_ID"]},
                "uniques": [],
                "indexes": [],
                "skipped_indexes": [],
                "fks": [
                    {
                        "name": "FK_AE_AH",
                        "cols": ["Action_ID"],
                        "ref_table": "Action_Header",
                        "ref_cols": ["Action_ID"],
                    }
                ],
                "checks": [],
            },
        ],
        "columns": [
            {
                "table": "Supplier",
                "name": "Email_2",
                "type": "varchar(255)",
                "nullable": True,
                "default": None,
            },
        ],
    }


def test_scope_constants_are_the_delta_scope():
    """OD-42: 12 tables in dependency order, 15 columns on 9 tables, one skipped index."""
    assert len(gen.TABLES) == 12 and len(set(gen.TABLES)) == 12
    assert len(gen.COLUMNS) == 15 and len({t for t, _ in gen.COLUMNS}) == 9
    assert gen.TABLES.index("Action_Header") < gen.TABLES.index("Action_Event")
    assert "IX_PO_Email_Log_PO" in gen.SKIP_INDEXES and len(gen.SKIP_INDEXES) == 1
    assert gen.REVISION == "0001" and gen.SLUG == "kt_parity_additive"


def test_mssql_type_text_from_catalog_numbers():
    assert gen.mssql_type("nvarchar", 200, 0, 0) == "nvarchar(100)"  # bytes -> chars
    assert gen.mssql_type("nvarchar", -1, 0, 0) == "nvarchar(max)"
    assert gen.mssql_type("varchar", 255, 0, 0) == "varchar(255)"
    assert gen.mssql_type("numeric", 9, 18, 0) == "numeric(18,0)"
    assert gen.mssql_type("datetime2", 7, 23, 3) == "datetime2(3)"
    assert gen.mssql_type("bigint", 8, 19, 0) == "bigint"
    assert gen.mssql_type("char", 1, 0, 0) == "char(1)"


def test_pg_type_map_is_od46_and_refuses_the_unknown():
    cases = {
        "bigint": "bigint",
        "int": "integer",
        "numeric(18,0)": "numeric(18,0)",
        "datetime": "timestamp",
        "datetime2(3)": "timestamp(3)",
        "nvarchar(100)": "varchar(100)",
        "varchar(255)": "varchar(255)",
        "nvarchar(max)": "text",
        "varchar(max)": "text",
        "char(1)": "char(1)",
        "bit": "boolean",
    }
    for mssql, pg in cases.items():
        assert gen.pg_type(mssql) == pg, mssql
    with pytest.raises(ValueError):
        gen.pg_type("hierarchyid")
    with pytest.raises(ValueError):
        gen.pg_type("sql_variant")


def test_default_and_check_normalisation():
    assert gen.normalise_default("((0))") == "0"
    assert gen.normalise_default("((1))") == "1"
    assert gen.normalise_default("('N')") == "'N'"
    assert gen.normalise_default("(getdate())") == "CURRENT_TIMESTAMP"
    assert gen.normalise_default("(GETDATE())") == "CURRENT_TIMESTAMP"
    assert gen.normalise_default(None) is None
    assert (
        gen.normalise_check("([Progress_ID]>=(1) AND [Progress_ID]<=(6))")
        == "Progress_ID>=(1) AND Progress_ID<=(6)"
    )
    assert gen.pg_default("bit", "1") == "true" and gen.pg_default("bit", "0") == "false"
    assert gen.pg_default("char(1)", "'N'") == "'N'"


def test_mssql_rendering_is_as_read_and_getdate_free():
    stmts = gen.render_mssql(_catalog())
    text = "\n".join(stmts)
    assert "IDENTITY(1,1)" in text and "GENERATED BY DEFAULT" not in text
    assert "DEFAULT CURRENT_TIMESTAMP" in text and "getdate" not in text.lower()
    assert "[" not in text and "]" not in text
    assert "DEFAULT 'R'" in text and "bit NOT NULL DEFAULT 1" in text
    assert "CONSTRAINT PK_Action_Header PRIMARY KEY (Action_ID)" in text
    assert "CONSTRAINT UQ_Action_Status UNIQUE (Status)" in text
    assert "REFERENCES dbo.Action_Header (Action_ID)" in text
    assert "CHECK (Status='G' OR Status='R')" in text
    assert "ALTER TABLE dbo.Supplier ADD Email_2 varchar(255) NULL" in stmts
    assert "CREATE INDEX IX_A ON dbo.Action_Header (Crt_Date) INCLUDE (Status)" in stmts


def test_pg_rendering_lowercases_and_maps():
    stmts = gen.render_pg(_catalog())
    text = "\n".join(stmts)
    assert "GENERATED BY DEFAULT AS IDENTITY" in text and "IDENTITY(1,1)" not in text
    assert "showtips boolean NOT NULL DEFAULT true" in text
    assert "detail text NULL" in text and "logged_at timestamp(3) NOT NULL" in text
    assert "CREATE TABLE dbo.action_header" in text and "dbo.Action_Header" not in text
    assert "REFERENCES dbo.action_header (action_id)" in text
    assert "CHECK (Status='G' OR Status='R')" in text  # expression carried as spelled; identifiers fold on PG
    assert "ALTER TABLE dbo.supplier ADD email_2 varchar(255) NULL" in stmts
    assert "CREATE INDEX ix_a ON dbo.action_header (crt_date) INCLUDE (status)" in stmts


def test_skipped_index_is_in_neither_rendering_and_counted():
    cat = _catalog()
    assert "IX_PO_Email_Log_PO" not in "\n".join(gen.render_mssql(cat))
    assert "ix_po_email_log_po" not in "\n".join(gen.render_pg(cat))
    c = gen.counts(cat)
    assert c == {
        "tables": 2,
        "columns": 1,
        "pks": 2,
        "uqs": 1,
        "fks": 1,
        "checks": 1,
        "indexes": 1,
        "skipped": 1,
    }
    assert gen.counts_line(cat) == "tables=2 columns=1 pks=2 uqs=1 fks=1 checks=1 indexes=1 (skipped 1)"


def test_system_named_constraints_render_unnamed():
    """SQL Server names an unnamed PK PK__<8 of table>__<16 hex>; KT never named three of the twelve.
    Those render as bare PRIMARY KEY so each database names its own; real names are carried."""
    assert gen.is_system_name("PK__Action_H__A1196392C97A2CD4")
    assert gen.is_system_name("UQ__Email_Au__7BC6D8B2EDD27755")
    assert not gen.is_system_name("PK_Action_Header") and not gen.is_system_name("CK_Action_Progress")
    cat = _catalog()
    cat["tables"][0]["pk"]["name"] = "PK__Action_H__A1196392C97A2CD4"
    ms, pg = "\n".join(gen.render_mssql(cat)), "\n".join(gen.render_pg(cat))
    assert "    PRIMARY KEY (Action_ID)" in ms and "PK__Action_H" not in ms
    assert "    PRIMARY KEY (action_id)" in pg and "pk__action_h" not in pg
    assert "CONSTRAINT PK_Action_Event PRIMARY KEY (Event_ID)" in ms  # a real name still carries


def test_numeric_identity_is_bigint_on_pg_only():
    """PG identity takes integer types only; KT's three legacy-style numeric(18,0) identities become
    bigint there and stay numeric(18,0) IDENTITY(1,1) on MSSQL. A numeric NON-identity stays numeric."""
    cat = _catalog()
    cat["tables"][1]["columns"] = [
        _col("Log_Id", "numeric(18,0)", nullable=False, identity=True),
        _col("PO_Id", "numeric(18,0)", nullable=False),
    ]
    cat["tables"][1]["pk"] = {"name": "PK_X", "cols": ["Log_Id"]}
    cat["tables"][1]["fks"] = []
    ms, pg = "\n".join(gen.render_mssql(cat)), "\n".join(gen.render_pg(cat))
    assert "Log_Id numeric(18,0) IDENTITY(1,1) NOT NULL" in ms
    assert "log_id bigint GENERATED BY DEFAULT AS IDENTITY NOT NULL" in pg
    assert "po_id numeric(18,0) NOT NULL" in pg


def test_validate_refuses_bad_order_and_pg_collisions():
    cat = _catalog()
    cat["tables"].reverse()  # Action_Event now precedes the table its FK references
    with pytest.raises(ValueError):
        gen.validate(cat)
    cat = _catalog()
    cat["tables"][0]["columns"].append(_col("STATUS", "char(1)"))  # collides with Status once lowercased
    with pytest.raises(ValueError):
        gen.validate(cat)


def test_rendered_migration_parses_and_guards_every_step():
    cat = _catalog()
    src = gen.render_migration(cat)
    tree = ast.parse(src)
    names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert {"upgrade", "downgrade", "_exists", "_drop", "_steps"} <= names
    ns: dict[str, Any] = {}
    assigns = ast.Module(body=[n for n in tree.body if isinstance(n, ast.Assign)], type_ignores=[])
    exec(compile(assigns, "0001", "exec"), ns)  # literals only: revision, SCHEMA, MSSQL, PG
    assert ns["revision"] == "0001" and ns["down_revision"] is None and ns["SCHEMA"] == "dbo"
    for steps in (ns["MSSQL"], ns["PG"]):
        assert len(steps) == 4  # 2 tables, 1 column, 1 index
        assert all(set(s) == {"kind", "table", "name", "sql"} for s in steps)
        assert [s["kind"] for s in steps] == ["table", "table", "column", "index"]
    assert "is_offline_mode()" in src and "DO NOT HAND-EDIT" in src


# ---------------------------------------------------------------------------
# §5.2 - the committed files match a fresh read of the oracle (skips when it is unreachable)
# ---------------------------------------------------------------------------


def _strip_generated_on(m: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in m.items() if k != "generated_on"}


def test_committed_migration_matches_the_kt_catalog():
    """Assumes dbWorkmate_KT on localhost, reachable over Windows auth (OD-45). The oracle is read
    only; this issues SELECTs against sys.* and nothing else. A drift here means someone hand-edited
    the migration or KT's catalog moved - either way, regenerate with --write --force and re-read."""
    from sqlalchemy import create_engine  # noqa: PLC0415 - the one test that opens a second engine

    engine = create_engine(gen.default_source_url())  # no connection until .connect()
    try:
        with engine.connect() as conn:
            cat = gen.read_catalog(conn)
    except Exception as e:  # noqa: BLE001 - reported as a skip reason
        pytest.skip(f"dbWorkmate_KT unreachable: {db.db_error(e)}")
    finally:
        engine.dispose()
    assert cat["source"] == "dbWorkmate_KT"
    mp, jp = gen.migration_path(ROOT), gen.manifest_path(ROOT)
    assert mp.exists() and jp.exists(), "run the generator with --write first"
    assert mp.read_text(encoding="utf-8") == gen.render_migration(cat)
    committed = json.loads(jp.read_text(encoding="utf-8"))
    assert _strip_generated_on(committed) == _strip_generated_on(gen.render_manifest(cat, generated_on="x"))
    assert committed["counts"] == gen.counts(cat)


# ---------------------------------------------------------------------------
# §5.3 - RST after `alembic upgrade head` (rolled-back connection; skips when unreachable)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def conn():
    try:
        engine = db.get_engine()
        c = engine.connect()
    except Exception as e:  # noqa: BLE001 - reported as a skip reason
        pytest.skip(f"database unreachable: {db.db_error(e)}")
    trans = c.begin()
    repo.clear_caches()
    try:
        yield c
    finally:
        trans.rollback()
        c.close()
        repo.clear_caches()


def test_rst_carries_the_twelve_tables_and_fifteen_columns(conn):
    """Assumes dbWorkmate (RST) after 0001. Red until the migration has run - by design."""
    from sqlalchemy import inspect  # noqa: PLC0415

    assert repo.pin_table_exists(conn) is True, "WO_N_Plan missing: alembic upgrade head has not run"
    for t in gen.TABLES:
        assert db.table_exists(conn, t), t
    insp = inspect(conn)
    for t, c in gen.COLUMNS:
        have = {x["name"].lower() for x in insp.get_columns(t, schema="dbo")}
        assert c.lower() in have, f"{t}.{c}"
    assert db.table_exists(conn, "alembic_version")
    assert db.scalar(conn, "SELECT version_num FROM dbo.alembic_version") == "0001"


def test_marker_law_every_crossed_table_is_empty(conn):
    """Nothing wrote data - except the tables the product writes by design (WRITTEN_BY_DESIGN), which
    only prove they exist: Diag_Log since D1a, WO_N_Plan since DP3's first move."""
    for t in gen.TABLES:
        n = db.scalar(conn, f"SELECT COUNT(*) AS n FROM dbo.{t}")
        if t in WRITTEN_BY_DESIGN:
            assert n is not None, t
            continue
        assert n == 0, t


def test_pinned_variant_executes_and_agrees_with_nopin(conn):
    """WO_RANGE_PINNED had never run on data before S1j (item 37 named its three correlated selects).
    With WO_N_Plan present and empty it must return the same rows as NOPIN with every pin column off."""
    params = {"from_d": repo._bound(FROM_D), "to_d": repo._exclusive_end(TO_D)}
    pinned = db.rows(conn, psql.WO_RANGE_PINNED, **params)
    nopin = db.rows(conn, psql.WO_RANGE_NOPIN, **params)
    assert len(pinned) == len(nopin) > 0
    assert [r["WO_ID"] for r in pinned] == [r["WO_ID"] for r in nopin]
    assert all(db.i_(r["Pinned"]) == 0 and r["Prev_Start"] is None and r["Pinned_On"] is None for r in pinned)
