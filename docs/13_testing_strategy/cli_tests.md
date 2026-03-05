# CLI Tests

The CLI is the entry point for the entire orchestration system.

CLI tests validate that the command interface behaves correctly and produces deterministic outputs.

## CLI Command Coverage

Tests validate the behavior of:


ai-orchestrator start


The CLI must:

1. load configuration
2. compute sizing requirements
3. run orchestration
4. output JSON results

## CLI Pipeline Mocking

CLI tests isolate CLI logic by monkeypatching the orchestration pipeline.

Example:


monkeypatch.setattr(cli_module, "run_orchestration", fake_result)


This allows testing CLI behavior without executing infrastructure logic.

## Output Validation

CLI tests verify the output schema.

Expected output keys include:


instance_id
gpu_type
cost_per_hour
deepseek_url
whisper_url


Tests verify that:

- output contains required keys
- raw provider keys are not exposed
- JSON serialization is deterministic

## GPU Field Mapping

Provider responses may contain:


gpu_name
dph


The CLI maps these to:


gpu_type
cost_per_hour


Tests enforce this mapping.

## Error Handling

CLI tests verify that configuration and provider errors are handled cleanly.

Instead of raw tracebacks, the CLI prints readable messages.

Example:


Provider error: <message>


## Deterministic Output

Tests run CLI twice with identical inputs and confirm identical JSON output.