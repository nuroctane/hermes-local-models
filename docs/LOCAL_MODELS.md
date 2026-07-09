# Local models — runless Hermes (Windows + macOS)

**Goal:** Open Hermes and see **all finished Atomic Chat / Jan GGUFs**. Pick one; it loads on demand.

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
# Ensure router + Desktop
python3 ~/.hermes/scripts/start_hermes_desktop_local.py   # Mac
python  %LOCALAPPDATA%\hermes\scripts\start_hermes_desktop_local.py  # Win

# Router only
python3 ensure_local_router.py start|stop|status|restart
python3 ensure_local_router.py start --cpu
```

After a new GGUF download finishes: `ensure_local_router.py restart`.

## Architecture

See root README. Router = Atomic/Jan/Homebrew `llama-server` in multi-model preset mode on port 8080.
