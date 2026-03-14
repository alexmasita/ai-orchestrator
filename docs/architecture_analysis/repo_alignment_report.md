# Repository Alignment Report

## Repository architecture detected

Observation:
The repository currently centers on infrastructure provisioning orchestration (CLI -> provider -> bootstrap -> readiness) with combo-aware runtime configuration.

Evidence:
- src/ai_orchestrator/cli.py
- src/ai_orchestrator/orchestrator.py
- src/ai_orchestrator/provider/vast.py
- src/ai_orchestrator/core/combo_manager.py
- combos/reasoning_80gb/bootstrap.sh

Observation:
Implemented subsystems are strongest in provider integration, bootstrap delivery, readiness checks, and deterministic contract tests.

Evidence:
- src/ai_orchestrator/provider/vast.py
- src/ai_orchestrator/runtime/healthcheck.py
- tests/test_vast_provider.py
- tests/pass_combo2/
- tests/pass_combo_cli/

## Legacy documentation alignment summary

Observation:
Legacy documentation mostly reflects earlier architecture accurately at concept level but diverges in details from the current combo-centric and evolving runtime code.

Evidence:
- docs/legacy_docs_alignment_report.md

Classification summary (legacy docs):
- `accurate`: 14
- `partially_accurate`: 38
- `conceptually_valid_but_outdated`: 31
- `obsolete`: 4
- `architecture_target`: 8

Observation:
Largest legacy divergences are around plugin/runtime boot assumptions, sizing formulas, and older docs structure references.

Evidence:
- docs/legacy_docs/05_model_plugin_layer/*
- docs/legacy_docs/06_sizing_and_requirements/vram_calculation.md
- docs/legacy_docs/09_runtime_bootstrap/bootstrap_script_generation.md
- docs/legacy_docs/ai-orchestrator Documentation Structure.md

## New architecture document alignment summary

Observation:
Most `architecture_v2` files represent future-state architecture targets rather than currently implemented runtime subsystems.

Evidence:
- docs/new_docs_alignment_report.md

Classification summary (architecture_v2 docs):
- `already_implemented`: 5
- `partially_aligned`: 6
- `architecture_target`: 37
- `not_supported_by_repo`: 19

Observation:
Documents closest to current implementation are environment constraints and combo/runtime assumptions; least aligned areas are agent loop, tool gateway, repo mutation abstraction, and session API.

Evidence:
- docs/architecture_v2/01_setup/environment_and_constraints.md
- docs/architecture_v2/01_setup/combo_plugin_architecture.md
- docs/architecture_v2/04_phase_3_agent_loop/*
- docs/architecture_v2/05_phase_4_tool_execution_layer/*
- docs/architecture_v2/06_phase_5_repo_interaction/*
- docs/architecture_v2/02_phase_1_orchestrator_core/api_surface.md

## Major architecture drift areas

Observation:
Primary drift is between implemented infra-orchestration code and unimplemented cognition/control-plane architecture.

Evidence:
- docs/architecture_drift_findings.md
- src/ai_orchestrator/orchestrator.py
- src/ai_orchestrator/provider/vast.py

High-drift concepts:
- Session manager and session API surface
- Dedicated model runtime manager and hot-swap contract
- Packetized architect/developer loop supervisor
- Structured tool execution gateway
- RepoMutationEngine abstraction (Local/CDOS adapters)
- Governance + telemetry schema layer
- Failure packet protocol objects

Evidence:
- docs/architecture_v2/00_overview/system_layers.md
- docs/architecture_v2/03_phase_2_model_runtime_manager/runtime_contract.md
- docs/architecture_v2/04_phase_3_agent_loop/packet_schemas.md
- docs/architecture_v2/05_phase_4_tool_execution_layer/tool_contracts.md
- docs/architecture_v2/06_phase_5_repo_interaction/repo_mutation_engine.md
- docs/architecture_v2/10_observability_and_governance/telemetry_architecture.md
- src/ai_orchestrator/

## Capabilities missing for MVP

Observation:
Capability assessment identifies partial implementation in infrastructure/runtime concerns and major gaps in autonomous loop architecture.

Evidence:
- docs/mvp_gap_report.md

Current states:
- Session lifecycle: partially implemented
- Model runtime management: partially implemented
- Agent loop execution: not implemented
- Structured tool usage: not implemented
- Repository mutation abstraction: not implemented
- Verification loop: partially implemented
- Failure packet handling: not implemented

Evidence:
- src/ai_orchestrator/core/state_manager.py
- src/ai_orchestrator/provider/vast.py
- src/ai_orchestrator/runtime/healthcheck.py
- docs/architecture_v2/04_phase_3_agent_loop/architecture.md
- docs/architecture_v2/05_phase_4_tool_execution_layer/architecture.md
- docs/architecture_v2/06_phase_5_repo_interaction/repo_mutation_engine.md

## Recommended areas for architectural clarification (evidence-focused)

Observation:
The following clarification areas would reduce ambiguity between current code and target docs.

1. Define whether current combo bootstrap path is transitional or foundational.
- Evidence: `combos/reasoning_80gb/bootstrap.sh`, `src/ai_orchestrator/provider/vast.py`, `docs/architecture_v2/03_phase_2_model_runtime_manager/architecture.md`

2. Define minimum session object and API boundary required before loop work begins.
- Evidence: `src/ai_orchestrator/core/state_manager.py`, `docs/architecture_v2/02_phase_1_orchestrator_core/api_surface.md`

3. Define first concrete packet schemas to implement in code (and storage location).
- Evidence: `docs/architecture_v2/04_phase_3_agent_loop/packet_schemas.md`, `docs/architecture_v2/ai_orchestrator_protocol.md`

4. Define MVP-safe tool contract subset and enforcement layer.
- Evidence: `docs/architecture_v2/05_phase_4_tool_execution_layer/tool_contracts.md`, `src/ai_orchestrator/runtime/healthcheck.py`, `src/ai_orchestrator/provider/vast.py`

5. Define transitional local mutation interface matching future CDOS adapter shape.
- Evidence: `docs/architecture_v2/06_phase_5_repo_interaction/repo_mutation_engine.md`, `docs/architecture_v2/08_cdos_integration_layer/cdos_integration_spec.md`, `src/ai_orchestrator/`
