# MVP Capability Gap Report

Capability states use: `implemented`, `partially implemented`, `not implemented`.

| Capability | State | Evidence (implemented portions) | Evidence (gaps) |
|---|---|---|---|
| Session lifecycle | `partially implemented` | Generic persisted runtime state utilities exist (`src/ai_orchestrator/core/state_manager.py`); CLI has deterministic invocation boundaries (`src/ai_orchestrator/cli.py`) | No session creation/resume/stop API or session domain model (`src/ai_orchestrator/cli.py`, `src/ai_orchestrator/devserver/app.py`, `docs/architecture_v2/02_phase_1_orchestrator_core/api_surface.md`) |
| Model runtime management | `partially implemented` | Provider-backed provisioning and runtime readiness are implemented (`src/ai_orchestrator/provider/vast.py`, `src/ai_orchestrator/orchestrator.py`, `src/ai_orchestrator/runtime/healthcheck.py`); combo runtime config selection exists (`src/ai_orchestrator/core/combo_manager.py`) | No dedicated in-process runtime manager with explicit load/unload/swap contract (`docs/architecture_v2/03_phase_2_model_runtime_manager/runtime_contract.md`) |
| Agent loop execution | `not implemented` | Role-oriented naming exists in combo/runtime endpoint resolution (`src/ai_orchestrator/orchestrator.py`, `combos/reasoning_80gb/combo.yaml`) | No architect/developer packet loop supervisor or iterative orchestrator (`docs/architecture_v2/04_phase_3_agent_loop/architecture.md`, `src/ai_orchestrator/`) |
| Structured tool usage | `not implemented` | Some bounded behavior patterns exist (timeouts/output constraints in provider/healthcheck code) (`src/ai_orchestrator/provider/vast.py`, `src/ai_orchestrator/runtime/healthcheck.py`) | No schema-first tool request/result gateway (`docs/architecture_v2/05_phase_4_tool_execution_layer/tool_contracts.md`, `docs/architecture_v2/05_phase_4_tool_execution_layer/tool_result_schema.md`) |
| Repository mutation abstraction | `not implemented` | Local filesystem state writes are present (`src/ai_orchestrator/core/state_manager.py`) | No `RepoMutationEngine` interface or Local/CDOS implementations (`docs/architecture_v2/06_phase_5_repo_interaction/repo_mutation_engine.md`, `src/ai_orchestrator/`) |
| Verification loop | `partially implemented` | Runtime readiness verification exists (`src/ai_orchestrator/runtime/healthcheck.py`); extensive automated tests exist (`tests/`) | No iterative verify/fail/refine loop integrated into orchestrator runtime (`docs/architecture_v2/04_phase_3_agent_loop/mvp_loop_design.md`, `src/ai_orchestrator/orchestrator.py`) |
| Failure packet handling | `not implemented` | Error propagation and typed exceptions exist (`src/ai_orchestrator/cli.py`, `src/ai_orchestrator/provider/vast.py`, `src/ai_orchestrator/runtime/healthcheck.py`) | No structured `FailurePacket` schema lifecycle in runtime (`docs/architecture_v2/04_phase_3_agent_loop/packet_schemas.md`, `docs/architecture_v2/ai_orchestrator_protocol.md`) |

## MVP gap summary
- Infrastructure orchestration is present.
- Autonomous development runtime capabilities (session manager, packetized agent loop, mutation abstraction, governance, tool contracts) remain open gaps.
