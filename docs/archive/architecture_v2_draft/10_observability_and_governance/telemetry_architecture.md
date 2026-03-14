Telemetry Architecture
Telemetry Principles

append-only

schema-versioned

bounded payloads

no secrets

no uncontrolled raw prompt logging by default

Event Categories

session_created

role_invoked

model_loaded

model_unloaded

model_swap_completed

tool_requested

tool_executed

patch_submitted

patch_rejected

iteration_completed

session_stopped

escalation_triggered

Required Correlation IDs

session_id

iteration_id

plan_id optional

patch_id optional

repo_context_id optional