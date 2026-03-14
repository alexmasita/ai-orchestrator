# Implementation Map (Raw)

This map links current repository files to architectural responsibilities without inferring non-existent components.

## Runtime Entry Points
- `src/ai_orchestrator/cli.py` (`main`, parser, start/docs dispatch)
- `launch.sh` (local convenience launch wrapper)
- `src/ai_orchestrator/devserver/app.py` (`run_dev_server`)
- `control_api.py` (FastAPI control endpoints)
- `pyproject.toml` and `setup.cfg` (CLI entrypoint registration)

## Model Runtime
- `src/ai_orchestrator/provider/vast.py` (instance creation + runtime bootstrap payload)
- `src/ai_orchestrator/core/combo_manager.py` (runtime config resolution by combo)
- `combos/reasoning_80gb/bootstrap.sh` (actual in-instance model startup workflow)
- `configs/reasoning_80gb.yaml` (runtime constraints for combo path)
- `src/ai_orchestrator/runtime/bootstrap.py` (legacy/start command definitions)

## Agent Loop
- Not implemented as a bounded architect/developer iteration supervisor in current code.
- Related role naming and endpoint resolution only:
  - `src/ai_orchestrator/orchestrator.py`
  - `src/ai_orchestrator/cli.py`
  - `combos/reasoning_80gb/combo.yaml`

## API Layer
- `src/ai_orchestrator/devserver/app.py` (docs UI + docs concat + health + CLI contract endpoint)
- `control_api.py` (`/status`, `/health`, `/ping`, `/stop`, `/destroy`)

## Tool Execution
- No dedicated structured tool execution gateway module found.
- Bounded command/tool concepts primarily represented in documentation/test contracts:
  - `docs/architecture_v2/05_phase_4_tool_execution_layer/*`
  - `tests/pass_combo2/*`
  - `tests/pass_combo_cli/*`

## Repository Mutation
- No dedicated repo mutation engine abstraction implemented.
- Existing local file mutation utilities:
  - `src/ai_orchestrator/core/state_manager.py` (atomic state file writes)
  - `combos/reasoning_80gb/bootstrap.sh` (writes runtime files such as state/control script in instance context)

## Session Lifecycle
- No explicit `SessionManager` subsystem.
- Minimal lifecycle-adjacent state handling:
  - `src/ai_orchestrator/core/state_manager.py`
  - `state.json`

## Orchestration Core
- `src/ai_orchestrator/orchestrator.py` (selection, orchestration flow, endpoint resolution)
- `src/ai_orchestrator/sizing.py` (resource requirement computation)
- `src/ai_orchestrator/config.py` (config loading/validation)
- `src/ai_orchestrator/config_merge.py` (config layer merge)
- `src/ai_orchestrator/cli.py` (orchestration wiring and output schema)

## Provider Layer
- `src/ai_orchestrator/provider/interface.py` (provider contracts + datamodels)
- `src/ai_orchestrator/provider/vast.py` (Vast implementation)
- `src/ai_orchestrator/provider/mock.py` (test/mock implementation)

## Combo / Runtime State
- `src/ai_orchestrator/combos/loader.py` (combo discovery and loading)
- `src/ai_orchestrator/core/combo_manager.py` (runtime state assembly)
- `src/ai_orchestrator/core/service_registry.py` (service metadata + aggregate health)
- `src/ai_orchestrator/core/snapshot_manager.py` (snapshot namespace logic)
- `combos/reasoning_80gb/combo.yaml`
- `configs/reasoning_80gb.yaml`

## Health Checks / Observability
- `src/ai_orchestrator/runtime/healthcheck.py` (port/http readiness waits)
- `src/ai_orchestrator/core/service_registry.py` (aggregate health result shape)
- `src/ai_orchestrator/devserver/app.py` (`/health`)
- `control_api.py` (`/health`)
- `combos/reasoning_80gb/bootstrap.sh` (state reporting + idle monitor)

## Plugins
- `src/ai_orchestrator/plugins/base.py` (plugin contract)
- `src/ai_orchestrator/plugins/registry.py` (plugin mapping/lookup)
- `src/ai_orchestrator/plugins/deepseek_llamacpp.py` (deepseek plugin)

## Bootstrap / Infrastructure
- `launch.sh`
- `combos/reasoning_80gb/bootstrap.sh`
- `config.yaml`
- `config 48gb Duo.yaml`
- `config 80GB Duo.yaml`
- `Inspirations/*`

## Testing
- `tests/test_*.py` (core unit and integration-style tests)
- `tests/pass1/*` (baseline contracts)
- `tests/pass_combo2/*` (combo2 contract suite)
- `tests/pass_combo_cli/*` (combo CLI contract suite)
- `pyproject.toml` (`pytest` config)
