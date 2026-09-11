"""
Azztec_SaaS_app_main_v1_0_2.py  ->  backend/app/main.py
Version:  0.2.1   (app version reported by /api/v1/health)
Author:   Adriaan
Spec:     Azztec_SaaS_Architecture_and_Stack_v1_0_0.md (D-6, D-8, D-9), S1c chunk spec §3.4 / §5 / §6

App factory, lifespan (engine up/down + tz probe), request-id middleware with [F]/[G]/[E] outcome lines,
/api/v1/health, /api/v1/_diag/self-test, the planner router, and app.frontend() serving web/dist in prod.
Run: uv run fastapi dev app/main.py

Changelog:
  0.2.1  Ruff B008: the two S0 routes take `Annotated[Connection, Depends(db.get_conn)]` like router.py.
         Pre-existing from 0.1.0; surfaced once main.py changed. No behaviour change.
  0.2.0  S1c: mount app.planner.router under /api/v1; lifespan probes WORKMATE_TZ and logs [E] on a bad
         zone (boot anyway, same habit as the DB); HTTPException handler renders the flat OD-15 body
         {ok:false, code, message, rid} so 401/404/405 match INTERNAL. This is the error *shape*, not the
         queued API 404 handler (OD-17) - the web/dist RuntimeError still surfaces as a 500 and the known
         red test stays red until `pnpm build`. health adds "planner" to versions.
  0.1.0  Initial S0.
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Connection
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core import db, diag
from app.core.config import get_settings
from app.planner import router as planner_router
from app.planner import service as planner_service

__version__ = "0.2.1"

_HTTP_CODES = {401: "NO_IDENTITY", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}

Conn = Annotated[Connection, Depends(db.get_conn)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    engine = db.get_engine()
    try:
        with engine.connect() as conn:
            diag.log("F", f"startup db={db.ping(conn)} dialect={engine.dialect.name}", source="main")
    except Exception as e:  # noqa: BLE001 - boot anyway; /health reports the error text
        diag.log("E", "startup db connect failed", detail=db.db_error(e), source="main")
    try:
        diag.log("F", f"startup tz={planner_service.resolve_tz()}", source="main")
    except Exception as e:  # noqa: BLE001 - boot anyway; /range will 500 and this line says why
        diag.log("E", f"startup tz={s.tz} invalid", detail=repr(e), source="main")
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
            return JSONResponse(
                {"ok": False, "code": "INTERNAL", "message": str(e), "rid": rid}, status_code=500
            )
        ms = int((time.perf_counter() - t0) * 1000)
        if request.url.path.startswith("/api/"):
            tag = "E" if response.status_code >= 500 else "G" if response.status_code >= 400 else "F"
            diag.log(
                tag,
                f"{request.method} {request.url.path} {response.status_code} {ms}ms",
                request_id=rid,
                persist=False,
            )
        response.headers["X-Request-Id"] = rid
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_flat(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """OD-15: every HTTP error is {ok:false, code, message, rid}. A dict detail with a code wins."""
        rid = getattr(request.state, "rid", "")
        d = exc.detail
        if isinstance(d, dict) and "code" in d:
            code, message = str(d["code"]), str(d.get("message", ""))
        else:
            code, message = _HTTP_CODES.get(exc.status_code, f"HTTP_{exc.status_code}"), str(d)
        return JSONResponse(
            {"ok": False, "code": code, "message": message, "rid": rid},
            status_code=exc.status_code,
            headers=exc.headers,
        )

    api = APIRouter(prefix="/api/v1")

    @api.get("/health")
    def health(conn: Conn) -> dict:
        dist = _dist_dir(s.frontend_dist)
        return {
            "app": s.app_name,
            "version": __version__,
            "env": s.env,
            "db": db.ping(conn),
            "dbKind": conn.dialect.name,
            "dbName": s.db_name
            if conn.dialect.name == "mssql"
            else (s.db_url.rsplit("/", 1)[-1] if s.db_url else ""),
            "tz": s.tz,
            "frontend": "built" if (dist / "index.html").exists() else "missing",
            "diag": diag.persist_mode(),
            "versions": {
                "db": db.__version__,
                "diag": diag.__version__,
                "config": "1.0.0",
                "planner": planner_router.__version__,
            },
        }

    @api.get("/_diag/self-test")
    def diag_self_test(request: Request, conn: Conn) -> dict:
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

    api.include_router(planner_router.router)
    app.include_router(api)

    # SPA: path operations always win; fallback serves index.html for browser navigations only.
    # check_dir only in prod so pytest / first boot work before `pnpm build`.
    app.frontend("/", directory=str(_dist_dir(s.frontend_dist)), check_dir=(s.env == "prod"))
    return app


def _dist_dir(rel: str) -> Path:
    return (Path(__file__).resolve().parents[1] / rel).resolve()


app = create_app()
