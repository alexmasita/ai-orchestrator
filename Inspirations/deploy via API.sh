import requests

api_key = "your_api_key"
offer_id = 12345678

# Read your script files
with open("onstart.sh") as f:
    onstart_content = f.read()

# The onstart must create the module directory and files first,
# then call itself. Wrap it all in one script:
bootstrap = """#!/usr/bin/env bash
set -e
mkdir -p /workspace/modules

# Write module scripts (only if not already present from snapshot)
if [ ! -f /workspace/modules/deepseek.sh ]; then
cat > /workspace/modules/deepseek.sh << 'MODULE1EOF'
... (paste deepseek.sh content here) ...
MODULE1EOF
fi

if [ ! -f /workspace/modules/whisper.sh ]; then
cat > /workspace/modules/whisper.sh << 'MODULE2EOF'
... (paste whisper.sh content here) ...
MODULE2EOF
fi

if [ ! -f /workspace/modules/control.sh ]; then
cat > /workspace/modules/control.sh << 'MODULE3EOF'
... (paste control.sh content here) ...
MODULE3EOF
fi

# Now run the main orchestrator
... (paste onstart.sh content here, minus the shebang) ...
"""

response = requests.put(
    f"https://console.vast.ai/api/v0/asks/{offer_id}/",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "image": "nvidia/cuda:12.1.0-devel-ubuntu22.04",
        "disk": 100,
        "runtype": "jupyter_direct",
        "use_jupyter_lab": True,
        "jupyter_dir": "/workspace",
        "env": {
            "VAST_API_KEY": api_key,
            "WEBHOOK_URL": "https://your-app.com/api/vast-status",
            "IDLE_TIMEOUT_SECONDS": "1800",
            "-p 8080:8080": "1",
            "-p 9000:9000": "1",
            "-p 7999:7999": "1"
        },
        "onstart": bootstrap
    }
)