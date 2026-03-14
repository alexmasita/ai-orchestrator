Combo Plugin Architecture
Purpose

AI-Orchestrator must preserve a combo-based model composition system so new orchestrated role combinations can be added with minimal code churn.

A combo defines:

role map

model identifiers

runtime constraints

serving parameters

residency assumptions

swap strategy

prompt strategy overrides

tool policy overrides

Combo Contract

A combo must declare:

combo name

supported roles

model reference per role

serving backend

memory profile

whether concurrent residency is allowed

preferred active role

swap warmup behavior

context packing strategy

safety notes

Example Combo Shape
name: reasoning_80gb
roles:
  architect:
    model: twhitworth/gpt-oss-120b-awq-w4a16
    backend: vllm
    concurrent_residency: false
  developer:
    model: cyankiwi/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit
    backend: vllm
    concurrent_residency: false
runtime:
  scheduling_mode: single_active
  preferred_hot_role: developer
  state_strategy: packetized
Design Rule

Combo plugins must not require orchestrator core rewrites.

They may extend behavior through declarative configuration and bounded adapter hooks.