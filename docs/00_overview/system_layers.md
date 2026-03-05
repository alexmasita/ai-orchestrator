System Layers

The architecture of ai-orchestrator consists of several logical layers.

Each layer is responsible for a specific portion of the orchestration pipeline.

CLI Layer
↓
Orchestrator Core
↓
Sizing Engine
↓
Model Plugin Layer
↓
Provider Interface
↓
Provider Implementation
↓
Runtime Bootstrap
↓
Healthcheck System
CLI Layer

The CLI layer provides the primary user interface.

Responsibilities:

parse command-line arguments

load configuration

invoke orchestration

print final JSON output

Main module:

src/ai_orchestrator/cli.py
Orchestrator Core

The orchestrator coordinates the entire provisioning workflow.

Responsibilities:

selecting a suitable provider offer

generating bootstrap scripts

requesting instance creation

performing readiness checks

Main module:

src/ai_orchestrator/orchestrator.py
Sizing Engine

The sizing engine determines the hardware requirements for requested models.

Responsibilities:

VRAM estimation

disk requirements

network requirements

Main module:

src/ai_orchestrator/sizing.py
Model Plugin Layer

Model plugins define the runtime characteristics of individual models.

Examples:

deepseek_llamacpp
whisper

Plugins declare:

VRAM usage

disk usage

runtime dependencies

Modules:

plugins/base.py
plugins/registry.py
plugins/deepseek_llamacpp.py
Provider Interface

Defines a generic contract for interacting with infrastructure providers.

Responsibilities:

searching for available GPU offers

creating compute instances

Module:

provider/interface.py
Provider Implementation

Implements the provider interface for specific providers.

Currently implemented:

provider/vast.py

Responsibilities:

calling Vast API endpoints

parsing responses

converting results into internal objects

Runtime Bootstrap

Bootstrap scripts configure the newly created instance.

Responsibilities:

installing runtime dependencies

launching AI services

exposing required ports

Modules:

runtime/bootstrap.py
runtime/script.py
runtime/snapshot.py
Healthcheck System

Ensures services are operational before returning control to the user.

Responsibilities:

port readiness checks

HTTP endpoint checks

timeout handling

Module:

runtime/healthcheck.py