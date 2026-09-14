"""
Azztec_SaaS_scripts_kt_uplift_ddl_v1_0_1.py  ->  scripts/kt_uplift_ddl.py
Version:  1.0.1
Author:   Adriaan
Spec:     Azztec_SaaS_S1j_KT_Uplift_Chunk_Spec_v1_0_0.md §3.2 (OD-42 scope, OD-43 numbering, OD-45 source,
          OD-46 types); Azztec_SaaS_KT_Schema_Delta_v1_0_0.md §4.1, §4.3, §5
Pair of:  backend/tests/test_kt_uplift.py 1.0.1

The KT parity migration is SCRIPTED FROM THE ORACLE'S CATALOG, NEVER TYPED (Ways of Working §3). This
script reads dbWorkmate_KT's sys.* views for the 12 in-scope tables and 15 in-scope columns, renders the
DDL twice (MSSQL as read, PG per the OD-46 map) and writes

    backend/alembic/versions/0001_kt_parity_additive.py    the migration - a static, reviewable file
    docs/kt_uplift_manifest_0001.json                       what the catalog said, for the diff gate

Run from backend/ so the venv is in play:
    uv run python ..\\scripts\\kt_uplift_ddl.py            dry run (default): prints, writes nothing
    uv run python ..\\scripts\\kt_uplift_ddl.py --write    writes both files; refuses to overwrite
    uv run python ..\\scripts\\kt_uplift_ddl.py --write --force

The oracle is READ_ONLY and stays that way: the source connection is Windows auth (OD-45), in-process as
the logged-in user, and this script issues nothing but SELECT against it. Everything below the I/O edge
is a pure function of plain dicts so the test file can drive it with a hand-built catalog.

Changelog:
  1.0.1  Two things the first dry run showed (2026-09-14). System-named constraints (SQL Server's
         PK__Tbl__<hash>) render UNNAMED so each database names its own - three KT PKs were never named,
         and a hash lowercased on PG is noise; the manifest keeps the source name. Identity columns of
         numeric type render as bigint on PG - GENERATED ... AS IDENTITY takes integer types only
         (OD-46 addendum; three legacy-style identities). MSSQL rendering unchanged except the names.
  1.0.0  Initial. S1j.
"""

from __future__ import annotations

import argparse
import json
import pprint
import re
import sys
import urllib.parse
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

__version__ = "1.0.1"

REVISION = "0001"
SLUG = "kt_parity_additive"
SCHEMA = "dbo"

# ---------------------------------------------------------------------------
# scope (OD-42) - dependency order matters: a referenced in-scope table comes first
# ---------------------------------------------------------------------------

TABLES: tuple[str, ...] = (
    "Action_Header",  # Bucket 3 - Action module
    "Action_Event",  # Bucket 3 - FK -> Action_Header
    "Account_WorkCode",  # Bucket 3 - FK -> Account, Work_Code (legacy)
    "External_Contractor",  # Bucket 3 - FK -> Supplier (legacy)
    "WO_N_Plan",  # Bucket 1 - OD-1 pin table; S3 inherits it (OD-43)
    "Diag_Log",  # Bucket 1 - D-8 persist target
    "Module_Settings",  # Bucket 1 - S5
    "Diag_NightShift",  # Bucket 1 - S5/S6
    "Diag_PM_Engine_Run",  # Bucket 1 - PM engine
    "Home_View",  # Bucket 3 - Home page views
    "Email_Automation",  # Bucket 3 - scheduled-email registry
    "PO_Email_Log",  # Bucket 3 - one of its duplicate indexes is skipped
)

COLUMNS: tuple[tuple[str, str], ...] = (
    ("WO_N_Header", "Source_Action_ID"),
    ("WO_C_header", "Source_Action_ID"),
    ("Supplier", "Email_2"),
    ("Supplier", "Email_3"),
    ("PO_Details", "Invoice_Ref"),
    ("WO_Attachment", "Creation_Date"),
    ("WO_Attachment", "User_id_Created_By"),
    ("WO_M_Attachment", "Creation_Date"),
    ("WO_M_Attachment", "User_id_Created_By"),
    ("PO_Attachment", "Creation_Date"),
    ("PO_Attachment", "User_id_Created_By"),
    ("Part_Attachment", "Creation_Date"),
    ("Part_Attachment", "User_id_Created_By"),
    ("Location_Attachment", "Creation_Date"),
    ("Location_Attachment", "User_id_Created_By"),
)

