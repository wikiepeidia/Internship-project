"""Fail-closed Phase 39 F-01 Zalo semantic reconstruction.

The prior quote-strip repair removed only the outer scaffold. All 240 live
Zalo rows still equal four known narrator formulas derived from 60 semantic
roots. This one-off migration proves that exact legacy state, replaces each
four-row seed group with five newly authored direct messages, validates a
candidate bundle completely, and only then promotes it to the canonical
splits. No provider or network path exists in this module.

The replacement is new wording reconstructed from preserved semantics. It is
not a claim that authentic original wording was recovered.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from src.data_pipeline.generation.generator import TieredGenerator
from src.data_pipeline.generation.zalo_codex_catalog import SCENARIO_ROOTS, ScenarioRoot
from src.data_pipeline.generation.zalo_codex_recovery import (
    BUILD_METADATA,
    materialize_catalog,
    seed_record_for_root,
    validate_direct_message,
    validate_records,
)
from src.data_pipeline.processing.dedup import fuzz
from src.data_pipeline.processing.normalizer import normalize_text
from src.data_pipeline.schemas import DatasetRecord


SPLIT_NAMES = ("train", "val", "test")
ALL_LABELS = ("bank_impersonation", "task_scam", "benign", "zalo_social_engineering")
TARGET_LABEL = "zalo_social_engineering"
AUTHORING_SOURCE_PATHS = (
    "src/data_pipeline/generation/zalo_codex_catalog.py",
    "src/data_pipeline/generation/zalo_codex_recovery.py",
    "src/data_pipeline/generation/zalo_direct_actions.py",
    "src/data_pipeline/generation/zalo_direct_messages.py",
    "src/data_pipeline/generation/zalo_direct_messages_01_20.py",
    "src/data_pipeline/generation/zalo_direct_messages_21_40.py",
    "src/data_pipeline/generation/zalo_direct_messages_41_60.py",
    "src/data_pipeline/repair_zalo_narrator_scaffold.py",
    "src/data_pipeline/reconstruct_zalo_direct_catalog.py",
)
INPUT_TOTAL = 2343
OUTPUT_TOTAL = 2403
EXPECTED_INPUT_COUNTS = {"train": 1862, "val": 244, "test": 237}
EXPECTED_OUTPUT_COUNTS = {"train": 1900, "val": 252, "test": 251}
EXPECTED_INPUT_DISTRIBUTION = {
    "train": {"bank_impersonation": 575, "task_scam": 599, "benign": 536, TARGET_LABEL: 152},
    "val": {"bank_impersonation": 75, "task_scam": 71, "benign": 66, TARGET_LABEL: 32},
    "test": {"bank_impersonation": 65, "task_scam": 59, "benign": 57, TARGET_LABEL: 56},
}
EXPECTED_OUTPUT_DISTRIBUTION = {
    "train": {"bank_impersonation": 575, "task_scam": 599, "benign": 536, TARGET_LABEL: 190},
    "val": {"bank_impersonation": 75, "task_scam": 71, "benign": 66, TARGET_LABEL: 40},
    "test": {"bank_impersonation": 65, "task_scam": 59, "benign": 57, TARGET_LABEL: 70},
}
EXPECTED_CANONICAL_SHA256 = {
    "train.jsonl": "755003bbe39f98e50ed0061eaaea7b8842af54f22971a2e1dbd74e6eea425175",
    "val.jsonl": "0f18925b807faecdcf0bc89179d6acd4dbb802ccb60a6d8e9d1fd78d826d2fa9",
    "test.jsonl": "bcbccaf99cb4ea6d5d504dc6256d55bbd91435aaaa73b071735f842103aac32d",
    "manifest.json": "84bf80948d8074baf10a22d4b388c46dde65415ee94cd6b874be6a2df85d1fb8",
}
EXPECTED_ZALO_SEEDS_BY_SPLIT = {
    "train": {
        "seed_22a3792ae08c", "seed_e65835eb3d29", "seed_a09548afbece", "seed_4138907174a2",
        "seed_b71053db4c59", "seed_24b14f8f8c65", "seed_bf96acd71944", "seed_bb3b10a9913f",
        "seed_a236e34e7773", "seed_99c391bfadbb", "seed_dc701821055a", "seed_6f9409a0db8e",
        "seed_c91388584205", "seed_a8e1aabe0a03", "seed_b32d6227d048", "seed_733902197374",
        "seed_73d2bbdefec8", "seed_b1abe3716ff6", "seed_5b0a14e09ba5", "seed_2caef64d33a6",
        "seed_8596de0b7d00", "seed_5e905f426e5f", "seed_e3c1635c4810", "seed_3ceb8f4aab76",
        "seed_9ee1810bccf0", "seed_f020dc770cc4", "seed_f9c3030a5dc9", "seed_3e8555a04059",
        "seed_a631c566f8db", "seed_a65264a0b6dc", "seed_e2773f4d633e", "seed_c566963f8cf1",
        "seed_8edd966a5732", "seed_a8249971ee78", "seed_d40f162d4435", "seed_9040926c38f5",
        "seed_8f5da072ee2b", "seed_8a9023c64e76",
    },
    "val": {
        "seed_aceb430e924d", "seed_1ed2f91485cb", "seed_0025666ab8bc", "seed_d8eb5e399eb2",
        "seed_41cf38a0c17e", "seed_93405628f8a6", "seed_061054f83650", "seed_f3054d9546f9",
    },
    "test": {
        "seed_d382e715896d", "seed_546e81dc221d", "seed_42b4669351dd", "seed_f96fa34949cf",
        "seed_453f4123d6fb", "seed_4f15a566105c", "seed_4cbd996abac3", "seed_a23c0ac8b044",
        "seed_c1b8d1d09927", "seed_5a769dbbe464", "seed_3662ea861e45", "seed_25b122d5e71c",
        "seed_4d0cf7ee3edc", "seed_8949a6dd5453",
    },
}


class ReconstructionError(ValueError):
    """Raised before canonical promotion when any migration invariant fails."""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _normalized(text: str) -> str:
    return normalize_text(text).casefold()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ReconstructionError(f"{path} line {line_number} is invalid JSON: {exc}") from exc
    return records


def encode_jsonl(records: Iterable[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        for record in records
    ).encode("utf-8")


def legacy_inner_narration_texts(root: ScenarioRoot) -> tuple[str, str, str, str]:
    """Exact post-quote-strip survivors from legacy variants 1, 2, 3, and 5."""
    return (
        f"{root.relationship}. {root.pretext}. {root.requested_action}. {root.urgency}.",
        f"{root.relationship}. {root.requested_action} {root.urgency}",
        f"{root.pretext}. {root.relationship}. {root.requested_action}; {root.urgency}.",
        f"{root.relationship}. Người gửi nói {root.mechanism}. {root.pretext}. "
        f"{root.requested_action}. {root.urgency}.",
    )


def seed_to_root() -> dict[str, ScenarioRoot]:
    finalizer = object.__new__(TieredGenerator)
    mapping = {
        finalizer._derive_seed_id(seed_record_for_root(root)): root for root in SCENARIO_ROOTS
    }
    if len(mapping) != 60:
        raise ReconstructionError(f"frozen root namespace produced {len(mapping)} seeds, expected 60")
    return mapping


def class_distribution(records: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(record["label"] for record in records)
    return {label: counts.get(label, 0) for label in ALL_LABELS}


def validate_legacy_inputs(splits: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
    """Prove the exact 2,343-row Phase 39 state before reconstructing anything."""
    if set(splits) != set(SPLIT_NAMES):
        raise ReconstructionError(f"expected splits {SPLIT_NAMES}, got {sorted(splits)}")
    if sum(map(len, splits.values())) != INPUT_TOTAL:
        raise ReconstructionError("legacy corpus must contain exactly 2,343 rows")

    expected_roots = seed_to_root()
    observed_seed_split: dict[str, str] = {}
    target_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_seed_splits: dict[str, set[str]] = defaultdict(set)

    for split_name in SPLIT_NAMES:
        rows = splits[split_name]
        if len(rows) != EXPECTED_INPUT_COUNTS[split_name]:
            raise ReconstructionError(
                f"{split_name} has {len(rows)} rows, expected {EXPECTED_INPUT_COUNTS[split_name]}"
            )
        if class_distribution(rows) != EXPECTED_INPUT_DISTRIBUTION[split_name]:
            raise ReconstructionError(f"{split_name} class distribution is not the locked input state")
        for index, row in enumerate(rows):
            try:
                payload = DatasetRecord.model_validate(row).model_dump()
            except Exception as exc:
                raise ReconstructionError(f"{split_name}:{index} is not schema-valid: {exc}") from exc
            if any(not span or span not in payload["text"] for span in payload["suspicious_spans"]):
                raise ReconstructionError(f"{split_name}:{index} has an invalid suspicious span")
            all_seed_splits[payload["seed_id"]].add(split_name)
            if payload["label"] == TARGET_LABEL:
                target_groups[payload["seed_id"]].append(payload)
                observed_seed_split[payload["seed_id"]] = split_name

    leaking = {seed: names for seed, names in all_seed_splits.items() if len(names) != 1}
    if leaking:
        raise ReconstructionError(f"input already has cross-split seed leakage: {leaking}")
    if set(target_groups) != set(expected_roots):
        raise ReconstructionError("live Zalo seed set does not equal the frozen 60-root namespace")

    observed_by_split = {
        split_name: {seed for seed, assigned in observed_seed_split.items() if assigned == split_name}
        for split_name in SPLIT_NAMES
    }
    if observed_by_split != EXPECTED_ZALO_SEEDS_BY_SPLIT:
        raise ReconstructionError("live Zalo seed-to-split assignment differs from the locked Phase 39 state")

    for seed_id, root in expected_roots.items():
        rows = target_groups[seed_id]
        if len(rows) != 4:
            raise ReconstructionError(f"{seed_id}/{root.anchor} has {len(rows)} rows, expected exactly 4")
        texts = [row["text"] for row in rows]
        if len(set(texts)) != 4 or set(texts) != set(legacy_inner_narration_texts(root)):
            raise ReconstructionError(
                f"{seed_id}/{root.anchor} is not exactly the four known legacy narrator formulas"
            )
        if any(row["source"] != "synthetic_openai_compatible" for row in rows):
            raise ReconstructionError(f"{seed_id}/{root.anchor} has unexpected provenance")
    return observed_seed_split


def reconstruct_splits(
    before: dict[str, list[dict[str, Any]]],
    replacement_records: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Replace each four-row Zalo group at its first position with five direct rows."""
    validate_legacy_inputs(before)
    replacements = (
        validate_records(replacement_records)
        if replacement_records is not None
        else materialize_catalog()
    )
    replacements_by_seed: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in replacements:
        replacements_by_seed[record["seed_id"]].append(record)

    after: dict[str, list[dict[str, Any]]] = {}
    for split_name in SPLIT_NAMES:
        output: list[dict[str, Any]] = []
        emitted: set[str] = set()
        for row in before[split_name]:
            if row["label"] != TARGET_LABEL:
                output.append(copy.deepcopy(row))
                continue
            seed_id = row["seed_id"]
            if seed_id not in emitted:
                output.extend(copy.deepcopy(replacements_by_seed[seed_id]))
                emitted.add(seed_id)
        after[split_name] = output
    return after


