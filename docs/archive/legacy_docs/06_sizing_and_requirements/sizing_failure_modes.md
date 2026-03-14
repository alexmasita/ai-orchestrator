Purpose

This document defines the failure scenarios in the sizing stage.

Sizing failures occur before orchestration begins.

Failure Type

Sizing failures raise:

OrchestratorConfigError

This error propagates to the CLI where it is converted into a user-facing configuration error.

Failure Scenarios
Missing Model Configuration

Example:

whisper_vram_gb missing

Error:

OrchestratorConfigError("Missing whisper config")
Unknown Model

If a model is not registered:

OrchestratorConfigError("Unknown model")
Invalid Configuration Values

Examples:

whisper_vram_gb = "eight"
whisper_disk_gb = -5

These cause validation failures.

Empty Model List

CLI must provide at least one model.

Example invalid command:

ai-orchestrator start --config config.yaml
Plugin Contract Violation

Plugins must provide required sizing fields.

If a plugin fails to return valid sizing data, sizing fails.

CLI Handling

The CLI catches sizing errors:

except OrchestratorConfigError as exc:
    print("Configuration error:", exc)
    return 1

This ensures:

no stack trace

clean CLI output

Design Philosophy

Sizing failures occur early by design.

The goal is to prevent:

invalid provider requests

wasted GPU provisioning

runtime crashes

By validating configuration and model compatibility before orchestration begins.