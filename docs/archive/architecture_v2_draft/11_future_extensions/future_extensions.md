Future Extensions

These are possible future capabilities. They must not violate core invariants.

1. Voice Interface Layer

Recommendation:

Voice belongs above the orchestrator core, not in CDOS.

Voice pipeline:

speech input
→ intent normalization
→ orchestrator session/task creation

2. Websocket Control Plane

For real-time telemetry and human supervision.

3. Browser Automation Adapter

Potential observational tool.

Must remain bounded and non-mutating.

4. Multi-Combo Routing

Allow combo choice per task type.

5. Hosted / Remote Runtime Backends

Possible later, but trust model changes must be explicit.

6. Self-Hosting and Self-Improvement Workflows

Use same repo mutation abstraction and governance controls as other target repos.