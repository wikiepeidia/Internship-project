"""Phase 4 renderer expectations for terminal output."""

from src.runtime.contracts import AnalysisResult, SuspiciousCue
from src.runtime.render import render_analysis_result


def test_render_analysis_result_maps_internal_labels_to_user_facing_wording():
    result = AnalysisResult(
        risk_tier="high-risk",
        summary="Tin nhan co dau hieu lua dao ro rang.",
        threat_labels=["bank_impersonation"],
        top_cues=[
            SuspiciousCue(span="OTP", reason="Yeu cau ma xac thuc nhay cam"),
            SuspiciousCue(span="https://vpbank-safe.example", reason="Dan nguoi dung toi lien ket la"),
        ],
        recommendations=[
            "Khong bam vao lien ket trong tin nhan.",
            "Xac minh bang ung dung hoac tong dai chinh thuc.",
        ],
        backend_name="gguf",
    )

    rendered = render_analysis_result(result)

    assert "Risk tier: High risk" in rendered
    assert "Threat labels: Bank impersonation" in rendered
    assert "Grounded cues:" in rendered
    assert '- "OTP" - Yeu cau ma xac thuc nhay cam' in rendered
    assert "Next steps:" in rendered
    assert "- Khong bam vao lien ket trong tin nhan." in rendered


def test_render_analysis_result_preserves_legacy_summary_only_output():
    result = AnalysisResult(
        risk_tier="benign",
        summary="Provisional benign result.",
        backend_name="heuristic",
    )

    assert render_analysis_result(result) == "Provisional benign result."