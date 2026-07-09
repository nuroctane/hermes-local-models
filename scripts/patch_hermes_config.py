#!/usr/bin/env python3
"""Idempotently wire Hermes config for local primary + cloud fallback (cross-platform)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import hermes_paths  # noqa: E402


def main() -> int:
    hp = hermes_paths()
    config = hp["config"]
    backup = config.with_suffix(".yaml.bak-before-local")

    if not config.is_file():
        print(f"No Hermes config at {config} — install Hermes first.")
        print("  Windows: %LOCALAPPDATA%\\hermes")
        print("  macOS/Linux: ~/.hermes  (or set HERMES_HOME)")
        return 1

    text = config.read_text(encoding="utf-8")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")
        print(f"Backup: {backup}")

    new_model = """model:
  default: qwen3-coder
  provider: custom
  base_url: http://127.0.0.1:8080/v1
  # Hermes agent requires >= 64K reported context window
  context_length: 65536
"""
    m = re.search(r"^model:\n(?:  .*\n)*?(?=^agent:)", text, re.M)
    if m:
        text = text[: m.start()] + new_model + text[m.end() :]
        print("Updated model: primary -> local custom :8080")
    else:
        print("Warning: could not locate model: block")

    if "name: atomic-local" not in text:
        text = (
            text.rstrip()
            + """

# Local Atomic Chat / Jan bridge (hermes-local-models)
custom_providers:
  - name: atomic-local
    base_url: http://127.0.0.1:8080/v1
    models:
      qwen3-coder:
        context_length: 65536
      gemma-3n:
        context_length: 65536

fallback_model:
  provider: nvidia
  model: nvidia/nemotron-3-ultra-550b-a55b
"""
        )
        print("Appended custom_providers + fallback_model")
    elif not re.search(r"^fallback_model:\n  provider:", text, re.M):
        text = (
            text.rstrip()
            + """

fallback_model:
  provider: nvidia
  model: nvidia/nemotron-3-ultra-550b-a55b
"""
        )
        print("Appended fallback_model")

    config.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {config}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
