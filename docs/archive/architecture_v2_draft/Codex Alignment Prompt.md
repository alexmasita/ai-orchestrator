You are working inside the AI-Orchestrator repository.

Your goal is to prepare the repository for architecture alignment before MVP development begins.

You must NOT make architectural decisions.
You must gather evidence about the repository and documentation.

This task must be performed in TWO PASSES:

PASS 1 — Build an architecture analysis framework
PASS 2 — Perform repository analysis using that framework

The repository will contain three information sources:

1. Source code (current implementation)
2. docs/legacy_docs/ (previous documentation)
3. docs/architecture_v2/ (new draft architecture documents)

Your task is to analyze all three and produce evidence-based reports.

------------------------------------------------

STEP 0 — Pre-Analysis Architecture Framework

Before scanning the repository you must construct an analysis checklist.

Create:

docs/architecture_analysis_framework.md

This file must define the architectural elements that will be searched for in the repository.

Examples include (but are not limited to):

- Runtime entry points
- Model runtime management
- Agent loop logic
- API servers
- Tool execution infrastructure
- Repository mutation logic
- Session lifecycle management
- Configuration / environment handling
- Health checks / observability
- Infrastructure scripts
- CLI tools
- Testing infrastructure

For each element define:

- What the component represents
- How it would typically appear in code
- Typical file naming patterns
- Typical directory locations

Do NOT analyze the repository until this checklist is complete.

------------------------------------------------

STEP 1 — Documentation Structure

Ensure the following directory structure exists:

docs/
    architecture_v2/
    legacy_docs/

If documentation currently exists directly under docs/, move it into:

docs/legacy_docs/

Do not delete any files.

------------------------------------------------

STEP 2 — Repository Architecture Discovery

Analyze the entire repository and identify the following subsystems if they exist:

Model runtime management
Agent loop logic
API servers
Bootstrap/runtime scripts
Tool execution logic
Repository mutation logic
Session lifecycle logic
Model orchestration
Health checks
Infrastructure scripts
CLI tools
Testing infrastructure

Document your findings.

Create:

docs/repo_current_state.md

This document must describe:

- What the repository currently implements
- Major runtime entry points
- Key modules and directories
- Current orchestration behavior
- Current repo mutation approach
- Current model serving approach
- Missing architecture components

All claims MUST reference actual repository file paths.

Use the following evidence format whenever possible:

Claim:
<description>

Evidence:
<file path>
<file path>
<file path>

------------------------------------------------

STEP 3 — Implementation Mapping

Inspect the repository code and map files to architectural responsibilities.

Create:

docs/implementation_map_raw.md

Example sections:

Model Runtime
Agent Loop
API Layer
Tool Execution
Repository Mutation
Bootstrap / Infrastructure
Testing

Map directories and files to these responsibilities where possible.

Do not infer architecture that does not exist.

------------------------------------------------

STEP 4 — Legacy Documentation Analysis

Inspect every file in:

docs/legacy_docs/

For each document classify it as one of the following:

accurate
partially_accurate
conceptually_valid_but_outdated
obsolete
architecture_target

Create:

docs/legacy_docs_alignment_report.md

For each file include:

File path
Classification
Short explanation
Which repository files support or contradict the document

Do not delete any documents.

------------------------------------------------

STEP 5 — Architecture Draft Comparison

Inspect every file in:

docs/architecture_v2/

These documents represent the proposed architecture.

Compare them against the actual repository implementation.

Create:

docs/new_docs_alignment_report.md

For each document classify it as:

already_implemented
partially_aligned
architecture_target
not_supported_by_repo

Explain:

- what parts align with the repository
- what parts are not implemented yet
- which repo files relate to the document

------------------------------------------------

STEP 6 — Architecture Drift Analysis

Create:

docs/architecture_drift_findings.md

This report must identify:

Architecture concepts mentioned in documentation but missing in code.

Examples may include:

session manager
model runtime manager
agent loop supervisor
repo mutation abstraction
tool execution gateway
packet schemas

For each missing concept include:

Concept name
Which documents reference it
Whether it appears partially implemented
Which files would likely implement it in the future

------------------------------------------------

STEP 7 — Capability Gap Report

Create:

docs/mvp_gap_report.md

This document must identify what capabilities are missing to reach a minimal AI-Orchestrator MVP.

Analyze the repository for the following:

Session lifecycle
Model runtime management
Agent loop execution
Structured tool usage
Repository mutation abstraction
Verification loop
Failure packet handling

For each capability state:

implemented
partially implemented
not implemented

Include references to relevant repository files.

------------------------------------------------

STEP 8 — Alignment Summary

Create a final report:

docs/repo_alignment_report.md

This report must summarize:

Repository architecture detected
Legacy documentation alignment summary
New architecture document alignment summary
Major architecture drift areas
Capabilities missing for MVP
Recommended areas for architectural clarification

This document should only present evidence and observations.

Do NOT rewrite architecture documents.

------------------------------------------------

CONSTRAINTS

Do NOT delete documentation.
Do NOT rewrite architecture_v2 documents.
Do NOT invent architecture that does not exist in the repository.
Do NOT infer architecture without file evidence.
Every architectural claim must reference repository files.

Your job is to produce evidence so architecture decisions can be made later.