Purpose

Idle timeout prevents unused GPU instances from running indefinitely.

Configuration Field
idle_timeout_seconds

Defined in config.yaml.

Example:

idle_timeout_seconds: 1800
Validation Rules

The value must satisfy:

type(value) == int
value > 0

Invalid values raise:

ValueError
Propagation

The timeout is passed to the provider:

instance_config = {
    "bootstrap_script": script,
    "idle_timeout_seconds": value
}
Determinism Guarantee

The instance config must be rebuilt each run.

This prevents shared mutable state across runs.

Runtime Enforcement

Timeout behavior is enforced inside the instance runtime environment.

Typical implementation:

system idle monitor
service inactivity tracking
automatic shutdown
Example Behavior
user launches instance
instance serves inference
no requests for 30 minutes
instance shuts down

If you'd like, I can next generate the provider architecture docs (Vast integration), which is the most complex and critical section of the system.