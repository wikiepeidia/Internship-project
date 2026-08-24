"""Observational timing and disposable-probe contracts for Phase 40.

This module deliberately does not import Transformers or Torch.  The Trainer
callback surface, monotonic clock, and CUDA operations are injected so the
scientific measurement logic remains fixture-testable without a model or GPU.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import json
import math
import os
from pathlib import Path, PurePosixPath
import shutil
from statistics import median
import time
from typing import Any, Protocol

from src.model_adaptation.phase40_modes import ExperimentIdentity, RunKind
from src.model_adaptation.registry import build_model_checksum


MIN_PROBE_POST_WARMUP_STEPS = 30
MAX_PROBE_POST_WARMUP_STEPS = 50
CALLBACK_SCHEMA_VERSION = "phase40-callback-v1"
CALLBACK_RESUME_STATE_SCHEMA_VERSION = "phase40-callback-resume-state-v1"
DISCARD_RECEIPT_SCHEMA_VERSION = "phase40-discard-v1"
NO_ARTIFACT_RECEIPT_SCHEMA_VERSION = "phase40-no-artifact-v1"


class CudaTimingAdapter(Protocol):
    """Small CUDA seam used by :class:`Phase40EvidenceCallback`."""

    def synchronize(self) -> None: ...

    def reset_peak_memory_stats(self) -> None: ...

    def max_memory_allocated(self) -> int: ...

    def max_memory_reserved(self) -> int: ...


class NoCudaTimingAdapter:
    """CPU-safe adapter that records zero CUDA memory without importing Torch."""

    def synchronize(self) -> None:
        return None

    def reset_peak_memory_stats(self) -> None:
        return None

    def max_memory_allocated(self) -> int:
        return 0

    def max_memory_reserved(self) -> int:
        return 0


class TorchCudaTimingAdapter:
    """Adapt an injected ``torch.cuda``-like object without importing Torch."""

    def __init__(self, cuda: Any) -> None:
        self._cuda = cuda
        self._enabled = bool(cuda.is_available())

    def synchronize(self) -> None:
        if self._enabled:
            self._cuda.synchronize()

    def reset_peak_memory_stats(self) -> None:
        if self._enabled:
            self._cuda.reset_peak_memory_stats()

    def max_memory_allocated(self) -> int:
        return int(self._cuda.max_memory_allocated()) if self._enabled else 0

    def max_memory_reserved(self) -> int:
        return int(self._cuda.max_memory_reserved()) if self._enabled else 0


class CallbackEventKind(StrEnum):
    TRAIN_BEGIN = "train_begin"
    OPTIMIZER_STEP = "optimizer_step"
    LOG = "log"
    EVALUATION = "evaluation"
    CHECKPOINT = "checkpoint"
    TRAIN_END = "train_end"


RawScalar = bool | int | float | str | None


def _require_nonempty_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be non-empty normalized text")
    return value


def _require_non_negative_int(name: str, value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _require_positive_int(name: str, value: object) -> int:
    result = _require_non_negative_int(name, value)
    if result == 0:
        raise ValueError(f"{name} must be positive")
    return result


def _require_finite_seconds(name: str, value: object, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be finite seconds")
    result = float(value)
    if not math.isfinite(result) or result < 0 or (positive and result <= 0):
        qualifier = "positive finite" if positive else "non-negative finite"
        raise ValueError(f"{name} must be {qualifier} seconds")
    return result


def _normalize_scalar(name: str, value: object) -> RawScalar:
    if hasattr(value, "item") and not isinstance(value, (bool, int, float, str)):
        value = value.item()
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"raw callback value {name!r} must be finite")
        return value
    raise ValueError(f"raw callback value {name!r} must be a JSON scalar")


def _normalize_values(values: Mapping[str, object] | None) -> tuple[tuple[str, RawScalar], ...]:
    if values is None:
        return ()
    normalized: list[tuple[str, RawScalar]] = []
    for key in sorted(values):
        if not isinstance(key, str) or not key:
            raise ValueError("callback raw-value keys must be non-empty strings")
        normalized.append((key, _normalize_scalar(key, values[key])))
    return tuple(normalized)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalized_utc_timestamp(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("callback UTC clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class Phase40CallbackEvent:
    """One ordered raw callback observation suitable for an append-only sink."""

    sequence_id: int
    source_run_id: str
    run_kind: RunKind
    event_kind: CallbackEventKind
    timestamp_utc: str
    optimizer_step: int
    epoch: float | None
    duration_seconds: float | None
    is_warmup: bool | None
    values: tuple[tuple[str, RawScalar], ...] = ()
    schema_version: str = CALLBACK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_non_negative_int("sequence_id", self.sequence_id)
        _require_nonempty_text("source_run_id", self.source_run_id)
        object.__setattr__(self, "run_kind", RunKind(self.run_kind))
        object.__setattr__(self, "event_kind", CallbackEventKind(self.event_kind))
        _require_nonempty_text("timestamp_utc", self.timestamp_utc)
        _require_non_negative_int("optimizer_step", self.optimizer_step)
        if self.epoch is not None:
            _require_finite_seconds("epoch", self.epoch)
        if self.duration_seconds is not None:
            _require_finite_seconds("duration_seconds", self.duration_seconds)
        if self.is_warmup is not None and not isinstance(self.is_warmup, bool):
            raise ValueError("is_warmup must be a boolean or None")
        if not isinstance(self.values, tuple):
            raise ValueError("callback event values must be an immutable tuple")
        keys = tuple(key for key, _ in self.values)
        if len(set(keys)) != len(keys) or keys != tuple(sorted(keys)):
            raise ValueError("callback event value keys must be unique and sorted")
        if self.schema_version != CALLBACK_SCHEMA_VERSION:
            raise ValueError("unknown Phase 40 callback schema version")

    def as_json_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "sequence_id": self.sequence_id,
            "source_run_id": self.source_run_id,
            "run_kind": self.run_kind.value,
            "event_kind": self.event_kind.value,
            "timestamp_utc": self.timestamp_utc,
            "optimizer_step": self.optimizer_step,
            "epoch": self.epoch,
            "duration_seconds": self.duration_seconds,
            "is_warmup": self.is_warmup,
            "values": dict(self.values),
        }


@dataclass(frozen=True, slots=True)
class Phase40ResourceSummary:
    """Mechanically derived timing/resource summary from retained raw events."""

    source_run_id: str
    run_kind: RunKind
    warmup_optimizer_steps: int
    observed_optimizer_steps: int
    retained_optimizer_steps: int
    steady_state_step_seconds_median: float
    examples_per_second: float
    tokens_per_second: float
    peak_allocated_bytes: int
    peak_reserved_bytes: int
    evaluation_overhead_seconds: float
    checkpoint_overhead_seconds: float
    measured_overhead_seconds: float
    actual_wall_seconds: float
    planned_full_optimizer_steps: int
    projected_local_runtime_seconds: float
    projected_local_runtime_is_estimate: bool = True

    def __post_init__(self) -> None:
        _require_nonempty_text("source_run_id", self.source_run_id)
        object.__setattr__(self, "run_kind", RunKind(self.run_kind))
        _require_non_negative_int("warmup_optimizer_steps", self.warmup_optimizer_steps)
        _require_positive_int("observed_optimizer_steps", self.observed_optimizer_steps)
        _require_positive_int("retained_optimizer_steps", self.retained_optimizer_steps)
        if self.retained_optimizer_steps > self.observed_optimizer_steps:
            raise ValueError("retained optimizer steps cannot exceed observed steps")
        for name in (
            "steady_state_step_seconds_median",
            "examples_per_second",
            "tokens_per_second",
            "actual_wall_seconds",
        ):
            _require_finite_seconds(name, getattr(self, name), positive=True)
        for name in (
            "evaluation_overhead_seconds",
            "checkpoint_overhead_seconds",
            "measured_overhead_seconds",
            "projected_local_runtime_seconds",
        ):
            _require_finite_seconds(name, getattr(self, name))
        _require_non_negative_int("peak_allocated_bytes", self.peak_allocated_bytes)
        _require_non_negative_int("peak_reserved_bytes", self.peak_reserved_bytes)
        if self.peak_reserved_bytes < self.peak_allocated_bytes:
            raise ValueError("peak reserved bytes cannot be below peak allocated bytes")
        _require_positive_int("planned_full_optimizer_steps", self.planned_full_optimizer_steps)
        if self.measured_overhead_seconds != (
            self.evaluation_overhead_seconds + self.checkpoint_overhead_seconds
        ):
            raise ValueError("measured overhead must equal evaluation plus checkpoint overhead")
        expected_eta = (
            self.steady_state_step_seconds_median * self.planned_full_optimizer_steps
            + self.measured_overhead_seconds
        )
        if self.projected_local_runtime_seconds != expected_eta:
            raise ValueError("projected local runtime does not match the locked ETA formula")
        if self.projected_local_runtime_is_estimate is not True:
            raise ValueError("projected local runtime must be explicitly marked as an estimate")


class Phase40EvidenceCallback:
    """Observe Trainer events without changing losses or Trainer control state."""

    def __init__(
        self,
        *,
        run_id: str,
        run_kind: RunKind | str,
        warmup_optimizer_steps: int = 5,
        target_post_warmup_steps: int | None = None,
        examples_per_optimizer_step: int,
        planned_full_optimizer_steps: int,
        tokens_per_optimizer_step: int | None = None,
        event_sink: Callable[[Phase40CallbackEvent], None] | None = None,
        resume_state: Mapping[str, object] | None = None,
        clock: Callable[[], float] = time.perf_counter,
        utc_clock: Callable[[], datetime] = _utc_now,
        cuda: CudaTimingAdapter | None = None,
    ) -> None:
        self.run_id = _require_nonempty_text("run_id", run_id)
        self.run_kind = RunKind(run_kind)
        self.warmup_optimizer_steps = _require_non_negative_int(
            "warmup_optimizer_steps", warmup_optimizer_steps
        )
        if self.run_kind == RunKind.PROBE:
            self.target_post_warmup_steps = validate_probe_target_steps(
                target_post_warmup_steps
            )
        elif target_post_warmup_steps is not None:
            raise ValueError("target_post_warmup_steps is reserved for probe runs")
        else:
            self.target_post_warmup_steps = None
        self.examples_per_optimizer_step = _require_positive_int(
            "examples_per_optimizer_step", examples_per_optimizer_step
        )
        self.planned_full_optimizer_steps = _require_positive_int(
            "planned_full_optimizer_steps", planned_full_optimizer_steps
        )
        self.tokens_per_optimizer_step = (
            None
            if tokens_per_optimizer_step is None
            else _require_positive_int("tokens_per_optimizer_step", tokens_per_optimizer_step)
        )
        if not callable(clock) or not callable(utc_clock):
            raise ValueError("clock and utc_clock must be callable")
        self._clock = clock
        self._utc_clock = utc_clock
        self._cuda = cuda or NoCudaTimingAdapter()
        self._event_sink = event_sink
        self._events: list[Phase40CallbackEvent] = []
        self._started = False
        self._ended = False
        self._train_started_at: float | None = None
        self._actual_wall_seconds: float | None = None
        self._active_step: int | None = None
        self._active_step_started_at: float | None = None
        self._active_tokens_before: int | None = None
        self._observed_steps = 0
        self._retained_durations: list[float] = []
        self._retained_examples = 0
        self._retained_tokens = 0
        self._evaluation_overheads: list[float] = []
        self._checkpoint_overheads: list[float] = []
        self._unmeasured_evaluations = 0
        self._unmeasured_checkpoints = 0
        self._peak_allocated_bytes = 0
        self._peak_reserved_bytes = 0
        self._prior_wall_seconds = 0.0
        if resume_state is not None:
            self._restore_resume_state(resume_state)

    def _restore_resume_state(self, state: Mapping[str, object]) -> None:
        """Restore only a fully compatible, checkpoint-sealed telemetry prefix."""

        expected_keys = {
            "schema_version",
            "run_id",
            "run_kind",
            "warmup_optimizer_steps",
            "examples_per_optimizer_step",
            "planned_full_optimizer_steps",
            "observed_optimizer_steps",
            "retained_step_seconds",
            "retained_examples",
            "retained_tokens",
            "evaluation_overhead_seconds",
            "checkpoint_overhead_seconds",
            "unmeasured_evaluations",
            "unmeasured_checkpoints",
            "peak_allocated_bytes",
            "peak_reserved_bytes",
            "actual_wall_seconds",
        }
        if not isinstance(state, Mapping) or set(state) != expected_keys:
            raise ValueError("callback resume state has missing or extra fields")
        if state["schema_version"] != CALLBACK_RESUME_STATE_SCHEMA_VERSION:
            raise ValueError("callback resume state schema version is unsupported")
        if state["run_id"] != self.run_id or RunKind(state["run_kind"]) != self.run_kind:
            raise ValueError("callback resume state belongs to a different run")
        compatibility = {
            "warmup_optimizer_steps": self.warmup_optimizer_steps,
            "examples_per_optimizer_step": self.examples_per_optimizer_step,
            "planned_full_optimizer_steps": self.planned_full_optimizer_steps,
        }
        if any(state[name] != expected for name, expected in compatibility.items()):
            raise ValueError("callback resume state is incompatible with runtime controls")

        durations_raw = state["retained_step_seconds"]
        evaluation_raw = state["evaluation_overhead_seconds"]
        checkpoint_raw = state["checkpoint_overhead_seconds"]
        if not isinstance(durations_raw, list) or not isinstance(evaluation_raw, list) or not isinstance(
            checkpoint_raw, list
        ):
            raise ValueError("callback resume duration histories must be JSON arrays")
        durations = [
            _require_finite_seconds("retained step duration", value, positive=True)
            for value in durations_raw
        ]
        evaluation = [
            _require_finite_seconds("evaluation overhead", value) for value in evaluation_raw
        ]
        checkpoint = [
            _require_finite_seconds("checkpoint overhead", value) for value in checkpoint_raw
        ]
        observed_steps = _require_non_negative_int(
            "observed_optimizer_steps", state["observed_optimizer_steps"]
        )
        if len(durations) > observed_steps:
            raise ValueError("callback resume state retains more steps than it observed")
        retained_examples = _require_non_negative_int(
            "retained_examples", state["retained_examples"]
        )
        if retained_examples != len(durations) * self.examples_per_optimizer_step:
            raise ValueError("callback resume example count differs from retained steps")
        retained_tokens = _require_non_negative_int("retained_tokens", state["retained_tokens"])
        peak_allocated = _require_non_negative_int(
            "peak_allocated_bytes", state["peak_allocated_bytes"]
        )
        peak_reserved = _require_non_negative_int(
            "peak_reserved_bytes", state["peak_reserved_bytes"]
        )
        if peak_reserved < peak_allocated:
            raise ValueError("callback resume peak reserved bytes are below allocated bytes")

        self._observed_steps = observed_steps
        self._retained_durations = durations
        self._retained_examples = retained_examples
        self._retained_tokens = retained_tokens
        self._evaluation_overheads = evaluation
        self._checkpoint_overheads = checkpoint
        self._unmeasured_evaluations = _require_non_negative_int(
            "unmeasured_evaluations", state["unmeasured_evaluations"]
        )
        self._unmeasured_checkpoints = _require_non_negative_int(
            "unmeasured_checkpoints", state["unmeasured_checkpoints"]
        )
        self._peak_allocated_bytes = peak_allocated
        self._peak_reserved_bytes = peak_reserved
        self._prior_wall_seconds = _require_finite_seconds(
            "actual_wall_seconds", state["actual_wall_seconds"]
        )

    def checkpoint_state(self) -> dict[str, object]:
        """Return the cumulative telemetry prefix to seal into one checkpoint."""

        if not self._started or self._ended or self._train_started_at is None:
            raise RuntimeError("callback checkpoint state requires active training")
        if self._active_step is not None:
            raise RuntimeError("callback checkpoint state cannot be captured inside a step")
        return self._active_resume_state(description="checkpoint wall time")

    def _active_resume_state(self, *, description: str) -> dict[str, object]:
        if not self._started or self._ended or self._train_started_at is None:
            raise RuntimeError("callback resume state requires active training")
        self._cuda.synchronize()
        elapsed = _require_finite_seconds(
            description, self._now() - self._train_started_at
        )
        self._peak_allocated_bytes = max(
            self._peak_allocated_bytes,
            _require_non_negative_int(
                "CUDA peak allocated bytes", self._cuda.max_memory_allocated()
            ),
        )
        self._peak_reserved_bytes = max(
            self._peak_reserved_bytes,
            _require_non_negative_int(
                "CUDA peak reserved bytes", self._cuda.max_memory_reserved()
            ),
        )
        return self._resume_state_payload(self._prior_wall_seconds + elapsed)

    def _resume_state_payload(self, actual_wall_seconds: float) -> dict[str, object]:
        return {
            "schema_version": CALLBACK_RESUME_STATE_SCHEMA_VERSION,
            "run_id": self.run_id,
            "run_kind": self.run_kind.value,
            "warmup_optimizer_steps": self.warmup_optimizer_steps,
            "examples_per_optimizer_step": self.examples_per_optimizer_step,
            "planned_full_optimizer_steps": self.planned_full_optimizer_steps,
            "observed_optimizer_steps": self._observed_steps,
            "retained_step_seconds": list(self._retained_durations),
            "retained_examples": self._retained_examples,
            "retained_tokens": self._retained_tokens,
            "evaluation_overhead_seconds": list(self._evaluation_overheads),
            "checkpoint_overhead_seconds": list(self._checkpoint_overheads),
            "unmeasured_evaluations": self._unmeasured_evaluations,
            "unmeasured_checkpoints": self._unmeasured_checkpoints,
            "peak_allocated_bytes": self._peak_allocated_bytes,
            "peak_reserved_bytes": self._peak_reserved_bytes,
            "actual_wall_seconds": actual_wall_seconds,
        }

    def failure_state(self) -> dict[str, object]:
        """Capture completed work, wall time, and peaks when Trainer exits by exception."""

        return self._active_resume_state(description="failed-attempt wall time")

    def completed_state(self) -> dict[str, object]:
        """Return cumulative measured resources after Trainer ended successfully."""

        if not self._ended or self._actual_wall_seconds is None:
            raise RuntimeError("completed callback state requires a successful train_end")
        return self._resume_state_payload(self._actual_wall_seconds)

    @property
    def events(self) -> tuple[Phase40CallbackEvent, ...]:
        return tuple(self._events)

    @property
    def total_probe_optimizer_steps(self) -> int | None:
        if self.target_post_warmup_steps is None:
            return None
        return self.warmup_optimizer_steps + self.target_post_warmup_steps

    def _now(self) -> float:
        value = self._clock()
        return _require_finite_seconds("monotonic clock", value)

    @staticmethod
    def _state_step(state: object) -> int:
        return _require_non_negative_int("Trainer global_step", getattr(state, "global_step", None))

    @staticmethod
    def _state_epoch(state: object) -> float | None:
        value = getattr(state, "epoch", None)
        if value is None:
            return None
        return _require_finite_seconds("Trainer epoch", value)

    @staticmethod
    def _state_tokens(state: object) -> int | None:
        value = getattr(state, "num_input_tokens_seen", None)
        if value is None:
            return None
        return _require_non_negative_int("Trainer num_input_tokens_seen", value)

    def _emit(
        self,
        event_kind: CallbackEventKind,
        *,
        state: object,
        duration_seconds: float | None = None,
        is_warmup: bool | None = None,
        values: Mapping[str, object] | None = None,
    ) -> Phase40CallbackEvent:
        event = Phase40CallbackEvent(
            sequence_id=len(self._events),
            source_run_id=self.run_id,
            run_kind=self.run_kind,
            event_kind=event_kind,
            timestamp_utc=_normalized_utc_timestamp(self._utc_clock()),
            optimizer_step=self._state_step(state),
            epoch=self._state_epoch(state),
            duration_seconds=duration_seconds,
            is_warmup=is_warmup,
            values=_normalize_values(values),
        )
        if self._event_sink is not None:
            self._event_sink(event)
        self._events.append(event)
        return event

    def on_train_begin(self, args, state, control, **kwargs):  # noqa: ANN001, ARG002
        if self._started:
            raise RuntimeError("Phase 40 callback observed train_begin more than once")
        self._cuda.reset_peak_memory_stats()
        self._cuda.synchronize()
        self._train_started_at = self._now()
        self._started = True
        self._emit(CallbackEventKind.TRAIN_BEGIN, state=state)
        return control

    def on_step_begin(self, args, state, control, **kwargs):  # noqa: ANN001, ARG002
        if not self._started or self._ended:
            raise RuntimeError("optimizer step began outside the active training region")
        if self._active_step is not None:
            raise RuntimeError("optimizer timing regions may not overlap")
        self._active_step = self._state_step(state) + 1
        self._active_tokens_before = self._state_tokens(state)
        self._cuda.synchronize()
        self._active_step_started_at = self._now()
        return control

    def on_step_end(self, args, state, control, **kwargs):  # noqa: ANN001, ARG002
        if self._active_step is None or self._active_step_started_at is None:
            raise RuntimeError("optimizer step ended without a matching begin event")
        completed_step = self._state_step(state)
        if completed_step != self._active_step:
            raise RuntimeError("Trainer global_step drifted across the optimizer timing region")
        self._cuda.synchronize()
        ended_at = self._now()
        duration = _require_finite_seconds(
            "optimizer step duration",
            ended_at - self._active_step_started_at,
            positive=True,
        )
        tokens_after = self._state_tokens(state)
        measured_tokens: int | None = None
        if self._active_tokens_before is not None and tokens_after is not None:
            measured_tokens = tokens_after - self._active_tokens_before
            if measured_tokens < 0:
                raise RuntimeError("Trainer input-token counter moved backwards")
        if not measured_tokens and self.tokens_per_optimizer_step is not None:
            measured_tokens = self.tokens_per_optimizer_step
        is_warmup = completed_step <= self.warmup_optimizer_steps
        self._observed_steps += 1
        if not is_warmup:
            self._retained_durations.append(duration)
            self._retained_examples += self.examples_per_optimizer_step
            if measured_tokens is not None:
                self._retained_tokens += measured_tokens
        self._peak_allocated_bytes = max(
            self._peak_allocated_bytes,
            _require_non_negative_int(
                "CUDA peak allocated bytes", self._cuda.max_memory_allocated()
            ),
        )
        self._peak_reserved_bytes = max(
            self._peak_reserved_bytes,
            _require_non_negative_int(
                "CUDA peak reserved bytes", self._cuda.max_memory_reserved()
            ),
        )
        self._emit(
            CallbackEventKind.OPTIMIZER_STEP,
            state=state,
            duration_seconds=duration,
            is_warmup=is_warmup,
            values={
                "examples": self.examples_per_optimizer_step,
                "tokens": measured_tokens,
                "peak_allocated_bytes": self._peak_allocated_bytes,
                "peak_reserved_bytes": self._peak_reserved_bytes,
            },
        )
        self._active_step = None
        self._active_step_started_at = None
        self._active_tokens_before = None
        return control

    def on_log(self, args, state, control, logs=None, **kwargs):  # noqa: ANN001, ARG002
        self._emit(CallbackEventKind.LOG, state=state, values=logs)
        return control

    def on_evaluate(self, args, state, control, metrics=None, **kwargs):  # noqa: ANN001, ARG002
        normalized_metrics = {} if metrics is None else dict(metrics)
        runtime = normalized_metrics.get("eval_runtime")
        if runtime is None:
            self._unmeasured_evaluations += 1
            duration = None
        else:
            duration = _require_finite_seconds("eval_runtime", runtime)
            self._evaluation_overheads.append(duration)
        self._emit(
            CallbackEventKind.EVALUATION,
            state=state,
            duration_seconds=duration,
            values=normalized_metrics,
        )
        return control

    def on_save(
        self,
        args,
        state,
        control,
        checkpoint_runtime_seconds=None,
        **kwargs,
    ):  # noqa: ANN001, ARG002
        if checkpoint_runtime_seconds is None:
            self._unmeasured_checkpoints += 1
            duration = None
        else:
            duration = _require_finite_seconds(
                "checkpoint_runtime_seconds", checkpoint_runtime_seconds
            )
            self._checkpoint_overheads.append(duration)
        self._emit(
            CallbackEventKind.CHECKPOINT,
            state=state,
            duration_seconds=duration,
            values={"measurement_scope": "isolated" if duration is not None else "not_isolated"},
        )
        return control

    def on_train_end(self, args, state, control, **kwargs):  # noqa: ANN001, ARG002
        if not self._started or self._ended or self._train_started_at is None:
            raise RuntimeError("Phase 40 callback observed an invalid train_end")
        if self._active_step is not None:
            raise RuntimeError("training ended inside an optimizer timing region")
        self._cuda.synchronize()
        ended_at = self._now()
        segment_wall_seconds = _require_finite_seconds(
            "actual wall time", ended_at - self._train_started_at, positive=True
        )
        self._actual_wall_seconds = self._prior_wall_seconds + segment_wall_seconds
        self._peak_allocated_bytes = max(
            self._peak_allocated_bytes,
            _require_non_negative_int(
                "CUDA peak allocated bytes", self._cuda.max_memory_allocated()
            ),
        )
        self._peak_reserved_bytes = max(
            self._peak_reserved_bytes,
            _require_non_negative_int(
                "CUDA peak reserved bytes", self._cuda.max_memory_reserved()
            ),
        )
        self._ended = True
        self._emit(
            CallbackEventKind.TRAIN_END,
            state=state,
            duration_seconds=self._actual_wall_seconds,
            values={
                "peak_allocated_bytes": self._peak_allocated_bytes,
                "peak_reserved_bytes": self._peak_reserved_bytes,
            },
        )
        return control

    def summary(self) -> Phase40ResourceSummary:
        if not self._ended or self._actual_wall_seconds is None:
            raise RuntimeError("resource summary requires a completed callback lifecycle")
        if not self._retained_durations:
            raise RuntimeError("resource summary requires post-warm-up optimizer steps")
        if self.run_kind == RunKind.PROBE and len(self._retained_durations) != self.target_post_warmup_steps:
            raise RuntimeError("completed probe does not contain its exact post-warm-up target")
        if self._retained_tokens <= 0:
            raise RuntimeError("resource summary requires measured post-warm-up input tokens")
        if self._unmeasured_evaluations:
            raise RuntimeError("resource summary contains evaluation events without eval_runtime")
        if self._unmeasured_checkpoints:
            raise RuntimeError("resource summary contains checkpoint events without isolated timing")
        retained_seconds = sum(self._retained_durations)
        steady_median = float(median(self._retained_durations))
        evaluation_overhead = float(sum(self._evaluation_overheads))
        checkpoint_overhead = float(sum(self._checkpoint_overheads))
        measured_overhead = evaluation_overhead + checkpoint_overhead
        projected = steady_median * self.planned_full_optimizer_steps + measured_overhead
        return Phase40ResourceSummary(
            source_run_id=self.run_id,
            run_kind=self.run_kind,
            warmup_optimizer_steps=self.warmup_optimizer_steps,
            observed_optimizer_steps=self._observed_steps,
            retained_optimizer_steps=len(self._retained_durations),
            steady_state_step_seconds_median=steady_median,
            examples_per_second=self._retained_examples / retained_seconds,
            tokens_per_second=self._retained_tokens / retained_seconds,
            peak_allocated_bytes=self._peak_allocated_bytes,
            peak_reserved_bytes=self._peak_reserved_bytes,
            evaluation_overhead_seconds=evaluation_overhead,
            checkpoint_overhead_seconds=checkpoint_overhead,
            measured_overhead_seconds=measured_overhead,
            actual_wall_seconds=self._actual_wall_seconds,
            planned_full_optimizer_steps=self.planned_full_optimizer_steps,
            projected_local_runtime_seconds=projected,
            projected_local_runtime_is_estimate=True,
        )


def validate_probe_target_steps(value: object) -> int:
    """Require the locked inclusive 30-50 post-warm-up probe range."""

    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("probe target must be an integer post-warm-up optimizer-step count")
    if not MIN_PROBE_POST_WARMUP_STEPS <= value <= MAX_PROBE_POST_WARMUP_STEPS:
        raise ValueError("probe target must be within the inclusive 30-50 range")
    return value


@dataclass(frozen=True, slots=True)
class ProbeExecutionContract:
    run_id: str
    requested_identity: ExperimentIdentity
    target_post_warmup_steps: int
    warmup_optimizer_steps: int = 5
    resume_from_checkpoint: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_text("run_id", self.run_id)
        if not isinstance(self.requested_identity, ExperimentIdentity):
            raise ValueError("requested_identity must be a typed ExperimentIdentity")
        if self.requested_identity.run_kind != RunKind.PROBE:
            raise ValueError("ProbeExecutionContract requires run_kind=probe")
        validate_probe_target_steps(self.target_post_warmup_steps)
        _require_non_negative_int("warmup_optimizer_steps", self.warmup_optimizer_steps)
        if self.resume_from_checkpoint is not None:
            raise ValueError("Phase 40 probes cannot accept resume input")

    @property
    def total_optimizer_steps(self) -> int:
        return self.warmup_optimizer_steps + self.target_post_warmup_steps


def require_registry_publication_allowed(
    *,
    run_kind: RunKind | str,
    evidence_complete: bool,
    evidence_verified: bool,
) -> None:
    """Fail before a caller reaches any registry mutation."""

    kind = RunKind(run_kind)
    if kind == RunKind.PROBE:
        raise RuntimeError("Phase 40 probe runs are never registry-publishable")
    if evidence_complete is not True or evidence_verified is not True:
        raise RuntimeError("registry publication requires complete hash-verified full-run evidence")


def require_full_run_event_stream(events: Sequence[Phase40CallbackEvent]) -> None:
    """Reject probe events as parents or curve inputs for a full run."""

    if not events:
        raise ValueError("a full-run event stream must not be empty")
    for index, event in enumerate(events):
        if not isinstance(event, Phase40CallbackEvent):
            raise ValueError("event stream contains an untyped callback event")
        if event.sequence_id != index:
            raise ValueError("event stream sequence IDs must be contiguous and ordered")
        if event.run_kind != RunKind.FULL:
            raise ValueError("probe events cannot enter a full-run curve or evidence bundle")


def _validate_relative_identity(value: object) -> str:
    identity = _require_nonempty_text("artifact path identity", value)
    path = PurePosixPath(identity)
    if path.is_absolute() or identity.startswith(("/", "\\")):
        raise ValueError("artifact path identity must be relative")
    if not path.parts or any(part in {"", ".", ".."} or ":" in part for part in path.parts):
        raise ValueError("artifact path identity contains unsafe components")
    if path.as_posix() != identity:
        raise ValueError("artifact path identity must use normalized POSIX separators")
    return identity


def _bounded_path(root: Path, identity: str, *, must_exist: bool) -> tuple[Path, Path]:
    normalized = _validate_relative_identity(identity)
    root_path = Path(root)
    if root_path.is_symlink():
        raise ValueError("probe root must not be a symlink")
    root_resolved = root_path.resolve(strict=must_exist)
    candidate = root_path.joinpath(*PurePosixPath(normalized).parts)
    if candidate.is_symlink():
        raise ValueError("probe artifact target must not be a symlink")
    candidate_resolved = candidate.resolve(strict=must_exist)
    if candidate_resolved == root_resolved or not candidate_resolved.is_relative_to(root_resolved):
        raise ValueError("probe artifact target escapes or equals the probe root")
    return root_resolved, candidate_resolved


@dataclass(frozen=True, slots=True)
class ProbeDiscardReceipt:
    run_id: str
    discarded_path_identity: str
    pre_discard_sha256: str
    removal_result: str
    path_absent: bool
    schema_version: str = DISCARD_RECEIPT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_nonempty_text("run_id", self.run_id)
        _validate_relative_identity(self.discarded_path_identity)
        if (
            not isinstance(self.pre_discard_sha256, str)
            or len(self.pre_discard_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.pre_discard_sha256)
        ):
            raise ValueError("pre_discard_sha256 must be a lowercase SHA-256 value")
        if self.removal_result != "removed" or self.path_absent is not True:
            raise ValueError("discard receipt must prove a removed and absent artifact")
        if self.schema_version != DISCARD_RECEIPT_SCHEMA_VERSION:
            raise ValueError("unknown probe discard receipt schema")

    def as_json_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "discarded_path_identity": self.discarded_path_identity,
            "pre_discard_sha256": self.pre_discard_sha256,
            "removal_result": self.removal_result,
            "path_absent": self.path_absent,
        }


def discard_probe_artifact(
    *,
    run_id: str,
    probe_root: Path,
    discarded_path_identity: str,
) -> ProbeDiscardReceipt:
    """Hash and remove one explicitly bounded probe artifact path."""

    _require_nonempty_text("run_id", run_id)
    _, target = _bounded_path(
        Path(probe_root), discarded_path_identity, must_exist=True
    )
    if target.is_dir():
        symlinks = [path for path in target.rglob("*") if path.is_symlink()]
        if symlinks:
            raise ValueError("probe artifacts containing symlinks cannot be discarded automatically")
    pre_discard_sha256 = build_model_checksum(target)
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    path_absent = not target.exists() and not target.is_symlink()
    if not path_absent:
        raise RuntimeError("probe artifact removal did not leave the target absent")
    return ProbeDiscardReceipt(
        run_id=run_id,
        discarded_path_identity=_validate_relative_identity(discarded_path_identity),
        pre_discard_sha256=pre_discard_sha256,
        removal_result="removed",
        path_absent=True,
    )


def verify_probe_discard_receipt(
    receipt: ProbeDiscardReceipt,
    *,
    probe_root: Path,
) -> None:
    if not isinstance(receipt, ProbeDiscardReceipt):
        raise ValueError("discard receipt must be a ProbeDiscardReceipt")
    _, target = _bounded_path(
        Path(probe_root), receipt.discarded_path_identity, must_exist=False
    )
    if target.exists() or target.is_symlink():
        raise ValueError("discarded probe artifact exists again")


def write_probe_discard_receipt(
    receipt: ProbeDiscardReceipt,
    output_path: Path,
) -> Path:
    """Atomically persist canonical discard-receipt bytes without rewriting drift."""

    if not isinstance(receipt, ProbeDiscardReceipt):
        raise ValueError("discard receipt must be a ProbeDiscardReceipt")
    output = Path(output_path)
    payload = (
        json.dumps(receipt.as_json_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    if output.exists():
        if output.read_bytes() != payload:
            raise FileExistsError("refusing to replace a different probe discard receipt")
        return output
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise FileExistsError(f"temporary receipt path already exists: {temporary}")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    if output.read_bytes() != payload:
        raise RuntimeError("probe discard receipt failed read-back verification")
    return output


@dataclass(frozen=True, slots=True)
class NoArtifactReceipt:
    run_id: str
    expected_path_identities: tuple[str, ...]
    paths_absent: bool
    schema_version: str = NO_ARTIFACT_RECEIPT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_nonempty_text("run_id", self.run_id)
        if not isinstance(self.expected_path_identities, tuple) or not self.expected_path_identities:
            raise ValueError("no-artifact receipt requires expected adapter/checkpoint paths")
        normalized = tuple(
            _validate_relative_identity(value) for value in self.expected_path_identities
        )
        if normalized != self.expected_path_identities or len(set(normalized)) != len(normalized):
            raise ValueError("no-artifact path identities must be normalized and unique")
        if self.paths_absent is not True:
            raise ValueError("no-artifact receipt must prove every expected path absent")
        if self.schema_version != NO_ARTIFACT_RECEIPT_SCHEMA_VERSION:
            raise ValueError("unknown no-artifact receipt schema")


def create_no_artifact_receipt(
    *,
    run_id: str,
    probe_root: Path,
    expected_path_identities: Sequence[str],
) -> NoArtifactReceipt:
    identities = tuple(expected_path_identities)
    receipt = NoArtifactReceipt(
        run_id=run_id,
        expected_path_identities=identities,
        paths_absent=True,
    )
    verify_no_artifact_receipt(receipt, probe_root=probe_root)
    return receipt


def verify_no_artifact_receipt(receipt: NoArtifactReceipt, *, probe_root: Path) -> None:
    if not isinstance(receipt, NoArtifactReceipt):
        raise ValueError("no-artifact receipt must be typed")
    for identity in receipt.expected_path_identities:
        _, target = _bounded_path(Path(probe_root), identity, must_exist=False)
        if target.exists() or target.is_symlink():
            raise ValueError(f"pre-start artifact unexpectedly exists: {identity}")


class PrestartFailureStage(StrEnum):
    PACKAGE_AUTHORITY = "package_authority"
    CAPABILITY_PREFLIGHT = "capability_preflight"
    MODE_PROOF = "mode_proof"


@dataclass(frozen=True, slots=True)
class PrestartFailureEvidence:
    """Failure-only branch that cannot carry synthesized completion fields."""

    run_id: str
    requested_identity: ExperimentIdentity
    failure_stage: PrestartFailureStage
    environment_reference: str
    authority_reference: str
    no_artifact_receipt: NoArtifactReceipt

    def __post_init__(self) -> None:
        _require_nonempty_text("run_id", self.run_id)
        if not isinstance(self.requested_identity, ExperimentIdentity):
            raise ValueError("pre-start evidence requires a typed requested identity")
        if self.requested_identity.run_kind != RunKind.PROBE:
            raise ValueError("pre-start probe failure must preserve run_kind=probe")
        object.__setattr__(self, "failure_stage", PrestartFailureStage(self.failure_stage))
        _require_nonempty_text("environment_reference", self.environment_reference)
        _require_nonempty_text("authority_reference", self.authority_reference)
        if not isinstance(self.no_artifact_receipt, NoArtifactReceipt):
            raise ValueError("pre-start evidence requires a typed no-artifact receipt")
        if self.no_artifact_receipt.run_id != self.run_id:
            raise ValueError("pre-start evidence and no-artifact receipt run IDs differ")


def verify_prestart_failure_evidence(
    evidence: PrestartFailureEvidence,
    *,
    probe_root: Path,
) -> None:
    if not isinstance(evidence, PrestartFailureEvidence):
        raise ValueError("pre-start failure evidence must be typed")
    verify_no_artifact_receipt(evidence.no_artifact_receipt, probe_root=probe_root)


def require_completed_probe(
    *,
    contract: ProbeExecutionContract,
    summary: Phase40ResourceSummary,
    discard_receipt: ProbeDiscardReceipt,
    probe_root: Path,
) -> None:
    """Require exact measurements and verified absence before success is claimable."""

    if summary.source_run_id != contract.run_id or discard_receipt.run_id != contract.run_id:
        raise ValueError("probe contract, summary, and discard receipt run IDs differ")
    if summary.run_kind != RunKind.PROBE:
        raise ValueError("completed probe summary must remain marked run_kind=probe")
    if summary.warmup_optimizer_steps != contract.warmup_optimizer_steps:
        raise ValueError("probe summary warm-up count differs from its execution contract")
    if summary.retained_optimizer_steps != contract.target_post_warmup_steps:
        raise ValueError("probe summary does not contain the exact contracted target")
    verify_probe_discard_receipt(discard_receipt, probe_root=probe_root)
