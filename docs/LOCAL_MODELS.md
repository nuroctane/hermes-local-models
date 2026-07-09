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

## Mac smoke check

```bash
curl -s http://127.0.0.1:8080/v1/models | python3 -m json.tool
launchctl print gui/$(id -u)/xyz.nuroctane.hermes-local-router | head
tail -50 ~/.hermes/logs/local-router.err.log
open ~/Applications/Hermes\ Desktop\ Local\ Models.command
```

`stop` only kills a process whose command line contains `llama-server` (won’t nuke random apps on :8080).

Default Hermes model is taken from the discovered catalog (prefers `qwen3-coder`, then `gemma-3n`, else first id).

## Architecture

See root README. Router = Atomic/Jan/Homebrew `llama-server` in multi-model preset mode on port 8080.

## ADEs (Orca, etc.)

ADEs do **not** load GGUFs. They launch Hermes (or another CLI). After install, Hermes already points at `http://127.0.0.1:8080/v1`, so any ADE that can start Hermes inherits local models for free.

```
ADE → Hermes → localhost:8080 router → GGUFs
```

Full write-up: root [README.md](../README.md#ades-orca-and-any-hermes-capable-agent-ide) (Orca notes, checklist, caveats, optional OpenAI-compatible agents).
