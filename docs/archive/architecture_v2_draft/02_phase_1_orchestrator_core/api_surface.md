Phase 1 API Surface
Endpoints
POST /sessions

Create session.

GET /sessions/{session_id}

Read session state.

POST /sessions/{session_id}/invoke

Invoke architect or developer role with structured input.

POST /sessions/{session_id}/stop

Pause or stop session.

GET /health

Service health.

GET /combos

List combo definitions.

Constraints

These APIs do not imply repository mutation power.
They are orchestration APIs only.