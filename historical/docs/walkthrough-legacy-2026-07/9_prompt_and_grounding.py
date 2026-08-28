# ============================================================
# STEP 9 of 10 — Prompt Construction + Evidence Grounding (THE MOST
# IMPORTANT FILE FOR "HOW DOES THIS ACTUALLY WORK" QUESTIONS)
# ============================================================
# Canonical source (this numbered copy exists ONLY for defense-day
# navigation — it is not a second implementation and is not imported
# by anything): src/runtime/analyzers/local_model.py
#
# What this file does, in order:
#   1. build_structured_analysis_prompt() (~line 262) builds the exact
#      prompt string sent to the model.
#   2. extract_structured_payload() (~line 298) scans the model's raw
#      text output for a valid JSON object.
#   3. cue_span_is_grounded() (~line 550) — THE key function. A plain
#      case-insensitive substring check: is this claimed evidence span
#      actually present in the input text? This is the entire "grounded
#      cues" algorithm. Not fuzzy matching, not embeddings, not RAG.
#   4. _apply_safety_floor() (~line 576) — an independent, hand-written
#      regex-based rule engine (see rules.py) that can force the risk
#      tier upward even if the model said "benign."
#   5. build_analysis_result() (~line 730) assembles everything into
#      the final typed result the user sees.
#
# See also: documents/reports/supervisor/defense_code_navigation.md
# ============================================================

