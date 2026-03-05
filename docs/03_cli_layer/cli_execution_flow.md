# CLI Execution Flow

This document describes the real runtime flow of `ai_orchestrator.cli.main()` and the boundaries between the CLI and the rest of the system.

The CLI is intentionally a wiring layer; it orchestrates the orchestration engine.

---

## High-Level Flow

When invoked as:

```bash
ai-orchestrator start --config config.yaml --models deepseek_llamacpp whisper

the control flow is:

cli.main(argv)

build_parser() → argparse parse

load_config(args.config) → dict config

SizingInput(models=args.models, config=config)

compute_requirements(sizing_input) → sizing_result

VastProvider(api_key=config["vast_api_key"], base_url=config["vast_api_url"])

run_orchestration(provider=provider, sizing_result=sizing_result, config=config)

Build final CLI JSON payload (mapping provider fields if needed)

Print JSON to stdout (single line)

return 0

Step-by-Step Flow
1) Parse args

The parser is constructed by build_parser().

The CLI currently expects:

args.command == "start"

args.config string path

args.models list of strings

If the command is not start, the CLI returns exit code 1.

2) Load config

load_config(path) loads YAML into a python dict and applies normalization.

Key behaviors:

Vast API URL may be normalized (quote stripping, trailing slash stripping).

The returned object must be dict-like and contain required keys.

If load_config() raises ConfigError, the CLI exits with 1.

3) Build SizingInput

The CLI constructs a sizing input object:

SizingInput(models=args.models, config=config)

This is a pure data object used to compute requirements.

4) Compute requirements

The CLI calls:

compute_requirements(sizing_input)

This step is responsible for validating that required model-specific config fields exist.

Example of model-driven config validation:

If whisper is in the models list, sizing requires whisper-specific keys (e.g., VRAM and disk requirement keys) and will raise OrchestratorConfigError if missing.

CLI behavior on OrchestratorConfigError:

prints a single-line stderr message:

Configuration error: <message>

returns exit code 1

This is an explicit contract: sizing/config errors should not produce full tracebacks in normal use.

5) Initialize provider

The CLI constructs the provider:

VastProvider(api_key=config["vast_api_key"], base_url=config["vast_api_url"])

Provider initialization may fail-fast if runtime dependencies are missing (for example requests), in which case it raises VastProviderError.

CLI behavior on VastProviderError:

prints a single-line stderr message:

Provider error: <message>

returns exit code 1

6) Run orchestration

The CLI then calls:

raw_result = run_orchestration(
  provider=provider,
  sizing_result=sizing_result,
  config=config,
)

run_orchestration owns the full lifecycle:

generates bootstrap script using generate_bootstrap_script(config, models) (the models list originates from CLI args and/or sizing input in the pipeline)

validates script (type, non-empty, stripped, max-bytes)

selects offer (provider.search_offers + selection rules)

creates instance (provider.create_instance)

runs readiness checks (wait_for_instance_ready)

returns a result dict including instance info and service URLs

The CLI does not implement any of these details; it treats run_orchestration as a black box that returns a dictionary.

7) Normalize CLI output fields

The CLI builds its own output dict from raw_result.

Key compatibility mapping:

gpu_type is taken from:

raw_result["gpu_type"] if present

otherwise raw_result["gpu_name"]

cost_per_hour is taken from:

raw_result["cost_per_hour"] if present

otherwise raw_result["dph"]

URL handling:

deepseek_url and whisper_url are expected from orchestration output; if missing, the CLI falls back to deterministic defaults:

http://127.0.0.1:8080

http://127.0.0.1:9000

The CLI output schema does not expose provider raw keys like gpu_name or dph.

8) Print output

On success:

stdout prints a single JSON line

keys are sorted with sort_keys=True

returns exit code 0

Debug Mode Execution

Debug logs are emitted by lower layers (orchestrator/provider) to stderr when:

AI_ORCH_DEBUG=1

The CLI itself maintains the stdout contract regardless of debug mode.

Determinism Notes

The CLI must not introduce nondeterminism:

no timestamps

no random values

stable key ordering

All nondeterministic behavior (network calls, offer availability, runtime state) is outside the CLI layer and is handled by provider/orchestrator layers and their error wrapping.