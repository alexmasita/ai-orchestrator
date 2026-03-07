#!/usr/bin/env bash
set -e

# ============================================
# UNIVERSAL PATH DETECTION
# ============================================
# Use /workspace if it exists (Vast.ai), otherwise use current directory (Local/Mac)
BASE_DIR="/workspace"
if [ ! -d "$BASE_DIR" ]; then
    BASE_DIR="."
fi

SETUP_MARKER="$BASE_DIR/.setup_complete"
MODELS_DIR="$BASE_DIR/models"
STATE_FILE="$BASE_DIR/state.json"
CONTROL_PY="$BASE_DIR/control_api.py"

# Ports controlled by AI-Orchestrator (fallback defaults)
ARCHITECT_PORT="${AI_ORCH_ARCHITECT_PORT:-8080}"
DEVELOPER_PORT="${AI_ORCH_DEVELOPER_PORT:-8081}"
WHISPER_PORT="${AI_ORCH_STT_PORT:-9000}"
TTS_PORT="${AI_ORCH_TTS_PORT:-9001}"
CONTROL_PORT="${AI_ORCH_CONTROL_PORT:-7999}"

# Runtime configuration
WEBHOOK_URL="${WEBHOOK_URL:-}"
VAST_API_KEY="${CONTAINER_API_KEY:-${VAST_API_KEY:-}}"
IDLE_TIMEOUT_SECONDS="${AI_ORCH_IDLE_TIMEOUT:-${IDLE_TIMEOUT_SECONDS:-1800}}"
ARCHITECT_MODEL="${AI_ORCH_ARCHITECT_MODEL:-twhitworth/gpt-oss-120b-awq-w4a16}"
DEVELOPER_MODEL="${AI_ORCH_DEVELOPER_MODEL:-cyankiwi/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit}"

# ============================================
# STATE REPORTING FUNCTIONS
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
        echo "[VAST_STATE] ERROR: Cannot self-destroy. API key or instance ID missing."
    fi
}

# ============================================
# IDLE TIMEOUT MONITOR
# ============================================
start_idle_monitor() {
    if [ -z "$VAST_API_KEY" ]; then
        echo "[VAST_STATE] API key not set - idle auto-destroy DISABLED"
        return
    fi

    echo "[VAST_STATE] Idle monitor started. Timeout: ${IDLE_TIMEOUT_SECONDS}s"

    (
        LAST_ACTIVITY_FILE="/tmp/.last_activity"
        date +%s > "$LAST_ACTIVITY_FILE"

        while true; do
            sleep 30
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
# ============================================
start_control_api() {
    update_state "control_api" "starting" "Launching control API on port $CONTROL_PORT"

    # Pass the BASE_DIR into the Python script dynamically
    cat > "$CONTROL_PY" << PYEOF
from fastapi import FastAPI
from datetime import datetime, timezone
import json, os

app = FastAPI(title="Vast Instance Control API - High-Reasoning 80GB Duo")

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
    except Exception:
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
        except Exception:
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
    api_key = os.environ.get("VAST_API_KEY", "") or os.environ.get("CONTAINER_API_KEY", "")
    instance_id = os.environ.get("VAST_CONTAINERLABEL", "")
    if not api_key or not instance_id:
        return {"error": "API key or instance ID not available"}
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
    api_key = os.environ.get("VAST_API_KEY", "") or os.environ.get("CONTAINER_API_KEY", "")
    instance_id = os.environ.get("VAST_CONTAINERLABEL", "")
    if not api_key or not instance_id:
        return {"error": "API key or instance ID not available"}
    import httpx
    async with httpx.AsyncClient() as client:
        r = await client.delete(
            f"https://console.vast.ai/api/v0/instances/{instance_id}/",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        return {"action": "destroy", "response": r.json()}
PYEOF

    pip install httpx uvicorn fastapi -q 2>/dev/null || true
    # Run uvicorn from the detected BASE_DIR
    cd "$BASE_DIR"
    uvicorn control_api:app --host 0.0.0.0 --port $CONTROL_PORT &
    update_state "control_api" "started" "Control API on port $CONTROL_PORT"
}

# ============================================
# PHASE 1: ONE-TIME SETUP
# ============================================
if [ ! -f "$SETUP_MARKER" ]; then
    update_state "setup_start" "running" "First-time setup beginning"
    
    # Create models dir if missing
    mkdir -p "$MODELS_DIR"

    # Only run apt-get if on Debian/Ubuntu (skip on Mac)
    if command -v apt-get >/dev/null; then
        update_state "apt_install" "running" "Installing system dependencies"
        apt-get update
        apt-get install -y ffmpeg python3-pip curl
    fi
    
    # Mark setup as complete
    touch "$SETUP_MARKER"
    update_state "setup_complete" "success" "Base environment ready"
fi

# ============================================
# EXECUTION
# ============================================
start_control_api
start_idle_monitor

# Keep script alive for logs
wait
