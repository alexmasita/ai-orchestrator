AI-Orchestrator — Current System Baseline
Purpose of This Document

This document defines the actual architecture of the repository at the time of analysis.

It exists to prevent architectural drift between:

repository implementation

legacy documentation

new architecture documents

All future architecture work must begin from this baseline.

This document intentionally describes what currently exists, not what is planned.

System Identity

AI-Orchestrator currently functions as an infrastructure orchestration system for GPU inference runtimes.

Its primary responsibility is to:

provision compute instances

configure model runtimes

deploy bootstrap scripts

wait for service readiness

expose service endpoints

The system does not yet implement autonomous reasoning loops, tool execution orchestration, or repository mutation capabilities.

Those capabilities exist only in architecture documents.

High-Level System Architecture

Current runtime architecture:

CLI
  ↓
Orchestrator
  ↓
Provider Integration
  ↓
Instance Provisioning
  ↓
Bootstrap Script Injection
  ↓
Runtime Service Startup
  ↓
Readiness Health Checks
  ↓
Resolved Service Endpoints

This architecture focuses on infrastructure provisioning and runtime startup.

Core Responsibilities

The repository currently implements the following responsibilities:

Infrastructure Provisioning

The system provisions GPU instances using external provider APIs.

Responsibilities include:

selecting offers

creating instances

passing bootstrap scripts

polling instance readiness

Primary modules:

src/ai_orchestrator/orchestrator.py
src/ai_orchestrator/provider/vast.py
Runtime Bootstrap Deployment

Once instances are created, bootstrap scripts configure the runtime environment.

These scripts typically start:

LLM inference servers

auxiliary services

control APIs

monitoring processes

Example bootstrap location:

combos/reasoning_80gb/bootstrap.sh

Bootstrap scripts define the runtime topology inside the instance.

Combo Runtime Configuration

The system supports combo configurations representing pre-defined runtime setups.

Combos describe:

model roles

service endpoints

hardware assumptions

runtime parameters

Primary artifacts:

combos/reasoning_80gb/combo.yaml
configs/reasoning_80gb.yaml
src/ai_orchestrator/core/combo_manager.py

Combos act as deployment templates for runtime environments.

Runtime Health Verification

The orchestrator waits for services to become ready before reporting success.

Health checks include:

port availability

HTTP readiness endpoints

retry and timeout logic

Primary implementation:

src/ai_orchestrator/runtime/healthcheck.py
Service Endpoint Resolution

Once services are healthy, the system returns resolved endpoints.

These typically include:

inference endpoints

speech services

control APIs

Endpoint discovery is coordinated by:

src/ai_orchestrator/orchestrator.py
src/ai_orchestrator/core/service_registry.py
CLI Orchestration Interface

The primary user interface is a CLI tool.

Command example:

ai-orchestrator start

The CLI performs:

configuration loading

combo resolution

orchestration flow invocation

JSON result output

Primary module:

src/ai_orchestrator/cli.py
Development Control APIs

Two auxiliary API services exist.

Development server:

src/ai_orchestrator/devserver/app.py

Control API:

control_api.py

These provide endpoints such as:

/health

/status

/stop

/destroy

These APIs interact with runtime state files and control scripts.

Implemented Subsystems

The following subsystems are currently implemented.

CLI Layer

Responsibilities:

command parsing

configuration loading

orchestration invocation

JSON output formatting

Primary file:

src/ai_orchestrator/cli.py
Orchestrator Core

Responsibilities:

resource requirement computation

offer selection

instance provisioning

bootstrap injection

endpoint resolution

Primary files:

src/ai_orchestrator/orchestrator.py
src/ai_orchestrator/sizing.py
Provider Integration Layer

Responsibilities:

provider API abstraction

offer discovery

instance creation

retry logic

Primary files:

src/ai_orchestrator/provider/interface.py
src/ai_orchestrator/provider/vast.py
src/ai_orchestrator/provider/mock.py
Combo Runtime Layer

Responsibilities:

runtime template selection

role configuration

service endpoint definitions

Primary files:

src/ai_orchestrator/combos/loader.py
src/ai_orchestrator/core/combo_manager.py

Runtime definitions:

combos/reasoning_80gb/combo.yaml
configs/reasoning_80gb.yaml
Runtime Bootstrap System

