#!/usr/bin/env python3
"""Ensure llama-server router lists all Atomic/Jan GGUFs on :8080 (Windows + macOS + Linux)."""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import SYSTEM, find_llama_server, hermes_paths  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
PORT = int(os.environ.get("HERMES_LOCAL_PORT", "8080"))


def sync() -> None:
    subprocess.check_call([sys.executable, str(SCRIPTS / "sync_atomic_models.py")])


def listener_pid(port: int = PORT) -> int | None:
    if SYSTEM == "Windows":
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
    # macOS / Linux
    try:
        out = subprocess.check_output(
            ["lsof", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        for line in out.splitlines():
            line = line.strip()
            if line.isdigit():
                return int(line)
    except Exception:
        pass
    try:
        out = subprocess.check_output(
            ["ss", "-lptn", f"sport = :{port}"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        import re

        m = re.search(r"pid=(\d+)", out)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None


def process_cmdline(pid: int) -> str:
    """Best-effort command line / image name for pid (lowercased)."""
    if SYSTEM == "Windows":
        try:
            out = subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"(Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\").CommandLine",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            if out:
                return out.lower()
        except Exception:
            pass
        try:
            out = subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"(Get-Process -Id {pid} -EA SilentlyContinue).ProcessName",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            return out.lower()
        except Exception:
            pass
        return ""
    # Unix: args, then comm
    try:
        out = subprocess.check_output(
            ["ps", "-p", str(pid), "-o", "args="],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if out:
            return out.lower()
    except Exception:
        pass
    try:
        out = subprocess.check_output(
            ["ps", "-p", str(pid), "-o", "comm="],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return out.lower()
    except Exception:
        pass
    # Linux /proc fallback
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ").decode(
            "utf-8", errors="replace"
        )
        return cmdline.lower()
    except Exception:
        pass
    return ""


def is_llama_server_pid(pid: int) -> bool:
    cmd = process_cmdline(pid)
    if not cmd:
        return False
    return "llama-server" in cmd


def fetch_models(port: int = PORT):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def stop() -> None:
    pid = listener_pid()
    if not pid:
        print(f"No listener on port {PORT}")
        return
    if not is_llama_server_pid(pid):
        cmd = process_cmdline(pid) or "(unknown)"
        print(
            f"Port {PORT} is held by pid {pid}, which does not look like llama-server:\n"
            f"  {cmd[:200]}\n"
            f"Not killing it. Free the port manually or set HERMES_LOCAL_PORT."
        )
        return
    if SYSTEM == "Windows":
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    else:
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        except ProcessLookupError:
            pass
    time.sleep(1)
    print(f"Stopped llama-server pid {pid} on port {PORT}")


def start(cpu: bool = False, models_max: int = 1) -> None:
    hp = hermes_paths()
    preset = hp["preset"]
    out_log = hp["out_log"]
    err_log = hp["err_log"]
    hp["logs"].mkdir(parents=True, exist_ok=True)

    sync()
    if not preset.is_file():
        raise SystemExit(f"Preset missing: {preset}")

    pid = listener_pid()
    api = fetch_models()
    if pid and api and api.get("data"):
        # Healthy OpenAI-compatible API on our port — already up
        print(f"Already up on :{PORT} (pid={pid})")
        for m in api["data"]:
            print(f"  {m.get('id')}")
        return
    if pid:
        if is_llama_server_pid(pid):
            print("Port busy with llama-server but API unhealthy - restarting")
            stop()
        else:
            cmd = process_cmdline(pid) or "(unknown)"
            raise SystemExit(
                f"Port {PORT} is in use by non-router process pid={pid}:\n"
                f"  {cmd[:200]}\n"
                f"Stop that process or set HERMES_LOCAL_PORT to another port."
            )

    server = find_llama_server(prefer_cpu=cpu)
    if not server:
        raise SystemExit(
            "llama-server not found.\n"
            "  Windows: install/open Atomic Chat once so backends download.\n"
            "  macOS:   brew install llama.cpp   OR use Atomic/Jan backends under\n"
            "           ~/Library/Application Support/\n"
            "  Or set LLAMA_SERVER=/path/to/llama-server"
        )

    # Ensure +x on Unix when we can (Atomic drops sometimes lack execute bit)
    if SYSTEM != "Windows":
        try:
            mode = server.stat().st_mode
            if not (mode & 0o111):
                server.chmod(mode | 0o755)
                print(f"  chmod +x {server}")
        except OSError as e:
            print(f"  warning: could not chmod {server}: {e}")

    # Metal (mac) and CUDA both use high n-gpu-layers; --cpu forces 0
    ngl = "0" if cpu else "99"
    args = [
        str(server),
        "--models-preset",
        str(preset),
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
    print(f"  system : {SYSTEM}")
    print(f"  server : {server}")
    print(f"  preset : {preset}")
    print(f"  port   : {PORT}")
    print(f"  api    : http://127.0.0.1:{PORT}/v1")

    out_fh = open(out_log, "w", encoding="utf-8")
    err_fh = open(err_log, "w", encoding="utf-8")
    popen_kwargs: dict = {
        "cwd": str(server.parent),
        "stdout": out_fh,
        "stderr": err_fh,
    }
    if SYSTEM == "Windows":
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        # Detach from controlling terminal on Unix
        popen_kwargs["start_new_session"] = True

    try:
        subprocess.Popen(args, **popen_kwargs)
    finally:
        # Parent no longer needs these handles; child keeps its copies
        try:
            out_fh.close()
        except Exception:
            pass
        try:
            err_fh.close()
        except Exception:
            pass

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
    if err_log.is_file():
        print(err_log.read_text(encoding="utf-8", errors="replace")[-2000:])
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
    ap = argparse.ArgumentParser(description="Hermes local multi-model router (Atomic/Jan GGUFs)")
    ap.add_argument(
        "action",
        nargs="?",
        default="start",
        choices=["start", "stop", "restart", "status", "sync"],
    )
    ap.add_argument("--cpu", action="store_true", help="Force CPU (ngl 0)")
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
