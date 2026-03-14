Determinism Guarantees

Determinism is a core design requirement of ai-orchestrator.

The system must behave predictably when provided with identical inputs.

Deterministic CLI Output

CLI JSON output uses sorted keys.

Example:

json.dumps(result, sort_keys=True)

This ensures that repeated runs produce identical output ordering.

Deterministic Bootstrap Scripts

Bootstrap scripts must be generated deterministically.

This ensures:

reproducible environments

identical startup behavior

Deterministic Offer Selection

Given the same set of provider offers, the orchestrator must select the same offer.

Selection criteria include:

VRAM requirements

reliability threshold

price limits

interruptibility constraints

Deterministic Tests

All tests must be deterministic.

Rules:

no randomness

no time-based logic

no network access

no dependency on external systems

Deterministic Provider Payloads

Provider API requests must generate consistent payload structures.

Example:

deterministic JSON ordering

stable request parameters

Deterministic Runtime Ports

Service ports are fixed and deterministic.

DeepSeek: 8080
Whisper: 9000

This enables deterministic readiness checks.

If you'd like, the next logical step is generating the next architecture section:

docs/01_repository_structure/

Those documents will explain:

how the repository is structured

how each module maps to the architecture

how engineers should navigate the codebase.