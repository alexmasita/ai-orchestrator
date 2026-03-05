# Orchestration Errors

Orchestration errors occur inside the core orchestration engine.

File:


src/ai_orchestrator/orchestrator.py


These failures occur after configuration and sizing have succeeded.

---

# Orchestration Responsibilities

The orchestrator manages:


offer selection
instance creation
bootstrap injection
readiness validation


Failures during these phases produce orchestration errors.

---

# Common Orchestration Failures

## No Valid Offers

Occurs when provider returns no usable GPU offers.

Example:


RuntimeError("No valid GPU offers found")


---

## Invalid Bootstrap Script

Bootstrap scripts must obey strict constraints:


MAX_BOOTSTRAP_SCRIPT_BYTES = 16384


If exceeded:


ValueError("bootstrap script exceeds provider size limit")


---

## Invalid Idle Timeout

Idle timeout must be:


positive integer


Invalid values:


0
-1
float
string
None


Result:


ValueError("invalid idle_timeout_seconds")


---

# Readiness Failures

After instance creation, readiness checks verify runtime services.

Endpoints:


http://<ip>:8080
http://<ip>:9000


Failure example:


RuntimeError("instance not ready")


---

# Failure Propagation

Orchestration errors propagate to the CLI unless caught earlier.

The CLI converts them to error output.

---

# Deterministic Guarantees

Orchestration errors must:

- never retry automatically
- never partially modify instance_config
- always fail consistently

---

# Summary

Orchestration errors represent failures during instance lifecycle management.

They ensure:

- infrastructure problems surface cleanly
- deterministic system behavior