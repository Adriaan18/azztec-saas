"""
Azztec_SaaS_app_auth_router_v1_0_0.py  ->  backend/app/auth/router.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s5 (OD-96..OD-101)
Pair:     backend/tests/test_auth_api.py 1.0.0

Three routes under /api/v1/auth (main.py 0.6.0 mounts it). Plain def (D-2). Errors are the flat OD-15
shape through main.py's handler:
  POST /signin    200 SessionInfo + the azztec_session cookie (HttpOnly, Secure, SameSite=Strict, Path=/)
                  401 SIGNIN_FAILED (one body for an unknown login and a wrong password - OD-98)
                  403 SYS_USER | DEFAULT_PASSWORD | NO_GROUP | RESET_DUE (only after the password is proved)
                  423 LOCKED (OD-99)   403 CSRF without X-Azztec-Request: 1 (OD-97)
  POST /signout   200 {ok:true}, cookie cleared, session revoked; idempotent
  GET  /me        200 SessionInfo · 401 NO_IDENTITY
Diag: one [F] per sign-in and sign-out, one [G] per refusal, carrying the login as typed and the reason.

Changelog:
  1.0.0  Initial DP2a.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.auth import rules, service
from app.auth.schemas import AuthUser, PageRights, SessionInfo, SignedOut, SignIn
from app.core import deps, diag
from app.core.config import get_settings
from app.planner.schemas import ApiError

__version__ = "1.0.0"

router = APIRouter(prefix="/auth", tags=["auth"])

_ERRORS = {401: {"model": ApiError}, 403: {"model": ApiError}, 423: {"model": ApiError}}


def _info(p: deps.Principal) -> SessionInfo:
    return SessionInfo(
        ok=True,
        user=AuthUser(userId=p.user_id, shortId=p.short_id, name=p.name),
        rights=PageRights(planner=p.rights.get("planner", "NA"), womaint=p.rights.get("womaint", "NA")),
        isAdmin=p.is_admin,
        expiresAt=p.expires_at,
    )


def _ip(request: Request) -> str:
    return request.client.host if request.client else ""


@router.post(
    "/signin", response_model=SessionInfo, responses=_ERRORS, dependencies=[Depends(deps.require_csrf)]
)
def sign_in(body: SignIn, request: Request, response: Response) -> SessionInfo:
    s = get_settings()
    rid = getattr(request.state, "rid", "")
    out = service.sign_in(body.login, body.password, _ip(request), request.headers.get("user-agent", ""), rid)
    login = rules.clip_login(body.login)
    if not out.ok or out.principal is None:
        request.state.actor = int(out.detail.get("userId", 0) or 0)
        diag.log(
            "G",
            f"signin refused code={out.code}",
            detail={"login": login, **out.detail},
            actor=request.state.actor,
            request_id=rid,
            source="auth",
        )
        raise HTTPException(status_code=out.status, detail={"code": out.code, "message": out.message})
    p = out.principal
    request.state.actor = p.user_id
    response.set_cookie(
        key=s.session_cookie,
        value=out.token,
        max_age=s.session_hours * 3600,
        httponly=True,
        secure=s.cookie_secure,
        samesite="strict",
        path="/",
    )
    diag.log(
        "F",
        f"signin ok {p.short_id} planner={p.rights.get('planner')} womaint={p.rights.get('womaint')} "
        f"admin={p.is_admin}",
        actor=p.user_id,
        request_id=rid,
        source="auth",
    )
    return _info(p)


@router.post("/signout", response_model=SignedOut, dependencies=[Depends(deps.require_csrf)])
def sign_out(request: Request, response: Response) -> SignedOut:
    s = get_settings()
    rid = getattr(request.state, "rid", "")
    user_id = service.sign_out(
        request.cookies.get(s.session_cookie), _ip(request), request.headers.get("user-agent", ""), rid
    )
    request.state.actor = user_id
    response.delete_cookie(
        key=s.session_cookie, path="/", secure=s.cookie_secure, httponly=True, samesite="strict"
    )
    diag.log("F", f"signout user={user_id}", actor=user_id, request_id=rid, source="auth")
    return SignedOut(ok=True)


@router.get("/me", response_model=SessionInfo, responses={401: {"model": ApiError}})
def me(principal: Annotated[deps.Principal, Depends(deps.get_principal)]) -> SessionInfo:
    return _info(principal)
