Packet Schemas
ArchitectPlan
{
  "version": "1",
  "plan_id": "uuid",
  "session_id": "uuid",
  "iteration": 1,
  "repo_context": {
    "repo_id": "github.com/example/repo",
    "commit_sha": "abc123"
  },
  "summary": "Add health-check caching to service layer.",
  "file_targets": ["app/service/health.py", "tests/test_health.py"],
  "steps": [
    "Inspect existing cache interface",
    "Add bounded TTL cache",
    "Add unit tests"
  ],
  "validation_plan": [
    {"type": "run_tests", "target": "tests/test_health.py"}
  ],
  "risk_notes": ["May affect service startup behavior"]
}
DeveloperPatch
{
  "version": "1",
  "patch_id": "uuid",
  "plan_id": "uuid",
  "file_patches": [
    {
      "path": "app/service/health.py",
      "diff": "--- ..."
    }
  ],
  "tool_requests": [
    {
      "type": "run_command",
      "argv": ["pytest", "-q", "tests/test_health.py"]
    }
  ],
  "confidence": 0.72
}
FailurePacket
{
  "version": "1",
  "failure_id": "uuid",
  "phase": "verification",
  "category": "test_failure",
  "exit_code": 1,
  "stdout_tail": "...",
  "stderr_tail": "...",
  "affected_paths": ["tests/test_health.py"],
  "suggested_focus": "cache TTL behavior mismatch"
}