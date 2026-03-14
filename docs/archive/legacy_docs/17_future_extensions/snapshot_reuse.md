Overview

Snapshot reuse enables fast instance boot times by using prebuilt environments.

Currently the system uses:

snapshot_version

in configuration.

Snapshot Concept

Snapshots represent preconfigured machine images containing:

runtime dependencies

model binaries

inference services

Snapshot Lifecycle
build snapshot
store snapshot
launch instances from snapshot
Snapshot Benefits

Snapshots reduce:

bootstrap time
network downloads
cold start latency
Snapshot Versioning

Snapshots are versioned:

snapshot_version: v1
snapshot_version: v2
Snapshot Management

Future snapshot management may include:

snapshot registry

snapshot validation

snapshot compatibility checks

Deterministic Requirements

Snapshot selection must remain deterministic.