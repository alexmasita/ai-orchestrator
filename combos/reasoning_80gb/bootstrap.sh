#!/usr/bin/env bash
set -e

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
# PORT CONFIGURATION (AI-Orchestrator aware)
# ============================================
ARCHITECT_PORT="${AI_ORCH_ARCHITECT_PORT:-8080}"
DEVELOPER_PORT="${AI_ORCH_DEVELOPER_PORT:-8081}"
WHISPER_PORT="${AI_ORCH_STT_PORT:-9000}"
TTS_PORT="${AI_ORCH_TTS_PORT:-9001}"
CONTROL_PORT="${AI_ORCH_CONTROL_PORT:-7999}"

# ============================================
# RUNTIME CONFIGURATION
# ============================================
WEBHOOK_URL="${WEBHOOK_URL:-}"

# Vast automatically injects CONTAINER_API_KEY
VAST_API_KEY="${CONTAINER_API_KEY:-${VAST_API_KEY:-}}"

IDLE_TIMEOUT_SECONDS="${AI_ORCH_IDLE_TIMEOUT_SECONDS:-${IDLE_TIMEOUT_SECONDS:-1800}}"

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

cat > "$STATE_FILE" << EOSTATE
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
EOSTATE

    echo "[VAST_STATE] $timestamp | stage=$stage | status=$status | $message"

    if [ -n "$WEBHOOK_URL" ]; then
        curl -s -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d @"$STATE_FILE" || true
    fi
}

# ============================================
# HEALTH CHECK HELPER
# ============================================
wait_for_port() {
    local port=$1
    local name=$2
    local max_wait=${3:-120}

    local waited=0

    update_state "${name}_health_check" "waiting" "Waiting for $name on port $port..."

    while ! curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port" | grep -qE "200|404|405"; do
        sleep 2
        waited=$((waited+2))

        if [ $waited -ge $max_wait ]; then
            update_state "${name}_health_check" "timeout" "$name did not respond on port $port after ${max_wait}s"
            return 1
        fi
    done

    update_state "${name}_health_check" "ready" "$name is responding on port $port"
}

# ============================================
# SELF DESTROY
# ============================================
self_destroy() {

    local instance_id="${VAST_CONTAINERLABEL:-}"

    update_state "auto_destroy" "triggered" "Idle timeout reached (${IDLE_TIMEOUT_SECONDS}s). Self destroying."

    if [ -n "$VAST_API_KEY" ] && [ -n "$instance_id" ]; then

        curl -s -X DELETE \
        "https://console.vast.ai/api/v0/instances/${instance_id}/" \
        -H "Authorization: Bearer $VAST_API_KEY" \
        -H "Content-Type: application/json" || true

        echo "[VAST_STATE] Self destroy request sent"

    else
        echo "[VAST_STATE] Cannot self destroy, API key missing"
    fi
}

# ============================================
# IDLE MONITOR
# ============================================
start_idle_monitor() {

if [ -z "$VAST_API_KEY" ]; then
    echo "[VAST_STATE] API key not set, idle destroy disabled"
    return
fi

echo "[VAST_STATE] Idle monitor started (${IDLE_TIMEOUT_SECONDS}s)"

(
LAST_ACTIVITY_FILE="/tmp/.last_activity"

date +%s > "$LAST_ACTIVITY_FILE"

while true; do

    sleep 30

    if [ -f "/tmp/.last_request" ]; then
        date +%s > "$LAST_ACTIVITY_FILE"
        rm -f "/tmp/.last_request"
    fi

    LAST=$(cat "$LAST_ACTIVITY_FILE")
    NOW=$(date +%s)

    IDLE=$((NOW-LAST))

    if [ $IDLE -ge $IDLE_TIMEOUT_SECONDS ]; then
        self_destroy
        exit 0
    fi

done
) &

}

# ============================================
# CONTROL API
# ============================================
start_control_api() {

update_state "control_api" "starting" "Launching control API"

cat > "$CONTROL_PY" << PYEOF
from fastapi import FastAPI
from datetime import datetime, timezone
import json, os

app = FastAPI(title="Vast Instance Control API")

STATE_FILE = "$STATE_FILE"
ACTIVITY_FILE = "/tmp/.last_request"

SERVICE_PORTS = {
 "architect": $ARCHITECT_PORT,
 "developer": $DEVELOPER_PORT,
 "stt": $WHISPER_PORT,
 "tts": $TTS_PORT,
}

@app.get("/status")
async def status():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {"status":"unknown"}

@app.get("/health")
async def health():
    import httpx
    results={}
    for name,port in SERVICE_PORTS.items():
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r=await client.get(f"http://localhost:{port}/health")
                results[name]={"status":"up","code":r.status_code}
        except:
            results[name]={"status":"down"}
    results["control"]={"status":"up"}
    open(ACTIVITY_FILE,"w").close()
    return {"services":results,"timestamp":datetime.now(timezone.utc).isoformat()}
PYEOF

pip install fastapi uvicorn httpx -q 2>/dev/null || true

cd "$BASE_DIR"
uvicorn control_api:app --host 0.0.0.0 --port $CONTROL_PORT &

update_state "control_api" "started" "Control API running"

}

