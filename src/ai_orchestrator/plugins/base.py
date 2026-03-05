class ModelPlugin:
    name = ""
    ports = ()

    def required_vram_gb(self, config):
        raise NotImplementedError

    def required_disk_gb(self, config):
        raise NotImplementedError

    def snapshot_assets(self):
        raise NotImplementedError

    def runtime_env(self):
        raise NotImplementedError
