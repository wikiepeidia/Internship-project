"""Wave 0 shared helper tests for local model-backed analyzers."""

import json

import pytest

from src.runtime.analyzers.local_model import (
    build_analysis_result,
    cue_span_is_grounded,
    extract_structured_payload,
    is_recommendation_safe,
)
from src.runtime.contracts import AnalysisRequest


def test_build_analysis_result_preserves_phase_four_fields():
    request = AnalysisRequest(
        text="VPBank yeu cau khach hang xac minh OTP de mo khoa tai khoan.",
        channel="sms",
    )
    payload = {
        "risk_tier": "high-risk",
        "threat_labels": ["bank_impersonation"],
        "suspicious_spans": ["OTP", "VPBank"],
        "xai_explanation": "Tin nhan gia danh ngan hang va yeu cau thong tin nhay cam.",
        "recommendations": [
            "Khong chia se OTP cho nguoi gui tin nhan.",
            "Mo ung dung ngan hang chinh thuc de tu kiem tra tai khoan.",
        ],
    }

    result = build_analysis_result(payload, request, backend_name="gguf")

    assert result.risk_tier == "high-risk"
    assert result.threat_labels == ["bank_impersonation"]
    assert result.recommendations == [
        "Khong chia se OTP cho nguoi gui tin nhan.",
        "Mo ung dung ngan hang chinh thuc de tu kiem tra tai khoan.",
    ]
    assert [cue.span for cue in result.top_cues] == ["OTP", "VPBank"]
    assert result.normalized_text == request.text


def test_build_analysis_result_caps_overlong_model_recommendations():
    request = AnalysisRequest(
        text="VPBank yeu cau khach hang xac minh OTP de mo khoa tai khoan.",
        channel="sms",
    )
    payload = {
        "risk_tier": "high-risk",
        "threat_labels": ["bank_impersonation"],
        "suspicious_spans": ["OTP", "VPBank"],
        "xai_explanation": "Tin nhan gia danh ngan hang va yeu cau thong tin nhay cam.",
        "recommendations": [
            "Khong chia se OTP cho nguoi gui tin nhan.",
            "Khong bam vao lien ket trong tin nhan.",
            "Xac minh qua ung dung hoac tong dai chinh thuc.",
            "Luu lai tin nhan de bao cao neu can.",
        ],
    }

    result = build_analysis_result(payload, request, backend_name="gguf")

    assert result.recommendations == [
        "Khong chia se OTP cho nguoi gui tin nhan.",
        "Khong bam vao lien ket trong tin nhan.",
        "Xac minh qua ung dung hoac tong dai chinh thuc.",
    ]


def test_build_analysis_result_accepts_evidence_spans_alias_from_gguf_payload():
    request = AnalysisRequest(
        text='! Db]qo-rg.com/BK+Zmoz.M G 8D\'A\'Y U.u"Da\'j~C\'OD',
        channel="sms",
    )
    payload = {
        "risk_tier": "high-risk",
        "threat_labels": ["task_scam", "bank_impersonation"],
        "evidence_spans": [
            "! Db]qo-rg.com/BK+Zmoz.M",
            "8D'A'Y U.u\"Da'j~C'OD",
        ],
        "recommendations": [
            "Khong truy cap bat ky lien ket nao trong tin nhan nay.",
            "Khong cung cap thong tin ca nhan hoac OTP cho bat ky ai.",
            "Goi truc tiep den ngan hang neu nghi ngo.",
            "Xac minh lai thong tin qua kenh chinh thuc.",
        ],
    }

    result = build_analysis_result(payload, request, backend_name="gguf")

    assert result.risk_tier == "high-risk"
    assert result.threat_labels == ["task_scam", "bank_impersonation"]
    assert [cue.span for cue in result.top_cues] == [
        "! Db]qo-rg.com/BK+Zmoz.M",
        "8D'A'Y U.u\"Da'j~C'OD",
    ]
    assert len(result.recommendations) == 3


def test_local_model_rejects_out_of_scope_labels():
    request = AnalysisRequest(text="Nhan thuong qua app moi hom nay.", channel="sms")
    payload = {
        "risk_tier": "suspicious",
        "threat_labels": ["lottery_scam"],
        "suspicious_spans": ["thuong"],
        "xai_explanation": "Nhan sai nhan de du nguoi dung thao tac.",
    }

    with pytest.raises(ValueError, match="Unsupported threat_labels"):
        build_analysis_result(payload, request, backend_name="accelerated")


