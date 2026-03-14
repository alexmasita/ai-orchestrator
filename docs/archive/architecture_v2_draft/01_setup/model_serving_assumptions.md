Model Serving Assumptions
Serving Backend

The orchestrator assumes model serving is performed through bounded adapters, not hardcoded backend logic spread across the system.

Examples:

vLLM adapter

future llama.cpp adapter

future hosted API adapter

Current Assumption

Current combo development assumes vLLM.

Required Adapter Responsibilities

start runtime

stop runtime

health check runtime

expose request endpoint

report readiness

report swap timing

expose model metadata

normalize inference errors