"""Shared helpers for Phase 4 local model-backed runtime analyzers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Literal, cast, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.model_adaptation.training import _load_download_manifest
from src.runtime.analyzers.rules import CueRule, build_default_rules
from src.runtime.contracts import AnalysisRequest, AnalysisResult, SuspiciousCue, ThreatLabel


# CueType / Priority are the closed vocabularies the WHOLE evidence system
# is built on — every piece of evidence, whether it came from the model or
# from the regex rule engine (rules.py), gets normalized into one of these
# cue_type values. "generic" is the deliberate catch-all for anything that
# doesn't cleanly fit a specific bucket, so evidence never gets DROPPED
# just because it doesn't match a named category.
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

# get_args() pulls the allowed values straight from the ThreatLabel/CueType
# Literal type definitions (contracts.py / this file) — same trick as the
# CLI's --channel choices in step 7, so these "supported values" sets can
# never silently drift out of sync with the actual type definitions.
SUPPORTED_THREAT_LABELS = get_args(ThreatLabel)
SUPPORTED_CUE_TYPES = set(get_args(CueType))
# The FALLBACK recommendations used when the model doesn't provide usable
# ones, or when every model-provided recommendation gets sanitized away
# (see _sanitize_recommendation_models below) — these are hand-written,
# not model output, specifically so there's always at least one guaranteed-
# safe recommendation string available no matter what the model says.
DEFAULT_RISKY_RECOMMENDATIONS = (
    "Khong bam vao lien ket hoac cai ung dung tu tin nhan nay.",
    "Khong chia se OTP, mat khau, CCCD, hoac CVV.",
    "Xac minh qua ung dung, website, hoac tong dai chinh thuc.",
)
DEFAULT_BENIGN_RECOMMENDATION = (
    "Không cần thao tác thêm nếu bạn nhận ra nội dung này. "
    "Nếu vẫn thấy bất thường, hãy tự kiểm tra qua ứng dụng, website hoặc tổng đài chính thức."
)
# THE RECOMMENDATION SAFETY BLOCKLIST — every phrase here is something a
# recommendation should NEVER tell a user to do (click a link, reply,
# share an OTP/CCCD/CVV, transfer money, install an app, or call/contact a
# number FROM the suspicious message itself). This is what
# _is_unsafe_recommendation checks against below. Both Vietnamese
# no-diacritics and with-diacritics forms are listed for each phrase
# because model output is inconsistent about diacritics — matching only
# one form would let the other slip through the filter.
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
# The next three tuples exist ONLY to support
# _looks_like_legitimate_bank_otp_notice below — the specific, deliberate
# exception for "this looks like a REAL bank sending a REAL OTP notice,
# not a phishing attempt." A message needs a bank brand name AND OTP
# language AND legitimate-context phrasing ("don't share this," "valid
# for X minutes") AND the ABSENCE of any unsafe action marker (a link, "tap
# here," "your account is locked") to qualify — all four conditions, not
# just one, because real banks legitimately do send "here's your OTP,
# don't share it" texts, and treating every OTP mention as automatically
# suspicious would create constant false positives on completely normal
# banking messages.
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
)


@dataclass(frozen=True)
class HelperCue:
    """
    One finding from the INDEPENDENT regex rule engine (rules.py) — NOT
    from the model. "Helper" because these cues can help fill in evidence
    the model missed, or force the risk tier upward (_apply_safety_floor
    below) regardless of what the model concluded. tier_override lets a
    specific hand-written rule assert "if this pattern matches, the risk
    tier can't be lower than X," a deliberate authored safety signal
    independent of anything learned.
    """
    span: str
    reason: str
    cue_type: CueType
    severity: Priority
    start: int
    suggested_label: ThreatLabel | None = None
    tier_override: str | None = None


class EvidenceReason(BaseModel):
    """
    One piece of evidence in the FINAL validated decision. model_config =
    ConfigDict(extra="forbid") on every model in this file is a deliberate,
    strict choice: if the model (or a helper cue) tries to sneak in an
    unexpected extra field, Pydantic raises rather than silently accepting
    unknown data — closed-schema-by-default, matching the "don't trust,
    verify" posture this whole module is built around. span/reason have
    length bounds (1-160 / 1-240 chars) as a sanity guard against a model
    dumping an entire paragraph into a field meant to be a short quoted
    span or a short reason.
    """
    model_config = ConfigDict(extra="forbid")

    span: str = Field(min_length=1, max_length=160)
    reason: str = Field(min_length=1, max_length=240)
    cue_type: CueType
    supports_labels: list[ThreatLabel] = Field(min_length=1, max_length=2)
    severity: Priority = "medium"

    @field_validator("span", "reason")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        # min_length=1 alone doesn't catch a string that's ALL whitespace
        # (e.g. "   ") — Pydantic's length check counts characters, not
        # meaningful content. This validator closes that gap.
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
    """
    The complete, fully-validated decision object — this is the LAST gate
    before build_analysis_result (bottom of this file) turns it into the
    public AnalysisResult the user actually sees. Every field is bounded
    (evidence capped at 5 items, recommendations at 1-3, decision_summary
    at 12-280 chars) — these caps exist for UX (don't overwhelm the user
    with 20 evidence bullets) as much as for safety.
    """
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
        """
        CROSS-FIELD consistency rules — these can't be expressed as a
        single-field Field()/field_validator constraint because they
        depend on the RELATIONSHIP between risk_tier and threat_labels
        together. Four rules, each guarding against a specific
        self-contradictory decision the model (or the safety-floor logic)
        could otherwise produce:
          1. "benign" can never appear ALONGSIDE another threat label —
             benign is mutually exclusive by definition.
          2. risk_tier="benign" MUST have threat_labels exactly
             ["benign"] — no partial credit, no "benign but also kind of
             bank_impersonation."
          3. The mirror of rule 2: a non-benign tier can never carry the
             "benign" label at all.
          4. risk_tier="high-risk" REQUIRES at least one evidence item —
             you cannot tell a user "this is high risk" with zero
             justification for why; that would be an unaccountable,
             unverifiable claim, which is exactly what this whole
             grounding system exists to prevent.
        Raising ValueError here means an inconsistent decision fails to
        even CONSTRUCT — it can never reach the user in a self-
        contradictory shape.
        """
        if "benign" in self.threat_labels and len(self.threat_labels) > 1:
            raise ValueError("benign cannot be combined with threat labels")
        if self.risk_tier == "benign" and self.threat_labels != ["benign"]:
            raise ValueError("benign tier must map to benign only")
        if self.risk_tier != "benign" and "benign" in self.threat_labels:
            raise ValueError("non-benign tier cannot include benign")
        if self.risk_tier == "high-risk" and not self.evidence:
            raise ValueError("high-risk decisions require evidence")
        return self


# HONEST NOTE (worth knowing if asked): STRUCTURED_ANALYSIS_SCHEMA and
# STRUCTURED_ANALYSIS_EXAMPLE below document the FULL intended JSON
# contract (matching ThreatDecision's shape) as a readable reference, but
# the actual runtime prompt (build_structured_analysis_prompt, just below
# these) does NOT embed either of them — it sends a much shorter,
# condensed instruction set instead. That's a deliberate size/latency
# tradeoff for local CPU inference (a smaller prompt means faster
# generation on modest hardware), not an oversight; these two constants
# stay in the module as the canonical, precise reference for what the
# schema and a good example actually look like — useful for a human
# reading this file, for documentation, or for future prompt-tuning work,
# even though nothing in the current runtime path imports them. If asked
# "is this dead code" — yes, structurally unused at runtime right now, and
# that's a fair, honest answer; it's reference documentation living next
# to the code it documents rather than in a separate doc file.
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

# Used by _score_structured_payload_candidate below to tell apart a
# TOP-LEVEL decision object (has keys like risk_tier/threat_labels/
# decision_summary) from a NESTED evidence-item object (has keys like
# span/reason/cue_type) that might also parse as valid JSON out of the
# same raw model output — see extract_structured_payload for why this
# distinction matters.
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
    """
    THE ACTUAL PROMPT SENT TO THE MODEL — every single time. Five plain
    instruction lines plus the message text, no few-shot examples embedded
    (deliberately — see the note on STRUCTURED_ANALYSIS_EXAMPLE above: kept
    short for local CPU inference speed, relying on the fine-tuning itself
    to have taught the model the expected response shape, rather than
    re-teaching it via a long prompt every single call). Notice line 5
    explicitly whitelists safe recommendation behavior and blacklists
    unsafe verbs (click/reply/share OTP/share CCCD-CVV/install/transfer) —
    this is the FIRST layer of defense against unsafe recommendations; the
    second, stricter layer is the code-level _is_unsafe_recommendation
    check further down, which doesn't just ask nicely, it actually verifies
    the model's output against the same blocklist after the fact.
    """
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
    # Heuristic scoring, not a hard rule — rewards a candidate JSON object
    # for having primary-decision-shaped keys (risk_tier, threat_labels,
    # etc, each worth a meaningful point bonus on top of the base
    # per-primary-key score), and PENALIZES it for looking like a NESTED
    # evidence item instead (has nested keys like span/cue_type but ZERO
    # primary keys) — that penalty is what stops extract_structured_payload
    # below from accidentally picking a lone {"span": "...", "reason": "..."}
    # evidence fragment as if it were the whole decision.
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
    """
    Scans the model's RAW text output for every possible JSON object it
    contains, and picks the BEST one — not just the first one, and not
    just "the biggest one." Why this is more careful than a naive
    json.loads(raw_output) or even the code-fence-stripping approach used
    in the data-generation pipeline (step 2/3): a local, smaller
    fine-tuned model's raw output can be messier than a big commercial
    API's — it might emit stray text before/after the JSON, or even
    produce a nested example JSON object as part of its reasoning before
    the real answer. So this walks EVERY character position, and at every
    `{` tries json.JSONDecoder().raw_decode() (which parses just one valid
    JSON value starting at that position and tells you where it ended,
    rather than requiring the WHOLE remaining string to be valid JSON) —
    collecting every dict-shaped candidate found anywhere in the output,
    then uses _score_structured_payload_candidate to pick whichever one
    actually looks like a complete top-level decision object, not a
    fragment. Only raises if NOTHING dict-shaped was found anywhere.
    """
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
    # Accepts EITHER a bare string OR a list of strings for the same
    # field — small local models are inconsistent about whether they
    # return "threat_labels": "bank_impersonation" or
    # "threat_labels": ["bank_impersonation"], and this accepts both
    # rather than treating the "wrong" shape as an error. Also dedupes
    # (via the `seen` set) and drops blank entries, so the model repeating
    # itself or emitting an empty string doesn't pollute the result.
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
    # Hard rejection (not silent dropping) of any label outside
    # SUPPORTED_THREAT_LABELS — if the model hallucinates a label that was
    # never in its training vocabulary, that's treated as an ERROR to
    # surface, not something to quietly discard and hope nobody notices.
    labels = _normalize_text_list(raw_labels, field_name="threat_labels")
    unsupported = [label for label in labels if label not in SUPPORTED_THREAT_LABELS]
    if unsupported:
        raise ValueError(f"Unsupported threat_labels from model output: {unsupported!r}")
    return cast(list[ThreatLabel], labels)


def normalize_recommendations(raw_recommendations: Any) -> list[str]:
    return _normalize_text_list(raw_recommendations, field_name="recommendations")


def _map_rule_to_helper_cue(rule: CueRule, span: str, start: int, text: str, channel: str) -> HelperCue:
    """
    Translates ONE regex rule match (from rules.py's CueRule catalog,
    which knows about its own generic categories like "credential_request"
    or "link_prompt") into the more specific CueType/ThreatLabel vocabulary
    this file uses. E.g. rules.py's generic "credential_request" category
    gets refined here into specifically "otp_request" if the matched text
    itself contains "otp", or a plain "credential_request" otherwise — a
    small extra layer of specificity added at this mapping boundary rather
    than needing rules.py itself to know about every fine-grained
    downstream category.
    """
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

    # Channel-aware fallback: if nothing else suggested a label yet, but
    # this message came in on Zalo (or mentions "zalo" in its own text),
    # nudge toward zalo_social_engineering — channel context is a real,
    # legitimate signal for THIS specific label since that threat category
    # is inherently about the Zalo platform.
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
    """
    Runs EVERY rule in the default rule catalog (build_default_rules(),
    rules.py) against the message and collects every match as a HelperCue
    — this is the independent regex safety layer mentioned in the code
    navigation doc, running completely separately from whatever the model
    itself produces. Matching is done against shadow_text (casefolded) so
    rules don't need to worry about case sensitivity themselves, but the
    actual `span` extracted uses the ORIGINAL text's exact casing/
    formatting (text[match.start():match.end()]) — so evidence shown to
    the user preserves the real message's exact appearance, not a
    lowercased version. Deduped by (span, reason) so the same rule
    matching the same span twice (possible with overlapping alternation
    patterns) doesn't produce duplicate cues. Sorted by position
    (cue.start) so cues are presented in the order they actually appear in
    the message, reading top to bottom.
    """
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
    """
    A CASCADE of increasingly indirect ways to arrive at a threat label,
    tried IN ORDER, stopping as soon as one succeeds:
      1. Trust the model's own raw_labels first, if it gave any valid ones.
      2. If risk_tier is "benign" and the model gave nothing, that's fine —
         benign doesn't need a specific threat label beyond "benign"
         itself.
      3. Channel/keyword fallback: Zalo channel or "zalo" mentioned in text
         → zalo_social_engineering; known bank brand names in the text →
         bank_impersonation; task-scam vocabulary (nhiem vu/hoa hong/cong
         tac vien — "task"/"commission"/"collaborator", classic Vietnamese
         task-scam recruiting language) → task_scam.
      4. Helper-cue-TYPE combination fallback: e.g. if the regex layer
         independently found BOTH a credential/OTP request AND a URL or
         spoofed-brand cue in the same message, that combination itself is
         a strong bank_impersonation signal, even without keyword matches.
      5. Individual helper cues' own suggested_label (set in
         _map_rule_to_helper_cue above) get appended too, up to a max of 2
         total labels.
    Raises if, after ALL of that, still nothing was inferred — a decision
    truly cannot ship with zero labels; that would be an unclassified,
    meaningless result.
    """
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
    # Same alias-collapsing idea as the dataset-generation normalizers in
    # step 2/3 — the model might say "brand_spoofing" or "login_link"
    # instead of this file's canonical "spoofed_brand"/"url" vocabulary;
    # this maps observed variants onto the closed CueType set. Anything
    # totally unrecognized falls back to "generic" rather than raising —
    # an unrecognized cue_type shouldn't be fatal to the whole decision the
    # way an ungrounded SPAN is (see below), it just gets bucketed
    # generically.
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
    """
    THIS IS WHERE cue_span_is_grounded() ACTUALLY GETS ENFORCED — the
    single most important function in this whole file to be able to
    narrate live. Two possible input shapes, both funneling through the
    SAME grounding check:

      SHAPE A (payload.get("evidence") is None): the model used the
      simpler "suspicious_spans"/"evidence_spans" list-of-strings shape
      instead of full evidence objects. Every span in that list is checked
      via cue_span_is_grounded — if EVEN ONE ungrounded span shows up here,
      this raises ValueError immediately, aborting the whole evidence list
      rather than silently keeping the grounded ones and dropping the bad
      one. (Contrast with SHAPE B below, which is more lenient — see why
      there.)

      SHAPE B (payload["evidence"] is a real list of evidence objects):
      each item is checked individually — `if not
      cue_span_is_grounded(...): continue` SKIPS just that one ungrounded
      item and keeps processing the rest, rather than failing the whole
      batch. This is the actual guarantee behind "the model's claimed
      evidence is verified, not trusted": a model can output 5 evidence
      items, and if 2 of them cite text that doesn't actually appear in
      the message, those 2 are silently dropped and only the 3 real ones
      reach the user — the model doesn't get to fabricate evidence just by
      asserting it exists.

      The final check (`if raw_evidence and not evidence: raise`) catches
      the case where the model DID provide evidence, but every single item
      failed grounding — that's suspicious enough (the model hallucinated
      its entire evidence list) to treat as a hard error rather than
      silently proceeding with an empty evidence list, which is why SHAPE
      B is per-item-lenient but still has an all-or-nothing fallback at
      the very end.
    """
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
    # Converts HelperCue objects (from the regex rule engine) into the same
    # plain-dict evidence shape the model's own evidence uses — this is
    # what lets _build_threat_decision below use helper cues as a FALLBACK
    # evidence source when the model provided none at all (see "if not
    # evidence_payload and helper_cues" further down). Note these never
    # need a grounding check themselves — they're extracted directly FROM
    # the message text via regex match, so they're grounded by
    # construction, not by verification.
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
    # NEGATIVE-PREFIX ESCAPE HATCH FIRST: if the recommendation text
    # STARTS WITH a negating word ("khong"/"không" = "don't", "tranh"/
    # "tránh" = "avoid", "xac minh"/"xác minh" = "verify") it's treated as
    # automatically safe, WITHOUT even checking the marker list — this
    # matters because a genuinely safe recommendation like "Khong bam vao
    # lien ket" ("Don't click the link") would otherwise trip the "bam
    # vao"/"click" marker below despite being the OPPOSITE of unsafe
    # advice. Only after this early-exit does it fall through to checking
    # whether any literal unsafe marker phrase appears anywhere in the
    # text.
    lowered = text.casefold().strip()
    if lowered.startswith(("khong ", "không ", "tranh ", "tránh ", "xac minh ", "xác minh ")):
        return False
    return any(marker in lowered for marker in UNSAFE_RECOMMENDATION_MARKERS)


def cue_span_is_grounded(normalized_text: str, span: str) -> bool:
    """
    Return True when a cue span is present in the reviewable normalized text.

    ============================================================
    THE SINGLE MOST IMPORTANT FUNCTION IN THE ENTIRE PROJECT.
    ============================================================
    This is THE "how do nodes connect" answer, THE entire "grounded
    evidence" algorithm, in two lines: strip whitespace off the claimed
    span, then check whether that span — casefolded — is a literal
    SUBSTRING of the casefolded normalized message text.

    That's it. Read it out loud if asked "what's the algorithm":
      normalized_span.casefold() in normalized_text.casefold()

    NOT fuzzy matching. NOT embeddings. NOT a second model call asking
    "does this evidence support this text?" NOT retrieval, NOT RAG, NOT a
    vector database. A deterministic, case-insensitive substring
    containment check — the same kind of check taught in an intro
    programming class, applied here as a DELIBERATE choice: it means every
    single piece of evidence shown to a user can be mechanically,
    independently PROVEN to be real text that actually appears in their
    message, with zero trust placed in the model's own claim that it does.
    A fuzzy/similarity-based check would have been WEAKER for this
    purpose — it could pass evidence that merely resembles real text
    without actually quoting it, which defeats the entire point of
    "grounded" evidence.

    casefold() (not just .lower()) is used on both sides specifically
    because it's the more aggressive/correct Unicode case-folding — for
    text that mixes Vietnamese diacritics with plain ASCII, casefold
    handles more edge cases correctly than a simple lower() would.

    Called from exactly two places: _coerce_payload_evidence above (the
    real enforcement point, on every span the MODEL claims) and nowhere
    else needs it, because helper cues (from the regex rule engine) are
    extracted directly from the real text via regex match — they're
    grounded by construction, they never need to be checked.
    """

    normalized_span = span.strip()
    return bool(normalized_span) and normalized_span.casefold() in normalized_text.casefold()


def is_recommendation_safe(text: str) -> bool:
    """Expose the Phase 4 recommendation-safety rule for reuse in release evaluation."""
    # Public wrapper around the private _is_unsafe_recommendation check —
    # exists so OTHER code (e.g. an offline evaluation/release-gating
    # script that scores model output before shipping a new adapter) can
    # reuse the EXACT same safety definition this runtime enforces live,
    # rather than a second, potentially-drifting reimplementation.
    return not _is_unsafe_recommendation(text)


def _sanitize_recommendation_models(recommendations: list[Recommendation], *, risk_tier: str) -> list[Recommendation]:
    """
    THE SECOND, CODE-LEVEL SAFETY LAYER for recommendations (the first
    being the prompt instruction in build_structured_analysis_prompt).
    Filters OUT any recommendation whose text fails _is_unsafe_recommendation,
    keeping only genuinely safe ones (and force-setting offline_safe=True
    on the survivors). If that filtering leaves ZERO recommendations —
    meaning every single one the model or helper logic proposed turned out
    unsafe — this doesn't just return an empty list (a user should never
    see "no guidance available" after a risky message); it falls back to
    the hand-written DEFAULT_RISKY_RECOMMENDATIONS / DEFAULT_BENIGN_RECOMMENDATION
    constants, which are guaranteed safe by construction since a human
    wrote them, not a model.
    """
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
    """
    THE SAFETY-NET OVERRIDE — the second half of "the model's decision is
    not the final word." Even after the model has spoken and said
    "benign," this function gets one more say: if the INDEPENDENT regex
    rule engine found strong danger signals the model apparently missed,
    the risk tier gets force-escalated regardless of what the model
    concluded.

    Only even CONSIDERS acting if decision.risk_tier == "benign" — a
    model that already said suspicious/high-risk doesn't need flooring,
    it's already escalated. Two specific danger patterns trigger a floor:
      - has_credential_or_payment: helper cues found an OTP/credential/
        payment request pattern.
      - has_bank_url: helper cues found a URL AND the message separately
        mentions a known bank brand name — the combination (a link plus a
        bank name) is the classic phishing shape, even without a
        credential ask.
    If EITHER holds, escalate: to "high-risk" if there's ALSO an
    escalation-support signal (url/spoofed_brand/job_offer cue types —
    stronger corroborating evidence), otherwise the more conservative
    "suspicious." This isn't a binary escalate-to-max — it scales the
    severity of the override to the severity of what was actually found.

    The `try/except ValueError: return decision` around _infer_threat_labels
    is a safety valve on the safety valve: if flooring can't even produce
    a valid label set, better to silently keep the model's original
    (unfloored) decision than to crash the whole analysis — a missed
    escalation is bad, but a hard crash on a real user's message would be
    worse.

    helper_evidence is prepended (not appended) ahead of the model's
    original evidence — the REASON for the floor should be the first,
    most visible evidence shown, with model evidence for spans not already
    covered kept after it (deduped by span so nothing shows twice).
    """
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


def _looks_like_legitimate_bank_otp_notice(text: str) -> bool:
    # The four-condition AND check described in the constants section
    # above — ALL FOUR must hold (real bank brand + OTP language +
    # legitimate reassurance phrasing + NO unsafe action prompt) before a
    # message is treated as a genuine, harmless bank notification rather
    # than a phishing attempt. This runs BEFORE _apply_safety_floor in
    # _build_threat_decision below — a legitimate OTP notice gets
    # DOWNGRADED to benign even if it happens to also trip some helper
    # cue pattern (e.g. containing the word "OTP" itself, which the
    # credential-request rule watches for) — a real bank OTP text
    # shouldn't get flagged just because it necessarily talks about OTPs.
    shadow_text = text.casefold()
    has_bank_brand = any(marker in shadow_text for marker in BANK_BRAND_MARKERS)
    has_otp_notice = any(marker in shadow_text for marker in LEGITIMATE_OTP_NOTICE_MARKERS)
    has_legitimate_context = any(marker in shadow_text for marker in LEGITIMATE_OTP_CONTEXT_MARKERS)
    has_unsafe_action = any(marker in shadow_text for marker in UNSAFE_OTP_ACTION_MARKERS)
    return has_bank_brand and has_otp_notice and has_legitimate_context and not has_unsafe_action


def _downgrade_legitimate_otp_notice(decision: ThreatDecision, request: AnalysisRequest) -> ThreatDecision:
    # Full replacement, not a partial patch: builds a brand-new benign
    # ThreatDecision from scratch (empty evidence — nothing suspicious TO
    # cite — and the standard benign recommendation) rather than trying to
    # adjust the model's original fields piecemeal, since a downgrade this
    # complete makes a from-scratch reconstruction simpler and safer than
    # surgically editing the old decision.
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
    """
    THE FULL PIPELINE, END TO END — this is what ties together every
    function above into one coherent decision. Walk it top to bottom as
    the answer to "what happens to the model's raw JSON before it reaches
    the user":
      1. Validate risk_tier is one of the 3 allowed values (hard reject
         otherwise).
      2. Pick a decision_summary from whichever field name the model
         actually used (decision_summary / xai_explanation / summary —
         yet more tolerance for model output shape drift), with a generic
         fallback string if all three are empty.
      3. Run the independent regex rule engine (_find_helper_cues) — this
         ALWAYS runs, regardless of what the model said, because its
         output feeds both label inference AND the safety floor later.
      4. Infer/validate threat labels (_infer_threat_labels — the cascade
         covered above).
      5. Coerce and GROUND evidence (_coerce_payload_evidence — where
         cue_span_is_grounded is actually enforced). If the model gave NO
         evidence at all but the regex layer found helper cues, those
         become the evidence instead of leaving the decision with nothing.
      6. Normalize recommendations into the Recommendation shape, with
         hand-written defaults if the model gave none.
      7. Construct the ThreatDecision — this is where ThreatDecision's own
         model_validator (the benign/non-benign consistency rules) gets
         triggered; an internally-contradictory decision fails to
         construct right here.
      8. TWO MUTUALLY EXCLUSIVE OVERRIDE PATHS: either downgrade (if this
         looks like a legitimate bank OTP notice) OR apply the safety
         floor (otherwise) — never both, since a message that qualifies
         as a legitimate notice by definition shouldn't ALSO be
         floor-escalated.
      9. Sanitize recommendations (strip anything unsafe, fall back to
         hand-written safe defaults if everything got stripped).
      10. Reconstruct ONE FINAL ThreatDecision from the (possibly
          overridden, possibly sanitized) pieces — re-validated one more
          time through ThreatDecision's constructor, so the object that
          leaves this function is guaranteed to have passed every
          consistency check, no matter which override path was taken.
    """
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
    if _looks_like_legitimate_bank_otp_notice(request.text):
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
    # Same manifest-then-fallback lookup pattern seen in training.py (step
    # 5) and convert.py (step 6) — used here by the ACCELERATED analyzer
    # backend variant (not the GGUF one covered in step 10), which needs
    # the original HuggingFace-format base model rather than a .gguf file.
    manifest_model_paths = _load_download_manifest(artifact_root)
    manifest_path = manifest_model_paths.get(candidate_id)
    if manifest_path is not None and manifest_path.exists():
        return manifest_path

    fallback_path = artifact_root / "base" / candidate_id
    if fallback_path.exists():
        return fallback_path

    raise FileNotFoundError(
        f"Missing base model for candidate_id={candidate_id}. "
        f"Expected {artifact_root / 'manifests' / 'download-manifest.json'} or {fallback_path}"
    )


def build_analysis_result(payload: dict[str, Any], request: AnalysisRequest, backend_name: str) -> AnalysisResult:
    """
    THE FINAL STEP — every backend (GGUFAnalyzer in step 10,
    AcceleratedAnalyzer, even HeuristicAnalyzer) calls this SAME function
    at the end of its own analyze() implementation, after it has a raw
    payload dict (parsed model JSON, or a rule-engine-only payload for the
    heuristic backend). Runs the full _build_threat_decision pipeline
    above, then reshapes the internal ThreatDecision into the PUBLIC
    AnalysisResult contract (contracts.py) that RuntimeService (step 8)
    and ultimately the CLI/browser demo actually consume.
    Note top_cues and recommendations are both re-capped to 3 items HERE
    (on top of ThreatDecision's own cap of 5 evidence / 3 recommendations)
    — this is the FINAL display-facing trim, separate from
    RuntimeService's own runtime_max_cues cap (step 8) which operates on
    this already-trimmed list; two independent limits at two different
    layers, not a contradiction, just belt-and-suspenders UX control.
    normalized_text is carried through into the result too — so a caller
    (or a test) can always see exactly what text the decision was actually
    made against, the same normalized form cue_span_is_grounded checked
    evidence spans within.
    """
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
