"""Shared helpers for Phase 4 local model-backed runtime analyzers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Literal, cast, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.artifacts import resolve_downloaded_model
from src.runtime.analyzers.rules import CueRule, build_default_rules
from src.runtime.contracts import AnalysisRequest, AnalysisResult, SuspiciousCue, ThreatLabel


CueType = Literal[
    "url",
    "otp_request",
    "spoofed_brand",
    "urgency",
    "credential_request",
    "payment_request",
    "contact_takeover",
    "job_offer",
    "generic",
]
Priority = Literal["low", "medium", "high"]

SUPPORTED_THREAT_LABELS = get_args(ThreatLabel)
SUPPORTED_CUE_TYPES = set(get_args(CueType))
DEFAULT_RISKY_RECOMMENDATIONS = (
    "Khong bam vao lien ket va khong cai ung dung tu tin nhan nay.",
    "Khong chia se OTP, mat khau, CCCD, hoac CVV.",
    "Xac minh qua ung dung, website, hoac tong dai chinh thuc.",
)
DEFAULT_BENIGN_RECOMMENDATION = (
    "Không cần thao tác thêm nếu bạn nhận ra nội dung này. "
    "Nếu vẫn thấy bất thường, hãy tự kiểm tra qua ứng dụng, website hoặc tổng đài chính thức."
)
UNSAFE_RECOMMENDATION_MARKERS = (
    "bam vao",
    "bấm vào",
    "click",
    "tra loi",
    "trả lời",
    "reply",
    "chia se otp",
    "chia sẻ otp",
    "cung cap otp",
    "cung cấp otp",
    "cung cap cccd",
    "cung cấp cccd",
    "cung cap cvv",
    "cung cấp cvv",
    "chuyen tien",
    "chuyển tiền",
    "transfer money",
    "cai ung dung",
    "cài ứng dụng",
    "install app",
    "goi theo so trong tin nhan",
    "gọi theo số trong tin nhắn",
    "lien he so trong tin nhan",
    "liên hệ số trong tin nhắn",
)
BANK_BRAND_MARKERS = ("vpbank", "vietcombank", "techcombank", "mb bank", "agribank")
TASK_SCAM_MARKERS = ("nhiem vu", "nạp tiền", "nap tien", "hoa hong", "cong tac vien")
LEGITIMATE_OTP_NOTICE_MARKERS = (
    "otp",
    "smart otp",
    "ma xac thuc",
    "mã xác thực",
)
LEGITIMATE_OTP_CONTEXT_MARKERS = (
    "khong chia se",
    "không chia sẻ",
    "giu bao mat",
    "giữ bảo mật",
    "xac nhan giao dich",
    "xác nhận giao dịch",
    "xac nhan dang nhap",
    "xác nhận đăng nhập",
    "hieu luc",
    "hiệu lực",
)
LEGITIMATE_OTP_NONDISCLOSURE_MARKERS = (
    "khong chia se",
    "không chia sẻ",
    "giu bao mat",
    "giữ bảo mật",
)
UNSAFE_OTP_ACTION_MARKERS = (
    "http://",
    "https://",
    "bit.ly",
    "tinyurl",
    "bam vao",
    "bấm vào",
    "click",
    "link",
    "mo khoa",
    "mở khóa",
    "khoa ngay",
    "khóa ngay",
    "bi khoa",
    "bị khóa",
    "truy cap tu thiet bi la",
    "truy cập từ thiết bị lạ",
    "neu ko phai ban",
    "nếu không phải bạn",
    "chuyen tien",
    "chuyển tiền",
    "transfer money",
    "nap tien",
    "nạp tiền",
    "thanh toan",
    "thanh toán",
    "dat coc",
    "đặt cọc",
    "cai ung dung",
    "cài ứng dụng",
    "install app",
    "cung cap otp",
    "cung cấp otp",
    "mat khau",
    "mật khẩu",
    "cvv",
    "cccd",
    "goi theo so",
    "gọi theo số",
    "lien he so",
    "liên hệ số",
    "khẩn cấp",
    "khan cap",
    "gap",
    "gấp",
)


@dataclass(frozen=True)
class HelperCue:
    span: str
    reason: str
    cue_type: CueType
    severity: Priority
    start: int
    suggested_label: ThreatLabel | None = None
    tier_override: str | None = None


class EvidenceReason(BaseModel):
    model_config = ConfigDict(extra="forbid")

    span: str = Field(min_length=1, max_length=160)
    reason: str = Field(min_length=1, max_length=240)
    cue_type: CueType
    supports_labels: list[ThreatLabel] = Field(min_length=1, max_length=2)
    severity: Priority = "medium"

    @field_validator("span", "reason")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=180)
    priority: Priority = "medium"
    offline_safe: bool = True

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("text must not be blank")
        return value


class ThreatDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_tier: Literal["benign", "suspicious", "high-risk"]
    threat_labels: list[ThreatLabel] = Field(min_length=1, max_length=2)
    decision_summary: str = Field(min_length=12, max_length=280)
    evidence: list[EvidenceReason] = Field(default_factory=list, max_length=5)
    recommendations: list[Recommendation] = Field(min_length=1, max_length=3)
    provisional: bool = True

    @field_validator("decision_summary")
    @classmethod
    def reject_blank_summary(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("decision_summary must not be blank")
        return value

    @model_validator(mode="after")
    def validate_consistency(self) -> "ThreatDecision":
        if "benign" in self.threat_labels and len(self.threat_labels) > 1:
            raise ValueError("benign cannot be combined with threat labels")
        if self.risk_tier == "benign" and self.threat_labels != ["benign"]:
            raise ValueError("benign tier must map to benign only")
        if self.risk_tier != "benign" and "benign" in self.threat_labels:
            raise ValueError("non-benign tier cannot include benign")
        if self.risk_tier == "high-risk" and not self.evidence:
            raise ValueError("high-risk decisions require evidence")
        return self


STRUCTURED_ANALYSIS_SCHEMA = {
    "risk_tier": "benign | suspicious | high-risk",
    "threat_labels": list(SUPPORTED_THREAT_LABELS),
    "decision_summary": "short Vietnamese explanation grounded in the message text",
    "evidence": [
        {
            "span": "exact suspicious substring from the message",
            "reason": "why that cue matters",
            "cue_type": "otp_request | url | spoofed_brand | urgency | credential_request | payment_request | contact_takeover | job_offer | generic",
            "supports_labels": ["bank_impersonation"],
            "severity": "low | medium | high",
        }
    ],
    "recommendations": [
        {
            "text": "short safe next step that does not tell the user to click, reply, or share secrets",
            "priority": "low | medium | high",
            "offline_safe": True,
        }
    ],
}

STRUCTURED_ANALYSIS_EXAMPLE = {
    "risk_tier": "suspicious",
    "threat_labels": ["bank_impersonation"],
    "decision_summary": "Thong diep yeu cau OTP va dan nguoi dung toi lien ket khong chinh thong.",
    "evidence": [
        {
            "span": "ma OTP",
            "reason": "Tin nhan yeu cau ma xac thuc nhay cam.",
            "cue_type": "otp_request",
            "supports_labels": ["bank_impersonation"],
            "severity": "high",
        },
        {
            "span": "vpbank-safe.example",
            "reason": "Lien ket la dan nguoi dung toi diem dang nhap gia danh.",
            "cue_type": "url",
            "supports_labels": ["bank_impersonation"],
            "severity": "high",
        },
    ],
    "recommendations": [
        {
            "text": "Khong bam vao lien ket trong tin nhan.",
            "priority": "high",
            "offline_safe": True,
        },
        {
            "text": "Xac minh bang ung dung hoac tong dai chinh thuc cua ngan hang.",
            "priority": "high",
            "offline_safe": True,
        },
    ],
}

STRUCTURED_PAYLOAD_PRIMARY_KEYS = {
    "risk_tier",
    "threat_labels",
    "label",
    "decision_summary",
    "summary",
    "xai_explanation",
    "evidence",
    "evidence_spans",
    "suspicious_spans",
    "recommendations",
}
STRUCTURED_PAYLOAD_NESTED_KEYS = {
    "span",
    "reason",
    "cue_type",
    "supports_labels",
    "severity",
}


def build_structured_analysis_prompt(text: str) -> str:
    return "\n".join(
        [
            "You are a local Vietnamese phishing detector.",
            "Analyze the message text and return JSON only.",
            "Choose risk_tier from: benign, suspicious, high-risk.",
            "Choose threat_labels only from: bank_impersonation, zalo_social_engineering, task_scam, benign.",
            "Use exact evidence spans from the message whenever possible.",
            "Recommendations must be safe next steps and must not tell the user to click, reply, share OTP, share CCCD/CVV, install an app, or transfer money.",
            f"Message text: {text}",
        ]
    )


def _score_structured_payload_candidate(payload: dict[str, Any]) -> tuple[int, int]:
    keys = set(payload)
    primary_key_count = len(keys & STRUCTURED_PAYLOAD_PRIMARY_KEYS)
    nested_key_count = len(keys & STRUCTURED_PAYLOAD_NESTED_KEYS)

    score = primary_key_count * 10
    if "risk_tier" in payload:
        score += 8
    if "threat_labels" in payload or "label" in payload:
        score += 8
    if "decision_summary" in payload or "summary" in payload or "xai_explanation" in payload:
        score += 6
    if "evidence" in payload or "suspicious_spans" in payload:
        score += 6
    if "recommendations" in payload:
        score += 6
    if primary_key_count == 0 and nested_key_count:
        score -= nested_key_count * 3

    return score, len(payload)


def extract_structured_payload(raw_output: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    best_payload: dict[str, Any] | None = None
    best_score: tuple[int, int] | None = None

    for index, character in enumerate(raw_output):
        if character != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(raw_output[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            payload_score = _score_structured_payload_candidate(payload)
            if best_score is None or payload_score > best_score:
                best_payload = payload
                best_score = payload_score

    if best_payload is not None:
        return best_payload
    raise ValueError("Model response did not contain a valid JSON object")


def _normalize_text_list(raw_value: Any, *, field_name: str) -> list[str]:
    if raw_value is None:
        return []
    if isinstance(raw_value, str):
        values = [raw_value]
    elif isinstance(raw_value, list):
        values = raw_value
    else:
        raise ValueError(f"{field_name} must be a string or list of strings")

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_item in values:
        text = str(raw_item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def normalize_threat_labels(raw_labels: Any) -> list[ThreatLabel]:
    labels = _normalize_text_list(raw_labels, field_name="threat_labels")
    unsupported = [label for label in labels if label not in SUPPORTED_THREAT_LABELS]
    if unsupported:
        raise ValueError(f"Unsupported threat_labels from model output: {unsupported!r}")
    return cast(list[ThreatLabel], labels)


def normalize_recommendations(raw_recommendations: Any) -> list[str]:
    return _normalize_text_list(raw_recommendations, field_name="recommendations")


def _map_rule_to_helper_cue(rule: CueRule, span: str, start: int, text: str, channel: str) -> HelperCue:
    shadow_text = text.casefold()
    suggested_label: ThreatLabel | None = None
    cue_type: CueType = "generic"
    severity: Priority = "medium"

    if rule.cue_type == "credential_request":
        cue_type = "otp_request" if "otp" in span.casefold() else "credential_request"
        severity = "high"
    elif rule.cue_type == "link_prompt":
        cue_type = "url" if "://" in span or "bit.ly" in span.casefold() or "tinyurl" in span.casefold() else "generic"
    elif rule.cue_type == "urgency":
        cue_type = "urgency"
    elif rule.cue_type == "bank_impersonation":
        cue_type = "spoofed_brand"
        suggested_label = "bank_impersonation"
        severity = "high"
    elif rule.cue_type == "task_scam":
        cue_type = "job_offer"
        suggested_label = "task_scam"
        severity = "high"

    if suggested_label is None and (channel == "zalo" or "zalo" in shadow_text):
        suggested_label = "zalo_social_engineering"

    return HelperCue(
        span=span,
        reason=rule.reason,
        cue_type=cue_type,
        severity=severity,
        start=start,
        suggested_label=suggested_label,
        tier_override=rule.tier_override,
    )


def _find_helper_cues(text: str, channel: str) -> list[HelperCue]:
    helper_cues: list[HelperCue] = []
    shadow_text = text.casefold()
    seen: set[tuple[str, str]] = set()

    for rule in build_default_rules():
        for match in rule.pattern.finditer(shadow_text):
            span = text[match.start() : match.end()]
            if not span.strip():
                continue

            dedupe_key = (span, rule.reason)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            helper_cues.append(_map_rule_to_helper_cue(rule, span, match.start(), text, channel))

    helper_cues.sort(key=lambda cue: (cue.start, cue.span))
    return helper_cues


def _infer_threat_labels(
    raw_labels: Any,
    *,
    text: str,
    channel: str,
    helper_cues: list[HelperCue],
    risk_tier: str,
) -> list[ThreatLabel]:
    labels = normalize_threat_labels(raw_labels)
    inferred: list[ThreatLabel] = list(labels)
    helper_cue_types = {cue.cue_type for cue in helper_cues}

    if not inferred and risk_tier == "benign":
        return ["benign"]

    if not inferred and (channel == "zalo" or "zalo" in text.casefold()):
        inferred.append("zalo_social_engineering")

    shadow_text = text.casefold()
    if not inferred and any(marker in shadow_text for marker in BANK_BRAND_MARKERS):
        inferred.append("bank_impersonation")
    if not inferred and any(marker in shadow_text for marker in TASK_SCAM_MARKERS):
        inferred.append("task_scam")

    if not inferred and {"otp_request", "credential_request"} & helper_cue_types and {"url", "spoofed_brand"} & helper_cue_types:
        inferred.append("bank_impersonation")
    if not inferred and {"job_offer", "payment_request"} & helper_cue_types:
        inferred.append("task_scam")
    if not inferred and "contact_takeover" in helper_cue_types:
        inferred.append("zalo_social_engineering")

    for cue in helper_cues:
        if cue.suggested_label is None or cue.suggested_label in inferred:
            continue
        inferred.append(cue.suggested_label)
        if len(inferred) == 2:
            break

    if inferred:
        return inferred[:2]
    raise ValueError("Threat decision requires at least one in-scope label")


def _normalize_evidence_cue_type(raw_cue_type: Any) -> CueType:
    cue_type = str(raw_cue_type or "").strip().casefold()
    alias_map: dict[str, CueType] = {
        "suspicious_tone": "urgency",
        "tone": "urgency",
        "brand_impersonation": "spoofed_brand",
        "brand_spoofing": "spoofed_brand",
        "link": "url",
        "login_link": "url",
        "otp": "otp_request",
        "credential": "credential_request",
        "money_request": "payment_request",
        "contact_switch": "contact_takeover",
    }
    normalized = alias_map.get(cue_type, cue_type or "generic")
    if normalized not in SUPPORTED_CUE_TYPES:
        return "generic"
    return cast(CueType, normalized)


def _coerce_payload_evidence(
    payload: dict[str, Any],
    *,
    normalized_text: str,
    fallback_labels: list[ThreatLabel],
    fallback_summary: str,
) -> list[dict[str, Any]]:
    raw_evidence = payload.get("evidence")
    if raw_evidence is None:
        raw_spans = payload.get("suspicious_spans") or payload.get("evidence_spans") or []
        if isinstance(raw_spans, str):
            raw_spans = [raw_spans]
        evidence: list[dict[str, Any]] = []
        for raw_span in raw_spans:
            span = str(raw_span).strip()
            if not span:
                continue
            if not cue_span_is_grounded(normalized_text, span):
                raise ValueError("Evidence span was not found in normalized text")
            evidence.append(
                {
                    "span": span,
                    "reason": fallback_summary,
                    "cue_type": "generic",
                    "supports_labels": fallback_labels,
                    "severity": "medium",
                }
            )
        return evidence

    if not isinstance(raw_evidence, list):
        raise ValueError("evidence must be a list")

    evidence = []
    for item in raw_evidence:
        if not isinstance(item, dict):
            raise ValueError("evidence items must be objects")
        span = str(item.get("span", "")).strip()
        if not cue_span_is_grounded(normalized_text, span):
            continue
        evidence_item = dict(item)
        evidence_item["cue_type"] = _normalize_evidence_cue_type(evidence_item.get("cue_type"))
        if not evidence_item.get("supports_labels"):
            evidence_item["supports_labels"] = fallback_labels
        evidence.append(evidence_item)

    if raw_evidence and not evidence:
        raise ValueError("Evidence span was not found in normalized text")
    return evidence


def _build_helper_evidence(helper_cues: list[HelperCue], *, labels: list[ThreatLabel]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for cue in helper_cues:
        evidence_labels = [cue.suggested_label] if cue.suggested_label is not None else labels
        if not evidence_labels:
            continue
        evidence.append(
            {
                "span": cue.span,
                "reason": cue.reason,
                "cue_type": cue.cue_type,
                "supports_labels": evidence_labels[:2],
                "severity": cue.severity,
            }
        )
    return evidence[:5]


def _is_unsafe_recommendation(text: str) -> bool:
    lowered = text.casefold().strip()
    for clause in re.split(r"[,.!?;:\n]+", lowered):
        clause = " ".join(clause.split())
        occurrences = sorted(
            (clause.find(marker), marker)
            for marker in UNSAFE_RECOMMENDATION_MARKERS
            if marker in clause
        )
        if not clause or not occurrences:
            continue
        negation = re.compile(r"(?:^|\s)(?:khong|không|dung|đừng|tranh|tránh)\s+$")
        previous_end = -1
        for start, marker in occurrences:
            if start < previous_end:
                continue
            if negation.search(clause[:start]) is None:
                return True
            previous_end = start + len(marker)
    return False


def cue_span_is_grounded(normalized_text: str, span: str) -> bool:
    """Return True when a cue span is present in the reviewable normalized text."""

    normalized_span = span.strip()
    return bool(normalized_span) and normalized_span.casefold() in normalized_text.casefold()


def is_recommendation_safe(text: str) -> bool:
    """Expose the Phase 4 recommendation-safety rule for reuse in release evaluation."""

    return not _is_unsafe_recommendation(text)


def _sanitize_recommendation_models(recommendations: list[Recommendation], *, risk_tier: str) -> list[Recommendation]:
    safe_recommendations = [
        recommendation.model_copy(update={"offline_safe": True})
        for recommendation in recommendations
        if not _is_unsafe_recommendation(recommendation.text)
    ]
    if safe_recommendations:
        return safe_recommendations[:3]

    fallback_texts = DEFAULT_RISKY_RECOMMENDATIONS if risk_tier != "benign" else (DEFAULT_BENIGN_RECOMMENDATION,)
    return [Recommendation(text=text, priority="high" if risk_tier != "benign" else "medium") for text in fallback_texts]


def _apply_safety_floor(decision: ThreatDecision, helper_cues: list[HelperCue], request: AnalysisRequest) -> ThreatDecision:
    cue_types = {cue.cue_type for cue in helper_cues}
    has_credential_or_payment = bool({"otp_request", "credential_request", "payment_request"} & cue_types)
    has_bank_url = "url" in cue_types and any(marker in request.text.casefold() for marker in BANK_BRAND_MARKERS)
    has_escalation_support = bool({"url", "spoofed_brand", "job_offer"} & cue_types)

    if decision.risk_tier != "benign":
        return decision
    if not helper_cues or not (has_credential_or_payment or has_bank_url):
        return decision

    floored_tier = "high-risk" if has_escalation_support else "suspicious"
    try:
        floored_labels = _infer_threat_labels(
            [label for label in decision.threat_labels if label != "benign"],
            text=request.text,
            channel=request.channel,
            helper_cues=helper_cues,
            risk_tier=floored_tier,
        )
    except ValueError:
        return decision
    helper_evidence = [
        EvidenceReason.model_validate(item) for item in _build_helper_evidence(helper_cues, labels=floored_labels)
    ]
    if helper_evidence:
        seen_spans = {item.span for item in helper_evidence}
        floored_evidence = helper_evidence + [item for item in decision.evidence if item.span not in seen_spans]
    else:
        floored_evidence = decision.evidence
    return ThreatDecision.model_validate(
        {
            "risk_tier": floored_tier,
            "threat_labels": floored_labels,
            "decision_summary": decision.decision_summary,
            "evidence": [item.model_dump() for item in floored_evidence[:5]],
            "recommendations": [item.model_dump() for item in decision.recommendations],
            "provisional": decision.provisional,
        }
    )


def _looks_like_legitimate_bank_otp_notice(
    text: str,
    helper_cues: list[HelperCue],
) -> bool:
    shadow_text = text.casefold()
    has_bank_brand = any(marker in shadow_text for marker in BANK_BRAND_MARKERS)
    has_otp_notice = any(marker in shadow_text for marker in LEGITIMATE_OTP_NOTICE_MARKERS)
    has_legitimate_context = any(marker in shadow_text for marker in LEGITIMATE_OTP_CONTEXT_MARKERS)
    has_nondisclosure_notice = any(
        marker in shadow_text for marker in LEGITIMATE_OTP_NONDISCLOSURE_MARKERS
    )
    has_unsafe_action = any(marker in shadow_text for marker in UNSAFE_OTP_ACTION_MARKERS)
    unsafe_cue_types = {
        "credential_request",
        "payment_request",
        "urgency",
        "url",
        "contact_takeover",
        "job_offer",
    }
    has_unsafe_helper_cue = any(cue.cue_type in unsafe_cue_types for cue in helper_cues)
    return (
        has_bank_brand
        and has_otp_notice
        and has_legitimate_context
        and has_nondisclosure_notice
        and not has_unsafe_action
        and not has_unsafe_helper_cue
    )


def _downgrade_legitimate_otp_notice(decision: ThreatDecision, request: AnalysisRequest) -> ThreatDecision:
    if decision.risk_tier != "suspicious":
        return decision
    return ThreatDecision.model_validate(
        {
            "risk_tier": "benign",
            "threat_labels": ["benign"],
            "decision_summary": (
                f"Structured decision from {request.channel} local runtime: legitimate bank OTP notice."
            ),
            "evidence": [],
            "recommendations": [{"text": DEFAULT_BENIGN_RECOMMENDATION, "priority": "medium"}],
            "provisional": decision.provisional,
        }
    )


def _build_threat_decision(payload: dict[str, Any], request: AnalysisRequest) -> ThreatDecision:
    risk_tier = str(payload.get("risk_tier", "suspicious")).strip().casefold()
    if risk_tier not in {"benign", "suspicious", "high-risk"}:
        raise ValueError(f"Unsupported risk_tier from model output: {payload.get('risk_tier')!r}")

    summary = str(
        payload.get("decision_summary")
        or payload.get("xai_explanation")
        or payload.get("summary")
        or f"Structured decision from {request.channel} local runtime."
    ).strip()
    if not summary:
        summary = f"Structured decision from {request.channel} local runtime."

    helper_cues = _find_helper_cues(request.text, request.channel)
    labels = _infer_threat_labels(
        payload.get("threat_labels") or payload.get("label"),
        text=request.text,
        channel=request.channel,
        helper_cues=helper_cues,
        risk_tier=risk_tier,
    )
    evidence_payload = _coerce_payload_evidence(
        payload,
        normalized_text=request.text,
        fallback_labels=labels,
        fallback_summary=summary,
    )
    if not evidence_payload and helper_cues:
        evidence_payload = _build_helper_evidence(helper_cues, labels=labels)

    raw_recommendations = payload.get("recommendations")
    if raw_recommendations is None:
        raw_recommendations = DEFAULT_RISKY_RECOMMENDATIONS if risk_tier != "benign" else (DEFAULT_BENIGN_RECOMMENDATION,)

    if isinstance(raw_recommendations, (list, tuple)):
        recommendation_payload = [
            item if isinstance(item, dict) else {"text": str(item), "priority": "high" if risk_tier != "benign" else "medium"}
            for item in raw_recommendations
        ][:3]
    elif isinstance(raw_recommendations, str):
        recommendation_payload = [{"text": raw_recommendations, "priority": "high" if risk_tier != "benign" else "medium"}]
    else:
        raise ValueError("recommendations must be a string or list")

    decision = ThreatDecision.model_validate(
        {
            "risk_tier": risk_tier,
            "threat_labels": labels,
            "decision_summary": summary,
            "evidence": evidence_payload,
            "recommendations": recommendation_payload,
            "provisional": payload.get("provisional", True),
        }
    )
    if _looks_like_legitimate_bank_otp_notice(request.text, helper_cues):
        decision = _downgrade_legitimate_otp_notice(decision, request)
    else:
        decision = _apply_safety_floor(decision, helper_cues, request)
    sanitized_recommendations = _sanitize_recommendation_models(decision.recommendations, risk_tier=decision.risk_tier)
    return ThreatDecision.model_validate(
        {
            "risk_tier": decision.risk_tier,
            "threat_labels": decision.threat_labels,
            "decision_summary": decision.decision_summary,
            "evidence": [item.model_dump() for item in decision.evidence],
            "recommendations": [item.model_dump() for item in sanitized_recommendations],
            "provisional": decision.provisional,
        }
    )


def resolve_base_model_path(candidate_id: str, artifact_root: Path) -> Path:
    """Resolve one manifest-bound base model after byte/tree verification."""

    return resolve_downloaded_model(artifact_root, candidate_id).path


def build_analysis_result(payload: dict[str, Any], request: AnalysisRequest, backend_name: str) -> AnalysisResult:
    decision = _build_threat_decision(payload, request)
    return AnalysisResult(
        risk_tier=decision.risk_tier,
        summary=decision.decision_summary,
        top_cues=[
            SuspiciousCue(span=evidence.span, reason=evidence.reason, cue_type=evidence.cue_type)
            for evidence in decision.evidence[:3]
        ],
        threat_labels=decision.threat_labels,
        recommendations=[recommendation.text for recommendation in decision.recommendations[:3]],
        backend_name=backend_name,
        provisional=decision.provisional,
        normalized_text=request.text,
    )
