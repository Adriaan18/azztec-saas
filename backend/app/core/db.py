"""
Azztec_SaaS_app_core_db_v1_0_0.py  ->  backend/app/core/db.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_Data_Layer_and_RST_DB_v1_0_0.md §3-§5, Architecture D-2/D-3/D-12

The only module that knows which database it is talking to.
  - build_url()             mssql+pyodbc (odbc_connect, ODBC 18, TrustServerCertificate) or postgresql+psycopg
  - get_engine()            cached per tenant; pyodbc.pooling off, fast_executemany, pool_pre_ping
  - get_conn()              FastAPI dependency (read); writes use `with get_engine().begin() as conn:` in services
  - rows()/scalar()/execute()   text() + named binds; values come back stripped, Decimal -> int/float
  - insert_returning_id()   SCOPE_IDENTITY vs RETURNING lives HERE and nowhere else
  - table_exists()          the pinTableExists() twin
  - config_value()          dbo.System_Configuration switch reader
  - db_error()              walks e.orig for the driver message (the Ignition _err() twin)
  - s_/i_/f_                the Jython _s/_i/_f coercion twins

Changelog:
  1.0.0  Initial.
"""

from __future__ import annotations

import urllib.parse
from collections.abc import Iterator
from decimal import Decimal
from functools import lru_cache
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection, Engine

from app.core.config import Settings, get_settings

__version__ = "1.0.0"


# ---------------------------------------------------------------------------
# engine
# ---------------------------------------------------------------------------


def build_url(s: Settings) -> str:
    if s.db_kind == "postgresql":
        if not s.db_url:
            raise ValueError("WORKMATE_DB_URL is required when WORKMATE_DB_KIND=postgresql")
        return s.db_url
    if s.db_url:
        return s.db_url
    parts = [
        f"Driver={{{s.db_driver}}}",
        f"Server={s.db_server}",
        f"Database={s.db_name}",
        f"UID={s.db_user}",
        f"PWD={s.db_password}",
        "Encrypt=yes",
        f"TrustServerCertificate={'yes' if s.db_trust_cert else 'no'}",
    ]
    return "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(";".join(parts))


@lru_cache
def get_engine(tenant: str = "default") -> Engine:
    """One engine per tenant (D-12). Today every tenant maps to the settings URL."""
    s = get_settings()
    url = build_url(s)
    kwargs: dict[str, Any] = {"pool_pre_ping": True, "echo": s.sqlalchemy_echo}
    if url.startswith("mssql+pyodbc"):
        import pyodbc  # noqa: PLC0415 - only when the dialect is in use

        pyodbc.pooling = False  # SQLAlchemy pools; double pooling is the documented landmine
        kwargs["fast_executemany"] = True
    return create_engine(url, **kwargs)


def get_conn() -> Iterator[Connection]:
    """FastAPI dependency for reads. Writes belong in services: `with get_engine().begin() as conn:`."""
    with get_engine().connect() as conn:
        yield conn


# ---------------------------------------------------------------------------
# coercion twins (_s / _i / _f from workmate.planner)
# ---------------------------------------------------------------------------


def s_(v: Any) -> str:
    return "" if v is None else str(v).strip()


def i_(v: Any, d: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return d


def f_(v: Any, d: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _clean(v: Any) -> Any:
    if isinstance(v, str):
        return v.strip()  # legacy char(n) padding
    if isinstance(v, Decimal):
        return (
            int(v) if v == v.to_integral_value() else float(v)
        )  # Pydantic would emit Decimal as a JSON string
    return v


# ---------------------------------------------------------------------------
# statements
# ---------------------------------------------------------------------------


def rows(conn: Connection, sql: str, **params: Any) -> list[dict[str, Any]]:
    res = conn.execute(text(sql), params)
    return [{k: _clean(v) for k, v in m.items()} for m in res.mappings()]


def scalar(conn: Connection, sql: str, **params: Any) -> Any:
    return _clean(conn.execute(text(sql), params).scalar())


def execute(conn: Connection, sql: str, **params: Any) -> int:
    return conn.execute(text(sql), params).rowcount


def insert_returning_id(conn: Connection, sql: str, id_col: str = "id", **params: Any) -> int:
    """Insert and return the new identity. The dialect split lives here only (PG-CONVERT resolved at runtime)."""
    if conn.dialect.name == "postgresql":
        stmt = sql.rstrip().rstrip(";") + f" RETURNING {id_col}"
        return int(conn.execute(text(stmt), params).scalar())
    conn.execute(text(sql), params)
    new_id = conn.execute(text("SELECT CAST(SCOPE_IDENTITY() AS bigint) AS new_id")).scalar()
    return int(new_id or 0)


def table_exists(conn: Connection, name: str, schema: str = "dbo") -> bool:
    nm = name.lower() if conn.dialect.name == "postgresql" else name
    return bool(inspect(conn).has_table(nm, schema=schema))


def config_value(conn: Connection, key: str, default: str = "") -> str:
    v = scalar(
        conn,
        "SELECT RTRIM(System_ConfigVal) AS v FROM dbo.System_Configuration WHERE RTRIM(System_ConfigCol) = :key",
        key=key,
    )
    return default if v is None or s_(v) == "" else s_(v)


def db_error(e: BaseException) -> str:
    """Driver-level message: walk .orig / __cause__ up to 4 deep (the Ignition _err() habit)."""
    msg = str(e)
    cur: Any = getattr(e, "orig", None)
    depth = 0
    while cur is not None and depth < 4:
        msg = str(cur)
        cur = getattr(cur, "__cause__", None) or getattr(cur, "orig", None)
        depth += 1
    return msg


def ping(conn: Connection) -> str:
    try:
        conn.execute(text("SELECT 1 AS ok"))
        return "ok"
    except Exception as e:  # noqa: BLE001 - reported, never raised, by design
        return "error: " + db_error(e)
