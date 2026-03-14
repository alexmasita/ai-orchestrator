#!/usr/bin/env bash
set -euo pipefail

export PYTHONUNBUFFERED=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export VLLM_CPU_KVCACHE_SPACE=4

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

INTERPRET_PORT="${AI_ORCH_INTERPRET_PORT:-8080}"
REASONER_PORT="${AI_ORCH_REASONER_PORT:-8081}"
RERANK_PORT="${AI_ORCH_RERANK_PORT:-8082}"
STT_PORT="${AI_ORCH_STT_PORT:-9000}"
TTS_PORT="${AI_ORCH_TTS_PORT:-9001}"
CONTROL_PORT="${AI_ORCH_CONTROL_PORT:-7999}"

# ============================================
# RUNTIME CONFIG
# ============================================

WEBHOOK_URL="${WEBHOOK_URL:-}"
VAST_API_KEY="${CONTAINER_API_KEY:-${VAST_API_KEY:-}}"
IDLE_TIMEOUT_SECONDS="${AI_ORCH_IDLE_TIMEOUT_SECONDS:-1800}"

INTERPRET_MODEL="${AI_ORCH_INTERPRET_MODEL:-Qwen/Qwen3-32B-AWQ}"
REASONER_MODEL="${AI_ORCH_REASONER_MODEL:-openai/gpt-oss-20b}"
RERANK_MODEL="${AI_ORCH_RERANK_MODEL:-BAAI/bge-reranker-v2-m3}"
STT_MODEL="${AI_ORCH_STT_MODEL:-turbo}"
TTS_MODEL="${AI_ORCH_TTS_MODEL:-hexgrad/Kokoro-82M}"

ENABLE_REASONER="${AI_ORCH_ENABLE_REASONER:-1}"
ENABLE_RERANK="${AI_ORCH_ENABLE_RERANK:-1}"
ENABLE_STT="${AI_ORCH_ENABLE_STT:-1}"
ENABLE_TTS="${AI_ORCH_ENABLE_TTS:-1}"

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
        "interpret": $INTERPRET_PORT,
        "reasoner": $REASONER_PORT,
        "rerank": $RERANK_PORT,
        "stt": $STT_PORT,
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
    "interpret": $INTERPRET_PORT,
    "reasoner": $REASONER_PORT,
    "rerank": $RERANK_PORT,
    "stt": $STT_PORT,
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
    mkdir -p "$MODELS_DIR/interpret"
    mkdir -p "$MODELS_DIR/reasoner"
    mkdir -p "$MODELS_DIR/rerank"
    mkdir -p "$MODELS_DIR/whisper"
    mkdir -p "$MODELS_DIR/kokoro"

    update_state "apt_install" "running" "Installing system dependencies"
    apt-get update
    apt-get install -y espeak-ng ffmpeg curl git python3-pip python3-venv
    update_state "apt_install" "complete" "System dependencies installed"

    update_state "python_install" "running" "Installing NeuroFlow AI runtime dependencies"
    pip install -q --no-cache-dir \
        vllm \
        faster-whisper \
        huggingface_hub \
        fastapi \
        uvicorn \
        httpx \
        tomli \
        python-multipart
    update_state "python_install" "complete" "Python dependencies installed"

    update_state "interpret_download" "running" "Downloading interpret model"
    hf download "$INTERPRET_MODEL" \
        --local-dir "$MODELS_DIR/interpret" \
        --include "config.json" \
        --include "generation_config.json" \
        --include "tokenizer.json" \
        --include "tokenizer_config.json" \
        --include "merges.txt" \
        --include "vocab.json" \
        --include "model.safetensors.index.json" \
        --include "model-*.safetensors"
    rm -rf "$MODELS_DIR/interpret/.cache"
    update_state "interpret_download" "complete" "Interpret model downloaded"

    if [ "$ENABLE_REASONER" = "1" ]; then
        update_state "reasoner_download" "running" "Downloading reasoner model"
        hf download "$REASONER_MODEL" \
            --local-dir "$MODELS_DIR/reasoner" \
            --include "config.json" \
            --include "generation_config.json" \
            --include "chat_template.jinja" \
            --include "tokenizer.json" \
            --include "tokenizer_config.json" \
            --include "special_tokens_map.json" \
            --include "model.safetensors.index.json" \
            --include "model-*.safetensors"
        rm -rf "$MODELS_DIR/reasoner/.cache"
        update_state "reasoner_download" "complete" "Reasoner model downloaded"
    fi

    if [ "$ENABLE_RERANK" = "1" ]; then
        update_state "rerank_download" "running" "Downloading rerank model"
        hf download "$RERANK_MODEL" \
            --local-dir "$MODELS_DIR/rerank" \
            --include "config.json" \
            --include "model.safetensors" \
            --include "sentencepiece.bpe.model" \
            --include "tokenizer.json" \
            --include "tokenizer_config.json" \
            --include "special_tokens_map.json"
        rm -rf "$MODELS_DIR/rerank/.cache"
        update_state "rerank_download" "complete" "Rerank model downloaded"
    fi

    if [ "$ENABLE_STT" = "1" ]; then
        update_state "stt_download" "running" "Preloading Faster-Whisper STT model"
        python3 - <<PY
from faster_whisper import WhisperModel

WhisperModel("${STT_MODEL}", device="cpu", compute_type="int8")
PY
        update_state "stt_download" "complete" "Faster-Whisper STT model ready"
    fi

    touch "$SETUP_MARKER"
    update_state "setup_complete" "complete" "First time setup finished. Snapshot recommended."

