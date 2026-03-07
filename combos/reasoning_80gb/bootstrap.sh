#!/usr/bin/env bash
set -euo pipefail

export PYTHONUNBUFFERED=1

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

if [ -n "$WEBHOOK_URL" ]; then
    curl -s -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d @"$STATE_FILE" || true
fi

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

    while ! curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port" | grep -qE "200|404|405"; do
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
# SELF DESTROY
# ============================================

self_destroy() {

    local instance_id="${VAST_CONTAINERLABEL:-}"
    update_state "auto_destroy" "triggered" "Idle timeout reached (${IDLE_TIMEOUT_SECONDS}s). Self-destroying."

    if [ -n "$VAST_API_KEY" ] && [ -n "$instance_id" ]; then
        curl -s -X DELETE \
        "https://console.vast.ai/api/v0/instances/${instance_id}/" \
        -H "Authorization: Bearer $VAST_API_KEY" \
        -H "Content-Type: application/json" || true

        echo "[VAST_STATE] Self-destroy request sent for instance $instance_id"
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

    cat > "$CONTROL_PY" <<PYEOF
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
        return {"status": "unknown", "error": "state file not found"}

@app.get("/health")
async def health():
    import httpx
    results={}
    for name,port in SERVICE_PORTS.items():
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r=await client.get(f"http://localhost:{port}")
                results[name]={"status":"up","code":r.status_code}
        except:
            results[name]={"status":"down"}
    results["control"]={"status":"up"}
    open(ACTIVITY_FILE,"w").close()
    return {"services":results,"timestamp":datetime.now(timezone.utc).isoformat()}

@app.post("/ping")
async def ping():
    open(ACTIVITY_FILE,"w").close()
    return {"pong": True, "timestamp": datetime.now(timezone.utc).isoformat()}
@app.post("/stop")
async def stop():
    api_key=os.environ.get("VAST_API_KEY","")
    instance_id=os.environ.get("VAST_CONTAINERLABEL","")
    if not api_key or not instance_id:
        return {"error":"missing api key"}
    import httpx
    async with httpx.AsyncClient() as client:
        r=await client.put(
            f"https://console.vast.ai/api/v0/instances/{instance_id}/",
            headers={"Authorization":f"Bearer {api_key}"},
            json={"state":"stopped"}
        )
        return {"action": "stop", "response": r.json()}

@app.post("/destroy")
async def destroy():
    api_key=os.environ.get("VAST_API_KEY","")
    instance_id=os.environ.get("VAST_CONTAINERLABEL","")
    if not api_key or not instance_id:
        return {"error":"missing api key"}
    import httpx
    async with httpx.AsyncClient() as client:
        r=await client.delete(
            f"https://console.vast.ai/api/v0/instances/{instance_id}/",
            headers={"Authorization":f"Bearer {api_key}"}
        )
        return {"action": "destroy", "response": r.json()}
PYEOF

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
    mkdir -p "$MODELS_DIR/whisper"
    mkdir -p "$MODELS_DIR/kokoro"

    update_state "apt_install" "running" "Installing system dependencies"
    apt-get update
    apt-get install -y ffmpeg curl python3-pip
    update_state "apt_install" "complete" "System dependencies installed"

    update_state "python_install" "running" "Installing vLLM, faster-whisper-server, and Python dependencies"
    pip install -q --no-cache-dir \
        vllm \
        faster-whisper \
        huggingface_hub \
        fastapi \
        uvicorn \
        httpx \
        tomli

    update_state "python_install" "complete" "Python dependencies installed"

    update_state "architect_download" "running" "Downloading architect model"
    hf download "$ARCHITECT_MODEL" --local-dir "$MODELS_DIR/architect"
    update_state "architect_download" "complete" "Architect model downloaded"

    update_state "developer_download" "running" "Downloading developer model"
    hf download "$DEVELOPER_MODEL" --local-dir "$MODELS_DIR/developer"
    update_state "developer_download" "complete" "Developer model downloaded"

    touch "$SETUP_MARKER"
    update_state "setup_complete" "complete" "First time setup finished. Snapshot recommended."

fi

# ============================================
# PHASE 2 SERVE
# ============================================

update_state "services_starting" "running" "Starting all services"

start_control_api

update_state "architect_server" "starting" "Launching Architect vLLM on port $ARCHITECT_PORT"
vllm serve "$MODELS_DIR/architect" \
    --port $ARCHITECT_PORT \
    --gpu-memory-utilization 0.55 \
    --max-model-len 8192 \
    --dtype float16 \
    --served-model-name architect &

wait_for_port $ARCHITECT_PORT "architect" 300

update_state "developer_server" "starting" "Launching Developer vLLM on port $DEVELOPER_PORT"
vllm serve "$MODELS_DIR/developer" \
    --port $DEVELOPER_PORT \
    --gpu-memory-utilization 0.25 \
    --max-model-len 8192 \
    --dtype float16 \
    --served-model-name developer &

update_state "stt_server" "starting" "Launching Faster-Whisper STT on port $WHISPER_PORT"

cat > "$BASE_DIR/stt_server.py" <<PY
from faster_whisper import WhisperModel
from fastapi import FastAPI, UploadFile, File
import tempfile

model = WhisperModel("large-v3", device="cpu", compute_type="int8")

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/v1/audio/transcriptions")
async def transcribe(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(await file.read())
        path=f.name

    segments,_ = model.transcribe(path)

    text=" ".join([s.text for s in segments])

    return {"text":text}
PY

uvicorn stt_server:app \
    --host 0.0.0.0 \
    --port $WHISPER_PORT &

update_state "tts_server" "starting" "Launching Kokoro TTS on port $TTS_PORT"

cd "$BASE_DIR"

if [ ! -d "kokoro-fastapi" ]; then
    git clone https://github.com/remsky/Kokoro-FastAPI.git kokoro-fastapi
fi

cd kokoro-fastapi

pip install -q uv

uv pip install -e ".[gpu]" || true

python docker/scripts/download_model.py --output api/src/models/v1_0

uvicorn api.src.main:app \
    --host 0.0.0.0 \
    --port $TTS_PORT &

wait_for_port $ARCHITECT_PORT "architect" 300 &
wait_for_port $DEVELOPER_PORT "developer" 300 &
wait_for_port $WHISPER_PORT "stt" 120 &
wait_for_port $TTS_PORT "tts" 120 &
wait

start_idle_monitor

update_state "all_services" "ready" \
"All services up. Architect:$ARCHITECT_PORT Developer:$DEVELOPER_PORT STT:$WHISPER_PORT TTS:$TTS_PORT Control:$CONTROL_PORT"

echo "============================================"
echo " HIGH-REASONING 80GB DUO — ALL SERVICES READY"
echo "============================================"
echo " Architect: http://localhost:$ARCHITECT_PORT"
echo " Developer: http://localhost:$DEVELOPER_PORT"
echo " STT:       http://localhost:$WHISPER_PORT"
echo " TTS:       http://localhost:$TTS_PORT"
echo " Control:   http://localhost:$CONTROL_PORT"
echo ""
echo " CONTROL API:"
echo "   GET  /status"
echo "   GET  /health"
echo "   POST /ping"
echo "   POST /stop"
echo "   POST /destroy"
echo ""
echo "  IDLE TIMEOUT: ${IDLE_TIMEOUT_SECONDS}s"
echo "============================================"

wait