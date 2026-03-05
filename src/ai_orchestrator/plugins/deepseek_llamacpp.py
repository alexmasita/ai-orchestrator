from ai_orchestrator.plugins.base import ModelPlugin


class DeepSeekLlamaCppPlugin(ModelPlugin):
    name = "deepseek"
    ports = []

    def vram_profiles_gb(self):
        return {"Q4_K_M": 20, "Q5_K_M": 26}

    def required_vram_gb(self, config):
        return max(self.vram_profiles_gb().values())

    def required_disk_gb(self, config):
        return 0

    def snapshot_assets(self):
        return []

    def runtime_env(self):
        return {}
