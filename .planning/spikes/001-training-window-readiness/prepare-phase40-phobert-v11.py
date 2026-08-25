from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import uuid

from src.model_adaptation import phase40_handoff as handoff


PACKAGE_ROOT = Path(r"D:\PROJEct\AI MODELS\phase40-full-local-20260825")
FROZEN_RUNTIME = PACKAGE_ROOT / "source-runtime-v9"
FROZEN_TRANSFER_ROOT = PACKAGE_ROOT / "transfer-root-v3"
TARGET_RUNTIME = PACKAGE_ROOT / "source-runtime-v11"
TARGET_TRANSFER_ROOT = PACKAGE_ROOT / "transfer-root-v4"
TESTED_PHOBERT_SOURCE = Path("src/model_adaptation/phobert_training.py").resolve()
NEW_PHOBERT_RUN_ID = "phase40-phobert-full-seed42-v11"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _make_read_only(path: Path) -> None:
    path.chmod(path.stat().st_mode & ~stat.S_IWRITE)


def _publish_directory(staging: Path, target: Path) -> None:
    if target.exists():
        raise FileExistsError(f"refusing existing v11 target: {target}")
    staging.replace(target)


def main() -> int:
    for target in (TARGET_RUNTIME, TARGET_TRANSFER_ROOT):
        if target.exists():
            raise FileExistsError(f"refusing existing v11 target: {target}")

    build_id = uuid.uuid4().hex
    runtime_stage = PACKAGE_ROOT / f"source-runtime-v11.staging-{build_id}"
    transfer_stage = PACKAGE_ROOT / f"transfer-root-v4.staging-{build_id}"
    if runtime_stage.exists() or transfer_stage.exists():
        raise FileExistsError("unexpected v11 staging collision")

    old_manifest_path = (
        FROZEN_TRANSFER_ROOT
        / "data"
        / "models"
        / "phase40"
        / "source"
        / "phase40-source-manifest.json"
    )
    old_request_path = (
        FROZEN_TRANSFER_ROOT / "data" / "models" / "phase40" / "full-run-request.json"
    )
    old_input_path = (
        FROZEN_TRANSFER_ROOT
        / "data"
        / "models"
        / "phase40"
        / "input"
        / "phase40-train-validation.zip"
    )
    old_manifest = handoff.SourceInventory.model_validate_json(old_manifest_path.read_bytes())
    old_request = handoff.RunRequest.model_validate_json(old_request_path.read_bytes())
    old_by_path = {entry.path: entry for entry in old_manifest.files}
    allowlist = tuple(sorted(handoff.PHASE40_SOURCE_ALLOWLIST))
    if tuple(old_by_path) != allowlist:
        raise RuntimeError("frozen v9 manifest is not the exact source allowlist")

    entries: list[handoff.SourceInventoryEntry] = []
    members: list[tuple[str, bytes]] = []
    for relative in allowlist:
        frozen_source = FROZEN_RUNTIME / Path(relative)
        frozen_payload = frozen_source.read_bytes()
        frozen_entry = old_by_path[relative]
        if len(frozen_payload) != frozen_entry.bytes or _sha256(frozen_payload) != frozen_entry.sha256:
            raise RuntimeError(f"frozen v9 runtime identity changed: {relative}")
        source = TESTED_PHOBERT_SOURCE if relative == "src/model_adaptation/phobert_training.py" else frozen_source
        payload = source.read_bytes()
        destination = runtime_stage / Path(relative)
        _write_exclusive(destination, payload)
        entries.append(
            handoff.SourceInventoryEntry(
                path=relative,
                bytes=len(payload),
                sha256=_sha256(payload),
            )
        )
        members.append((relative, payload))

    archive_bytes = handoff._deterministic_zip(tuple(members))
    inventory = handoff.SourceInventory(
        archive_sha256=_sha256(archive_bytes),
        files=tuple(entries),
    )
    inventory_bytes = handoff._canonical_json_bytes(inventory.model_dump(mode="json"))
    source_root = transfer_stage / "data" / "models" / "phase40" / "source"
    archive_path = source_root / "phase40-source.zip"
    inventory_path = source_root / "phase40-source-manifest.json"
    _write_exclusive(archive_path, archive_bytes)
    _write_exclusive(inventory_path, inventory_bytes)
    source_reference = handoff.SourceBundleReference(
        archive_sha256=_sha256(archive_bytes),
        inventory_sha256=_sha256(inventory_bytes),
        files=inventory.files,
    )

    input_path = (
        transfer_stage
        / "data"
        / "models"
        / "phase40"
        / "input"
        / "phase40-train-validation.zip"
    )
    input_path.parent.mkdir(parents=True, exist_ok=True)
    with old_input_path.open("rb") as source_handle, input_path.open("xb") as target_handle:
        shutil.copyfileobj(source_handle, target_handle, length=1024 * 1024)
        target_handle.flush()
        os.fsync(target_handle.fileno())
    if _sha256(input_path.read_bytes()) != old_request.input_bundle.archive_sha256:
        raise RuntimeError("copied train/validation input archive identity changed")

    request_payload = old_request.model_dump(mode="json")
    request_payload["source_bundle"] = source_reference.model_dump(mode="json")
    old_phobert_run_id = next(
        run["run_id"]
        for run in request_payload["runs"]
        if run["model_family"] == "phobert"
    )
    for run in request_payload["runs"]:
        if run["run_id"] == old_phobert_run_id:
            run["run_id"] = NEW_PHOBERT_RUN_ID

    template_payload = request_payload["control_template_by_run"].pop(old_phobert_run_id)
    for control in template_payload["controls_without_accelerator"]["additional_controls"]:
        if control["name"] == "source_archive_sha256":
            control["value"] = source_reference.archive_sha256
        elif control["name"] == "source_inventory_sha256":
            control["value"] = source_reference.inventory_sha256
    template = handoff.RequestedControlTemplate.model_validate(template_payload)
    request_payload["control_template_by_run"][NEW_PHOBERT_RUN_ID] = template.model_dump(mode="json")
    request_payload["control_template_digest_by_run"].pop(old_phobert_run_id)
    request_payload["control_template_digest_by_run"][NEW_PHOBERT_RUN_ID] = template.sha256
    request = handoff.RunRequest.model_validate(request_payload)
    request_bytes = handoff._canonical_json_bytes(request.model_dump(mode="json"))
    request_path = transfer_stage / "data" / "models" / "phase40" / "full-run-request.json"
    _write_exclusive(request_path, request_bytes)

    handoff.verify_phase40_source_bundle(repo_root=transfer_stage, reference=source_reference)
    handoff.verify_phase40_run_request(request, repo_root=transfer_stage, verify_input=True)
    for entry in inventory.files:
        runtime_path = runtime_stage / Path(entry.path)
        payload = runtime_path.read_bytes()
        if len(payload) != entry.bytes or _sha256(payload) != entry.sha256:
            raise RuntimeError(f"staged v11 runtime differs from its manifest: {entry.path}")

    for entry in inventory.files:
        _make_read_only(runtime_stage / Path(entry.path))
    for authority in (archive_path, inventory_path, input_path, request_path):
        _make_read_only(authority)

    _publish_directory(runtime_stage, TARGET_RUNTIME)
    _publish_directory(transfer_stage, TARGET_TRANSFER_ROOT)

    result = {
        "request_path": str(
            TARGET_TRANSFER_ROOT / "data" / "models" / "phase40" / "full-run-request.json"
        ),
        "request_sha256": _sha256(request_bytes),
        "run_id": NEW_PHOBERT_RUN_ID,
        "source_archive_sha256": source_reference.archive_sha256,
        "source_inventory_sha256": source_reference.inventory_sha256,
        "source_file_count": len(inventory.files),
        "source_runtime": str(TARGET_RUNTIME),
        "tested_phobert_source_sha256": next(
            entry.sha256
            for entry in inventory.files
            if entry.path == "src/model_adaptation/phobert_training.py"
        ),
        "transfer_root": str(TARGET_TRANSFER_ROOT),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
