# Orchestration Sequence

This document provides a detailed sequence diagram of the orchestration runtime pipeline.

The goal is to illustrate the interactions between system layers.

---

# Runtime Components

The orchestration system contains the following actors:

User  
CLI  
Config Loader  
Sizing Engine  
Orchestrator  
Provider (Vast)  
Instance Runtime  
Healthcheck System  

---

# Execution Sequence


User
│
│ CLI command
▼
CLI
│
│ load_config()
▼
Config Loader
│
│ return configuration
▼
CLI
│
│ compute_requirements()
▼
Sizing Engine
│
│ return SizingResult
▼
CLI
│
│ run_orchestration()
▼
Orchestrator
│
│ search_offers()
▼
Provider (Vast API)
│
│ POST /bundles
▼
Provider
│
│ return offer list
▼
Orchestrator
│
│ select_offer()
▼
Orchestrator
│
│ create_instance()
▼
Provider
│
│ PUT /asks/{id}
▼
Provider
│
│ return instance
▼
Orchestrator
│
│ generate bootstrap script
▼
Instance Runtime
│
│ start services
▼
Healthcheck System
│
│ wait_for_instance_ready()
▼
Orchestrator
│
│ return result
▼
CLI
│
│ print JSON output
▼
User


---

# Layer Responsibilities

### CLI

Handles:

• argument parsing  
• configuration loading  
• output formatting  

The CLI never communicates directly with providers.

---

### Orchestrator

Responsible for:

• offer selection  
• instance lifecycle management  
• readiness verification  

---

### Provider

Responsible for:

• interacting with infrastructure APIs  
• parsing provider responses  
• returning normalized objects  

---

### Runtime

Responsible for:

• launching model servers  
• exposing service endpoints  

---

# Key Design Principle

Each layer has **one responsibility** and communicates through **explicit contracts**.

This prevents:

• architectural coupling  
• provider leakage into orchestration logic  
• nondeterministic behavior  

---

# Determinism

The sequence ensures deterministic behavior by:

• avoiding concurrency during orchestration
• deterministic offer ordering
• deterministic configuration parsing
• deterministic JSON output