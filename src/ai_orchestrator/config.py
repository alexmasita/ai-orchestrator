from __future__ import annotations

from typing import Any

try:
    import yaml as _yaml
except Exception:  # pragma: no cover
    _yaml = None


class _FallbackYaml:
    @staticmethod
    def _strip_one_layer_quotes(value: str) -> str:
        if len(value) >= 2 and ((value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'")):
            return value[1:-1]
        return value

    @staticmethod
    def safe_load(stream) -> dict[str, Any]:
        text = stream.read() if hasattr(stream, "read") else str(stream)
        parsed: dict[str, Any] = {}
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if ":" not in stripped:
                continue
            key, raw_value = stripped.split(":", 1)
            value = raw_value.strip()
            key = key.strip()

            # Quoted scalars are treated as strings with one quote layer removed.
            if len(value) >= 2 and ((value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'")):
                parsed[key] = _FallbackYaml._strip_one_layer_quotes(value)
                continue

            lowered = value.lower()
            if lowered == "true":
                parsed[key] = True
            elif lowered == "false":
                parsed[key] = False
            else:
                try:
                    parsed[key] = int(value)
                except ValueError:
                    try:
                        parsed[key] = float(value)
                    except ValueError:
                        parsed[key] = value
        return parsed


yaml = _yaml if _yaml is not None else _FallbackYaml()


class ConfigError(Exception):
    pass


_REQUIRED_FIELDS = (
    "vast_api_key",
    "vast_api_url",
    "snapshot_version",
    "idle_timeout_seconds",
    "min_reliability",
    "min_inet_up_mbps",
    "min_inet_down_mbps",
    "allow_interruptible",
    "max_dph",
)


def _strip_one_layer_quotes(value: str) -> str:
    if len(value) >= 2 and ((value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'")):
        return value[1:-1]
    return value


def _normalize_vast_api_url(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = _strip_one_layer_quotes(value.strip())
    return normalized.rstrip("/")


def load_config(path):
    with open(path, "r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)

    if not isinstance(loaded, dict):
        raise ConfigError("Config must parse to a dict")

    for field in _REQUIRED_FIELDS:
        if field not in loaded:
            raise ConfigError(f"Missing required field: {field}")

    loaded["vast_api_url"] = _normalize_vast_api_url(loaded["vast_api_url"])
    return loaded
