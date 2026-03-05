docs/
│
├── 02_environment_setup/
│   ├── python_environment.md
│   ├── dependency_management.md
│   ├── editable_install.md
│   ├── cli_entrypoints.md
│   └── running_locally.md
│
├── 03_cli_layer/
│   ├── cli_architecture.md
│   ├── cli_command_contract.md
│   ├── cli_execution_flow.md
│   └── cli_output_schema.md
│
├── 04_orchestrator_core/
│   ├── orchestrator_design.md
│   ├── run_orchestration_flow.md
│   ├── offer_selection.md
│   ├── instance_lifecycle.md
│   └── idle_timeout_behavior.md
│
├── 05_model_plugin_layer/
│   ├── plugin_architecture.md
│   ├── plugin_registry.md
│   ├── deepseek_plugin.md
│   ├── whisper_requirements.md
│   └── adding_new_models.md
│
├── 06_sizing_and_requirements/
│   ├── sizing_engine.md
│   ├── resource_requirements.md
│   ├── vram_calculation.md
│   ├── disk_and_network_constraints.md
│   └── sizing_failure_modes.md
│
├── 07_provider_interface/
│   ├── provider_contract.md
│   ├── provider_instance_model.md
│   ├── provider_offer_model.md
│   ├── provider_error_model.md
│   └── mock_provider.md
│
├── 08_vast_provider/
│   ├── vast_provider_architecture.md
│   ├── bundles_offer_search.md
│   ├── instance_creation_flow.md
│   ├── response_parsing.md
│   ├── api_error_wrapping.md
│   └── vast_runtime_debugging.md
│
├── 09_runtime_bootstrap/
│   ├── bootstrap_script_generation.md
│   ├── bootstrap_script_limits.md
│   ├── service_startup.md
│   ├── deepseek_runtime.md
│   ├── whisper_runtime.md
│   └── runtime_security_considerations.md
│
├── 10_runtime_healthchecks/
│   ├── healthcheck_architecture.md
│   ├── port_readiness_checks.md
│   ├── http_readiness_checks.md
│   ├── readiness_wait_strategy.md
│   └── failure_handling.md
│
├── 11_execution_flow/
│   ├── end_to_end_execution.md
│   ├── orchestration_sequence.md
│   ├── data_flow_contracts.md
│   └── runtime_state_transitions.md
│
├── 12_configuration/
│   ├── config_schema.md
│   ├── config_field_reference.md
│   ├── config_normalization.md
│   └── example_config.md
│
├── 13_testing_strategy/
│   ├── testing_philosophy.md
│   ├── deterministic_tests.md
│   ├── provider_mocking.md
│   ├── cli_tests.md
│   ├── bootstrap_tests.md
│   ├── runtime_tests.md
│   └── integration_boundary_tests.md
│
├── 14_operational_guides/
│   ├── running_the_system.md
│   ├── expected_output.md
│   ├── debug_mode.md
│   ├── common_runtime_failures.md
│   └── recovering_failed_instances.md
│
├── 15_error_handling/
│   ├── error_model.md
│   ├── configuration_errors.md
│   ├── provider_errors.md
│   ├── orchestration_errors.md
│   └── user_facing_errors.md
│
├── 16_debugging_and_observability/
│   ├── debug_logging.md
│   ├── ai_orch_debug_flag.md
│   ├── tracing_runtime_execution.md
│   └── diagnosing_provider_failures.md
│
└── 17_future_extensions/
    ├── additional_providers.md
    ├── autoscaling_architecture.md
    ├── multi_node_orchestration.md
    ├── snapshot_reuse.md
    ├── instance_reuse.md
    ├── caching_and_artifacts.md
    └── distributed_inference.md
Section Descriptions

Below is the purpose of every section and file so the documentation remains aligned with the architecture.

00_overview

High-level understanding of the system.

system_vision.md

Explains the purpose of ai-orchestrator:

deterministic GPU orchestration

reproducible model deployment

automated infrastructure provisioning

Defines what the system exists to solve.

architecture_principles.md

Core design philosophy:

deterministic execution

strict contracts between layers

provider abstraction

runtime reproducibility

test-driven architecture evolution

system_layers.md

Defines the architectural stack:

CLI
 ↓
Orchestrator
 ↓
Model Plugins
 ↓
Sizing Engine
 ↓
Provider Interface
 ↓
Vast Provider
 ↓
Runtime Bootstrap
 ↓
Healthcheck System

Explains boundaries between layers.

system_invariants.md

Documents critical non-negotiable rules:

Examples:

CLI stdout must always be JSON on success

provider code must never leak secrets

tests must not use real network

bootstrap script must remain deterministic

runtime services must expose fixed ports

determinism_guarantees.md

Explains how determinism is preserved:

deterministic JSON output ordering

deterministic offer selection

deterministic bootstrap script generation

deterministic test execution

01_repository_structure

Explains the repository layout.

repository_layout.md

Overview of repository:

src/
tests/
config.yaml
launch.sh
docs/
src_directory.md

Explains all modules inside:

src/ai_orchestrator/

including:

cli

config

orchestrator

provider

runtime

plugins

sizing

tests_directory.md

Explains the purpose of every test group.

configuration_files.md

Documents:

config.yaml

launch.sh

