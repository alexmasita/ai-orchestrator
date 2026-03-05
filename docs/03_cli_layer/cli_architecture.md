# CLI Architecture

The CLI is the *only* supported entry point for invoking the ai-orchestrator end-to-end workflow from a user’s shell. It is intentionally thin: it performs argument parsing, configuration loading/normalization, sizing computation, provider initialization, orchestration invocation, and finally prints a deterministic JSON result.

The CLI is designed around two constraints:

1. **Deterministic user-visible output**
   - On success, stdout is a **single line JSON** string produced via `json.dumps(..., sort_keys=True)`.
   - Keys and values are stable across identical inputs.

2. **Strict separation of concerns**
   - The CLI does not implement orchestration logic.
   - The CLI does not implement provider or Vast API logic.
   - The CLI does not implement healthchecks or bootstrap behavior.
   - The CLI is responsible for *wiring* these components and presenting results/errors.

---

## Entry Point

The CLI function is:

- `ai_orchestrator.cli:main`

It is exposed via the package console script (entry point), so that after installation a shell command exists:

- `ai-orchestrator`

In development this is typically invoked using:

- `.venv/bin/ai-orchestrator ...`

---

## Responsibilities

The CLI performs the following steps:

1. **Parse arguments**
   - Builds a parser (`build_parser()`)
   - Parses argv
   - Validates command selection (currently `start`)

2. **Load configuration**
   - Uses `load_config(path)` from `ai_orchestrator.config`
   - The loader normalizes values (including Vast URL normalization rules)
   - If config loading fails, CLI exits with `1`

3. **Build sizing input**
   - Constructs a `SizingInput(models=args.models, config=config)`

4. **Compute requirements**
   - Calls `compute_requirements(sizing_input)`
   - This computes a sizing result required for orchestration/selection
   - If sizing fails due to missing/invalid model config keys, the CLI exits cleanly

5. **Initialize provider**
   - Constructs `VastProvider(api_key=..., base_url=...)` using config values
   - Provider may fail fast if runtime dependencies are missing (e.g., requests)

6. **Invoke orchestrator**
   - Calls `run_orchestration(...)`
   - The orchestrator owns:
     - bootstrap script generation and injection
     - offer selection
     - instance creation
     - readiness checks
     - return payload composition

7. **Map/normalize output for CLI schema**
   - CLI output schema is stable and does not leak provider internal fields
   - The CLI supports compatibility mapping:
     - `gpu_name -> gpu_type`
     - `dph -> cost_per_hour`

8. **Emit output**
   - Prints one JSON line to stdout
   - Returns process exit code `0`

---

## What the CLI Does *Not* Do

The CLI intentionally does not:

- call Vast directly (except indirectly via provider methods)
- run network calls itself
- implement any retry logic
- implement bootstrapping logic
- implement healthcheck logic
- print multi-line formatted output (success output is JSON-only)

---

## Debugging and Observability

Debug mode is implemented as stderr logging gated behind:

- `AI_ORCH_DEBUG=1`

The CLI itself does not dump debug logs on success; it delegates debug printing to the lower layers (orchestrator/provider) while keeping stdout clean.

---

## Exit Code Policy

- `0` on success
- `1` on any failure (config, sizing, provider, orchestration)

Failures are reported as **one-line stderr messages** for known error types, avoiding raw tracebacks for common user mistakes and environment gaps.

Known error classes handled by the CLI:

- `ConfigError` (from configuration loading)
- `OrchestratorConfigError` (from sizing/orchestration configuration validation)
- `VastProviderError` (provider/runtime failures surfaced in a user-safe way)