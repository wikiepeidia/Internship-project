"""Dataset-loading and training-example helpers for Phase 3 fine-tuning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.data_pipeline.schemas import DatasetRecord
from src.model_adaptation.prompts import format_training_prompt
from src.model_adaptation.schemas import ModelCandidate


def load_split_records(split_path: Path) -> list[DatasetRecord]:
    """Load one Phase 1 split JSONL file into typed dataset records."""

    records: list[DatasetRecord] = []
    with split_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            records.append(DatasetRecord.model_validate(json.loads(line)))
    return records


def build_training_examples(
    records: list[DatasetRecord],
    candidate: ModelCandidate,
) -> list[dict[str, Any]]:
    """Create candidate-aware instruction/response pairs from dataset records."""

    examples: list[dict[str, Any]] = []
    for record in records:
        response_payload = {
            "label": record.label,
            "risk_tier": record.risk_tier,
            "suspicious_spans": record.suspicious_spans,
            "xai_explanation": record.xai_explanation,
        }
        examples.append(
            {
                "candidate_id": candidate.candidate_id,
                "hf_source": candidate.hf_source,
                "prompt": format_training_prompt(record, candidate),
                "response": json.dumps(response_payload, ensure_ascii=False),
                "text": record.text,
                "risk_tier": record.risk_tier,
                "suspicious_spans": list(record.suspicious_spans),
                "xai_explanation": record.xai_explanation,
            }
        )
    return examples