pyproject.toml

setup.cfg

02_environment_setup

How to prepare the development environment.

python_environment.md

Creating virtual environment.

python -m venv .venv
source .venv/bin/activate
dependency_management.md

Explains runtime dependencies:

requests

PyYAML

editable_install.md

Why editable installs are used:

pip install -e .

for development.

cli_entrypoints.md

How the CLI command is exposed:

[project.scripts]
ai-orchestrator = ai_orchestrator.cli:main
running_locally.md

How to launch locally.

03_cli_layer

Explains CLI design.

cli_architecture.md

How the CLI acts as the system entry point.

cli_command_contract.md

Defines command:

ai-orchestrator start

and required arguments.

cli_execution_flow.md

CLI logic flow.

cli_output_schema.md

Defines final output JSON:

{
  instance_id
  gpu_type
  cost_per_hour
  idle_timeout
  snapshot_version
  deepseek_url
  whisper_url
}
04_orchestrator_core

Core orchestration logic.

orchestrator_design.md

Explains orchestration responsibilities.

run_orchestration_flow.md

Detailed flow of run_orchestration().

offer_selection.md

How GPUs are selected.

instance_lifecycle.md

Lifecycle from offer → instance → readiness.

idle_timeout_behavior.md

Explains idle timeout handling.

05_model_plugin_layer

Explains plugin architecture.

plugin_architecture.md

Plugin interface design.

plugin_registry.md

How plugins are discovered and registered.

deepseek_plugin.md

DeepSeek runtime requirements.

whisper_requirements.md

Whisper runtime configuration.

adding_new_models.md

Developer guide for new models.

06_sizing_and_requirements

Explains resource sizing logic.

sizing_engine.md

Role of compute_requirements.

resource_requirements.md

VRAM / disk calculations.

vram_calculation.md

How model memory is estimated.

disk_and_network_constraints.md

Network + disk constraints.

sizing_failure_modes.md

When sizing fails.

07_provider_interface

Defines provider abstraction.

provider_contract.md

Provider interface requirements.

provider_instance_model.md

ProviderInstance contract.

provider_offer_model.md

ProviderOffer structure.

provider_error_model.md

Provider error handling.

mock_provider.md

Mock provider used in tests.

08_vast_provider

Detailed Vast integration.

vast_provider_architecture.md

Vast provider overview.

bundles_offer_search.md

POST /bundles search flow.

instance_creation_flow.md

PUT /asks/{id} instance creation.

response_parsing.md

Parsing Vast API responses.

api_error_wrapping.md

Wrapping request errors into VastProviderError.

vast_runtime_debugging.md

Debugging provider failures.

09_runtime_bootstrap

Bootstrap runtime environment.

bootstrap_script_generation.md

Script generation process.

bootstrap_script_limits.md

Script size limit.

service_startup.md

Service launch steps.

deepseek_runtime.md

DeepSeek runtime.

whisper_runtime.md

Whisper runtime.

runtime_security_considerations.md

Security implications of bootstrap scripts.

10_runtime_healthchecks

Runtime readiness.

healthcheck_architecture.md

Healthcheck design.

port_readiness_checks.md

TCP port checks.

http_readiness_checks.md

HTTP endpoint checks.

readiness_wait_strategy.md

Retry logic.

failure_handling.md

Handling readiness failures.

11_execution_flow

System execution.

end_to_end_execution.md

Full runtime pipeline.

orchestration_sequence.md

Sequence diagram.

data_flow_contracts.md

Data structures between layers.

runtime_state_transitions.md

State machine.

12_configuration

Configuration documentation.

config_schema.md

Full schema.

config_field_reference.md

Explanation of every config field.

config_normalization.md

Normalization rules.

example_config.md

Working example.

13_testing_strategy

Testing philosophy.

testing_philosophy.md

Why deterministic tests.

deterministic_tests.md

Ensuring repeatability.

provider_mocking.md

Mocking requests.

cli_tests.md

CLI behavior tests.

bootstrap_tests.md

Bootstrap tests.

runtime_tests.md

Healthcheck tests.

integration_boundary_tests.md

Integration boundaries.

14_operational_guides

Running the system.

running_the_system.md

Command usage.

expected_output.md

What success looks like.

debug_mode.md

AI_ORCH_DEBUG usage.

common_runtime_failures.md

Troubleshooting.

recovering_failed_instances.md

How to clean up instances.

15_error_handling

Error propagation.

error_model.md

Error hierarchy.

configuration_errors.md

Config errors.

provider_errors.md

Provider failures.

orchestration_errors.md

Orchestration failures.

user_facing_errors.md

User-visible errors.

16_debugging_and_observability

Debugging system.

debug_logging.md

Logging strategy.

ai_orch_debug_flag.md

Environment flag behavior.

tracing_runtime_execution.md

Tracing runtime events.

diagnosing_provider_failures.md

Debugging provider interactions.

17_future_extensions

Future architecture.

additional_providers.md

AWS/GCP providers.

autoscaling_architecture.md

Autoscaling clusters.

multi_node_orchestration.md

Multi-node inference.

snapshot_reuse.md

Reusable environments.

instance_reuse.md

Warm pools.

caching_and_artifacts.md

Model caching.

distributed_inference.md

Future distributed inference.