"""Tests for the synthetic generation pipeline."""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx

from src.data_pipeline.schemas import SeedRecord
from src.data_pipeline.generation.generator import TieredGenerator
from src.data_pipeline.generation.prompts import THREAT_CLASSES, build_bulk_prompt, build_complex_prompt


def _make_record(label: str, index: int, source: str = "synthetic_claude", seed_id: str = "seed_x") -> dict:
    return {
        "text": f"Tin nhắn mẫu {index} cho lớp {label} với OTP và link login giả mạo {index}",
        "label": label,
        "risk_tier": "high-risk" if label != "benign" else "benign",
        "suspicious_spans": ["OTP", "link login"] if label != "benign" else [],
        "xai_explanation": "Giải thích đủ dài để vượt qua kiểm tra chất lượng của DatasetRecord.",
        "source": source,
        "seed_id": seed_id,
    }


def _settings(
    tmp_path,
    anthropic_key: str = "anthropic",
    gemini_key: str = "gemini",
    openrouter_key: str = "openrouter",
    deepseek_key: str = "",
):
    return SimpleNamespace(
        anthropic_api_key=anthropic_key,
        gemini_api_key=gemini_key,
        google_oauth_access_token="",
        openrouter_api_key=openrouter_key,
        deepseek_api_key=deepseek_key,
        openai_compatible_base_url="",
        openai_compatible_api_key="",
        openai_compatible_model="",
        google_application_credentials="",
        google_cloud_project="",
        gemini_use_adc=False,
        data_dir=tmp_path,
    )


def test_threat_classes_constant():
    assert THREAT_CLASSES == ["bank_impersonation", "zalo_social_engineering", "task_scam", "benign"]


def test_build_complex_prompt_contains_seed_class_and_code_switch(sample_seed_record):
    prompt = build_complex_prompt(sample_seed_record.text, "bank_impersonation", num_variants=4)

    assert sample_seed_record.text in prompt
    assert "bank_impersonation" in prompt
    assert "OTP" in prompt
    assert "Internet Banking" in prompt
    assert "Smart OTP" in prompt
    assert "Vary URLs, phone numbers, urgency level" in prompt


def test_build_bulk_prompt_includes_count_and_diversity(sample_seed_record):
    prompt = build_bulk_prompt(sample_seed_record.text, "task_scam", count=12)

    assert "Generate 12 Vietnamese financial messaging examples" in prompt
    assert "Diversity instructions" in prompt
    assert "OTP" in prompt
    assert "teencode" in prompt


def test_generate_complex(sample_seed_record, tmp_path):
    response_records = [_make_record("bank_impersonation", idx) for idx in range(2)]
    anthropic_client = SimpleNamespace(
        messages=SimpleNamespace(
            create=lambda **_: SimpleNamespace(content=[SimpleNamespace(text=json.dumps(response_records))])
        )
    )
    generator = TieredGenerator(
        settings=_settings(tmp_path),
        anthropic_client=anthropic_client,
    )

    records = generator.generate_complex(sample_seed_record, "bank_impersonation", num_variants=2)

    assert len(records) == 2
    assert all(record["source"] == "synthetic_claude" for record in records)
    assert all(record["seed_id"] == records[0]["seed_id"] for record in records)


def test_generate_complex_normalizes_provider_risk_tier_aliases(sample_seed_record, tmp_path):
    response_records = [_make_record("bank_impersonation", 1) | {"risk_tier": "critical"}]
    anthropic_client = SimpleNamespace(
        messages=SimpleNamespace(
            create=lambda **_: SimpleNamespace(content=[SimpleNamespace(text=json.dumps(response_records))])
        )
    )
    generator = TieredGenerator(
        settings=_settings(tmp_path),
        anthropic_client=anthropic_client,
    )

    records = generator.generate_complex(sample_seed_record, "bank_impersonation", num_variants=1)

    assert records[0]["risk_tier"] == "high-risk"


def test_generate_complex_uses_configured_api_key_without_prebuilt_client(sample_seed_record, tmp_path):
    generator = TieredGenerator(settings=_settings(tmp_path), anthropic_client=None)
    generator._call_claude = lambda prompt, max_tokens=2000: [_make_record("bank_impersonation", 1)]

    records = generator.generate_complex(sample_seed_record, "bank_impersonation", num_variants=1)

    assert len(records) == 1
    assert records[0]["source"] == "synthetic_claude"


