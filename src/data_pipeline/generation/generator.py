"""Tiered LLM generation pipeline for synthetic Vietnamese scam data."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import re
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

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


CLAUDE_MODEL = "claude-sonnet-4-6"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
CLAUDE_DEFAULT_MAX_TOKENS = 2000
CLAUDE_LARGE_BATCH_MAX_TOKENS = 4096
COMPLEX_BATCH_SIZE = 5
BULK_BATCH_SIZE = 10
MAX_EMPTY_BATCHES = 2


@dataclass(frozen=True)
class BatchSpec:
    order: int
    threat_class: str
    batch_type: str
    batch_index: int
    count: int
    seed: SeedRecord


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


def _normalize_risk_tier(value: Any) -> str:
    normalized = str(value or "suspicious").strip().casefold().replace("_", "-")
    aliases = {
        "benign": "benign",
        "safe": "benign",
        "low": "benign",
        "suspicious": "suspicious",
        "warning": "suspicious",
        "medium": "suspicious",
        "high-risk": "high-risk",
        "high risk": "high-risk",
        "high": "high-risk",
        "critical": "high-risk",
    }
    return aliases.get(normalized, "suspicious")


class TieredGenerator:
    """Generate DatasetRecord-compatible synthetic samples using multiple providers."""

    def __init__(
        self,
        settings: Settings | None = None,
        anthropic_client: Any | None = None,
        http_client: Any | None = None,
        bulk_provider: str = "auto",
    ) -> None:
        self.settings = settings or get_settings()
        self.anthropic_api_key = self.settings.anthropic_api_key
        self.gemini_api_key = self.settings.gemini_api_key
        self.openrouter_api_key = self.settings.openrouter_api_key
        self.data_dir = self.settings.data_dir
        self.anthropic_client = anthropic_client
        self.http_client = http_client or httpx.Client(timeout=60)
        self.bulk_provider = bulk_provider

    def generate_complex(
        self,
        seed: SeedRecord,
        threat_class: str,
        num_variants: int = 3,
    ) -> list[dict[str, Any]]:
        """Generate high-quality complex examples with Claude."""
        if self.anthropic_client is None and not self.anthropic_api_key:
            raise ValueError("Anthropic API key is required for complex generation")
        prompt = self._build_generation_prompt(seed, threat_class, count=num_variants, bulk=False)
        max_tokens = CLAUDE_LARGE_BATCH_MAX_TOKENS if num_variants > 3 else CLAUDE_DEFAULT_MAX_TOKENS
        records = self._call_claude(prompt, max_tokens=max_tokens)
        return self._finalize_records(records, seed, threat_class, "synthetic_claude")

    def generate_bulk(
        self,
        seed: SeedRecord,
        threat_class: str,
        count: int = 10,
    ) -> list[dict[str, Any]]:
        """Generate higher-volume variations with Gemini or OpenRouter."""
        prompt = self._build_generation_prompt(seed, threat_class, count=count, bulk=True)
        if self.bulk_provider not in {"auto", "gemini", "openrouter", "claude"}:
            raise ValueError(f"Unsupported bulk provider: {self.bulk_provider}")

        if self.bulk_provider in {"auto", "gemini"} and self.gemini_api_key:
            try:
                records = self._call_gemini(prompt)
                return self._finalize_records(records, seed, threat_class, "synthetic_gemini")
            except httpx.HTTPError:
                if not self.openrouter_api_key and not self.anthropic_api_key and self.anthropic_client is None:
                    raise
                if self.bulk_provider == "gemini":
                    raise
        if self.bulk_provider in {"auto", "openrouter"} and self.openrouter_api_key:
            try:
                records = self._call_openrouter(prompt)
                return self._finalize_records(records, seed, threat_class, "synthetic_openrouter")
            except httpx.HTTPError:
                if not self.anthropic_api_key and self.anthropic_client is None:
                    raise
                if self.bulk_provider == "openrouter":
                    raise
        if self.bulk_provider in {"auto", "claude"} and (self.anthropic_api_key or self.anthropic_client is not None):
            records = self._call_claude(prompt, max_tokens=CLAUDE_LARGE_BATCH_MAX_TOKENS)
            return self._finalize_records(records, seed, threat_class, "synthetic_claude")
        raise ValueError("No bulk API key configured")

    def generate_dataset(
        self,
        seeds: list[SeedRecord],
        target_count: int = 2500,
        max_parallel_batches: int = 1,
        checkpoint_path: Path | None = None,
        partial_output_path: Path | None = None,
        resume: bool = False,
        progress_callback: Callable[[str], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate a roughly balanced synthetic dataset across all threat classes."""
        if not seeds:
            raise ValueError("At least one seed is required")
        if max_parallel_batches < 1:
            raise ValueError("max_parallel_batches must be at least 1")

        class_targets = self._build_class_targets(target_count)
        completed_batches, restored_records = self._prepare_resume_state(
            checkpoint_path=checkpoint_path,
            partial_output_path=partial_output_path,
            resume=resume,
            progress_callback=progress_callback,
        )
        work_items = self._build_batch_specs(
            seeds=seeds,
            class_targets=class_targets,
            completed_batch_keys=set(completed_batches),
        )
        total_batches = len(completed_batches) + len(work_items)

        if work_items:
            if max_parallel_batches > 1:
                self._emit_progress(
                    progress_callback,
                    f"Starting {len(work_items)} generation batches with {max_parallel_batches} workers.",
                )
            restored_records.extend(
                self._execute_batch_specs(
                    work_items=work_items,
                    checkpoint_path=checkpoint_path,
                    partial_output_path=partial_output_path,
                    max_parallel_batches=max_parallel_batches,
                    initial_completed=len(completed_batches),
                    total_batches=total_batches,
                    progress_callback=progress_callback,
                )
            )

        generated: list[dict[str, Any]] = []
        for threat_class in THREAT_CLASSES:
            class_records = [record for record in restored_records if record.get("label") == threat_class]
            generated.extend(class_records[: class_targets[threat_class]])

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

    def _call_claude(
        self,
        prompt: str,
        max_tokens: int = CLAUDE_DEFAULT_MAX_TOKENS,
    ) -> list[dict[str, Any]]:
        if self.anthropic_client is None:
            if anthropic is None or not self.anthropic_api_key:
                raise ValueError("Anthropic API key is required for complex generation")
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        response = self.anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            temperature=0.7,
            max_tokens=max_tokens,
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
            payload["risk_tier"] = _normalize_risk_tier(payload.get("risk_tier", "suspicious"))
            payload["suspicious_spans"] = payload.get("suspicious_spans", [])
            payload["source"] = source
            payload["seed_id"] = seed_id
            validated = DatasetRecord.model_validate(payload)
            finalized.append(validated.model_dump())
        return finalized

    def _derive_seed_id(self, seed: SeedRecord) -> str:
        fingerprint = hashlib.sha256(f"{seed.source_url}|{seed.text}".encode("utf-8")).hexdigest()
        return f"seed_{fingerprint[:12]}"

    def _prepare_resume_state(
        self,
        checkpoint_path: Path | None,
        partial_output_path: Path | None,
        resume: bool,
        progress_callback: Callable[[str], None] | None,
    ) -> tuple[dict[str, tuple[int, list[dict[str, Any]]]], list[dict[str, Any]]]:
        if not resume:
            for artifact_path in (checkpoint_path, partial_output_path):
                if artifact_path and artifact_path.exists():
                    artifact_path.unlink()
            return {}, []

        completed_batches = self._load_checkpoint(checkpoint_path)
        restored_records: list[dict[str, Any]] = []
        for _, records in sorted(completed_batches.values(), key=lambda item: item[0]):
            restored_records.extend(records)

        if completed_batches:
            self._emit_progress(
                progress_callback,
                f"Resuming from {len(completed_batches)} completed batches and {len(restored_records)} generated records.",
            )
            if partial_output_path and not partial_output_path.exists():
                self._append_records(partial_output_path, restored_records)

        return completed_batches, restored_records

    def _build_batch_specs(
        self,
        seeds: list[SeedRecord],
        class_targets: dict[str, int],
        completed_batch_keys: set[str],
    ) -> list[BatchSpec]:
        specs: list[BatchSpec] = []
        order = 0

        for index, threat_class in enumerate(THREAT_CLASSES):
            seed = seeds[index % len(seeds)]
            class_target = class_targets[threat_class]
            complex_target = min(class_target, max(1, round(class_target * 0.2))) if class_target else 0
            bulk_target = max(class_target - complex_target, 0)

            for batch_type, target, batch_size in (
                ("complex", complex_target, COMPLEX_BATCH_SIZE),
                ("bulk", bulk_target, BULK_BATCH_SIZE),
            ):
                remaining = target
                batch_index = 0
                while remaining > 0:
                    requested = min(batch_size, remaining)
                    spec = BatchSpec(
                        order=order,
                        threat_class=threat_class,
                        batch_type=batch_type,
                        batch_index=batch_index,
                        count=requested,
                        seed=seed,
                    )
                    order += 1
                    if self._batch_key(spec) not in completed_batch_keys:
                        specs.append(spec)
                    remaining -= requested
                    batch_index += 1

        return specs

    def _execute_batch_specs(
        self,
        work_items: list[BatchSpec],
        checkpoint_path: Path | None,
        partial_output_path: Path | None,
        max_parallel_batches: int,
        initial_completed: int,
        total_batches: int,
        progress_callback: Callable[[str], None] | None,
    ) -> list[dict[str, Any]]:
        if max_parallel_batches <= 1:
            return self._execute_batch_specs_sequential(
                work_items=work_items,
                checkpoint_path=checkpoint_path,
                partial_output_path=partial_output_path,
                initial_completed=initial_completed,
                total_batches=total_batches,
                progress_callback=progress_callback,
            )
        return self._execute_batch_specs_parallel(
            work_items=work_items,
            checkpoint_path=checkpoint_path,
            partial_output_path=partial_output_path,
            max_parallel_batches=max_parallel_batches,
            initial_completed=initial_completed,
            total_batches=total_batches,
            progress_callback=progress_callback,
        )

    def _execute_batch_specs_sequential(
        self,
        work_items: list[BatchSpec],
        checkpoint_path: Path | None,
        partial_output_path: Path | None,
        initial_completed: int,
        total_batches: int,
        progress_callback: Callable[[str], None] | None,
    ) -> list[dict[str, Any]]:
        completed = initial_completed
        records: list[dict[str, Any]] = []

        for spec in work_items:
            self._emit_progress(
                progress_callback,
                f"[generate {completed + 1}/{total_batches}] requesting {spec.count} {spec.threat_class} {spec.batch_type} records",
            )
            batch_records = self._run_batch_spec(spec)
            self._persist_completed_batch(
                spec=spec,
                records=batch_records,
                checkpoint_path=checkpoint_path,
                partial_output_path=partial_output_path,
            )
            records.extend(batch_records)
            completed += 1
            self._emit_progress(
                progress_callback,
                f"[generate {completed}/{total_batches}] saved {len(batch_records)} {spec.threat_class} {spec.batch_type} records",
            )

        return records

    def _execute_batch_specs_parallel(
        self,
        work_items: list[BatchSpec],
        checkpoint_path: Path | None,
        partial_output_path: Path | None,
        max_parallel_batches: int,
        initial_completed: int,
        total_batches: int,
        progress_callback: Callable[[str], None] | None,
    ) -> list[dict[str, Any]]:
        lock = threading.Lock()
        completed = {"count": initial_completed}
        results_by_order: dict[int, list[dict[str, Any]]] = {}

        def worker(spec: BatchSpec) -> tuple[int, list[dict[str, Any]]]:
            batch_records = self._run_batch_spec(spec, use_worker_clone=True)
            with lock:
                self._persist_completed_batch(
                    spec=spec,
                    records=batch_records,
                    checkpoint_path=checkpoint_path,
                    partial_output_path=partial_output_path,
                )
                completed["count"] += 1
                self._emit_progress(
                    progress_callback,
                    f"[generate {completed['count']}/{total_batches}] saved {len(batch_records)} {spec.threat_class} {spec.batch_type} records",
                )
            return spec.order, batch_records

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel_batches) as executor:
                futures = [executor.submit(worker, spec) for spec in work_items]
                for future in concurrent.futures.as_completed(futures):
                    order, batch_records = future.result()
                    results_by_order[order] = batch_records
        except KeyboardInterrupt:
            self._emit_progress(
                progress_callback,
                "Interrupted during generation. Completed batches were checkpointed and can be resumed with --resume.",
            )
            raise

        records: list[dict[str, Any]] = []
        for spec in sorted(work_items, key=lambda item: item.order):
            records.extend(results_by_order.get(spec.order, []))
        return records

    def _run_batch_spec(self, spec: BatchSpec, use_worker_clone: bool = False) -> list[dict[str, Any]]:
        generator = self
        if use_worker_clone:
            generator = TieredGenerator(settings=self.settings, bulk_provider=self.bulk_provider)

        if spec.batch_type == "complex":
            return generator.generate_complex(spec.seed, spec.threat_class, num_variants=spec.count)
        return generator.generate_bulk(spec.seed, spec.threat_class, count=spec.count)

    def _persist_completed_batch(
        self,
        spec: BatchSpec,
        records: list[dict[str, Any]],
        checkpoint_path: Path | None,
        partial_output_path: Path | None,
    ) -> None:
        if partial_output_path:
            self._append_records(partial_output_path, records)
        if checkpoint_path:
            self._save_batch_checkpoint(checkpoint_path, spec, records)

    def _append_records(self, destination: Path, records: list[dict[str, Any]]) -> None:
        if not records:
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("a", encoding="utf-8") as handle:
            for record in records:
                validated = DatasetRecord.model_validate(record)
                handle.write(validated.model_dump_json() + "\n")

    def _load_checkpoint(self, path: Path | None) -> dict[str, tuple[int, list[dict[str, Any]]]]:
        if path is None or not path.exists():
            return {}

        completed: dict[str, tuple[int, list[dict[str, Any]]]] = {}
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                records = [DatasetRecord.model_validate(record).model_dump() for record in entry.get("records", [])]
                completed[entry["batch_key"]] = (entry["order"], records)
        return completed

    def _save_batch_checkpoint(self, path: Path, spec: BatchSpec, records: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "batch_key": self._batch_key(spec),
            "order": spec.order,
            "threat_class": spec.threat_class,
            "batch_type": spec.batch_type,
            "batch_index": spec.batch_index,
            "requested_count": spec.count,
            "returned_count": len(records),
            "provider": records[0].get("source") if records else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "records": records,
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _batch_key(self, spec: BatchSpec) -> str:
        return f"{spec.threat_class}:{spec.batch_type}:{spec.batch_index}"

    def _emit_progress(
        self,
        progress_callback: Callable[[str], None] | None,
        message: str,
    ) -> None:
        if progress_callback is not None:
            progress_callback(message)
        else:  # pragma: no cover - default live CLI behavior uses the callback path
            print(message, file=sys.stderr, flush=True)

    def _collect_records(
        self,
        target: int,
        batch_size: int,
        generate: Callable[[int], list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        empty_batches = 0

        while len(collected) < target and empty_batches < MAX_EMPTY_BATCHES:
            remaining = target - len(collected)
            requested = min(batch_size, remaining)
            batch = generate(requested)[:requested]
            if not batch:
                empty_batches += 1
                continue
            collected.extend(batch)
            empty_batches = 0

        return collected[:target]

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