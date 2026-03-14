Context Reconstruction
Purpose

Because model KV state is not preserved across swaps, the orchestrator must rebuild sufficient state for each invocation.

Reconstruction Inputs

normalized task intent

current repo context

latest architect plan packet

latest developer packet

recent failure packet

current iteration summary

tool result summary

explicit role request

Reconstruction Rules

summaries first

raw transcript last resort

only include relevant file slices

include explicit next objective

include current stop constraints