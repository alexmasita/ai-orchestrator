Shared Packet Contracts
ToolRequest
{
  "type": "run_command",
  "argv": ["pytest", "-q"],
  "cwd_scope": "draft_root",
  "timeout_s": 120
}
ToolResult
{
  "status": "ok",
  "exit_code": 0,
  "stdout_tail": "...",
  "stderr_tail": "...",
  "duration_ms": 2200
}
VerificationSummary
{
  "status": "pass",
  "checks": [
    {"name": "pytest", "result": "pass"}
  ]
}