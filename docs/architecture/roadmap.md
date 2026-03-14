AI-Orchestrator Development Roadmap
Purpose

This document defines the development roadmap for AI-Orchestrator.

It translates the architecture into a practical implementation sequence.

The roadmap ensures that the system evolves in controlled stages while preserving architectural invariants.

Each phase introduces new capabilities while maintaining system stability.

Development Philosophy

The system will be built incrementally following three rules:

Build minimal working layers first

Validate each layer before adding the next

Preserve deterministic infrastructure

Infrastructure stability must never be compromised by experimental reasoning systems.

Current System State (Phase 0)

The current repository already implements infrastructure orchestration.

Capabilities currently implemented include:

CLI interface
provider integration
GPU instance provisioning
bootstrap script injection
runtime health checks
service endpoint resolution
combo runtime configuration

Key modules include:

src/ai_orchestrator/cli.py
src/ai_orchestrator/orchestrator.py
src/ai_orchestrator/provider/vast.py
src/ai_orchestrator/runtime/healthcheck.py
src/ai_orchestrator/core/combo_manager.py

This layer forms the Infrastructure Control Plane.

Phase 1 — Session Layer
Objective

Introduce the concept of bounded execution sessions.

Sessions provide the foundation for autonomous workflows.

Required Components
SessionManager
SessionStore
SessionLifecycle
Responsibilities

The session layer manages:

session creation
session persistence
session resume
session termination
session configuration
Proposed Implementation

Directory:

src/ai_orchestrator/session/

Initial modules:

session_manager.py
session_models.py
session_store.py
Success Criteria

The system can:

create sessions
track session state
resume interrupted sessions
terminate sessions safely
Phase 2 — Model Runtime Manager
Objective

Introduce controlled model execution.

The runtime manager schedules models according to hardware constraints.

Hardware Constraint
Single GPU
~94GB VRAM

Because of this constraint:

only one large model can run at a time
models must be hot-swapped
Responsibilities

Runtime manager controls:

model load
model unload
model swap
inference routing
context reconstruction
Proposed Implementation

Directory:

src/ai_orchestrator/runtime_manager/

Modules:

runtime_manager.py
model_registry.py
runtime_scheduler.py
Success Criteria

The runtime manager can:

load architect model
unload architect model
load developer model
route inference requests
preserve reasoning context
Phase 3 — Agent Loop
Objective

Introduce the autonomous development loop.

This is the core cognitive system.

Agent Roles
Architect
Developer
Loop Structure

Example workflow:

Architect → create plan
Developer → generate patch
Runner → execute tests
Architect → analyze failures
Developer → refine patch
Required Components
LoopSupervisor
ArchitectAgent
DeveloperAgent
VerificationRunner
FailureAnalyzer
Proposed Implementation

Directory:

src/ai_orchestrator/agent_loop/

Modules:

loop_supervisor.py
architect_agent.py
developer_agent.py
verification_runner.py
failure_analyzer.py
Success Criteria

The system can:

execute iterative development loops
generate code patches
run verification tests
adapt based on failures
Phase 4 — Tool Execution Gateway
Objective

Introduce controlled system interaction.

Tools allow agents to interact with the environment.

Tool Categories

Examples include:

read_file
write_file
search_repo
run_tests
run_command
list_files
Required Components
ToolGateway
ToolRegistry
ToolExecutor
Proposed Implementation

Directory:

src/ai_orchestrator/tools/

Modules:

tool_gateway.py
tool_registry.py
tool_executor.py
Success Criteria

Agents can:

inspect repositories
modify files
execute tests
run controlled commands

All tool executions must remain observable and sandboxed.

Phase 5 — Repository Mutation Layer
Objective

Introduce structured repository mutation.

This layer converts AI-generated patches into safe repository changes.

Mutation Interface
RepoMutationEngine

Implementations:

LocalRepoEngine
CDOSMutationEngine
LocalRepoEngine

Used during MVP development.

Responsibilities:

apply patches
run verification tests
commit changes
Proposed Implementation

Directory:

src/ai_orchestrator/repo_engine/

Modules:

repo_mutation_engine.py
local_repo_engine.py
Success Criteria

The system can:

apply patches
run verification pipelines
create commits
Phase 6 — Autonomous Supervisor
Objective

Introduce governance and safety.

This layer supervises autonomous reasoning.

Responsibilities
loop limits
failure classification
escalation policies
autonomy modes
Proposed Implementation

Directory:

src/ai_orchestrator/governance/

Modules:

autonomy_controller.py
failure_classifier.py
loop_limits.py
Success Criteria

The system prevents:

infinite loops
runaway tool usage
unsafe repository mutations
Phase 7 — CDOS Integration
Objective

Integrate deterministic mutation workflows.

Responsibilities
draft lifecycle management
snapshot immutability
deterministic patch application
commit locking
Integration Boundary

AI-Orchestrator responsibilities:

planning
tool execution
orchestration

CDOS responsibilities:

mutation lifecycle
repository state transitions
deterministic intelligence
Proposed Implementation

Directory:

src/ai_orchestrator/integrations/cdos/

Modules:

cdos_adapter.py
cdos_client.py
Phase 8 — Self-Improvement Layer
Objective

Allow the system to improve its reasoning strategies.

Potential Capabilities
prompt registry
policy registry
evaluation pipelines
experiment tracking
Proposed Implementation

Directory:

src/ai_orchestrator/improvement/

Modules:

prompt_registry.py
policy_registry.py
evaluation_runner.py
Final Architecture

When all phases are complete, the system architecture becomes:

Intent Interface
    ↓
Session Layer
    ↓
Agent Loop
    ↓
Model Runtime Manager
    ↓
Tool Gateway
    ↓
Repository Mutation Layer
    ↓
Infrastructure Orchestrator
    ↓
GPU Runtime Environment
MVP Definition

The minimal viable system requires only:

Session Manager
Runtime Manager
Agent Loop
Tool Gateway
LocalRepoEngine

All other subsystems can be added later.

Summary

This roadmap ensures the system evolves from:

infrastructure orchestrator

to

autonomous development orchestration system

while preserving architectural stability.