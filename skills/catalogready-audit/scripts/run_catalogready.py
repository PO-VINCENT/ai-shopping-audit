#!/usr/bin/env python3
"""Run CatalogReady from a source checkout, local install, or uvx fallback."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _is_catalogready_checkout(directory: Path) -> bool:
    pyproject = directory / "pyproject.toml"
    if not pyproject.is_file():
        return False
    try:
        content = pyproject.read_text(encoding="utf-8")
    except OSError:
        return False
    return any(
        line.strip().replace(" ", "") in {'name="catalogready-ai"', "name='catalogready-ai'"}
        for line in content.splitlines()
    )


def _command(arguments: list[str]) -> list[str]:
    uv = shutil.which("uv")
    if uv and _is_catalogready_checkout(Path.cwd()):
        return [uv, "run", "catalogready", *arguments]

    installed = shutil.which("catalogready")
    if installed:
        return [installed, *arguments]

    uvx = shutil.which("uvx")
    if uvx:
        return [uvx, "--from", "catalogready-ai", "catalogready", *arguments]

    raise RuntimeError(
        "CatalogReady is unavailable. Install it with "
        "`python3 -m pip install catalogready-ai` or install uv/uvx."
    )


def main() -> int:
    if len(sys.argv) == 1:
        print("usage: run_catalogready.py <catalogready arguments>", file=sys.stderr)
        return 2
    try:
        command = _command(sys.argv[1:])
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 127
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
