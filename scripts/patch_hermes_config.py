#!/usr/bin/env python3
"""Idempotently wire Hermes config for local primary + cloud fallback (cross-platform)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import hermes_paths, preferred_default_model  # noqa: E402


def load_catalog_ids() -> list[str]:
    catalog = hermes_paths()["catalog"]
    if not catalog.is_file():
        return []
    try:
        data = json.loads(catalog.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [e["id"] for e in data if isinstance(e, dict) and e.get("id")]
    except Exception:
        pass
    return []


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

    catalog_ids = load_catalog_ids()
    default_id = preferred_default_model(catalog_ids)
    if catalog_ids:
        print(f"Default model from catalog: {default_id} ({len(catalog_ids)} models)")
    else:
        print(f"No catalog yet; default model: {default_id}")

    # Build models block for custom_providers
    if catalog_ids:
        models_yaml = "\n".join(
            f"      {mid}:\n        context_length: 65536" for mid in catalog_ids
        )
    else:
        models_yaml = (
            "      qwen3-coder:\n"
            "        context_length: 65536\n"
            "      gemma-3n:\n"
            "        context_length: 65536"
        )

    new_model = (
        "model:\n"
        f"  default: {default_id}\n"
        "  provider: custom\n"
        "  base_url: http://127.0.0.1:8080/v1\n"
        "  # Hermes agent requires >= 64K reported context window\n"
        "  context_length: 65536\n"
    )
    m = re.search(r"^model:\n(?:  .*\n)*?(?=^agent:)", text, re.M)
    if m:
        text = text[: m.start()] + new_model + text[m.end() :]
        print(f"Updated model: primary -> local custom :8080 (default={default_id})")
    else:
        # Try looser: just replace default under model if present
        if re.search(r"^model:\n  default: ", text, re.M):
            text = re.sub(
                r"^(model:\n  default: )\S+",
                rf"\g<1>{default_id}",
                text,
                count=1,
                flags=re.M,
            )
            print(f"Updated model.default -> {default_id} (loose match)")
        else:
            print("Warning: could not locate model: block")

    if "name: atomic-local" not in text:
        text = (
            text.rstrip()
            + f"""

# Local Atomic Chat / Jan bridge (hermes-local-models)
custom_providers:
  - name: atomic-local
    base_url: http://127.0.0.1:8080/v1
    models:
{models_yaml}

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
    else:
        # Keep default in sync when re-running patch after catalog exists
        text = re.sub(
            r"^(model:\n  default: )\S+",
            rf"\g<1>{default_id}",
            text,
            count=1,
            flags=re.M,
        )

    config.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {config}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
