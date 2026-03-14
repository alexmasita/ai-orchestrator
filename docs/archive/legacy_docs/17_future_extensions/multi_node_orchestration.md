Overview

Current architecture launches one inference node.

Multi-node orchestration would support:

distributed inference

parallel workloads

model sharding

horizontal scaling

Multi-Node Architecture

Future architecture:

Orchestrator
   │
   ├── Node 1
   ├── Node 2
   ├── Node 3
   └── Node N
Node Roles

Possible node types:

inference nodes

Run DeepSeek / Whisper services.

coordinator node

Handles request routing.

storage node

Hosts model artifacts or caches.

Cluster Lifecycle

Cluster creation flow:

select_offers
launch_instances
bootstrap_cluster
start_services
register_nodes
Network Requirements

Nodes must communicate via:

internal private network
orchestrator control channel
Synchronization

Distributed nodes must synchronize:

model state

readiness status

cluster metadata

Testing Strategy

Cluster orchestration must be simulated with deterministic provider mocks.