# hermes-local-models

**Bridge Atomic Chat / Jan GGUFs into [Hermes Agent](https://github.com/NousResearch/hermes-agent) / Hermes Desktop — multi-model OpenAI-compatible router on `localhost:8080` with cloud fallback.**

Works on **Windows** and **macOS** (Linux paths supported too). Download models in Atomic Chat or Jan → start Hermes → every finished GGUF appears in the model picker. Selecting one loads it on demand (one model in VRAM at a time by default).

## Why this exists

Hermes does **not** load GGUF files. Atomic Chat / Jan store them on disk. This repo:

1. **Scans** local GGUF folders (Atomic Chat + Jan layouts)
2. Builds a **llama-server multi-model preset** (`/v1/models` lists all)
3. **Starts** the router on `http://127.0.0.1:8080/v1`
4. Points Hermes at it as **primary**, with **cloud fallback**

## Requirements

| | Windows | macOS |
|--|---------|--------|
| Hermes | `%LOCALAPPDATA%\hermes` | `~/.hermes` (or `HERMES_HOME`) |
| Models | Atomic Chat under `%APPDATA%\Atomic Chat\data\llamacpp\models` | `~/Library/Application Support/Atomic Chat/data/llamacpp/models` **or** `…/Jan/data/llamacpp/models` |
| llama-server | Bundled in Atomic Chat backends | Atomic/Jan backends **or** `brew install llama.cpp` |
| Python | 3.10+ on PATH | `python3` 3.10+ |

Optional env overrides:

| Variable | Purpose |
|----------|---------|
| `HERMES_HOME` | Hermes config/scripts home |
| `ATOMIC_MODELS_DIR` / `JAN_MODELS_DIR` | Force models root |
| `LLAMA_SERVER` | Force path to `llama-server` binary |
| `HERMES_LOCAL_PORT` | Router port (default `8080`) |

## Quick install

### Windows

```powershell
git clone https://github.com/nuroctane/hermes-local-models.git
cd hermes-local-models
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

CPU-only: `.\install.ps1 -Cpu`  
Skip starting router: `.\install.ps1 -SkipStart`

### macOS

```bash
git clone https://github.com/nuroctane/hermes-local-models.git
cd hermes-local-models
chmod +x install.sh
./install.sh
```

If Atomic/Jan didn’t bundle a router-capable `llama-server`:

```bash
brew install llama.cpp
# Metal is enabled by default on Apple Silicon
./install.sh
```

Options: `./install.sh --cpu` · `./install.sh --skip-start` · `./install.sh --no-shortcuts`

`install.sh` on Mac also installs a **LaunchAgent** so the router can start at login, plus  
`~/Applications/Hermes Desktop Local Models.command`.

## Usage

| Action | Command |
|--------|---------|
| Ensure router + open Desktop | `python3 start_hermes_desktop_local.py` (or Desktop / Applications launcher) |
| Start / stop / status | `python3 ensure_local_router.py start\|stop\|status\|restart` |
| After new Atomic/Jan download | `python3 ensure_local_router.py restart` |
| Rescan only | `python3 sync_atomic_models.py` |

List models:

```bash
curl -s http://127.0.0.1:8080/v1/models | python3 -m json.tool
```

Hermes CLI:

```bash
hermes chat -m qwen3-coder
hermes chat -m gemma-3n
hermes model
```

## How new downloads show up

1. Finish the download in Atomic Chat / Jan (no `.tmp`).  
2. Restart the router (`ensure_local_router.py restart`) **or** use the Desktop Local launcher (re-syncs).  
3. New id appears in Hermes; first message loads weights (may swap off the previous model).

## Repo layout

```
hermes-local-models/
├── README.md
├── install.ps1          # Windows
├── install.sh           # macOS / Linux
├── LICENSE
├── docs/LOCAL_MODELS.md
└── scripts/
    ├── paths.py                    # cross-platform discovery
    ├── sync_atomic_models.py
    ├── ensure_local_router.py
    ├── start_hermes_desktop_local.py
    ├── patch_hermes_config.py
    └── start-hermes-local.ps1      # legacy single-model (Windows)
```

## Hermes config (after install)

```yaml
model:
  default: qwen3-coder
  provider: custom
  base_url: http://127.0.0.1:8080/v1
  context_length: 65536

custom_providers:
  - name: atomic-local
    base_url: http://127.0.0.1:8080/v1
    models: { …discovered… }

fallback_model:
  provider: nvidia
  model: nvidia/nemotron-3-ultra-550b-a55b
```

Change `fallback_model` to any cloud provider you’ve already set up in Hermes.

## Platform notes

### macOS

- Prefer **Metal** via Homebrew `llama-server` or Atomic/Jan mac backends (`-ngl 99`).
- Hermes home is **`~/.hermes`**, not LocalAppData.
- LaunchAgent label: `xyz.nuroctane.hermes-local-router` under `~/Library/LaunchAgents/`.
- Unload agent: `launchctl unload ~/Library/LaunchAgents/xyz.nuroctane.hermes-local-router.plist`

### Windows

- Uses Atomic Chat CUDA backend when present; `-Cpu` / `--cpu` forces CPU build.
- Startup + Desktop `.lnk` shortcuts from `install.ps1`.

## Limits

- One heavy model in VRAM by default (`--models-max 1`).
- Hermes Agent wants **≥ 64K** context reporting; presets use `65536`.
- Tool-calling quality varies by model.
- Does not replace Atomic Chat / Jan — reuses their GGUFs and (when present) backends.

## Uninstall

1. `python3 ensure_local_router.py stop`  
2. Remove Startup / LaunchAgent / Desktop launchers.  
3. Restore `config.yaml` from `config.yaml.bak-before-local` if present.  
4. Delete installed scripts under Hermes `scripts/` if desired.

## License

MIT — see [LICENSE](LICENSE).
