# tests Directory

The `tests/` directory contains the complete test suite for the orchestrator.

The testing strategy focuses on:

- deterministic execution
- contract validation
- provider mocking
- strict isolation

Tests are written using **pytest**.

---

# Test Categories

The test suite validates all system layers.

Example structure:


tests/
│
├── test_cli_start_command.py
├── test_cli_gpu_type_output.py
│
├── test_config_loader.py
│
├── test_sizing_engine.py
│
├── test_selection_engine.py
│
├── test_plugin_contract.py
├── test_deepseek_plugin.py
│
├── test_runtime_bootstrap.py
├── test_runtime_bootstrap_script.py
├── test_runtime_healthcheck.py
├── test_runtime_snapshot.py
│
├── test_orchestrator_output.py
├── test_orchestrator_bootstrap_injection.py
├── test_orchestrator_instance_readiness.py
├── test_orchestrator_idle_timeout.py
│
├── test_provider_interface.py
├── test_vast_provider.py
├── test_vast_provider_bootstrap_injection.py
│
└── test_registry_determinism.py


---

# Deterministic Testing Philosophy

All tests must be deterministic.

This means:

- no real network calls
- no randomness
- no time-based behavior
- no external system dependencies

Provider interactions are simulated using monkeypatching.

---

# Provider Mocking

The Vast provider uses HTTP requests.

Tests replace these with mocked responses:


monkeypatch.setattr(requests, "post", fake_post)


This ensures:

- zero external API usage
- deterministic behavior

---

# Bootstrap Script Tests

Bootstrap tests validate:

- deterministic script generation
- script size limits
- script structure

These tests ensure runtime environments remain reproducible.

---

# Healthcheck Tests

Healthcheck tests simulate service readiness.

Examples:

- port open checks
- HTTP response checks
- timeout behavior

---

# Orchestrator Tests

These validate orchestration flow:

- instance creation
- bootstrap injection
- readiness waits
- output schema

---

# CLI Tests

CLI tests verify:

- command parsing
- configuration loading
- output formatting
- deterministic JSON output

---

# Contract Tests

Provider and plugin layers use contract tests to enforce interfaces.

These tests guarantee:

- provider methods exist
- expected fields are returned
- plugins follow required structure

---

# Why Deterministic Tests Matter

The orchestrator provisions infrastructure.

If tests depended on real providers, they would be:

- slow
- unreliable
- expensive

Deterministic tests ensure:

- fast feedback loops
- reliable CI pipelines
- safe architectural refactoring