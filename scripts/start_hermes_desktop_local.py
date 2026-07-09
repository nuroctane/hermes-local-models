#!/usr/bin/env python3
"""Ensure multi-model router is up, then launch Hermes Desktop."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", ""))
SCRIPTS = Path(__file__).resolve().parent


def main() -> int:
    ensure = SCRIPTS / "ensure_local_router.py"
    rc = subprocess.call([sys.executable, str(ensure), "start"])
    if rc != 0:
        print("Router failed - Hermes may use cloud fallback.")

    candidates = [
        LOCALAPPDATA / "Programs" / "hermes" / "Hermes Desktop.exe",
        LOCALAPPDATA / "hermes" / "Hermes Desktop.exe",
        LOCALAPPDATA / "hermes" / "hermes-desktop.exe",
    ]
    for c in candidates:
        if c.is_file():
            subprocess.Popen([str(c)])
            print(f"Launched {c}")
            return 0

    hermes = LOCALAPPDATA / "hermes" / "hermes-agent" / "venv" / "Scripts" / "hermes.exe"
    if hermes.is_file():
        subprocess.Popen([str(hermes), "desktop"])
        print("Launched: hermes desktop")
        return 0

    print("Router ensured. Open Hermes Desktop manually.")
    print("Models: http://127.0.0.1:8080/v1/models")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
