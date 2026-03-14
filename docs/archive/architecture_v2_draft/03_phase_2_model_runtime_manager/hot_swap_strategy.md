Hot-Swap Strategy
Primary Runtime Rule

For the current 80GB-class combo on ~94GB GPU:

only one large reasoning model is active at a time

Why

The architect and developer models are too large to rely on simultaneous stable residency.

Core logic must assume:

no shared persistent KV cache between roles

all cross-role continuity is packetized

Swap Flow

current role completes response

structured packet persisted

runtime manager unloads current model if necessary

target role model starts

health check and ready state confirmed

target role receives reconstructed context bundle

invocation proceeds

Correctness Rule

Swap latency may affect speed.
It must not affect correctness.