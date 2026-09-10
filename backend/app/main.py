"""
Azztec_SaaS_app_main_v1_0_0.py  ->  backend/app/main.py
Version:  0.1.0   (app version reported by /api/v1/health)
Author:   Adriaan
Spec:     Azztec_SaaS_Architecture_and_Stack_v1_0_0.md (D-6, D-8, D-9), Planner Port Spec S0

S0 scaffold: app factory, lifespan (engine up/down), request-id middleware with [F]/[G]/[E] outcome lines,
/api/v1/health, /api/v1/_diag/self-test, and app.frontend() serving web/dist in prod.
Run: uv run fastapi dev app/main.py

Changelog:
  0.1.0  Initial S0.
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Connection

from app.core import db, diag
from app.core.config import get_settings

__version__ = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = db.get_engine()
    try:
        with engine.connect() as conn:
            diag.log("F", f"startup db={db.ping(conn)} dialect={engine.dialect.name}", source="main")
    except Exception as e:  # noqa: BLE001 - boot anyway; /health reports the error text
        diag.log("E", "startup db connect failed", detail=db.db_error(e), source="main")
    yield
    engine.dispose()


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="Workmate SaaS", version=__version__, lifespan=lifespan)

    @app.middleware("http")
    async def request_outcome(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request.state.rid = rid
        t0 = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as e:  # noqa: BLE001 - logged as [E], returned as JSON 500
            diag.log("E", f"{request.method} {request.url.path} crashed", detail=repr(e), request_id=rid)
            return JSONResponse({"ok": False, "code": "INTERNAL", "message": str(e), "rid": rid}, status_code=500)
        ms = int((time.perf_counter() - t0) * 1000)
        if request.url.path.startswith("/api/"):
            tag = "E" if response.status_code >= 500 else "G" if response.status_code >= 400 else "F"
            diag.log(tag, f"{request.method} {request.url.path} {response.status_code} {ms}ms", request_id=rid, persist=False)
        response.headers["X-Request-Id"] = rid
        return response

    api = APIRouter(prefix="/api/v1")

    @api.get("/health")
    def health(conn: Connection = Depends(db.get_conn)) -> dict:
        dist = _dist_dir(s.frontend_dist)
        return {
            "app": s.app_name,
            "version": __version__,
            "env": s.env,
            "db": db.ping(conn),
            "dbKind": conn.dialect.name,
            "dbName": s.db_name if conn.dialect.name == "mssql" else (s.db_url.rsplit("/", 1)[-1] if s.db_url else ""),
            "tz": s.tz,
            "frontend": "built" if (dist / "index.html").exists() else "missing",
            "diag": diag.persist_mode(),
            "versions": {"db": db.__version__, "diag": diag.__version__, "config": "1.0.0"},
        }

    @api.get("/_diag/self-test")
    def diag_self_test(request: Request, conn: Connection = Depends(db.get_conn)) -> dict:
        rid = getattr(request.state, "rid", "")
        rec = diag.log("F", "diag self-test", request_id=rid)
        return {
            "ok": True,
            "rid": rid,
            "actor": s.dev_user_id if s.is_dev else 0,
            "persist": diag.persist_mode(),
            "db": db.ping(conn),
            "record": rec,
        }

    app.include_router(api)

    # SPA: path operations always win; fallback serves index.html for browser navigations only.
    # check_dir only in prod so pytest / first boot work before `pnpm build`.
    app.frontend("/", directory=str(_dist_dir(s.frontend_dist)), check_dir=(s.env == "prod"))
    return app


def _dist_dir(rel: str) -> Path:
    return (Path(__file__).resolve().parents[1] / rel).resolve()


app = create_app()
