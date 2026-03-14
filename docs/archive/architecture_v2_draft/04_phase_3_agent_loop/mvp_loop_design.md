MVP Loop Design
Constraint

CDOS is not yet available.

MVP Strategy

Use LocalRepoEngine behind RepoMutationEngine.

Preserve the same orchestrator architecture so CDOS can replace the backend later.

MVP Loop

Intent
→ Architect plan
→ Developer patch
→ Local draft patch application
→ Local test run
→ Failure packet
→ Retry or stop

MVP Non-Goals

deterministic snapshot guarantees at CDOS level

full push lifecycle rigor

advanced self-improvement

multi-user runtime