CDOS Integration Specification
API Contracts
bind_context

Input:

repo_id

commit_sha

Output:

normalized context handle

query_intelligence

Input:

context handle

query_type

params

Output:

normalized intelligence result

start_draft

Input:

context handle

Output:

draft_id

apply_patch

Input:

draft_id

developer patch packet or normalized diff payload

Output:

patch validation result

updated draft state

run_tool

Input:

draft_id

tool request

Output:

tool result

finalize_draft

Input:

draft_id

Output:

finalized commit reference or equivalent artifact

push

Input:

finalized reference

Output:

push result

End-to-End Workflow Example

User submits intent

AI-Orchestrator creates session

AI-Orchestrator calls bind_context

AI-Orchestrator calls query_intelligence

Architect produces ArchitectPlan

Developer produces DeveloperPatch

AI-Orchestrator calls apply_patch

AI-Orchestrator calls run_tool

CDOS returns ToolResult or FailurePacket

Architect refines if needed

Developer patches again

AI-Orchestrator calls finalize_draft

Optional explicit push