def test_generate_bulk(sample_seed_record, tmp_path):
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps([_make_record("task_scam", 1)])}]}}
            ]
        },
    )
    http_client = SimpleNamespace(post=lambda *args, **kwargs: response)
    generator = TieredGenerator(settings=_settings(tmp_path), http_client=http_client)

    records = generator.generate_bulk(sample_seed_record, "task_scam", count=1)

    assert len(records) == 1
    assert records[0]["source"] == "synthetic_gemini"
    assert records[0]["seed_id"]


def test_generate_bulk_uses_adc_when_configured(sample_seed_record, tmp_path, monkeypatch):
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps([_make_record("task_scam", 1)])}]}}
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
        request_capture["url"] = url
        request_capture["headers"] = kwargs.get("headers")
        request_capture["params"] = kwargs.get("params")
        return response

    monkeypatch.setattr(
        "src.data_pipeline.generation.gemini_auth._load_google_credentials",
        lambda credentials_path, scopes: (FakeCredentials(), "quota-project"),
    )
    settings = _settings(tmp_path, gemini_key="")
    settings.google_application_credentials = "creds.json"
    settings.google_cloud_project = "quota-project"
    settings.gemini_use_adc = True
    generator = TieredGenerator(
        settings=settings,
        http_client=SimpleNamespace(post=fake_post),
    )

    records = generator.generate_bulk(sample_seed_record, "task_scam", count=1)

    assert records[0]["source"] == "synthetic_gemini"
    assert request_capture["params"] is None
    assert request_capture["headers"]["Authorization"] == "Bearer adc-token"
    assert request_capture["headers"]["x-goog-user-project"] == "quota-project"


def test_generate_bulk_uses_oauth_access_token_when_configured(sample_seed_record, tmp_path):
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps([_make_record("task_scam", 1)])}]}}
            ]
        },
    )
    request_capture: dict[str, object] = {}

    def fake_post(url, *args, **kwargs):
        request_capture["url"] = url
        request_capture["headers"] = kwargs.get("headers")
        request_capture["params"] = kwargs.get("params")
        return response

    settings = _settings(tmp_path, gemini_key="")
    settings.google_oauth_access_token = "oauth-token"
    settings.google_cloud_project = "project-37c29ced-23da-4655-aff"
    generator = TieredGenerator(settings=settings, http_client=SimpleNamespace(post=fake_post))

    records = generator.generate_bulk(sample_seed_record, "task_scam", count=1)

    assert records[0]["source"] == "synthetic_gemini"
    assert request_capture["params"] is None
    assert request_capture["headers"]["Authorization"] == "Bearer oauth-token"
    assert request_capture["headers"]["x-goog-user-project"] == "project-37c29ced-23da-4655-aff"


def test_generate_bulk_prefers_adc_over_oauth_token_when_adc_is_explicit(sample_seed_record, tmp_path, monkeypatch):
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps([_make_record("task_scam", 1)])}]}}
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
    settings = _settings(tmp_path, gemini_key="")
    settings.google_oauth_access_token = "stale-oauth-token"
    settings.google_cloud_project = "quota-project"
    settings.gemini_use_adc = True
    generator = TieredGenerator(settings=settings, http_client=SimpleNamespace(post=fake_post))

    records = generator.generate_bulk(sample_seed_record, "task_scam", count=1)

    assert records[0]["source"] == "synthetic_gemini"
    assert request_capture["headers"]["Authorization"] == "Bearer adc-token"


def test_generate_bulk_falls_back_to_openrouter(sample_seed_record, tmp_path):
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "choices": [
                {"message": {"content": json.dumps([_make_record("task_scam", 1, source="synthetic_openrouter")])}}
            ]
        },
    )
    http_client = SimpleNamespace(post=lambda *args, **kwargs: response)
    generator = TieredGenerator(
        settings=_settings(tmp_path, gemini_key="", openrouter_key="openrouter"),
        http_client=http_client,
    )

    records = generator.generate_bulk(sample_seed_record, "task_scam", count=1)

    assert records[0]["source"] == "synthetic_openrouter"


