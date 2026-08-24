"""Deterministic raw-evidence-to-graph rendering for Phase 40."""

from __future__ import annotations

from collections.abc import Callable
from io import BytesIO
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from src.model_adaptation.phase40_evidence import (
    GraphProvenanceEvidence,
    RunEvent,
    RunEventKind,
    Sha256,
    _StrictModel,
    _atomic_write_bytes,
    _canonical_json_bytes,
    _domain_sha256,
    _run_relative_path,
    _sha256_file,
    _validate_json_value,
    load_run_events,
)
from src.model_adaptation.registry import build_model_checksum


GraphRenderer = Callable[["NormalizedGraphData", "GraphRenderOptions"], bytes]


class CurvePoint(_StrictModel):
    sequence_id: int = Field(ge=0)
    optimizer_step: int = Field(ge=0)
    epoch: float = Field(ge=0)
    value: float

    @field_validator("value")
    @classmethod
    def require_finite_value(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("curve values must be finite")
        return value


class SmoothedCurvePoint(_StrictModel):
    first_sequence_id: int = Field(ge=0)
    last_sequence_id: int = Field(ge=0)
    optimizer_step: int = Field(ge=0)
    value: float

    @model_validator(mode="after")
    def validate_window(self) -> "SmoothedCurvePoint":
        if self.last_sequence_id < self.first_sequence_id:
            raise ValueError("smoothed point sequence window is reversed")
        if not math.isfinite(self.value):
            raise ValueError("smoothed curve values must be finite")
        return self


class GraphRenderOptions(_StrictModel):
    schema_version: Literal["phase40-graph-options-v1"]
    graph_id: Literal["loss-curves"]
    smoothing_window: int | None = Field(default=None, ge=2)
    smoothing_label: str | None
    raw_points_authoritative: Literal[True]
    output_format: Literal["png"]
    dpi: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_smoothing_label(self) -> "GraphRenderOptions":
        expected = (
            None
            if self.smoothing_window is None
            else f"trailing-mean-window-{self.smoothing_window}"
        )
        if self.smoothing_label != expected:
            raise ValueError("smoothing label must exactly identify the configured window")
        return self

    @property
    def sha256(self) -> str:
        return _domain_sha256("phase40-graph-options-v1", self.model_dump(mode="json"))


class NormalizedGraphData(_StrictModel):
    schema_version: Literal["phase40-normalized-graph-data-v1"]
    graph_id: Literal["loss-curves"]
    event_source_sha256: Sha256
    metrics_source_sha256: Sha256
    train_loss_raw: tuple[CurvePoint, ...] = Field(min_length=1)
    validation_loss_raw: tuple[CurvePoint, ...] = Field(min_length=1)
    train_loss_smoothed: tuple[SmoothedCurvePoint, ...]
    validation_loss_smoothed: tuple[SmoothedCurvePoint, ...]
    options_sha256: Sha256

    @model_validator(mode="after")
    def preserve_event_order(self) -> "NormalizedGraphData":
        for name, points in (
            ("train_loss_raw", self.train_loss_raw),
            ("validation_loss_raw", self.validation_loss_raw),
        ):
            sequences = tuple(point.sequence_id for point in points)
            if sequences != tuple(sorted(sequences)) or len(set(sequences)) != len(sequences):
                raise ValueError(f"{name} must preserve unique raw event order")
        return self

    @property
    def canonical_bytes(self) -> bytes:
        return _canonical_json_bytes(self.model_dump(mode="json")) + b"\n"

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()


class GraphFileReference(_StrictModel):
    logical_name: str
    relative_path: str
    sha256: Sha256


class GraphProvenance(_StrictModel):
    schema_version: Literal["phase40-graph-provenance-v1"]
    graph_id: Literal["loss-curves"]
    renderer: str
    renderer_version: str
    options: GraphRenderOptions
    options_sha256: Sha256
    event_source: GraphFileReference
    metrics_source: GraphFileReference
    model_artifact: GraphFileReference
    normalized_data: GraphFileReference
    output: GraphFileReference

    @model_validator(mode="after")
    def validate_options_hash(self) -> "GraphProvenance":
        if self.options_sha256 != self.options.sha256:
            raise ValueError("graph options hash mismatch")
        return self

    def as_evidence(self) -> GraphProvenanceEvidence:
        return GraphProvenanceEvidence(
            graph_id=self.graph_id,
            renderer=self.renderer,
            renderer_version=self.renderer_version,
            options_sha256=self.options_sha256,
            event_source_logical_name=self.event_source.logical_name,
            event_source_sha256=self.event_source.sha256,
            metrics_source_logical_name=self.metrics_source.logical_name,
            metrics_source_sha256=self.metrics_source.sha256,
            model_artifact_logical_name=self.model_artifact.logical_name,
            model_artifact_sha256=self.model_artifact.sha256,
            normalized_data_logical_name=self.normalized_data.logical_name,
            normalized_data_sha256=self.normalized_data.sha256,
            output_logical_name=self.output.logical_name,
            output_sha256=self.output.sha256,
        )


def _load_metric_source(path: Path) -> Any:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("graph metric source is missing or empty")
    payload = path.read_bytes()
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise RuntimeError("graph metric source is not strict UTF-8") from exc
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = [json.loads(line) for line in text.splitlines() if line]
        except json.JSONDecodeError as exc:
            raise RuntimeError("graph metric source is not JSON or JSONL") from exc
    if not isinstance(parsed, (dict, list)) or not parsed:
        raise RuntimeError("graph metric source is structurally empty")
    return _validate_json_value(parsed, location="graph metrics")


def _numeric_value(event: RunEvent, *names: str) -> float | None:
    for name in names:
        value = event.trainer_values.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        numeric = float(value)
        if not math.isfinite(numeric):
            raise RuntimeError(f"event {event.sequence_id} contains non-finite {name}")
        return numeric
    return None


def _raw_loss_points(events: tuple[RunEvent, ...]) -> tuple[tuple[CurvePoint, ...], tuple[CurvePoint, ...]]:
    train: list[CurvePoint] = []
    validation: list[CurvePoint] = []
    for event in events:
        validation_value = _numeric_value(event, "eval_loss", "validation_loss")
        train_value = _numeric_value(event, "loss", "train_loss")
        if event.event_kind == RunEventKind.EVALUATION:
            if validation_value is None:
                validation_value = train_value
            train_value = None
        if train_value is not None:
            train.append(
                CurvePoint(
                    sequence_id=event.sequence_id,
                    optimizer_step=event.optimizer_step,
                    epoch=event.epoch,
                    value=train_value,
                )
            )
        if validation_value is not None:
            validation.append(
                CurvePoint(
                    sequence_id=event.sequence_id,
                    optimizer_step=event.optimizer_step,
                    epoch=event.epoch,
                    value=validation_value,
                )
            )
    if not train or not validation:
        raise RuntimeError("loss graph requires non-empty raw train and validation loss events")
    return tuple(train), tuple(validation)


def _smooth(points: tuple[CurvePoint, ...], window: int | None) -> tuple[SmoothedCurvePoint, ...]:
    if window is None:
        return ()
    smoothed: list[SmoothedCurvePoint] = []
    for end in range(window, len(points) + 1):
        sample = points[end - window : end]
        smoothed.append(
            SmoothedCurvePoint(
                first_sequence_id=sample[0].sequence_id,
                last_sequence_id=sample[-1].sequence_id,
                optimizer_step=sample[-1].optimizer_step,
                value=sum(point.value for point in sample) / window,
            )
        )
    return tuple(smoothed)


def build_normalized_graph_data(
    events_path: Path,
    metrics_path: Path,
    *,
    options: GraphRenderOptions,
) -> NormalizedGraphData:
    """Derive graph points exclusively from retained raw sources."""

    events = load_run_events(events_path)
    _load_metric_source(metrics_path)
    train, validation = _raw_loss_points(events)
    return NormalizedGraphData(
        schema_version="phase40-normalized-graph-data-v1",
        graph_id="loss-curves",
        event_source_sha256=_sha256_file(events_path),
        metrics_source_sha256=_sha256_file(metrics_path),
        train_loss_raw=train,
        validation_loss_raw=validation,
        train_loss_smoothed=_smooth(train, options.smoothing_window),
        validation_loss_smoothed=_smooth(validation, options.smoothing_window),
        options_sha256=options.sha256,
    )


def _matplotlib_renderer(
    data: NormalizedGraphData,
    options: GraphRenderOptions,
) -> tuple[bytes, str, str]:
    try:
        import matplotlib  # type: ignore[import-not-found]

        matplotlib.use("Agg")
        import matplotlib.pyplot as pyplot  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "Phase 40 graph rendering requires Matplotlib; install it only through an approved environment plan"
        ) from exc

    figure, axis = pyplot.subplots(figsize=(8, 5), dpi=options.dpi)
    try:
        axis.plot(
            [point.optimizer_step for point in data.train_loss_raw],
            [point.value for point in data.train_loss_raw],
            marker="o",
            linewidth=1,
            label="train loss (raw)",
        )
        axis.plot(
            [point.optimizer_step for point in data.validation_loss_raw],
            [point.value for point in data.validation_loss_raw],
            marker="s",
            linewidth=1,
            label="validation loss (raw)",
        )
        if data.train_loss_smoothed:
            axis.plot(
                [point.optimizer_step for point in data.train_loss_smoothed],
                [point.value for point in data.train_loss_smoothed],
                linestyle="--",
                label=f"train loss ({options.smoothing_label})",
            )
        if data.validation_loss_smoothed:
            axis.plot(
                [point.optimizer_step for point in data.validation_loss_smoothed],
                [point.value for point in data.validation_loss_smoothed],
                linestyle="--",
                label=f"validation loss ({options.smoothing_label})",
            )
        axis.set_xlabel("Optimizer step")
        axis.set_ylabel("Loss")
        axis.set_title("Phase 40 loss curves")
        axis.grid(True, alpha=0.25)
        axis.legend()
        figure.tight_layout()
        buffer = BytesIO()
        figure.savefig(
            buffer,
            format="png",
            dpi=options.dpi,
            metadata={"Software": "phase40-graph-renderer-v1"},
        )
        payload = buffer.getvalue()
    finally:
        pyplot.close(figure)
    if not payload:
        raise RuntimeError("Matplotlib produced an empty graph")
    return payload, "matplotlib", str(matplotlib.__version__)


