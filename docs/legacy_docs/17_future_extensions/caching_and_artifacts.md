Overview

Model loading and downloads can be expensive.

Future architecture may include artifact caching.

Artifact Types

Artifacts include:

model weights

tokenizer files

runtime binaries

compiled kernels

Cache Locations

Caches may exist in:

local disk
shared storage
object storage
snapshot images
Cache Strategy

Cache keys must include:

model version
architecture
runtime version
Cache Benefits

Caching reduces:

instance boot time

network usage

repeated downloads

Determinism Constraints

Cache lookup must remain deterministic.