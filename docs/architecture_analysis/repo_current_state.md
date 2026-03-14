# Repository Current State

## Scope
This report summarizes the current codebase implementation status using file-backed evidence only.

## What the repository currently implements

Claim:
The repository implements a Python-based orchestration CLI that provisions Vast instances, resolves combo runtime state, injects bootstrap scripts, waits for readiness, and returns structured JSON output.

Evidence:
- src/ai_orchestrator/cli.py
- src/ai_orchestrator/orchestrator.py
- src/ai_orchestrator/provider/vast.py
- src/ai_orchestrator/core/combo_manager.py

Claim:
The repository includes a combo-centric runtime path (`--combo`) and a legacy model-list path (`--models`) in the same CLI surface.

Evidence:
- src/ai_orchestrator/cli.py
- combos/reasoning_80gb/combo.yaml
- configs/reasoning_80gb.yaml

## Major runtime entry points

Claim:
Primary operator entry point is the `ai-orchestrator` CLI command with `start` and `docs` subcommands.

Evidence:
- pyproject.toml
- setup.cfg
- src/ai_orchestrator/cli.py

Claim:
A development FastAPI docs/control server exists as a secondary API entry point.

Evidence:
- src/ai_orchestrator/devserver/app.py
- src/ai_orchestrator/cli.py

Claim:
A separate runtime control API exists at repository root for status/health/stop/destroy actions.

Evidence:
- control_api.py
- state.json
- combos/reasoning_80gb/bootstrap.sh

## Key modules and directories

Claim:
Core orchestration modules are implemented under `src/ai_orchestrator` with clear boundaries for provider, runtime, plugins, combo loading, and core state utilities.

Evidence:
- src/ai_orchestrator/orchestrator.py
- src/ai_orchestrator/provider/interface.py
- src/ai_orchestrator/provider/vast.py
- src/ai_orchestrator/runtime/healthcheck.py
- src/ai_orchestrator/combos/loader.py
- src/ai_orchestrator/core/combo_manager.py
- src/ai_orchestrator/core/service_registry.py
- src/ai_orchestrator/core/state_manager.py

Claim:
Runtime combo assets are represented as declarative manifests plus shell bootstrap scripts.

Evidence:
- combos/reasoning_80gb/combo.yaml
- combos/reasoning_80gb/bootstrap.sh
- configs/reasoning_80gb.yaml

Claim:
Testing is substantial and contract-oriented, including base tests and pass-specific contract suites.

Evidence:
- tests/
- tests/pass1/
- tests/pass_combo2/
- tests/pass_combo_cli/
- pyproject.toml

## Subsystem discovery

### Model runtime management

Claim:
Model runtime management exists indirectly via provider instance provisioning and combo runtime config resolution, not as a dedicated in-process runtime manager service.

Evidence:
- src/ai_orchestrator/core/combo_manager.py
- src/ai_orchestrator/provider/vast.py
- combos/reasoning_80gb/bootstrap.sh

### Agent loop logic

Claim:
No architect/developer iterative agent loop supervisor is implemented in application code.

Evidence:
- src/ai_orchestrator/cli.py
- src/ai_orchestrator/orchestrator.py
- src/ai_orchestrator/core/

### API servers

Claim:
Two FastAPI servers are present: a dev docs server and a control API server.

Evidence:
- src/ai_orchestrator/devserver/app.py
- control_api.py

### Bootstrap/runtime scripts

Claim:
Bootstrap/runtime script logic is central to environment bring-up and service startup.

Evidence:
- combos/reasoning_80gb/bootstrap.sh
- src/ai_orchestrator/runtime/script.py
- src/ai_orchestrator/provider/vast.py
- launch.sh

### Tool execution logic

Claim:
There is no standalone structured tool execution gateway in current orchestrator code; command execution contracts mainly appear in documentation and tests.

Evidence:
- src/ai_orchestrator/
- src/ai_orchestrator/core/
- docs/architecture_v2/05_phase_4_tool_execution_layer/architecture.md

### Repository mutation logic

Claim:
No repository mutation abstraction (for patching/edit/finalize/push lifecycle) is implemented in runtime code.

Evidence:
- src/ai_orchestrator/
- docs/architecture_v2/06_phase_5_repo_interaction/repo_mutation_engine.md