# ============================================
# PHASE 1 SETUP
# ============================================
if [ ! -f "$SETUP_MARKER" ]; then

update_state "setup_start" "running" "Initial setup"

mkdir -p "$MODELS_DIR"

apt-get update
apt-get install -y ffmpeg python3-pip curl

pip install vllm faster-whisper-server fastapi uvicorn httpx huggingface_hub

update_state "architect_download" "running" "Downloading architect model"

huggingface-cli download "$ARCHITECT_MODEL" --local-dir "$MODELS_DIR/architect"

update_state "developer_download" "running" "Downloading developer model"

huggingface-cli download "$DEVELOPER_MODEL" --local-dir "$MODELS_DIR/developer"

docker pull ghcr.io/remsky/kokoro-fastapi-gpu:latest || true

touch "$SETUP_MARKER"

update_state "setup_complete" "complete" "Snapshot ready"

fi

update_state "services_starting" "running" "Starting all services"

# --- Control API ---
start_control_api

# --- Architect ---
update_state "architect_server" "starting" "Launching Architect vLLM on port $ARCHITECT_PORT"

vllm serve "$MODELS_DIR/architect" \
    --port $ARCHITECT_PORT \
    --gpu-memory-utilization 0.55 \
    --quantization awq \
    --dtype float16 \
    --trust-remote-code \
    --served-model-name architect &

# --- Developer ---
update_state "developer_server" "starting" "Launching Developer vLLM on port $DEVELOPER_PORT"

vllm serve "$MODELS_DIR/developer" \
    --port $DEVELOPER_PORT \
    --gpu-memory-utilization 0.25 \
    --quantization awq \
    --dtype float16 \
    --trust-remote-code \
    --served-model-name developer &

# --- STT ---
update_state "stt_server" "starting" "Launching faster-whisper-server (CPU) on port $WHISPER_PORT"

WHISPER__MODEL=large-v3 \
WHISPER__DEVICE=cpu \
WHISPER__COMPUTE_TYPE=int8 \
WHISPER__MODEL_DIR="$MODELS_DIR/whisper" \
uvicorn faster_whisper_server.main:app \
    --host 0.0.0.0 \
    --port $WHISPER_PORT &

# --- TTS ---
update_state "tts_server" "starting" "Launching kokoro-tts on port $TTS_PORT"

docker run -d --rm \
    --gpus all \
    --name kokoro-tts \
    -p ${TTS_PORT}:8880 \
    ghcr.io/remsky/kokoro-fastapi-gpu:latest || true


# --- Wait for readiness ---
wait_for_port $ARCHITECT_PORT "architect" 300 &
wait_for_port $DEVELOPER_PORT "developer" 300 &
wait_for_port $WHISPER_PORT "stt" 120 &
wait_for_port $TTS_PORT "tts" 120 &
wait


# --- Idle monitor ---
start_idle_monitor


# --- Final ready state ---
update_state "all_services" "ready" \
"All services up. Architect:$ARCHITECT_PORT Developer:$DEVELOPER_PORT STT:$WHISPER_PORT TTS:$TTS_PORT Control:$CONTROL_PORT"


echo "============================================"
echo "  HIGH-REASONING 80GB DUO — ALL SERVICES READY"
echo "  Target: A100/H100 80GB"
echo "============================================"
echo "  Architect (120B AWQ):  http://localhost:$ARCHITECT_PORT"
echo "  Developer (30B AWQ):   http://localhost:$DEVELOPER_PORT"
echo "  STT (Whisper CPU):     http://localhost:$WHISPER_PORT"
echo "  TTS (Kokoro GPU):      http://localhost:$TTS_PORT"
echo "  Control API:           http://localhost:$CONTROL_PORT"
echo ""
echo "  CONTROL API ENDPOINTS:"
echo "    GET  /status"
echo "    GET  /health"
echo "    POST /ping"
echo "    POST /stop"
echo "    POST /destroy"
echo ""
echo "  IDLE TIMEOUT: ${IDLE_TIMEOUT_SECONDS}s"
echo "============================================"

# Keep script alive
wait