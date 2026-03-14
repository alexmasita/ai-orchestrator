System Layers
Purpose

This document defines the layered architecture of the AI-Orchestrator system.

The purpose of the layered architecture is to ensure:

separation of responsibilities

deterministic control boundaries

safe reasoning orchestration

compatibility with CDOS deterministic mutation rules

hardware-aware model scheduling

Each layer has strict responsibilities and invariants.

Layers must communicate only through defined interfaces.

Architectural Overview

The AI-Orchestrator architecture separates infrastructure orchestration from cognitive orchestration.

Conceptual stack:

User Intent
    ↓
Intent Interface
    ↓
Session Layer
    ↓
Agent Loop Layer
    ↓
Model Runtime Layer
    ↓
Tool Execution Layer
    ↓
Repository Mutation Layer
    ↓
Infrastructure Orchestration Layer
    ↓
GPU Runtime Environment

Each layer is described below.

Layer 1 — Intent Interface
Responsibility

The Intent Interface is responsible for receiving high-level requests from users or external systems.

These requests may include:

software development tasks

repository modification tasks

runtime orchestration tasks

analysis or debugging requests

The intent interface does not perform reasoning itself.

Instead, it converts requests into structured session inputs.

Typical Implementations

Examples include:

CLI commands

HTTP APIs

IDE integrations

automated pipelines

Current repository evidence:

src/ai_orchestrator/cli.py
src/ai_orchestrator/devserver/app.py
control_api.py
Layer 2 — Session Layer
Responsibility

The Session Layer manages the lifecycle of autonomous work sessions.

A session represents a bounded execution context containing:

user intent

session configuration

reasoning history

tool interactions

repository mutation state

Sessions provide:

isolation

persistence

reproducibility

Session Responsibilities

The session layer manages:

session creation

session persistence

session resume

session termination

Session objects serve as the anchor for cognitive state.

Current Status

Not yet implemented.

Current partial state utilities:

src/ai_orchestrator/core/state_manager.py
Layer 3 — Agent Loop Layer
Responsibility

The Agent Loop Layer coordinates autonomous reasoning cycles.

It implements the architect → developer → verification loop.

Example cycle:

Architect → plan
Developer → implement
Runner → test
Architect → analyze results
Developer → patch
repeat

This layer contains the core intelligence orchestration.

Key Components

Agent Loop components include:

Architect role

Developer role

Loop supervisor

Failure analyzer

Verification coordinator

Loop Structure

The loop is packet-driven.

Example packet flow:

ArchitectPlan
    ↓
DeveloperPatch
    ↓
ToolRequest
    ↓
ToolResult
    ↓
FailurePacket
Current Status

Not implemented.

The repository currently performs infrastructure orchestration only.

Layer 4 — Model Runtime Layer
Responsibility

The Model Runtime Layer manages LLM execution environments.

Responsibilities include:

model loading

model unloading

GPU memory allocation

model hot-swapping

inference request routing

Hardware Constraint

The current target environment uses:

Single GPU
~94GB VRAM

Because of this constraint:

architect and developer models cannot run simultaneously

models must be hot-swapped

Runtime Responsibilities

The runtime manager must:

start model servers

stop model servers

reconstruct model context

route inference requests

Current Implementation

Partial runtime logic exists through instance bootstrap scripts.

Evidence:

combos/reasoning_80gb/bootstrap.sh
src/ai_orchestrator/core/combo_manager.py

However, a dedicated runtime manager is not implemented.

Layer 5 — Tool Execution Layer
Responsibility

The Tool Execution Layer provides controlled access to system capabilities.

Tools allow the AI system to interact with the environment.

Examples:

reading files

writing files

searching repositories

executing commands

running tests

Tool Gateway

All tool execution must pass through a gateway that enforces:

tool allowlists

execution limits

sandbox boundaries

structured outputs

Tool Interface

Each tool follows a contract:

ToolRequest
ToolExecution
ToolResult
Current Status

Not implemented.

Layer 6 — Repository Mutation Layer
Responsibility

The Repository Mutation Layer manages controlled modifications to source code repositories.

This layer ensures:

deterministic patch creation

safe mutation workflows

versioned state transitions

Mutation Abstraction

Mutations are executed through a common interface:

RepoMutationEngine

Possible implementations:

LocalRepoEngine
CDOSMutationEngine
LocalRepoEngine

Used during MVP development.

Responsibilities:

file patch generation

patch validation

test execution

commit creation

CDOSMutationEngine

Future integration layer.

Responsibilities:

deterministic patch lifecycle

draft state transitions

snapshot immutability

commit-locked intelligence

Current Status

Not implemented.

Layer 7 — Infrastructure Orchestration Layer
Responsibility

This layer provisions and manages runtime infrastructure.

It is responsible for:

instance provisioning

runtime configuration

bootstrap injection

readiness verification

Current Implementation

This layer already exists.

Key modules:

src/ai_orchestrator/orchestrator.py
src/ai_orchestrator/provider/vast.py
src/ai_orchestrator/runtime/healthcheck.py
src/ai_orchestrator/core/combo_manager.py
Bootstrap System

Bootstrap scripts define runtime services.

Example:

combos/reasoning_80gb/bootstrap.sh

These scripts launch:

vLLM servers

speech services

control APIs

monitoring agents

Layer 8 — Runtime Environment

The runtime environment consists of:

GPU instances

model servers

inference APIs

control APIs

The orchestrator communicates with these services after startup.

Layer Interaction Rules

To preserve system stability, layers must obey the following rules.

Rule 1

Higher layers may depend on lower layers.

Lower layers must not depend on higher layers.

Rule 2

The Agent Loop Layer must not interact directly with infrastructure.

It must use the Model Runtime Layer.

Rule 3

Repository mutations must pass through the mutation engine.

Direct filesystem edits are forbidden.

Rule 4

Tool execution must pass through the Tool Gateway.

Rule 5

Model inference must pass through the runtime manager.

Architectural Positioning

The current repository implements:

Infrastructure Orchestration Layer

Future development will add:

Session Layer
Agent Loop Layer
Model Runtime Layer
Tool Execution Layer
Repository Mutation Layer
Governance Layer

Together these layers will form the complete AI-Orchestrator architecture.