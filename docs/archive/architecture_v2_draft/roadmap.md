AI-Orchestrator Roadmap
Phase 1 — Orchestrator Core
Objectives

FastAPI control plane

session manager

combo registry

telemetry envelope

mutation abstraction interface

Success Criteria

create and manage sessions

invoke roles structurally

persist orchestrator state

Risks

core service sprawl

premature feature layering

Phase 2 — Model Runtime Manager
Objectives

model lifecycle control

health checks

swap-safe runtime

role-specific serving

Success Criteria

reliable architect/developer load/unload

context reconstruction after swap

Risks

swap instability

backend coupling

Phase 3 — Agent Loop
Objectives

architect/developer loop

packet schemas

failure packet flow

bounded iteration

Success Criteria

complete multi-step coding loop with stop control

Risks

packet design too loose

over-reliance on raw transcripts

Phase 4 — Tool Ecosystem
Objectives

structured tools

security controls

bounded command execution

patch request routing

Success Criteria

developer can inspect, patch, verify via tools

Risks

tool abuse

insufficient observability

Phase 5 — Repo Mutation Abstraction Maturity
Objectives

stabilize RepoMutationEngine

improve LocalRepoEngine

prepare for CDOS adapter

Success Criteria

orchestrator loop independent of mutation backend internals

Risks

local-engine shortcuts leaking into orchestrator design

Phase 6 — CDOS Integration
Objectives

implement CDOSMutationEngine

route intelligence and patching via CDOS

preserve deterministic kernel boundary

Success Criteria

end-to-end loop through CDOS

no forbidden overlap

Risks

responsibility leakage

contract mismatch

Phase 7 — Autonomous Supervisor
Objectives

autonomy modes

loop supervision

checkpointing

escalation policy

Success Criteria

bounded autonomous task execution

Risks

runaway loops

weak stop conditions

Phase 8 — Self-Improvement Layer
Objectives

prompt registry

policy registry

evaluation harness

controlled experimentation

Success Criteria

measurable improvement without runtime drift

Risks

overfitting

silent prompt drift

Phase 9 — Real-Time UX and Voice
Objectives

websocket telemetry

human supervision UI

voice intent integration above orchestrator

Success Criteria

live controllable sessions

safe supervisory workflow

Risks

UX overreach before runtime maturity