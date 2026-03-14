Tool Contracts
list_files

Input:

path

recursive

limit

read_file

Input:

path

start_line optional

end_line optional

search_repo

Input:

query

path_scope optional

limit

write_patch

Input:

diff_text

Note:
This is not direct filesystem mutation.
It routes through mutation abstraction.

run_tests

Input:

argv

cwd scope

timeout

run_command

Input:

argv

cwd

timeout

get_context_summary

Input:

session_id

Contract Rules

array argv only

shell=False

bounded output

timeout mandatory

telemetry mandatory

denylist and allowlist enforcement available