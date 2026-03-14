Domain Model
TaskIntent

Represents user goal and constraints.

Fields:

task_id

objective

acceptance_criteria

repo_target

autonomy_mode

max_iterations

risk_level

SessionState

Fields:

session_id

active_combo

active_role

repo_context

current_iteration

status

created_at

last_updated_at

IterationState

Fields:

iteration_id

phase

architect_packet_ref

developer_packet_ref

failure_packet_ref

verification_summary_ref

decision

RepoContext

Fields:

repo_id

commit_sha

draft_id optional

context_version