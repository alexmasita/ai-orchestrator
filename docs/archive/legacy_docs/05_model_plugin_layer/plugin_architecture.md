Overview

The Model Plugin Layer provides a deterministic mechanism for defining the resource and runtime requirements of models used by the orchestrator.

It allows the system to support multiple models while keeping the orchestrator core provider-agnostic and model-agnostic.

Each plugin defines:

resource requirements

runtime startup configuration

bootstrap script fragments

sizing metadata

The plugin layer ensures that the orchestrator can:

compute required GPU resources

generate runtime bootstrap scripts

launch model services on predictable ports

without hardcoding model logic in the orchestrator core.

Architectural Position

The plugin layer sits between the CLI model selection and the sizing engine.

CLI
 ↓
Model Plugins
 ↓
Sizing Engine
 ↓
Offer Selection
 ↓
Provider

CLI passes the model list:

--models deepseek_llamacpp whisper

The orchestrator then loads the corresponding plugins to determine system requirements.

Plugin Responsibilities

Each plugin must define:

Responsibility	Description
model identification	unique plugin name
resource requirements	VRAM, disk, network
runtime configuration	ports and services
bootstrap instructions	shell script fragments
Plugin Lifecycle

When orchestration begins:

CLI receives model names

Registry resolves plugins

Sizing engine aggregates requirements

Runtime bootstrap generator composes startup script

Example flow:

models = ["deepseek_llamacpp", "whisper"]

registry.resolve(models)

→ plugin objects returned

→ sizing engine aggregates requirements

→ bootstrap script generated
Plugin Isolation

Plugins must not perform side effects.

Allowed behavior:

declare requirements

return deterministic metadata

Forbidden behavior:

network calls

environment inspection

randomness

file system modification

This preserves deterministic orchestration behavior.

Deterministic Requirements

Plugins must produce identical outputs given identical inputs.

Example:

DeepSeekPlugin.requirements()

must always return identical values.

This guarantees:

reproducible orchestration

deterministic offer selection

predictable bootstrap scripts

Ports and Runtime Contracts

Each plugin defines service ports.

Example:

Model	Port
DeepSeek	8080
Whisper	9000

Ports are part of system invariants and cannot change without breaking compatibility.

Plugin Data Structures

Typical plugin metadata:

{
  name: "deepseek_llamacpp",
  required_vram_gb: 20,
  required_disk_gb: 10,
  service_port: 8080
}

These values are consumed by:

sizing engine

bootstrap script generator

readiness checks

Plugin Determinism Guarantees

Plugins must satisfy the following:

deterministic outputs

no environment dependencies

stable service ports

stable resource declarations

Violation of these rules will break orchestration reproducibility.