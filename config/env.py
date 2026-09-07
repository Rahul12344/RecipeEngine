"""
Generic .env file support.

`read_env_var(name)` is the one boilerplate function every env-var-backed
config provider should be built on: it checks the real process environment
first (so CI/deploy environments can always override), falling back to a
`.env` file at the repo root (parsed once and cached) for local dev.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE_PATH = _REPO_ROOT / ".env"


def _parse_dotenv(path: Path) -> Dict[str, str]:
    if not path.is_file():
        return {}
    values: Dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@lru_cache(maxsize=1)
def _dotenv_values() -> Dict[str, str]:
    return _parse_dotenv(_ENV_FILE_PATH)


def read_env_var(name: str) -> Optional[str]:
    """Read `name` from the real environment, falling back to `.env` at the
    repo root. Real env vars always win over `.env`, so a checked-in-for-
    local-dev value never silently overrides a real deployment setting."""
    return os.environ.get(name) or _dotenv_values().get(name)
