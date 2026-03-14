Environment and Constraints
Current Target Runtime

single GPU

approximately 94GB VRAM

vLLM-based serving

FastAPI control plane target

local or remote containerized execution

Active Development Combo

Architect:
twhitworth/gpt-oss-120b-awq-w4a16

Developer:
cyankiwi/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit

Constraint Reality

These models cannot be treated as simultaneously resident for reliable orchestration on the current target GPU.

Therefore the system must support:

single-active-model scheduling

swap-safe orchestration

context externalization

developer-primary loop operation

architect-on-demand reasoning

Operational Consequences

swap latency is part of the product behavior

prompt reconstruction matters more than long chat transcripts

model role separation must be packetized

autonomous loop design must not assume shared live context