def test_generate_bulk_uses_deepseek_when_configured(sample_seed_record, tmp_path):
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "choices": [
                {"message": {"content": json.dumps([_make_record("task_scam", 1, source="synthetic_deepseek")])}}
            ]
        },
    )
    http_client = SimpleNamespace(post=lambda *args, **kwargs: response)
    generator = TieredGenerator(
        settings=_settings(tmp_path, gemini_key="", openrouter_key="", deepseek_key="deepseek"),
        http_client=http_client,
        bulk_provider="deepseek",
    )

    records = generator.generate_bulk(sample_seed_record, "task_scam", count=1)

    assert len(records) == 1
    assert records[0]["source"] == "synthetic_deepseek"


def test_generate_complex_uses_openai_compatible_endpoint(sample_seed_record, tmp_path):
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "choices": [
                {
                    "message": {
                        "content": json.dumps([
                            _make_record("bank_impersonation", 1, source="synthetic_openai_compatible")
                        ])
                    }
                }
            ]
        },
    )
    settings = _settings(tmp_path, anthropic_key="")
    settings.openai_compatible_base_url = "http://127.0.0.1:8000/v1"
    settings.openai_compatible_model = "Qwen/Qwen2.5-32B-Instruct-AWQ"
    generator = TieredGenerator(
        settings=settings,
        http_client=SimpleNamespace(post=lambda *args, **kwargs: response),
        bulk_provider="openai-compatible",
    )

    records = generator.generate_complex(sample_seed_record, "bank_impersonation", num_variants=1)

    assert len(records) == 1
    assert records[0]["source"] == "synthetic_openai_compatible"


def test_generate_bulk_uses_openai_compatible_endpoint(sample_seed_record, tmp_path):
    request_capture: dict[str, object] = {}
    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {
            "choices": [
                {
                    "message": {
                        "content": json.dumps([
                            _make_record("task_scam", 1, source="synthetic_openai_compatible")
                        ])
                    }
                }
            ]
        },
    )

    def fake_post(url, *args, **kwargs):
        request_capture["url"] = url
        request_capture["headers"] = kwargs.get("headers")
        request_capture["json"] = kwargs.get("json")
        return response

    settings = _settings(tmp_path, anthropic_key="", gemini_key="", openrouter_key="", deepseek_key="")
    settings.openai_compatible_base_url = "http://127.0.0.1:8000/v1/"
    settings.openai_compatible_api_key = "colab-token"
    settings.openai_compatible_model = "Qwen/Qwen2.5-32B-Instruct-AWQ"
    generator = TieredGenerator(
        settings=settings,
        http_client=SimpleNamespace(post=fake_post),
        bulk_provider="openai-compatible",
    )

    records = generator.generate_bulk(sample_seed_record, "task_scam", count=1)

    assert len(records) == 1
    assert records[0]["source"] == "synthetic_openai_compatible"
    assert request_capture["url"] == "http://127.0.0.1:8000/v1/chat/completions"
    assert request_capture["headers"]["Authorization"] == "Bearer colab-token"
    assert request_capture["json"]["model"] == "Qwen/Qwen2.5-32B-Instruct-AWQ"


def test_generate_bulk_falls_back_to_openrouter_when_gemini_request_fails(sample_seed_record, tmp_path):
    request = httpx.Request("POST", "https://generativelanguage.googleapis.com")
    gemini_error = httpx.HTTPStatusError(
        "Gemini disabled",
        request=request,
        response=httpx.Response(403, request=request),
    )

    def fake_post(url, *args, **kwargs):
        if "generativelanguage.googleapis.com" in url:
            raise gemini_error
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                [_make_record("task_scam", 1, source="synthetic_openrouter")]
                            )
                        }
                    }
                ]
            },
        )

    generator = TieredGenerator(settings=_settings(tmp_path), http_client=SimpleNamespace(post=fake_post))

    records = generator.generate_bulk(sample_seed_record, "task_scam", count=1)

    assert records[0]["source"] == "synthetic_openrouter"


def test_generate_bulk_falls_back_to_claude_when_other_bulk_providers_fail(sample_seed_record, tmp_path):
    request = httpx.Request("POST", "https://provider.example")
    provider_error = httpx.HTTPStatusError(
        "Provider forbidden",
        request=request,
        response=httpx.Response(403, request=request),
    )

    def fake_post(*args, **kwargs):
        raise provider_error

    anthropic_client = SimpleNamespace(
        messages=SimpleNamespace(
            create=lambda **_: SimpleNamespace(
                content=[SimpleNamespace(text=json.dumps([_make_record("task_scam", 1)]))]
            )
        )
    )
    generator = TieredGenerator(
        settings=_settings(tmp_path),
        anthropic_client=anthropic_client,
        http_client=SimpleNamespace(post=fake_post),
    )

    records = generator.generate_bulk(sample_seed_record, "task_scam", count=1)

    assert records[0]["source"] == "synthetic_claude"


