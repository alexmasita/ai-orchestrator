# NeuroFlow Runtime Architecture

## Purpose

This document describes how the `neuroflow` combo is launched, how external
services should discover its URLs, how to test it, and what data contracts are
available today.

It is written for operators who:

- create and destroy Vast instances frequently
- need stable discovery for changing public IPs and host ports
- want external systems to call the `interpret`, `reasoner`, `rerank`, `stt`,
  `tts`, and `control` services safely


## High-Level Architecture

The current runtime has four layers:

1. Control plane launcher
   - Commands:
     - `ai-orchestrator wizard`
     - `ai-orchestrator start --combo neuroflow`
     - `ai-orchestrator resolve --combo neuroflow --instance-id <id>`
   - Responsibility: select combo, create or reuse Vast instances, resolve
     public endpoints deterministically, and publish runtime records

2. Vast provider integration
   - File: `src/ai_orchestrator/provider/vast.py`
   - Responsibility: create instance, poll instance metadata, expose public IP
     and host-port mappings

3. NeuroFlow runtime instance
   - Files:
     - `combos/neuroflow/combo.yaml`
     - `combos/neuroflow/bootstrap.sh`
   - Responsibility: install/download assets on first boot, launch all model
     services, expose local service ports inside the container

4. External consumers
   - Responsibility: discover the latest public URLs for the current instance
     and call the appropriate service endpoints


## Service Topology

Internal container ports are fixed by the combo manifest:

```yaml
interpret: 8080
reasoner: 8081
rerank: 8082
stt: 9000
tts: 9001
control: 7999
```

Public URLs are not fixed.

Vast allocates new public host ports each time an instance is created, so the
 effective public URLs look like:

```text
http://<public_ip>:<host_port>
```

Example from a successful run:

```text
CONTROL_URL=http://173.207.82.240:40005
INTERPRET_URL=http://173.207.82.240:40036
REASONER_URL=http://173.207.82.240:40035
RERANK_URL=http://173.207.82.240:40021
STT_URL=http://173.207.82.240:40001
TTS_URL=http://173.207.82.240:40037
```


## Launch Flow

Current end-to-end flow:

1. User runs one of:

   ```bash
   .venv/bin/ai-orchestrator wizard
   .venv/bin/ai-orchestrator start --combo neuroflow
   .venv/bin/ai-orchestrator resolve --combo neuroflow --instance-id 32890211
   ```

2. CLI resolves combo runtime state from:
   - `config.yaml`
   - `configs/neuroflow.yaml`
   - `combos/neuroflow/combo.yaml`
   - `combos/neuroflow/bootstrap.sh`

3. Vast provider either:
   - creates a new instance, or
   - reuses / restarts an existing instance selected by the operator

4. CLI polls Vast instance metadata until:
   - the instance is running
   - public port mappings exist for all declared services
   - `control_url/health` is externally reachable
   - all declared services report `up`

5. CLI resolves public URLs by combining:
   - `public_ipaddr`
   - `ports["<container_port>/tcp"][0]["HostPort"]`

6. CLI writes the resolved runtime record to any configured `runtime_file_paths`
   plus any `--write-runtime-file` destinations.

7. CLI prints final JSON to stdout.


## Runtime Bundle Schema

NeuroFlow publishes one primary runtime bundle and, when at least one live
probe succeeds, one companion probe bundle.

Primary file:

- `combos/neuroflow/neuroflow-runtime.json`

Companion file:

- `combos/neuroflow/neuroflow-runtime-probes.json`

Current NeuroFlow runtime success payload:

```json
{
  "runtime_schema_version": "2026-03-15-neuroflow-runtime-v1",
  "instance_id": "32870552",
  "status": "ready",
  "resolved_at": "2026-03-15T07:14:07+00:00",
  "gpu_type": "A100 SXM4",
  "cost_per_hour": 0.8333333333333333,
  "idle_timeout": 1200,
  "snapshot_version": "v2-neuroflow-dev-80gb",
  "interpret_url": "http://<ip>:<port>",
  "reasoner_url": "http://<ip>:<port>",
  "rerank_url": "http://<ip>:<port>",
  "stt_url": "http://<ip>:<port>",
  "tts_url": "http://<ip>:<port>",
  "control_url": "http://<ip>:<port>",
  "runtime_readiness": {
    "live_integration_ready": true,
    "notes": []
  },
  "capabilities": {
    "interpret": {
      "name": "interpret",
      "base_url": "http://<ip>:<port>",
      "health_url": "http://<ip>:<port>/health",
      "provider_kind": "vllm_openai_compatible",
      "api_style": "openai_chat_completions",
      "model_alias": "interpret",
      "upstream_model": "Qwen/Qwen3-32B-AWQ",
      "auth_required": false,
      "ready": true,
      "last_probe": "2026-03-15T07:14:07+00:00",
      "health_status": "up",
      "health_http_status": 200,
      "recommended_timeout_ms": 20000,
      "request_content_type": "application/json",
      "response_kind": "json"
    }
  },
  "publication_status": "success" | "partial" | "failed" | "not_requested",
  "runtime_file_writes": [
    {
      "path": "/abs/path/to/runtime.json",
      "status": "written" | "failed",
      "error": null | "permission denied"
    }
  ]
}
```

