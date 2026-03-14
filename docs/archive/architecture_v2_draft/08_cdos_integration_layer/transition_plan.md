Transition Plan from LocalRepoEngine to CDOSMutationEngine
Step 1

Keep orchestrator on RepoMutationEngine.

Step 2

Implement CDOSMutationEngine adapter.

Step 3

Route read-only repo intelligence through CDOS first.

Step 4

Route draft lifecycle through CDOS.

Step 5

Route patch application and finalize through CDOS.

Step 6

Retire direct local mutation paths except for test/dev modes.