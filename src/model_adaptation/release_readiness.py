"""Fail-closed held-out release-evaluation readiness audit for Phase 5."""

from __future__ import annotations

from pathlib import Path

from src.model_adaptation.data import load_split_records
from src.model_adaptation.schemas import LOCKED_RELEASE_LABELS, LOCKED_RISKY_LABELS, HeldOutSupportAudit


DEFAULT_RELEASE_SPLIT_ROOT = Path("data/splits")
DEFAULT_RELEASE_SPLIT_NAME = "test.jsonl"


def resolve_release_eval_path(
    split_path: Path | None = None,
    split_root: Path | None = None,
) -> Path:
    """Resolve the held-out release-evaluation file without inventing a merged split."""

    if split_path is not None and split_root is not None:
        raise ValueError("Provide either split_path or split_root, not both")
    if split_path is not None:
        return split_path

    root = split_root if split_root is not None else DEFAULT_RELEASE_SPLIT_ROOT
    return root / DEFAULT_RELEASE_SPLIT_NAME


def audit_release_eval_support(
    split_path: Path | None = None,
    split_root: Path | None = None,
) -> HeldOutSupportAudit:
    """Count held-out support over the locked label order and block on risky gaps."""

    resolved_path = resolve_release_eval_path(split_path=split_path, split_root=split_root)
    resolved_root = split_root if split_root is not None else resolved_path.parent
    support_by_label = {label: 0 for label in LOCKED_RELEASE_LABELS}
    blocker_reasons: list[str] = []

    if not resolved_path.exists():
        blocker_reasons.append(f"Release-eval split not found at {resolved_path}")
        return HeldOutSupportAudit(
            evaluated_split_path=resolved_path,
            evaluated_split_root=resolved_root,
            support_by_label=support_by_label,
            blocker_reasons=blocker_reasons,
        )

    records = load_split_records(resolved_path)
    for record in records:
        support_by_label[record.label] += 1

    if not records:
        blocker_reasons.append(f"Release-eval split at {resolved_path} is empty")

    for label in LOCKED_RISKY_LABELS:
        if support_by_label[label] == 0:
            blocker_reasons.append(f"Missing support for risky label {label} in release-eval split {resolved_path}")

    return HeldOutSupportAudit(
        evaluated_split_path=resolved_path,
        evaluated_split_root=resolved_root,
        support_by_label=support_by_label,
        blocker_reasons=blocker_reasons,
    )