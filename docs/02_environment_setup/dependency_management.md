Purpose

This document describes how runtime and development dependencies are managed in the ai-orchestrator system.

Dependency management is intentionally minimal to preserve system portability and deterministic behavior.

Dependency Source of Truth

Dependencies are defined in:

pyproject.toml

This file acts as the single source of truth for:

runtime dependencies

packaging configuration

build metadata

Runtime Dependencies

The current runtime dependencies include:

requests

Used for:

Vast API communication

HTTP provider interactions

Example usage:

requests.get(...)
requests.post(...)
requests.put(...)

All HTTP exceptions are wrapped into VastProviderError.

PyYAML

Used for:

parsing config.yaml

loading orchestrator configuration

Example:

yaml.safe_load(...)

The loader normalizes configuration values to prevent:

quoted URL issues

whitespace inconsistencies

trailing slash errors

Installing Dependencies

Dependencies are installed through editable installation:

pip install -e .

This installs:

runtime dependencies

CLI entrypoints

package metadata

Offline Installation Considerations

If installation fails due to network restrictions:

Possible solutions:

use internal package mirrors

configure pip proxy settings

install from local wheels

Example:

pip install requests PyYAML
pip install -e .
Dependency Design Philosophy

The system intentionally keeps dependencies minimal.

Reasons:

simpler deployments

faster environment setup

easier debugging

lower security surface

Dependencies are added only when required by architecture.