def _assert_no_duplicates(splits: dict[str, list[dict[str, Any]]]) -> None:
    indexed: list[tuple[str, int, str]] = []
    seen: dict[str, tuple[str, int]] = {}
    for split_name in SPLIT_NAMES:
        for index, record in enumerate(splits[split_name]):
            normalized = _normalized(record["text"])
            if normalized in seen:
                other = seen[normalized]
                raise ReconstructionError(
                    f"normalized duplicate at {other} and {(split_name, index)}"
                )
            seen[normalized] = (split_name, index)
            indexed.append((split_name, index, normalized))

    for left_index, (left_split, left_row, left) in enumerate(indexed):
        for right_split, right_row, right in indexed[left_index + 1 :]:
            ratio = fuzz.ratio(left, right) / 100.0
            if ratio >= 0.95:
                raise ReconstructionError(
                    "lexical near-duplicate at "
                    f"{left_split}:{left_row}/{right_split}:{right_row} ({ratio:.3f})"
                )


def validate_projected_corpus(
    before: dict[str, list[dict[str, Any]]],
    after: dict[str, list[dict[str, Any]]],
    expected_catalog_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run every corpus, lineage, leakage, and preservation gate before writes."""
    if sum(map(len, after.values())) != OUTPUT_TOTAL:
        raise ReconstructionError("projected corpus must contain exactly 2,403 rows")

    expected_catalog = validate_records(
        expected_catalog_records if expected_catalog_records is not None else materialize_catalog()
    )
    # Rebuild the one acceptable projection from the validated static catalog.
    # This binds every field and preserves the first-occurrence group position;
    # a schema-valid forged row must never pass merely because its seed counts fit.
    expected_after = reconstruct_splits(before, expected_catalog)
    expected_zalo_by_split = {
        split_name: [
            record
            for record in expected_after[split_name]
            if record["label"] == TARGET_LABEL
        ]
        for split_name in SPLIT_NAMES
    }
    actual_zalo_by_split: dict[str, list[dict[str, Any]]] = {}
    seed_splits: dict[str, set[str]] = defaultdict(set)
    combined: list[dict[str, Any]] = []
    for split_name in SPLIT_NAMES:
        rows = after[split_name]
        if len(rows) != EXPECTED_OUTPUT_COUNTS[split_name]:
            raise ReconstructionError(
                f"projected {split_name} has {len(rows)} rows; expected {EXPECTED_OUTPUT_COUNTS[split_name]}"
            )
        distribution = class_distribution(rows)
        if distribution != EXPECTED_OUTPUT_DISTRIBUTION[split_name]:
            raise ReconstructionError(
                f"projected {split_name} class distribution differs: {distribution}"
            )
        if any(distribution[label] <= 0 for label in ALL_LABELS):
            raise ReconstructionError(f"projected {split_name} lacks an expected label")

        old_non_zalo = [row for row in before[split_name] if row["label"] != TARGET_LABEL]
        new_non_zalo = [row for row in rows if row["label"] != TARGET_LABEL]
        if new_non_zalo != old_non_zalo:
            raise ReconstructionError(f"non-Zalo records changed or moved in {split_name}")
        actual_zalo_by_split[split_name] = [
            row for row in rows if row["label"] == TARGET_LABEL
        ]

        for index, row in enumerate(rows):
            try:
                payload = DatasetRecord.model_validate(row).model_dump()
            except Exception as exc:
                raise ReconstructionError(f"projected {split_name}:{index} invalid: {exc}") from exc
            if any(not span or span not in payload["text"] for span in payload["suspicious_spans"]):
                raise ReconstructionError(f"projected {split_name}:{index} has an invalid span")
            if payload["label"] == TARGET_LABEL:
                validate_direct_message(payload["text"])
            seed_splits[payload["seed_id"]].add(split_name)
            combined.append(payload)

    leaking = {seed: names for seed, names in seed_splits.items() if len(names) != 1}
    if leaking:
        raise ReconstructionError(f"projected corpus has seed leakage: {leaking}")

    actual_zalo = [
        record for split_name in SPLIT_NAMES for record in actual_zalo_by_split[split_name]
    ]
    try:
        validate_records(actual_zalo)
    except Exception as exc:
        raise ReconstructionError(f"projected Zalo subset is not a valid 60x5 catalog: {exc}") from exc
    actual_seed_counts = Counter(record["seed_id"] for record in actual_zalo)
    expected_seed_set = set().union(*EXPECTED_ZALO_SEEDS_BY_SPLIT.values())
    if set(actual_seed_counts) != expected_seed_set or set(actual_seed_counts.values()) != {5}:
        raise ReconstructionError("projected Zalo subset must contain the exact 60 frozen seeds x5")
    for split_name in SPLIT_NAMES:
        actual_seeds = {record["seed_id"] for record in actual_zalo_by_split[split_name]}
        if actual_seeds != EXPECTED_ZALO_SEEDS_BY_SPLIT[split_name]:
            raise ReconstructionError(f"projected Zalo seed assignment changed in {split_name}")
        if actual_zalo_by_split[split_name] != expected_zalo_by_split[split_name]:
            raise ReconstructionError(
                f"projected {split_name} Zalo rows differ from the validated direct catalog"
            )
        if after[split_name] != expected_after[split_name]:
            raise ReconstructionError(
                f"projected {split_name} does not preserve the locked group positions"
            )
    _assert_no_duplicates(after)

    total = len(combined)
    seed_counts = Counter(record["seed_id"] for record in combined)
    max_seed, max_count = max(seed_counts.items(), key=lambda item: item[1])
    max_share = max_count / total
    if max_share > 0.08 + 1e-9:
        raise ReconstructionError(f"seed {max_seed} exceeds cap at {max_share:.6%}")

    ratios = {split_name: len(after[split_name]) / total for split_name in SPLIT_NAMES}
    targets = {"train": 0.8, "val": 0.1, "test": 0.1}
    if any(abs(ratios[name] - targets[name]) > 0.01 for name in SPLIT_NAMES):
        raise ReconstructionError(f"projected split ratios outside tolerance: {ratios}")
    return {
        "total_rows": total,
        "split_counts": {name: len(after[name]) for name in SPLIT_NAMES},
        "split_class_distribution": {
            name: class_distribution(after[name]) for name in SPLIT_NAMES
        },
        "unique_zalo_seeds": len(
            {record["seed_id"] for record in combined if record["label"] == TARGET_LABEL}
        ),
        "max_seed_id": max_seed,
        "max_seed_count": max_count,
        "max_seed_share": max_share,
        "split_ratios": ratios,
    }


def _authoring_source_provenance(repo_root: Path | None = None) -> dict[str, Any]:
    """Bind the generated data to source bytes and an honest scoped Git state."""
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    source_sha256: dict[str, str] = {}
    for relative_path in AUTHORING_SOURCE_PATHS:
        source_path = root / relative_path
        if not source_path.is_file():
            raise ReconstructionError(f"authoring source is missing: {relative_path}")
        source_sha256[relative_path] = _sha256_bytes(source_path.read_bytes())

    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        status = subprocess.run(
            [
                "git",
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                *AUTHORING_SOURCE_PATHS,
            ],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ReconstructionError("git is required for reconstruction provenance") from exc
    if head.returncode != 0:
        raise ReconstructionError(f"cannot resolve reconstruction Git HEAD: {head.stderr.strip()}")
    if status.returncode != 0:
        raise ReconstructionError(
            f"cannot inspect reconstruction source status: {status.stderr.strip()}"
        )
    commit = head.stdout.strip()
    if len(commit) < 40:
        raise ReconstructionError(f"resolved invalid reconstruction Git commit: {commit!r}")
    return {
        "git_commit": commit,
        "worktree_dirty": bool(status.stdout.strip()),
        "source_sha256": source_sha256,
    }


def _validate_implementation_provenance(
    provenance: dict[str, Any],
    *,
    current: dict[str, Any] | None = None,
) -> None:
    if not isinstance(provenance, dict):
        raise ReconstructionError("implementation provenance is missing")
    if not isinstance(provenance.get("git_commit"), str) or len(provenance["git_commit"]) < 40:
        raise ReconstructionError("implementation provenance has no valid Git commit")
    if not isinstance(provenance.get("worktree_dirty"), bool):
        raise ReconstructionError("implementation provenance has no honest dirty flag")
    hashes = provenance.get("source_sha256")
    if not isinstance(hashes, dict) or set(hashes) != set(AUTHORING_SOURCE_PATHS):
        raise ReconstructionError("implementation provenance does not cover every authoring source")
    if any(
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
        for value in hashes.values()
    ):
        raise ReconstructionError("implementation provenance contains an invalid source hash")
    if current is not None and provenance != current:
        raise ReconstructionError("implementation provenance is stale for the current source tree")


def build_updated_manifest(
    existing: dict[str, Any],
    split_payloads: dict[str, bytes],
    stats: dict[str, Any],
    input_hashes: dict[str, str],
    catalog_payload: bytes,
    implementation_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Preserve prior history while recording truthful local reconstruction provenance."""
    provenance = (
        copy.deepcopy(implementation_provenance)
        if implementation_provenance is not None
        else _authoring_source_provenance()
    )
    _validate_implementation_provenance(provenance)
    updated = copy.deepcopy(existing)
    updated["manifest"] = {
        "version": "phase39-f01-zalo-direct-reconstruction-v1",
        "build_timestamp": datetime.now(timezone.utc).isoformat(),
        # A dirty source tree cannot truthfully be represented by its bare HEAD.
        "git_commit": None if provenance["worktree_dirty"] else provenance["git_commit"],
        "files": {
            f"{name}.jsonl": {
                "sha256": _sha256_bytes(split_payloads[name]),
                "records": EXPECTED_OUTPUT_COUNTS[name],
                "bytes": len(split_payloads[name]),
            }
            for name in SPLIT_NAMES
        },
    }
    updated["split_class_distribution"] = stats["split_class_distribution"]
    updated["zalo_direct_semantic_reconstruction"] = {
        "finding_id": "F-01",
        "description": (
            "Replaced all 240 live narrator-derived Zalo rows (60 known seeds x 4 known "
            "legacy formulas) with 300 locally authored direct sender messages (5 per seed), "
            "preserving every seed's split assignment and every non-Zalo record."
        ),
        "wording_status": "new-semantic-reconstruction-not-verbatim-recovery",
        "input_rows_replaced": 240,
        "output_rows_added": 300,
        "unique_seed_groups": 60,
        "variants_per_seed": 5,
        "split_replacement": {
            "train": {"before": 152, "after": 190, "seeds": 38},
            "val": {"before": 32, "after": 40, "seeds": 8},
            "test": {"before": 56, "after": 70, "seeds": 14},
        },
        "corpus_rows_before": INPUT_TOTAL,
        "corpus_rows_after": OUTPUT_TOTAL,
        "non_zalo_records_preserved_exactly": True,
        "seed_to_split_assignments_preserved": True,
        "input_sha256": input_hashes,
        "catalog_sha256": _sha256_bytes(catalog_payload),
        "generation_provenance": dict(BUILD_METADATA),
        "implementation_provenance": provenance,
        "external_api_call_count": 0,
        "validation": {
            "schema_and_spans": "pass",
            "all_label_support": "pass",
            "seed_disjointness": "pass",
            "normalized_and_lexical_duplicates_at_0_95": "zero",
            "seed_cap_pct": 0.08,
            "max_seed_id": stats["max_seed_id"],
            "max_seed_count": stats["max_seed_count"],
            "max_seed_share": stats["max_seed_share"],
            "split_ratios": stats["split_ratios"],
        },
    }
    return updated


def _write_bytes_atomically(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.f01.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def verify_backup(
    backup_dir: Path,
    canonical_paths: dict[str, Path],
    input_hashes: dict[str, str],
) -> None:
    for name in (*SPLIT_NAMES, "manifest"):
        filename = f"{name}.jsonl" if name in SPLIT_NAMES else "manifest.json"
        backup_path = Path(backup_dir) / filename
        canonical_key = filename
        if not backup_path.exists():
            raise ReconstructionError(f"locked backup is missing {backup_path}")
        backup_hash = _sha256_bytes(backup_path.read_bytes())
        if backup_hash != input_hashes[canonical_key]:
            raise ReconstructionError(f"backup {backup_path} does not match locked canonical input")
        if _sha256_bytes(canonical_paths[canonical_key].read_bytes()) != backup_hash:
            raise ReconstructionError(f"canonical {filename} changed after backup")


def stage_candidate_bundle(
    candidate_dir: Path,
    after: dict[str, list[dict[str, Any]]],
    manifest: dict[str, Any],
    catalog_records: list[dict[str, Any]],
) -> dict[str, Path]:
    candidate_dir = Path(candidate_dir)
    if candidate_dir.exists() and any(candidate_dir.iterdir()):
        raise ReconstructionError(f"candidate directory is not empty: {candidate_dir}")
    split_dir = candidate_dir / "splits"
    paths: dict[str, Path] = {}
    for name in SPLIT_NAMES:
        path = split_dir / f"{name}.jsonl"
        _write_bytes_atomically(path, encode_jsonl(after[name]))
        paths[f"{name}.jsonl"] = path
    manifest_path = candidate_dir / "manifest.json"
    _write_bytes_atomically(
        manifest_path,
        (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
    )
    paths["manifest.json"] = manifest_path
    catalog_path = candidate_dir / "zalo-social-engineering-codex-2026-08-08.jsonl"
    _write_bytes_atomically(catalog_path, encode_jsonl(catalog_records))
    paths["catalog.jsonl"] = catalog_path

    reloaded = {name: read_jsonl(paths[f"{name}.jsonl"]) for name in SPLIT_NAMES}
    manifest_loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name in SPLIT_NAMES:
        payload = paths[f"{name}.jsonl"].read_bytes()
        entry = manifest_loaded["manifest"]["files"][f"{name}.jsonl"]
        if entry != {
            "sha256": _sha256_bytes(payload),
            "records": len(reloaded[name]),
            "bytes": len(payload),
        }:
            raise ReconstructionError(f"candidate manifest mismatch for {name}")
    validate_records(read_jsonl(catalog_path))
    return paths


def _validate_candidate_after_reload(
    before: dict[str, list[dict[str, Any]]], paths: dict[str, Path]
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    reloaded = {name: read_jsonl(paths[f"{name}.jsonl"]) for name in SPLIT_NAMES}
    stats = validate_projected_corpus(before, reloaded)
    return reloaded, stats


def validate_existing_candidate(
    candidate_dir: Path,
    before: dict[str, list[dict[str, Any]]],
    input_hashes: dict[str, str],
) -> tuple[dict[str, Path], dict[str, Any]]:
    """Revalidate a previously staged candidate against current code and locked input."""
    candidate_dir = Path(candidate_dir)
    paths = {
        **{
            f"{name}.jsonl": candidate_dir / "splits" / f"{name}.jsonl"
            for name in SPLIT_NAMES
        },
        "manifest.json": candidate_dir / "manifest.json",
        "catalog.jsonl": candidate_dir / "zalo-social-engineering-codex-2026-08-08.jsonl",
    }
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise ReconstructionError(f"existing candidate is incomplete: {missing}")

    _after, stats = _validate_candidate_after_reload(before, paths)
    current_catalog_payload = encode_jsonl(materialize_catalog())
    if paths["catalog.jsonl"].read_bytes() != current_catalog_payload:
        raise ReconstructionError("candidate catalog differs from the current validated source catalog")
    validate_records(read_jsonl(paths["catalog.jsonl"]))

    manifest = json.loads(paths["manifest.json"].read_text(encoding="utf-8"))
    reconstruction = manifest.get("zalo_direct_semantic_reconstruction", {})
    if reconstruction.get("input_sha256") != input_hashes:
        raise ReconstructionError("candidate manifest input hashes differ from locked canonical files")
    if reconstruction.get("external_api_call_count") != 0:
        raise ReconstructionError("candidate manifest does not prove zero external API calls")
    if reconstruction.get("wording_status") != "new-semantic-reconstruction-not-verbatim-recovery":
        raise ReconstructionError("candidate manifest overstates wording recovery provenance")
    current_provenance = _authoring_source_provenance()
    _validate_implementation_provenance(
        reconstruction.get("implementation_provenance"),
        current=current_provenance,
    )
    expected_manifest_commit = (
        None
        if current_provenance["worktree_dirty"]
        else current_provenance["git_commit"]
    )
    if manifest.get("manifest", {}).get("git_commit") != expected_manifest_commit:
        raise ReconstructionError("candidate manifest Git commit does not match its dirty state")
    for name in SPLIT_NAMES:
        payload = paths[f"{name}.jsonl"].read_bytes()
        entry = manifest["manifest"]["files"][f"{name}.jsonl"]
        expected = {
            "sha256": _sha256_bytes(payload),
            "records": EXPECTED_OUTPUT_COUNTS[name],
            "bytes": len(payload),
        }
        if entry != expected:
            raise ReconstructionError(f"existing candidate manifest mismatch for {name}")
    if reconstruction.get("catalog_sha256") != _sha256_bytes(current_catalog_payload):
        raise ReconstructionError("candidate manifest catalog hash is stale")
    return paths, stats


def refresh_manifest_implementation_provenance(
    manifest_paths: Iterable[Path],
    *,
    require_clean: bool,
) -> dict[str, Any]:
    """Refresh ignored candidate/live manifests after source review or commit.

    Every manifest is validated and encoded before the first write. If a write
    fails, all prior bytes are restored and verified with the same fail-closed
    rollback helper used for canonical promotion.
    """
    paths = [Path(path) for path in manifest_paths]
    if not paths or len(set(paths)) != len(paths):
        raise ReconstructionError("provenance refresh requires distinct manifest paths")
    provenance = _authoring_source_provenance()
    if require_clean and provenance["worktree_dirty"]:
        raise ReconstructionError("authoring sources are dirty; refusing to pin a clean commit")

    payloads: dict[str, bytes] = {}
    destinations: dict[str, Path] = {}
    originals: dict[str, bytes | None] = {}
    for index, path in enumerate(paths):
        if not path.is_file():
            raise ReconstructionError(f"manifest is missing: {path}")
        original = path.read_bytes()
        try:
            manifest = json.loads(original.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ReconstructionError(f"manifest is invalid: {path}: {exc}") from exc
        reconstruction = manifest.get("zalo_direct_semantic_reconstruction")
        if not isinstance(reconstruction, dict) or reconstruction.get("finding_id") != "F-01":
            raise ReconstructionError(f"manifest has no F-01 reconstruction history: {path}")
        reconstruction["implementation_provenance"] = copy.deepcopy(provenance)
        manifest_block = manifest.get("manifest")
        if not isinstance(manifest_block, dict):
            raise ReconstructionError(f"manifest metadata is missing: {path}")
        manifest_block["git_commit"] = (
            None if provenance["worktree_dirty"] else provenance["git_commit"]
        )
        key = f"manifest-{index}"
        destinations[key] = path
        originals[key] = original
        payloads[key] = (
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        ).encode("utf-8")

    _replace_payload_bundle(
        destinations,
        payloads,
        originals,
        operation="implementation provenance refresh",
    )
    return provenance


def _restore_and_verify_destinations(
    destinations: dict[str, Path],
    original_bytes: dict[str, bytes | None],
) -> list[str]:
    """Attempt every restoration, then independently verify every destination."""
    errors: list[str] = []
    for key, destination in destinations.items():
        try:
            original = original_bytes[key]
            if original is None:
                if destination.exists():
                    destination.unlink()
            else:
                _write_bytes_atomically(destination, original)
        except Exception as exc:  # Continue: partial rollback is worse than a composite report.
            errors.append(f"restore {key}: {type(exc).__name__}: {exc}")

    for key, destination in destinations.items():
        try:
            original = original_bytes[key]
            if original is None:
                if destination.exists():
                    errors.append(f"verify {key}: expected destination to be absent")
                continue
            if not destination.is_file():
                errors.append(f"verify {key}: destination is missing")
                continue
            actual = destination.read_bytes()
            expected_hash = _sha256_bytes(original)
            actual_hash = _sha256_bytes(actual)
            if actual_hash != expected_hash or len(actual) != len(original):
                errors.append(
                    f"verify {key}: expected sha256={expected_hash}/bytes={len(original)}, "
                    f"got sha256={actual_hash}/bytes={len(actual)}"
                )
        except Exception as exc:
            errors.append(f"verify {key}: {type(exc).__name__}: {exc}")
    return errors


def _replace_payload_bundle(
    destinations: dict[str, Path],
    payloads: dict[str, bytes],
    original_bytes: dict[str, bytes | None],
    *,
    operation: str,
    verify_promoted: Callable[[], None] | None = None,
) -> None:
    expected_keys = set(destinations)
    if set(payloads) != expected_keys or set(original_bytes) != expected_keys:
        raise ReconstructionError(f"{operation} bundle keys are inconsistent")
    try:
        for key, destination in destinations.items():
            _write_bytes_atomically(destination, payloads[key])
        for key, destination in destinations.items():
            actual = destination.read_bytes()
            expected = payloads[key]
            if (
                len(actual) != len(expected)
                or _sha256_bytes(actual) != _sha256_bytes(expected)
            ):
                raise ReconstructionError(
                    f"{operation} post-write verification failed for {key}"
                )
        if verify_promoted is not None:
            verify_promoted()
    except Exception as exc:
        rollback_errors = _restore_and_verify_destinations(destinations, original_bytes)
        if rollback_errors:
            details = "; ".join(rollback_errors)
            raise ReconstructionError(
                f"{operation} failed ({type(exc).__name__}: {exc}); "
                f"rollback incomplete: {details}"
            ) from exc
        raise


def promote_candidate(
    candidate_paths: dict[str, Path],
    canonical_paths: dict[str, Path],
    original_bytes: dict[str, bytes | None],
    catalog_output: Path,
    verify_promoted: Callable[[], None] | None = None,
) -> None:
    """Promote validated candidates; restore every original byte if any replace fails."""
    destinations = {
        **{f"{name}.jsonl": canonical_paths[f"{name}.jsonl"] for name in SPLIT_NAMES},
        "manifest.json": canonical_paths["manifest.json"],
        "catalog.jsonl": Path(catalog_output),
    }
    payloads = {key: candidate_paths[key].read_bytes() for key in destinations}
    _replace_payload_bundle(
        destinations,
        payloads,
        original_bytes,
        operation="candidate promotion",
        verify_promoted=verify_promoted,
    )


def _validate_promoted_bundle(
    before: dict[str, list[dict[str, Any]]],
    canonical_paths: dict[str, Path],
    manifest_path: Path,
    catalog_output: Path,
    expected_catalog_payload: bytes,
) -> None:
    promoted = {name: read_jsonl(canonical_paths[f"{name}.jsonl"]) for name in SPLIT_NAMES}
    validate_projected_corpus(before, promoted)
    promoted_manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    for name in SPLIT_NAMES:
        payload = canonical_paths[f"{name}.jsonl"].read_bytes()
        entry = promoted_manifest["manifest"]["files"][f"{name}.jsonl"]
        expected = {
            "sha256": _sha256_bytes(payload),
            "records": EXPECTED_OUTPUT_COUNTS[name],
            "bytes": len(payload),
        }
        if entry != expected:
            raise ReconstructionError(f"promoted manifest mismatch for {name}")
    if Path(catalog_output).read_bytes() != expected_catalog_payload:
        raise ReconstructionError("promoted catalog artifact differs from the validated candidate")


def run_reconstruction(
    splits_dir: Path,
    manifest_path: Path,
    backup_dir: Path,
    candidate_dir: Path,
    catalog_output: Path,
    *,
    promote: bool,
) -> dict[str, Any]:
    canonical_paths = {
        **{f"{name}.jsonl": Path(splits_dir) / f"{name}.jsonl" for name in SPLIT_NAMES},
        "manifest.json": Path(manifest_path),
    }
    original_bytes: dict[str, bytes | None] = {
        key: path.read_bytes() for key, path in canonical_paths.items()
    }
    original_bytes["catalog.jsonl"] = (
        Path(catalog_output).read_bytes() if Path(catalog_output).exists() else None
    )
    input_hashes = {
        key: _sha256_bytes(payload)
        for key, payload in original_bytes.items()
        if key != "catalog.jsonl" and payload is not None
    }
    if input_hashes != EXPECTED_CANONICAL_SHA256:
        raise ReconstructionError(
            f"canonical inputs do not match the locked Phase 39 hashes: {input_hashes}"
        )
    verify_backup(backup_dir, canonical_paths, input_hashes)

    before = {name: read_jsonl(canonical_paths[f"{name}.jsonl"]) for name in SPLIT_NAMES}
    validate_legacy_inputs(before)
    catalog_records = materialize_catalog()
    after = reconstruct_splits(before, catalog_records)
    stats = validate_projected_corpus(before, after, catalog_records)
    split_payloads = {name: encode_jsonl(after[name]) for name in SPLIT_NAMES}
    catalog_payload = encode_jsonl(catalog_records)
    existing_manifest = json.loads((original_bytes["manifest.json"] or b"").decode("utf-8"))
    manifest = build_updated_manifest(
        existing_manifest, split_payloads, stats, input_hashes, catalog_payload
    )
    candidate_paths = stage_candidate_bundle(candidate_dir, after, manifest, catalog_records)
    _validate_candidate_after_reload(before, candidate_paths)

    if promote:
        current_hashes = {
            key: _sha256_bytes(path.read_bytes()) for key, path in canonical_paths.items()
        }
        if current_hashes != input_hashes:
            raise ReconstructionError("canonical inputs changed between validation and promotion")
        promote_candidate(
            candidate_paths,
            canonical_paths,
            original_bytes,
            catalog_output,
            verify_promoted=lambda: _validate_promoted_bundle(
                before,
                canonical_paths,
                manifest_path,
                catalog_output,
                catalog_payload,
            ),
        )

    return {
        **stats,
        "candidate_dir": str(Path(candidate_dir)),
        "promoted": promote,
        "input_sha256": input_hashes,
        "candidate_sha256": {
            key: _sha256_bytes(path.read_bytes()) for key, path in candidate_paths.items()
        },
    }


def promote_existing_candidate(
    splits_dir: Path,
    manifest_path: Path,
    backup_dir: Path,
    candidate_dir: Path,
    catalog_output: Path,
) -> dict[str, Any]:
    """Promote only a previously staged and independently revalidated candidate."""
    canonical_paths = {
        **{f"{name}.jsonl": Path(splits_dir) / f"{name}.jsonl" for name in SPLIT_NAMES},
        "manifest.json": Path(manifest_path),
    }
    original_bytes: dict[str, bytes | None] = {
        key: path.read_bytes() for key, path in canonical_paths.items()
    }
    original_bytes["catalog.jsonl"] = (
        Path(catalog_output).read_bytes() if Path(catalog_output).exists() else None
    )
    input_hashes = {
        key: _sha256_bytes(payload)
        for key, payload in original_bytes.items()
        if key != "catalog.jsonl" and payload is not None
    }
    if input_hashes != EXPECTED_CANONICAL_SHA256:
        raise ReconstructionError("canonical inputs changed before existing-candidate promotion")
    verify_backup(backup_dir, canonical_paths, input_hashes)
    before = {name: read_jsonl(canonical_paths[f"{name}.jsonl"]) for name in SPLIT_NAMES}
    validate_legacy_inputs(before)
    candidate_paths, stats = validate_existing_candidate(candidate_dir, before, input_hashes)
    catalog_payload = candidate_paths["catalog.jsonl"].read_bytes()

    current_hashes = {
        key: _sha256_bytes(path.read_bytes()) for key, path in canonical_paths.items()
    }
    if current_hashes != input_hashes:
        raise ReconstructionError("canonical inputs changed during candidate revalidation")
    promote_candidate(
        candidate_paths,
        canonical_paths,
        original_bytes,
        catalog_output,
        verify_promoted=lambda: _validate_promoted_bundle(
            before,
            canonical_paths,
            manifest_path,
            catalog_output,
            catalog_payload,
        ),
    )
    return {
        **stats,
        "candidate_dir": str(Path(candidate_dir)),
        "promoted": True,
        "input_sha256": input_hashes,
        "output_sha256": {
            key: _sha256_bytes(path.read_bytes()) for key, path in canonical_paths.items()
        },
        "catalog_sha256": _sha256_bytes(Path(catalog_output).read_bytes()),
    }


def validate_promoted_state(
    splits_dir: Path,
    manifest_path: Path,
    backup_dir: Path,
    candidate_dir: Path,
    catalog_output: Path,
) -> dict[str, Any]:
    """Re-audit an already promoted corpus against backup, source, and candidate bytes."""
    backup_paths = {
        **{
            f"{name}.jsonl": Path(backup_dir) / f"{name}.jsonl"
            for name in SPLIT_NAMES
        },
        "manifest.json": Path(backup_dir) / "manifest.json",
    }
    missing_backup = [str(path) for path in backup_paths.values() if not path.is_file()]
    if missing_backup:
        raise ReconstructionError(f"locked backup is incomplete: {missing_backup}")
    backup_hashes = {
        key: _sha256_bytes(path.read_bytes()) for key, path in backup_paths.items()
    }
    if backup_hashes != EXPECTED_CANONICAL_SHA256:
        raise ReconstructionError(f"locked backup hashes changed: {backup_hashes}")
    before = {
        name: read_jsonl(backup_paths[f"{name}.jsonl"])
        for name in SPLIT_NAMES
    }
    validate_legacy_inputs(before)

    candidate_paths, stats = validate_existing_candidate(
        candidate_dir,
        before,
        backup_hashes,
    )
    canonical_paths = {
        **{f"{name}.jsonl": Path(splits_dir) / f"{name}.jsonl" for name in SPLIT_NAMES},
        "manifest.json": Path(manifest_path),
    }
    live_destinations = {
        **canonical_paths,
        "catalog.jsonl": Path(catalog_output),
    }
    missing_live = [str(path) for path in live_destinations.values() if not path.is_file()]
    if missing_live:
        raise ReconstructionError(f"promoted corpus is incomplete: {missing_live}")
    for key, live_path in live_destinations.items():
        live_payload = live_path.read_bytes()
        candidate_payload = candidate_paths[key].read_bytes()
        if live_payload != candidate_payload:
            raise ReconstructionError(f"promoted {key} differs from the verified candidate")

    catalog_payload = candidate_paths["catalog.jsonl"].read_bytes()
    _validate_promoted_bundle(
        before,
        canonical_paths,
        manifest_path,
        catalog_output,
        catalog_payload,
    )
    return {
        **stats,
        "promoted_state_valid": True,
        "input_sha256": backup_hashes,
        "output_sha256": {
            key: _sha256_bytes(path.read_bytes())
            for key, path in live_destinations.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstruct the F-01 Zalo direct-message corpus.")
    parser.add_argument("--splits-dir", type=Path, default=Path("data/splits"))
    parser.add_argument("--manifest-path", type=Path, default=Path("data/manifests/manifest.json"))
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path("data/processed/f01-zalo-reconstruction-backup-20260817"),
    )
    parser.add_argument(
        "--candidate-dir",
        type=Path,
        default=Path("data/processed/f01-zalo-direct-candidate-20260817-verified"),
    )
    parser.add_argument(
        "--catalog-output",
        type=Path,
        default=Path("data/synthetic/zalo-social-engineering-codex-2026-08-08.jsonl"),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--promote",
        action="store_true",
        help="Build, validate, and promote a new candidate; default is candidate-only.",
    )
    mode.add_argument(
        "--promote-existing-candidate",
        action="store_true",
        help="Revalidate and promote the already staged candidate without rebuilding it.",
    )
    mode.add_argument(
        "--refresh-provenance",
        action="store_true",
        help="Refresh source hashes/Git state in live and candidate manifests.",
    )
    mode.add_argument(
        "--verify-promoted-state",
        action="store_true",
        help="Revalidate live bytes against the locked backup and verified candidate.",
    )
    parser.add_argument(
        "--require-clean-provenance",
        action="store_true",
        help="With --refresh-provenance, fail unless all authoring sources are committed.",
    )
    args = parser.parse_args()
    if args.require_clean_provenance and not args.refresh_provenance:
        parser.error("--require-clean-provenance requires --refresh-provenance")
    if args.refresh_provenance:
        provenance = refresh_manifest_implementation_provenance(
            [args.manifest_path, args.candidate_dir / "manifest.json"],
            require_clean=args.require_clean_provenance,
        )
        stats = {
            "provenance_refreshed": True,
            "manifest_paths": [
                str(args.manifest_path),
                str(args.candidate_dir / "manifest.json"),
            ],
            "implementation_provenance": provenance,
        }
    elif args.verify_promoted_state:
        stats = validate_promoted_state(
            args.splits_dir,
            args.manifest_path,
            args.backup_dir,
            args.candidate_dir,
            args.catalog_output,
        )
    elif args.promote_existing_candidate:
        stats = promote_existing_candidate(
            args.splits_dir,
            args.manifest_path,
            args.backup_dir,
            args.candidate_dir,
            args.catalog_output,
        )
    else:
        stats = run_reconstruction(
            args.splits_dir,
            args.manifest_path,
            args.backup_dir,
            args.candidate_dir,
            args.catalog_output,
            promote=args.promote,
        )
    print(json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
