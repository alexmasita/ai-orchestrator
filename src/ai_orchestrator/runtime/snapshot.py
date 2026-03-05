from __future__ import annotations


def get_snapshot_version(config: dict) -> str:
    snapshot_version = config["snapshot_version"]
    if not isinstance(snapshot_version, str):
        raise TypeError("snapshot_version must be a string")
    return snapshot_version