# Delta §4.3: IX_PO_Email_Log_PO_Id and IX_PO_Email_Log_PO are both (PO_Id, Sent_Date). One crosses.
SKIP_INDEXES: frozenset[str] = frozenset({"IX_PO_Email_Log_PO"})

# OD-46 type map, MSSQL -> PG. Anything not listed is an error, not a guess.
_PG_BASE: dict[str, str] = {
    "bigint": "bigint",
    "int": "integer",
    "smallint": "smallint",
    "tinyint": "smallint",
    "bit": "boolean",
    "numeric": "numeric",
    "decimal": "numeric",
    "float": "double precision",
    "datetime": "timestamp",
    "datetime2": "timestamp",
    "date": "date",
    "char": "char",
    "nchar": "char",
    "varchar": "varchar",
    "nvarchar": "varchar",
}

_CATALOG_COLUMNS = """
SELECT c.name, t.name AS type_name, c.max_length, c.precision, c.scale, c.is_nullable, c.is_identity,
       dc.definition AS default_def
  FROM sys.columns c
  JOIN sys.types t ON t.user_type_id = c.user_type_id
  LEFT JOIN sys.default_constraints dc
         ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
 WHERE c.object_id = OBJECT_ID(:tbl)
 ORDER BY c.column_id
"""

_CATALOG_INDEXES = """
SELECT i.name, i.index_id, i.is_primary_key, i.is_unique_constraint, i.is_unique,
       ic.key_ordinal, ic.is_included_column, col.name AS col_name
  FROM sys.indexes i
  JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
  JOIN sys.columns col ON col.object_id = ic.object_id AND col.column_id = ic.column_id
 WHERE i.object_id = OBJECT_ID(:tbl) AND i.index_id > 0
 ORDER BY i.index_id, ic.is_included_column, ic.key_ordinal, ic.index_column_id
"""

_CATALOG_FKS = """
SELECT fk.name, pc.name AS col_name, OBJECT_NAME(fk.referenced_object_id) AS ref_table,
       rc.name AS ref_col, fkc.constraint_column_id
  FROM sys.foreign_keys fk
  JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
  JOIN sys.columns pc ON pc.object_id = fkc.parent_object_id AND pc.column_id = fkc.parent_column_id
  JOIN sys.columns rc ON rc.object_id = fkc.referenced_object_id AND rc.column_id = fkc.referenced_column_id
 WHERE fk.parent_object_id = OBJECT_ID(:tbl)
 ORDER BY fk.name, fkc.constraint_column_id
"""

_CATALOG_CHECKS = """
SELECT name, definition FROM sys.check_constraints WHERE parent_object_id = OBJECT_ID(:tbl) ORDER BY name
"""


# ---------------------------------------------------------------------------
# pure: normalisation
# ---------------------------------------------------------------------------


def mssql_type(type_name: str, max_length: int, precision: int, scale: int) -> str:
    """Render a sys.columns row as the MSSQL type text. nvarchar/nchar max_length is bytes (2 per char)."""
    t = type_name.lower()
    if t in ("varchar", "char", "varbinary", "binary"):
        return f"{t}(max)" if max_length == -1 else f"{t}({max_length})"
    if t in ("nvarchar", "nchar"):
        return f"{t}(max)" if max_length == -1 else f"{t}({max_length // 2})"
    if t in ("numeric", "decimal"):
        return f"{t}({precision},{scale})"
    if t in ("datetime2", "time", "datetimeoffset"):
        return f"{t}({scale})"
    return t


_TYPE_RE = re.compile(r"^([a-z0-9]+)(?:\((.+)\))?$")
# SQL Server's own constraint names: PK__Action_H__A1196392C97A2CD4 - unnamed at KT, unnamed here
_SYSTEM_NAME = re.compile(r"^(PK|UQ|FK|CK|DF)__\w+__[0-9A-Fa-f]{16}$")


def is_system_name(name: str) -> bool:
    return bool(_SYSTEM_NAME.match(name))


def _cprefix(name: str, pg: bool) -> str:
    """'CONSTRAINT <name> ' or '' for a system-generated name (each database names its own)."""
    if is_system_name(name):
        return ""
    return f"CONSTRAINT {name.lower() if pg else name} "


