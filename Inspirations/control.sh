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