#!/usr/bin/env python3
"""Ensure llama-server router lists all Atomic Chat GGUFs on :8080."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import urllib.request

LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", ""))
APPDATA = Path(os.environ.get("APPDATA", ""))
# Prefer scripts next to this file (repo or installed copy)
SCRIPTS = Path(__file__).resolve().parent
PRESET = LOCALAPPDATA / "hermes" / "local-models" / "models-preset.ini"
LOG_DIR = LOCALAPPDATA / "hermes" / "logs"
OUT_LOG = LOG_DIR / "local-router.out.log"
ERR_LOG = LOG_DIR / "local-router.err.log"

CUDA_SERVER = (
    APPDATA
    / "Atomic Chat"
    / "data"
    / "llamacpp"
    / "backends"
    / "turboquant-windows-x64-cuda-13.3-61ee3eb"
    / "windows-x64-cuda-13.3"
    / "build"
    / "bin"
    / "llama-server.exe"
)
CPU_SERVER = (
    APPDATA
    / "Atomic Chat"
    / "data"
    / "llamacpp"
    / "backends"
    / "turboquant-windows-x64-cpu-61ee3eb"
    / "windows-x64-cpu"
    / "build"
    / "bin"
    / "llama-server.exe"
)

PORT = 8080


def sync() -> None:
    subprocess.check_call([sys.executable, str(SCRIPTS / "sync_atomic_models.py")])


def listener_pid(port: int = PORT) -> int | None:
    try:
        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"(Get-NetTCPConnection -LocalPort {port} -State Listen -EA SilentlyContinue | Select-Object -First 1).OwningProcess",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if out.isdigit():
            return int(out)
    except Exception:
        pass
    return None


def fetch_models(port: int = PORT):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=5) as r:
            import json

            return json.loads(r.read().decode())
    except Exception:
        return None


def stop() -> None:
    pid = listener_pid()
    if pid:
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        time.sleep(1)
        print(f"Stopped pid {pid} on port {PORT}")
    else:
        print(f"No listener on port {PORT}")


def start(cpu: bool = False, models_max: int = 1) -> None:
    sync()
    if not PRESET.is_file():
        raise SystemExit(f"Preset missing: {PRESET}")

    pid = listener_pid()
    api = fetch_models()
    if pid and api and api.get("data"):
        print(f"Already up on :{PORT} (pid={pid})")
        for m in api["data"]:
            print(f"  {m.get('id')}")
        return
    if pid:
        print("Port busy but API unhealthy - restarting")
        stop()

    server = CPU_SERVER if cpu or not CUDA_SERVER.is_file() else CUDA_SERVER
    if not server.is_file():
        raise SystemExit(f"llama-server.exe not found: {server}")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ngl = "0" if cpu else "99"
    # Router mode: models-preset, no single -m
    args = [
        str(server),
        "--models-preset",
        str(PRESET),
        "--host",
        "127.0.0.1",
        "--port",
        str(PORT),
        "--models-max",
        str(models_max),
        "-c",
        "65536",
        "-ngl",
        ngl,
        "--jinja",
    ]
    print("Starting local model router")
    print(f"  server : {server}")
    print(f"  preset : {PRESET}")
    print(f"  port   : {PORT}")
    print(f"  api    : http://127.0.0.1:{PORT}/v1")

    with open(OUT_LOG, "w", encoding="utf-8") as out, open(ERR_LOG, "w", encoding="utf-8") as err:
        subprocess.Popen(
            args,
            cwd=str(server.parent),
            stdout=out,
            stderr=err,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    print("Waiting for /v1/models ...")
    for i in range(90):
        time.sleep(2)
        api = fetch_models()
        if api and api.get("data"):
            print(f"Ready after ~{i * 2} sec - {len(api['data'])} model(s)")
            for m in api["data"]:
                print(f"  {m.get('id')}")
            return
        if i % 10 == 0:
            print(f"  still starting... {i * 2} sec")
    print("Failed. Tail of error log:")
    if ERR_LOG.is_file():
        print(ERR_LOG.read_text(encoding="utf-8", errors="replace")[-2000:])
    raise SystemExit(2)


def status() -> None:
    pid = listener_pid()
    api = fetch_models()
    if api and api.get("data"):
        print(f"UP pid={pid}")
        for m in api["data"]:
            print(f"  {m.get('id')}")
    else:
        print("DOWN")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "action",
        nargs="?",
        default="start",
        choices=["start", "stop", "restart", "status", "sync"],
    )
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--models-max", type=int, default=1)
    args = ap.parse_args()

    if args.action == "sync":
        sync()
    elif args.action == "stop":
        stop()
    elif args.action == "status":
        status()
    elif args.action == "restart":
        stop()
        start(cpu=args.cpu, models_max=args.models_max)
    else:
        start(cpu=args.cpu, models_max=args.models_max)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
