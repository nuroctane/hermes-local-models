# Local models — runless Hermes Desktop

**Goal:** Open Hermes and see **all finished Atomic Chat GGUFs**. Pick one; it loads on demand.

## Architecture

```
Atomic Chat downloads GGUFs
        |
        v  sync_atomic_models.py
  models-preset.ini
        |
        v  ensure_local_router.py
  llama-server ROUTER  http://127.0.0.1:8080/v1
  GET /v1/models -> every finished GGUF
  chat model X  -> loads that GGUF (max 1 in VRAM)
        |
        v
  Hermes Desktop / CLI (custom provider)
```

## Install

See root [README.md](../README.md).

## Day-to-day

```powershell
# One-click Desktop
python $env:LOCALAPPDATA\hermes\scripts\start_hermes_desktop_local.py

# Or ensure router only
python $env:LOCALAPPDATA\hermes\scripts\ensure_local_router.py start
python $env:LOCALAPPDATA\hermes\scripts\ensure_local_router.py status
python $env:LOCALAPPDATA\hermes\scripts\ensure_local_router.py restart
python $env:LOCALAPPDATA\hermes\scripts\ensure_local_router.py stop
```

After a new Atomic download finishes (no `.tmp`):

```powershell
python $env:LOCALAPPDATA\hermes\scripts\ensure_local_router.py restart
```

## Paths

| Item | Path |
|------|------|
| Scripts | `%LOCALAPPDATA%\hermes\scripts\` |
| Preset | `%LOCALAPPDATA%\hermes\local-models\models-preset.ini` |
| Catalog | `%LOCALAPPDATA%\hermes\local-models\catalog.json` |
| Logs | `%LOCALAPPDATA%\hermes\logs\local-router.*.log` |
| Atomic GGUFs | `%APPDATA%\Atomic Chat\data\llamacpp\models\` |
| llama-server | Atomic Chat CUDA/CPU backends |

## Hermes config

- Primary: `custom` → `http://127.0.0.1:8080/v1`
- Default model: `qwen3-coder` (when present)
- Context: `65536` (Hermes agent minimum)
- Fallback: cloud (e.g. nvidia) if router is down
