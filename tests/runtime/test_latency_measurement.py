from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest


def _load_module():
    path = Path("historical/tooling/runtime-validation/measure_cold_latency.py")
    spec = importlib.util.spec_from_file_location("measure_cold_latency", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_load_locked_prompts_reads_phase28_shape(tmp_path):
    module = _load_module()
    prompts_path = tmp_path / "results.json"
    prompts_path.write_text(
        json.dumps(
            {
                "golden_scam": {"text": "scam text", "channel": "sms"},
                "golden_benign": {"text": "benign text", "channel": "sms"},
            }
        ),
        encoding="utf-8",
    )

    prompts = module.load_locked_prompts(prompts_path)

    assert prompts["scam"]["text"] == "scam text"
    assert prompts["scam"]["expected_risk_tier"] == "high-risk"
    assert prompts["scam"]["expected_labels"] == ["bank_impersonation"]
    assert prompts["benign"]["text"] == "benign text"
    assert prompts["benign"]["expected_risk_tier"] == "benign"


def test_validate_args_requires_post_reboot_for_evidence():
    module = _load_module()
    parser = module.build_parser()
    args = parser.parse_args(["--condition", "ac-high-performance", "--run-purpose", "evidence"])

    with pytest.raises(ValueError, match="post-reboot"):
        module.validate_args(args)


def test_validate_args_rejects_diagnostic_condition_for_evidence():
    module = _load_module()
    parser = module.build_parser()
    args = parser.parse_args(["--condition", "diagnostic", "--run-purpose", "evidence", "--post-reboot-confirmed"])

    with pytest.raises(ValueError, match="condition"):
        module.validate_args(args)


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


def test_build_output_path_includes_condition_purpose_and_timestamp(tmp_path):
    module = _load_module()
    recorded_at = datetime(2026, 7, 5, 14, 45, tzinfo=timezone.utc)

    output = module.build_output_path(
        "ac-high-performance",
        "evidence",
        recorded_at=recorded_at,
        artifact_dir=tmp_path,
    )

    assert output == tmp_path / "30-latency-ac-high-performance-evidence-20260705T144500Z.json"


def test_parse_prompt_sequence_rejects_unknown_prompt():
    module = _load_module()

    assert module.parse_prompt_sequence("scam, benign") == ["scam", "benign"]
    with pytest.raises(Exception, match="unknown prompt"):
        module.parse_prompt_sequence("scam,other")
