# ============================================================
# STEP 2 of 10 — Generate Synthetic Scam Messages From Seeds
# ============================================================
# Canonical source (this numbered copy exists ONLY for defense-day
# navigation — it is not a second implementation and is not imported
# by anything): src/data_pipeline/generation/generator.py
#
# What this file does: TieredGenerator takes the real seeds from step 1
# and drives an LLM provider (Claude by default, with Gemini/OpenRouter/
# DeepSeek/OpenAI-compatible fallbacks) to generate variations at scale.
# Checkpointed so a long generation run can be resumed. Output goes to
# data/synthetic/generated.jsonl, ready for the quality judge in step 3.
#
# See also: documents/reports/supervisor/defense_code_navigation.md
# ============================================================

"""Tiered LLM generation pipeline for synthetic Vietnamese scam data."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import re
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import httpx

# `anthropic` (Claude's own SDK) is imported defensively, not required. Why:
# this class supports FIVE possible LLM providers (Claude, Gemini,
# OpenRouter, DeepSeek, any generic OpenAI-compatible endpoint), and only
# Claude needs its own SDK object — the other four are called with plain
# httpx HTTP requests. If `anthropic` isn't installed, the whole module
# should still import fine; you'd just get a clear ValueError later if you
# actually try to use the Claude path without the package present.
try:
    import anthropic
except ImportError:  # pragma: no cover - exercised via lazy provider fallback
    anthropic = None

from src.config.settings import Settings, get_settings
from src.data_pipeline.generation.gemini_auth import GeminiAuthSession
from src.data_pipeline.generation.prompts import (
    THREAT_CLASSES,
    build_benign_prompt,
    build_bulk_prompt,
    build_complex_prompt,
)
from src.data_pipeline.schemas import DatasetRecord, SeedRecord


# WHY MULTIPLE PROVIDERS AT ALL, instead of just calling Claude 2500 times:
# this is the "tiered" in TieredGenerator. Complex, nuanced examples (small
# batches, higher reasoning needed — e.g. subtle social-engineering variants)
# go to Claude, which is the highest quality but also the most expensive per
# call. Bulk, higher-volume, more repetitive variations go to a cheaper/
# faster provider (Gemini by default, with OpenRouter/DeepSeek as further
# fallbacks) so the dataset can reach thousands of rows without the whole
# generation run being Claude-API-cost-prohibitive. This is a cost/quality
# tradeoff made explicitly, not an accident of what API key happened to be
# configured.
CLAUDE_MODEL = "claude-sonnet-4-6"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
OPENAI_COMPATIBLE_SOURCE = "synthetic_openai_compatible"
CLAUDE_DEFAULT_MAX_TOKENS = 1400
CLAUDE_LARGE_BATCH_MAX_TOKENS = 2200
BULK_PROVIDER_MAX_TOKENS = 2200
COMPLEX_BATCH_SIZE = 3   # small batches for the expensive, high-quality Claude path
BULK_BATCH_SIZE = 5      # bigger batches for the cheap/fast bulk providers
MAX_EMPTY_BATCHES = 2
CHECKPOINT_KEEP_COUNT = 5   # only the last 5 checkpoint files are kept on disk — old ones pruned
OPENAI_COMPATIBLE_CONNECT_TIMEOUT_SECONDS = 30.0
OPENAI_COMPATIBLE_READ_TIMEOUT_SECONDS = 300.0   # generous read timeout: local/self-hosted OpenAI-compatible servers can be slow
OPENAI_COMPATIBLE_TIMEOUT_RETRIES = 3
OPENAI_COMPATIBLE_RETRY_BACKOFF_SECONDS = 2.0


@dataclass(frozen=True)
class BatchSpec:
    """
    One unit of generation work: "give me `count` examples of `threat_class`,
    generated via `batch_type` ('complex' or 'bulk'), seeded from `seed`."
    `order` preserves the original scheduling order so that when batches run
    in parallel (out of order) the final record list can still be
    reassembled deterministically. frozen=True because a BatchSpec is a
    plan, not mutable state — once built it should never be edited, only
    read by whichever worker executes it.
    """
    order: int
    threat_class: str
    batch_type: str
    batch_index: int
    count: int
    seed: SeedRecord


def _strip_code_fence(text: str) -> str:
    # LLMs (all 5 providers) very often wrap JSON output in a markdown code
    # fence even when explicitly told "return raw JSON only" — e.g.
    # ```json\n[...]\n```. This regex strips that fence off if present, or
    # returns the text unchanged (just stripped of whitespace) if it wasn't
    # fenced at all. DOTALL so `.` matches newlines — the JSON payload
    # itself is almost always multi-line.
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text.strip(), flags=re.DOTALL)
    return fenced.group(1) if fenced else text.strip()


def _load_json_payload(text: str) -> Any:
    """
    Best-effort JSON extraction from a raw LLM text response. This is
    defensive parsing, not naive `json.loads(text)`, because real LLM output
    is messy: it might have the fence handled above but STILL have leading
    chatter ("Here is the JSON you asked for:") or trailing commentary
    before/after the actual array. Strategy: try the cleaned text as-is
    first; if that fails, try slicing out just the substring between the
    first `[`/`{` and the last matching `]`/`}` — that recovers the JSON
    even if there's stray prose wrapped around it. Only raises if NONE of
    these candidates parse, which means the model genuinely didn't return
    usable JSON.
    """
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
    """
    LLMs are inconsistent about exactly which string they use for a given
    risk level, even when the prompt specifies the allowed values — one
    call might say "High Risk", another "critical", another "high_risk".
    This collapses every observed variant down to exactly one of the three
    canonical tiers the rest of this project uses: benign / suspicious /
    high-risk. Unknown/unrecognized values default to "suspicious" (the
    middle tier) rather than crashing — a safer default than silently
    calling something benign, and not so aggressive as auto-escalating
    everything unknown straight to high-risk.
    """
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


def _normalize_dataset_label(value: Any, default: str) -> str:
    """
    Same idea as _normalize_risk_tier but for the fine-grained threat-class
    label (bank_impersonation / zalo_social_engineering / task_scam /
    benign). Notice most of the alias keys here map to "benign" —
    that's because when generating BENIGN examples, the prompt
    (build_benign_prompt) asks for realistic legitimate message *types*
    ("transaction_confirmation", "otp_confirmation", "marketing_offer",
    etc.) for variety, but all of those still collapse to the single
    dataset label "benign" — the sub-type is just a generation-diversity
    hint, not a label the classifier is trained to predict. `default`
    (the threat_class this batch was generating for) is the fallback if the
    LLM's returned label string isn't recognized at all.
    """
    normalized = str(value or default).strip().casefold().replace("-", "_").replace(" ", "_")
    aliases = {
        "bank_impersonation": "bank_impersonation",
        "zalo_social_engineering": "zalo_social_engineering",
        "task_scam": "task_scam",
        "benign": "benign",
        "transaction_confirmation": "benign",
        "service_update": "benign",
        "otp_confirmation": "benign",
        "marketing_offer": "benign",
        "balance_alert": "benign",
        "account_statement": "benign",
        "bank_notification": "benign",
        "payment_confirmation": "benign",
        "transfer_confirmation": "benign",
    }
    return aliases.get(normalized, default)


class TieredGenerator:
    """Generate DatasetRecord-compatible synthetic samples using multiple providers."""

    def __init__(
        self,
        settings: Settings | None = None,
        anthropic_client: Any | None = None,
        http_client: Any | None = None,
        bulk_provider: str = "auto",
    ) -> None:
        # All API keys/config pulled from Settings (env-var backed, see
        # src/config/settings.py) — never hardcoded here. A missing key
        # just means that provider's methods will raise/be skipped later,
        # not a crash at construction time. That's deliberate: you should
        # be able to build a TieredGenerator with e.g. only a Gemini key
        # configured and it just works for generate_bulk, even with zero
        # Claude access.
        self.settings = settings or get_settings()
        self.anthropic_api_key = self.settings.anthropic_api_key
        self.gemini_api_key = self.settings.gemini_api_key
        self.openrouter_api_key = self.settings.openrouter_api_key
        self.deepseek_api_key = self.settings.deepseek_api_key
        self.openai_compatible_base_url = self.settings.openai_compatible_base_url.rstrip("/")
        self.openai_compatible_api_key = self.settings.openai_compatible_api_key
        self.openai_compatible_model = self.settings.openai_compatible_model
        self.data_dir = self.settings.data_dir
        # anthropic_client / http_client are injectable (not just built
        # internally) specifically so unit tests can pass in a fake/mock
        # client instead of making real network calls. If not injected,
        # http_client defaults to a real httpx.Client here.
        self.anthropic_client = anthropic_client
        self.http_client = http_client or httpx.Client(timeout=60)
        # bulk_provider: "auto" (try Gemini, then OpenRouter, then DeepSeek,
        # then Claude, in that cost-ascending order — see generate_bulk) or
        # a specific provider name to force. Forcing is mainly for the
        # compare_models() pilot / debugging a specific provider.
        self.bulk_provider = bulk_provider
        self.gemini_session = GeminiAuthSession(self.settings)

    def generate_complex(
        self,
        seed: SeedRecord,
        threat_class: str,
        num_variants: int = 3,
    ) -> list[dict[str, Any]]:
        """Generate high-quality complex examples with Claude."""
        # openai-compatible is checked FIRST here, ahead of the normal
        # Claude path, because if the caller explicitly forced
        # bulk_provider="openai-compatible" that's an intentional override
        # (e.g. pointing at a locally-hosted model for a specific
        # experiment) that should win even for the "complex" tier, which
        # otherwise always means Claude.
        if self.bulk_provider == "openai-compatible":
            records = self._call_openai_compatible(prompt=self._build_generation_prompt(seed, threat_class, count=num_variants, bulk=False), max_tokens=CLAUDE_LARGE_BATCH_MAX_TOKENS)
            return self._finalize_records(records, seed, threat_class, OPENAI_COMPATIBLE_SOURCE)
        if self.anthropic_client is None and not self.anthropic_api_key:
            raise ValueError("Anthropic API key is required for complex generation")
        prompt = self._build_generation_prompt(seed, threat_class, count=num_variants, bulk=False)
        # More variants requested in one call needs more output tokens —
        # bump the ceiling for anything above the default small batch size
        # (COMPLEX_BATCH_SIZE == 3) so the response doesn't get truncated
        # mid-JSON.
        max_tokens = CLAUDE_LARGE_BATCH_MAX_TOKENS if num_variants > 3 else CLAUDE_DEFAULT_MAX_TOKENS
        records = self._call_claude(prompt, max_tokens=max_tokens)
        return self._finalize_records(records, seed, threat_class, "synthetic_claude")

    def generate_bulk(
        self,
        seed: SeedRecord,
        threat_class: str,
        count: int = 10,
    ) -> list[dict[str, Any]]:
        """Generate higher-volume variations with Gemini, OpenRouter, or DeepSeek."""
        prompt = self._build_generation_prompt(seed, threat_class, count=count, bulk=True)
        if self.bulk_provider not in {"auto", "gemini", "openrouter", "deepseek", "claude", "openai-compatible"}:
            raise ValueError(f"Unsupported bulk provider: {self.bulk_provider}")

        if self.bulk_provider == "openai-compatible":
            records = self._call_openai_compatible(prompt, max_tokens=BULK_PROVIDER_MAX_TOKENS)
            return self._finalize_records(records, seed, threat_class, OPENAI_COMPATIBLE_SOURCE)

        # THE FALLBACK CHAIN — this is the heart of "auto" mode. Try
        # providers in cost-ascending order: Gemini first (cheapest/
        # fastest), then OpenRouter, then DeepSeek, and only fall back all
        # the way to Claude (most expensive) if every cheaper option is
        # either unconfigured or actively failing. Each `if` block below is
        # gated two ways: (1) is this the provider the caller asked for
        # (or "auto"), and (2) is it actually configured (has an API key).
        # On an HTTPError from a given provider, the `raise` re-raises
        # ONLY if there's truly nothing left to fall back to, OR if the
        # caller pinned bulk_provider to exactly this one (no fallback
        # wanted in that case) — otherwise it silently falls through to
        # try the next provider in the chain.
        if self.bulk_provider in {"auto", "gemini"} and self.gemini_session.is_configured():
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
        if self.bulk_provider in {"auto", "deepseek"} and self.deepseek_api_key:
            try:
                records = self._call_deepseek(prompt)
                return self._finalize_records(records, seed, threat_class, "synthetic_deepseek")
            except httpx.HTTPError:
                if not self.anthropic_api_key and self.anthropic_client is None:
                    raise
                if self.bulk_provider == "deepseek":
                    raise
        # Last resort: Claude, even for bulk. Expensive, but better than
        # failing the whole batch if every cheaper provider is down/unset.
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
        class_targets: dict[str, int] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Generate a roughly balanced synthetic dataset across all threat classes.

        THIS IS THE TOP-LEVEL ENTRY POINT for generating the whole ~2500-row
        (or however many target_count says) corpus in one call. Everything
        below it (_build_batch_specs, _execute_batch_specs*, checkpointing)
        exists to serve this one function. High-level shape:
          1. Figure out how many rows PER threat class are needed
             (class_targets — defaults to an even split via
             _build_class_targets, e.g. target_count/4 each for 4 classes).
          2. Check for a resumable checkpoint (a prior run that was
             interrupted — see _prepare_resume_state).
          3. Turn "N rows needed for class X" into a concrete list of
             BatchSpec work items (small Claude batches + bigger bulk-
             provider batches, per class).
          4. Run them (sequentially or in a thread pool), checkpointing
             after every single batch so a crash/interrupt never loses more
             than one batch's worth of API calls.
          5. Trim the final combined pool down to exactly target_count,
             per-class, in case any provider over-returned.
        """
        if not seeds:
            raise ValueError("At least one seed is required")
        if max_parallel_batches < 1:
            raise ValueError("max_parallel_batches must be at least 1")

        if class_targets is None:
            # Default path: split target_count evenly across THREAT_CLASSES
            # (e.g. bank_impersonation / zalo_social_engineering /
            # task_scam / benign), so the trained model sees a balanced
            # dataset rather than being skewed toward whichever class was
            # easiest to generate.
            class_targets = self._build_class_targets(target_count)
        else:
            # Caller supplied an explicit per-class breakdown instead (used
            # for e.g. topping up one specific under-represented class
            # without regenerating everything). Validate it: every key must
            # be a real threat class, every value must be non-negative, and
            # target_count is recomputed as the sum so the two can never
            # silently disagree.
            unknown_labels = sorted(set(class_targets) - set(THREAT_CLASSES))
            if unknown_labels:
                raise ValueError(f"Unsupported class target labels: {', '.join(unknown_labels)}")

            normalized_targets: dict[str, int] = {}
            for threat_class in THREAT_CLASSES:
                requested = int(class_targets.get(threat_class, 0))
                if requested < 0:
                    raise ValueError("class_targets values must be zero or greater")
                normalized_targets[threat_class] = requested
            class_targets = normalized_targets
            target_count = sum(class_targets.values())
            if target_count == 0:
                return []

        # Resume support: if a prior run left checkpoint files behind and
        # resume=True, this loads however many batches already completed
        # so we don't re-spend API calls regenerating them.
        completed_batches, restored_records = self._prepare_resume_state(
            checkpoint_path=checkpoint_path,
            partial_output_path=partial_output_path,
            resume=resume,
            progress_callback=progress_callback,
        )
        # Build the full work plan, MINUS whatever's already done (that's
        # what completed_batch_keys is for — _build_batch_specs skips specs
        # whose batch_key was already checkpointed).
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

        # Final trim: group everything (freshly generated + restored from
        # checkpoint) by label, and cap each class at exactly its target —
        # a provider can occasionally return a few more rows than asked
        # for in one batch, so this guarantees the final counts match
        # class_targets exactly rather than drifting slightly over.
        generated: list[dict[str, Any]] = []
        for threat_class in THREAT_CLASSES:
            class_records = [record for record in restored_records if record.get("label") == threat_class]
            generated.extend(class_records[: class_targets[threat_class]])

        return generated[:target_count]

    def compare_models(self, seed: SeedRecord, threat_class: str) -> dict[str, dict[str, Any]]:
        """
        Run a small pilot generation pass across available providers.
        Not part of the main generation path — this is a diagnostic/
        exploration tool: generate ONE example from every configured
        provider and report length stats, so a human can eyeball which
        provider's output style/quality is worth using for the real run
        before committing thousands of API calls to it. Providers without
        a configured key just get an {"available": False, ...} entry
        instead of being skipped silently, so the report shows the full
        picture of what's set up vs. not.
        """
        prompt = self._build_generation_prompt(seed, threat_class, count=1, bulk=False)
        comparison: dict[str, dict[str, Any]] = {}

        if self.anthropic_client:
            claude_records = self._call_claude(prompt)
            comparison["claude"] = self._summarize_provider("claude", claude_records, CLAUDE_MODEL)
        else:
            comparison["claude"] = {"available": False, "notes": "Anthropic API key not configured"}

        if self.gemini_session.is_configured():
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

        if self.deepseek_api_key:
            deepseek_records = self._call_deepseek(
                self._build_generation_prompt(seed, threat_class, count=1, bulk=True)
            )
            comparison["deepseek"] = self._summarize_provider(
                "deepseek",
                deepseek_records,
                DEEPSEEK_MODEL,
            )
        else:
            comparison["deepseek"] = {"available": False, "notes": "DeepSeek API key not configured"}

        if self._openai_compatible_is_configured():
            openai_compatible_records = self._call_openai_compatible(
                self._build_generation_prompt(seed, threat_class, count=1, bulk=True),
                max_tokens=BULK_PROVIDER_MAX_TOKENS,
            )
            comparison["openai-compatible"] = self._summarize_provider(
                "openai-compatible",
                openai_compatible_records,
                self.openai_compatible_model,
            )
        else:
            comparison["openai-compatible"] = {"available": False, "notes": "OpenAI-compatible endpoint not configured"}

        return comparison

    def save_generated(
        self,
        records: list[dict[str, Any]],
        output_path: Path | None = None,
    ) -> Path:
        """Validate and persist generated records as JSONL."""
        destination = output_path or (self.data_dir / "synthetic" / "generated.jsonl")
        destination.parent.mkdir(parents=True, exist_ok=True)

        # model_validate() here is a SECOND validation pass (the first
        # already happened per-record in _finalize_records) — cheap
        # insurance that nothing malformed slipped in between generation
        # and disk, since this is the function that actually produces the
        # generated.jsonl file step 3 (quality_judge) reads from.
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
        # Three different prompt shapes depending on WHAT'S being asked
        # for, not just which provider: benign examples don't need a real
        # scam seed to riff on (there's no "seed" for a legitimate
        # message), so they get their own dedicated prompt builder that
        # just asks for varied realistic non-scam message types. Bulk vs
        # complex (for actual threat classes) use the SAME seed text but
        # different prompt templates — the bulk one is tuned for cheaper/
        # faster providers to crank out more variants at once, the complex
        # one leans on Claude's stronger reasoning for higher-fidelity,
        # more nuanced single examples.
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
        # Lazy client construction: only actually build the anthropic.Anthropic
        # client the FIRST time it's needed, not in __init__. Means you can
        # construct a TieredGenerator and call generate_bulk() with e.g.
        # only a Gemini key set, and never touch anthropic at all.
        if self.anthropic_client is None:
            if anthropic is None or not self.anthropic_api_key:
                raise ValueError("Anthropic API key is required for complex generation")
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        response = self.anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            # temperature=0.7: deliberately NOT 0.0 here. This is
            # generation (want varied, creative scam-message phrasings),
            # the opposite intent from the runtime inference path (step 9),
            # which uses temperature=0.0 because it wants deterministic,
            # repeatable classification — two different jobs, two very
            # different correct temperature choices.
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
        # gemini_session (GeminiAuthSession) handles Gemini's own auth
        # quirks (API key vs OAuth, whichever this project is configured
        # for) — kept in its own helper class rather than inlined here
        # because Gemini's auth is meaningfully more involved than "stick a
        # bearer token in a header" (see the other three providers below,
        # which all do exactly that).
        response = self.gemini_session.post_generate_content(
            self.http_client,
            GEMINI_MODEL,
            prompt,
            temperature=0.9,   # even higher than Claude's 0.7 — bulk tier wants max variety per call
            max_output_tokens=BULK_PROVIDER_MAX_TOKENS,
        )
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        payload = _load_json_payload(text)
        if not isinstance(payload, list):
            raise ValueError("Gemini response must be a JSON array")
        return payload

    def _call_openrouter(self, prompt: str) -> list[dict[str, Any]]:
        # OpenRouter is a single API that proxies many underlying models —
        # here it's pointed at "openai/gpt-4.1-mini" specifically, chosen
        # as a cheap/fast bulk-tier option. Plain bearer-token auth, OpenAI
        # chat-completions-shaped request/response — the simplest of the 5
        # provider integrations in this file.
        response = self.http_client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {self.openrouter_api_key}"},
            json={
                "model": "openai/gpt-4.1-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.9,
                "max_tokens": BULK_PROVIDER_MAX_TOKENS,
            },
        )
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]
        payload = _load_json_payload(text)
        if not isinstance(payload, list):
            raise ValueError("OpenRouter response must be a JSON array")
        return payload

    def _call_deepseek(self, prompt: str) -> list[dict[str, Any]]:
        # DeepSeek's own first-party API, also OpenAI-chat-completions-
        # shaped. This is the third fallback in the auto chain (after
        # Gemini and OpenRouter) — kept as a distinct provider rather than
        # folded into the generic openai-compatible path below because it
        # has its own dedicated API key/URL and is a first-class option in
        # bulk_provider's allowed set, not just an arbitrary endpoint.
        response = self.http_client.post(
            DEEPSEEK_URL,
            headers={"Authorization": f"Bearer {self.deepseek_api_key}"},
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.9,
                "max_tokens": BULK_PROVIDER_MAX_TOKENS,
            },
        )
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]
        payload = _load_json_payload(text)
        if not isinstance(payload, list):
            raise ValueError("DeepSeek response must be a JSON array")
        return payload

    def _openai_compatible_is_configured(self) -> bool:
        return bool(self.openai_compatible_base_url and self.openai_compatible_model)

    def _call_openai_compatible(self, prompt: str, max_tokens: int) -> list[dict[str, Any]]:
        # This is the "escape hatch" provider: any server that speaks the
        # OpenAI chat-completions HTTP shape (a locally-hosted model, a
        # university-provided endpoint, LM Studio, vLLM, etc.) can be
        # plugged in via just a base URL + model name in Settings, with no
        # code changes. It's the most defensive of the 5 call sites because
        # it's the LEAST trusted endpoint — self-hosted/third-party servers
        # are more likely to be slow or flaky than the big commercial APIs
        # above, hence the explicit retry loop below (none of the other 4
        # providers retry on timeout; they just let the exception propagate
        # to the fallback chain in generate_bulk).
        if not self._openai_compatible_is_configured():
            raise ValueError(
                "OPENAI_COMPATIBLE_BASE_URL and OPENAI_COMPATIBLE_MODEL are required for openai-compatible generation"
            )
        headers = {}
        if self.openai_compatible_api_key:
            # Auth is OPTIONAL here (unlike the other 4 providers) — a
            # local self-hosted server often doesn't require a key at all.
            headers["Authorization"] = f"Bearer {self.openai_compatible_api_key}"
        # Separate, longer read timeout than the default 60s http_client:
        # a self-hosted model running on modest hardware can genuinely take
        # minutes to generate a batch, especially without a fast GPU.
        request_timeout = httpx.Timeout(
            timeout=OPENAI_COMPATIBLE_READ_TIMEOUT_SECONDS,
            connect=OPENAI_COMPATIBLE_CONNECT_TIMEOUT_SECONDS,
            read=OPENAI_COMPATIBLE_READ_TIMEOUT_SECONDS,
            write=OPENAI_COMPATIBLE_CONNECT_TIMEOUT_SECONDS,
            pool=OPENAI_COMPATIBLE_CONNECT_TIMEOUT_SECONDS,
        )
        request_url = f"{self.openai_compatible_base_url}/chat/completions"
        request_payload = {
            "model": self.openai_compatible_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.9,
            "max_tokens": max_tokens,
        }

        # Manual retry loop with linear backoff (2s, 4s, 6s...), ONLY on
        # timeout specifically — a timeout is the one failure mode where
        # "the server might just be slow/busy, try again" is a reasonable
        # assumption. Other HTTP errors (4xx/5xx) are NOT retried here —
        # they propagate immediately, since retrying a 401/404 would just
        # fail the same way three times slower.
        for attempt in range(1, OPENAI_COMPATIBLE_TIMEOUT_RETRIES + 1):
            try:
                response = self.http_client.post(
                    request_url,
                    headers=headers,
                    json=request_payload,
                    timeout=request_timeout,
                )
                if hasattr(response, "raise_for_status"):
                    response.raise_for_status()
                text = response.json()["choices"][0]["message"]["content"]
                payload = _load_json_payload(text)
                if not isinstance(payload, list):
                    raise ValueError("OpenAI-compatible response must be a JSON array")
                return payload
            except httpx.TimeoutException:
                if attempt == OPENAI_COMPATIBLE_TIMEOUT_RETRIES:
                    raise
                time.sleep(OPENAI_COMPATIBLE_RETRY_BACKOFF_SECONDS * attempt)

        raise RuntimeError("OpenAI-compatible generation failed without returning a response")

    def _finalize_records(
        self,
        records: list[dict[str, Any]],
        seed: SeedRecord,
        threat_class: str,
        source: str,
    ) -> list[dict[str, Any]]:
        """
        The common landing point for ALL 5 providers' raw output — every
        _call_* method above returns a bare list[dict] parsed from LLM
        JSON, and every one of them funnels through here before becoming a
        real DatasetRecord. This is where the alias-normalization functions
        (_normalize_dataset_label, _normalize_risk_tier) get applied, where
        every record is stamped with its seed's deterministic id and which
        provider produced it (`source` — this is what later analysis can
        group by to see e.g. "how did Gemini-generated rows compare to
        Claude-generated rows"), and where DatasetRecord.model_validate()
        acts as a hard gate — if any record doesn't match the schema
        (missing required field, wrong type), this raises HERE, at
        generation time, rather than silently writing a malformed row that
        would only surface as a confusing failure two pipeline stages
        later.
        """
        seed_id = self._derive_seed_id(seed)
        finalized: list[dict[str, Any]] = []
        for record in records:
            payload = dict(record)
            payload["label"] = _normalize_dataset_label(payload.get("label"), threat_class)
            payload["risk_tier"] = _normalize_risk_tier(payload.get("risk_tier", "suspicious"))
            payload["suspicious_spans"] = payload.get("suspicious_spans", [])
            payload["source"] = source
            payload["seed_id"] = seed_id
            validated = DatasetRecord.model_validate(payload)
            finalized.append(validated.model_dump())
        return finalized

    def _derive_seed_id(self, seed: SeedRecord) -> str:
        # Deterministic, not random (no uuid4()) — hashing (source_url +
        # text) means the SAME seed always produces the SAME seed_id across
        # separate runs. That matters because seed_id is what
        # splitter.py (step 4) uses to keep every synthetic variant of one
        # seed together on the same side of the train/val/test split — if
        # this were random per-run, re-running generation would silently
        # break that grouping guarantee.
        fingerprint = hashlib.sha256(f"{seed.source_url}|{seed.text}".encode("utf-8")).hexdigest()
        return f"seed_{fingerprint[:12]}"

    def _prepare_resume_state(
        self,
        checkpoint_path: Path | None,
        partial_output_path: Path | None,
        resume: bool,
        progress_callback: Callable[[str], None] | None,
    ) -> tuple[dict[str, tuple[int, list[dict[str, Any]]]], list[dict[str, Any]]]:
        """
        Two completely different code paths depending on `resume`:
          - resume=False (fresh start): WIPE any leftover checkpoint/
            partial-output files from a previous run before starting, so a
            brand-new run can never accidentally mix in stale data from an
            old, unrelated run.
          - resume=True: load whatever checkpoint exists and reconstruct
            (a) the set of batch_keys already done (so _build_batch_specs
            can skip re-requesting them) and (b) the flat list of already-
            generated records to seed the final output with.
        """
        if not resume:
            # checkpoint_path is a directory — delete numbered checkpoint files inside it
            if checkpoint_path and checkpoint_path.exists():
                for cp_file in checkpoint_path.glob("checkpoint-*.jsonl"):
                    cp_file.unlink(missing_ok=True)
            if partial_output_path and partial_output_path.exists():
                partial_output_path.unlink()
            return {}, []

        completed_batches = self._load_checkpoint(checkpoint_path)
        restored_records: list[dict[str, Any]] = []
        # sorted by item[0] (the original `order` field) so records are
        # restored in the same order they were originally scheduled in,
        # even though the checkpoint file itself is a dict keyed by
        # batch_key (unordered).
        for _, records in sorted(completed_batches.values(), key=lambda item: item[0]):
            restored_records.extend(records)

        if completed_batches:
            self._emit_progress(
                progress_callback,
                f"Resuming from {len(completed_batches)} completed batches and {len(restored_records)} generated records.",
            )
            # If a partial_output_path was requested but doesn't exist yet
            # (e.g. resuming from a checkpoint-only run that never wrote a
            # partial file), backfill it now with everything restored so
            # far — keeps the two persistence mechanisms (checkpoint dir +
            # flat partial-output file) consistent with each other.
            if partial_output_path and not partial_output_path.exists():
                self._append_records(partial_output_path, restored_records)

        return completed_batches, restored_records

    def _build_batch_specs(
        self,
        seeds: list[SeedRecord],
        class_targets: dict[str, int],
        completed_batch_keys: set[str],
    ) -> list[BatchSpec]:
        """
        Turns "N rows needed per threat class" into a concrete, ordered
        list of BatchSpec work items, splitting each class's target between
        the "complex" (Claude, high quality, small batches) and "bulk"
        (cheap providers, bigger batches) tiers.
        """
        specs: list[BatchSpec] = []
        order = 0

        for index, threat_class in enumerate(THREAT_CLASSES):
            class_target = class_targets[threat_class]
            # 20% of each class's target goes to the expensive "complex"
            # tier (at least 1, if the class has any target at all) — just
            # enough high-quality Claude examples to anchor the class's
            # nuance, with the bulk of the volume (the remaining 80%) made
            # up cheaply. This 20/80 split is a deliberate cost control:
            # 100% Claude would be far more expensive; 100% bulk-provider
            # would lose some of the harder, more nuanced examples.
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
                    # Round-robin through the seed pool (index + batch_index,
                    # wrapped with modulo) rather than always using the same
                    # one or two seeds — spreads generation across many
                    # different real reported cases so the synthetic corpus
                    # doesn't over-fit its variety to just a handful of
                    # source seeds.
                    seed = seeds[(index + batch_index) % len(seeds)]
                    spec = BatchSpec(
                        order=order,
                        threat_class=threat_class,
                        batch_type=batch_type,
                        batch_index=batch_index,
                        count=requested,
                        seed=seed,
                    )
                    order += 1
                    # Skip specs that are already done per the checkpoint —
                    # this is the actual "resume" mechanic: the spec still
                    # gets an `order` (so numbering stays stable/comparable
                    # across resumed runs) but isn't added to the work list.
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
        # Simple dispatcher: max_parallel_batches == 1 (the default) runs
        # everything one batch at a time, in order — simplest to reason
        # about and debug, and the safest default. Anything above 1 hands
        # off to the thread-pool version below for real concurrency.
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
        # One spec at a time, checkpointing after EACH one. This is why an
        # interrupted 2-hour generation run only ever loses at most one
        # batch's worth of work (a handful of records) — not the whole run.
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
        # threading.Lock guards the ONLY shared mutable state touched from
        # multiple worker threads at once: the checkpoint/partial-output
        # files on disk, and the `completed` counter used for progress
        # messages. Without this lock, two worker threads finishing at
        # nearly the same instant could interleave their writes to the
        # same checkpoint file and corrupt it, or print out-of-order/
        # duplicate progress counts.
        lock = threading.Lock()
        completed = {"count": initial_completed}
        results_by_order: dict[int, list[dict[str, Any]]] = {}

        def worker(spec: BatchSpec) -> tuple[int, list[dict[str, Any]]]:
            # use_worker_clone=True: each thread gets its OWN TieredGenerator
            # instance (see _run_batch_spec below) rather than sharing
            # `self`. This matters because httpx.Client and the anthropic
            # SDK client aren't guaranteed safe to share across threads for
            # concurrent requests — a fresh clone per worker sidesteps that
            # entirely instead of having to reason about thread-safety of
            # third-party HTTP client internals.
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
                # as_completed: process results in WHATEVER order threads
                # actually finish (not submission order) — that's fine here
                # because results_by_order re-sorts by spec.order afterward,
                # so completion order never affects the final output order.
                for future in concurrent.futures.as_completed(futures):
                    order, batch_records = future.result()
                    results_by_order[order] = batch_records
        except KeyboardInterrupt:
            # Ctrl+C mid-run: every batch that already finished was already
            # checkpointed (inside the lock above, before this exception
            # could even propagate up), so re-raising here is safe — no
            # in-flight work silently vanishes, the next run with
            # resume=True just picks up from the last checkpointed batch.
            self._emit_progress(
                progress_callback,
                "Interrupted during generation. Completed batches were checkpointed and can be resumed with --resume.",
            )
            raise

        # Reassemble in original scheduling order (spec.order), not thread-
        # completion order, so the final record list is deterministic
        # regardless of how the thread pool happened to interleave work.
        records: list[dict[str, Any]] = []
        for spec in sorted(work_items, key=lambda item: item.order):
            records.extend(results_by_order.get(spec.order, []))
        return records

    def _run_batch_spec(self, spec: BatchSpec, use_worker_clone: bool = False) -> list[dict[str, Any]]:
        # See the use_worker_clone comment above — a clone gets an
        # independent httpx.Client/anthropic client instead of racing with
        # other threads on `self`'s shared clients.
        generator = self
        if use_worker_clone:
            generator = TieredGenerator(settings=self.settings, bulk_provider=self.bulk_provider)

        # Dispatch to whichever tier this spec was built for — this is the
        # one place batch_type ("complex" vs "bulk") actually decides which
        # public generation method (and therefore which underlying
        # provider strategy) runs.
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
        # Two independent, optional persistence sinks, both written after
        # every single batch: partial_output_path is a flat, append-only
        # JSONL of every record (simple, human-inspectable running total);
        # checkpoint_path is the structured, resumable state (tracks WHICH
        # batch_keys are done, not just the raw records). Either can be
        # None if the caller doesn't want that particular kind of
        # persistence — generate_dataset can be called with neither, for a
        # quick one-off in-memory-only run.
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

    def _find_latest_checkpoint_file(self, checkpoint_dir: Path | None) -> Path | None:
        if checkpoint_dir is None or not checkpoint_dir.exists():
            return None
        files = sorted(checkpoint_dir.glob("checkpoint-*.jsonl"))
        return files[-1] if files else None

    def _next_checkpoint_number(self, checkpoint_dir: Path) -> int:
        files = sorted(checkpoint_dir.glob("checkpoint-*.jsonl"))
        if not files:
            return 1
        stem = files[-1].stem  # e.g. "checkpoint-003"
        try:
            return int(stem.rsplit("-", 1)[-1]) + 1
        except ValueError:
            return len(files) + 1

    def _load_checkpoint(self, checkpoint_dir: Path | None) -> dict[str, tuple[int, list[dict[str, Any]]]]:
        # Only ever reads the SINGLE latest checkpoint file (not all of
        # them) — because _save_batch_checkpoint (below) always writes the
        # FULL cumulative state into each new checkpoint file, the latest
        # one alone is a complete picture. Older files are redundant
        # snapshots kept only as a safety margin (see CHECKPOINT_KEEP_COUNT
        # pruning below), not something that needs to be merged together.
        latest = self._find_latest_checkpoint_file(checkpoint_dir)
        if latest is None:
            return {}

        completed: dict[str, tuple[int, list[dict[str, Any]]]] = {}
        with latest.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                records = [DatasetRecord.model_validate(record).model_dump() for record in entry.get("records", [])]
                completed[entry["batch_key"]] = (entry["order"], records)
        return completed

    def _save_batch_checkpoint(self, checkpoint_dir: Path, spec: BatchSpec, records: list[dict[str, Any]]) -> None:
        """
        Checkpoint strategy: rather than appending one line per batch
        forever (which would mean _load_checkpoint has to scan and merge
        potentially hundreds of files), each save writes out a BRAND NEW
        file containing the FULL accumulated state (every batch done so
        far, not just this one) under the next sequential number. This
        keeps loading O(1) files at the cost of O(n) disk writes over a
        full run — a deliberate trade favoring simple, fast resume logic
        over disk efficiency, since checkpoint files are small JSONL and
        pruned anyway (see below).
        """
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Load all entries from the latest checkpoint file (cumulative state)
        existing_entries: list[dict[str, Any]] = []
        latest = self._find_latest_checkpoint_file(checkpoint_dir)
        if latest is not None:
            with latest.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if line:
                        existing_entries.append(json.loads(line))

        new_entry = {
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
        # Replace entry for same batch_key if it already exists, otherwise append.
        # Using a dict keyed by batch_key (not a plain list append) is what
        # makes this idempotent — re-running/re-saving the same spec twice
        # overwrites its one entry instead of duplicating it.
        entry_map = {e["batch_key"]: e for e in existing_entries}
        entry_map[new_entry["batch_key"]] = new_entry
        all_entries = list(entry_map.values())

        next_num = self._next_checkpoint_number(checkpoint_dir)
        next_file = checkpoint_dir / f"checkpoint-{next_num:03d}.jsonl"
        with next_file.open("w", encoding="utf-8") as handle:
            for entry in all_entries:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Prune: keep only the last CHECKPOINT_KEEP_COUNT files. Safe to
        # delete the older ones because, as noted above, the newest file
        # always contains the FULL cumulative state — nothing is lost by
        # dropping older snapshots, they're pure redundancy.
        all_files = sorted(checkpoint_dir.glob("checkpoint-*.jsonl"))
        for old_file in all_files[:-CHECKPOINT_KEEP_COUNT]:
            old_file.unlink(missing_ok=True)

    def _batch_key(self, spec: BatchSpec) -> str:
        # threat_class + batch_type + batch_index uniquely identifies a
        # spec's SLOT in the overall plan, independent of `order` (order
        # can shift between runs if class_targets changes; this key
        # shouldn't). This is the identity checkpointing/resume is built on.
        return f"{spec.threat_class}:{spec.batch_type}:{spec.batch_index}"

    def _emit_progress(
        self,
        progress_callback: Callable[[str], None] | None,
        message: str,
    ) -> None:
        # Two audiences: a caller that passed progress_callback (e.g. a CLI
        # progress bar, or a UI hooked up to stream status) gets the
        # message routed there; otherwise it just goes to stderr (not
        # stdout — stdout is reserved for actual data output in a CLI
        # tool, stderr is the right stream for incidental status noise).
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
        # A smaller, generic "keep calling `generate` in batch_size chunks
        # until `target` records are collected" helper. Guards against an
        # infinite loop if a provider starts returning empty batches
        # repeatedly (e.g. hitting a content filter or rate limit) by
        # bailing out after MAX_EMPTY_BATCHES consecutive empty results,
        # returning whatever was collected so far rather than hanging
        # forever.
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
        # Even split with remainder distributed to the FIRST `remainder`
        # classes (not randomly) — deterministic, so calling this twice
        # with the same target_count always produces the same breakdown.
        # e.g. target_count=2500 over 4 classes: base_count=625, remainder=0
        # → exactly 625 each. A target_count not evenly divisible (e.g.
        # 2501) gives the first class 626 and the rest 625, rather than
        # silently dropping or duplicating the leftover row.
        base_count = target_count // len(THREAT_CLASSES)
        remainder = target_count % len(THREAT_CLASSES)
        targets: dict[str, int] = {}
        for index, threat_class in enumerate(THREAT_CLASSES):
            targets[threat_class] = base_count + (1 if index < remainder else 0)
        return targets

    def _summarize_provider(self, provider: str, records: list[dict[str, Any]], model: str) -> dict[str, Any]:
        # Just descriptive stats (record count, average text/explanation
        # length) for the compare_models() pilot report — nothing here
        # feeds back into the real generation path. Purely "does this
        # provider's output look reasonable" at a glance.
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