fi

# ============================================
# PHASE 2 SERVE
# ============================================

update_state "services_starting" "running" "Starting NeuroFlow AI services"

start_control_api

update_state "interpret_server" "starting" "Launching Interpret vLLM on port $INTERPRET_PORT"
vllm serve "$MODELS_DIR/interpret" \
    --port $INTERPRET_PORT \
    --gpu-memory-utilization 0.42 \
    --max-model-len 8192 \
    --dtype auto \
    --served-model-name interpret &

wait_for_port $INTERPRET_PORT "interpret" 300

if [ "$ENABLE_REASONER" = "1" ]; then
    update_state "reasoner_server" "starting" "Launching Reasoner vLLM on port $REASONER_PORT"
    vllm serve "$MODELS_DIR/reasoner" \
        --port $REASONER_PORT \
        --gpu-memory-utilization 0.22 \
        --max-model-len 8192 \
        --dtype auto \
        --served-model-name reasoner &
fi

if [ "$ENABLE_RERANK" = "1" ]; then
    update_state "rerank_server" "starting" "Launching Rerank vLLM on port $RERANK_PORT"
    vllm serve "$MODELS_DIR/rerank" \
        --port $RERANK_PORT \
        --runner pooling \
        --gpu-memory-utilization 0.12 \
        --max-model-len 1024 \
        --dtype float16 \
        --served-model-name rerank &
fi

if [ "$ENABLE_STT" = "1" ]; then
    update_state "stt_server" "starting" "Launching Faster-Whisper STT on port $STT_PORT"

    cat > "$BASE_DIR/stt_server.py" <<PY
from faster_whisper import BatchedInferencePipeline, WhisperModel
from fastapi import FastAPI, File, UploadFile
import os
import tempfile

model_name = os.environ.get("AI_ORCH_STT_MODEL", "turbo")
device = "cuda" if os.environ.get("CUDA_VISIBLE_DEVICES", "") != "" else "cpu"
compute_type = "float16" if device == "cuda" else "int8"

base_model = WhisperModel(model_name, device=device, compute_type=compute_type)
batched = BatchedInferencePipeline(model=base_model)

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok", "model": model_name}

@app.post("/v1/audio/transcriptions")
async def transcribe(file: UploadFile = File(...)):
    path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(await file.read())
            path = f.name

        segments, info = batched.transcribe(
            path,
            batch_size=8 if device == "cuda" else 4,
            vad_filter=True,
            word_timestamps=False,
        )

        text = " ".join(segment.text.strip() for segment in segments).strip()

        return {
            "text": text,
            "language": getattr(info, "language", None),
            "duration": getattr(info, "duration", None),
            "model": model_name,
        }
    finally:
        if path and os.path.exists(path):
            os.unlink(path)
PY

    cd "$BASE_DIR"
    uvicorn stt_server:app \
        --host 0.0.0.0 \
        --port $STT_PORT &
fi

if [ "$ENABLE_TTS" = "1" ]; then
    update_state "tts_server" "starting" "Launching Kokoro TTS on port $TTS_PORT"

    cd "$BASE_DIR"

    if [ ! -d "kokoro-fastapi" ]; then
        git clone https://github.com/remsky/Kokoro-FastAPI.git kokoro-fastapi
    fi

    cd kokoro-fastapi

    pip install -q uv
    if [ ! -d ".venv" ]; then
        uv venv .venv
    fi

    . .venv/bin/activate

    PROJECT_ROOT=$(pwd)
    export USE_GPU=true
    export USE_ONNX=false
    export PYTHONPATH=$PROJECT_ROOT:$PROJECT_ROOT/api
    export MODEL_DIR=src/models
    export VOICES_DIR=src/voices/v1_0
    export WEB_PLAYER_PATH=$PROJECT_ROOT/web

    uv pip install -e ".[gpu]"
    uv run --no-sync python docker/scripts/download_model.py --output api/src/models/v1_0

    uv run --no-sync uvicorn api.src.main:app \
        --host 0.0.0.0 \
        --port $TTS_PORT &
fi

wait_for_port $INTERPRET_PORT "interpret" 300 &
if [ "$ENABLE_REASONER" = "1" ]; then wait_for_port $REASONER_PORT "reasoner" 300 & fi
if [ "$ENABLE_RERANK" = "1" ]; then wait_for_port $RERANK_PORT "rerank" 180 & fi
if [ "$ENABLE_STT" = "1" ]; then wait_for_port $STT_PORT "stt" 120 & fi
if [ "$ENABLE_TTS" = "1" ]; then wait_for_port $TTS_PORT "tts" 120 & fi
wait

start_idle_monitor

update_state "all_services" "ready" \
"All services up. Interpret:$INTERPRET_PORT Reasoner:$REASONER_PORT Rerank:$RERANK_PORT STT:$STT_PORT TTS:$TTS_PORT Control:$CONTROL_PORT"

echo "============================================"
echo " NEUROFLOW AI RUNTIME - ALL SERVICES READY"
echo "============================================"
echo " Interpret: http://localhost:$INTERPRET_PORT"
echo " Reasoner:  http://localhost:$REASONER_PORT"
echo " Rerank:    http://localhost:$RERANK_PORT"
echo " STT:       http://localhost:$STT_PORT"
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
echo " IDLE TIMEOUT: ${IDLE_TIMEOUT_SECONDS}s"
echo "============================================"

wait
