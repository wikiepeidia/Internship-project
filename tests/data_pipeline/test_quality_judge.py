"""Tests for the synthetic data quality judge."""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx

from src.data_pipeline.generation.quality_judge import (
    CLAUDE_MODEL,
    GEMINI_MODEL,
    OPENAI_COMPATIBLE_JUDGE_KEY,
    QualityJudge,
)


def _settings(
    gemini_key: str = "gemini",
    anthropic_key: str = "anthropic",
    openai_compatible_base_url: str = "",
    openai_compatible_api_key: str = "",
    openai_compatible_model: str = "",
):
    return SimpleNamespace(
        gemini_api_key=gemini_key,
        google_oauth_access_token="",
        anthropic_api_key=anthropic_key,
        google_application_credentials="",
        google_cloud_project="",
        gemini_use_adc=False,
        openai_compatible_base_url=openai_compatible_base_url,
        openai_compatible_api_key=openai_compatible_api_key,
        openai_compatible_model=openai_compatible_model,
    )


def _response_text(
    realism: int,
    label_correctness: int,
    code_switch_naturalness: int,
    risk_tier_correctness: int,
    suspicious_span_accuracy: int,
    reason: str,
) -> str:
    return json.dumps(
        {
            "realism": realism,
            "label_correctness": label_correctness,
            "code_switch_naturalness": code_switch_naturalness,
            "risk_tier_correctness": risk_tier_correctness,
            "suspicious_span_accuracy": suspicious_span_accuracy,
            "pass": all(
                value >= 3
                for value in (
                    realism,
                    label_correctness,
                    code_switch_naturalness,
                    risk_tier_correctness,
                    suspicious_span_accuracy,
                )
            ),
            "reason": reason,
        }
    )


def test_judge_record_pass(sample_dataset_record):
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "candidates": [
                {"content": {"parts": [{"text": _response_text(4, 4, 5, 4, 5, "Looks realistic")}]}}
            ]
        },
    )
    judge = QualityJudge(
        settings=_settings(),
        http_client=SimpleNamespace(post=lambda *args, **kwargs: response),
    )
    record = sample_dataset_record.model_dump() | {"source": "synthetic_claude"}

    verdict = judge.judge_record(record)

    assert verdict.pass_verdict is True
    assert verdict.realism == 4
    assert verdict.risk_tier_correctness == 4
    assert verdict.suspicious_span_accuracy == 5


def test_judge_record_fail(sample_dataset_record):
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "candidates": [
                {"content": {"parts": [{"text": _response_text(2, 4, 4, 4, 4, "Too templated")}]}}
            ]
        },
    )
    judge = QualityJudge(
        settings=_settings(),
        http_client=SimpleNamespace(post=lambda *args, **kwargs: response),
    )
    record = sample_dataset_record.model_dump() | {"source": "synthetic_claude"}

    verdict = judge.judge_record(record)

    assert verdict.pass_verdict is False
    assert verdict.reason == "Too templated"


def test_filter_passed(sample_dataset_record, sample_benign_record):
    judge = QualityJudge(settings=_settings())
    judge.judge_batch = lambda records: [
        (records[0], judge.judge_record(records[0])),
        (records[1], judge.judge_record(records[1])),
    ]
    judge.judge_record = lambda record: SimpleNamespace(
        realism=4,
        label_correctness=4,
        code_switch_naturalness=4,
        risk_tier_correctness=4,
        suspicious_span_accuracy=4,
        pass_verdict=record["label"] != "benign",
        reason="ok",
    )

    passed, stats = judge.filter_passed([sample_dataset_record.model_dump(), sample_benign_record.model_dump()])

    assert len(passed) == 1
    assert stats.passed == 1
    assert stats.failed == 1


def test_quality_stats(sample_dataset_record, sample_benign_record):
    judge = QualityJudge(settings=_settings())
    judge.judge_batch = lambda records: [
        (
            records[0],
            SimpleNamespace(
                realism=5,
                label_correctness=4,
                code_switch_naturalness=5,
                risk_tier_correctness=5,
                suspicious_span_accuracy=4,
                pass_verdict=True,
                reason="good",
            ),
        ),
        (
            records[1],
            SimpleNamespace(
                realism=2,
                label_correctness=3,
                code_switch_naturalness=2,
                risk_tier_correctness=3,
                suspicious_span_accuracy=2,
                pass_verdict=False,
                reason="weak",
            ),
        ),
    ]

    _, stats = judge.filter_passed([sample_dataset_record.model_dump(), sample_benign_record.model_dump()])

    assert stats.pass_rate == 0.5
    assert stats.avg_realism == 3.5
    assert stats.avg_label_correctness == 3.5
    assert stats.avg_code_switch_naturalness == 3.5
    assert stats.avg_risk_tier_correctness == 4.0
    assert stats.avg_suspicious_span_accuracy == 3.0