Responsibilities:

generating runtime environment scripts

configuring service startup

injecting environment variables

Primary files:

src/ai_orchestrator/runtime/script.py
combos/reasoning_80gb/bootstrap.sh
Runtime Health Monitoring

Responsibilities:

readiness polling

port checks

HTTP health endpoints

Primary file:

src/ai_orchestrator/runtime/healthcheck.py
State Management Utilities

Responsibilities:

writing runtime state files

atomic state updates

Primary file:

src/ai_orchestrator/core/state_manager.py

This module does not implement a session system.

Testing Infrastructure

The repository contains extensive contract-oriented testing.

Testing includes:

CLI contract validation

provider mocking

bootstrap validation

combo configuration tests

readiness tests

Primary directories:

tests/
tests/pass1/
tests/pass_combo2/
tests/pass_combo_cli/

Testing philosophy emphasizes:

deterministic outputs

mock providers

contract verification

Model Runtime Strategy

Model serving is externalized to provisioned instances.

The orchestrator does not host model inference directly.

Instead it:

provisions infrastructure

deploys runtime bootstrap scripts

waits for services to become ready

Example services started by bootstrap scripts include:

vLLM inference servers

FastAPI services

speech services

monitoring utilities

Example artifact:

combos/reasoning_80gb/bootstrap.sh
Current Operational Workflow

Typical execution flow:

User executes CLI command
        ↓
Configuration is loaded
        ↓
Combo runtime is resolved
        ↓
Provider offer search executed
        ↓
Instance created
        ↓
Bootstrap script injected
        ↓
Runtime services start
        ↓
Health checks poll readiness
        ↓
Endpoints returned to user
Architecture Boundaries

The current system deliberately limits its scope.

It does not perform:

repository editing

autonomous reasoning loops

tool orchestration

agent decision pipelines

model hot-swap runtime control

These capabilities are future architecture targets.

Known Architectural Gaps

Based on the architecture analysis, the following components are not implemented.

Session Manager

No session lifecycle system exists.

Missing features:

session creation

session persistence

session resume

session termination

Model Runtime Manager

Model lifecycle control is not implemented.

Missing features:

model load/unload

runtime hot-swap

memory scheduling

Agent Loop Supervisor

There is no iterative reasoning pipeline.

Missing features:

architect role

developer role

reasoning iteration

failure analysis

Tool Execution Gateway

No structured tool execution system exists.

Missing features:

tool request schema

tool allowlist

sandbox execution

tool result schema

Repository Mutation Engine

The system does not support repository modification.

Missing features:

patch creation

patch validation

commit lifecycle

CDOS integration

Governance Layer

No runtime policy engine exists.

Missing features:

autonomy modes

policy enforcement

telemetry schemas

Packet Protocol System

Architecture documents define packet schemas such as:

ArchitectPlan

DeveloperPatch

FailurePacket

These are not implemented in code.

Relationship to Architecture v2

The architecture_v2 documents define a future AI-orchestration architecture.

Those documents describe capabilities such as:

autonomous coding loops

tool orchestration

session management

CDOS integration

reasoning pipelines

These capabilities do not exist yet in the repository implementation.

They represent target architecture, not current behavior.

Architectural Positioning

The current repository provides the infrastructure layer for the future system.

Future AI-Orchestrator components will operate on top of this infrastructure.

Conceptual layering:

Future AI-Orchestrator
    ↓
Runtime Manager
    ↓
Current Infrastructure Orchestrator
    ↓
GPU Runtime Instances

Thus the current repository should be viewed as:

Infrastructure Control Plane for AI Runtime Environments

Architectural Invariants for This Baseline

The following statements describe invariant properties of the current system.

The orchestrator provisions compute infrastructure but does not host inference directly.

Model runtimes are started through bootstrap scripts executed inside provisioned instances.

The CLI is the primary orchestration interface.

Combo configurations define runtime topology.

Health checks gate successful orchestration completion.

Provider integrations handle infrastructure provisioning.

Deterministic testing is a core development principle.

Why This Baseline Matters

Future architecture work must avoid rewriting the system based on assumptions.

This document establishes the authoritative description of the existing repository architecture.

All architecture proposals must explicitly state whether they:

extend the baseline

replace parts of the baseline

layer additional systems above the baseline