"""Load provider credentials from a local, git-ignored ``.env`` file.

Only entry points call this. Existing environment variables always win,
values are never logged, and the core never reads credential files.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_local_env(path: str = ".env") -> None:
    file = Path(path)
    if not file.is_file():
        return
    for line in file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


__all__ = ["load_local_env"]