def test_filter_passed_emits_progress(sample_dataset_record):
    judge = QualityJudge(settings=_settings())
    progress_messages: list[str] = []
    judge.judge_batch = lambda records, progress_callback=None: [
        (
            records[0],
            SimpleNamespace(
                realism=4,
                label_correctness=4,
                code_switch_naturalness=4,
                risk_tier_correctness=4,
                suspicious_span_accuracy=4,
                pass_verdict=True,
                reason="ok",
            ),
        )
    ]

    passed, stats = judge.filter_passed([sample_dataset_record.model_dump()], progress_callback=progress_messages.append)

    assert len(passed) == 1
    assert stats.passed == 1


def test_uses_different_model_than_generator():
    judge = QualityJudge(settings=_settings())

    assert judge._select_judge_model("synthetic_claude") == GEMINI_MODEL

    claude_judge = QualityJudge(settings=_settings(gemini_key="", anthropic_key="anthropic"), anthropic_client=object())
    assert claude_judge._select_judge_model("synthetic_gemini") == CLAUDE_MODEL


def test_selects_gemini_when_adc_is_configured():
    judge = QualityJudge(
        settings=SimpleNamespace(
            gemini_api_key="",
            anthropic_api_key="anthropic",
            google_application_credentials="creds.json",
            google_cloud_project="quota-project",
            gemini_use_adc=True,
            openai_compatible_base_url="",
            openai_compatible_api_key="",
            openai_compatible_model="",
        )
    )

    assert judge._select_judge_model("synthetic_claude") == GEMINI_MODEL


def test_judge_falls_back_to_claude_when_gemini_is_disabled(sample_dataset_record):
    request = httpx.Request("POST", "https://generativelanguage.googleapis.com")
    gemini_error = httpx.HTTPStatusError(
        "Gemini disabled",
        request=request,
        response=httpx.Response(403, request=request),
    )

    anthropic_client = SimpleNamespace(
        messages=SimpleNamespace(
            create=lambda **_: SimpleNamespace(content=[SimpleNamespace(text=_response_text(4, 4, 4, 4, 4, "Claude fallback"))])
        )
    )
    judge = QualityJudge(
        settings=_settings(),
        anthropic_client=anthropic_client,
        http_client=SimpleNamespace(post=lambda *args, **kwargs: (_ for _ in ()).throw(gemini_error)),
    )
    record = sample_dataset_record.model_dump() | {"source": "synthetic_claude"}

    verdict = judge.judge_record(record)

    assert verdict.pass_verdict is True
    assert verdict.reason == "Claude fallback"


def test_judge_uses_adc_when_configured(sample_dataset_record, monkeypatch):
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "candidates": [
                {"content": {"parts": [{"text": _response_text(4, 4, 5, 4, 4, "ADC Gemini")}]}}
            ]
        },
    )
    request_capture: dict[str, object] = {}

    class FakeCredentials:
        valid = False
        token = None
        quota_project_id = None

        def refresh(self, request):
            self.valid = True
            self.token = "adc-token"

    def fake_post(url, *args, **kwargs):
        request_capture["headers"] = kwargs.get("headers")
        request_capture["params"] = kwargs.get("params")
        return response

    monkeypatch.setattr(
        "src.data_pipeline.generation.gemini_auth._load_google_credentials",
        lambda credentials_path, scopes: (FakeCredentials(), "quota-project"),
    )
    judge = QualityJudge(
        settings=SimpleNamespace(
            gemini_api_key="",
            anthropic_api_key="anthropic",
            google_application_credentials="creds.json",
            google_cloud_project="quota-project",
            gemini_use_adc=True,
            openai_compatible_base_url="",
            openai_compatible_api_key="",
            openai_compatible_model="",
        ),
        http_client=SimpleNamespace(post=fake_post),
    )
    record = sample_dataset_record.model_dump() | {"source": "synthetic_claude"}

    verdict = judge.judge_record(record)

    assert verdict.pass_verdict is True
    assert verdict.reason == "ADC Gemini"
    assert request_capture["params"] is None
    assert request_capture["headers"]["Authorization"] == "Bearer adc-token"


