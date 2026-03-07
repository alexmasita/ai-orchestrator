from __future__ import annotations


def compute_snapshot_namespace(combo_name: str, snapshot_version: str) -> str:
    # Preserve existing v1-style namespace compatibility while supporting
    # combo-scoped version-first namespaces for combo runtime assets.
    if "-" in snapshot_version or "_" in snapshot_version:
        return f"{snapshot_version}_{combo_name}"
    return f"{combo_name}{snapshot_version}"


def is_snapshot_compatible(
    snapshot_namespace: str,
    combo_name: str,
    snapshot_version: str,
) -> bool:
    expected_namespace = compute_snapshot_namespace(combo_name, snapshot_version)
    return snapshot_namespace == expected_namespace
