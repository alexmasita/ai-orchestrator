Overview

This guide explains how to add a new model plugin without breaking system invariants.

Step 1 — Create Plugin File

Create a plugin file in:

src/ai_orchestrator/plugins/

Example:

my_model_plugin.py
Step 2 — Implement Plugin Class

Example structure:

class MyModelPlugin:

    name = "my_model"

    required_vram_gb = 12
    required_disk_gb = 8
    service_port = 7000
Step 3 — Register Plugin

Add to registry:

PLUGINS["my_model"] = MyModelPlugin
Step 4 — Define Bootstrap Behavior

Add startup logic for the model service.

Example responsibilities:

install dependencies

download model

start service

Step 5 — Define Healthcheck Port

Choose a unique port.

Avoid collisions with:

Service	Port
DeepSeek	8080
Whisper	9000
Step 6 — Update Sizing Logic

Ensure resource requirements are integrated into the sizing engine.

Step 7 — Write Tests

Required tests:

plugin registration

deterministic requirements

sizing integration

Example test file:

tests/test_my_model_plugin.py
Plugin Development Rules

Plugins must follow strict rules:

Deterministic behavior

No randomness.

No external network calls

Model downloads must occur only during bootstrap.

No environment inspection

Plugin logic must not depend on runtime machine state.

Validation Checklist

Before merging a plugin:

deterministic outputs

ports unique

sizing integrated

tests added

registry updated

Summary

The plugin layer allows the system to support new AI models without modifying the orchestrator core.

Plugins provide:

model requirements

runtime configuration

bootstrap integration

while preserving:

deterministic orchestration

provider independence

test isolation.