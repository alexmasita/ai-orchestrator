# Bootstrap Tests

Bootstrap tests verify that runtime bootstrap scripts are generated correctly.

Bootstrap scripts configure the GPU instance to run the required services.

## Bootstrap Script Generation

Bootstrap scripts are generated using deterministic templates.

Tests validate that:

- scripts contain required commands
- scripts are deterministic
- scripts remain within size limits

## Script Size Limits

The orchestrator enforces a strict bootstrap script size limit.


MAX_BOOTSTRAP_SCRIPT_BYTES = 16384


Tests verify that oversized scripts cause a validation error.

## Service Startup

Bootstrap scripts start two services:

DeepSeek runtime  
Whisper runtime

Tests verify that the script contains the correct startup commands.

## Script Validation

The orchestrator validates that:

- scripts are strings
- scripts are not empty
- scripts are within size limits

Tests ensure validation failures occur before provider calls.

## Deterministic Script Generation

Running the script generator multiple times must produce identical scripts.

Tests compare generated scripts byte-for-byte.