def pg_type(mssql: str) -> str:
    """OD-46: the PG rendering of an MSSQL type text. Unknown base types raise - never guessed."""
    m = _TYPE_RE.match(mssql.strip().lower())
    if not m:
        raise ValueError(f"unparseable type: {mssql!r}")
    base, args = m.group(1), m.group(2)
    if base not in _PG_BASE:
        raise ValueError(f"no PG mapping for {mssql!r} (OD-46 map)")
    pg = _PG_BASE[base]
    if base in ("varchar", "nvarchar", "char", "nchar"):
        return "text" if args == "max" else f"{pg}({args})"
    if base in ("numeric", "decimal"):
        return f"numeric({args})"
    if base == "datetime2":
        return f"timestamp({args})"
    return pg


def normalise_default(definition: str | None) -> str | None:
    """sys.default_constraints.definition -> portable literal. ((0)) -> 0, ('N') -> 'N',
    (getdate()) -> CURRENT_TIMESTAMP. Returns None when there is no default."""
    if definition is None:
        return None
    d = definition.strip()
    while d.startswith("(") and d.endswith(")") and _balanced_wrap(d):
        d = d[1:-1].strip()
    d = re.sub(r"(?i)^getdate\(\)$", "CURRENT_TIMESTAMP", d)
    d = re.sub(r"(?i)^sysdatetime\(\)$", "CURRENT_TIMESTAMP", d)
    return d


def _balanced_wrap(s: str) -> bool:
    """True when the outermost parens wrap the whole string (so they can be stripped)."""
    depth = 0
    for i, ch in enumerate(s):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0 and i != len(s) - 1:
                return False
    return depth == 0


def normalise_check(definition: str) -> str:
    """sys.check_constraints.definition -> portable expression: brackets off, one outer wrap off.
    The expression itself is carried as KT spelled it (parity) - not rewritten into IN (...)."""
    d = definition.strip().replace("[", "").replace("]", "")
    if d.startswith("(") and d.endswith(")") and _balanced_wrap(d):
        d = d[1:-1].strip()
    return d


def pg_default(mssql_type_text: str, default: str | None) -> str | None:
    if default is None:
        return None
    if mssql_type_text.lower() == "bit":
        return {"1": "true", "0": "false"}.get(default, default)
    return default


# ---------------------------------------------------------------------------
# I/O edge: read the catalog
# ---------------------------------------------------------------------------


def default_source_url() -> str:
    parts = [
        "Driver={ODBC Driver 18 for SQL Server}",
        "Server=localhost",
        "Database=dbWorkmate_KT",
        "Trusted_Connection=yes",
        "Encrypt=yes",
        "TrustServerCertificate=yes",
    ]
    return "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(";".join(parts))


def _rows(conn: Connection, sql: str, **p: Any) -> list[dict[str, Any]]:
    return [dict(m) for m in conn.execute(text(sql), p).mappings()]


def read_table(conn: Connection, table: str) -> dict[str, Any]:
    full = f"{SCHEMA}.{table}"
    cols = []
    for r in _rows(conn, _CATALOG_COLUMNS, tbl=full):
        cols.append(
            {
                "name": r["name"],
                "type": mssql_type(r["type_name"], r["max_length"], r["precision"], r["scale"]),
                "nullable": bool(r["is_nullable"]),
                "identity": bool(r["is_identity"]),
                "default": normalise_default(r["default_def"]),
            }
        )
    if not cols:
        raise LookupError(f"{full}: not in the source catalog")

    pk: dict[str, Any] | None = None
    uniques: dict[str, dict[str, Any]] = {}
    indexes: dict[str, dict[str, Any]] = {}
    for r in _rows(conn, _CATALOG_INDEXES, tbl=full):
        if r["is_primary_key"]:
            pk = pk or {"name": r["name"], "cols": []}
            pk["cols"].append(r["col_name"])
        elif r["is_unique_constraint"]:
            uniques.setdefault(r["name"], {"name": r["name"], "cols": []})["cols"].append(r["col_name"])
        else:
            ix = indexes.setdefault(
                r["name"], {"name": r["name"], "unique": bool(r["is_unique"]), "cols": [], "include": []}
            )
            (ix["include"] if r["is_included_column"] else ix["cols"]).append(r["col_name"])

    fks: dict[str, dict[str, Any]] = {}
    for r in _rows(conn, _CATALOG_FKS, tbl=full):
        fk = fks.setdefault(
            r["name"], {"name": r["name"], "cols": [], "ref_table": r["ref_table"], "ref_cols": []}
        )
        fk["cols"].append(r["col_name"])
        fk["ref_cols"].append(r["ref_col"])

    checks = [
        {"name": r["name"], "definition": normalise_check(r["definition"])}
        for r in _rows(conn, _CATALOG_CHECKS, tbl=full)
    ]
    return {
        "name": table,
        "columns": cols,
        "pk": pk,
        "uniques": list(uniques.values()),
        "indexes": [ix for ix in indexes.values() if ix["name"] not in SKIP_INDEXES],
        "skipped_indexes": sorted(n for n in indexes if n in SKIP_INDEXES),
        "fks": list(fks.values()),
        "checks": checks,
    }


