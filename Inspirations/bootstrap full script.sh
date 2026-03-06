#!/usr/bin/env bash
set -e

SETUP_MARKER="/workspace/.setup_complete"
MODELS_DIR="/workspace/models"
LLAMA_DIR="/workspace/llama.cpp"
STATE_FILE="/workspace/state.json"
WHISPER_PORT=9000
DEEPSEEK_PORT=8080
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
        "deepseek": $DEEPSEEK_PORT,
        "whisper": $WHISPER_PORT,
        "control": $CONTROL_PORT
    }
}
EOF

    # Log to stdout (visible via `vastai logs <id>` or
    # GET /api/v0/instances/request_logs/{id})
    echo "[VAST_STATE] $timestamp | stage=$stage | status=$status | $message"

    # POST to webhook if configured
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
# CLI equivalent: vastai destroy instance <id>
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
        echo "[VAST_STATE] Set VAST_API_KEY env var when creating the instance."
    fi
}

# ============================================
# IDLE TIMEOUT MONITOR
# Watches both service ports for activity.
# Resets timer on any request. Destroys on timeout.
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

            # Check DeepSeek activity (llama-server /health returns slot info)
            DS_ACTIVE=$(curl -s "http://localhost:$DEEPSEEK_PORT/health" 2>/dev/null | grep -c "ok" || true)
            # Check Whisper activity
            WH_ACTIVE=$(curl -s "http://localhost:$WHISPER_PORT/health" 2>/dev/null | grep -c "ready" || true)

            # If either service got a recent request, update timestamp
            # We also check if /tmp/.last_request was touched by the control API
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
#
# Query remotely via:
#   vastai execute <id> "curl -s http://localhost:7999/status"
#   Or via: PUT /api/v0/instances/command/{id}/
#           {"command": "curl -s http://localhost:7999/status"}
# ============================================
start_control_api() {
    update_state "control_api" "starting" "Launching control API on port $CONTROL_PORT"

    cat > /workspace/control_api.py << 'PYEOF'
from fastapi import FastAPI
from datetime import datetime, timezone
import json, os, signal, subprocess

app = FastAPI(title="Vast Instance Control API")

STATE_FILE = "/workspace/state.json"
ACTIVITY_FILE = "/tmp/.last_request"

@app.get("/status")
async def status():
    """Return current instance state (pollable via vastai execute)."""
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {"status": "unknown", "error": "state file not found"}

@app.get("/health")
async def health():
    """Combined health check for all services."""
    import httpx
    results = {}
    for name, port in [("deepseek", 8080), ("whisper", 9000)]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"http://localhost:{port}/health")
                results[name] = {"status": "up", "code": r.status_code}
        except:
            results[name] = {"status": "down"}
    results["control"] = {"status": "up"}
    # Touch activity file to reset idle timer
    open(ACTIVITY_FILE, "w").close()
    return {"services": results, "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/ping")
async def ping():
    """Reset idle timer without doing anything else."""
    open(ACTIVITY_FILE, "w").close()
    return {"pong": True, "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/stop")
async def stop():
    """Stop this instance (sets state to stopped via Vast API).
    Uses: PUT /api/v0/instances/{id}/ {"state": "stopped"}
    """
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
    """Permanently destroy this instance.
    Uses: DELETE /api/v0/instances/{id}/
    WARNING: Irreversible. All data will be deleted.
    """
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
    update_state "setup_start" "running" "First-time setup beginning"

    # --- APT INSTALL ---
    update_state "apt_install" "running" "Installing system dependencies"
    apt-get update
    apt-get install -y libcurl4-openssl-dev ffmpeg python3-pip
    update_state "apt_install" "complete" "System dependencies installed"

    # --- BUILD LLAMA.CPP ---
    update_state "llama_build" "running" "Cloning and building llama.cpp with CUDA"
    git clone https://github.com/ggerganov/llama.cpp "$LLAMA_DIR"
    cmake "$LLAMA_DIR" -B "$LLAMA_DIR/build" \
        -DBUILD_SHARED_LIBS=OFF -DGGML_CUDA=ON -DLLAMA_CURL=ON
    cmake --build "$LLAMA_DIR/build" --config Release -j \
        --clean-first --target llama-server
    update_state "llama_build" "complete" "llama.cpp built successfully"

    # --- INSTALL PYTHON DEPS ---
    update_state "python_install" "running" "Installing Python dependencies"
    pip install faster-whisper fastapi uvicorn python-multipart httpx huggingface_hub
    update_state "python_install" "complete" "Python dependencies installed"

    # --- CREATE WHISPER API ---
    update_state "whisper_api_create" "running" "Creating Whisper API server script"
    cat > /workspace/whisper_api.py << 'PYEOF'
