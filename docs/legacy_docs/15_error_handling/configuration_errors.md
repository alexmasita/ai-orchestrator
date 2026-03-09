# Configuration Errors

Configuration errors occur when the system cannot load or validate the user-provided configuration file.

These errors originate from:


src/ai_orchestrator/config.py


---

# Configuration Loading

Configuration files are loaded through:


load_config(path)


The loader performs the following steps:

1. Read YAML file
2. Normalize values
3. Validate required keys
4. Return deterministic configuration dictionary

---

# Configuration Error Type

Configuration failures raise:


ConfigError


This exception indicates the configuration file cannot be safely used.

---

# Examples of Configuration Errors

## Missing Config File

Example:


ai-orchestrator start --config missing.yaml


Result:


Configuration error: file not found


---

## Invalid YAML

Example:


vast_api_url: https://console.vast.ai/api/v0

gpu:
min_vram_gb: 24
invalid indentation


Result:


Configuration error: invalid YAML syntax


---

## Missing Required Fields

Example missing field:


vast_api_key


Error:


Configuration error: missing required field 'vast_api_key'


---

# Configuration Normalization

The loader performs normalization to avoid common user errors.

Examples:

### Remove Quotes


vast_api_url: "https://console.vast.ai/api/v0/
"


Normalized to:


https://console.vast.ai/api/v0


---

### Remove Trailing Slash


https://console.vast.ai/api/v0/


Normalized to:


https://console.vast.ai/api/v0


---

# CLI Handling

The CLI catches configuration errors.

Example:

```python
try:
    config = load_config(args.config)
except ConfigError:
    return 1

Result:

Configuration error: invalid configuration

The CLI exits with code:

1
Deterministic Behavior

Configuration errors must always:

fail immediately

not attempt recovery

not attempt default inference

produce deterministic messages

Summary

Configuration errors prevent the system from launching.

They guarantee:

invalid configurations cannot produce undefined behavior

runtime orchestration never starts with malformed inputs