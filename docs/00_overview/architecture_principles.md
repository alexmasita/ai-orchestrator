Architecture Principles

The architecture of ai-orchestrator is guided by a set of strict engineering principles that ensure reliability, extensibility, and testability.

1. Determinism First

The system must behave deterministically wherever possible.

Examples:

identical inputs must produce identical orchestration decisions

CLI output must be deterministic

bootstrap script generation must be deterministic

unit tests must never depend on external services

Determinism enables:

reproducible deployments

reliable automated testing

predictable system behavior

2. Layered Architecture

The system is divided into clearly defined layers:

CLI
↓
Orchestrator
↓
Sizing Engine
↓
Model Plugins
↓
Provider Interface
↓
Provider Implementation (Vast)
↓
Runtime Bootstrap
↓
Healthcheck System

Each layer has a well-defined responsibility and interacts with adjacent layers only through explicit contracts.

3. Provider Abstraction

Infrastructure providers are accessed through a common interface.

This ensures that:

orchestration logic is provider-agnostic

providers can be replaced or added

provider implementations can evolve independently

The provider interface defines methods such as:

search_offers()
create_instance()
4. Fail Fast

Configuration errors and provider failures must be detected early and reported clearly.

The system avoids silent failure.

Examples:

missing configuration values raise explicit errors

provider response schema mismatches raise errors

dependency issues produce clear error messages

5. Testability

Every major component must be testable in isolation.

Testing constraints include:

no real network access

deterministic inputs

predictable outputs

The provider layer is tested using mocked HTTP responses.

6. Minimal Runtime State

The system avoids maintaining internal state.

Each CLI execution performs a complete orchestration workflow:

determine requirements
select offer
create instance
bootstrap runtime
wait for readiness
return result

This simplifies reasoning about system behavior.