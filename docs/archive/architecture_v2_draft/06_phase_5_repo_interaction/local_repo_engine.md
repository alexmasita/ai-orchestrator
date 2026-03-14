Purpose

Provide a temporary mutation abstraction while CDOS is not yet available.

Responsibilities

clone or bind local repo workspace

create draft worktree or isolated working directory

apply unified diffs

run bounded tools

finalize changes in local form

Limitations

This engine is a transitional implementation.

It will not match CDOS determinism guarantees fully.
It exists to allow early orchestrator progress without blocking on CDOS.

Design Requirement

Its interface must match RepoMutationEngine so later replacement does not churn orchestrator logic.