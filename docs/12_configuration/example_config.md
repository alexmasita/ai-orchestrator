Example Configuration

Below is a complete working configuration.

config.yaml
vast_api_key: "YOUR_VAST_API_KEY"
vast_api_url: "https://console.vast.ai/api/v0"

gpu:
  min_vram_gb: 24
  preferred_models:
    - RTX_4090
    - RTX_A6000
    - A100

min_inet_down_mbps: 100
min_inet_up_mbps: 100

reliability_min: 0.98
verified_only: true

max_dph: 0.6
allow_interruptible: true

# Required if whisper model is enabled
whisper_vram_gb: 8
whisper_disk_gb: 10

idle_timeout_seconds: 1800
snapshot_version: "v1"
Running the System

With this configuration:

ai-orchestrator start \
  --config config.yaml \
  --models deepseek_llamacpp whisper
Expected Output

Successful execution prints JSON:

{
  "instance_id": "abc123",
  "gpu_type": "RTX_4090",
  "cost_per_hour": 0.58,
  "idle_timeout": 1800,
  "snapshot_version": "v1",
  "deepseek_url": "http://1.2.3.4:8080",
  "whisper_url": "http://1.2.3.4:9000"
}
Security Guidance

Never commit:

vast_api_key

to public repositories.

Use environment variables or secrets management for production.