Phase 2 — Model Runtime Manager
Purpose

This phase introduces hardware-aware role execution and model lifecycle management.

This is where AI-Orchestrator becomes real under current GPU limits.

Responsibilities

load model by role

unload inactive role model

health check runtime

measure load and unload timing

expose readiness state

serialize conflicting load operations

enforce combo-specific residency rules

Non-Goals

repository mutation

loop supervision

policy learning