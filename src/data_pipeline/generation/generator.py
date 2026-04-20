"""Tiered LLM generation pipeline for synthetic Vietnamese scam data."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import httpx

try:
    import anthropic
except ImportError:  # pragma: no cover - exercised via lazy provider fallback
    anthropic = None

from src.config.settings import Settings, get_settings
from src.data_pipeline.generation.prompts import (
    THREAT_CLASSES,
    build_benign_prompt,
    build_bulk_prompt,
    build_complex_prompt,
)
from src.data_pipeline.schemas import DatasetRecord, SeedRecord


CLAUDE_MODEL = "claude-sonnet-4-20250514"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _strip_code_fence(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text.strip(), flags=re.DOTALL)
    return fenced.group(1) if fenced else text.strip()


def _load_json_payload(text: str) -> Any:
    cleaned = _strip_code_fence(text)
    candidates = [cleaned]
    for opening, closing in (("[", "]"), ("{", "}")):
        start = cleaned.find(opening)
        end = cleaned.rfind(closing)
        if start != -1 and end != -1 and end > start:
            candidates.append(cleaned[start : end + 1])
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise ValueError("LLM response did not contain valid JSON")


class TieredGenerator:
    """Generate DatasetRecord-compatible synthetic samples using multiple providers."""

    def __init__(
        self,
        settings: Settings | None = None,
        anthropic_client: Any | None = None,
        http_client: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.anthropic_api_key = self.settings.anthropic_api_key
        self.gemini_api_key = self.settings.gemini_api_key
        self.openrouter_api_key = self.settings.openrouter_api_key
        self.data_dir = self.settings.data_dir
        self.anthropic_client = anthropic_client
        self.http_client = http_client or httpx.Client(timeout=60)

    def generate_complex(
        self,
        seed: SeedRecord,
        threat_class: str,
        num_variants: int = 3,
    ) -> list[dict[str, Any]]:
        """Generate high-quality complex examples with Claude."""
        if not self.anthropic_client:
            raise ValueError("Anthropic API key is required for complex generation")
        prompt = self._build_generation_prompt(seed, threat_class, count=num_variants, bulk=False)
        records = self._call_claude(prompt)
        return self._finalize_records(records, seed, threat_class, "synthetic_claude")

    def generate_bulk(
        self,
        seed: SeedRecord,
        threat_class: str,
        count: int = 10,
    ) -> list[dict[str, Any]]:
        """Generate higher-volume variations with Gemini or OpenRouter."""
        prompt = self._build_generation_prompt(seed, threat_class, count=count, bulk=True)
        if self.gemini_api_key:
            records = self._call_gemini(prompt)
            return self._finalize_records(records, seed, threat_class, "synthetic_gemini")
        if self.openrouter_api_key:
            records = self._call_openrouter(prompt)
            return self._finalize_records(records, seed, threat_class, "synthetic_openrouter")
        raise ValueError("No bulk API key configured")

    def generate_dataset(
        self,
        seeds: list[SeedRecord],
        target_count: int = 2500,
    ) -> list[dict[str, Any]]:
        """Generate a roughly balanced synthetic dataset across all threat classes."""
        if not seeds:
            raise ValueError("At least one seed is required")

        class_targets = self._build_class_targets(target_count)
        generated: list[dict[str, Any]] = []

        for index, threat_class in enumerate(THREAT_CLASSES):
            seed = seeds[index % len(seeds)]
            class_target = class_targets[threat_class]
            complex_target = min(class_target, max(1, round(class_target * 0.2))) if class_target else 0
            bulk_target = max(class_target - complex_target, 0)

            class_records: list[dict[str, Any]] = []
            if complex_target:
                class_records.extend(
                    self.generate_complex(seed, threat_class, num_variants=complex_target)[:complex_target]
                )
            if bulk_target:
                class_records.extend(self.generate_bulk(seed, threat_class, count=bulk_target)[:bulk_target])

            generated.extend(class_records[:class_target])

        return generated[:target_count]

    def compare_models(self, seed: SeedRecord, threat_class: str) -> dict[str, dict[str, Any]]:
        """Run a small pilot generation pass across available providers."""
        prompt = self._build_generation_prompt(seed, threat_class, count=1, bulk=False)
        comparison: dict[str, dict[str, Any]] = {}

        if self.anthropic_client:
            claude_records = self._call_claude(prompt)
            comparison["claude"] = self._summarize_provider("claude", claude_records, CLAUDE_MODEL)
        else:
            comparison["claude"] = {"available": False, "notes": "Anthropic API key not configured"}

        if self.gemini_api_key:
            gemini_records = self._call_gemini(self._build_generation_prompt(seed, threat_class, count=1, bulk=True))
            comparison["gemini"] = self._summarize_provider("gemini", gemini_records, GEMINI_MODEL)
        else:
            comparison["gemini"] = {"available": False, "notes": "Gemini API key not configured"}

        if self.openrouter_api_key:
            openrouter_records = self._call_openrouter(
                self._build_generation_prompt(seed, threat_class, count=1, bulk=True)
            )
            comparison["openrouter"] = self._summarize_provider(
                "openrouter",
                openrouter_records,
                "openrouter-default",
            )
        else:
            comparison["openrouter"] = {"available": False, "notes": "OpenRouter API key not configured"}

        return comparison

    def save_generated(
        self,
        records: list[dict[str, Any]],
        output_path: Path | None = None,
    ) -> Path:
        """Validate and persist generated records as JSONL."""
        destination = output_path or (self.data_dir / "synthetic" / "generated.jsonl")
        destination.parent.mkdir(parents=True, exist_ok=True)

        validated_records = [DatasetRecord.model_validate(record) for record in records]
        with destination.open("w", encoding="utf-8") as handle:
            for record in validated_records:
                handle.write(record.model_dump_json() + "\n")
        return destination

    def _build_generation_prompt(
        self,
        seed: SeedRecord,
        threat_class: str,
        count: int,
        bulk: bool,
    ) -> str:
        if threat_class == "benign":
            return build_benign_prompt(num_variants=count)
        if bulk:
            return build_bulk_prompt(seed.text, threat_class, count=count)
        return build_complex_prompt(seed.text, threat_class, num_variants=count)

    def _call_claude(self, prompt: str) -> list[dict[str, Any]]:
        if self.anthropic_client is None:
            if anthropic is None or not self.anthropic_api_key:
                raise ValueError("Anthropic API key is required for complex generation")
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        response = self.anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            temperature=0.7,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        payload = _load_json_payload(text)
        if not isinstance(payload, list):
            raise ValueError("Claude response must be a JSON array")
        return payload

    def _call_gemini(self, prompt: str) -> list[dict[str, Any]]:
        response = self.http_client.post(
            GEMINI_URL,
            params={"key": self.gemini_api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.9, "maxOutputTokens": 4000},
            },
        )
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        payload = _load_json_payload(text)
        if not isinstance(payload, list):
            raise ValueError("Gemini response must be a JSON array")
        return payload

    def _call_openrouter(self, prompt: str) -> list[dict[str, Any]]:
        response = self.http_client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {self.openrouter_api_key}"},
            json={
                "model": "openai/gpt-4.1-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.9,
                "max_tokens": 4000,
            },
        )
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]
        payload = _load_json_payload(text)
        if not isinstance(payload, list):
            raise ValueError("OpenRouter response must be a JSON array")
        return payload

    def _finalize_records(
        self,
        records: list[dict[str, Any]],
        seed: SeedRecord,
        threat_class: str,
        source: str,
    ) -> list[dict[str, Any]]:
        seed_id = self._derive_seed_id(seed)
        finalized: list[dict[str, Any]] = []
        for record in records:
            payload = dict(record)
            payload["label"] = payload.get("label", threat_class)
            payload["risk_tier"] = payload.get("risk_tier", "suspicious")
            payload["suspicious_spans"] = payload.get("suspicious_spans", [])
            payload["source"] = source
            payload["seed_id"] = seed_id
            validated = DatasetRecord.model_validate(payload)
            finalized.append(validated.model_dump())
        return finalized

    def _derive_seed_id(self, seed: SeedRecord) -> str:
        fingerprint = hashlib.sha256(f"{seed.source_url}|{seed.text}".encode("utf-8")).hexdigest()
        return f"seed_{fingerprint[:12]}"

    def _build_class_targets(self, target_count: int) -> dict[str, int]:
        base_count = target_count // len(THREAT_CLASSES)
        remainder = target_count % len(THREAT_CLASSES)
        targets: dict[str, int] = {}
        for index, threat_class in enumerate(THREAT_CLASSES):
            targets[threat_class] = base_count + (1 if index < remainder else 0)
        return targets

    def _summarize_provider(self, provider: str, records: list[dict[str, Any]], model: str) -> dict[str, Any]:
        text_lengths = [len(record.get("text", "")) for record in records]
        explanation_lengths = [len(record.get("xai_explanation", "")) for record in records]
        return {
            "available": True,
            "provider": provider,
            "model": model,
            "records": len(records),
            "avg_text_length": round(sum(text_lengths) / max(len(text_lengths), 1), 2),
            "avg_explanation_length": round(
                sum(explanation_lengths) / max(len(explanation_lengths), 1),
                2,
            ),
            "notes": f"Pilot output captured for {provider} before large-scale generation.",
        }