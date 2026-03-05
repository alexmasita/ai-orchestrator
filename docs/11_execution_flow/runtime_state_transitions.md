# Runtime State Transitions

This document describes the lifecycle states of an orchestrated instance.

Understanding these states is critical for debugging and extending the system.

---

# Instance Lifecycle


REQUESTED
↓
OFFER_SELECTED
↓
INSTANCE_CREATING
↓
BOOTSTRAP_RUNNING
↓
SERVICE_STARTING
↓
READY
↓
RUNNING
↓
IDLE_TIMEOUT
↓
TERMINATED


---

# State Definitions

### REQUESTED

Triggered by CLI invocation.

The orchestration pipeline begins.

---

### OFFER_SELECTED

A GPU offer has been chosen.

Selection guarantees:

• meets VRAM requirement  
• meets price constraint  
• satisfies reliability requirements  

---

### INSTANCE_CREATING

Provider instance creation request is sent.

Example:


PUT /asks/{offer_id}


The provider allocates GPU infrastructure.

---

### BOOTSTRAP_RUNNING

The bootstrap script begins execution on the instance.

The script performs:

• dependency installation  
• runtime initialization  
• service startup  

---

### SERVICE_STARTING

DeepSeek and Whisper services start.

Ports exposed:


8080 → DeepSeek
9000 → Whisper


---

### READY

Readiness checks pass.

Checks include:

• TCP connectivity
• HTTP endpoint availability

---

### RUNNING

The instance is fully operational.

User may connect to services.

---

### IDLE_TIMEOUT

If no activity occurs for the configured duration:


idle_timeout_seconds


the instance is eligible for shutdown.

---

### TERMINATED

The instance is shut down.

Possible triggers:

• idle timeout
• provider interruption
• manual termination

---

# Failure States

Failures may occur at any stage.

Examples:

| Stage | Failure |
|-----|-------|
Offer Selection | No GPU available |
Instance Creation | Provider API failure |
Bootstrap | script error |
Readiness | port never opens |

Each failure produces a deterministic error message.

---

# Observability

When debugging:


AI_ORCH_DEBUG=1


The orchestrator prints runtime transitions and provider calls.

---

# Design Principle

State transitions are **sequential and deterministic**.

No background orchestration loops exist.

The orchestration process completes before CLI returns.