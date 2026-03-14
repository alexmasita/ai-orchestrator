# Architecture Analysis Framework

This framework defines the architectural elements to verify during repository analysis.
It is intentionally implementation-agnostic and must be applied before drawing conclusions.

## 1) Runtime Entry Points
- What it represents:
  - Primary execution starts for services, workers, daemons, CLIs, and scripts.
- Typical code signals:
  - `if __name__ == "__main__"`, process startup functions, app factories, command dispatch.
  - Invocation wrappers for `uvicorn`, `gunicorn`, `node`, `python -m`, shell entry commands.
- Typical file naming patterns:
  - `main.py`, `app.py`, `server.py`, `run.py`, `start.sh`, `cli.py`, `manage.py`.
- Typical directory locations:
  - `services/`, `api/`, `backend/`, `bin/`, `scripts/`, project root.

## 2) Model Runtime Management
- What it represents:
  - Logic that starts/stops model backends, configures model providers, and manages inference runtime state.
- Typical code signals:
  - Provider clients, runtime pool/config, model registry, timeout/retry handling for inference.
- Typical file naming patterns:
  - `model_runtime.py`, `llm_client.py`, `provider.py`, `inference.py`, `runtime_manager.py`.
- Typical directory locations:
  - `services/`, `orchestrator/`, `runtime/`, `models/`, `adapters/`.

## 3) Agent Loop Logic
- What it represents:
  - Iterative reasoning/execution loop (plan -> act -> observe -> refine), including turn or step progression.
- Typical code signals:
  - Loop controllers, state machines, step executors, stop conditions, retries/escalation.
- Typical file naming patterns:
  - `agent_loop.py`, `executor.py`, `planner.py`, `controller.py`, `supervisor.py`.
- Typical directory locations:
  - `agent/`, `orchestrator/`, `core/`, `runtime/`.

## 4) API Servers
- What it represents:
  - HTTP/WS interfaces exposing orchestration or runtime functionality.
- Typical code signals:
  - FastAPI/Flask/Django/Express app instances, route handlers, middleware, schemas.
- Typical file naming patterns:
  - `main.py`, `api.py`, `routes.py`, `router.py`, `endpoints.py`.
- Typical directory locations:
  - `services/*/`, `api/`, `web/`, `server/`.

## 5) Tool Execution Infrastructure
- What it represents:
  - Safe invocation of tools/commands/functions and tool result mediation.
- Typical code signals:
  - Tool registries, executor wrappers, sandbox checks, command runners, structured tool calls.
- Typical file naming patterns:
  - `tools.py`, `tool_executor.py`, `registry.py`, `runner.py`, `sandbox.py`.
- Typical directory locations:
  - `tools/`, `orchestrator/tools/`, `runtime/tools/`, `integrations/`.

## 6) Repository Mutation Logic
- What it represents:
  - Controlled file edits, patch application, commit workflows, and guardrails around code changes.
- Typical code signals:
  - Patch builders/appliers, file write abstractions, git wrappers, mutation validation.
- Typical file naming patterns:
  - `patch.py`, `mutator.py`, `repo_ops.py`, `git_ops.py`, `apply_patch.py`.
- Typical directory locations:
  - `repo/`, `orchestrator/repo/`, `tools/`, `scripts/`.

## 7) Session Lifecycle Management
- What it represents:
  - Session creation, state persistence, resume/terminate behavior, and context continuity.
- Typical code signals:
  - Session IDs, stores, lifecycle transitions, persistence adapters.
- Typical file naming patterns:
  - `session.py`, `session_store.py`, `lifecycle.py`, `state_manager.py`.
- Typical directory locations:
  - `runtime/`, `state/`, `storage/`, `orchestrator/session/`.

## 8) Model Orchestration
- What it represents:
  - Coordination across multiple model calls, routing policies, fallback paths, and task-level model selection.
- Typical code signals:
  - Router strategies, policy objects, model selection rules, ensemble/fallback logic.
- Typical file naming patterns:
  - `router.py`, `orchestrator.py`, `policy.py`, `model_selector.py`.
- Typical directory locations:
  - `orchestrator/`, `runtime/`, `services/`, `adapters/`.

## 9) Configuration / Environment Handling
- What it represents:
  - Loading and validating runtime settings and environment variables.
- Typical code signals:
  - `.env` loading, settings classes, typed config validation, defaults/overrides.
- Typical file naming patterns:
  - `config.py`, `settings.py`, `.env.example`, `constants.py`.
- Typical directory locations:
  - project root, `config/`, `services/*/`.

## 10) Health Checks / Observability
- What it represents:
  - Service health, readiness/liveness probes, metrics, tracing, and structured logging.
- Typical code signals:
  - `/health` routes, metrics endpoints, logger setup, telemetry middleware.
- Typical file naming patterns:
  - `health.py`, `monitoring.py`, `logging.py`, `metrics.py`.
- Typical directory locations:
  - `services/*/`, `observability/`, `infra/`, `api/`.

## 11) Bootstrap / Infrastructure Scripts
- What it represents:
  - Scripts and automation that set up runtime environments, start local stacks, and provision dependencies.
- Typical code signals:
  - Docker compose hooks, shell automation, setup scripts, build scripts, CI bootstraps.
- Typical file naming patterns:
  - `bootstrap.sh`, `setup.sh`, `start*.sh`, `Makefile`, `docker-compose*.yml`.
- Typical directory locations:
  - `scripts/`, `infra/`, project root, `.github/workflows/`.

## 12) CLI Tools
- What it represents:
  - User/developer command-line interfaces for orchestration operations.
- Typical code signals:
  - argparse/click/typer commands, subcommand dispatch, command docs.
- Typical file naming patterns:
  - `cli.py`, `commands.py`, `__main__.py`.
- Typical directory locations:
  - `cli/`, `tools/`, `bin/`, package root.

## 13) Testing Infrastructure
- What it represents:
  - Automated tests, fixtures, harnesses, and validation tooling.
- Typical code signals:
  - `pytest`/`unittest` suites, fixture factories, integration/e2e harnesses.
- Typical file naming patterns:
  - `test_*.py`, `*_test.py`, `conftest.py`.
- Typical directory locations:
  - `tests/`, `services/*/tests/`, `integration_tests/`, `e2e/`.

## 14) Data Contracts / Packet Schemas
- What it represents:
  - Structured messages exchanged between subsystems (requests, responses, event packets).
- Typical code signals:
  - Pydantic/dataclass schemas, contract validators, versioned payload definitions.
- Typical file naming patterns:
  - `schema.py`, `types.py`, `contracts.py`, `packet.py`, `models.py`.
- Typical directory locations:
  - `schemas/`, `contracts/`, `api/`, `shared/`.

## Evidence Rules For PASS 2
- Every architectural claim must include concrete file-path evidence.
- Prefer direct code references over inferred intent.
- Mark unsupported concepts explicitly as missing or partially implemented.
- Distinguish implementation evidence from documentation-only claims.
