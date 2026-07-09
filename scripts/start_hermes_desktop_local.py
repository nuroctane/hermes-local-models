#!/usr/bin/env python3
"""Ensure multi-model router is up, then launch Hermes Desktop (Windows + macOS + Linux)."""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import hermes_home  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
SYSTEM = platform.system()


def _launch_mac_app(app_path: Path) -> bool:
    """
    Launch a .app bundle on macOS.
    Prefer `open /path/App.app` (path form). Fall back to `open -a Name`.
    """
    # Canonical: open the bundle path (do NOT use -a with a full path)
    try:
        r = subprocess.run(
            ["open", str(app_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode == 0:
            print(f"Launched {app_path}")
            return True
        if r.stderr:
            print(f"  open path failed: {r.stderr.strip()}")
    except Exception as e:
        print(f"  open path failed: {e}")

    # Name-only fallback: "Hermes Desktop.app" -> "Hermes Desktop"
    name = app_path.stem if app_path.suffix == ".app" else app_path.name
    if name.endswith(".app"):
        name = name[: -len(".app")]
    try:
        r = subprocess.run(
            ["open", "-a", name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode == 0:
            print(f"Launched via open -a {name!r}")
            return True
        if r.stderr:
            print(f"  open -a failed: {r.stderr.strip()}")
    except Exception as e:
        print(f"  open -a failed: {e}")
    return False


def main() -> int:
    ensure = SCRIPTS / "ensure_local_router.py"
    rc = subprocess.call([sys.executable, str(ensure), "start"])
    if rc != 0:
        print("Router failed - Hermes may use cloud fallback.")

    home = hermes_home()
    candidates: list[Path] = []

    if SYSTEM == "Darwin":
        candidates += [
            Path("/Applications/Hermes Desktop.app"),
            Path("/Applications/Hermes.app"),
            Path.home() / "Applications" / "Hermes Desktop.app",
            Path.home() / "Applications" / "Hermes.app",
        ]
    elif SYSTEM == "Windows":
        la = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        candidates += [
            la / "Programs" / "hermes" / "Hermes Desktop.exe",
            la / "hermes" / "Hermes Desktop.exe",
            home / "Hermes Desktop.exe",
            home / "hermes-desktop.exe",
        ]
    else:
        candidates += [
            Path.home() / ".local" / "bin" / "hermes-desktop",
        ]

    for c in candidates:
        if SYSTEM == "Darwin" and c.suffix == ".app" and c.is_dir():
            if _launch_mac_app(c):
                return 0
            continue
        if c.is_file():
            subprocess.Popen([str(c)])
            print(f"Launched {c}")
            return 0

    # Name-only Mac attempt even if path candidates missing
    if SYSTEM == "Darwin":
        for name in ("Hermes Desktop", "Hermes"):
            try:
                r = subprocess.run(
                    ["open", "-a", name],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if r.returncode == 0:
                    print(f"Launched via open -a {name!r}")
                    return 0
            except Exception:
                pass

    if SYSTEM == "Windows":
        hermes_cli = home / "hermes-agent" / "venv" / "Scripts" / "hermes.exe"
    else:
        hermes_cli = home / "hermes-agent" / "venv" / "bin" / "hermes"
    if hermes_cli.is_file():
        subprocess.Popen([str(hermes_cli), "desktop"])
        print("Launched: hermes desktop")
        return 0

    which = shutil.which("hermes")
    if which:
        subprocess.Popen([which, "desktop"])
        print("Launched: hermes desktop (PATH)")
        return 0

    print("Router is up. Open Hermes Desktop manually.")
    print("Models: http://127.0.0.1:8080/v1/models")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