def test_judge_uses_oauth_access_token_when_configured(sample_dataset_record):
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "candidates": [
                {"content": {"parts": [{"text": _response_text(4, 4, 5, 4, 4, "OAuth Gemini")}]}}
            ]
        },
    )
    request_capture: dict[str, object] = {}

    def fake_post(url, *args, **kwargs):
        request_capture["headers"] = kwargs.get("headers")
        request_capture["params"] = kwargs.get("params")
        return response

    settings = _settings(gemini_key="", anthropic_key="")
    settings.google_oauth_access_token = "oauth-token"
    settings.google_cloud_project = "project-37c29ced-23da-4655-aff"
    judge = QualityJudge(settings=settings, http_client=SimpleNamespace(post=fake_post))

    verdict = judge.judge_record(sample_dataset_record.model_dump() | {"source": "synthetic_claude"})

    assert verdict.pass_verdict is True
    assert verdict.reason == "OAuth Gemini"
    assert request_capture["params"] is None
    assert request_capture["headers"]["Authorization"] == "Bearer oauth-token"
    assert request_capture["headers"]["x-goog-user-project"] == "project-37c29ced-23da-4655-aff"


def test_judge_prefers_adc_over_oauth_token_when_adc_is_explicit(sample_dataset_record, monkeypatch):
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "candidates": [
                {"content": {"parts": [{"text": _response_text(4, 4, 5, 4, 4, "ADC beats stale token")}]}}
            ]
        },
    )
    request_capture: dict[str, object] = {}

    class FakeCredentials:
        valid = False
        token = None
        quota_project_id = None

        def refresh(self, request):
            self.valid = True
            self.token = "adc-token"

    def fake_post(url, *args, **kwargs):
        request_capture["headers"] = kwargs.get("headers")
        return response

    monkeypatch.setattr(
        "src.data_pipeline.generation.gemini_auth._load_google_credentials",
        lambda credentials_path, scopes: (FakeCredentials(), "quota-project"),
    )
    settings = _settings(gemini_key="", anthropic_key="")
    settings.google_oauth_access_token = "stale-oauth-token"
    settings.google_cloud_project = "quota-project"
    settings.gemini_use_adc = True
    judge = QualityJudge(settings=settings, http_client=SimpleNamespace(post=fake_post))

    verdict = judge.judge_record(sample_dataset_record.model_dump() | {"source": "synthetic_claude"})

    assert verdict.pass_verdict is True
    assert verdict.reason == "ADC beats stale token"
    assert request_capture["headers"]["Authorization"] == "Bearer adc-token"


def test_selects_openai_compatible_when_no_other_key_configured():
    judge = QualityJudge(
        settings=_settings(
            gemini_key="",
            anthropic_key="",
            openai_compatible_base_url="https://colab-tunnel.example/v1",
            openai_compatible_model="Qwen/Qwen2.5-32B-Instruct-AWQ",
        )
    )
    assert judge._select_judge_model("synthetic_openai_compatible") == OPENAI_COMPATIBLE_JUDGE_KEY
    assert judge._select_judge_model(None) == OPENAI_COMPATIBLE_JUDGE_KEY


def test_openai_compatible_source_cross_judges_with_gemini_when_available():
    judge = QualityJudge(
        settings=_settings(
            gemini_key="gemini",
            openai_compatible_base_url="https://colab-tunnel.example/v1",
            openai_compatible_model="Qwen/Qwen2.5-32B-Instruct-AWQ",
        )
    )
    assert judge._select_judge_model("synthetic_openai_compatible") == GEMINI_MODEL


def test_call_judge_openai_compatible(sample_dataset_record):
    request_capture: dict[str, object] = {}

    def fake_post(url, *args, **kwargs):
        request_capture["url"] = url
        request_capture["json"] = kwargs.get("json")
        request_capture["headers"] = kwargs.get("headers")
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "choices": [
                    {"message": {"content": _response_text(4, 4, 4, 4, 4, "Colab judge ok")}}
                ]
            },
        )

    judge = QualityJudge(
        settings=_settings(
            gemini_key="",
            anthropic_key="",
            openai_compatible_base_url="https://colab-tunnel.example/v1",
            openai_compatible_api_key="test-token",
            openai_compatible_model="Qwen/Qwen2.5-32B-Instruct-AWQ",
        ),
        http_client=SimpleNamespace(post=fake_post),
    )
    record = sample_dataset_record.model_dump() | {"source": "synthetic_openai_compatible"}

    verdict = judge.judge_record(record)

    assert verdict.pass_verdict is True
    assert verdict.reason == "Colab judge ok"
    assert request_capture["url"] == "https://colab-tunnel.example/v1/chat/completions"
    assert request_capture["headers"]["Authorization"] == "Bearer test-token"
    assert request_capture["json"]["model"] == "Qwen/Qwen2.5-32B-Instruct-AWQ"
    assert request_capture["json"]["temperature"] == 0.3