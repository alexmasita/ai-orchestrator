Overview

The plugin registry is responsible for resolving model names into plugin implementations.

It acts as a deterministic lookup table.

Location:

src/ai_orchestrator/plugins/registry.py
Registry Responsibilities

The registry performs the following tasks:

register plugins

validate model names

return plugin instances

enforce deterministic ordering

Registry Structure

Plugins are registered in a dictionary.

Example:

PLUGINS = {
  "deepseek_llamacpp": DeepSeekPlugin,
  "whisper": WhisperPlugin
}
Model Resolution

Given a model list:

["deepseek_llamacpp", "whisper"]

The registry performs:

resolve_plugins(model_list)

Returns:

[
  DeepSeekPlugin(),
  WhisperPlugin()
]
Deterministic Ordering

Plugins are returned in exactly the order provided by the CLI.

Example:

--models whisper deepseek_llamacpp

must produce:

[WhisperPlugin(), DeepSeekPlugin()]

This ensures deterministic bootstrap script generation.

Validation Behavior

The registry validates all model names.

If a plugin is unknown:

Unknown model: <name>

An error is raised before orchestration proceeds.

Plugin Registration Rules

Plugins must be:

statically registered

deterministic

side-effect free

Dynamic plugin loading is intentionally avoided.

Reason:

reduces runtime unpredictability

simplifies testing

ensures deterministic behavior