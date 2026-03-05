Purpose

Bootstrap scripts must remain within provider size limits.

Infrastructure providers impose limits on:

startup scripts

metadata fields

environment variables

To guarantee compatibility, ai-orchestrator enforces strict script size validation.

Maximum Script Size

The orchestrator enforces the following limit:

MAX_BOOTSTRAP_SCRIPT_BYTES = 16384

Equivalent to 16 KB.

Enforcement Location

The limit is enforced inside:

run_orchestration()

before the instance is created.

Example logic:

script_bytes = script.encode("utf-8")

if len(script_bytes) > MAX_BOOTSTRAP_SCRIPT_BYTES:
    raise ValueError("bootstrap script exceeds provider size limit")
Why the Limit Exists

Providers typically restrict startup script sizes:

Provider	Limit
Vast	~16 KB
AWS user-data	16 KB
GCP metadata scripts	~32 KB

Using a conservative limit ensures cross-provider compatibility.

Deterministic Enforcement

The script size check occurs before provider interaction.

This prevents:

unnecessary instance creation

partial deployments

What Happens When Limit Is Exceeded

The orchestrator raises:

ValueError("bootstrap script exceeds provider size limit")

This failure happens before:

provider.create_instance()
Mitigation Strategies

If scripts grow too large:

Possible solutions include:

move setup logic to external scripts

download runtime scripts from repository

use container images

use snapshot-based boot environments

Testing

Script size limits are validated by:

tests/test_bootstrap_script_limits.py

These tests ensure:

scripts exceeding limits fail

scripts within limits succeed