def test_build_analysis_result_maps_phase_four_payload_into_public_contract():
    request = AnalysisRequest(
        text="VPBank yeu cau xac minh OTP tai https://vpbank-safe.example ngay hom nay.",
        channel="sms",
    )
    payload = extract_structured_payload(
        json.dumps(
            {
                "risk_tier": "high-risk",
                "threat_labels": ["bank_impersonation"],
                "decision_summary": "Thong diep gia danh ngan hang va yeu cau thong tin nhay cam.",
                "evidence": [
                    {
                        "span": "OTP",
                        "reason": "Tin nhan yeu cau ma xac thuc nhay cam.",
                        "cue_type": "otp_request",
                        "supports_labels": ["bank_impersonation"],
                        "severity": "high",
                    },
                    {
                        "span": "https://vpbank-safe.example",
                        "reason": "Lien ket la co the dan toi trang dang nhap gia danh.",
                        "cue_type": "url",
                        "supports_labels": ["bank_impersonation"],
                        "severity": "high",
                    },
                ],
                "recommendations": [
                    {"text": "Khong bam vao lien ket trong tin nhan.", "priority": "high", "offline_safe": True},
                    {
                        "text": "Xac minh qua ung dung hoac tong dai chinh thuc cua ngan hang.",
                        "priority": "high",
                        "offline_safe": True,
                    },
                ],
            }
        )
    )

    result = build_analysis_result(payload, request, backend_name="gguf")

    assert result.risk_tier == "high-risk"
    assert result.summary == "Thong diep gia danh ngan hang va yeu cau thong tin nhay cam."
    assert result.threat_labels == ["bank_impersonation"]
    assert result.recommendations == [
        "Khong bam vao lien ket trong tin nhan.",
        "Xac minh qua ung dung hoac tong dai chinh thuc cua ngan hang.",
    ]
    assert [cue.cue_type for cue in result.top_cues] == ["otp_request", "url"]


def test_extract_structured_payload_prefers_top_level_analysis_object_over_nested_evidence():
        raw_output = """https://vpbank-safe.example.com/verify

```json
{
    \"risk_tier\": \"high-risk\",
    \"threat_labels\": [\"bank_impersonation\"],
    \"decision_summary\": \"Tin nhan gia mao ngan hang va dan nguoi dung toi lien ket khong chinh thuc.\",
    \"evidence\": [
        {
            \"span\": \"OTP\",
            \"reason\": \"Tin nhan yeu cau ma OTP.\",
            \"cue_type\": \"otp_request\",
            \"supports_labels\": [\"bank_impersonation\"],
            \"severity\": \"high\"
        }
    ],
    \"recommendations\": [
        {\"text\": \"Khong bam vao lien ket trong tin nhan.\", \"priority\": \"high\", \"offline_safe\": true}
    ]
}
```"""

        payload = extract_structured_payload(raw_output)

        assert payload["risk_tier"] == "high-risk"
        assert payload["threat_labels"] == ["bank_impersonation"]
        assert payload["evidence"][0]["span"] == "OTP"


@pytest.mark.parametrize(
    ("raw_output", "error_message"),
    [
        (
            json.dumps(
                {
                    "risk_tier": "critical",
                    "threat_labels": ["bank_impersonation"],
                    "decision_summary": "Khong hop le nhung van co du noi dung.",
                    "evidence": [
                        {
                            "span": "OTP",
                            "reason": "Tin nhan yeu cau ma OTP.",
                            "cue_type": "otp_request",
                            "supports_labels": ["bank_impersonation"],
                            "severity": "high",
                        }
                    ],
                    "recommendations": [{"text": "Khong bam vao lien ket."}],
                }
            ),
            "Unsupported risk_tier",
        ),
        (
            json.dumps(
                {
                    "risk_tier": "suspicious",
                    "threat_labels": ["lottery_scam"],
                    "decision_summary": "Nhan sai nhan de du nguoi dung thao tac.",
                    "evidence": [
                        {
                            "span": "OTP",
                            "reason": "Tin nhan yeu cau ma OTP.",
                            "cue_type": "otp_request",
                            "supports_labels": ["lottery_scam"],
                            "severity": "high",
                        }
                    ],
                    "recommendations": [{"text": "Khong bam vao lien ket."}],
                }
            ),
            "Unsupported threat_labels",
        ),
    ],
)
def test_extract_structured_payload_rejects_unsupported_risk_tier_or_label(raw_output, error_message):
    request = AnalysisRequest(
        text="VPBank yeu cau xac minh OTP tai https://vpbank-safe.example ngay hom nay.",
        channel="sms",
    )
    payload = extract_structured_payload(raw_output)

    with pytest.raises(ValueError, match=error_message):
        build_analysis_result(payload, request, backend_name="gguf")


