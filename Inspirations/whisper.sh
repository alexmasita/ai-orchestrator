Now I have enough context. Here's the comprehensive answer:

Snapshot workflow is fully compatible with modular scripts. The key: all scripts write to /workspace/ (persisted in snapshots), and each uses its own setup marker. Here's the architecture:

Master orchestrator: /workspace/onstart.sh
#!/usr/bin/env bash
set -e

WORKSPACE="/workspace"

# ============================================
# SHARED STATE / WEBHOOK FUNCTIONS
# ============================================
STATE_FILE="/workspace/state.json"
WEBHOOK_URL="${WEBHOOK_URL:-}"
VAST_API_KEY="${VAST_API_KEY:-}"
IDLE_TIMEOUT_SECONDS="${IDLE_TIMEOUT_SECONDS:-1800}"
CONTROL_PORT=7999

export STATE_FILE WEBHOOK_URL VAST_API_KEY IDLE_TIMEOUT_SECONDS CONTROL_PORT

update_state() {
    local stage="$1" status="$2" message="$3"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local instance_id="${VAST_CONTAINERLABEL:-unknown}"
    cat > "$STATE_FILE" << EOF
{
    "instance_id": "$instance_id",
    "stage": "$stage",
    "status": "$status",
    "message": "$message",
    "timestamp": "$timestamp",
    "is_snapshot": $([ -f "$WORKSPACE/.setup_deepseek_complete" ] && [ -f "$WORKSPACE/.setup_whisper_complete" ] && echo "true" || echo "false")
}
EOF
    echo "[VAST_STATE] $timestamp | stage=$stage | status=$status | $message"
    if [ -n "$WEBHOOK_URL" ]; then
        curl -s -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d @"$STATE_FILE" || true
    fi
}
export -f update_state

# ============================================
# SHARED DEPENDENCIES (one-time)
# ============================================
if [ ! -f "$WORKSPACE/.setup_shared_complete" ]; then
    update_state "shared_setup" "running" "Installing shared dependencies"
    apt-get update
    apt-get install -y libcurl4-openssl-dev ffmpeg python3-pip
    pip install fastapi uvicorn python-multipart httpx
    touch "$WORKSPACE/.setup_shared_complete"
    update_state "shared_setup" "complete" "Shared dependencies installed"
fi

# ============================================
# RUN MODULE SCRIPTS (setup + serve)
# Each module handles its own setup marker.
# ============================================
update_state "modules" "running" "Running module scripts"

# Module 1: DeepSeek
bash "$WORKSPACE/modules/deepseek.sh"

# Module 2: Whisper
bash "$WORKSPACE/modules/whisper.sh"

# Module 3: Control API + Idle Monitor
bash "$WORKSPACE/modules/control.sh"

# ============================================
# WAIT FOR SERVICES
# ============================================
wait_for_port() {
    local port=$1 name=$2 max_wait=${3:-120} waited=0
    update_state "${name}_health" "waiting" "Waiting for $name on port $port..."
    while ! curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port" | grep -qE "200|404|405"; do
        sleep 2; waited=$((waited + 2))
        if [ $waited -ge $max_wait ]; then
            update_state "${name}_health" "timeout" "$name did not respond after ${max_wait}s"
            return 1
        fi
    done
    update_state "${name}_health" "ready" "$name responding on port $port"
}

wait_for_port 8080 "deepseek" 180 &
wait_for_port 9000 "whisper" 120 &
wait

update_state "all_services" "ready" "All services up. DeepSeek:8080 Whisper:9000 Control:$CONTROL_PORT"

echo "============================================"
echo "  SERVICES READY"
echo "  DeepSeek:  http://localhost:8080"
echo "  Whisper:   http://localhost:9000"
echo "  Control:   http://localhost:$CONTROL_PORT"
echo "  IDLE TIMEOUT: ${IDLE_TIMEOUT_SECONDS}s"
echo "============================================"

wait
Module 1: /workspace/modules/deepseek.sh
#!/usr/bin/env bash
set -e

SETUP_MARKER="/workspace/.setup_deepseek_complete"
MODELS_DIR="/workspace/models"
LLAMA_DIR="/workspace/llama.cpp"
DEEPSEEK_PORT=8080

# Model config — CHANGE ONLY THESE to swap models
DEEPSEEK_REPO="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
DEEPSEEK_LOCAL_DIR="$MODELS_DIR/deepseek-coder"

# ============================================
# SETUP (skipped after snapshot)
# ============================================
if [ ! -f "$SETUP_MARKER" ]; then
    update_state "deepseek_setup" "running" "Setting up DeepSeek Coder V2 Lite Instruct"

    # Build llama.cpp with CUDA
    update_state "llama_build" "running" "Cloning and building llama.cpp with CUDA"
    if [ ! -d "$LLAMA_DIR" ]; then
        git clone https://github.com/ggerganov/llama.cpp "$LLAMA_DIR"
    fi
    cmake "$LLAMA_DIR" -B "$LLAMA_DIR/build" \
        -DBUILD_SHARED_LIBS=OFF -DGGML_CUDA=ON -DLLAMA_CURL=ON
    cmake --build "$LLAMA_DIR/build" --config Release -j \
        --clean-first --target llama-server
    update_state "llama_build" "complete" "llama.cpp built"

    # Download model
    update_state "deepseek_download" "running" "Downloading $DEEPSEEK_REPO"
    pip install huggingface_hub -q 2>/dev/null || true
    mkdir -p "$DEEPSEEK_LOCAL_DIR"
    huggingface-cli download "$DEEPSEEK_REPO" \
        --local-dir "$DEEPSEEK_LOCAL_DIR"
    update_state "deepseek_download" "complete" "DeepSeek model downloaded"

    touch "$SETUP_MARKER"
    update_state "deepseek_setup" "complete" "DeepSeek setup finished"
fi

# ============================================
# SERVE
# ============================================
update_state "deepseek_server" "starting" "Launching DeepSeek on port $DEEPSEEK_PORT"

# Find the model file (adapt pattern to your downloaded format)
# DeepSeek-Coder-V2-Lite-Instruct is a safetensors model, NOT GGUF.
# You need to convert it first, OR use a GGUF quantized version.
# Option A: If you have a GGUF file:
MODEL_FILE=$(find "$DEEPSEEK_LOCAL_DIR" -name "*.gguf" -type f | head -1)

# Option B: If no GGUF found, convert from safetensors
if [ -z "$MODEL_FILE" ]; then
    update_state "deepseek_convert" "running" "No GGUF found. Converting safetensors to GGUF..."
    pip install sentencepiece protobuf -q 2>/dev/null || true
    python3 "$LLAMA_DIR/convert_hf_to_gguf.py" "$DEEPSEEK_LOCAL_DIR" \
        --outfile "$DEEPSEEK_LOCAL_DIR/deepseek-coder-v2-lite-instruct.gguf" \
        --outtype f16
    MODEL_FILE="$DEEPSEEK_LOCAL_DIR/deepseek-coder-v2-lite-instruct.gguf"
    update_state "deepseek_convert" "complete" "Conversion complete: $MODEL_FILE"
fi

"$LLAMA_DIR/build/bin/llama-server" \
    --model "$MODEL_FILE" \
    --ctx-size 8192 \
    --n-gpu-layers 62 \
    --port $DEEPSEEK_PORT &

update_state "deepseek_server" "started" "DeepSeek serving on port $DEEPSEEK_PORT"
Module 2: 