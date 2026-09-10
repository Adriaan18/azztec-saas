"""
Azztec_SaaS_app_core_config_v1_0_0.py  ->  backend/app/core/config.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_Architecture_and_Stack_v1_0_0.md (D-11), Azztec_SaaS_Data_Layer_and_RST_DB_v1_0_0.md §3

Settings from environment / backend/.env (prefix WORKMATE_). One place, typed, cached.

Changelog:
  1.0.0  Initial.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

__version__ = "1.0.0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WORKMATE_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "workmate-saas"
    env: str = "dev"  # dev | test | prod
    tz: str = "Pacific/Auckland"
    secret_key: str = "change-me"
    frontend_dist: str = "../web/dist"  # relative to backend/

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

    # dev-only actor override (the PLANNER_DEV_USER_ID twin); ignored unless env == dev
    dev_user_id: int = 0

    @property
    def is_dev(self) -> bool:
        return self.env == "dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()