def read_column(conn: Connection, table: str, column: str) -> dict[str, Any]:
    full = f"{SCHEMA}.{table}"
    for r in _rows(conn, _CATALOG_COLUMNS, tbl=full):
        if r["name"].lower() == column.lower():
            return {
                "table": table,
                "name": r["name"],
                "type": mssql_type(r["type_name"], r["max_length"], r["precision"], r["scale"]),
                "nullable": bool(r["is_nullable"]),
                "default": normalise_default(r["default_def"]),
            }
    raise LookupError(f"{full}.{column}: not in the source catalog")


def read_catalog(conn: Connection) -> dict[str, Any]:
    cat = {
        "source": str(conn.execute(text("SELECT DB_NAME()")).scalar()),
        "tables": [read_table(conn, t) for t in TABLES],
        "columns": [read_column(conn, t, c) for t, c in COLUMNS],
    }
    validate(cat)
    return cat


# ---------------------------------------------------------------------------
# pure: validation and rendering
# ---------------------------------------------------------------------------


def validate(cat: dict[str, Any]) -> None:
    """Dependency order, PG name collisions, and every type mappable - before anything is rendered."""
    seen: list[str] = []
    for t in cat["tables"]:
        lowered = [c["name"].lower() for c in t["columns"]]
        if len(set(lowered)) != len(lowered):
            raise ValueError(f"{t['name']}: column names collide once lowercased (PG)")
        for fk in t["fks"]:
            ref = fk["ref_table"]
            if ref in TABLES and ref not in seen:
                raise ValueError(f"{t['name']}: FK {fk['name']} references {ref} which is later in TABLES")
        for c in t["columns"]:
            pg_type(c["type"])
        seen.append(t["name"])
    for c in cat["columns"]:
        pg_type(c["type"])


def _col_mssql(c: dict[str, Any]) -> str:
    s = f"{c['name']} {c['type']}"
    if c["identity"]:
        s += " IDENTITY(1,1)"
    s += " NOT NULL" if not c["nullable"] else " NULL"
    if c["default"] is not None:
        s += f" DEFAULT {c['default']}"
    return s


def _col_pg(c: dict[str, Any]) -> str:
    typ = pg_type(c["type"])
    if c["identity"] and typ.startswith("numeric"):
        typ = "bigint"  # PG identity takes integer types only; numeric(18,0) identities are legacy-style ids
    s = f"{c['name'].lower()} {typ}"
    if c["identity"]:
        s += " GENERATED BY DEFAULT AS IDENTITY"
    s += " NOT NULL" if not c["nullable"] else " NULL"
    d = pg_default(c["type"], c["default"])
    if d is not None:
        s += f" DEFAULT {d}"
    return s


def _cols(names: list[str], pg: bool) -> str:
    return ", ".join(n.lower() if pg else n for n in names)


def _create_table(t: dict[str, Any], pg: bool) -> str:
    name = t["name"].lower() if pg else t["name"]
    lines = [(_col_pg if pg else _col_mssql)(c) for c in t["columns"]]
    if t["pk"]:
        lines.append(f"{_cprefix(t['pk']['name'], pg)}PRIMARY KEY ({_cols(t['pk']['cols'], pg)})")
    for u in t["uniques"]:
        lines.append(f"{_cprefix(u['name'], pg)}UNIQUE ({_cols(u['cols'], pg)})")
    for fk in t["fks"]:
        ref = fk["ref_table"].lower() if pg else fk["ref_table"]
        lines.append(
            f"{_cprefix(fk['name'], pg)}FOREIGN KEY ({_cols(fk['cols'], pg)}) "
            f"REFERENCES {SCHEMA}.{ref} ({_cols(fk['ref_cols'], pg)})"
        )
    for ck in t["checks"]:
        # the expression is carried as spelled; unquoted identifiers fold to lowercase on PG (OD-46)
        lines.append(f"{_cprefix(ck['name'], pg)}CHECK ({ck['definition']})")
    body = ",\n    ".join(lines)
    return f"CREATE TABLE {SCHEMA}.{name} (\n    {body}\n)"


