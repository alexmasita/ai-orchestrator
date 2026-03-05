Purpose

This document describes how to create and manage the Python runtime environment required to develop and run the ai-orchestrator system.

The orchestrator is designed to run inside a dedicated virtual environment to ensure:

deterministic dependency resolution

isolation from system Python packages

reproducible development environments

consistent CLI behavior across machines

Python Version Requirements

The system is designed to run on:

Python ≥ 3.10

Recommended version:

Python 3.11

Earlier Python versions are not supported due to:

typing features

packaging compatibility

dependency expectations

Creating the Virtual Environment

From the repository root:

python3 -m venv .venv

This creates the environment directory:

.venv/

The .venv directory should never be committed to source control.

Activating the Environment

macOS / Linux:

source .venv/bin/activate

After activation, your shell should show:

(.venv)

You can confirm Python is coming from the virtual environment:

which python

Expected:

./.venv/bin/python
Verifying the Environment

Run:

python --version

Example output:

Python 3.11.x

Confirm pip location:

which pip

Expected:

./.venv/bin/pip
Environment Isolation Guarantee

All dependencies must be installed inside the virtual environment.

The system must never rely on:

global site-packages

system Python libraries

user-installed packages outside .venv

This rule ensures:

deterministic behavior

reproducible deployments

test stability

Environment Directory Structure

After installation, the environment will contain:

.venv/
  bin/
    python
    pip
    ai-orchestrator
  lib/
  include/

The ai-orchestrator executable appears here after installation.

Deleting and Recreating the Environment

If the environment becomes corrupted:

rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

Recreating the environment is safe and expected during development.