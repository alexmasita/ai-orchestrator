from __future__ import annotations

import contextlib
import importlib
import io
import sys


def _load_cli_module():
    try:
        return importlib.import_module("ai_orchestrator.cli")
    except ModuleNotFoundError:
        return None


def _parse_safely(parser, argv):
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        try:
            parsed = parser.parse_args(argv)
            return True, parsed, stderr.getvalue()
        except SystemExit as exc:
            return False, exc.code, stderr.getvalue()


def test_start_accepts_combo_argument():
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"
    assert hasattr(cli, "build_parser"), "Expected build_parser() contract"

    parser = cli.build_parser()
    ok, parsed_or_code, stderr_text = _parse_safely(
        parser,
        ["start", "--combo", "reasoning_80gb"],
    )

    assert ok, f"Expected combo start parse success; stderr={stderr_text!r}"
    parsed = parsed_or_code
    assert parsed.command == "start"
    assert getattr(parsed, "combo", None) == "reasoning_80gb"


def test_start_legacy_mode_still_supported():
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"
    assert hasattr(cli, "build_parser"), "Expected build_parser() contract"

    parser = cli.build_parser()
    ok, parsed_or_code, stderr_text = _parse_safely(
        parser,
        ["start", "--config", "config.yaml", "--models", "a", "b"],
    )

    assert ok, f"Expected legacy parse success; stderr={stderr_text!r}"
    parsed = parsed_or_code
    assert parsed.command == "start"
    assert getattr(parsed, "config", None) == "config.yaml"
    assert getattr(parsed, "models", None) == ["a", "b"]


def test_combo_and_models_are_mutually_exclusive():
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"
    assert hasattr(cli, "build_parser"), "Expected build_parser() contract"

    parser = cli.build_parser()
    ok, code_or_parsed, stderr_text = _parse_safely(
        parser,
        [
            "start",
            "--combo",
            "reasoning_80gb",
            "--config",
            "config.yaml",
            "--models",
            "a",
        ],
    )

    assert not ok, "Expected parse failure when --combo and --models are both provided"
    assert code_or_parsed != 0
    lowered = stderr_text.lower()
    assert "--combo" in lowered
    assert "--models" in lowered
    assert (
        "not allowed" in lowered or "mutually exclusive" in lowered
    ), "Expected explicit mutual-exclusion parser contract"


def test_wizard_defaults_to_root_config():
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"

    parser = cli.build_parser()
    ok, parsed_or_code, stderr_text = _parse_safely(parser, ["wizard"])

    assert ok, f"Expected wizard parse success; stderr={stderr_text!r}"
    parsed = parsed_or_code
    assert parsed.command == "wizard"
    assert getattr(parsed, "config", None) == "config.yaml"


def test_resolve_defaults_to_root_config():
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"

    parser = cli.build_parser()
    ok, parsed_or_code, stderr_text = _parse_safely(
        parser,
        ["resolve", "--combo", "neuroflow", "--instance-id", "32890211"],
    )

    assert ok, f"Expected resolve parse success; stderr={stderr_text!r}"
    parsed = parsed_or_code
    assert parsed.command == "resolve"
    assert getattr(parsed, "config", None) == "config.yaml"


def test_main_without_args_prints_help(monkeypatch, capsys):
    cli = _load_cli_module()
    assert cli is not None, "Expected ai_orchestrator.cli module"

    monkeypatch.setattr(sys, "argv", ["ai-orchestrator"], raising=False)
    exit_code = cli.main()

    assert exit_code == 0
    stdout = capsys.readouterr().out
    assert "wizard" in stdout
    assert "combos" in stdout
    assert "resolve" in stdout