def _create_index(t: dict[str, Any], ix: dict[str, Any], pg: bool) -> str:
    tname = t["name"].lower() if pg else t["name"]
    iname = ix["name"].lower() if pg else ix["name"]
    uniq = "UNIQUE " if ix["unique"] else ""
    s = f"CREATE {uniq}INDEX {iname} ON {SCHEMA}.{tname} ({_cols(ix['cols'], pg)})"
    if ix["include"]:
        s += f" INCLUDE ({_cols(ix['include'], pg)})"
    return s


def _add_column(c: dict[str, Any], pg: bool) -> str:
    tname = c["table"].lower() if pg else c["table"]
    col = {**c, "identity": False}
    return f"ALTER TABLE {SCHEMA}.{tname} ADD {(_col_pg if pg else _col_mssql)(col)}"


def render_steps(cat: dict[str, Any], pg: bool) -> list[dict[str, str]]:
    """Ordered, guarded steps: tables (with their keys/checks inline), then columns, then indexes.
    Each step names what its guard looks for, so the migration never re-creates an existing object."""
    steps: list[dict[str, str]] = []
    for t in cat["tables"]:
        steps.append({"kind": "table", "table": t["name"], "name": t["name"], "sql": _create_table(t, pg)})
    for c in cat["columns"]:
        steps.append({"kind": "column", "table": c["table"], "name": c["name"], "sql": _add_column(c, pg)})
    for t in cat["tables"]:
        for ix in t["indexes"]:
            steps.append(
                {"kind": "index", "table": t["name"], "name": ix["name"], "sql": _create_index(t, ix, pg)}
            )
    return steps


def render_mssql(cat: dict[str, Any]) -> list[str]:
    return [s["sql"] for s in render_steps(cat, pg=False)]


def render_pg(cat: dict[str, Any]) -> list[str]:
    return [s["sql"] for s in render_steps(cat, pg=True)]


def counts(cat: dict[str, Any]) -> dict[str, int]:
    ts = cat["tables"]
    return {
        "tables": len(ts),
        "columns": len(cat["columns"]),
        "pks": sum(1 for t in ts if t["pk"]),
        "uqs": sum(len(t["uniques"]) for t in ts),
        "fks": sum(len(t["fks"]) for t in ts),
        "checks": sum(len(t["checks"]) for t in ts),
        "indexes": sum(len(t["indexes"]) for t in ts),
        "skipped": sum(len(t["skipped_indexes"]) for t in ts),
    }


def counts_line(cat: dict[str, Any]) -> str:
    c = counts(cat)
    return (
        f"tables={c['tables']} columns={c['columns']} pks={c['pks']} uqs={c['uqs']} fks={c['fks']} "
        f"checks={c['checks']} indexes={c['indexes']} (skipped {c['skipped']})"
    )


