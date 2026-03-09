# Configuration Files

This document describes the key configuration files used by the orchestrator.

These files control runtime behavior, environment setup, and CLI execution.

---

# config.yaml

Primary runtime configuration file.

Defines:

- provider credentials
- GPU requirements
- pricing limits
- network constraints
- model sizing parameters

Example:


vast_api_key: "<api key>"
vast_api_url: "https://console.vast.ai/api/v0
"

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

idle_timeout_seconds: 1800
snapshot_version: "v1"

whisper_vram_gb: 8
whisper_disk_gb: 10


---

# launch.sh

Convenience launch script.

Purpose:

- simplify repeated runs
- enforce execution from repository root
- verify CLI availability

Example:


./launch.sh


Internally runs:


ai-orchestrator start
--config config.yaml
--models deepseek_llamacpp whisper


---

# pyproject.toml

Defines:

- Python packaging configuration
- build backend
- runtime dependencies

Example dependencies:


requests
PyYAML


Also defines console entrypoints:


[project.scripts]
ai-orchestrator = ai_orchestrator.cli:main


---

# setup.cfg

Defines packaging configuration.

Includes:

- package discovery
- CLI entrypoints

Example:


[options.entry_points]
console_scripts =
ai-orchestrator = ai_orchestrator.cli:main


---

# Why Configuration is Externalized

Configuration is intentionally kept outside runtime code.

Benefits:

- reproducible deployments
- environment-specific tuning
- secure credential handling
- easier debugging

---

# Configuration Validation

The system validates configuration at startup.

Invalid configurations raise:


ConfigError
OrchestratorConfigError


This prevents misconfigured infrastructure launches.

---

# Configuration Normalization

Configuration values undergo normalization during loading:

Examples:

Input:


"https://console.vast.ai/api/v0/
"


Normalized:


https://console.vast.ai/api/v0


Normalization ensures compatibility with provider API calls.

---

# Security Considerations

Configuration files may contain API keys.

Recommended practices:

- do not commit real credentials
- use environment variables in production
- rotate API keys periodically