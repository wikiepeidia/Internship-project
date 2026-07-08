"""Wave 0 CLI expectations for the Phase 2 runtime."""

import argparse
import importlib
import io
import re
import sys
from pathlib import Path

from src.runtime.contracts import AnalysisResult, DoctorStatus

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_LAUNCHER_PATH = REPO_ROOT / "scripts" / "START_DEMO_UI.bat"
ANALYZE_LAUNCHER_PATH = REPO_ROOT / "scripts" / "START_TEXT_ANALYZE.bat"

# Patterns that would interpolate pasted user text through cmd variables.
USER_TEXT_INTERPOLATION_PATTERN = re.compile(
    r"(?i)set\s+/p|for\s+/f|%\*|%1|%2|%TEXT%|%MESSAGE%|%INPUT%|!TEXT!|!MESSAGE!|!INPUT!"
)


def _load_cli_module():
    return importlib.import_module("src.runtime.cli")


def test_analyze_reads_single_message_from_stdin_when_text_flag_absent(
    monkeypatch,
    capsys,
    sample_mixed_vn_en_message,
):
    cli_module = _load_cli_module()
    captured = {}

    class FakeService:
        def analyze_text(self, text: str, channel: str = "unknown") -> AnalysisResult:
            captured["text"] = text
            captured["channel"] = channel
            return AnalysisResult(
                risk_tier="suspicious",
                summary="Provisional suspicious result.",
                backend_name="heuristic",
            )

    monkeypatch.setattr(
        cli_module,
        "run_runtime_doctor",
        lambda: DoctorStatus(ready=True, backend_name="heuristic", checks=[]),
    )
    monkeypatch.setattr(cli_module, "build_default_runtime_service", lambda: FakeService())
    monkeypatch.setattr(
        cli_module,
        "render_analysis_result",
        lambda result: "\n".join(
            [
                "Provisional suspicious result.",
                '"mã OTP" - Yêu cầu mã xác thực nhạy cảm',
                '"Smart OTP" - Nhắc tới công cụ xác thực ngân hàng',
                '"link đăng nhập" - Dẫn người dùng tới liên kết đăng nhập',
            ]
        ),
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(sample_mixed_vn_en_message))

    exit_code = cli_module.main(["analyze"])

    output = capsys.readouterr().out.strip().splitlines()
    assert exit_code == 0
    assert captured["text"] == sample_mixed_vn_en_message
    assert captured["channel"] == "unknown"
    assert len([line for line in output if line.startswith('"')]) <= 3


def test_analyze_accepts_text_escape_hatch_for_automation(monkeypatch, sample_benign_message):
    cli_module = _load_cli_module()
    captured = {}

    class FakeService:
        def analyze_text(self, text: str, channel: str = "unknown") -> AnalysisResult:
            captured["text"] = text
            captured["channel"] = channel
            return AnalysisResult(
                risk_tier="benign",
                summary="Provisional benign result.",
                backend_name="heuristic",
            )

    monkeypatch.setattr(
        cli_module,
        "run_runtime_doctor",
        lambda: DoctorStatus(ready=True, backend_name="heuristic", checks=[]),
    )
    monkeypatch.setattr(cli_module, "build_default_runtime_service", lambda: FakeService())
    monkeypatch.setattr(cli_module, "render_analysis_result", lambda result: result.summary)

    exit_code = cli_module.main(
        ["analyze", "--text", sample_benign_message, "--channel", "telegram"]
    )

    assert exit_code == 0
    assert captured["text"] == sample_benign_message
    assert captured["channel"] == "telegram"


def test_cli_only_exposes_analyze_doctor_and_demo_commands():
    cli_module = _load_cli_module()
    parser = cli_module.build_parser()

    subparsers_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )

    assert sorted(subparsers_action.choices.keys()) == ["analyze", "demo", "doctor"]


def test_root_help_lists_analyze_demo_and_doctor_commands():
    cli_module = _load_cli_module()
    parser = cli_module.build_parser()

    root_help = parser.format_help()

    assert "analyze" in root_help
    assert "demo" in root_help
    assert "doctor" in root_help


def test_analyze_help_states_terminal_text_only_no_browser():
    cli_module = _load_cli_module()
    parser = cli_module.build_parser()

    subparsers_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    analyze_help = subparsers_action.choices["analyze"].format_help().lower()

    assert "text-only" in analyze_help or "text only" in analyze_help
    assert "no browser" in analyze_help
    assert "stdin" in analyze_help or "--text" in analyze_help


def test_demo_help_states_starts_web_ui_and_opens_browser():
    cli_module = _load_cli_module()
    parser = cli_module.build_parser()

    subparsers_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    demo_help = subparsers_action.choices["demo"].format_help().lower()

    assert "web ui" in demo_help
    assert "browser" in demo_help
    assert "--no-browser" in demo_help


