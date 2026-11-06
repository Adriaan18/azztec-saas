"""
Azztec_SaaS_app_auth_schemas_v1_0_0.py  ->  backend/app/auth/schemas.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s5 (OD-96, OD-97, OD-100)

Pydantic v2, camelCase on the wire, extra="forbid" on everything (the S1c drift guard). The session
token is never in a body - it travels only in the HttpOnly cookie.

Changelog:
  1.0.0  Initial DP2a.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__version__ = "1.0.0"

Right = Literal["RWD", "RW", "RO", "NA"]


class SignIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    login: str = Field(min_length=1, max_length=100, description="the Workmate.NET login id")
    password: str = Field(min_length=1, max_length=200, description="verified, never stored or logged")


class AuthUser(BaseModel):
    model_config = ConfigDict(extra="forbid")
    userId: int
    shortId: str
    name: str


class PageRights(BaseModel):
    model_config = ConfigDict(extra="forbid")
    planner: Right
    womaint: Right


class SessionInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ok: bool
    user: AuthUser
    rights: PageRights
    isAdmin: bool
    expiresAt: str = Field(description="UTC, ISO 8601 with a Z")


class SignedOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ok: bool
