#!/usr/bin/env bash
# Install hermes-local-models on macOS / Linux into Hermes home.
# Usage:
#   chmod +x install.sh
#   ./install.sh
#   ./install.sh --cpu --skip-start --no-shortcuts
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
DEST="$HERMES_HOME/scripts"
DOCS="$HERMES_HOME"
PY="${PYTHON:-python3}"

NO_SHORTCUTS=0
CPU=0
SKIP_START=0
for arg in "$@"; do
  case "$arg" in
    --no-shortcuts) NO_SHORTCUTS=1 ;;
    --cpu) CPU=1 ;;
    --skip-start) SKIP_START=1 ;;
    -h|--help)
      echo "Usage: ./install.sh [--cpu] [--skip-start] [--no-shortcuts]"
      exit 0
      ;;
  esac
done

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "ERROR: $PY not found. Install Python 3.10+."
  exit 1
fi

mkdir -p "$DEST"
for f in sync_atomic_models.py ensure_local_router.py start_hermes_desktop_local.py \
         patch_hermes_config.py paths.py start-hermes-local.ps1; do
  if [[ -f "$REPO_ROOT/scripts/$f" ]]; then
    cp -f "$REPO_ROOT/scripts/$f" "$DEST/$f"
    echo "Installed $f -> $DEST"
  fi
done
chmod +x "$DEST"/*.py 2>/dev/null || true

cp -f "$REPO_ROOT/docs/LOCAL_MODELS.md" "$DOCS/LOCAL_MODELS.md"
echo "Installed LOCAL_MODELS.md -> $DOCS"

"$PY" "$DEST/sync_atomic_models.py" || true
"$PY" "$DEST/patch_hermes_config.py"

if [[ "$NO_SHORTCUTS" -eq 0 ]]; then
  # LaunchAgent for login autostart (macOS)
  if [[ "$(uname -s)" == "Darwin" ]]; then
    LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
    mkdir -p "$LAUNCH_AGENTS"
    PLIST="$LAUNCH_AGENTS/xyz.nuroctane.hermes-local-router.plist"
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>xyz.nuroctane.hermes-local-router</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>$DEST/ensure_local_router.py</string>
    <string>start</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <false/>
  <key>WorkingDirectory</key>
  <string>$DEST</string>
  <key>StandardOutPath</key>
  <string>$HERMES_HOME/logs/launchagent-router.out.log</string>
  <key>StandardErrorPath</key>
  <string>$HERMES_HOME/logs/launchagent-router.err.log</string>
</dict>
</plist>
EOF
    mkdir -p "$HERMES_HOME/logs"
    launchctl unload "$PLIST" 2>/dev/null || true
    launchctl load "$PLIST" 2>/dev/null || launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null || true
    echo "LaunchAgent: $PLIST"

    # Optional Desktop-ish command in ~/Applications isn't always available;
    # drop a small launcher in ~/bin if present, else print open command.
    APP_SCRIPT="$HOME/Applications/Hermes Desktop Local Models.command"
    mkdir -p "$HOME/Applications"
    cat > "$APP_SCRIPT" <<EOF
#!/bin/bash
cd "$DEST"
exec "$PY" "$DEST/start_hermes_desktop_local.py"
EOF
    chmod +x "$APP_SCRIPT"
    echo "Launcher: $APP_SCRIPT"
  else
    # Linux: user systemd unit optional
    UNIT_DIR="$HOME/.config/systemd/user"
    mkdir -p "$UNIT_DIR"
    UNIT="$UNIT_DIR/hermes-local-router.service"
    cat > "$UNIT" <<EOF
[Unit]
Description=Hermes local multi-model router (Atomic/Jan GGUFs)
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$DEST
ExecStart=$PY $DEST/ensure_local_router.py start
ExecStop=$PY $DEST/ensure_local_router.py stop

[Install]
WantedBy=default.target
EOF
    systemctl --user daemon-reload 2>/dev/null || true
    systemctl --user enable --now hermes-local-router.service 2>/dev/null || true
    echo "systemd user unit: $UNIT (enable if systemctl available)"
  fi
fi

if [[ "$SKIP_START" -eq 0 ]]; then
  if [[ "$CPU" -eq 1 ]]; then
    "$PY" "$DEST/ensure_local_router.py" start --cpu
  else
    "$PY" "$DEST/ensure_local_router.py" start
  fi
fi

echo ""
echo "Install complete (Unix)."
echo "  Hermes home: $HERMES_HOME"
echo "  Docs:        $DOCS/LOCAL_MODELS.md"
echo "  API:         http://127.0.0.1:8080/v1/models"
echo "  Start:       python3 $DEST/ensure_local_router.py start"
echo ""
echo "macOS tip: brew install llama.cpp   # if Atomic/Jan backends missing"
echo "Models:    ~/Library/Application Support/Atomic Chat/data/llamacpp/models"
echo "       or  ~/Library/Application Support/Jan/data/llamacpp/models"
