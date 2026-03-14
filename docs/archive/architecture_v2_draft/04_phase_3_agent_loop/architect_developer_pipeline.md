Architect / Developer Pipeline
Architect Responsibilities

interpret objective

reason about repository structure

propose implementation plan

define validation strategy

define likely file targets

interpret failure packets

refine approach

Architect does not write directly to the filesystem.

Developer Responsibilities

consume architect plan

inspect relevant context

produce patch proposal

request tools when necessary

refine based on failure packets

Runner Responsibilities

Runner is an execution function, not necessarily a reasoning model.

It should:

execute tests

run commands

collect output

return structured results

The orchestrator may later use a model for additional failure interpretation, but runner correctness should not require a third reasoning model.