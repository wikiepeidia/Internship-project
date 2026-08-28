# ============================================================
# STEP 3 of 10 — Cross-Model Quality Judging
# ============================================================
# Canonical source (this numbered copy exists ONLY for defense-day
# navigation — it is not a second implementation and is not imported
# by anything): src/data_pipeline/generation/quality_judge.py
#
# What this file does: scores every generated record (from step 2) on
# 5 criteria, 1-5 each, using a DIFFERENT model than whichever one
# generated it (see _select_judge_model) so the generator never grades
# its own homework. All 5 scores must be >=3 to pass. This is the
# source of the t-test statistics discussed in the Q&A prep doc.
#
# See also: documents/reports/supervisor/defense_code_navigation.md
# ============================================================

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
from src.data_pipeline.generation.gemini_auth import GeminiAuthSession
from src.data_pipeline.generation.prompts import build_judge_prompt


CLAUDE_MODEL = "claude-sonnet-4-6"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
OPENAI_COMPATIBLE_JUDGE_KEY = "openai-compatible"
JUDGE_PROGRESS_INTERVAL = 25
JUDGE_MAX_TOKENS = 260   # judge only outputs 5 small integer scores + a short reason string — doesn't need a big budget like generation does


def _extract_json_object(text: str) -> dict[str, Any]:
    # Same defensive-parsing idea as generator.py's _load_json_payload
    # (step 2) but simpler: the judge always returns ONE JSON object (not
    # an array of records), so this only needs to find the outermost
    # {...} span, after stripping an optional markdown code fence first.
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
    """
    Per-record judge scores and pass decision.

    THE 5 CRITERIA, each scored 1-5 by the judge LLM (this is the exact
    rubric — good to know cold if asked "what does quality judging actually
    check"):
      - realism: does this read like a real Vietnamese scam/legit message,
        not generic/templated LLM prose?
      - label_correctness: does the message content actually match its
        assigned threat_class label?
      - code_switch_naturalness: Vietnamese scam texts often mix in English
        /numeric/brand tokens naturally (e.g. "OTP", "Zalo", bank names) —
        does the mixing read naturally, not awkwardly inserted?
      - risk_tier_correctness: does the assigned risk_tier (benign/
        suspicious/high-risk) actually match how dangerous the message
        content is?
      - suspicious_span_accuracy: do the suspicious_spans genuinely appear
        in and support the message (early echo of the same grounding
        principle step 9's cue_span_is_grounded() enforces at runtime —
        evidence has to be real, checked here even at DATA-GENERATION time,
        not just at inference time)?
    Field(ge=1, le=5) on every score is a Pydantic constraint — if the judge
    model returns e.g. 0 or 7 (out of its stated 1-5 range), construction of
    this object raises immediately rather than silently accepting a garbage
    score.
    """

    realism: int = Field(ge=1, le=5)
    label_correctness: int = Field(ge=1, le=5)
    code_switch_naturalness: int = Field(ge=1, le=5)
    risk_tier_correctness: int = Field(ge=1, le=5)
    suspicious_span_accuracy: int = Field(ge=1, le=5)
    pass_verdict: bool
    reason: str


