# CLI Command Contract

This document specifies the supported CLI commands, arguments, and behavioral contracts.

The CLI is intentionally small and currently supports a single primary workflow command: `start`.

---

## Command: `start`

### Purpose

`start` triggers the end-to-end orchestration workflow:

- load config
- compute sizing requirements
- instantiate provider
- run orchestration (bootstrap injection, offer selection, instance creation, readiness checks)
- print deterministic JSON output

### Invocation

```bash
ai-orchestrator start --config config.yaml --models deepseek_llamacpp whisper

Arguments
--config <path>

Required.

Path to a YAML configuration file.

The file must contain the minimum required keys for:

Vast connectivity (vast_api_key, vast_api_url)

global resource constraints (network, price, reliability)

model-specific sizing keys (depends on chosen --models)

--models <model...>

Required.

One or more model identifiers (space-separated).

Models are used in two places:

Sizing

compute_requirements() validates required fields for each model.

Bootstrap script generation

generate_bootstrap_script(config, models) is called by orchestration.

Example:

--models deepseek_llamacpp whisper
Return Codes

0 on success

1 on failure

Output Contracts

On success: stdout contains exactly one line of JSON.

On failure: stdout is not used for structured output. The CLI writes a one-line message to stderr for handled error classes and returns exit code 1.

Supported Error Behavior

The CLI catches and formats these known error types:

Configuration errors (ConfigError)

Raised during load_config().

CLI behavior:

no traceback

exit code 1

Orchestration configuration errors (OrchestratorConfigError)

Raised during sizing and other configuration validation.

Example: missing Whisper sizing fields when whisper is included in --models.

CLI behavior:

prints: Configuration error: <message> to stderr

exit code 1

Provider errors (VastProviderError)

Raised by provider code when:

HTTP request fails

response parsing fails

required runtime dependencies are missing

CLI behavior:

prints: Provider error: <message> to stderr

exit code 1

Other exception types may still surface as tracebacks. The project hardens the provider/orchestrator layers to convert common runtime failures into VastProviderError / OrchestratorConfigError so the CLI stays user-safe.

Determinism Requirements

The CLI command must be deterministic for identical inputs:

Given the same config + same models + same orchestration return payload, stdout JSON must match exactly.

The CLI uses json.dumps(..., sort_keys=True) to ensure stable key ordering.

The CLI does not include timestamps, random IDs, or non-deterministic formatting in its output schema.

Integration Notes
Editable installs

In development, the CLI is typically run from an editable install:

pip install -e .
Local wrapper script

A repository-provided launch.sh may exist to standardize invocation from repo root. It must not change CLI semantics; it is only a convenience wrapper around the ai-orchestrator start ... command.