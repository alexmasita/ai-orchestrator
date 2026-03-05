Purpose

This document explains how the ai-orchestrator CLI command is exposed through Python packaging.

The CLI entrypoint allows the system to be invoked using:

ai-orchestrator

instead of running Python modules directly.

Entry Point Definition

The CLI is defined in:

pyproject.toml

Example:

[project.scripts]
ai-orchestrator = ai_orchestrator.cli:main

This tells the Python packaging system:

ai-orchestrator → execute ai_orchestrator.cli.main()
Generated CLI Script

After installation, pip generates an executable:

.venv/bin/ai-orchestrator

The script internally runs:

from ai_orchestrator.cli import main
sys.exit(main())
CLI Command Structure

Primary command:

ai-orchestrator start

Example:

ai-orchestrator start \
  --config config.yaml \
  --models deepseek_llamacpp whisper
CLI Output Contract

Successful execution prints JSON to stdout:

Example:

{
  "instance_id": "abc123",
  "gpu_type": "RTX_4090",
  "cost_per_hour": 0.52,
  "idle_timeout": 1800,
  "snapshot_version": "v1",
  "deepseek_url": "http://1.2.3.4:8080",
  "whisper_url": "http://1.2.3.4:9000"
}
CLI Exit Codes

Exit code meanings:

Exit Code	Meaning
0	success
1	configuration or provider error

Errors are printed to stderr.