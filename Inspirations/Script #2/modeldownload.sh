# --- DOWNLOAD ARCHITECT MODEL ---
if [ ! -d "$MODELS_DIR/architect" ]; then
    update_state "architect_download" "running" "Downloading Architect model: $ARCHITECT_MODEL"
    huggingface-cli download "$ARCHITECT_MODEL" \
        --local-dir "$MODELS_DIR/architect"
    update_state "architect_download" "complete" "Architect model downloaded"
else
    update_state "architect_download" "skipped" "Architect model already present"
fi

# --- DOWNLOAD DEVELOPER MODEL ---
if [ ! -d "$MODELS_DIR/developer" ]; then
    update_state "developer_download" "running" "Downloading Developer model: $DEVELOPER_MODEL"
    huggingface-cli download "$DEVELOPER_MODEL" \
        --local-dir "$MODELS_DIR/developer"
    update_state "developer_download" "complete" "Developer model downloaded"
else
    update_state "developer_download" "skipped" "Developer model already present"
fi