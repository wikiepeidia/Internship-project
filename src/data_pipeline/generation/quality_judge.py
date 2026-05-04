"""LLM-as-judge quality validation for synthetic dataset records."""

from __future__ import annotations

import json
import re
from typing import Any, Callable

import httpx
from pydantic import BaseModel, Field

try:
    import anthropic
except ImportError:  # pragma: no cover - exercised via lazy provider fallback
    anthropic = None

from src.config.settings import Settings, get_settings
from src.data_pipeline.generation.prompts import build_judge_prompt


CLAUDE_MODEL = "claude-sonnet-4-6"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
JUDGE_PROGRESS_INTERVAL = 25


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Judge response did not contain a JSON object")
    return json.loads(cleaned[start : end + 1])


class JudgeVerdict(BaseModel):
    """Per-record judge scores and pass decision."""

    realism: int = Field(ge=1, le=5)
    label_correctness: int = Field(ge=1, le=5)
    code_switch_naturalness: int = Field(ge=1, le=5)
    pass_verdict: bool
    reason: str


class QualityStats(BaseModel):
    """Aggregated quality statistics for a judged batch."""

    total: int
    passed: int
    failed: int
    pass_rate: float
    avg_realism: float
    avg_label_correctness: float
    avg_code_switch_naturalness: float


class QualityJudge:
    """Validate generated dataset records with a different model than the generator."""

    def __init__(
        self,
        settings: Settings | None = None,
        judge_model: str | None = None,
        anthropic_client: Any | None = None,
        http_client: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.gemini_key = self.settings.gemini_api_key
        self.anthropic_key = self.settings.anthropic_api_key
        self.judge_model = judge_model
        self.anthropic_client = anthropic_client
        self.http_client = http_client or httpx.Client(timeout=60)

    def judge_record(self, record: dict[str, Any]) -> JudgeVerdict:
        """Judge a single dataset record and return its verdict."""
        prompt = build_judge_prompt(
            record_text=record["text"],
            record_label=record["label"],
            record_explanation=record["xai_explanation"],
        )
        model = self._select_judge_model(record.get("source"))
        result = _extract_json_object(self._call_judge(prompt, model))
        pass_verdict = all(
            result.get(metric, 0) >= 3
            for metric in ("realism", "label_correctness", "code_switch_naturalness")
        )
        return JudgeVerdict(
            realism=result["realism"],
            label_correctness=result["label_correctness"],
            code_switch_naturalness=result["code_switch_naturalness"],
            pass_verdict=pass_verdict,
            reason=result.get("reason", ""),
        )

    def judge_batch(
        self,
        records: list[dict[str, Any]],
        progress_callback: Callable[[str], None] | None = None,
    ) -> list[tuple[dict[str, Any], JudgeVerdict]]:
        """Judge a batch of records one by one."""
        judged: list[tuple[dict[str, Any], JudgeVerdict]] = []
        total = len(records)
        for index, record in enumerate(records, start=1):
            judged.append((record, self.judge_record(record)))
            if progress_callback and (index == total or index % JUDGE_PROGRESS_INTERVAL == 0):
                progress_callback(f"[judge {index}/{total}] scored generated records")
        return judged

    def filter_passed(
        self,
        records: list[dict[str, Any]],
        progress_callback: Callable[[str], None] | None = None,
    ) -> tuple[list[dict[str, Any]], QualityStats]:
        """Return only passed records plus aggregate quality statistics."""
        if progress_callback is None:
            judged = self.judge_batch(records)
        else:
            judged = self.judge_batch(records, progress_callback=progress_callback)
        passed_records = [record for record, verdict in judged if verdict.pass_verdict]
        verdicts = [verdict for _, verdict in judged]
        stats = QualityStats(
            total=len(records),
            passed=len(passed_records),
            failed=len(records) - len(passed_records),
            pass_rate=len(passed_records) / max(len(records), 1),
            avg_realism=sum(verdict.realism for verdict in verdicts) / max(len(verdicts), 1),
            avg_label_correctness=(
                sum(verdict.label_correctness for verdict in verdicts) / max(len(verdicts), 1)
            ),
            avg_code_switch_naturalness=(
                sum(verdict.code_switch_naturalness for verdict in verdicts) / max(len(verdicts), 1)
            ),
        )
        return passed_records, stats

    def _select_judge_model(self, source: str | None) -> str:
        if self.judge_model:
            return self.judge_model
        if source == "synthetic_claude" and self.gemini_key:
            return GEMINI_MODEL
        if source in {"synthetic_gemini", "synthetic_openrouter"} and self.anthropic_client:
            return CLAUDE_MODEL
        if self.gemini_key:
            return GEMINI_MODEL
        if self.anthropic_client:
            return CLAUDE_MODEL
        raise ValueError("No judge API key configured")

    def _call_judge(self, prompt: str, model: str) -> str:
        if model == GEMINI_MODEL and self.gemini_key:
            try:
                response = self.http_client.post(
                    GEMINI_URL,
                    params={"key": self.gemini_key},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 500},
                    },
                )
                if hasattr(response, "raise_for_status"):
                    response.raise_for_status()
                return response.json()["candidates"][0]["content"]["parts"][0]["text"]
            except httpx.HTTPError:
                if self.anthropic_client is None and not self.anthropic_key:
                    raise
                return self._call_judge(prompt, CLAUDE_MODEL)
        if model == CLAUDE_MODEL and self.anthropic_client:
            response = self.anthropic_client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        if model == CLAUDE_MODEL and self.anthropic_client is None and self.anthropic_key:
            if anthropic is None:
                raise ValueError("No judge API key configured")
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_key)
            response = self.anthropic_client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        raise ValueError("No judge API key configured")