def test_generate_bulk_raises_value_error_without_bulk_key(sample_seed_record, tmp_path):
    generator = TieredGenerator(
        settings=_settings(tmp_path, anthropic_key="", gemini_key="", openrouter_key="")
    )

    try:
        generator.generate_bulk(sample_seed_record, "task_scam", count=1)
    except ValueError as error:
        assert "No bulk API key configured" in str(error)
    else:
        raise AssertionError("Expected generate_bulk to raise ValueError")


def test_class_balance(sample_seed_record, tmp_path):
    generator = TieredGenerator(settings=_settings(tmp_path))

    def fake_complex(seed, threat_class, num_variants=3):
        return [_make_record(threat_class, index, source="synthetic_claude") for index in range(num_variants)]

    def fake_bulk(seed, threat_class, count=10):
        return [_make_record(threat_class, index, source="synthetic_gemini") for index in range(count)]

    generator.generate_complex = fake_complex
    generator.generate_bulk = fake_bulk

    records = generator.generate_dataset([sample_seed_record], target_count=20)

    counts = {label: 0 for label in THREAT_CLASSES}
    for record in records:
        counts[record["label"]] += 1

    average = sum(counts.values()) / len(counts)
    for count in counts.values():
        assert abs(count - average) <= average * 0.2


def test_generate_dataset_batches_large_requests(sample_seed_record, tmp_path):
    generator = TieredGenerator(settings=_settings(tmp_path))
    complex_batch_sizes: list[int] = []
    bulk_batch_sizes: list[int] = []

    def fake_complex(seed, threat_class, num_variants=3):
        complex_batch_sizes.append(num_variants)
        return [_make_record(threat_class, index, source="synthetic_claude") for index in range(num_variants)]

    def fake_bulk(seed, threat_class, count=10):
        bulk_batch_sizes.append(count)
        return [_make_record(threat_class, index, source="synthetic_gemini") for index in range(count)]

    generator.generate_complex = fake_complex
    generator.generate_bulk = fake_bulk

    records = generator.generate_dataset([sample_seed_record], target_count=250)

    assert len(records) == 250
    assert max(complex_batch_sizes) <= 3
    assert max(bulk_batch_sizes) <= 5
    assert len(complex_batch_sizes) > len(THREAT_CLASSES)
    assert len(bulk_batch_sizes) > len(THREAT_CLASSES)


def test_generate_dataset_spreads_seed_ids_when_multiple_seeds_available(tmp_path):
    generator = TieredGenerator(settings=_settings(tmp_path))
    seeds = [
        SeedRecord(
            text=f"Seed text {index} with OTP and login wording {index}",
            source_url=f"https://seed-{index}.example",
            scrape_timestamp="2026-05-25T00:00:00Z",
            raw_label_hint=None,
        )
        for index in range(4)
    ]

    def fake_complex(seed, threat_class, num_variants=3):
        seed_id = generator._derive_seed_id(seed)
        return [_make_record(threat_class, index, source="synthetic_claude", seed_id=seed_id) for index in range(num_variants)]

    def fake_bulk(seed, threat_class, count=10):
        seed_id = generator._derive_seed_id(seed)
        return [_make_record(threat_class, index, source="synthetic_gemini", seed_id=seed_id) for index in range(count)]

    generator.generate_complex = fake_complex
    generator.generate_bulk = fake_bulk

    records = generator.generate_dataset(seeds, target_count=80)

    seed_ids_by_label: dict[str, set[str]] = {label: set() for label in THREAT_CLASSES}
    for record in records:
        seed_ids_by_label[record["label"]].add(record["seed_id"])

    assert all(len(seed_ids) > 1 for seed_ids in seed_ids_by_label.values())