def render_phase40_graphs(
    run_root: Path,
    *,
    events_relative_path: str = "events.jsonl",
    metrics_relative_path: str = "validation-metrics.json",
    model_artifact_relative_path: str = "adapter-or-model",
    normalized_data_relative_path: str = "curves/normalized-loss-curves.json",
    output_relative_path: str = "curves/loss-curves.png",
    provenance_relative_path: str = "curves/graph-provenance.json",
    smoothing_window: int | None = None,
    dpi: int = 120,
    renderer: GraphRenderer | None = None,
    renderer_name: str | None = None,
    renderer_version: str | None = None,
) -> GraphProvenance:
    """Render verified raw sources and atomically persist deterministic provenance."""

    run_root = Path(run_root)
    if not run_root.is_dir() or run_root.is_symlink():
        raise ValueError("run_root must be an existing non-symlink directory")
    events_path = _run_relative_path(run_root, events_relative_path)
    metrics_path = _run_relative_path(run_root, metrics_relative_path)
    model_path = _run_relative_path(run_root, model_artifact_relative_path)
    normalized_path = _run_relative_path(run_root, normalized_data_relative_path)
    output_path = _run_relative_path(run_root, output_relative_path)
    provenance_path = _run_relative_path(run_root, provenance_relative_path)
    if len({events_path, metrics_path, model_path, normalized_path, output_path, provenance_path}) != 6:
        raise ValueError("graph source/output paths must be distinct")
    if not model_path.exists() or (
        model_path.is_file() and model_path.stat().st_size == 0
    ) or (
        model_path.is_dir() and not any(child.is_file() for child in model_path.rglob("*"))
    ):
        raise RuntimeError("model artifact source is missing or empty")
    options = GraphRenderOptions(
        schema_version="phase40-graph-options-v1",
        graph_id="loss-curves",
        smoothing_window=smoothing_window,
        smoothing_label=(
            None if smoothing_window is None else f"trailing-mean-window-{smoothing_window}"
        ),
        raw_points_authoritative=True,
        output_format="png",
        dpi=dpi,
    )
    normalized = build_normalized_graph_data(events_path, metrics_path, options=options)
    _atomic_write_bytes(normalized_path, normalized.canonical_bytes)
    if renderer is None:
        output_bytes, resolved_renderer, resolved_version = _matplotlib_renderer(normalized, options)
    else:
        if not renderer_name or not renderer_version:
            raise ValueError("an injected renderer requires explicit name and version provenance")
        output_bytes = renderer(normalized, options)
        if not isinstance(output_bytes, bytes) or not output_bytes:
            raise RuntimeError("injected graph renderer must return non-empty bytes")
        resolved_renderer = renderer_name
        resolved_version = renderer_version
    _atomic_write_bytes(output_path, output_bytes)
    provenance = GraphProvenance(
        schema_version="phase40-graph-provenance-v1",
        graph_id="loss-curves",
        renderer=resolved_renderer,
        renderer_version=resolved_version,
        options=options,
        options_sha256=options.sha256,
        event_source=GraphFileReference(
            logical_name="events",
            relative_path=events_relative_path,
            sha256=_sha256_file(events_path),
        ),
        metrics_source=GraphFileReference(
            logical_name="validation-metrics",
            relative_path=metrics_relative_path,
            sha256=_sha256_file(metrics_path),
        ),
        model_artifact=GraphFileReference(
            logical_name="model-artifact",
            relative_path=model_artifact_relative_path,
            sha256=build_model_checksum(model_path),
        ),
        normalized_data=GraphFileReference(
            logical_name="graph-data-loss",
            relative_path=normalized_data_relative_path,
            sha256=_sha256_file(normalized_path),
        ),
        output=GraphFileReference(
            logical_name="graph-output-loss",
            relative_path=output_relative_path,
            sha256=_sha256_file(output_path),
        ),
    )
    manifest_bytes = _canonical_json_bytes(provenance.model_dump(mode="json")) + b"\n"
    _atomic_write_bytes(provenance_path, manifest_bytes)
    verified = verify_graph_provenance(run_root, provenance_relative_path=provenance_relative_path)
    if verified != provenance:
        raise RuntimeError("graph provenance semantic read-back mismatch")
    return provenance


