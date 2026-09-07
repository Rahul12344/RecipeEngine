"""
The Postgres connection string every store in this codebase shares (one
database, different tables). Registered as a DI provider (so any class can
just declare a `database_url` constructor parameter and get it injected)
and also directly callable as a plain function -- @provides doesn't wrap
its target, so provider functions that need this value as part of their own
composition logic (e.g. the store/postgres/*_backing_store.py provider
functions) can just call it directly.
"""
from __future__ import annotations

from typing import Optional

from config.env import read_env_var
from di import provides

DATABASE_URL_ENV_VAR = "RECIPE_ENGINE_DATABASE_URL"


@provides("database_url")
def provide_database_url() -> Optional[str]:
    return read_env_var(DATABASE_URL_ENV_VAR)
