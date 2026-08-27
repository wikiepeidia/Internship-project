"""Prompt-formatting helpers for Qwen-family fine-tuning data."""

from __future__ import annotations

import json

from src.data_pipeline.schemas import DatasetRecord
from src.model_adaptation.schemas import ModelCandidate


def format_training_prompt(record: DatasetRecord, candidate: ModelCandidate) -> str:
    """Format one instruction-style prompt for the selected candidate family."""

    response_schema = {
        "label": "bank_impersonation | zalo_social_engineering | task_scam | benign",
        "risk_tier": "benign | suspicious | high-risk",
        "suspicious_spans": ["exact suspicious substrings"],
        "xai_explanation": "localized explanation for the end user",
    }
    schema_text = json.dumps(response_schema, ensure_ascii=False)
    return "\n".join(
        [
            f"Candidate: {candidate.hf_source}",
            "You are fine-tuning a local Vietnamese phishing detector.",
            "Analyze the following raw message text and produce a structured response.",
            f"Response schema: {schema_text}",
            f"Message text: {record.text}",
        ]
    )