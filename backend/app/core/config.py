"""
Azztec_SaaS_app_core_config_v1_3_0.py  ->  backend/app/core/config.py
Version:  1.3.0
Author:   Adriaan
Spec:     Azztec_SaaS_Architecture_and_Stack_v1_0_0.md (D-11), Azztec_SaaS_Data_Layer_and_RST_DB_v1_0_0.md §3
          Azztec_SaaS_S1d_Diag_Chunk_Spec_v1_0_0.md §4, Azztec_SaaS_D1a_Persist_Chunk_Spec_v1_0_0.md §3.5
          Azztec_SaaS_DP2_SignIn_Rights_Chunk_Spec_v1_0_1.md s5 (OD-97, OD-99, OD-100, OD-103)

Settings from environment / backend/.env (prefix WORKMATE_). One place, typed, cached.

TRAP (Raw Log 2026-09-11 1.1.0 §5): get_settings() is lru_cached, so a watchfiles reload does NOT pick up
a .env change - restart the server. And .env edits do not reliably reach disk from a chained PowerShell
heredoc; verify with Select-String before blaming code.

Changelog:
  1.3.0  DP2a: the session cookie and its lifetimes (12 h absolute, 4 h idle - OD-97), cookie_secure
         (default true; http://localhost still works, a LAN server needs HTTPS - trap 4), the lockout
         numbers (OD-99) and the rights cache (OD-100). dev_user_id stays readable for scripts but is no
         longer an identity for any request (OD-103).
  1.2.0  D1a: diag_persist (WORKMATE_DIAG_PERSIST) decides whether main.py hands diag.py the INSERT, and
         diag_purge (WORKMATE_DIAG_PURGE) whether this process runs the nightly purge - false on every
         worker but one, or the same rows are chased by several processes (OD-57, OD-60).
  1.1.0  log_level (WORKMATE_LOG_LEVEL, default INFO) - the threshold diag.configure() applies to the
         'workmate.diag' logger. S1d.
  1.0.0  Initial.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

__version__ = "1.3.0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WORKMATE_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "workmate-saas"
    env: str = "dev"  # dev | test | prod
    tz: str = "Pacific/Auckland"
    secret_key: str = "change-me"
    frontend_dist: str = "../web/dist"  # relative to backend/

    # diagnostics — threshold for the 'workmate.diag' logger; [F]/[G] are INFO, [E] is ERROR
    log_level: str = "INFO"
    diag_persist: bool = True  # False -> stdout only, exactly as every slice before D1a
    diag_purge: bool = True  # one process only; the others must set this false

    # database — kind selects the dialect; url (postgresql or a full mssql+pyodbc url) overrides the parts
    db_kind: str = "mssql"  # mssql | postgresql
    db_url: str = ""
    db_server: str = "localhost"
    db_name: str = "dbWorkmate"
    db_user: str = "svc_workmate"
    db_password: str = ""
    db_trust_cert: bool = True  # ODBC Driver 18 defaults Encrypt=yes; dev instances have self-signed certs
    db_driver: str = "ODBC Driver 18 for SQL Server"
    sqlalchemy_echo: bool = False

    # sign-in and sessions (DP2, OD-97 / OD-99 / OD-100)
    session_cookie: str = "azztec_session"
    session_hours: int = 12  # absolute lifetime
    session_idle_minutes: int = 240  # idle lifetime
    cookie_secure: bool = True  # http://localhost accepts a Secure cookie; a LAN server needs HTTPS
    lockout_failures: int = 5  # per login, inside lockout_minutes
    lockout_ip_failures: int = 20  # per client address, inside lockout_minutes
    lockout_minutes: int = 15
    rights_cache_seconds: int = 60

    # No longer an identity for any request (OD-103). Kept so scripts can still read it.
    dev_user_id: int = 0

    @property
    def is_dev(self) -> bool:
        return self.env == "dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()