### Session lifecycle logic

Claim:
Session lifecycle is not implemented as a session manager; only a generic state-file utility exists.

Evidence:
- src/ai_orchestrator/core/state_manager.py
- src/ai_orchestrator/cli.py
- src/ai_orchestrator/devserver/app.py

### Model orchestration

Claim:
Offer selection, provisioning flow, endpoint resolution, and readiness gating are implemented.

Evidence:
- src/ai_orchestrator/orchestrator.py
- src/ai_orchestrator/cli.py
- src/ai_orchestrator/provider/vast.py
- src/ai_orchestrator/runtime/healthcheck.py

### Health checks

Claim:
Both runtime health wait utilities and service-level aggregate health constructs are implemented.

Evidence:
- src/ai_orchestrator/runtime/healthcheck.py
- src/ai_orchestrator/core/service_registry.py
- src/ai_orchestrator/devserver/app.py
- control_api.py

### Infrastructure scripts

Claim:
Repository includes operational shell scripts for launch/bootstrap and additional inspiration scripts.

Evidence:
- launch.sh
- combos/reasoning_80gb/bootstrap.sh
- Inspirations/

### CLI tools

Claim:
CLI tooling includes orchestration start and docs server launch.

Evidence:
- src/ai_orchestrator/cli.py
- pyproject.toml
- setup.cfg

### Testing infrastructure

Claim:
Testing infrastructure includes unit and contract tests for CLI, provider behavior, combo contracts, and runtime readiness behavior.

Evidence:
- tests/test_cli_start_command.py
- tests/test_vast_provider.py
- tests/test_orchestrator_output.py
- tests/pass1/test_vast_bootstrap_contract.py
- tests/pass_combo2/test_combo2_cli_start_schema_contract.py
- tests/pass_combo_cli/test_cli_combo_output_contract.py

## Current orchestration behavior

Claim:
Current orchestration behavior is provider-first provisioning with deterministic selection filters, bootstrap injection, and readiness wait before success payload.

Evidence:
- src/ai_orchestrator/orchestrator.py
- src/ai_orchestrator/provider/vast.py
- src/ai_orchestrator/runtime/healthcheck.py

Claim:
Combo orchestration behavior resolves merged runtime config + combo manifest, renders env-injected bootstrap script, then creates and polls instance and resolves role endpoints.

Evidence:
- src/ai_orchestrator/core/combo_manager.py
- src/ai_orchestrator/cli.py
- src/ai_orchestrator/orchestrator.py
- configs/reasoning_80gb.yaml
- combos/reasoning_80gb/combo.yaml

## Current repo mutation approach

Claim:
No dedicated repository mutation subsystem exists for code editing workflows; current code mutates local state files and runtime-generated control API files only.

Evidence:
- src/ai_orchestrator/core/state_manager.py
- control_api.py
- combos/reasoning_80gb/bootstrap.sh

## Current model serving approach

Claim:
Model serving is externalized to provisioned instance bootstrap scripts (vLLM for architect/developer, uvicorn service processes for STT/TTS/control), not managed by an in-repo runtime daemon.

Evidence:
- combos/reasoning_80gb/bootstrap.sh
- src/ai_orchestrator/provider/vast.py
- control_api.py
- src/ai_orchestrator/runtime/bootstrap.py

## Missing architecture components (relative to architecture_v2 drafts)

Claim:
The following architecture_v2-targeted components are missing or not formalized in code: session manager API, model runtime manager, packetized agent loop, structured tool gateway, repo mutation abstraction interface, autonomy supervisor, policy registry, prompt registry, and governance/telemetry schema layer.

Evidence:
- docs/architecture_v2/00_overview/system_layers.md
- docs/architecture_v2/02_phase_1_orchestrator_core/api_surface.md
- docs/architecture_v2/03_phase_2_model_runtime_manager/architecture.md
- docs/architecture_v2/04_phase_3_agent_loop/packet_schemas.md
- docs/architecture_v2/05_phase_4_tool_execution_layer/tool_contracts.md
- docs/architecture_v2/06_phase_5_repo_interaction/repo_mutation_engine.md
- docs/architecture_v2/07_phase_6_autonomous_supervisor/architecture.md
- docs/architecture_v2/09_self_improvement_layer/prompt_registry.md
- src/ai_orchestrator/
