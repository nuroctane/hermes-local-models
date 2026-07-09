#!/usr/bin/env python3
"""Idempotently wire Hermes config for local primary + cloud fallback."""
from __future__ import annotations

import os
import re
from pathlib import Path

CONFIG = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / "config.yaml"
BACKUP = CONFIG.with_suffix(".yaml.bak-before-local")


def main() -> int:
    if not CONFIG.is_file():
        print(f"No Hermes config at {CONFIG} — install Hermes first.")
        return 1

    text = CONFIG.read_text(encoding="utf-8")
    if not BACKUP.exists():
        BACKUP.write_text(text, encoding="utf-8")
        print(f"Backup: {BACKUP}")

    # Ensure model block points at local router
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

    # Ensure custom_providers + fallback exist
    if "name: atomic-local" not in text:
        text = text.rstrip() + """

# Local Atomic Chat bridge (hermes-local-models)
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
        print("Appended custom_providers + fallback_model")
    elif "fallback_model:" not in text or re.search(
        r"^# fallback_model:", text, re.M
    ):
        # Only commented fallback exists — append live one if no live block
        if not re.search(r"^fallback_model:\n  provider:", text, re.M):
            text = text.rstrip() + """

fallback_model:
  provider: nvidia
  model: nvidia/nemotron-3-ultra-550b-a55b
"""
            print("Appended fallback_model")

    CONFIG.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {CONFIG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
