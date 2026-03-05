from ai_orchestrator.plugins.deepseek_llamacpp import DeepSeekLlamaCppPlugin


def _plugin_mapping():
    return {"deepseek": DeepSeekLlamaCppPlugin}


def list_plugin_names():
    return sorted(_plugin_mapping().keys())


def get_plugin_registry():
    return dict(_plugin_mapping())


def get_plugin_by_name(name):
    registry = get_plugin_registry()
    if name not in registry:
        raise KeyError(name)
    return registry[name]