class QualityStats(BaseModel):
    """
    Aggregated quality statistics for a judged batch — this is the object
    that ultimately feeds the pass-rate and per-criterion average numbers
    reported in the thesis/report, and the population these per-record
    scores are drawn from is what the report's t-test analysis runs over
    (comparing score distributions, e.g. across providers or batches).
    """

    total: int
    passed: int
    failed: int
    pass_rate: float
    avg_realism: float
    avg_label_correctness: float
    avg_code_switch_naturalness: float
    avg_risk_tier_correctness: float = 0.0
    avg_suspicious_span_accuracy: float = 0.0


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
        self.openai_compatible_base_url = self.settings.openai_compatible_base_url.rstrip("/")
        self.openai_compatible_api_key = self.settings.openai_compatible_api_key
        self.openai_compatible_model = self.settings.openai_compatible_model
        # judge_model: an optional FORCE override. Left None (the normal
        # case), _select_judge_model below picks automatically based on
        # which provider generated the record — that automatic cross-model
        # selection is the whole point of this class, so this override
        # exists mainly for testing/debugging a specific judge in isolation.
        self.judge_model = judge_model
        self.anthropic_client = anthropic_client
        self.http_client = http_client or httpx.Client(timeout=60)
        self.gemini_session = GeminiAuthSession(self.settings)

    def judge_record(self, record: dict[str, Any]) -> JudgeVerdict:
        """Judge a single dataset record and return its verdict."""
        # build_judge_prompt hands the judge model everything about the
        # record EXCEPT which provider generated it — the judge only ever
        # sees the record's content (text/label/risk_tier/spans/
        # explanation), never "this was written by Claude" or similar.
        # That's what keeps the judging honest: it's scored purely on
        # content quality, with no way to be biased for or against a
        # particular generator.
        prompt = build_judge_prompt(
            record_text=record["text"],
            record_label=record["label"],
            record_risk_tier=record["risk_tier"],
            record_suspicious_spans=record.get("suspicious_spans", []),
            record_explanation=record["xai_explanation"],
        )
        # THIS line is the "different model than the generator" guarantee
        # in code: record.get("source") tells us WHICH provider produced
        # this record (stamped back in _finalize_records, step 2), and
        # _select_judge_model deliberately routes to a DIFFERENT provider
        # for judging. This is the direct answer to "how do you know the
        # judge isn't just rubber-stamping its own generation" — it
        # structurally can't be judging its own output, by construction.
        model = self._select_judge_model(record.get("source"))
        result = _extract_json_object(self._call_judge(prompt, model))
        # Pass threshold: ALL FIVE criteria must independently score >= 3
        # (out of 5). Not an average — a single weak criterion (e.g.
        # realism=5 but suspicious_span_accuracy=2) fails the whole record,
        # even if the average would look fine. This is a conjunction
        # (`all(...)`), a deliberately strict gate: a record that nails 4
        # criteria but fabricates its evidence spans should NOT pass, and
        # averaging would have let it slip through.
        pass_verdict = all(
            result.get(metric, 0) >= 3
            for metric in (
                "realism",
                "label_correctness",
                "code_switch_naturalness",
                "risk_tier_correctness",
                "suspicious_span_accuracy",
            )
        )
        return JudgeVerdict(
            realism=result["realism"],
            label_correctness=result["label_correctness"],
            code_switch_naturalness=result["code_switch_naturalness"],
            risk_tier_correctness=result["risk_tier_correctness"],
            suspicious_span_accuracy=result["suspicious_span_accuracy"],
            pass_verdict=pass_verdict,
            reason=result.get("reason", ""),
        )

    def judge_batch(
        self,
        records: list[dict[str, Any]],
        progress_callback: Callable[[str], None] | None = None,
    ) -> list[tuple[dict[str, Any], JudgeVerdict]]:
        """Judge a batch of records one by one."""
        # Deliberately sequential (no thread pool here, unlike generator.py's
        # parallel option) — judging is comparatively cheap per call
        # (JUDGE_MAX_TOKENS=260, tiny compared to generation's ~1400-2200),
        # so the added complexity of parallelizing wasn't worth it for this
        # stage.
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
        # Records that failed even ONE criterion (see pass_verdict logic
        # above) are simply excluded here — they don't get "fixed" or
        # retried, just dropped from the corpus that continues on to
        # splitter.py (step 4). Failed records + verdicts still count
        # toward QualityStats though, so the reported pass_rate reflects
        # the TRUE fraction of generated output that was usable, not just
        # the fraction that made it to the final dataset.
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
            avg_risk_tier_correctness=(
                sum(verdict.risk_tier_correctness for verdict in verdicts) / max(len(verdicts), 1)
            ),
            avg_suspicious_span_accuracy=(
                sum(verdict.suspicious_span_accuracy for verdict in verdicts) / max(len(verdicts), 1)
            ),
        )
        return passed_records, stats

    def _openai_compatible_is_configured(self) -> bool:
        return bool(self.openai_compatible_base_url and self.openai_compatible_model)

    def _select_judge_model(self, source: str | None) -> str:
        """
        THE CROSS-MODEL ROUTING TABLE. Read this as: "if the record was
        generated BY provider X, judge it with a DIFFERENT provider Y."
        Claude-generated → judged by Gemini (if available). Gemini- or
        OpenRouter-generated → judged by Claude. The openai-compatible
        source similarly prefers whichever of Gemini/Claude is available
        rather than re-using the same self-hosted endpoint that generated
        it. The trailing fallback block (checked only if none of the
        source-specific rules matched or were available) just picks
        whatever's configured, in a fixed preference order — this only
        gets hit in edge cases like an unrecognized `source` value, and
        even then it still tries hard to prefer Gemini/Claude over an
        openai-compatible judge, since those two are the "real" judge
        options this project is designed around.
        """
        if self.judge_model:
            return self.judge_model
        if source == "synthetic_claude" and self.gemini_session.is_configured():
            return GEMINI_MODEL
        if source in {"synthetic_gemini", "synthetic_openrouter"} and self.anthropic_client:
            return CLAUDE_MODEL
        # openai-compatible source: prefer a different model for cross-judging
        if source == "synthetic_openai_compatible":
            if self.gemini_session.is_configured():
                return GEMINI_MODEL
            if self.anthropic_client or self.anthropic_key:
                return CLAUDE_MODEL
        if self.gemini_session.is_configured():
            return GEMINI_MODEL
        if self.anthropic_client or self.anthropic_key:
            return CLAUDE_MODEL
        if self._openai_compatible_is_configured():
            return OPENAI_COMPATIBLE_JUDGE_KEY
        raise ValueError("No judge API key configured")

    def _call_judge(self, prompt: str, model: str) -> str:
        # temperature=0.3 here (not generation's 0.7/0.9) — judging wants
        # consistent, repeatable scoring, not creative variety. Still not
        # 0.0 (fully deterministic) because a little slack is intentionally
        # left for the judge to weigh borderline cases, rather than being
        # rigidly literal.
        if model == GEMINI_MODEL and self.gemini_session.is_configured():
            try:
                response = self.gemini_session.post_generate_content(
                    self.http_client,
                    GEMINI_MODEL,
                    prompt,
                    temperature=0.3,
                    max_output_tokens=JUDGE_MAX_TOKENS,
                )
                if hasattr(response, "raise_for_status"):
                    response.raise_for_status()
                return response.json()["candidates"][0]["content"]["parts"][0]["text"]
            except httpx.HTTPError:
                # Gemini judge unreachable — fall back to Claude rather
                # than fail the whole judging pass, but ONLY if a Claude
                # credential actually exists; otherwise let the error
                # surface (nothing left to fall back to).
                if self.anthropic_client is None and not self.anthropic_key:
                    raise
                return self._call_judge(prompt, CLAUDE_MODEL)
        if model == CLAUDE_MODEL and self.anthropic_client:
            response = self.anthropic_client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=JUDGE_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        if model == CLAUDE_MODEL and self.anthropic_client is None and self.anthropic_key:
            # Same lazy-client-construction pattern as generator.py's
            # _call_claude — build the SDK client only the first time it's
            # actually needed.
            if anthropic is None:
                raise ValueError("No judge API key configured")
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_key)
            response = self.anthropic_client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=JUDGE_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        if model == OPENAI_COMPATIBLE_JUDGE_KEY and self._openai_compatible_is_configured():
            headers = {}
            if self.openai_compatible_api_key:
                headers["Authorization"] = f"Bearer {self.openai_compatible_api_key}"
            response = self.http_client.post(
                f"{self.openai_compatible_base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.openai_compatible_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": JUDGE_MAX_TOKENS,
                },
            )
            if hasattr(response, "raise_for_status"):
                response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        raise ValueError("No judge API key configured")