Notes:

- Runtime files are written by atomic overwrite, so existing files are replaced.
- `runtime_file_writes` includes both the primary runtime file and the probe
  sidecar when the probe bundle is emitted.
- Stopped or rebooted instances must always be re-resolved before external
  consumers trust the endpoints again.
- No legacy env-bridge aliases are emitted; clients should read the runtime
  bundle directly.


## Probe Bundle Schema

When live probing is at least partially successful, NeuroFlow also writes:

```json
{
  "runtime_schema_version": "2026-03-15-neuroflow-runtime-probes-v1",
  "resolved_at": "2026-03-15T07:14:07+00:00",
  "instance_id": "32870552",
  "capability_probes": {
    "interpret": {
      "probe_request": {"model": "interpret"},
      "probe_http_status": 200,
      "response_sample": {"object": "chat.completion"}
    },
    "tts": {
      "probe_request": {"model": "kokoro", "voice": "af_heart"},
      "probe_http_status": 200,
      "response_sample": {
        "content_type": "audio/mpeg",
        "content_length": 27692,
        "binary_preview_base64": "SUQzBAAAAAAAIlRTU0UAAA=="
      }
    }
  }
}
```

If a capability cannot be fully probed, the runtime bundle marks it with
`probe_incomplete` and includes the real reason in `runtime_readiness.notes`.

For STT specifically, NeuroFlow uses a hybrid probe strategy:

- prefer a tiny checked-in deterministic WAV fixture at
  `combos/neuroflow/assets/stt-probe.wav`
- fall back to a generated WAV built from the TTS probe output when the fixture
  is unavailable
- if neither works, keep publication successful but mark STT probe incomplete
  with explicit `probe_strategy` and `probe_error`


## Control API Contract

The `control` service is the best runtime introspection endpoint once
`control_url` is known.

Routes:

- `GET /status`
- `GET /health`
- `POST /ping`
- `POST /stop`
- `POST /destroy`

Current `GET /health` response shape:

```json
{
  "services": {
    "interpret": {"status": "up", "code": 404},
    "reasoner": {"status": "up", "code": 404},
    "rerank": {"status": "up", "code": 404},
    "stt": {"status": "up", "code": 404},
    "tts": {"status": "up", "code": 404},
    "control": {"status": "up"}
  },
  "timestamp": "2026-03-14T18:53:47.872975+00:00"
}
```

Current `GET /status` response shape:

```json
{
  "instance_id": "C.32866662",
  "stage": "tts_health_check",
  "status": "ready",
  "message": "tts responding on port 9001",
  "timestamp": "2026-03-14T18:46:23Z",
  "is_snapshot": true,
  "ports": {
    "interpret": 8080,
    "reasoner": 8081,
    "rerank": 8082,
    "stt": 9000,
    "tts": 9001,
    "control": 7999
  }
}
```

Important:

- `is_snapshot` here means the runtime setup marker exists inside the container.
- It does **not** prove a Vast snapshot image was used.


## Service API Summary

### Interpret

- Base URL: `interpret_url`
- Type: vLLM OpenAI-compatible generation endpoint
- Key routes:
  - `GET /v1/models`
  - `POST /v1/chat/completions`

### Reasoner

- Base URL: `reasoner_url`
- Type: vLLM OpenAI-compatible generation endpoint
- Key routes:
  - `GET /v1/models`
  - `POST /v1/chat/completions`

### Rerank

- Base URL: `rerank_url`
- Type: vLLM reranking / scoring endpoint
- Key routes:
  - `GET /v1/models`
  - `POST /rerank`
  - `POST /score`

### STT

- Base URL: `stt_url`
- Type: Faster-Whisper transcription endpoint
- Key routes:
  - `GET /health`
  - `POST /v1/audio/transcriptions`
- Probe strategy:
  - `fixture` for the checked-in WAV path
  - `generated` for generated WAV fallback
  - `unverified` if no valid audio fixture could be produced

### TTS

- Base URL: `tts_url`
- Type: Kokoro OpenAI-compatible speech endpoint
- Key routes:
  - `GET /docs`
  - `POST /v1/audio/speech`


## Capability Metadata

