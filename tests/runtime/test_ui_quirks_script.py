from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_module():
    path = Path("historical/tooling/runtime-validation/verify_ui_quirks.py")
    spec = importlib.util.spec_from_file_location("verify_ui_quirks", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_module_exposes_schema_version_and_case_names():
    module = _load_module()

    assert module.SCHEMA_VERSION == "vnphish.phase31.ui-quirks.v1"
    assert set(module.CASE_NAMES) == {
        "empty",
        "very_long",
        "malformed",
        "mixed_vi_en",
        "double_submit",
    }


def test_build_output_path_defaults_under_phase31_artifacts_dir(tmp_path):
    module = _load_module()

    default_in_tmp = module.build_output_path(None, artifact_dir=tmp_path)
    assert default_in_tmp == tmp_path / "31-ui-quirks-results.json"

    default_real = module.build_output_path(None)
    assert default_real == Path(
        ".planning/phases/31-ui-quirks-edge-cases-regression-re-check/artifacts/"
        "31-ui-quirks-results.json"
    )


def test_build_output_path_supports_explicit_path(tmp_path):
    module = _load_module()

    explicit = tmp_path / "custom-output.json"
    assert module.build_output_path(explicit) == explicit


def test_request_latency_ms_supports_mapping_and_callable_timing():
    module = _load_module()

    class Request:
        timing = {"requestStart": 5, "responseEnd": 12.5}

    class Response:
        request = Request()

    assert module.request_latency_ms(Response()) == 7.5

    class CallableRequest:
        def timing(self):
            return {"requestStart": 1, "responseEnd": 4}

    class CallableResponse:
        request = CallableRequest()

    assert module.request_latency_ms(CallableResponse()) == 3.0


def test_build_artifact_records_overall_pass_status_and_evidence_fields():
    module = _load_module()

    cases = [
        module.build_case_record("empty", passed=True, request_count=0, typing_count=0),
        module.build_case_record("very_long", passed=True, request_count=1, typing_count=0),
    ]

    artifact = module.build_artifact(
        cases=cases,
        console_messages=[{"type": "log", "text": "hello"}],
        page_errors=[],
    )

    assert artifact["schema"] == module.SCHEMA_VERSION
    assert artifact["overall_pass"] is True
    for case in artifact["cases"]:
        assert case["status"] in {"pass", "fail"}
        assert isinstance(case["passed"], bool)
        assert case["passed"] == (case["status"] == "pass")
    assert artifact["console_messages"] == [{"type": "log", "text": "hello"}]
    assert artifact["page_errors"] == []
    # Case records must not persist arbitrary raw input text.
    assert all("text" not in case for case in artifact["cases"])


def test_overall_pass_is_true_only_when_every_case_passed():
    module = _load_module()

    all_passing = [
        module.build_case_record("empty", passed=True),
        module.build_case_record("very_long", passed=True),
    ]
    assert (
        module.build_artifact(cases=all_passing, console_messages=[], page_errors=[])["overall_pass"]
        is True
    )

    one_failing = [
        module.build_case_record("empty", passed=True),
        module.build_case_record("very_long", passed=False),
    ]
    assert (
        module.build_artifact(cases=one_failing, console_messages=[], page_errors=[])["overall_pass"]
        is False
    )

    no_cases = module.build_artifact(cases=[], console_messages=[], page_errors=[])
    assert no_cases["overall_pass"] is False


def test_double_submit_passed_requires_every_uiq02_criterion():
    module = _load_module()

    assert (
        module.double_submit_passed(
            completed_analyze_response_count=1,
            completed_superseded_response_count=0,
            abort_error_bubble_count=0,
            typing_count=0,
            button_disabled=False,
        )
        is True
    )

    # Superseded response also completed (abort guard failed).
    assert (
        module.double_submit_passed(
            completed_analyze_response_count=2,
            completed_superseded_response_count=1,
            abort_error_bubble_count=0,
            typing_count=0,
            button_disabled=False,
        )
        is False
    )

    # AbortError leaked into the UI as a rendered error bubble.
    assert (
        module.double_submit_passed(
            completed_analyze_response_count=1,
            completed_superseded_response_count=0,
            abort_error_bubble_count=1,
            typing_count=0,
            button_disabled=False,
        )
        is False
    )

    # Orphaned typing indicator left behind.
    assert (
        module.double_submit_passed(
            completed_analyze_response_count=1,
            completed_superseded_response_count=0,
            abort_error_bubble_count=0,
            typing_count=1,
            button_disabled=False,
        )
        is False
    )

    # Button stuck disabled after settle.
    assert (
        module.double_submit_passed(
            completed_analyze_response_count=1,
            completed_superseded_response_count=0,
            abort_error_bubble_count=0,
            typing_count=0,
            button_disabled=True,
        )
        is False
    )


def test_build_parser_supports_port_output_headed_and_cases(tmp_path):
    module = _load_module()
    parser = module.build_parser()

    args = parser.parse_args(
        [
            "--port",
            "8888",
            "--output",
            str(tmp_path / "out.json"),
            "--headed",
            "--cases",
            "empty,malformed",
        ]
    )

    assert args.port == 8888
    assert args.output == tmp_path / "out.json"
    assert args.headed is True
    assert args.cases == ["empty", "malformed"]


def test_build_parser_defaults_to_all_cases():
    module = _load_module()
    parser = module.build_parser()

    args = parser.parse_args([])

    assert args.port == 8765
    assert args.output is None
    assert args.headed is False
    assert list(args.cases) == list(module.CASE_NAMES)


def test_parse_case_selection_rejects_unknown_case():
    module = _load_module()

    assert module.parse_case_selection("empty, malformed") == ["empty", "malformed"]
    with pytest.raises(Exception, match="unknown case"):
        module.parse_case_selection("empty,bogus")