def test_exact_grounding_rejects_evidence_not_found_in_normalized_text():
    request = AnalysisRequest(text="VPBank thong bao tai khoan co bien dong.", channel="sms")
    payload = {
        "risk_tier": "suspicious",
        "threat_labels": ["bank_impersonation"],
        "decision_summary": "Tin nhan co dau hieu gia danh ngan hang.",
        "evidence": [
            {
                "span": "OTP",
                "reason": "Tin nhan yeu cau ma OTP.",
                "cue_type": "otp_request",
                "supports_labels": ["bank_impersonation"],
                "severity": "high",
            }
        ],
        "recommendations": [{"text": "Khong bam vao lien ket trong tin nhan."}],
    }

    with pytest.raises(ValueError, match="Evidence span was not found"):
        build_analysis_result(payload, request, backend_name="gguf")


def test_build_analysis_result_skips_ungrounded_evidence_when_grounded_items_remain():
    request = AnalysisRequest(
        text="Ngân hàng thông báo tài khoản của bạn bị khóa. Hãy bấm vào liên kết này để xác minh ngay.",
        channel="sms",
    )
    payload = {
        "risk_tier": "high-risk",
        "threat_labels": ["bank_impersonation"],
        "decision_summary": "Tin nhan gia mao ngan hang va dan nguoi dung toi lien ket khong chinh thuc.",
        "evidence": [
            {
                "span": "Ngân hàng thông báo tài khoản của bạn bị khóa",
                "reason": "Dung ngon ngu gay lo lang de kich thich hanh dong nhanh chong.",
                "cue_type": "spoofed_brand",
                "supports_labels": ["bank_impersonation"],
                "severity": "high",
            },
            {
                "span": "https://vpbank-safe.example.com/verify",
                "reason": "Dia chi URL khong chinh thuc va co dau hieu bi gia mao.",
                "cue_type": "url",
                "supports_labels": ["bank_impersonation"],
                "severity": "high",
            },
        ],
        "recommendations": [
            {"text": "Khong bam vao lien ket trong tin nhan.", "priority": "high", "offline_safe": True}
        ],
    }

    result = build_analysis_result(payload, request, backend_name="gguf")

    assert result.risk_tier == "high-risk"
    assert result.threat_labels == ["bank_impersonation"]
    assert [cue.span for cue in result.top_cues] == ["Ngân hàng thông báo tài khoản của bạn bị khóa"]


def test_build_analysis_result_normalizes_unknown_model_evidence_cue_types():
    request = AnalysisRequest(
        text="Tai khoan cua ban can xac minh ngay de tranh bi tam khoa.",
        channel="sms",
    )
    payload = {
        "risk_tier": "suspicious",
        "threat_labels": ["bank_impersonation"],
        "decision_summary": "Tin nhan tao ap luc thoi gian de buoc nguoi dung hanh dong.",
        "evidence": [
            {
                "span": "xac minh ngay",
                "reason": "Ngon ngu gay ap luc.",
                "cue_type": "suspicious_tone",
                "supports_labels": ["bank_impersonation"],
                "severity": "medium",
            }
        ],
        "recommendations": [{"text": "Khong bam vao lien ket trong tin nhan."}],
    }

    result = build_analysis_result(payload, request, backend_name="gguf")

    assert result.risk_tier == "suspicious"
    assert result.threat_labels == ["bank_impersonation"]
    assert [cue.cue_type for cue in result.top_cues] == ["urgency"]


def test_safety_floor_blocks_harmful_benign_downgrade():
    request = AnalysisRequest(
        text=(
            "Techcombank canh bao tai khoan se bi khoa trong 24h. "
            "Vui long xac minh OTP tai https://techcombank-safe.example ngay."
        ),
        channel="sms",
    )
    payload = {
        "risk_tier": "benign",
        "threat_labels": ["benign"],
        "decision_summary": "Model du doan day la thong bao thong thuong.",
        "suspicious_spans": ["xac minh"],
        "recommendations": [{"text": "Khong bam vao lien ket trong tin nhan."}],
    }

    result = build_analysis_result(payload, request, backend_name="accelerated")

    assert result.risk_tier == "high-risk"
    assert result.threat_labels == ["bank_impersonation"]
    assert any(cue.cue_type in {"otp_request", "url", "spoofed_brand"} for cue in result.top_cues)


def test_safety_floor_keeps_benign_when_helper_cues_are_too_generic_to_map_in_scope():
    request = AnalysisRequest(
        text="Chao ban, tai khoan Internet Banking cua ban da duoc kich hoat thanh cong. Ban co the dang nhap ngay de su dung dich vu.",
        channel="unknown",
    )
    payload = {
        "risk_tier": "benign",
        "threat_labels": ["benign"],
        "decision_summary": "Model du doan day la thong bao thong thuong.",
        "suspicious_spans": [],
        "recommendations": [{"text": "Khong can thao tac them neu ban da kich hoat thanh cong."}],
    }

    result = build_analysis_result(payload, request, backend_name="gguf")

    assert result.risk_tier == "benign"
    assert result.threat_labels == ["benign"]