def test_generate_dataset_writes_checkpoint_and_partial_output(sample_seed_record, tmp_path):
    generator = TieredGenerator(settings=_settings(tmp_path))
    checkpoint_dir = tmp_path / "synthetic"
    partial_output_path = tmp_path / "synthetic" / "generated-partial.jsonl"
    progress_messages: list[str] = []

    def fake_complex(seed, threat_class, num_variants=3):
        return [_make_record(threat_class, index, source="synthetic_claude") for index in range(num_variants)]

    def fake_bulk(seed, threat_class, count=10):
        return [_make_record(threat_class, index, source="synthetic_gemini") for index in range(count)]

    generator.generate_complex = fake_complex
    generator.generate_bulk = fake_bulk

    records = generator.generate_dataset(
        [sample_seed_record],
        target_count=20,
        checkpoint_path=checkpoint_dir,
        partial_output_path=partial_output_path,
        progress_callback=progress_messages.append,
    )

    checkpoint_files = sorted(checkpoint_dir.glob("checkpoint-*.jsonl"))
    assert len(records) == 20
    assert checkpoint_files, "Expected at least one numbered checkpoint file"
    latest_checkpoint = checkpoint_files[-1]
    assert len(latest_checkpoint.read_text(encoding="utf-8").splitlines()) == 8
    assert partial_output_path.exists()
    assert len(partial_output_path.read_text(encoding="utf-8").splitlines()) == 20
    assert progress_messages


def test_generate_dataset_resume_skips_completed_batches(sample_seed_record, tmp_path):
    generator = TieredGenerator(settings=_settings(tmp_path))
    checkpoint_dir = tmp_path / "synthetic"
    partial_output_path = tmp_path / "synthetic" / "generated-partial.jsonl"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    restored_record = _make_record("bank_impersonation", 99)
    checkpoint_entry = {
        "batch_key": "bank_impersonation:complex:0",
        "order": 0,
        "threat_class": "bank_impersonation",
        "batch_type": "complex",
        "batch_index": 0,
        "requested_count": 1,
        "returned_count": 1,
        "provider": "synthetic_claude",
        "timestamp": "2026-05-04T00:00:00Z",
        "records": [restored_record],
    }
    (checkpoint_dir / "checkpoint-001.jsonl").write_text(
        json.dumps(checkpoint_entry, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    call_log: list[tuple[str, str, int]] = []

    def fake_complex(seed, threat_class, num_variants=3):
        call_log.append(("complex", threat_class, num_variants))
        return [_make_record(threat_class, index, source="synthetic_claude") for index in range(num_variants)]

    def fake_bulk(seed, threat_class, count=10):
        call_log.append(("bulk", threat_class, count))
        return [_make_record(threat_class, index, source="synthetic_gemini") for index in range(count)]

    generator.generate_complex = fake_complex
    generator.generate_bulk = fake_bulk

    records = generator.generate_dataset(
        [sample_seed_record],
        target_count=20,
        checkpoint_path=checkpoint_dir,
        partial_output_path=partial_output_path,
        resume=True,
    )

    assert len(records) == 20
    assert restored_record in records
    assert ("complex", "bank_impersonation", 1) not in call_log
    assert partial_output_path.exists()


def test_save_generated_writes_jsonl(tmp_path):
    generator = TieredGenerator(settings=_settings(tmp_path))
    output_path = tmp_path / "synthetic" / "generated.jsonl"

    saved_path = generator.save_generated([_make_record("bank_impersonation", 1)], output_path=output_path)

    assert saved_path.exists()
    assert saved_path.read_text(encoding="utf-8").count("\n") == 1


def test_compare_models_includes_all_provider_slots(sample_seed_record, tmp_path):
    generator = TieredGenerator(settings=_settings(tmp_path), anthropic_client=object())
    generator._call_claude = lambda prompt: [_make_record("bank_impersonation", 1)]
    generator._call_gemini = lambda prompt: [_make_record("bank_impersonation", 1, source="synthetic_gemini")]
    generator._call_openrouter = lambda prompt: [_make_record("bank_impersonation", 1, source="synthetic_openrouter")]
    generator.deepseek_api_key = "deepseek"
    generator._call_deepseek = lambda prompt: [_make_record("bank_impersonation", 1, source="synthetic_deepseek")]

    comparison = generator.compare_models(sample_seed_record, "bank_impersonation")

    assert set(comparison) == {"claude", "gemini", "openrouter", "deepseek", "openai-compatible"}
    assert comparison["claude"]["notes"]
    assert comparison["gemini"]["notes"]
    assert comparison["openrouter"]["notes"]
    assert comparison["deepseek"]["notes"]
    assert comparison["openai-compatible"]["notes"]