# Expected Output

When `ai-orchestrator start` executes successfully, the CLI prints a **deterministic JSON object** to `stdout`.

This JSON describes the provisioned GPU instance and the endpoints of the deployed services.

---

# Output Schema

The CLI output schema is fixed and must not change without a documented interface change.

```json
{
  "instance_id": "string",
  "gpu_type": "string",
  "cost_per_hour": "number",
  "idle_timeout": "integer",
  "snapshot_version": "string",
  "deepseek_url": "string",
  "whisper_url": "string"
}
Field Descriptions
instance_id

Identifier assigned by the provider.

Example:

abc123

This ID uniquely identifies the running GPU instance.

gpu_type

GPU model used by the instance.

Examples:

RTX_4090
RTX_A6000
A100

This value is mapped from the provider field gpu_name.

cost_per_hour

Hourly instance cost.

Example:

0.52

Mapped from the provider field dph.

idle_timeout

Configured shutdown timeout in seconds.

Example:

1800

After this time without activity the instance may terminate.

snapshot_version

Runtime snapshot version used to initialize the instance.

Example:

v1

Snapshots allow deterministic environment bootstrapping.

deepseek_url

HTTP endpoint for the DeepSeek inference service.

Example:

http://1.2.3.4:8080
whisper_url

HTTP endpoint for the Whisper transcription service.

Example:

http://1.2.3.4:9000
Deterministic Output

The JSON output is serialized using:

json.dumps(..., sort_keys=True)

This guarantees:

deterministic key ordering

reproducible CLI output

stable automation integration

Example sorted order:

cost_per_hour
deepseek_url
gpu_type
idle_timeout
instance_id
snapshot_version
whisper_url
Error Output

On failure the CLI prints a single-line error message to stderr.

Example:

Provider error: Vast /bundles request failed: DNS resolution error

Exit code will be non-zero.