# src/ai_orchestrator Directory

This directory contains the entire runtime implementation of the orchestrator system.

The module is installed as a Python package:


ai_orchestrator


Directory structure:


src/ai_orchestrator/
│
├── cli.py
├── config.py
├── orchestrator.py
├── sizing.py
│
├── plugins/
│
├── provider/
│
└── runtime/


Each module represents a **distinct architectural layer** of the system.

---

# Core Modules

## cli.py

Entry point for the system.

Responsible for:

- parsing CLI arguments
- loading configuration
- invoking orchestration
- printing deterministic JSON output

Primary command:


ai-orchestrator start


The CLI must guarantee:

- deterministic JSON output
- no stdout noise
- stderr-only error reporting

---

## config.py

Handles configuration loading and normalization.

Responsibilities:

- load YAML configuration
- fallback parsing when PyYAML unavailable
- normalize API URLs
- strip quotes from YAML values
- validate configuration structure

Normalization rules include:

- removing surrounding quotes
- trimming whitespace
- removing trailing slashes

Example:


"https://console.vast.ai/api/v0/
"


becomes


https://console.vast.ai/api/v0


---

## orchestrator.py

The core orchestration engine.

Responsible for:

- selecting GPU offers
- provisioning instances
- injecting bootstrap scripts
- waiting for runtime readiness
- producing orchestration results

Primary function:


run_orchestration()


The orchestrator coordinates:


CLI
↓
Sizing engine
↓
Offer selection
↓
Provider instance creation
↓
Runtime bootstrap
↓
Health checks
↓
Final result


---

## sizing.py

Determines system resource requirements based on selected models.

Responsibilities:

- calculate VRAM requirements
- enforce disk requirements
- validate model-specific configuration
- enforce network requirements

Example requirements:


whisper_vram_gb
whisper_disk_gb


If configuration is incomplete, an error is raised:


OrchestratorConfigError


---

# plugins/

Contains **model runtime plugins**.

Each plugin defines:

- runtime requirements
- bootstrap steps
- resource constraints

Example:


plugins/
base.py
registry.py
deepseek_llamacpp.py


---

## base.py

Defines the plugin interface contract.

All plugins must implement required methods.

---

## registry.py

Registers available plugins.

Responsible for:

- discovering plugins
- validating plugin interface
- deterministic plugin registration

---

## deepseek_llamacpp.py

Plugin implementation for DeepSeek running with `llama.cpp`.

Defines:

- VRAM requirements
- runtime startup commands
- inference port configuration

---

# provider/

Defines the provider abstraction layer.


provider/
interface.py
mock.py
vast.py


---

## interface.py

Defines the provider contract.

Includes:

- ProviderInstance
- ProviderOffer
- provider methods:


search_offers()
create_instance()
destroy_instance()


---

## mock.py

Mock provider used for testing.

Allows orchestration logic to run without network access.

---

## vast.py

Implementation of the Vast GPU marketplace provider.

Handles:

- searching offers
- creating instances
- parsing API responses
- wrapping API errors

---

# runtime/

Handles runtime provisioning and health monitoring.


runtime/
bootstrap.py
healthcheck.py
script.py
snapshot.py


---

## bootstrap.py

Generates deterministic bootstrap scripts for remote instances.

Responsibilities:

- install runtime dependencies
- launch model services
- configure ports

---

## script.py

Handles bootstrap script generation and validation.

Includes:

- script size limits
- deterministic script generation

---

## healthcheck.py

Waits for runtime readiness.

Checks:


http://instance:8080

http://instance:9000


---

## snapshot.py

Handles runtime snapshot logic for reproducible environments.

Used to support instance reuse and deterministic deployments.

---

# Architectural Principle

The `src/ai_orchestrator` directory represents a **layered architecture**:


CLI
↓
Orchestrator
↓
Sizing
↓
Plugins
↓
Provider
↓
Runtime


Each layer has **clear contracts and responsibilities**, preventing cross-layer coupling.