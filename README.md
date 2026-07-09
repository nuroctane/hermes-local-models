# hermes-local-models

**Bridge Atomic Chat (Jan) GGUFs into [Hermes Agent](https://github.com/NousResearch/hermes-agent) / Hermes Desktop — runless multi-model list on a fixed OpenAI-compatible port.**

Download models in Atomic Chat. Start Hermes. Every finished GGUF appears in the model picker. Selecting one loads it on demand (one model in VRAM at a time). Cloud fallback stays available when the local router is down.

## Why this exists

Hermes does **not** load GGUF files. Atomic Chat stores them on disk and only exposes an API while its own UI has a model loaded (usually one at a time, dynamic port).

This repo:

1. **Scans** Atomic Chat’s model folder  
2. Builds a **llama-server router preset** (multi-model `/v1/models`)  
3. **Starts** that router on `http://127.0.0.1:8080/v1`  
4. Points Hermes at it as **primary**, with **cloud fallback**

## Requirements

- Windows (paths and Atomic Chat layout are Windows-oriented)
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) installed (`%LOCALAPPDATA%\hermes`)
- [Atomic Chat](https://atomic.chat/) (or Jan-compatible layout) with GGUFs under  
  `%APPDATA%\Atomic Chat\data\llamacpp\models\**\model.gguf`
- Python 3.10+ on PATH
- Atomic Chat’s bundled `llama-server.exe` (CUDA preferred; CPU fallback supported)

## Quick install

```powershell
git clone https://github.com/nuroctane/hermes-local-models.git
cd hermes-local-models
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

`install.ps1` will:

- Copy scripts into `%LOCALAPPDATA%\hermes\scripts\`
- Sync Atomic GGUFs → router preset
- Patch Hermes `config.yaml` (local primary + nvidia fallback; backs up first)
- Create **Startup** shortcut: *Hermes Local Model Router*
- Create **Desktop** shortcut: *Hermes Desktop (Local Models)*
- Start the router

CPU-only machines:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Cpu
```

Skip autostart of router during install:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -SkipStart
```

## Usage

| Action | Command / shortcut |
|--------|-------------------|
| Open Desktop with local models ready | Desktop: **Hermes Desktop (Local Models)** |
| Router only | `python %LOCALAPPDATA%\hermes\scripts\ensure_local_router.py start` |
| Status | `… ensure_local_router.py status` |
| After new Atomic download | `… ensure_local_router.py restart` |
| Stop | `… ensure_local_router.py stop` |
| Rescan only | `python %LOCALAPPDATA%\hermes\scripts\sync_atomic_models.py` |

List API:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/v1/models
```

Hermes CLI:

```powershell
hermes chat -m qwen3-coder
hermes chat -m gemma-3n
hermes model   # picker
```

## How new Atomic downloads show up

1. Finish download in Atomic Chat (no `model.gguf.tmp`).  
2. Restart router (`ensure_local_router.py restart`) **or** use the Desktop Local shortcut (re-syncs on start).  
3. New id appears in Hermes model list. First message loads weights (may take a while / free VRAM from previous model).

Incomplete downloads are ignored.

## Repo layout

```
hermes-local-models/
├── README.md
├── install.ps1
├── LICENSE
├── .gitignore
├── docs/
│   └── LOCAL_MODELS.md
└── scripts/
    ├── sync_atomic_models.py      # Atomic GGUF scan → preset + Hermes catalog
    ├── ensure_local_router.py     # start/stop multi-model llama-server router
    ├── start_hermes_desktop_local.py
    ├── patch_hermes_config.py     # local primary + cloud fallback
    └── start-hermes-local.ps1     # legacy single-model helper
```

## Hermes config shape (after install)

```yaml
model:
  default: qwen3-coder
  provider: custom
  base_url: http://127.0.0.1:8080/v1
  context_length: 65536

custom_providers:
  - name: atomic-local
    base_url: http://127.0.0.1:8080/v1
    models:
      qwen3-coder:
        context_length: 65536
      # …all discovered models

fallback_model:
  provider: nvidia
  model: nvidia/nemotron-3-ultra-550b-a55b
```

Adjust `fallback_model` to match a cloud provider you already authenticated in Hermes (`hermes model` / `auth.json`).

## Notes & limits

- **One heavy model in VRAM** by default (`--models-max 1`); switching models unloads the previous.
- Hermes Agent requires **≥ 64K** context reporting; presets use `ctx-size = 65536`.
- Tool-calling quality varies by model; coding-class GGUFs work best for agent loops.
- Cron / `no_agent` Hermes jobs do **not** use these models.
- This does not replace Atomic Chat; it reuses the same GGUF files and backends.

## Uninstall

1. `python %LOCALAPPDATA%\hermes\scripts\ensure_local_router.py stop`  
2. Remove Startup / Desktop shortcuts created by install.  
3. Delete `%LOCALAPPDATA%\hermes\scripts\{sync,ensure,start}_*.py` if desired.  
4. Restore `config.yaml` from `config.yaml.bak-before-local` if present.

## License

MIT — see [LICENSE](LICENSE).
