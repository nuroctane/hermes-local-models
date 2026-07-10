# hermes-local-models

**Auto-wire [Hermes Agent](https://github.com/NousResearch/hermes-agent) / Hermes Desktop to [llama.cpp](https://github.com/ggml-org/llama.cpp) (`llama-server`).**

This repo discovers finished **Atomic Chat / Jan GGUFs**, runs a multi-model **OpenAI-compatible** router on `localhost:8080`, and patches Hermes so local llama.cpp is the **primary** backend (with **cloud fallback**). No manual model paths in Hermes — pick a model; weights load on demand.

Works on **Windows** and **macOS** (Linux paths supported too).

**Custom provider id:** `auto-llamacpp` (formerly `atomic-local`)

**ADEs included:** Install once, then any Agent Development Environment that can launch Hermes (Orca, and friends) inherits the same local llama.cpp stack — no per-ADE model host.

## Why this exists

Hermes does **not** load GGUF files itself. Atomic Chat / Jan (and Homebrew llama.cpp) provide `llama-server` + weights on disk. This bridge:

1. **Scans** local GGUF folders (Atomic Chat + Jan layouts)
2. Builds a **llama-server multi-model preset** (`/v1/models` lists all)
3. **Starts** llama.cpp’s OpenAI-compatible server on `http://127.0.0.1:8080/v1`
4. Points Hermes at it as **primary** (`auto-llamacpp`), with **cloud fallback**

```
Hermes (CLI / Desktop / ADE)
    →  custom provider auto-llamacpp
        →  http://127.0.0.1:8080/v1
            →  llama-server (llama.cpp)
                →  Atomic Chat / Jan GGUFs
```

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

`install.sh` on Mac also installs a **LaunchAgent** so the llama.cpp router can start at login, plus  
`~/Applications/Hermes Desktop (Auto llama.cpp).command`.

## Usage

| Action | Command |
|--------|---------|
| Ensure router + open Desktop | `python3 start_hermes_desktop_local.py` (or Scripts / Applications launcher) |
| Start / stop / status | `python3 ensure_local_router.py start\|stop\|status\|restart` |
| After new Atomic/Jan download | `python3 ensure_local_router.py restart` |
| Rescan only | `python3 sync_atomic_models.py` |

List models (llama-server):

```bash
curl -s http://127.0.0.1:8080/v1/models | python3 -m json.tool
```

Hermes CLI (uses `auto-llamacpp` primary):

```bash
hermes chat -m qwen3-coder
hermes chat -m gemma-3n
hermes model
```

## How new downloads show up

1. Finish the download in Atomic Chat / Jan (no `.tmp`).  
2. Restart the router (`ensure_local_router.py restart`) **or** use the Auto llama.cpp Desktop launcher (re-syncs).  
3. New id appears in Hermes; first message loads weights via llama.cpp (may swap off the previous model).

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
    ├── sync_atomic_models.py       # GGUF scan → models-preset.ini
    ├── ensure_local_router.py      # start/stop llama-server
    ├── start_hermes_desktop_local.py
    ├── patch_hermes_config.py      # wires auto-llamacpp + fallback
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
  - name: auto-llamacpp
    base_url: http://127.0.0.1:8080/v1
    models: { …discovered… }

fallback_model:
  provider: nvidia
  model: nvidia/nemotron-3-ultra-550b-a55b
```

Re-running install/`patch_hermes_config.py` renames legacy **`atomic-local`** → **`auto-llamacpp`**.  
Change `fallback_model` to any cloud provider you’ve already set up in Hermes.

## ADEs (Orca and any Hermes-capable agent IDE)

**Agent Development Environments do not host models.** They launch coding agents. Local inference stays with this llama.cpp router + Hermes `auto-llamacpp` config; the ADE just runs Hermes.

```
ADE (Orca, …)  →  Hermes CLI / Desktop
                      →  auto-llamacpp → http://127.0.0.1:8080/v1
                           →  llama-server (llama.cpp) → GGUFs
```

### One install, every ADE

1. Run `install.ps1` / `install.sh` (router + Hermes `config.yaml` patch).
2. Keep the router up (`ensure_local_router.py start` or login Startup/LaunchAgent).
3. Confirm models: `curl -s http://127.0.0.1:8080/v1/models`.
4. In any ADE that supports **Hermes Agent**, start Hermes on a worktree — same global Hermes home (`%LOCALAPPDATA%\hermes` / `~/.hermes`) and therefore the same auto-llamacpp primary + cloud fallback.

No Orca-specific plugin is required.

### [Orca](https://www.onorca.dev/docs)

- Orca is **not a model provider** — bring your own agent.
- **Hermes Agent** is a supported/preconfigured CLI.
- Launch Hermes from the agent picker. Same local catalog as outside Orca.

### Other ADEs / CLIs

| Path | How local models work |
|------|------------------------|
| ADE → **Hermes** | Prefer this. Install once; every Hermes launch is auto-llamacpp-ready. |
| Agent with **OpenAI-compatible** custom base URL | Point at `http://127.0.0.1:8080/v1` (same llama-server). Hermes is auto-patched; other agents are manual. |

### ADE checklist

- [ ] Router healthy (`ensure_local_router.py status` / `curl …/v1/models`)
- [ ] Hermes works outside the ADE (`hermes chat -m <id>` or Auto llama.cpp launcher)
- [ ] ADE can find the Hermes binary on PATH
- [ ] If traffic goes to cloud only: check router is up and `fallback_model` is not the only path

### ADE caveats

- **VRAM:** default is one heavy model loaded (`--models-max 1`). Many parallel Hermes sessions may swap models.
- **Remote/SSH worktrees:** `127.0.0.1:8080` is on the machine running the router. Tunnel or run the router on the remote host if agents run elsewhere.
- **Tool quality** still depends on the local model, not the ADE.

## Platform notes

### macOS

- Prefer **Metal** via Homebrew `llama-server` or Atomic/Jan mac backends (`-ngl 99`). Backend discovery ranks Metal/Apple over CPU.
- Hermes home is **`~/.hermes`**, not LocalAppData (override with `HERMES_HOME`).
- LaunchAgent label: `xyz.nuroctane.hermes-local-router` under `~/Library/LaunchAgents/`.
  Uses an **absolute Python path** and a Homebrew-friendly `PATH` so login start works.
- Unload agent:
  ```bash
  launchctl bootout gui/$(id -u)/xyz.nuroctane.hermes-local-router
  # older macOS:
  launchctl unload ~/Library/LaunchAgents/xyz.nuroctane.hermes-local-router.plist
  ```
- Desktop launch uses `open /path/App.app` (not `open -a` with a full path).

#### Mac smoke check (first install)

```bash
# 1) llama-server lists models
curl -s http://127.0.0.1:8080/v1/models | python3 -m json.tool

# 2) LaunchAgent registered
launchctl print gui/$(id -u)/xyz.nuroctane.hermes-local-router | head -40

# 3) Logs if something fails
tail -50 ~/.hermes/logs/local-router.err.log
tail -50 ~/.hermes/logs/launchagent-router.err.log

# 4) Desktop launcher
open ~/Applications/Hermes\ Desktop\ \(Auto\ llama.cpp\).command
```

If step 1 fails: `brew install llama.cpp`, set `LLAMA_SERVER` if needed, then  
`python3 ~/.hermes/scripts/ensure_local_router.py restart`.

### Windows

- Uses Atomic Chat CUDA backend when present; `-Cpu` / `--cpu` forces CPU build.
- `install.ps1` creates Startup **Hermes Auto llama.cpp Router** plus  
  **`%USERPROFILE%\Scripts\Hermes Desktop (Auto llama.cpp).lnk`** (not Desktop).

## Limits

- One heavy model in VRAM by default (`--models-max 1`).
- Hermes Agent wants **≥ 64K** context reporting; presets use `65536`.
- Tool-calling quality varies by model.
- Does not replace Atomic Chat / Jan — reuses their GGUFs and (when present) llama.cpp backends; can also use a system/`brew` `llama-server`.

## Uninstall

1. `python3 ensure_local_router.py stop`  
2. Remove Startup / LaunchAgent / Auto llama.cpp launchers.  
3. Restore `config.yaml` from `config.yaml.bak-before-local` if present.  
4. Delete installed scripts under Hermes `scripts/` if desired.

## License

MIT — see [LICENSE](LICENSE).
