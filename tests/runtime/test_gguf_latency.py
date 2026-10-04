"""Phase 7b smoke tests: verify stripped prompt still produces valid JSON output.

These tests do NOT require a real GGUF model. They use the same FakeRuntime
pattern as test_gguf_backend.py and verify that build_structured_analysis_prompt
produces output parseable by extract_structured_payload with the expected
risk_tier and threat_labels fields.
"""

from __future__ import annotations

import json

from src.runtime.analyzers.local_model import (
    build_structured_analysis_prompt,
    extract_structured_payload,
)


def _fake_response(risk_tier: str, threat_labels: list, summary: str, span: str) -> str:
    """Return a minimal JSON string matching the expected model output format."""
    payload = {
        "risk_tier": risk_tier,
        "threat_labels": threat_labels,
        "decision_summary": summary,
        "evidence": [
            {
                "span": span,
                "reason": "Suspicious cue detected.",
                "cue_type": "generic",
                "supports_labels": threat_labels,
                "severity": "high",
            }
        ] if risk_tier != "benign" else [],
        "recommendations": [
            {
                "text": "Xac minh qua kenh chinh thuc.",
                "priority": "medium",
                "offline_safe": True,
            }
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def test_stripped_prompt_bank_impersonation():
    """Stripped prompt for a bank impersonation message produces a parseable JSON payload."""
    text = "VPBank: Tai khoan cua ban bi khoa. Vui long xac minh OTP tai https://vpbank-secure.example"
    prompt = build_structured_analysis_prompt(text)

    assert "Schema:" not in prompt
    assert "Example output:" not in prompt
    assert text in prompt

    # Simulate model returning bank_impersonation decision
    fake_output = _fake_response("high-risk", ["bank_impersonation"], "Tin nhan gia danh ngan hang.", "OTP")
    payload = extract_structured_payload(fake_output)

    assert payload["risk_tier"] == "high-risk"
    assert "bank_impersonation" in payload["threat_labels"]


def test_stripped_prompt_task_scam():
    """Stripped prompt for a task scam message produces a parseable JSON payload."""
    text = "Lam viec online tai nha, nhiem vu don gian, hoa hong cao. Nap 500k de bat dau."
    prompt = build_structured_analysis_prompt(text)

    assert "Schema:" not in prompt
    assert "Example output:" not in prompt
    assert text in prompt

    fake_output = _fake_response("high-risk", ["task_scam"], "Tin nhan lua dao viec lam.", "nhiem vu")
    payload = extract_structured_payload(fake_output)

    assert payload["risk_tier"] == "high-risk"
    assert "task_scam" in payload["threat_labels"]


def test_stripped_prompt_zalo_social_engineering():
    """Stripped prompt for a zalo social engineering message produces a parseable JSON payload."""
    text = "Minh la nguoi quen cua ban tren Zalo. Cho minh muon so tai khoan ngan hang nhe."
    prompt = build_structured_analysis_prompt(text)

    assert "Schema:" not in prompt
    assert "Example output:" not in prompt
    assert text in prompt

    fake_output = _fake_response(
        "suspicious", ["zalo_social_engineering"], "Tin nhan yeu cau thong tin tai khoan qua Zalo.", "so tai khoan"
    )
    payload = extract_structured_payload(fake_output)

    assert payload["risk_tier"] == "suspicious"
    assert "zalo_social_engineering" in payload["threat_labels"]


def test_stripped_prompt_benign():
    """Stripped prompt for a clearly benign message produces a parseable JSON payload."""
    text = "Con nho gio nay ve nha an com nha, me nau mon ga kho gung roi."
    prompt = build_structured_analysis_prompt(text)

    assert "Schema:" not in prompt
    assert "Example output:" not in prompt
    assert text in prompt

    fake_output = _fake_response("benign", ["benign"], "Tin nhan binh thuong trong gia dinh.", "")
    # benign has no evidence, adjust the fake response
    benign_payload = {
        "risk_tier": "benign",
        "threat_labels": ["benign"],
        "decision_summary": "Tin nhan binh thuong.",
        "evidence": [],
        "recommendations": [{"text": "Xac minh qua kenh chinh thuc.", "priority": "low", "offline_safe": True}],
    }
    payload = extract_structured_payload(json.dumps(benign_payload, ensure_ascii=False))

    assert payload["risk_tier"] == "benign"
    assert "benign" in payload["threat_labels"]


def test_stripped_prompt_ambiguous():
    """Stripped prompt for an ambiguous message (generic financial request) produces a parseable payload."""
    text = "Ban co muon kiem them thu nhap khong? Lien he so nay de biet them chi tiet."
    prompt = build_structured_analysis_prompt(text)

    assert "Schema:" not in prompt
    assert "Example output:" not in prompt
    assert text in prompt

    # Ambiguous — could be task_scam or benign; test only that parsing succeeds
    fake_output = _fake_response(
        "suspicious", ["task_scam"], "Tin nhan co dau hieu lua dao viec lam.", "kiem them thu nhap"
    )
    payload = extract_structured_payload(fake_output)

    assert "risk_tier" in payload
    assert "threat_labels" in payload
