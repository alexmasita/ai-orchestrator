Architecture Invariants

These are hard invariants.

Runtime Invariants

AI-Orchestrator must not mutate repository state directly.

All repository mutation must flow through RepoMutationEngine.

When CDOS is available, CDOSMutationEngine becomes the preferred implementation.

Model swaps must not invalidate task correctness.

No live model memory may be required to continue a session.

Every autonomous loop iteration must emit structured telemetry.

Tool execution must be bounded by timeout and output limits.

All model invocations must include explicit role identity.

Architect and Developer outputs must be schema-constrained where practical.

Failure analysis must consume structured failure packets, not raw uncontrolled environment state.

Session Invariants

Sessions must be resumable from persisted orchestrator state.

Each session must track explicit iteration count.

Each session must track current context identity.

Each session must track active combo and model role transitions.

Session stop conditions must be explicit.

GPU Invariants

Combo designs must declare residency assumptions.

Current large-model combo runtime assumes single-active-model scheduling.

Simultaneous multi-model residency must not be assumed by core logic.

Swap latency is a runtime concern, not a correctness concern.

Integration Invariants

AI-Orchestrator must not bypass deterministic intelligence contracts when CDOS is integrated.

CDOS remains mutation authority.

AI-Orchestrator remains reasoning authority.

Observational tools must not silently create mutation side effects.