def verify_graph_provenance(
    run_root: Path,
    *,
    provenance_relative_path: str = "curves/graph-provenance.json",
) -> GraphProvenance:
    run_root = Path(run_root)
    provenance_path = _run_relative_path(run_root, provenance_relative_path)
    if not provenance_path.is_file() or provenance_path.stat().st_size == 0:
        raise RuntimeError("graph provenance is missing or empty")
    provenance = GraphProvenance.model_validate_json(
        provenance_path.read_text(encoding="utf-8", errors="strict")
    )
    references = (
        provenance.event_source,
        provenance.metrics_source,
        provenance.model_artifact,
        provenance.normalized_data,
        provenance.output,
    )
    for reference in references:
        path = _run_relative_path(run_root, reference.relative_path)
        if not path.exists():
            raise RuntimeError(f"graph source/output is missing: {reference.logical_name}")
        actual = build_model_checksum(path)
        if actual != reference.sha256:
            raise RuntimeError(f"graph source/output hash mismatch: {reference.logical_name}")
    normalized = NormalizedGraphData.model_validate_json(
        _run_relative_path(run_root, provenance.normalized_data.relative_path).read_text(
            encoding="utf-8",
            errors="strict",
        )
    )
    if normalized.options_sha256 != provenance.options_sha256:
        raise RuntimeError("normalized graph data uses different renderer options")
    if normalized.event_source_sha256 != provenance.event_source.sha256:
        raise RuntimeError("normalized graph data event source hash mismatch")
    if normalized.metrics_source_sha256 != provenance.metrics_source.sha256:
        raise RuntimeError("normalized graph data metric source hash mismatch")
    return provenance


__all__ = [
    "CurvePoint",
    "GraphFileReference",
    "GraphProvenance",
    "GraphRenderOptions",
    "GraphRenderer",
    "NormalizedGraphData",
    "SmoothedCurvePoint",
    "build_normalized_graph_data",
    "render_phase40_graphs",
    "verify_graph_provenance",
]
