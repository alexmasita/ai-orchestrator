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
   - Command: `ai-orchestrator start --combo neuroflow --config config.yaml`
   - Responsibility: select Vast offer, create instance, poll for public port
     mappings, print runtime URLs

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

1. User runs:

   ```bash
   .venv/bin/ai-orchestrator start --combo neuroflow --config config.yaml
   ```

2. CLI resolves combo runtime state from:
   - `config.yaml`
   - `configs/neuroflow.yaml`
   - `combos/neuroflow/combo.yaml`
   - `combos/neuroflow/bootstrap.sh`

3. Vast provider creates a new instance.

4. CLI polls Vast instance metadata until public port mappings appear.

5. CLI resolves public URLs by combining:
   - `public_ipaddr`
   - `ports["<container_port>/tcp"][0]["HostPort"]`

6. CLI prints JSON to stdout.


## CLI Output Schema

Current combo-start success payload:

```json
{
  "instance_id": "32870552",
  "gpu_type": "A100 SXM4",
  "cost_per_hour": 0.8333333333333333,
  "idle_timeout": 1200,
  "snapshot_version": "v2-neuroflow-dev-80gb",
  "interpret_url": "http://<ip>:<port>" | null,
  "reasoner_url": "http://<ip>:<port>" | null,
  "rerank_url": "http://<ip>:<port>" | null,
  "stt_url": "http://<ip>:<port>" | null,
  "tts_url": "http://<ip>:<port>" | null,
  "control_url": "http://<ip>:<port>" | null
}
```

Notes:

- URL fields may be `null` if Vast port mappings are not yet visible when the
  CLI returns.
- The CLI now waits longer for mappings before printing output, but consumers
  must still tolerate `null` and retry discovery.


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

### TTS

- Base URL: `tts_url`
- Type: Kokoro OpenAI-compatible speech endpoint
- Key routes:
  - `GET /docs`
  - `POST /v1/audio/speech`


## Testing Runbook

### 1. Launch

```bash
.venv/bin/ai-orchestrator start --combo neuroflow --config config.yaml | tee /tmp/neuroflow-start.json
```

### 2. Export discovered URLs

```bash
export CONTROL_URL="$(jq -r '.control_url' /tmp/neuroflow-start.json)"
export INTERPRET_URL="$(jq -r '.interpret_url' /tmp/neuroflow-start.json)"
export REASONER_URL="$(jq -r '.reasoner_url' /tmp/neuroflow-start.json)"
export RERANK_URL="$(jq -r '.rerank_url' /tmp/neuroflow-start.json)"
export STT_URL="$(jq -r '.stt_url' /tmp/neuroflow-start.json)"
export TTS_URL="$(jq -r '.tts_url' /tmp/neuroflow-start.json)"
```

### 3. If one or more URLs are `null`

Retry discovery by polling Vast instance metadata or by re-running the launcher
after the instance is fully established. The current launcher attempts to wait
for port mappings, but external automation must still handle delayed mappings.

### 4. Smoke test

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


## Best Current Recommendation

Given the current repo:

1. Keep using `ai-orchestrator start --combo neuroflow --config config.yaml`
2. Capture stdout JSON every time
3. Persist that JSON in a stable registry outside the Vast instance
4. Make external services fetch runtime URLs from that registry
5. Use `control_url/health` as the readiness gate before calling other routes

This is the most reliable current approach without requiring the runtime
container itself to know public host-port mappings.