def test_legitimate_bank_otp_notice_overrides_model_suspicion():
    request = AnalysisRequest(
        text=(
            "VPBank Smart OTP: Mã xác thực của bạn là 847291. "
            "Mã này có hiệu lực trong 90 giây để xác nhận đăng nhập Internet Banking. "
            "Tuyệt đối KHÔNG chia sẻ mã này với bất kỳ ai, kể cả nhân viên ngân hàng."
        ),
        channel="sms",
    )
    payload = {
        "risk_tier": "suspicious",
        "threat_labels": ["bank_impersonation"],
        "decision_summary": "Model treated the OTP notice as suspicious.",
        "suspicious_spans": ["Smart OTP", "Internet Banking"],
        "recommendations": [{"text": "Neu van thay bat thuong, hay xac minh qua ung dung chinh thuc."}],
    }

    result = build_analysis_result(payload, request, backend_name="gguf")

    assert result.risk_tier == "benign"
    assert result.threat_labels == ["benign"]
    assert result.top_cues == []


def test_ascii_legitimate_bank_otp_notice_overrides_model_suspicion():
    request = AnalysisRequest(
        text=(
            "Thông báo từ Techcombank :Ma OTP la 74449637. de xac nhan giao dich "
            "(TRU TIEN) tu The cua quy khach. Vui long giu bao mat va khong chia se "
            "OTP cho bat cu ai. LH Techcombank: 1800588822"
        ),
        channel="sms",
    )
    payload = {
        "risk_tier": "suspicious",
        "threat_labels": ["bank_impersonation"],
        "decision_summary": "Model treated the OTP notice as suspicious.",
        "suspicious_spans": ["Ma OTP la 74449637"],
        "recommendations": [{"text": "Kiem tra giao dich trong ung dung ngan hang chinh thuc."}],
    }

    result = build_analysis_result(payload, request, backend_name="gguf")

    assert result.risk_tier == "benign"
    assert result.threat_labels == ["benign"]


def test_legitimate_otp_override_does_not_hide_link_based_bank_scam():
    request = AnalysisRequest(
        text=(
            "【VIETCOMBANK】 Tai khoan cua ban vua bi truy cap tu thiet bi la luc 03:47 SA. "
            "Neu ko phai ban, bam vao link de khoa ngay: "
            "http://vcb-secure-alert.net/lock?id=9182736 hoac goi 1800.9999 "
            "(mien phi). OTP se het han sau 5 phut!"
        ),
        channel="sms",
    )
    payload = {
        "risk_tier": "benign",
        "threat_labels": ["benign"],
        "decision_summary": "Model attempted a harmful benign downgrade.",
        "suspicious_spans": [],
        "recommendations": [{"text": "Khong bam vao lien ket trong tin nhan."}],
    }

    result = build_analysis_result(payload, request, backend_name="gguf")

    assert result.risk_tier == "high-risk"
    assert result.threat_labels == ["bank_impersonation"]
    assert any(cue.cue_type == "url" for cue in result.top_cues)


def test_recommendation_sanitizer_blocks_unsafe_actions():
    request = AnalysisRequest(
        text="VPBank yeu cau OTP tai https://vpbank-safe.example de mo khoa tai khoan.",
        channel="sms",
    )
    payload = {
        "risk_tier": "high-risk",
        "threat_labels": ["bank_impersonation"],
        "decision_summary": "Tin nhan gia danh ngan hang va yeu cau thong tin nhay cam.",
        "suspicious_spans": ["OTP", "https://vpbank-safe.example"],
        "recommendations": [
            {"text": "Hay bam vao lien ket de xac minh OTP ngay."},
            {"text": "Tra loi nguoi gui de xac nhan tai khoan."},
        ],
    }

    result = build_analysis_result(payload, request, backend_name="gguf")

    assert result.recommendations == [
        "Khong bam vao lien ket hoac cai ung dung tu tin nhan nay.",
        "Khong chia se OTP, mat khau, CCCD, hoac CVV.",
        "Xac minh qua ung dung, website, hoac tong dai chinh thuc.",
    ]


def test_local_model_exposes_grounding_and_recommendation_safety_helpers():
    assert cue_span_is_grounded(
        "VPBank yeu cau nhap OTP de xac minh giao dich.",
        "OTP",
    )
    assert not cue_span_is_grounded(
        "VPBank yeu cau nhap OTP de xac minh giao dich.",
        "CVV",
    )
    assert is_recommendation_safe("Khong bam vao lien ket trong tin nhan.")
    assert not is_recommendation_safe("Hay bam vao lien ket de xac minh ngay.")