Each entry under `capabilities` includes enough information for external
clients to call NeuroFlow without guessing:

- `name`
- `base_url`
- `health_url`
- `provider_kind`
- `api_style`
- `model_alias`
- `upstream_model`
- `auth_required`
- `ready`
- `last_probe`
- `health_status`
- `health_http_status`
- `recommended_timeout_ms`
- `request_content_type`
- `response_content_type` or `response_kind`

Current provider kinds:

- `control_api`
- `vllm_openai_compatible`
- `faster_whisper_custom`
- `kokoro_fastapi_openai_compatible`


## Testing Runbook

## Runtime File Publication

Recommended combo config:

```yaml
runtime_file_paths:
  - /abs/path/to/consumer-a/neuroflow-runtime.json
  - /abs/path/to/consumer-b/neuroflow-runtime.json
```

Behavior:

- relative paths resolve from the repo root / current working directory
- directory paths expand to `<directory>/neuroflow-runtime.json`
- file paths are treated as primary runtime bundle destinations
- the probe bundle is always derived as a sibling `-probes.json` file
- existing files are overwritten atomically
- `--write-runtime-file` adds one-off destinations on top of config
- partial publication is reported per path
- when the wizard finds no configured runtime destinations, it offers a repo-local default:
  - `.ai-orchestrator/runtime/neuroflow-runtime.json`
- restarted stopped instances use a separate bounded wait budget:
  - `restart_transition_timeout_seconds`
  - if a reused instance stays in `scheduling` / `starting` / `loading` too long, the wizard offers remediation instead of waiting for the full `instance_ready_timeout_seconds`

Example directory-style config:

```yaml
runtime_file_paths:
  - /Users/macbook/dev/ai-orchestrator/combos/neuroflow
```

This publishes to:

```text
/Users/macbook/dev/ai-orchestrator/combos/neuroflow/neuroflow-runtime.json
```

and, when live probes succeed at least partially:

```text
/Users/macbook/dev/ai-orchestrator/combos/neuroflow/neuroflow-runtime-probes.json
```

Recommended explicit file-path config:

```yaml
runtime_file_paths:
  - /Users/macbook/Library/Mobile Documents/com~apple~CloudDocs/NeuroFlow_Experiments/moldavite/neuroflow-mvp/.runtime/neuroflow/neuroflow-runtime.json
```

This publishes:

```text
/Users/macbook/Library/Mobile Documents/com~apple~CloudDocs/NeuroFlow_Experiments/moldavite/neuroflow-mvp/.runtime/neuroflow/neuroflow-runtime.json
/Users/macbook/Library/Mobile Documents/com~apple~CloudDocs/NeuroFlow_Experiments/moldavite/neuroflow-mvp/.runtime/neuroflow/neuroflow-runtime-probes.json
```

Do not list the probe file itself in `runtime_file_paths`, because NeuroFlow
already derives it automatically from the primary runtime bundle path.


## Testing Runbook

### 1. Guided launch

```bash
.venv/bin/ai-orchestrator wizard
```

Wizard controls:

- enter a number to select a combo, instance, or runtime-file option
- enter `b` to go back when a step allows it
- enter `q` to cancel cleanly
- pressing `Ctrl-C` exits the wizard with `Wizard cancelled.` instead of a traceback
- if a restarted instance gets stuck in `scheduling`, the wizard can:
  - destroy it and start a new one
  - start a new one and keep the old one
  - extend the restart wait by 5 minutes
  - return to instance selection

### 2. Non-interactive launch with runtime file publication

```bash
.venv/bin/ai-orchestrator start --combo neuroflow \
  --write-runtime-file /tmp/neuroflow-runtime.json | tee /tmp/neuroflow-start.json
```

### 3. Resolve an existing instance and overwrite runtime files

```bash
.venv/bin/ai-orchestrator resolve --combo neuroflow \
  --instance-id 32890211 \
  --write-runtime-file /tmp/neuroflow-runtime.json
```

### 4. Export discovered URLs

```bash
export CONTROL_URL="$(jq -r '.control_url' /tmp/neuroflow-runtime.json)"
export INTERPRET_URL="$(jq -r '.interpret_url' /tmp/neuroflow-runtime.json)"
export REASONER_URL="$(jq -r '.reasoner_url' /tmp/neuroflow-runtime.json)"
export RERANK_URL="$(jq -r '.rerank_url' /tmp/neuroflow-runtime.json)"
export STT_URL="$(jq -r '.stt_url' /tmp/neuroflow-runtime.json)"
export TTS_URL="$(jq -r '.tts_url' /tmp/neuroflow-runtime.json)"
```

### 5. Smoke test