from fastapi import FastAPI, UploadFile, File
from faster_whisper import WhisperModel
import tempfile, os

app = FastAPI()
model = WhisperModel("large-v3", device="cuda", compute_type="float16",
                     download_root="/workspace/models/whisper")

@app.get("/health")
async def health():
    return {"status": "ready", "model": "whisper-large-v3"}

@app.post("/asr")
async def transcribe(file: UploadFile = File(...)):
    # Touch activity file to reset idle timer
    open("/tmp/.last_request", "w").close()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    segments, info = model.transcribe(tmp_path)
    text = " ".join([s.text for s in segments])
    os.unlink(tmp_path)
    return {"language": info.language, "text": text.strip()}

@app.post("/detect-language")
async def detect_language(file: UploadFile = File(...)):
    open("/tmp/.last_request", "w").close()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    _, info = model.transcribe(tmp_path)
    os.unlink(tmp_path)
    return {"language": info.language, "probability": info.language_probability}
PYEOF
    update_state "whisper_api_create" "complete" "Whisper API script created"

    # --- DOWNLOAD DEEPSEEK MODEL ---
    update_state "deepseek_download" "running" "Downloading DeepSeek model (this may take a while)"
    mkdir -p "$MODELS_DIR"
    huggingface-cli download unsloth/DeepSeek-R1-GGUF \
        --local-dir "$MODELS_DIR/deepseek"
    update_state "deepseek_download" "complete" "DeepSeek model downloaded"

    # --- PRE-DOWNLOAD WHISPER MODEL ---
    update_state "whisper_download" "running" "Pre-downloading Whisper large-v3 model"
    python3 -c "from faster_whisper import WhisperModel; WhisperModel('large-v3', device='cpu', download_root='/workspace/models/whisper')"
    update_state "whisper_download" "complete" "Whisper model downloaded"

    # --- MARK SETUP COMPLETE ---
    touch "$SETUP_MARKER"
    update_state "setup_complete" "complete" "First-time setup finished. TAKE A SNAPSHOT NOW via: vastai take snapshot <instance_id>"
fi

# ============================================
# PHASE 2: SERVE (runs every start, including after snapshot)
# ============================================
update_state "services_starting" "running" "Starting all services"

# --- Start Control API first (so you can poll status immediately) ---
start_control_api

# --- Start DeepSeek ---
update_state "deepseek_server" "starting" "Launching DeepSeek llama-server on port $DEEPSEEK_PORT"
"$LLAMA_DIR/build/bin/llama-server" \
    --model "$MODELS_DIR/deepseek/DeepSeek-R1.Q8_0-00001-of-00015.gguf" \
    --ctx-size 8192 \
    --n-gpu-layers 62 \
    --port $DEEPSEEK_PORT &

# --- Start Whisper ---
update_state "whisper_server" "starting" "Launching Whisper API on port $WHISPER_PORT"
cd /workspace
uvicorn whisper_api:app --host 0.0.0.0 --port $WHISPER_PORT &

# --- Wait for both services to be ready ---
wait_for_port $DEEPSEEK_PORT "deepseek" 180 &
wait_for_port $WHISPER_PORT "whisper" 120 &
wait

# --- Start idle monitor ---
start_idle_monitor

# --- Final ready state ---
update_state "all_services" "ready" "All services up. DeepSeek:$DEEPSEEK_PORT Whisper:$WHISPER_PORT Control:$CONTROL_PORT"

echo "============================================"
echo "  SERVICES READY"
echo "  DeepSeek:  http://localhost:$DEEPSEEK_PORT"
echo "  Whisper:   http://localhost:$WHISPER_PORT"
echo "  Control:   http://localhost:$CONTROL_PORT"
echo ""
echo "  CONTROL API ENDPOINTS:"
echo "    GET  /status   - Current instance state"
echo "    GET  /health   - All service health checks"
echo "    POST /ping     - Reset idle timer"
echo "    POST /stop     - Stop instance"
echo "    POST /destroy  - Destroy instance (IRREVERSIBLE)"
echo ""
echo "  IDLE TIMEOUT: ${IDLE_TIMEOUT_SECONDS}s"
echo "============================================"

# Keep script alive (so backgrounded processes don't get orphaned)
wait