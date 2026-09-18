"""
Azztec_SaaS_app_main_v1_0_6.py  ->  backend/app/main.py
Version:  0.4.0   (app version reported by /api/v1/health, and info.version of the exported OpenAPI document)
                  UNCHANGED by D1a on purpose: the published document does not move, because every route
                  this slice adds is include_in_schema=False. The card revision is 1.0.6.
Author:   Adriaan
Spec:     Azztec_SaaS_Architecture_and_Stack_v1_0_0.md (D-6, D-8, D-9), S1d chunk spec §5 (OD-19, OD-20)

App factory, lifespan (engine up/down + tz probe), request-id middleware with [F]/[G]/[E] outcome lines,
/api/v1/health, /api/v1/_diag/self-test, the planner router, and app.frontend() serving web/dist in prod.
Run: uv run fastapi dev app/main.py

Changelog:
  (card 1.0.6, app version unchanged)  D1a smoke fix, before the tag: persistence never switches on under
         WORKMATE_ENV=test. The suite boots the app with the real .env (test_smoke's lifespan, every
         TestClient), and 1.0.5 would have written its self-test marker and every [G] it provokes into
         RST's Diag_Log on every pytest run. The INSERT itself is proven by test_diag_trail inside a
         rolled-back transaction; the writer thread is proven by the smoke's self-test read-back.
  (card 1.0.5, app version unchanged)  D1a, spec §3.4 · OD-55…OD-61. create_app hands diag.py the INSERT
         when WORKMATE_DIAG_PERSIST is true, so rows reach dbo.Diag_Log; the lifespan starts the writer
         thread, runs the daily purge when WORKMATE_DIAG_PURGE is true, and flushes the queue on the way
         out. The middleware outcome line now carries the actor (deps.py 1.1.0 puts it on request.state)
         and persists only when it is worth a row - status >= 400, >= 2000 ms, or a method that writes;
         everything still prints. /health gains diagPersist, the counters that make a dead log visible
         instead of inferred, and versions gains diagApi. The self-test writes its marker, flushes and
         READS IT BACK, which is the only honest proof the path works. The dev-only diag router mounts
         under /api/v1.
  0.4.0  S1i (OD-38). Version line only, no logic change. The published schema gained a required field
         (Priority.colour, S1h) while this constant - which is the exported document's info.version and
         therefore the name of docs/api/openapi_<ver>.json - stayed at 0.3.0. Minor-for-a-new-field is the
         standing bump rule (WoW §2); the export is openapi_0_4_0.json and the 0.3.0 file leaves the tree.
         Export from THIS module's `app`, never a second create_app(): the module builds one at import
         time (last line), so the factory called again wires diag twice.
  0.3.0  S1d. create_app() calls diag.configure(level=WORKMATE_LOG_LEVEL) FIRST, so the lifespan's own
         startup lines are the boot-time proof the seam is wired; one [F] diag wired line names the level.
         OD-19: app.frontend() mounts only when dist/index.html exists - an /api/... miss no longer depends
         on the SPA mount, so it reaches the StarletteHTTPException handler as a flat 404 instead of
         500ing on StaticFiles' missing directory. Reverses OD-17; the "no frontend" signal moves to
         /health frontend:"missing" plus a [G] frontend not built line at boot, which is only visible
         because of the diag fix in the same slice. Deliberately NOT a catch-all /api/{rest:path} route:
         Starlette only falls back to its Match.PARTIAL 405 when nothing FULL-matches, so a catch-all
         would turn POST /planner/range into a 404 and red a green test.
         OD-20: health gains diagWired (is anything printing) next to diag (where records persist), and
         versions.config reads config.__version__ instead of a literal that was already stale at 1.0.0.
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

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Connection
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core import config, db, diag
from app.core.config import get_settings
from app.diag import repo as diag_repo
from app.diag import router as diag_router
from app.diag import sql as diag_sql
from app.planner import router as planner_router
from app.planner import service as planner_service

__version__ = "0.4.0"

_HTTP_CODES = {401: "NO_IDENTITY", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}

SLOW_MS = (
    2000  # OD-59: a slow outcome line is worth a row even when it succeeded (Landmines: over 2 s is the box)
)
PURGE_FIRST_DELAY_S = 300
PURGE_EVERY_S = 86_400


def _purge_once() -> dict:
    with db.get_engine().begin() as conn:
        return diag_repo.purge(conn, days=diag_repo.retention_days(conn), dry_run=False)


async def _purge_daily() -> None:
    """OD-60. Five minutes after boot, then once a day, on a worker thread so the loop never blocks."""
    await asyncio.sleep(PURGE_FIRST_DELAY_S)
    while True:
        try:
            out = await asyncio.to_thread(_purge_once)
            diag.log(
                "S",
                f"diag purge {out['deleted']} of {out['rows']} rows older than {out['cutoffDays']} days",
                source="diag",
                dedupe=False,
            )
        except Exception as e:  # noqa: BLE001 - housekeeping never takes the app down
            diag.log("E", "diag purge failed", detail=db.db_error(e), source="diag", dedupe=False)
        await asyncio.sleep(PURGE_EVERY_S)


Conn = Annotated[Connection, Depends(db.get_conn)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    engine = db.get_engine()
    diag.start_writer()  # D1a: one writer per process; idempotent, and a no-op while persistence is off
    try:
        with engine.connect() as conn:
            diag.log("F", f"startup db={db.ping(conn)} dialect={engine.dialect.name}", source="main")
    except Exception as e:  # noqa: BLE001 - boot anyway; /health reports the error text
        diag.log("E", "startup db connect failed", detail=db.db_error(e), source="main")
    try:
        diag.log("F", f"startup tz={planner_service.resolve_tz()}", source="main")
    except Exception as e:  # noqa: BLE001 - boot anyway; /range will 500 and this line says why
        diag.log("E", f"startup tz={s.tz} invalid", detail=repr(e), source="main")
    purge_task = asyncio.create_task(_purge_daily()) if (s.diag_purge and diag.PERSIST_SQL) else None
    yield
    if purge_task is not None:
        purge_task.cancel()
    diag.flush()  # the queue is drained before the engine goes, or the last rows are lost
    engine.dispose()


def create_app() -> FastAPI:
    s = get_settings()

    # First, before anything can want to log. Until 0.3.0 nothing attached a handler to 'workmate.diag'
    # and its effective level was root's WARNING, so every [F]/[G] was dropped on a dev server.
    diag.configure(level=s.log_level)
    diag.log(
        "F", f"diag wired level={s.log_level.upper()} stream=stdout diag={diag.__version__}", source="main"
    )
    # D1a: the one place persistence is switched on. Core never imports the feature package (OD-55).
    # Never under test: the suite boots this app against the real .env and must not write to RST.
    if s.diag_persist and s.env != "test":
        diag.PERSIST_SQL = diag_sql.INSERT
    diag.log("F", f"diag persist={diag.persist_mode()}", source="main", persist=False)

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
            # the dependency has run by now, so the actor is on the request; before call_next it is not
            actor = int(getattr(request.state, "actor", 0) or 0)
            keep = tag != "F" or ms >= SLOW_MS or request.method != "GET"  # OD-59
            diag.log(
                tag,
                f"{request.method} {request.url.path} {response.status_code} {ms}ms",
                actor=actor,
                request_id=rid,
                persist=keep,
                dedupe=False,
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
            "diag": diag.persist_mode(),  # where records PERSIST
            "diagWired": diag.is_wired(),  # whether anything is PRINTING (OD-20)
            "diagPersist": diag.counters(),  # D1a: written / failed / dropped - a dead log must be visible
            "versions": {
                "db": db.__version__,
                "diag": diag.__version__,
                "config": config.__version__,  # read, never a literal - /health must not lie (WoW §2)
                "planner": planner_router.__version__,
                "diagApi": diag_router.__version__,
            },
        }

    @api.get("/_diag/self-test")
    def diag_self_test(request: Request, conn: Conn) -> dict:
        rid = getattr(request.state, "rid", "")
        actor = s.dev_user_id if s.is_dev else 0
        rec = diag.log("F", "diag self-test", request_id=rid, actor=actor, dedupe=False)
        persisted, diag_id = False, 0
        if diag.PERSIST_SQL:
            diag.flush()
            found = diag_repo.by_rid(conn, rid)
            persisted = bool(found)
            diag_id = int(found[0]["Diag_Id"]) if found else 0
        return {
            "ok": True,
            "rid": rid,
            "actor": actor,
            "persist": diag.persist_mode(),
            "wired": diag.is_wired(),
            "db": db.ping(conn),
            "persisted": persisted,  # the marker written AND read back - the only honest proof
            "diagId": diag_id,
            "record": rec,
        }

    api.include_router(planner_router.router)
    api.include_router(diag_router.router)  # dev-only, out of the schema (OD-61)
    app.include_router(api)

    # SPA: path operations always win; fallback serves index.html for browser navigations only.
    # OD-19: mount only when there is something to serve. Without this, StaticFiles raises on the missing
    # directory and an /api/... miss becomes a 500 instead of reaching the flat-404 handler above.
    dist = _dist_dir(s.frontend_dist)
    if (dist / "index.html").exists():
        app.frontend("/", directory=str(dist), check_dir=(s.env == "prod"))
    else:
        diag.log("G", f"frontend not built dist={dist}", source="main")
    return app


def _dist_dir(rel: str) -> Path:
    return (Path(__file__).resolve().parents[1] / rel).resolve()


app = create_app()
