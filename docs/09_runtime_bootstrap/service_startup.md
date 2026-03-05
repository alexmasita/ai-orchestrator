Purpose

The bootstrap script launches all inference services required by the orchestrator.

Services are started automatically when the instance boots.

Runtime Services

The current runtime launches:

Service	Port
DeepSeek LLM	8080
Whisper ASR	9000

These ports are fixed system invariants.

Startup Strategy

Services are launched in background processes.

Example pattern:

deepseek_server --port 8080 &
whisper_server --port 9000 &
Background Execution

Services must not block the bootstrap script.

This ensures instance startup completes.

Example:

command &
Service Isolation

Each runtime service:

runs independently

exposes its own port

provides HTTP APIs

Required Service Properties

Services must:

bind to deterministic ports

run as background processes

remain active after bootstrap completes

Readiness Dependency

The orchestrator waits for these services using:

wait_for_instance_ready()

This ensures services are reachable before the CLI returns.

Runtime Failures

If services fail to start:

readiness checks will fail

orchestration will raise a runtime error