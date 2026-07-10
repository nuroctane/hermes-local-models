#!/usr/bin/env python3
"""Cross-platform paths for Hermes auto-llamacpp (Atomic Chat / Jan GGUFs + llama-server)."""
from __future__ import annotations

import os
import platform
import shutil
import stat
from pathlib import Path

SYSTEM = platform.system()  # Windows | Darwin | Linux


def hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME", "").strip()
    if env:
        return Path(env).expanduser()
    if SYSTEM == "Windows":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "hermes"
    # macOS / Linux CLI default
    return Path.home() / ".hermes"


def app_support() -> Path:
    """User app-data root (Windows APPDATA, macOS Application Support, Linux XDG)."""
    if SYSTEM == "Windows":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base)
    if SYSTEM == "Darwin":
        return Path.home() / "Library" / "Application Support"
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    if xdg:
        return Path(xdg)
    return Path.home() / ".local" / "share"


def candidate_model_roots() -> list[Path]:
    """Possible GGUF roots for Atomic Chat and Jan (nested llamacpp/models)."""
    support = app_support()
    names = [
        "Atomic Chat",
        "AtomicChat",
        "Jan",
        "jan",
    ]
    roots: list[Path] = []
    for name in names:
        roots.append(support / name / "data" / "llamacpp" / "models")
        roots.append(support / name / "llamacpp" / "models")
    # Explicit env override
    env = os.environ.get("ATOMIC_MODELS_DIR") or os.environ.get("JAN_MODELS_DIR")
    if env:
        roots.insert(0, Path(env).expanduser())
    # Dedup preserve order
    seen: set[str] = set()
    out: list[Path] = []
    for r in roots:
        key = str(r)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def find_model_roots() -> list[Path]:
    return [r for r in candidate_model_roots() if r.is_dir()]


def preferred_default_model(model_ids: list[str]) -> str:
    """Pick Hermes default model id from discovered catalog (prefer Qwen, then Gemma)."""
    ids = list(model_ids)
    for prefer in ("qwen3-coder", "gemma-3n", "laguna-xs"):
        if prefer in ids:
            return prefer
    return ids[0] if ids else "qwen3-coder"


def _backend_rank(path: Path) -> tuple[int, str]:
    """
    Higher rank = better default backend.
    Prefer GPU/Metal/CUDA over CPU; avoid pure-cpu when accelerators exist.
    """
    s = str(path).lower().replace("\\", "/")
    rank = 50
    if any(tok in s for tok in ("metal", "apple", "vulkan", "hip", "rocm")):
        rank = 100
    elif "cuda" in s:
        rank = 90
    elif "cpu" in s and "cuda" not in s and "metal" not in s:
        rank = 10
    # Homebrew / system PATH binaries are good fallbacks on Mac
    if "/opt/homebrew/" in s or "/usr/local/bin/" in s:
        rank = max(rank, 80)
    return (rank, s)


def _is_runnable_binary(path: Path) -> bool:
    if not path.is_file():
        return False
    if SYSTEM == "Windows":
        return path.suffix.lower() in (".exe", "") or path.name.lower().endswith("llama-server.exe")
    try:
        st = path.stat()
        if st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            return True
        # Some app bundles drop binaries without +x; still try if regular file
        return path.stat().st_size > 0
    except OSError:
        return False


def find_llama_server(prefer_cpu: bool = False) -> Path | None:
    """Locate llama-server binary (Atomic/Jan backends, PATH, Homebrew)."""
    # Explicit override
    env = os.environ.get("LLAMA_SERVER", "").strip()
    if env and Path(env).is_file():
        return Path(env)

    support = app_support()
    app_names = ["Atomic Chat", "AtomicChat", "Jan", "jan"]
    candidates: list[Path] = []

    if SYSTEM == "Windows":
        # Known Windows Atomic backends (CUDA first unless prefer_cpu)
        cuda = (
            support
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
        cpu = (
            support
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
        if prefer_cpu:
            candidates += [cpu, cuda]
        else:
            candidates += [cuda, cpu]
        # Upstream backends folder (any version)
        for base in [
            support / "Atomic Chat" / "data" / "llamacpp" / "backends",
            support / "Atomic Chat" / "data" / "llamacpp-upstream" / "backends",
        ]:
            if base.is_dir():
                candidates += sorted(base.rglob("llama-server.exe"), reverse=True)
    else:
        # macOS / Linux: bundled backends under app support
        for name in app_names:
            for base in [
                support / name / "data" / "llamacpp" / "backends",
                support / name / "data" / "llamacpp-upstream" / "backends",
                support / name / "llamacpp" / "backends",
            ]:
                if base.is_dir():
                    candidates += list(base.rglob("llama-server"))
        # Homebrew / PATH
        for name in ("llama-server", "llama-server.exe"):
            which = shutil.which(name)
            if which:
                candidates.append(Path(which))
        for brew in (
            Path("/opt/homebrew/bin/llama-server"),
            Path("/usr/local/bin/llama-server"),
        ):
            candidates.append(brew)

    # Dedup, filter runnable, rank
    seen: set[str] = set()
    ranked: list[tuple[tuple[int, str], Path]] = []
    for c in candidates:
        try:
            key = str(c.resolve()) if c.exists() else str(c)
        except OSError:
            key = str(c)
        if key in seen:
            continue
        seen.add(key)
        if not _is_runnable_binary(c):
            continue
        rank = _backend_rank(c)
        if prefer_cpu:
            # Invert: prefer cpu paths
            s = str(c).lower()
            if "cpu" in s and "cuda" not in s and "metal" not in s:
                rank = (200, rank[1])
            else:
                rank = (rank[0] // 2, rank[1])
        ranked.append((rank, c))

    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[0][1]


def hermes_paths() -> dict[str, Path]:
    home = hermes_home()
    return {
        "home": home,
        "scripts": home / "scripts",
        "local_models": home / "local-models",
        "preset": home / "local-models" / "models-preset.ini",
        "catalog": home / "local-models" / "catalog.json",
        "config": home / "config.yaml",
        "logs": home / "logs",
        "out_log": home / "logs" / "local-router.out.log",
        "err_log": home / "logs" / "local-router.err.log",
    }
