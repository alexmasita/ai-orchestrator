# ChatGPT + VS Code Safe Refactoring Workflow (Patch-Based)

This guide describes a **safe workflow for refactoring code using ChatGPT** while working in **VS Code with Git**, especially for **large files (1000–3000+ lines)**.

The goal is to **avoid accidental code modifications** and ensure that only intended changes are applied.

---

# Core Principle

Never ask ChatGPT to rewrite an entire file.

Instead, require ChatGPT to generate a **git diff patch** and let **git apply the changes automatically**.

This prevents:

* accidental deletion of code
* formatting changes
* unrelated edits
* missing lines

---

# Typical Workflow

```
VS Code file
      ↓
Copy file path + contents
      ↓
Paste into ChatGPT
      ↓
ChatGPT returns git patch
      ↓
Save patch to file
      ↓
git apply patch
      ↓
Review changes
```

---

# Step 1 — Commit Your Current Code

Always create a safety checkpoint before asking ChatGPT to refactor.

```bash
git add .
git commit -m "checkpoint before LLM refactor"
```

This allows easy rollback if something goes wrong.

---

# Step 2 — Copy File Path and Contents

In VS Code:

1. Copy the **relative file path from repo root**

Example:

```
src/config.js
```

2. Copy the **entire file contents**

---

# Step 3 — Ask ChatGPT for a Patch

Use the following prompt template.

```
You are generating a git patch.

Goal:
Replace hardcoded values with named constants.

Rules:
- Output ONLY a git diff patch
- The patch must apply cleanly with `git apply`
- Do NOT rewrite the entire file
- Do NOT change formatting
- Do NOT modify unrelated code
- Only change lines necessary for the refactor

File path:
src/config.js

File contents:
----------------
(paste file here)
----------------
```

Expected response format:

```diff
diff --git a/src/config.js b/src/config.js
--- a/src/config.js
+++ b/src/config.js
@@
-const timeout = 5000;
+const timeout = DEFAULT_TIMEOUT;
```

---

# Step 4 — Save the Patch

Create a patch file in your repo.

Example:

```
llm.patch
```

Paste ChatGPT's output into this file.

Project structure example:

```
project/
 ├ src/
 │  └ config.js
 ├ llm.patch
```

Save the file.

---

# Step 5 — Inspect the Patch

Before applying the patch, check what files will change.

```bash
git apply --stat llm.patch
```

Example output:

```
 src/config.js | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

Verify only the intended files are modified.

---

# Step 6 — Validate the Patch

Run a dry run to ensure the patch applies correctly.

```bash
git apply --check llm.patch
```

If the patch is valid, there will be **no output**.

If invalid, git will display an error and **no files will change**.

---

# Step 7 — Apply the Patch

```bash
git apply llm.patch
```

Git will automatically modify the correct file(s).

You do **not paste the patch into the source file manually**.

---

# Step 8 — Review the Changes

Inspect the edits.

```bash
git diff
```

Open the file in VS Code to visually confirm.

---

# Step 9 — Run Tests

Run your project tests or build.

Examples:

```bash
npm test
```

or

```bash
pytest
```

---

# Step 10 — Commit the Changes

If everything is correct:

```bash
git add .
git commit -m "replace hardcoded values with constants"
```

---

# Two-Phase Workflow for Large Files (Recommended)

Large files often cause unreliable patches.
A two-phase approach improves accuracy.

---

## Phase 1 — Ask ChatGPT to Identify Target Lines

Prompt:

```
Analyze the file and list all lines containing hardcoded values that should be replaced with constants.

Return:
- line number
- reason for change

Do NOT modify the code.

File path:
src/config.js

File contents:
(paste file)
```

Example response:

```
Line 45  - hardcoded timeout value
Line 112 - retry delay value
Line 308 - max connections limit
```

---

## Phase 2 — Generate the Patch

Prompt:

```
Generate a git diff patch.

Modify ONLY these lines:
45
112
308

Rules:
- Output ONLY a git diff patch
- The patch must apply with `git apply`
- Do not change formatting
- Do not modify unrelated lines

File path:
src/config.js

File contents:
(paste file)
```

---

# Best Prompt Template (Recommended)

```
You are an automated refactoring engine.

Goal:
Replace hardcoded values with named constants.

Constraints:
- Output ONLY a git diff patch
- The patch must apply cleanly with `git apply`
- Do NOT rewrite the full file
- Do NOT change formatting
- Do NOT modify unrelated code
- Only modify lines necessary for the change
- Maximum 30 lines changed

File path:
<relative path>

File contents:
(paste file)
```

---

# Helpful Git Commands

Check patch impact:

```bash
git apply --stat llm.patch
```

Validate patch:

```bash
git apply --check llm.patch
```

Apply patch:

```bash
git apply llm.patch
```

Inspect changes:

```bash
git diff
```

Undo changes:

```bash
git restore .
```

Rollback commit:

```bash
git reset --hard HEAD
```

---

# Safety Tips

Always:

* commit before refactoring
* inspect patches before applying
* run tests after applying

Avoid:

* asking ChatGPT to rewrite entire files
* manually pasting edited code back into the file
* applying patches without checking them first

---

# Why This Workflow Is Reliable

Git guarantees that patches:

* modify only specified files
* change only matching lines
* fail safely if context does not match

This prevents the most common LLM editing failures.

---

# Quick Summary

```
1. Commit code
2. Ask ChatGPT for git patch
3. Save patch
4. git apply --check patch
5. git apply patch
6. git diff
7. Run tests
8. Commit changes
```

---

# End
