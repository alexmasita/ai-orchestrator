# Runtime Tests

Runtime tests validate the behavior of services running inside the provisioned GPU instance.

Since tests do not create real instances, runtime behavior is simulated.

## Healthcheck Tests

Healthchecks confirm that services inside the instance become available.

Tests simulate readiness responses for:

DeepSeek endpoint  
Whisper endpoint

Example readiness URL:


http://<instance-ip>:8080
http://<instance-ip>:9000


## Readiness Logic

The orchestrator waits for both services to become ready.

Tests verify that:

- readiness checks are executed
- failures propagate correctly
- readiness is called exactly once

## Deterministic Call Ordering

Runtime readiness must occur after instance creation.

Tests enforce this ordering:


create_instance
wait_for_instance_ready


## Failure Handling

Tests simulate readiness failures.

The orchestrator must propagate the error rather than silently ignoring it.

## URL Construction

Tests validate that readiness URLs use the provider public IP.

If the provider does not return an IP, fallback logic is used.

## Runtime Guarantees

Runtime tests ensure that the orchestrator does not report success until services are ready.