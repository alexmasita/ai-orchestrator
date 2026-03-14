RepoMutationEngine
Interface

bind_context(repo_id, commit_sha)

query_intelligence(query_type, params)

start_draft(context)

apply_patch(draft_id, patch_packet)

run_tool(draft_id, tool_request)

finalize_draft(draft_id)

push(commit_ref)

MVP Implementation

LocalRepoEngine

Used before CDOS integration.

Future Implementation

CDOSMutationEngine

Used when deterministic kernel is available.

Important Rule

The orchestrator never depends on raw git commands scattered through loop logic.
It depends on this interface.