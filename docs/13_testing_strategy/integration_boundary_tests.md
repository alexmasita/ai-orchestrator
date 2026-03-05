# Integration Boundary Tests

Integration boundary tests validate interactions between system layers.

These tests ensure that layer contracts remain stable.

## Layer Boundaries

The system contains several integration boundaries:

CLI → Orchestrator  
Orchestrator → Provider  
Orchestrator → Runtime  
Runtime → Healthcheck  

Each boundary has tests verifying correct interaction.

## Orchestrator to Provider

Tests verify that the orchestrator sends the correct instance configuration to providers.

Example configuration fields:


bootstrap_script
idle_timeout_seconds


Tests confirm that these fields propagate correctly.

## Provider to Runtime

Provider instance objects must contain fields used by runtime logic.

Example:


instance_id
gpu_name
dph
public_ip


Tests validate that these values are returned correctly.

## CLI to Orchestrator

CLI tests verify that CLI arguments correctly propagate to orchestration logic.

Example:


--models deepseek_llamacpp whisper


## Contract Stability

Integration tests ensure that internal changes do not break layer contracts.

If a contract changes, tests must be updated accordingly.

## Architectural Safety

These tests protect the system from architectural drift.

They ensure that new features do not break the orchestration pipeline.