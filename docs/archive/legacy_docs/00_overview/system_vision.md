System Vision

ai-orchestrator is a deterministic infrastructure orchestration system designed to automatically provision GPU compute environments capable of running AI inference workloads.

The system abstracts GPU infrastructure providers (initially Vast.ai) and automates the process of:

Determining hardware requirements for requested AI models

Selecting appropriate GPU offers from providers

Provisioning a compute instance

Injecting a deterministic bootstrap runtime

Starting required AI services

Waiting for service readiness

Returning a machine-readable endpoint summary

The orchestration pipeline is designed so that the entire process can be invoked through a single CLI command:

ai-orchestrator start \
  --config config.yaml \
  --models deepseek_llamacpp whisper

The expected result is a JSON response describing the running AI inference environment.

Example output:

{
  "instance_id": "abc123",
  "gpu_type": "RTX_4090",
  "cost_per_hour": 0.72,
  "idle_timeout": 1800,
  "snapshot_version": "v1",
  "deepseek_url": "http://1.2.3.4:8080",
  "whisper_url": "http://1.2.3.4:9000"
}

This output provides all information needed for downstream systems to interact with the deployed inference services.

Primary Goals

The system is designed around the following goals.

Deterministic Infrastructure Orchestration

Given the same inputs:

configuration file

requested models

provider responses

the orchestration logic must behave deterministically.

Automated GPU Provisioning

The system should automatically:

determine required GPU memory

select a compatible provider offer

provision the instance

configure the runtime environment

Provider Abstraction

Infrastructure providers must be interchangeable through a provider interface.

Currently implemented:

Vast.ai

Future providers may include:

AWS GPU instances

GCP GPU instances

other marketplace providers

Runtime Automation

The orchestrator automatically installs and launches AI services inside the provisioned instance using a deterministic bootstrap script.

Machine-Readable Output

The CLI must always emit structured JSON on success to allow integration with automation systems.

Non-Goals

The following capabilities are intentionally not part of the system design:

model training orchestration

distributed GPU cluster scheduling

long-term job management

container orchestration

user authentication systems

ai-orchestrator is focused strictly on single-node AI inference environment provisioning.