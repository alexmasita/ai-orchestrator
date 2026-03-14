Overview

The current system always creates a new instance.

Instance reuse allows reusing existing nodes.

Motivation

Instance reuse reduces:

launch latency

cloud costs

model warmup time

Instance Pool

A future system may maintain a warm instance pool.

orchestrator
    ↓
instance pool
    ↓
available GPU nodes
Instance Lifecycle
launch
serve traffic
idle
reuse
terminate
Idle Detection

Instances may be reused if:

idle_timeout_seconds not exceeded
services still running
Orchestrator Changes

Instance reuse requires:

instance registry

instance health tracking

reuse eligibility logic