def test_demo_command_starts_local_demo_server(monkeypatch):
    cli_module = _load_cli_module()
    captured = {}

    def fake_run_demo_server(*, host: str, port: int, open_browser: bool) -> int:
        captured["host"] = host
        captured["port"] = port
        captured["open_browser"] = open_browser
        return 0

    monkeypatch.setattr(cli_module, "run_demo_server", fake_run_demo_server)

    exit_code = cli_module.main(["demo", "--host", "127.0.0.1", "--port", "8765", "--no-browser"])

    assert exit_code == 0
    assert captured == {
        "host": "127.0.0.1",
        "port": 8765,
        "open_browser": False,
    }


def test_analyze_prints_phase_four_result_through_existing_command_surface(monkeypatch, capsys):
    cli_module = _load_cli_module()

    class FakeService:
        def analyze_text(self, text: str, channel: str = "unknown") -> AnalysisResult:
            return AnalysisResult(
                risk_tier="high-risk",
                summary="Mocked Phase 4 result.",
                threat_labels=["bank_impersonation"],
                recommendations=["Khong bam vao lien ket trong tin nhan."],
                backend_name="heuristic",
            )

    monkeypatch.setattr(
        cli_module,
        "run_runtime_doctor",
        lambda: DoctorStatus(ready=True, backend_name="heuristic", checks=[]),
    )
    monkeypatch.setattr(cli_module, "build_default_runtime_service", lambda: FakeService())
    monkeypatch.setattr(
        cli_module,
        "render_analysis_result",
        lambda result: "\n".join(
            [
                "Mocked Phase 4 result.",
                "Risk tier: High risk",
                "Threat labels: Bank impersonation",
                "Next steps:",
                "- Khong bam vao lien ket trong tin nhan.",
            ]
        ),
    )

    exit_code = cli_module.main(["analyze", "--text", "VPBank yeu cau OTP"])

    output = capsys.readouterr().out.strip()
    assert exit_code == 0
    assert "Risk tier: High risk" in output
    assert "Threat labels: Bank impersonation" in output


def test_analyze_uses_phase_four_gguf_default_when_ready(monkeypatch, capsys):
    cli_module = _load_cli_module()

    class FakeService:
        def analyze_text(self, text: str, channel: str = "unknown") -> AnalysisResult:
            return AnalysisResult(
                risk_tier="high-risk",
                summary="GGUF default analyze path.",
                threat_labels=["bank_impersonation"],
                recommendations=["Khong bam vao lien ket trong tin nhan."],
                backend_name="gguf",
            )

    monkeypatch.setattr(
        cli_module,
        "run_runtime_doctor",
        lambda: DoctorStatus(ready=True, backend_name="gguf", checks=[]),
    )
    monkeypatch.setattr(cli_module, "build_default_runtime_service", lambda: FakeService())
    monkeypatch.setattr(
        cli_module,
        "render_analysis_result",
        lambda result: "\n".join([result.summary, f"backend={result.backend_name}"]),
    )

    exit_code = cli_module.main(["analyze", "--text", "VPBank yeu cau xac minh OTP"])

    output = capsys.readouterr().out.strip()
    assert exit_code == 0
    assert "backend=gguf" in output


def test_analyze_returns_setup_guidance_when_doctor_is_not_ready(monkeypatch, capsys):
    cli_module = _load_cli_module()

    monkeypatch.setattr(
        cli_module,
        "run_runtime_doctor",
        lambda: DoctorStatus(
            ready=False,
            backend_name="gguf",
            checks=[],
            setup_steps=["python -m src.runtime.cli doctor"],
        ),
    )
    monkeypatch.setattr(cli_module, "format_doctor_report", lambda status: "NOT READY")

    exit_code = cli_module.main(["analyze", "--text", "hello world"])

    assert exit_code == 2
    assert capsys.readouterr().out.strip() == "NOT READY"


def test_demo_launcher_batch_file_exists_and_runs_from_repo_root():
    assert DEMO_LAUNCHER_PATH.exists()

    text = DEMO_LAUNCHER_PATH.read_text(encoding="utf-8")

    assert 'cd /d "%~dp0.."' in text
    assert re.search(r"chcp\s+65001", text)
    assert "src.runtime.cli demo" in text
    assert not USER_TEXT_INTERPOLATION_PATTERN.search(text)


def test_text_analyze_launcher_batch_file_exists_and_runs_from_repo_root():
    assert ANALYZE_LAUNCHER_PATH.exists()

    text = ANALYZE_LAUNCHER_PATH.read_text(encoding="utf-8")

    assert 'cd /d "%~dp0.."' in text
    assert re.search(r"chcp\s+65001", text)
    assert "src.runtime.cli analyze" in text
    assert not USER_TEXT_INTERPOLATION_PATTERN.search(text)


def test_launcher_batch_files_do_not_interpolate_pasted_text():
    for path in (DEMO_LAUNCHER_PATH, ANALYZE_LAUNCHER_PATH):
        text = path.read_text(encoding="utf-8")
        assert not USER_TEXT_INTERPOLATION_PATTERN.search(text), (
            f"{path} appears to interpolate user text through cmd variables"
        )