_MIGRATION_TEMPLATE = '''"""
{rev}_{slug}.py  ->  backend/alembic/versions/{rev}_{slug}.py
GENERATED by scripts/kt_uplift_ddl.py {gen} from {source}'s catalog - DO NOT HAND-EDIT.
Regenerate with `uv run python ..\\\\scripts\\\\kt_uplift_ddl.py --write --force` and re-read the diff.
Spec:     Azztec_SaaS_S1j_KT_Uplift_Chunk_Spec_v1_0_0.md (OD-42..OD-46)
Manifest: docs/kt_uplift_manifest_{rev}.json  ({counts})

Additive KT parity: the tables, columns, keys, checks and indexes the Ignition edition added on top of
the .NET-era schema (KT Schema Delta §4.1, §4.3, §5). Every step is guarded by the inspector, so it is
idempotent on a database that already carries some of it; nothing here writes data; nothing touches a
view. Two renderings of one catalog, picked by dialect (OD-46). In offline mode (`alembic upgrade
head --sql`) every step is emitted unguarded - that render is the DRY_RUN, read it before the real run.
"""

from __future__ import annotations

from alembic import context, op
from sqlalchemy import inspect, text

revision = {rev!r}
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = {schema!r}

MSSQL = {mssql}

PG = {pg}


def _steps():
    return PG if op.get_bind().dialect.name == "postgresql" else MSSQL


def _exists(step) -> bool:
    bind = op.get_bind()
    pg = bind.dialect.name == "postgresql"
    insp = inspect(bind)
    table = step["table"].lower() if pg else step["table"]
    name = step["name"].lower()
    if step["kind"] == "table":
        return bool(insp.has_table(table, schema=SCHEMA))
    if not insp.has_table(table, schema=SCHEMA):
        return False
    if step["kind"] == "column":
        return name in {{c["name"].lower() for c in insp.get_columns(table, schema=SCHEMA)}}
    if step["kind"] == "index":
        return name in {{(i["name"] or "").lower() for i in insp.get_indexes(table, schema=SCHEMA)}}
    raise ValueError(step["kind"])


def _drop(step) -> str:
    pg = op.get_bind().dialect.name == "postgresql"
    t = step["table"].lower() if pg else step["table"]
    n = step["name"].lower() if pg else step["name"]
    if step["kind"] == "table":
        return f"DROP TABLE {{SCHEMA}}.{{t}}"
    if step["kind"] == "column":
        return f"ALTER TABLE {{SCHEMA}}.{{t}} DROP COLUMN {{n}}"
    return f"DROP INDEX {{SCHEMA}}.{{n}}" if pg else f"DROP INDEX {{n}} ON {{SCHEMA}}.{{t}}"


def upgrade() -> None:
    offline = context.is_offline_mode()
    for step in _steps():
        if offline or not _exists(step):
            op.execute(text(step["sql"]))


def downgrade() -> None:
    offline = context.is_offline_mode()
    for step in reversed(_steps()):
        if offline or _exists(step):
            op.execute(text(_drop(step)))
'''


def render_migration(cat: dict[str, Any], rev: str = REVISION, slug: str = SLUG) -> str:
    fmt = {"width": 110, "sort_dicts": False}
    return _MIGRATION_TEMPLATE.format(
        rev=rev,
        slug=slug,
        gen=__version__,
        source=cat["source"],
        counts=counts_line(cat),
        schema=SCHEMA,
        mssql=pprint.pformat(render_steps(cat, pg=False), **fmt),
        pg=pprint.pformat(render_steps(cat, pg=True), **fmt),
    )


def render_manifest(cat: dict[str, Any], generated_on: str | None = None) -> dict[str, Any]:
    return {
        "generator": f"scripts/kt_uplift_ddl.py {__version__}",
        "revision": REVISION,
        "source": cat["source"],
        "generated_on": generated_on or date.today().isoformat(),
        "counts": counts(cat),
        "tables": cat["tables"],
        "columns": cat["columns"],
        "skip_indexes": sorted(SKIP_INDEXES),
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def migration_path(root: Path) -> Path:
    return root / "backend" / "alembic" / "versions" / f"{REVISION}_{SLUG}.py"


def manifest_path(root: Path) -> Path:
    return root / "docs" / f"kt_uplift_manifest_{REVISION}.json"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render the KT parity migration from dbWorkmate_KT's catalog.")
    ap.add_argument(
        "--source-url", default=default_source_url(), help="SQLAlchemy URL of the KT oracle (read-only)"
    )
    ap.add_argument(
        "--write", action="store_true", help="write the migration and manifest (default: dry run)"
    )
    ap.add_argument("--force", action="store_true", help="overwrite existing outputs (dev only)")
    a = ap.parse_args(argv)

    engine = create_engine(a.source_url)
    with engine.connect() as conn:
        cat = read_catalog(conn)
    engine.dispose()

    print(f"source={cat['source']} generator={__version__} {counts_line(cat)}")
    if not a.write:
        print("-- DRY RUN: nothing written. MSSQL rendering:")
        for s in render_mssql(cat):
            print(s + ";")
        print("-- PG rendering:")
        for s in render_pg(cat):
            print(s + ";")
        return 0

    root = repo_root()
    mp, jp = migration_path(root), manifest_path(root)
    for p in (mp, jp):
        if p.exists() and not a.force:
            print(f"REFUSED: {p} exists (use --force)")
            return 2
    if a.force:
        print("--force: overwriting")
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(render_migration(cat), encoding="utf-8", newline="\n")
    jp.write_text(json.dumps(render_manifest(cat), indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {mp.relative_to(root)}")
    print(f"wrote {jp.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
