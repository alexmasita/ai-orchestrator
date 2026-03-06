# --- Start Architect LLM ---
update_state "architect_server" "starting" "Launching Architect on port $ARCHITECT_PORT"
vllm serve "$MODELS_DIR/architect" \
    --port $ARCHITECT_PORT \
    --gpu-memory-utilization $ARCHITECT_GPU_UTIL \
    --max-model-len 8192 \
    --quantization awq &

# --- Start Developer LLM ---
update_state "developer_server" "starting" "Launching Developer on port $DEVELOPER_PORT"
vllm serve "$MODELS_DIR/developer" \
    --port $DEVELOPER_PORT \
    --gpu-memory-utilization $DEVELOPER_GPU_UTIL \
    --max-model-len 8192 \
    --quantization awq &