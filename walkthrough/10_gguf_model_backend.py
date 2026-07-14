# ============================================================
# STEP 10 of 10 — The GGUF Backend (Loads and Calls the Local Model)
# ============================================================
# Canonical source (this numbered copy exists ONLY for defense-day
# navigation — it is not a second implementation and is not imported
# by anything): src/runtime/analyzers/gguf.py
#
# What this file does: GGUFAnalyzer is the default deployed backend.
# _resolve_artifact_path() reads the model registry (written by step 6)
# to find which .gguf file to load. _load_runtime() constructs
# llama_cpp.Llama(...) once and caches it. analyze() runs the doctor
# check, builds the prompt (step 9), calls the model with
# temperature=0.0 (deterministic, not creative), and hands the raw
# output back to step 9's parsing/grounding functions.
#
# See also: documents/reports/supervisor/defense_code_navigation.md
# ============================================================

"""Laptop-baseline GGUF backend for the Phase 3 local runtime."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.config.settings import get_settings
from src.model_adaptation.registry import find_latest_artifact, load_model_registry
from src.runtime.analyzers.local_model import (
    build_analysis_result,
    build_structured_analysis_prompt,
    extract_structured_payload,
)
from src.runtime.contracts import AnalysisRequest, AnalysisResult, DoctorCheck, DoctorStatus


GGUF_SETUP_GUIDE = (
    "Install GGUF runtime extras with python -m pip install -e .[dev,runtime] and run the Phase 3 GGUF conversion flow to register the selected local artifact."
)
GGUF_CONTEXT_WINDOW = 512   # small on purpose — this project's messages are short SMS/Zalo texts, not long documents; keeps memory/latency down on modest CPU hardware
GGUF_COMPLETION_MAX_TOKENS = 250   # the structured JSON decision is compact — risk_tier + a few labels + a handful of short evidence/recommendation strings, not free-form prose


@dataclass
class GGUFAnalyzer:
    """
    Contract-compatible local analyzer backed by registered GGUF artifacts.

    THIS CLASS IS "THE MODEL" AS FAR AS THE REST OF THE RUNTIME IS
    CONCERNED — it implements the same AnalyzerBackend interface
    (doctor() + analyze()) that HeuristicAnalyzer and AcceleratedAnalyzer
    also implement (see step 8's _build_backend_from_settings), so
    RuntimeService never needs a special case for "the GGUF one." Three
    private cache fields (_cached_runtime / _cached_artifact_path /
    _cached_doctor_status), all field(init=False) so they're NOT
    constructor arguments — they're internal state, populated lazily the
    first time they're needed. Loading a GGUF model file is comparatively
    slow (reading a multi-GB file, initializing llama.cpp's internal
    state) — caching means that cost is paid ONCE per process, not once
    per analyzed message, which matters a lot for a CLI/demo where a user
    might analyze many messages in one session.
    """

    registry_path: Path = field(default_factory=lambda: get_settings().model_registry_path)
    runtime_profile: str = field(default_factory=lambda: get_settings().runtime_profile_gguf)
    backend_name: str = "gguf"
    _cached_runtime: Any | None = field(default=None, init=False, repr=False)
    _cached_artifact_path: Path | None = field(default=None, init=False, repr=False)
    _cached_doctor_status: DoctorStatus | None = field(default=None, init=False, repr=False)

    def _allowed_profiles(self) -> dict[str, str]:
        # Maps a runtime_profile STRING (e.g. "gguf-laptop") to the
        # matching FIELD NAME on the registry's PilotSelection object
        # (e.g. "baseline_winner_id") — this is the link back to Phase 3's
        # pilot comparison (src/model_adaptation/pilot.py): "gguf-laptop"
        # always means "whichever candidate the pilot stage picked as the
        # winner," not a hardcoded model name, so swapping which model is
        # deployed never requires touching this backend's code.
        settings = get_settings()
        return {
            settings.runtime_profile_gguf: "baseline_winner_id",
            settings.runtime_profile_gguf_runner_up: "runner_up_id",
        }

    def _resolve_artifact_path(self) -> Path:
        # THE LINK BACK TO STEP 6: reads the SAME model registry
        # register_gguf_artifact wrote into, finds the pilot selection,
        # resolves which candidate_id this runtime_profile actually points
        # at, then finds that candidate's most recently registered "gguf"
        # artifact. This is the literal chain of custody from "a QLoRA
        # adapter got trained" (step 5) through "it got merged and
        # converted" (step 6) to "here's the exact file this running
        # process will load" — fully traceable via the registry's
        # checksums at every hop.
        registry = load_model_registry(self.registry_path)
        if registry.selection is None:
            raise RuntimeError("Pilot selection metadata is missing")

        candidate_field = self._allowed_profiles()[self.runtime_profile]
        target_candidate_id = getattr(registry.selection, candidate_field)
        gguf_artifact = find_latest_artifact(
            registry,
            candidate_id=target_candidate_id,
            artifact_type="gguf",
        )
        if gguf_artifact is None or not gguf_artifact.local_path.exists():
            raise FileNotFoundError(f"Missing GGUF artifact for candidate_id={target_candidate_id}")
        return gguf_artifact.local_path

    def _load_runtime(self, artifact_path: Path) -> Any:
        """
        THE ACTUAL MODEL LOAD. Cache check first: if a runtime is already
        loaded AND it's for the SAME artifact_path, reuse it — reloading a
        multi-GB model file on every single analyzed message would make
        the tool unusably slow. llama_cpp is imported lazily (same pattern
        as the heavy training-stack imports in step 5) so this whole
        module can still be imported without llama-cpp-python installed;
        you only hit the ImportError if you actually try to run analysis.

        n_gpu_layers=0 IS THE ANSWER TO "WHY LOCAL / WHY CPU": this
        explicitly tells llama.cpp to offload ZERO layers to a GPU — the
        entire model runs on CPU. This is a deliberate deployment choice,
        not a limitation stumbled into: it means this tool runs on a
        completely ordinary laptop with no dedicated GPU required, which
        matters for a tool meant to be realistically deployable, not just
        a research demo that only works on specialized hardware. This is
        also exactly why the GGUF Q8_0 quantization (step 6) matters so
        much — 8-bit weights are what make CPU-only inference at this
        model size fast enough to be usable at all.

        n_ctx=GGUF_CONTEXT_WINDOW (512): the context window llama.cpp
        allocates KV-cache memory for — kept small deliberately, matching
        the short-message nature of the input (see the constant's comment
        above).
        """
        if self._cached_runtime is not None and self._cached_artifact_path == artifact_path:
            return self._cached_runtime

        llama_cpp = importlib.import_module("llama_cpp")
        runtime = llama_cpp.Llama(
            model_path=str(artifact_path),
            n_ctx=GGUF_CONTEXT_WINDOW,
            n_gpu_layers=0,
            verbose=False,
        )
        self._cached_runtime = runtime
        self._cached_artifact_path = artifact_path
        return runtime

    def _infer_payload(self, runtime: Any, text: str) -> dict[str, Any]:
        """
        Builds the prompt (step 9's build_structured_analysis_prompt — the
        EXACT same prompt builder used regardless of which backend is
        running) and calls the loaded llama_cpp runtime with it.

        temperature=0.0 IS DELIBERATE AND IMPORTANT: zero temperature means
        greedy/deterministic decoding — the model always picks its single
        highest-probability next token, no random sampling. For a
        classification-shaped task like this (assign a risk tier, cite
        real evidence) determinism is exactly what's wanted: the same
        message should get the same analysis every time, not a different
        roll of the dice on each run. Contrast this directly with the data
        GENERATION pipeline (step 2), which uses temperature=0.7-0.9
        specifically to get VARIED synthetic examples — same underlying
        llama.cpp/API mechanism, opposite temperature choice, because the
        two tasks want opposite properties (repeatability vs. variety).

        Two API surfaces are handled because llama-cpp-python has evolved
        multiple calling conventions across versions: prefer
        create_chat_completion (the modern, chat-message-shaped API) if
        available, with a nested try/except for response_format={"type":
        "json_object"} — some llama-cpp-python versions/model configs
        support constraining output to valid JSON directly, others raise
        TypeError on that kwarg, in which case it retries without it and
        relies on extract_structured_payload's own defensive JSON-hunting
        (step 9) instead. If create_chat_completion isn't available at
        all, fall back to create_completion (plain text completion, not
        chat-shaped), and if EVEN THAT isn't available, fall back to
        calling the runtime object directly as a function (the oldest/most
        primitive llama-cpp-python calling convention). Whatever text comes
        back, from whichever code path, always funnels through the same
        extract_structured_payload — one shared, robust parser regardless
        of which API shape produced the raw text.
        """
        prompt = build_structured_analysis_prompt(text)
        if hasattr(runtime, "create_chat_completion"):
            chat_kwargs = {
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": GGUF_COMPLETION_MAX_TOKENS,
                "temperature": 0.0,
            }
            try:
                response = runtime.create_chat_completion(
                    **chat_kwargs,
                    response_format={"type": "json_object"},
                )
            except TypeError:
                response = runtime.create_chat_completion(**chat_kwargs)
            generated_text = str(response["choices"][0]["message"]["content"])
            return extract_structured_payload(generated_text)
        if hasattr(runtime, "create_completion"):
            response = runtime.create_completion(
                prompt=prompt,
                max_tokens=GGUF_COMPLETION_MAX_TOKENS,
                temperature=0.0,
            )
        else:
            response = runtime(
                prompt,
                max_tokens=GGUF_COMPLETION_MAX_TOKENS,
                temperature=0.0,
                echo=False,
            )
        generated_text = str(response["choices"][0]["text"])
        return extract_structured_payload(generated_text)

    def doctor(self) -> DoctorStatus:
        """
        THE READINESS CHECK — this is what `vnphish doctor` (step 7) and
        the pre-flight check inside RuntimeService.analyze_text (step 8)
        both ultimately call. Cached once ready=True (subsequent calls in
        the same process return instantly), but NEVER cached when NOT
        ready — a not-ready result might change moment to moment (e.g. the
        user fixes a missing file while the process is still running), so
        it's always freshly re-checked until it actually succeeds once.

        A LADDER of checks, each one gating whether the next is even
        attempted — this is deliberately structured as "check the cheapest/
        most-fundamental thing first, only check more expensive things if
        the cheaper checks already passed," and returns EARLY (skipping
        later checks entirely) the moment something's missing, since there's
        no point checking whether the model can LOAD if the registry file
        doesn't even exist yet:
          1. runtime_profile is a recognized value at all.
          2. the registry FILE exists on disk (return early if not).
          3. the registry has a pilot SELECTION recorded (return early if
             not, or if the profile doesn't map to an allowed candidate).
          4. a GGUF artifact is actually registered AND its file exists on
             disk for the target candidate.
          5. ONLY if the artifact file exists: actually try to LOAD it
             (this is the most expensive check — reads a multi-GB file —
             which is exactly why it's saved for last, after every cheaper
             check already passed). A load failure here is caught and
             reported as a specific failed check with the actual exception
             message, not a crash.
        Every check appends a DoctorCheck with passed/detail/a remediation
        command — `format_doctor_report` (step 7's dependency) renders
        these into the human-readable report a presenter sees when running
        `vnphish doctor`.
        """
        if self._cached_doctor_status is not None:
            return self._cached_doctor_status

        checks: list[DoctorCheck] = []
        allowed_profiles = self._allowed_profiles()
        checks.append(
            DoctorCheck(
                name="runtime-profile",
                passed=self.runtime_profile in allowed_profiles,
                detail=f"runtime_profile={self.runtime_profile}",
                remediation_command=GGUF_SETUP_GUIDE,
            )
        )

        if not self.registry_path.exists():
            checks.append(
                DoctorCheck(
                    name="model-registry",
                    passed=False,
                    detail=f"Missing model registry: {self.registry_path}",
                    remediation_command=GGUF_SETUP_GUIDE,
                )
            )
            return DoctorStatus(
                ready=False,
                backend_name=self.backend_name,
                checks=checks,
                setup_steps=[GGUF_SETUP_GUIDE],
            )

        registry = load_model_registry(self.registry_path)
        has_selection = registry.selection is not None
        checks.append(
            DoctorCheck(
                name="pilot-selection",
                passed=has_selection,
                detail="Pilot selection metadata is available." if has_selection else "Pilot selection metadata is missing.",
                remediation_command=GGUF_SETUP_GUIDE,
            )
        )

        if not has_selection or self.runtime_profile not in allowed_profiles:
            return DoctorStatus(
                ready=False,
                backend_name=self.backend_name,
                checks=checks,
                setup_steps=[GGUF_SETUP_GUIDE],
            )

        candidate_field = allowed_profiles[self.runtime_profile]
        target_candidate_id = getattr(registry.selection, candidate_field)
        gguf_artifact = find_latest_artifact(
            registry,
            candidate_id=target_candidate_id,
            artifact_type="gguf",
        )
        artifact_ready = gguf_artifact is not None and gguf_artifact.local_path.exists()
        checks.append(
            DoctorCheck(
                name="gguf-artifact",
                passed=artifact_ready,
                detail=(
                    f"GGUF artifact ready at {gguf_artifact.local_path}"
                    if artifact_ready
                    else f"Missing GGUF artifact for candidate_id={target_candidate_id}"
                ),
                remediation_command=GGUF_SETUP_GUIDE,
            )
        )

        if artifact_ready:
            try:
                artifact_path = self._resolve_artifact_path()
                self._load_runtime(artifact_path)
                checks.append(
                    DoctorCheck(
                        name="gguf-runtime-load",
                        passed=True,
                        detail=f"GGUF runtime can load {artifact_path}",
                        remediation_command=GGUF_SETUP_GUIDE,
                    )
                )
            except Exception as exc:
                checks.append(
                    DoctorCheck(
                        name="gguf-runtime-load",
                        passed=False,
                        detail=f"GGUF runtime failed to load local resources: {exc}",
                        remediation_command=GGUF_SETUP_GUIDE,
                    )
                )

        ready = all(check.passed for check in checks)
        setup_steps = [] if ready else [GGUF_SETUP_GUIDE]
        status = DoctorStatus(
            ready=ready,
            backend_name=self.backend_name,
            checks=checks,
            setup_steps=setup_steps,
        )
        if status.ready:
            self._cached_doctor_status = status
        return status

    def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        """
        THE FULL CIRCLE — the last hop in the six-step execution chain
        described in defense_code_navigation.md. By the time RuntimeService
        (step 8) calls this, the text has ALREADY been normalized and
        boundary-checked; this method's own job is narrow: confirm the
        backend itself is ready (belt-and-suspenders — RuntimeService
        already checked this too, but this method doesn't assume its only
        caller is RuntimeService), resolve which artifact file to use,
        load (or reuse the cached) runtime, run inference
        (_infer_payload — where the prompt from step 9 actually gets sent
        to the model and temperature=0.0 is applied), and hand the raw
        parsed JSON payload to build_analysis_result (step 9) — which is
        where grounding, the safety floor, and recommendation sanitization
        all happen. This method itself does NOT touch any of that
        validation logic directly; it's a thin "get raw model output, then
        hand off to the shared decision-building pipeline" layer, so
        every backend (GGUF, accelerated, heuristic) gets IDENTICAL
        validation/safety guarantees regardless of how its raw payload was
        produced.
        """
        status = self.doctor()
        if not status.ready:
            raise RuntimeError("GGUF backend is not ready")

        artifact_path = self._resolve_artifact_path()
        runtime = self._load_runtime(artifact_path)
        payload = self._infer_payload(runtime, request.text)
        return build_analysis_result(payload, request, self.backend_name)
