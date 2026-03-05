# Repository Layout

This document describes the top-level layout of the `ai-orchestrator` repository and the role of each directory and file.

The repository is intentionally structured to enforce a **clean separation between runtime code, configuration, orchestration logic, and deterministic testing.**

The project uses a **src-layout Python package structure** to prevent accidental imports from the project root and ensure correct packaging behavior.

---

# Top-Level Structure

Example repository layout:


ai-orchestrator/
│
├── src/
│ └── ai_orchestrator/
│
├── tests/
│
├── docs/
│
├── config.yaml
├── launch.sh
├── pyproject.toml
├── setup.cfg
│
└── README.md (optional)


---

# Directory Overview

## src/

Contains **all runtime source code** for the orchestrator system.

The project follows the **src-layout packaging pattern**:


src/
ai_orchestrator/


Advantages:

- Prevents accidental imports from project root
- Matches Python packaging best practices
- Ensures installed package matches runtime behavior
- Avoids shadowing during tests

---

## tests/

Contains **all unit and contract tests**.

Characteristics:

- Fully deterministic
- No network access
- Extensive use of monkeypatching
- Strict separation from runtime code

Tests validate:

- CLI behavior
- configuration parsing
- runtime bootstrap generation
- provider interface contracts
- Vast provider integration logic
- selection and sizing algorithms
- healthcheck system
- plugin architecture

---

## docs/

Contains **architecture and developer documentation**.

Documentation is organized into logical sections:


docs/
00_overview/
01_repository_structure/
02_environment_setup/
...


The documentation is designed to allow engineers to:

- understand the system architecture
- rebuild the system from scratch
- safely extend the orchestrator

---

# Top-Level Files

## config.yaml

Primary runtime configuration file.

Contains:

- Vast API credentials
- GPU selection constraints
- network requirements
- reliability filters
- pricing limits
- model sizing configuration

Example usage:


ai-orchestrator start --config config.yaml --models deepseek_llamacpp whisper


---

## launch.sh

Convenience script for running the orchestrator locally.

Purpose:

- simplify repeated launches
- ensure execution from project root
- verify CLI availability

Example:


./launch.sh


Equivalent command:


ai-orchestrator start
--config config.yaml
--models deepseek_llamacpp whisper


---

## pyproject.toml

Defines:

- build system
- runtime dependencies
- packaging metadata
- console entrypoints

Important dependency examples:


requests
PyYAML


---

## setup.cfg

Defines:

- package discovery
- entrypoints for CLI commands

Example:


[options.entry_points]
console_scripts =
ai-orchestrator = ai_orchestrator.cli:main


This creates the command:


ai-orchestrator


---

# Architectural Goals of the Layout

The repository structure enforces several architectural principles:

### Separation of Concerns

Runtime code:


src/ai_orchestrator


Tests:


tests/


Documentation:


docs/


Configuration:


config.yaml


---

### Deterministic Development

The project structure ensures:

- tests never rely on external state
- runtime behavior can be reproduced locally
- configuration is explicit

---

### Safe Extension

The layout makes it easy to add:

- additional providers
- new model plugins
- runtime components
- operational tooling

without breaking existing architecture.

---

# Key Design Invariants

The repository layout enforces the following invariants:

1. Runtime code only exists inside `src/ai_orchestrator`.
2. Tests never import from project root.
3. Configuration is externalized into YAML.
4. Provider implementations remain modular.
5. Plugin architecture remains extensible.
6. Tests remain fully deterministic.

These invariants prevent architectural drift as the system evolves.