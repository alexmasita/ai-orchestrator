#!/usr/bin/env bash
set -euo pipefail

# ============================================
# UNIVERSAL PATH DETECTION
# ============================================

BASE_DIR="/workspace"
if [ ! -d "$BASE_DIR" ]; then
    BASE_DIR="."
fi

SETUP_MARKER="$BASE_DIR/.setup_complete"
MODELS_DIR="$BASE_DIR/models"
STATE_FILE="$BASE_DIR/state.json"
CONTROL_PY="$BASE_DIR/control_api.py"

# ============================================
# PORT CONFIG
# ============================================

ARCHITECT_PORT="${AI_ORCH_ARCHITECT_PORT:-8080}"
DEVELOPER_PORT="${AI_ORCH_DEVELOPER_PORT:-8081}"
WHISPER_PORT="${AI_ORCH_STT_PORT:-9000}"
TTS_PORT="${AI_ORCH_TTS_PORT:-9001}"
CONTROL_PORT="${AI_ORCH_CONTROL_PORT:-7999}"

# ============================================
# RUNTIME CONFIG
# ============================================

WEBHOOK_URL="${WEBHOOK_URL:-}"
VAST_API_KEY="${CONTAINER_API_KEY:-${VAST_API_KEY:-}}"
IDLE_TIMEOUT_SECONDS="${AI_ORCH_IDLE_TIMEOUT_SECONDS:-1800}"

ARCHITECT_MODEL="${AI_ORCH_ARCHITECT_MODEL:-twhitworth/gpt-oss-120b-awq-w4a16}"
DEVELOPER_MODEL="${AI_ORCH_DEVELOPER_MODEL:-cyankiwi/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit}"

# ============================================
# STATE REPORTING
# ============================================

update_state() {

    local stage="$1"
    local status="$2"
    local message="$3"

    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    local instance_id="${VAST_CONTAINERLABEL:-unknown}"

cat > "$STATE_FILE" << EOF
{
    "instance_id": "$instance_id",
    "stage": "$stage",
    "status": "$status",
    "message": "$message",
    "timestamp": "$timestamp",
    "is_snapshot": $([ -f "$SETUP_MARKER" ] && echo "true" || echo "false"),
    "ports": {
        "architect": $ARCHITECT_PORT,
        "developer": $DEVELOPER_PORT,
        "stt": $WHISPER_PORT,
        "tts": $TTS_PORT,
        "control": $CONTROL_PORT
    }
}
EOF

echo "[VAST_STATE] $timestamp | stage=$stage | status=$status | $message"

}

# ============================================
# HEALTH CHECK
# ============================================

wait_for_port() {

    local port=$1
    local name=$2
    local max_wait=${3:-120}

    local waited=0

    update_state "${name}_health_check" "waiting" "Waiting for $name on port $port..."

    while ! curl -s http://localhost:$port >/dev/null 2>&1; do

        sleep 2
        waited=$((waited+2))

        if [ $waited -ge $max_wait ]; then

            update_state "${name}_health_check" "timeout" "$name did not respond on port $port after ${max_wait}s"
            return 1
        fi
    done

    update_state "${name}_health_check" "ready" "$name responding on port $port"
}

# ============================================
# CONTROL API
# ============================================

start_control_api() {

update_state "control_api" "starting" "Launching control API"

cat > "$CONTROL_PY" <<PY
from fastapi import FastAPI
from datetime import datetime, timezone
import json, os

app = FastAPI(title="Vast Instance Control API")

STATE_FILE = "$STATE_FILE"

@app.get("/status")
async def status():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {"status":"unknown"}
PY

pip install fastapi uvicorn httpx -q 2>/dev/null || true

cd "$BASE_DIR"

uvicorn control_api:app --host 0.0.0.0 --port $CONTROL_PORT &
update_state "control_api" "started" "Control API running on port $CONTROL_PORT"

}

# ============================================
# PHASE 1 SETUP
# ============================================

if [ ! -f "$SETUP_MARKER" ]; then

update_state "setup_start" "running" "Initial environment setup"

mkdir -p "$MODELS_DIR"

apt-get update
apt-get install -y ffmpeg curl python3-pip

pip install faster-whisper-server huggingface_hub kokoro-tts tomli -q
# Architect model

update_state "architect_download" "running" "Downloading architect model"
hf download "$ARCHITECT_MODEL" \
  --local-dir "$MODELS_DIR/architect"
update_state "architect_download" "complete" "Architect model downloaded"

# Developer model

update_state "developer_download" "running" "Downloading developer model"

hf download "$DEVELOPER_MODEL" \
  --local-dir "$MODELS_DIR/developer"

update_state "developer_download" "complete" "Developer model downloaded"

touch "$SETUP_MARKER"
update_state "setup_complete" "complete" "First time setup finished. Snapshot recommended."

fi

# ============================================
# PHASE 2 SERVE
# ============================================

update_state "services_starting" "running" "Starting all services"

# Control API

start_control_api

# Architect

update_state "architect_server" "starting" "Launching Architect vLLM on port $ARCHITECT_PORT"

vllm serve "$MODELS_DIR/architect" \
    --port $ARCHITECT_PORT \
    --gpu-memory-utilization 0.55 \
    --dtype float16 \
    --served-model-name architect &

# Developer

update_state "developer_server" "starting" "Launching Developer vLLM on port $DEVELOPER_PORT"

vllm serve "$MODELS_DIR/developer" \
    --port $DEVELOPER_PORT \
    --gpu-memory-utilization 0.25 \
    --dtype float16 \
    --served-model-name developer &

# STT

update_state "stt_server" "starting" "Launching faster-whisper-server (CPU) on port $WHISPER_PORT"

WHISPER__MODEL=large-v3 \
WHISPER__DEVICE=cpu \
WHISPER__COMPUTE_TYPE=int8 \
WHISPER__MODEL_DIR="$MODELS_DIR/whisper" \
uvicorn faster_whisper_server.main:app \
    --host 0.0.0.0 \
    --port $WHISPER_PORT &

# --- TTS ---
update_state "tts_server" "starting" "Launching Kokoro TTS on port $TTS_PORT"

python -m kokoro_fastapi \
  --host 0.0.0.0 \
  --port $TTS_PORT &

# Wait for readiness

wait_for_port $ARCHITECT_PORT "architect" 300 &
wait_for_port $DEVELOPER_PORT "developer" 300 &
wait_for_port $WHISPER_PORT "stt" 120 &
wait_for_port $TTS_PORT "tts" 120 &
wait

# ============================================
# FINAL READY STATE
# ============================================

update_state "all_services" "ready" \
"All services up. Architect:$ARCHITECT_PORT Developer:$DEVELOPER_PORT STT:$WHISPER_PORT Control:$CONTROL_PORT"

echo "============================================"
echo "  HIGH-REASONING 80GB DUO — ALL SERVICES READY"
echo "  Target: A100/H100 80GB"
echo "============================================"

echo "  Architect: http://localhost:$ARCHITECT_PORT"
echo "  Developer: http://localhost:$DEVELOPER_PORT"
echo "  STT:       http://localhost:$WHISPER_PORT"
echo "  Control:   http://localhost:$CONTROL_PORT"

echo ""
echo "  CONTROL API ENDPOINTS:"
echo "    GET  /status"
echo "    GET  /health"
echo ""
echo "  IDLE TIMEOUT: ${IDLE_TIMEOUT_SECONDS}s"
echo "============================================"

# Keep container alive

wait