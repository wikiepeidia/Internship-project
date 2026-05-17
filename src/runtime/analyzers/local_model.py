"""Shared helpers for Phase 3 local model-backed runtime analyzers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.model_adaptation.training import _load_download_manifest
from src.runtime.contracts import AnalysisRequest, AnalysisResult, SuspiciousCue


STRUCTURED_ANALYSIS_SCHEMA = {
    "risk_tier": "benign | suspicious | high-risk",
    "suspicious_spans": ["exact suspicious substrings from the message"],
    "xai_explanation": "short Vietnamese explanation grounded in the message text",
}

STRUCTURED_ANALYSIS_EXAMPLE = {
    "risk_tier": "suspicious",
    "suspicious_spans": ["ma OTP", "vpbank-safe.example"],
    "xai_explanation": "Thong diep yeu cau OTP va dan nguoi dung toi lien ket khong chinh thong.",
}


def build_structured_analysis_prompt(text: str) -> str:
    schema_text = json.dumps(STRUCTURED_ANALYSIS_SCHEMA, ensure_ascii=False)
    example_text = json.dumps(STRUCTURED_ANALYSIS_EXAMPLE, ensure_ascii=False)
    return "\n".join(
        [
            "You are a local Vietnamese phishing detector.",
            "Analyze the message text and return JSON only.",
            "Choose risk_tier from: benign, suspicious, high-risk.",
            "Use exact suspicious spans from the message when possible.",
            "Do not copy the instructions, schema text, or example values into the answer.",
            f"Schema: {schema_text}",
            f"Example output: {example_text}",
            f"Message text: {text}",
        ]
    )


def extract_structured_payload(raw_output: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, character in enumerate(raw_output):
        if character != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(raw_output[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ValueError("Model response did not contain a valid JSON object")


def resolve_base_model_path(candidate_id: str, artifact_root: Path) -> Path:
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
    risk_tier = str(payload.get("risk_tier", "suspicious")).strip().casefold()
    if risk_tier not in {"benign", "suspicious", "high-risk"}:
        raise ValueError(f"Unsupported risk_tier from model output: {payload.get('risk_tier')!r}")

    explanation = str(
        payload.get("xai_explanation")
        or payload.get("summary")
        or f"{backend_name} local profile returned a structured result."
    ).strip()
    if not explanation:
        explanation = f"{backend_name} local profile returned a structured result."

    suspicious_spans = payload.get("suspicious_spans") or []
    if isinstance(suspicious_spans, str):
        suspicious_spans = [suspicious_spans]

    top_cues: list[SuspiciousCue] = []
    seen_spans: set[str] = set()
    for raw_span in suspicious_spans:
        span = str(raw_span).strip()
        if not span or span in seen_spans:
            continue
        seen_spans.add(span)
        top_cues.append(
            SuspiciousCue(
                span=span,
                reason=explanation,
                cue_type="model_inference",
            )
        )
        if len(top_cues) == 3:
            break

    return AnalysisResult(
        risk_tier=risk_tier,
        summary=explanation,
        top_cues=top_cues,
        backend_name=backend_name,
        normalized_text=request.text,
    )