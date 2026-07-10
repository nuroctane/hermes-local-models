# Auto llama.cpp — Hermes local models (Windows + macOS)

**Goal:** Hermes automatically uses **llama.cpp** (`llama-server`) for finished Atomic Chat / Jan GGUFs. Open Hermes, pick a model; it loads on demand.

**Provider id:** `auto-llamacpp` (legacy name `atomic-local` is renamed on re-patch)

## Paths by OS

| | Windows | macOS |
|--|---------|--------|
| Hermes home | `%LOCALAPPDATA%\hermes` | `~/.hermes` |
| Models | `%APPDATA%\Atomic Chat\data\llamacpp\models` | `~/Library/Application Support/Atomic Chat/data/llamacpp/models` or `…/Jan/data/llamacpp/models` |
| Scripts (after install) | `%LOCALAPPDATA%\hermes\scripts` | `~/.hermes/scripts` |
| Preset | `…/local-models/models-preset.ini` | same under Hermes home |

Overrides: `HERMES_HOME`, `ATOMIC_MODELS_DIR`, `JAN_MODELS_DIR`, `LLAMA_SERVER`, `HERMES_LOCAL_PORT`.

## Install

- Windows: `install.ps1`
- macOS/Linux: `install.sh` (see root README)

## Day-to-day

```bash
# Ensure llama-server router + Desktop
python3 ~/.hermes/scripts/start_hermes_desktop_local.py   # Mac
python  %LOCALAPPDATA%\hermes\scripts/start_hermes_desktop_local.py  # Win

# Router only
python3 ensure_local_router.py start|stop|status|restart
python3 ensure_local_router.py start --cpu
```

After a new GGUF download finishes: `ensure_local_router.py restart`.

## Mac smoke check

```bash
curl -s http://127.0.0.1:8080/v1/models | python3 -m json.tool
launchctl print gui/$(id -u)/xyz.nuroctane.hermes-local-router | head
tail -50 ~/.hermes/logs/local-router.err.log
open ~/Applications/Hermes\ Desktop\ \(Auto\ llama.cpp\).command
```

`stop` only kills a process whose command line contains `llama-server` (won’t nuke random apps on :8080).

Default Hermes model is taken from the discovered catalog (prefers `qwen3-coder`, then `gemma-3n`, else first id).

## Architecture

```
Hermes → auto-llamacpp → :8080 → llama-server (llama.cpp) → GGUFs
```

See root README. Router = Atomic/Jan/Homebrew `llama-server` in multi-model preset mode on port 8080.

## ADEs (Orca, etc.)

ADEs do **not** load GGUFs. They launch Hermes. After install, Hermes already points at `http://127.0.0.1:8080/v1` via **auto-llamacpp**, so any ADE that can start Hermes inherits local llama.cpp for free.

Full write-up: root [README.md](../README.md#ades-orca-and-any-hermes-capable-agent-ide).
