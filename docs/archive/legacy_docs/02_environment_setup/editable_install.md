Purpose

The project is installed using editable mode during development.

Editable installs allow the codebase to be executed directly from the source tree without reinstalling the package after every code change.

Installing the Project

From the repository root:

pip install -e .

This command performs the following:

Installs package metadata

Installs runtime dependencies

Creates CLI entrypoints

Links the source directory into the environment

What Editable Install Does

Instead of copying files into site-packages, pip creates a reference to:

src/ai_orchestrator/

This allows immediate reflection of code changes.

Example:

src/ai_orchestrator/cli.py

can be modified and executed immediately via:

ai-orchestrator

without reinstalling.

Verifying Editable Install

After installation run:

pip list | grep ai-orchestrator

Expected:

ai-orchestrator 0.0.0 (editable)
CLI Installation Result

After editable install, the command should exist:

which ai-orchestrator

Expected:

.venv/bin/ai-orchestrator
Reinstalling the Package

If entrypoints or dependencies change:

pip install -e .

This refreshes the environment.