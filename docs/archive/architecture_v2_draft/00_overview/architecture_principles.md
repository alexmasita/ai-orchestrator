Architecture Principles

These principles are non-negotiable.

Any future phase that violates them must be redesigned.

1. Separation of Cognition and Mutation

AI-Orchestrator is never the mutation authority.

It may plan mutation.
It may request mutation.
It may reason about mutation outcomes.

It must not directly own:

repository patch application

commit creation

snapshot lifecycle

deterministic draft finalization

When CDOS is present, all mutation must flow through CDOS.

Before CDOS integration, mutation must flow through a dedicated abstraction layer with the same authority boundaries.

2. Packetized Cognition

Correctness must never depend on live model KV cache.

All cross-step reasoning state must be externalized into structured packets.

Examples:

architect plan packets

developer patch packets

failure packets

verification summaries

session context bundles

If a model is unloaded and reloaded, the system must reconstruct sufficient state from packets and persisted summaries.

3. Hot-Swap First Runtime Design

The runtime must assume:

only one large model may be active at a time

model state is disposable

swap operations are normal, not exceptional

Architectures that require simultaneous residency of large architect and developer models are invalid for the current hardware class.

4. No Hidden In-Memory State for Correctness

In-memory state may improve speed, but correctness must not depend on it.

A session must remain recoverable from persisted structured state and telemetry.

5. Bounded Autonomy

All autonomous loops must be bounded by policy.

Examples:

max iterations

max tool budget

max patch attempts

max swap count

max runtime duration

escalation thresholds

AI-Orchestrator must never enter unbounded retry or self-modification loops.

6. Tool Use Must Be Structured and Observable

Models do not “get terminal access”.

Models produce structured tool invocation intents.

The system validates, executes, bounds, and records tool use through governed interfaces.

7. Mutation Compatibility with Deterministic Systems

The orchestrator must remain compatible with deterministic development kernels such as CDOS.

This means AI-Orchestrator must preserve:

explicit context requirements

explicit lifecycle transitions

patch authority boundaries

observational vs mutation separation

bounded tool contracts

8. Minimal Required Context

Each model invocation should receive the smallest context bundle required for correctness.

State reconstruction should be compact, structured, and phase-aware.

The system should prefer:

summaries

file slices

scoped search results

explicit failure packets

over unbounded transcript replay.

9. Governance Before Power

New autonomy features must be introduced only with:

policy boundaries

telemetry

rollback strategy

human interrupt path

explicit success criteria

10. Evolution Through Versioned Contracts

Prompts, tool schemas, handoff packets, policies, and integration contracts must be versioned.

Silent drift is forbidden.