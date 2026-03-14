System Layers

AI-Orchestrator is layered intentionally.

No upper layer may violate the contract of the layer below it.

Layer 0 — Intent Interface

Responsibilities:

receive user text intent

receive structured task requests

later receive normalized voice intent

attach session metadata and execution mode

Produces:

normalized task intent

Does not:

invoke models directly

mutate repository state

Layer 1 — Session Manager

Responsibilities:

create, resume, pause, cancel sessions

track iteration count

track current repo/task context

persist session metadata

maintain state needed for hot-swap reconstruction

Produces:

session state

context bundle inputs for reasoning phases

Does not:

host models

execute mutation

Layer 2 — Model Runtime Manager

Responsibilities:

manage model process lifecycle

start architect runtime

start developer runtime

unload inactive model

enforce combo runtime policy

expose model readiness telemetry

This layer is hardware-aware.

It owns hot-swap mechanics.

Layer 3 — Cognitive Packet Layer

Responsibilities:

define architect plan packets

define developer patch packets

define failure packets

define verification summaries

reconstruct compact reasoning state after swaps

This layer is the key to swap-safe cognition.

Layer 4 — Agent Loop Supervisor

Responsibilities:

drive architect/developer/runner iteration

apply retry policy

apply stop conditions

route failure packets

decide escalation or finalize

This layer is the autonomous loop controller.

Layer 5 — Tool Execution Gateway

Responsibilities:

validate tool invocation requests

map tool requests to bounded execution backends

enforce security policy

normalize tool results

emit structured telemetry

This layer does not confer mutation authority by itself.

Layer 6 — Repo Mutation Abstraction

Responsibilities:

present a stable mutation contract to the orchestrator

allow local MVP implementation now

allow CDOS-backed implementation later

Interface:

bind_context

query_intelligence

start_draft

apply_patch

run_tool

finalize_draft

push

Implementations:

LocalRepoEngine

CDOSMutationEngine

Layer 7 — Memory and Learning Layer

Responsibilities:

store failure pattern memory

store repo heuristics

store prompt/policy versions

track experiment results

support offline improvement

This layer must not silently alter deterministic mutation behavior.

Layer 8 — Governance Layer

Responsibilities:

autonomy mode enforcement

iteration limits

risk-based execution policy

approval gates

policy audit trail

Layer 9 — Observability Layer

Responsibilities:

session telemetry

model lifecycle telemetry

tool telemetry

mutation request telemetry

failure taxonomy

swap timing metrics

Layer 10 — Control Plane API

Responsibilities:

expose orchestrator API

expose websocket or streaming telemetry later

serve as integration boundary for UI and external systems