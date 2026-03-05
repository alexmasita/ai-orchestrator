# Error Model

This document defines the **error-handling architecture** used throughout the ai-orchestrator system.

The error model ensures that:

1. Errors are **typed and deterministic**
2. Errors propagate **cleanly across system layers**
3. The CLI produces **predictable user-facing output**
4. **Tracebacks never leak to end users**
5. Tests can reliably validate failure modes

---

# Design Goals

The system enforces several key error-handling principles:

### 1. Layer Isolation

Each architectural layer raises **its own error types**.

Errors are not passed upward as raw Python exceptions unless explicitly intended.

Example:


requests.exceptions.RequestException
↓
VastProviderError
↓
CLI prints provider error message


---

### 2. Deterministic Behavior

Errors must be **fully deterministic**.

The following must never occur:

- random retries
- time-dependent behavior
- hidden side effects
- partial state mutation

If an error occurs, the operation must either:


fail completely


or


return a fully valid result


No intermediate states are allowed.

---

### 3. No Raw Tracebacks in CLI

The CLI must **never show a Python traceback** to the user.

All expected operational failures must be converted into clean messages.

Example:


Provider error: Vast /bundles request failed: DNS resolution failed


instead of


Traceback (most recent call last):
...


---

### 4. Explicit Error Types

The system defines **explicit domain-specific exceptions**.

Primary error classes include:

| Error Type | Purpose |
|------------|--------|
| `ConfigError` | Configuration loading failures |
| `OrchestratorConfigError` | Invalid runtime configuration |
| `VastProviderError` | Provider API failures |
| `RuntimeError` | Instance readiness failures |

These classes ensure each system layer can be reasoned about independently.

---

# Error Flow Across System Layers

The system consists of the following layers:


CLI
↓
Configuration Loader
↓
Sizing Engine
↓
Orchestrator
↓
Provider Interface
↓
Vast Provider
↓
Runtime Bootstrap
↓
Runtime Healthchecks


Errors propagate upward through this stack.

Example flow:


requests failure
↓
VastProviderError
↓
run_orchestration fails
↓
CLI catches VastProviderError
↓
CLI prints provider error message


---

# Layer Error Responsibilities

Each layer has a defined responsibility.

## CLI Layer

Responsible for:

- catching expected error types
- converting them into user-facing messages
- returning exit code `1`

---

## Configuration Layer

Responsible for:

- validating configuration files
- detecting missing or malformed fields

Raises:


ConfigError


---

## Sizing Engine

Responsible for:

- validating model requirements
- validating model-specific config

Raises:


OrchestratorConfigError


---

## Orchestrator

Responsible for:

- orchestration flow
- runtime bootstrap generation
- instance lifecycle

Raises:


ValueError
RuntimeError


depending on the failure.

---

## Provider Layer

Responsible for:

- communicating with cloud providers
- validating API responses

Raises:


VastProviderError


---

## Runtime Layer

Responsible for:

- service startup
- readiness detection

Raises:


RuntimeError


---

# Deterministic Failure Behavior

Failures must not cause:

- partially created instances
- partial bootstrap execution
- inconsistent CLI output

If a failure occurs before readiness, the CLI exits with code `1`.

---

# Logging Behavior

Error messages follow strict logging rules:

| Channel | Usage |
|------|------|
| stdout | JSON success output only |
| stderr | error messages |
| debug stderr | debug logs when enabled |

Environment variable:


AI_ORCH_DEBUG=1


enables verbose debugging.

---

# Summary

The ai-orchestrator error model ensures:

- deterministic behavior
- predictable CLI output
- strict layer isolation
- no hidden failures
- testable failure modes

This architecture is critical to maintaining system reliability and operational transparency.