#!/usr/bin/env bash
set -e

SETUP_MARKER="/workspace/.setup_complete"
MODELS_DIR="/workspace/models"
STATE_FILE="/workspace/state.json"
WHISPER_PORT=9000
TTS_PORT=9001
ARCHITECT_PORT=8080
DEVELOPER_PORT=8081
CONTROL_PORT=7999

# ============================================
# CONFIG (set as env vars when creating instance)
# WEBHOOK_URL=https://your-app.com/api/vast-status
# VAST_API_KEY=your_api_key_here
# IDLE_TIMEOUT_SECONDS=1800  (default 30 min)
# ============================================
WEBHOOK_URL="${WEBHOOK_URL:-}"
VAST_API_KEY="${VAST_API_KEY:-}"
IDLE_TIMEOUT_SECONDS="${IDLE_TIMEOUT_SECONDS:-1800}"

# Model repos
ARCHITECT_MODEL="twhitworth/gpt-oss-120b-awq-w4a16"
DEVELOPER_MODEL="cyankiwi/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit"

# ============================================
# STATE REPORTING FUNCTIONS
# ============================================
update_state() {
    local stage="$1"
    local status="$2"
    local message="$3"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
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
# HEALTH CHECK HELPERS
# ============================================
wait_for_port() {
    local port=$1
    local name=$2
    local max_wait=${3:-120}
    local waited=0

    update_state "${name}_health_check" "waiting" "Waiting for $name on port $port..."

    while ! curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port" | grep -qE "200|404|405"; do
        sleep 2
        waited=$((waited + 2))
        if [ $waited -ge $max_wait ]; then
            update_state "${name}_health_check" "timeout" "$name did not respond on port $port after ${max_wait}s"
            return 1
        fi
    done

    update_state "${name}_health_check" "ready" "$name is responding on port $port"
    return 0
}

# ============================================
# SELF-DESTROY FUNCTION
# Uses: DELETE /api/v0/instances/{id}/
# ============================================
self_destroy() {
    local instance_id="${VAST_CONTAINERLABEL:-}"
    update_state "auto_destroy" "triggered" "Idle timeout reached (${IDLE_TIMEOUT_SECONDS}s). Self-destroying."

    if [ -n "$VAST_API_KEY" ] && [ -n "$instance_id" ]; then
        curl -s -X DELETE "https://console.vast.ai/api/v0/instances/${instance_id}/" \
            -H "Authorization: Bearer $VAST_API_KEY" \
            -H "Content-Type: application/json" || true
        echo "[VAST_STATE] Self-destroy request sent for instance $instance_id"
    else
        echo "[VAST_STATE] ERROR: Cannot self-destroy. VAST_API_KEY or instance ID missing."
    fi
}

# ============================================
# IDLE TIMEOUT MONITOR
# Watches all 4 service ports for activity.
# ============================================
start_idle_monitor() {
    if [ -z "$VAST_API_KEY" ]; then
        echo "[VAST_STATE] VAST_API_KEY not set — idle auto-destroy DISABLED"
        return
    fi

    echo "[VAST_STATE] Idle monitor started. Timeout: ${IDLE_TIMEOUT_SECONDS}s"

    (
        LAST_ACTIVITY_FILE="/tmp/.last_activity"
        date +%s > "$LAST_ACTIVITY_FILE"

        while true; do
            sleep 30

            # Check if any service got a recent request via control API /ping or /health
            if [ -f "/tmp/.last_request" ]; then
                date +%s > "$LAST_ACTIVITY_FILE"
                rm -f "/tmp/.last_request"
            fi

            LAST_ACTIVITY=$(cat "$LAST_ACTIVITY_FILE" 2>/dev/null || date +%s)
            NOW=$(date +%s)
            IDLE_SECONDS=$((NOW - LAST_ACTIVITY))

            if [ $IDLE_SECONDS -ge $IDLE_TIMEOUT_SECONDS ]; then
                self_destroy
                exit 0
            fi
        done
    ) &
    IDLE_MONITOR_PID=$!
    echo "[VAST_STATE] Idle monitor PID: $IDLE_MONITOR_PID"
}

# ============================================
# CONTROL API (port 7999)
# Provides: /status, /health, /ping, /stop, /destroy
# ============================================
start_control_api() {
    update_state "control_api" "starting" "Launching control API on port $CONTROL_PORT"

    cat > /workspace/control_api.py << 'PYEOF'
from fastapi import FastAPI
from datetime import datetime, timezone
import json, os

app = FastAPI(title="Vast Instance Control API — High-Reasoning 80GB Duo")

STATE_FILE = "/workspace/state.json"
ACTIVITY_FILE = "/tmp/.last_request"

SERVICE_PORTS = {
    "architect": 8080,
    "developer": 8081,
    "stt": 9000,
    "tts": 9001,
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
    results = {}
    for name, port in SERVICE_PORTS.items():
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"http://localhost:{port}/health")
                results[name] = {"status": "up", "code": r.status_code}
        except:
            results[name] = {"status": "down"}
    results["control"] = {"status": "up"}
    open(ACTIVITY_FILE, "w").close()
    return {"services": results, "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/ping")
async def ping():
    open(ACTIVITY_FILE, "w").close()
    return {"pong": True, "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/stop")
async def stop():
    api_key = os.environ.get("VAST_API_KEY", "")
    instance_id = os.environ.get("VAST_CONTAINERLABEL", "")
    if not api_key or not instance_id:
        return {"error": "VAST_API_KEY or instance ID not available"}
    import httpx
    async with httpx.AsyncClient() as client:
        r = await client.put(
            f"https://console.vast.ai/api/v0/instances/{instance_id}/",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"state": "stopped"}
        )
        return {"action": "stop", "response": r.json()}

@app.post("/destroy")
async def destroy():
    api_key = os.environ.get("VAST_API_KEY", "")
    instance_id = os.environ.get("VAST_CONTAINERLABEL", "")
    if not api_key or not instance_id:
        return {"error": "VAST_API_KEY or instance ID not available"}
    import httpx
    async with httpx.AsyncClient() as client:
        r = await client.delete(
            f"https://console.vast.ai/api/v0/instances/{instance_id}/",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        return {"action": "destroy", "response": r.json()}
PYEOF

    pip install httpx -q 2>/dev/null || true
    cd /workspace
    uvicorn control_api:app --host 0.0.0.0 --port $CONTROL_PORT &
    update_state "control_api" "started" "Control API on port $CONTROL_PORT"
}

# ============================================
# PHASE 1: ONE-TIME SETUP (skipped after snapshot)
# ============================================
if [ ! -f "$SETUP_MARKER" ]; then
    update_state "setup_start" "running" "First-time setup beginning (High-Reasoning 80GB Duo)"

    # --- APT INSTALL ---
    update_state "apt_install" "running" "Installing system dependencies"
    apt-get update
    apt-get install -y ffmpeg python3-pip curl
    update_state "apt_install" "complete" "System dependencies installed"

    # --- INSTALL PYTHON DEPS ---
    update_state "python_install" "running" "Installing vLLM, faster-whisper-server, and Python dependencies"
    pip install vllm faster-whisper-server fastapi uvicorn httpx huggingface_hub
    update_state "python_install" "complete" "Python dependencies installed"

    # --- DOWNLOAD ARCHITECT MODEL ---
    update_state "architect_download" "running" "Downloading Architect model: $ARCHITECT_MODEL"
    mkdir -p "$MODELS_DIR"

    # Ensure subdirectories exist for all model families
    mkdir -p "$MODELS_DIR/whisper"
    mkdir -p "$MODELS_DIR/kokoro"

    if [ ! -d "$MODELS_DIR/architect" ] || [ -z "$(ls -A "$MODELS_DIR/architect" 2>/dev/null)" ]; then
        huggingface-cli download "$ARCHITECT_MODEL" \
            --local-dir "$MODELS_DIR/architect"
    else
        echo "[VAST_STATE] Architect model already present, skipping download."
    fi
    update_state "architect_download" "complete" "Architect model downloaded"

    # --- DOWNLOAD DEVELOPER MODEL ---
    update_state "developer_download" "running" "Downloading Developer model: $DEVELOPER_MODEL"
    if [ ! -d "$MODELS_DIR/developer" ] || [ -z "$(ls -A "$MODELS_DIR/developer" 2>/dev/null)" ]; then
        huggingface-cli download "$DEVELOPER_MODEL" \
            --local-dir "$MODELS_DIR/developer"
    else
        echo "[VAST_STATE] Developer model already present, skipping download."
    fi
    update_state "developer_download" "complete" "Developer model downloaded"

    # --- PULL KOKORO-TTS DOCKER IMAGE ---
    update_state "tts_pull" "running" "Pulling kokoro-tts Docker image"
    docker pull ghcr.io/remsky/kokoro-fastapi-gpu:latest || true
    update_state "tts_pull" "complete" "Kokoro-TTS image pulled"

    # --- MARK SETUP COMPLETE ---
    touch "$SETUP_MARKER"
    update_state "setup_complete" "complete" "First-time setup finished. TAKE A SNAPSHOT NOW via: vastai create instance --template_hash <hash>"
fi

# ============================================
# PHASE 2: SERVE (runs every start, including after snapshot)
# ============================================
update_state "services_starting" "running" "Starting all 4 services + control API"

# --- Start Control API first ---
start_control_api

# --- Start Architect LLM (vLLM, port 8080) ---
update_state "architect_server" "starting" "Launching Architect vLLM on port $ARCHITECT_PORT"
vllm serve "$MODELS_DIR/architect" \
    --port $ARCHITECT_PORT \
    --gpu-memory-utilization 0.45 \
    --quantization awq \
    --dtype float16 \
    --trust-remote-code \
    --served-model-name architect &

# --- Start Developer LLM (vLLM, port 8081) ---
update_state "developer_server" "starting" "Launching Developer vLLM on port $DEVELOPER_PORT"
vllm serve "$MODELS_DIR/developer" \
    --port $DEVELOPER_PORT \
    --gpu-memory-utilization 0.45 \
    --quantization awq \
    --dtype float16 \
    --trust-remote-code \
    --served-model-name developer &

# --- Start STT: faster-whisper-server on CPU (port 9000) ---
update_state "stt_server" "starting" "Launching faster-whisper-server (CPU) on port $WHISPER_PORT"
WHISPER__MODEL=large-v3 \
WHISPER__DEVICE=cpu \
WHISPER__COMPUTE_TYPE=int8 \
WHISPER__MODEL_DIR="$MODELS_DIR/whisper" \
uvicorn faster_whisper_server.main:app \
    --host 0.0.0.0 \
    --port $WHISPER_PORT &

# --- Start TTS: kokoro-tts via Docker on GPU (port 9001) ---
update_state "tts_server" "starting" "Launching kokoro-tts (GPU Docker) on port $TTS_PORT"
docker run -d --rm \
    --gpus all \
    --name kokoro-tts \
    -p ${TTS_PORT}:8880 \
    ghcr.io/remsky/kokoro-fastapi-gpu:latest || true

# --- Wait for ALL 4 services to be ready ---
wait_for_port $ARCHITECT_PORT "architect" 300 &
wait_for_port $DEVELOPER_PORT "developer" 300 &
wait_for_port $WHISPER_PORT "stt" 120 &
wait_for_port $TTS_PORT "tts" 120 &
wait

# --- Start idle monitor ---
start_idle_monitor

# --- Final ready state ---
update_state "all_services" "ready" "All services up. Architect:$ARCHITECT_PORT Developer:$DEVELOPER_PORT STT:$WHISPER_PORT TTS:$TTS_PORT Control:$CONTROL_PORT"

echo "============================================"
echo "  HIGH-REASONING 80GB DUO — ALL SERVICES READY"
echo "  Target: A100/H100 80GB"
echo "============================================"
echo "  Architect (120B AWQ):  http://localhost:$ARCHITECT_PORT  (0.45 VRAM)"
echo "  Developer (30B AWQ):   http://localhost:$DEVELOPER_PORT  (0.45 VRAM)"
echo "  STT (Whisper CPU):     http://localhost:$WHISPER_PORT"
echo "  TTS (Kokoro GPU):      http://localhost:$TTS_PORT"
echo "  Control API:           http://localhost:$CONTROL_PORT"
echo ""
echo "  CONTROL API ENDPOINTS:"
echo "    GET  /status   - Current instance state"
echo "    GET  /health   - All 4 service health checks"
echo "    POST /ping     - Reset idle timer"
echo "    POST /stop     - Stop instance (via Vast API)"
echo "    POST /destroy  - Destroy instance (IRREVERSIBLE)"
echo ""
echo "  IDLE TIMEOUT: ${IDLE_TIMEOUT_SECONDS}s"
echo "============================================"

# Keep script alive
wait