```bash
curl -sS "$CONTROL_URL/health" | jq
curl -sS "$INTERPRET_URL/v1/models" | jq
curl -sS "$REASONER_URL/v1/models" | jq
curl -sS "$RERANK_URL/v1/models" | jq
curl -sS "$STT_URL/health" | jq
curl -sS "$TTS_URL/docs" > /dev/null && echo tts-docs-ok
```


## External Discovery Problem

The core problem is that the public URLs are ephemeral:

- instance IDs change
- public IPs change
- public host ports change
- CLI output may temporarily contain `null` URL fields

Because of that, external systems should **not** hardcode model URLs.


## Recommended Discovery Architecture

Use a small external service registry.

Recommended pattern:

1. Launcher starts the NeuroFlow instance.
2. Launcher captures the JSON output.
3. Launcher stores that output in a stable registry record.
4. External systems query the registry, not Vast and not local shell exports.
5. External systems then call `control_url/health` to confirm the runtime is
   alive before using the model endpoints.

### Why this is the best current approach

- The CLI already knows the resolved public URLs.
- The runtime container does not know its public Vast host-port mappings.
- The bootstrap webhook/state file is useful for lifecycle telemetry, but not as
  a complete external discovery source because it only knows internal ports.


## Recommended External Registry Schema

Store one record per active NeuroFlow instance:

```json
{
  "combo_name": "neuroflow",
  "instance_id": "32870552",
  "snapshot_version": "v2-neuroflow-dev-80gb",
  "gpu_type": "A100 SXM4",
  "cost_per_hour": 0.8333333333333333,
  "idle_timeout": 1200,
  "created_at": "2026-03-14T19:00:00Z",
  "status": "starting|ready|inactive",
  "services": {
    "control": {
      "url": "http://<ip>:<port>",
      "health_url": "http://<ip>:<port>/health"
    },
    "interpret": {
      "url": "http://<ip>:<port>",
      "models_url": "http://<ip>:<port>/v1/models"
    },
    "reasoner": {
      "url": "http://<ip>:<port>",
      "models_url": "http://<ip>:<port>/v1/models"
    },
    "rerank": {
      "url": "http://<ip>:<port>",
      "models_url": "http://<ip>:<port>/v1/models"
    },
    "stt": {
      "url": "http://<ip>:<port>",
      "health_url": "http://<ip>:<port>/health"
    },
    "tts": {
      "url": "http://<ip>:<port>",
      "docs_url": "http://<ip>:<port>/docs"
    }
  }
}
```


## Recommended Automation Patterns

### Pattern A: File-based local registry

For simple use cases, persist the launcher JSON:

```bash
.venv/bin/ai-orchestrator start --combo neuroflow --config config.yaml > /tmp/neuroflow-instance.json
```

Then make downstream jobs read `/tmp/neuroflow-instance.json`.

### Pattern B: HTTP registry service

Best for multi-service environments.

Flow:

1. Launcher starts instance.
2. Launcher POSTs the JSON output to a stable internal service such as:
   - `/v1/runtime-instances`
3. Consumers GET the latest active NeuroFlow record from that service.

### Pattern C: DNS or reverse proxy indirection

Best long-term production pattern.

Flow:

1. External registry learns latest URLs.
2. A reverse proxy updates backend targets.
3. External callers use stable names such as:
   - `https://interpret.example.internal`
   - `https://reasoner.example.internal`

This is the cleanest way to hide changing Vast IPs and host ports.


## Running From A Snapshot Image

The best way to run a previously exported NeuroFlow snapshot in the current
architecture is:

1. use the pushed snapshot image as the Vast base image
2. keep the existing NeuroFlow bootstrap script

Why this works:

- the snapshot image should already contain the downloaded models and the
  `.setup_complete` marker
- the bootstrap still starts services and preserves the same runtime contract
- first-boot setup can be skipped while keeping the existing service topology

Example `configs/neuroflow.yaml` override:

```yaml
image: alexmasita/ai-neuroflow-snapshots:instance_32873649_at_March_14th_2026_at_09-44-20_PM_UTC
```

Launch command stays the same:

```bash
.venv/bin/ai-orchestrator start --combo neuroflow --config config.yaml
```

Operational note:

- if the snapshot image is missing the expected workspace state, the bootstrap
  may still fall back to full setup behavior
- the runtime contract is unchanged, so external systems should still discover
  URLs through the launcher JSON or a registry service


## Best Current Recommendation

Given the current repo:

1. Keep using `ai-orchestrator start --combo neuroflow --config config.yaml`
2. Capture stdout JSON every time
3. Persist that JSON in a stable registry outside the Vast instance
4. Make external services fetch runtime URLs from that registry
5. Use `control_url/health` as the readiness gate before calling other routes

This is the most reliable current approach without requiring the runtime
container itself to know public host-port mappings.
