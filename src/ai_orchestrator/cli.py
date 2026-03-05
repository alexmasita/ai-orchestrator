from __future__ import annotations

import argparse
import json
import sys

from ai_orchestrator.config import ConfigError, load_config
from ai_orchestrator.orchestrator import run_orchestration
from ai_orchestrator.provider.vast import VastProvider, VastProviderError
from ai_orchestrator.sizing import OrchestratorConfigError, SizingInput, compute_requirements


def build_parser():
    parser = argparse.ArgumentParser(prog="ai-orchestrator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--config", required=True)
    start_parser.add_argument("--models", nargs="+", required=True)
    subparsers.add_parser("docs")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "docs":
        try:
            from ai_orchestrator.devserver.app import run_dev_server
        except ModuleNotFoundError as exc:
            if exc.name in {"fastapi", "uvicorn"}:
                print(
                    "Missing optional dependencies for docs server. "
                    "Install with: pip install -e .[devdocs]",
                    file=sys.stderr,
                )
                return 1
            raise
        run_dev_server()
        return 0

    if args.command != "start":
        return 1

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    sizing_input = SizingInput(models=args.models, config=config)
    try:
        sizing_result = compute_requirements(sizing_input)
        provider = VastProvider(api_key=config["vast_api_key"], base_url=config["vast_api_url"])
        raw_result = run_orchestration(
            provider=provider,
            sizing_result=sizing_result,
            config=config,
        )
    except OrchestratorConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1
    except VastProviderError as exc:
        print(f"Provider error: {exc}", file=sys.stderr)
        return 1
    gpu_type = raw_result.get("gpu_type") or raw_result.get("gpu_name")
    cost_per_hour = raw_result.get("cost_per_hour") or raw_result.get("dph")
    result = {
        "instance_id": raw_result["instance_id"],
        "gpu_type": gpu_type,
        "cost_per_hour": cost_per_hour,
        "idle_timeout": raw_result["idle_timeout"],
        "snapshot_version": raw_result["snapshot_version"],
        "deepseek_url": raw_result.get("deepseek_url", "http://127.0.0.1:8080"),
        "whisper_url": raw_result.get("whisper_url", "http://127.0.0.1:9000"),
    }
    print(json.dumps(result, sort_keys=True), end="")
    return 0
