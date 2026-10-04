from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from src.model_adaptation.phase40_notebooks import (
    notebook_source_sha256,
    validate_phase40_notebook,
    validate_phase40_notebooks,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_ROOT = REPO_ROOT / "notebooks" / "phase40"
CANONICAL_NAMES = (
    "phobert_colab.ipynb",
    "qwen_lora_colab.ipynb",
    "qwen_qlora_colab.ipynb",
)


def _load(name: str) -> dict[str, object]:
    return json.loads((NOTEBOOK_ROOT / name).read_text(encoding="utf-8"))


def _cell(notebook: dict[str, object], role: str) -> dict[str, object]:
    return next(
        cell
        for cell in notebook["cells"]  # type: ignore[index]
        if cell["metadata"]["phase40_role"] == role  # type: ignore[index]
    )


def _source(cell: dict[str, object]) -> str:
    source = cell["source"]
    return source if isinstance(source, str) else "".join(source)  # type: ignore[arg-type]


def _write(tmp_path: Path, name: str, notebook: dict[str, object]) -> Path:
    destination = tmp_path / name
    destination.write_text(
        json.dumps(notebook, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return destination


def _mutate_role(
    tmp_path: Path,
    *,
    name: str = "qwen_lora_colab.ipynb",
    role: str,
    append: str = "",
    old: str | None = None,
    new: str = "",
) -> Path:
    notebook = _load(name)
    cell = _cell(notebook, role)
    source = _source(cell)
    if old is not None:
        assert old in source
        source = source.replace(old, new, 1)
    source += append
    cell["source"] = [source]
    return _write(tmp_path, name, notebook)


def _codes(path: Path) -> set[str]:
    return {issue.code for issue in validate_phase40_notebook(path)}


def test_three_fresh_canonical_notebooks_pass_static_validation() -> None:
    assert validate_phase40_notebooks(NOTEBOOK_ROOT) == ()
    for name in CANONICAL_NAMES:
        notebook = _load(name)
        for cell in notebook["cells"]:  # type: ignore[index]
            if cell["cell_type"] == "code":  # type: ignore[index]
                assert cell["execution_count"] is None  # type: ignore[index]
                assert cell["outputs"] == []  # type: ignore[index]
        digest = notebook_source_sha256(NOTEBOOK_ROOT / name)
        assert len(digest) == 64
        assert set(digest) <= set("0123456789abcdef")


def test_notebook_directory_is_closed_to_missing_or_extra_artifacts(tmp_path: Path) -> None:
    for name in CANONICAL_NAMES:
        shutil.copy2(NOTEBOOK_ROOT / name, tmp_path / name)
    (tmp_path / CANONICAL_NAMES[0]).unlink()
    (tmp_path / "historical.ipynb").write_text("{}", encoding="utf-8")
    assert "notebook-set" in {issue.code for issue in validate_phase40_notebooks(tmp_path)}


@pytest.mark.parametrize(
    ("role", "payload", "expected_code"),
    (
        ("full-run", '\nlegacy = "data/splits/recovered-balanced/train.jsonl"\n', "stale-data-path"),
        ("full-run", '\npersonal = r"C:\\Users\\operator\\rows.jsonl"\n', "personal-path"),
        ("full-run", '\napi_key = "embedded-value"\n', "embedded-secret"),
        ("full-run", "\nimport openai\n", "external-inference"),
        ("full-run", '\nparts = Path("/content/drive").glob("**")\n', "broad-discovery"),
        ("full-run", '\nreserved = open("/content/test.jsonl")\n', "reserved-reader"),
        ("full-run", "\ntrainer = Trainer(model=None)\n", "inline-implementation"),
        ("full-run", '\nlegacy_flag = "--full-precision"\n', "implicit-mode"),
        ("full-run", '\nprobe_adapter = Path("/content/probe")\n', "probe-lineage"),
        ("source-verify", "\nfrom src.model_adaptation.training import run_training\n", "source-order"),
        ("source-extract", '\nearly = open(INPUT_EXTRACTION_ROOT / "train.jsonl")\n', "input-order"),
        ("source-extract", '\nINPUT_EXTRACTION_ROOT.mkdir(parents=True)\n', "input-order"),
        ("full-run", '\nalternate = "/content/drive/MyDrive/other/input.zip"\n', "alternate-drive-path"),
        ("model-acquire", "\nsnapshot_download(MODEL_ID)\n", "inline-implementation"),
    ),
)
def test_forbidden_source_mutations_fail_closed(
    tmp_path: Path,
    role: str,
    payload: str,
    expected_code: str,
) -> None:
    path = _mutate_role(tmp_path, role=role, append=payload)
    assert expected_code in _codes(path)


def test_unpinned_dependency_mutation_is_rejected(tmp_path: Path) -> None:
    path = _mutate_role(
        tmp_path,
        role="constants",
        old="transformers==5.9.0",
        new="transformers>=5.9.0",
    )
    assert "unpinned-dependency" in _codes(path)


def test_torch_install_cannot_be_skipped(tmp_path: Path) -> None:
    path = _mutate_role(
        tmp_path,
        role="constants",
        old="tuple(pin for pin in DEPENDENCY_PINS if pin not in MODE_NO_DEPS_PINS)",
        new="DEPENDENCY_PINS[1:]",
    )
    assert "torch-install" in _codes(path)


@pytest.mark.parametrize(
    ("role", "old", "new", "expected_code"),
    (
        ("source-verify", 'source_reference.get("archive_sha256")', 'source_reference.get("archive_sha257")', "controller-source-drift"),
        ("source-verify", 'source_reference.get("inventory_sha256")', 'source_reference.get("inventory_sha257")', "controller-source-drift"),
        ("source-verify", '!= source_reference.get("archive_sha256")', '== source_reference.get("archive_sha256")', "controller-source-drift"),
        ("source-verify", "io.BytesIO(source_archive_bytes)", "source_archive_path", "missing-source-verify-contract"),
        ("request-verify", 'CONTROL_VALUES.get("model_id")', 'CONTROL_VALUES.get("alternate_model_id")', "missing-request-verify-contract"),
        ("input-verify", "input_authority.archive_sha256", "input_authority.archive_sha257", "missing-input-verify-contract"),
        ("input-verify", "input_authority.manifest_sha256", "input_authority.manifest_sha257", "missing-input-verify-contract"),
        ("input-verify", "data_member.ordered_row_ids_sha256", "data_member.ordered_row_ids_sha257", "missing-input-verify-contract"),
        ("input-verify", "phase40-snapshot-row-id-v1", "phase40-snapshot-row-id-v2", "controller-source-drift"),
    ),
)
def test_hash_and_manifest_verification_mutations_are_rejected(
    tmp_path: Path,
    role: str,
    old: str,
    new: str,
    expected_code: str,
) -> None:
    path = _mutate_role(tmp_path, role=role, old=old, new=new)
    assert expected_code in _codes(path)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("model_revision", "0" * 40),
        ("adaptation_mode", "qlora"),
        ("run_kind", "probe"),
        ("start_origin", "resume"),
        ("source_archive_path", "source.zip"),
        ("source_inventory_path", "manifest.json"),
        ("input_archive_drive_path", "/content/alternate.zip"),
        ("input_extraction_root", "/content/alternate-root"),
        ("qwen_matched_config", "drifted-controls"),
        ("model_repository_relative_path", "data/models/phase40/base/alternate"),
        (
            "model_provenance_repository_relative_path",
            "data/models/phase40/base/alternate.provenance.json",
        ),
    ),
)
def test_closed_metadata_contract_rejects_identity_or_path_drift(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    notebook = _load("qwen_lora_colab.ipynb")
    notebook["metadata"]["phase40"][field] = value  # type: ignore[index]
    path = _write(tmp_path, "qwen_lora_colab.ipynb", notebook)
    assert "metadata-contract" in _codes(path)


def test_extra_or_test_like_input_member_is_rejected(tmp_path: Path) -> None:
    notebook = _load("qwen_lora_colab.ipynb")
    notebook["metadata"]["phase40"]["input_members"].append("test.jsonl")  # type: ignore[index]
    path = _write(tmp_path, "qwen_lora_colab.ipynb", notebook)
    assert "metadata-contract" in _codes(path)


def test_source_extraction_cannot_move_before_source_verification(tmp_path: Path) -> None:
    notebook = _load("qwen_lora_colab.ipynb")
    cells = notebook["cells"]  # type: ignore[index]
    verify_index = next(
        index
        for index, cell in enumerate(cells)
        if cell["metadata"]["phase40_role"] == "source-verify"
    )
    extract_index = next(
        index
        for index, cell in enumerate(cells)
        if cell["metadata"]["phase40_role"] == "source-extract"
    )
    cells[verify_index], cells[extract_index] = cells[extract_index], cells[verify_index]
    path = _write(tmp_path, "qwen_lora_colab.ipynb", notebook)
    assert {"cell-layout", "source-order"} & _codes(path)


def test_input_verifier_cannot_move_after_full_run(tmp_path: Path) -> None:
    notebook = _load("qwen_lora_colab.ipynb")
    cells = notebook["cells"]  # type: ignore[index]
    verify_index = next(
        index
        for index, cell in enumerate(cells)
        if cell["metadata"]["phase40_role"] == "input-verify"
    )
    run_index = next(
        index
        for index, cell in enumerate(cells)
        if cell["metadata"]["phase40_role"] == "full-run"
    )
    cells[verify_index], cells[run_index] = cells[run_index], cells[verify_index]
    path = _write(tmp_path, "qwen_lora_colab.ipynb", notebook)
    assert "cell-layout" in _codes(path)


def test_model_acquisition_must_follow_typed_request_verification(tmp_path: Path) -> None:
    notebook = _load("qwen_lora_colab.ipynb")
    cells = notebook["cells"]  # type: ignore[index]
    request_index = next(
        index
        for index, cell in enumerate(cells)
        if cell["metadata"]["phase40_role"] == "request-verify"
    )
    acquisition_index = next(
        index
        for index, cell in enumerate(cells)
        if cell["metadata"]["phase40_role"] == "model-acquire"
    )
    cells[request_index], cells[acquisition_index] = (
        cells[acquisition_index],
        cells[request_index],
    )
    path = _write(tmp_path, "qwen_lora_colab.ipynb", notebook)
    assert "cell-layout" in _codes(path)


def test_model_acquisition_authority_and_sealed_manifest_are_mandatory(
    tmp_path: Path,
) -> None:
    path = _mutate_role(
        tmp_path,
        role="model-acquire",
        old="--authorize-model-acquisition",
        new="--acquire-without-authority",
    )
    assert "missing-model-acquire-contract" in _codes(path)


def test_full_run_requires_verified_model_snapshot(tmp_path: Path) -> None:
    path = _mutate_role(
        tmp_path,
        role="full-run",
        old="MODEL_SNAPSHOT_VERIFIED",
        new="MODEL_SNAPSHOT_UNCHECKED",
    )
    assert "missing-full-run-contract" in _codes(path)


def test_executed_outputs_are_not_accepted_as_canonical_source(tmp_path: Path) -> None:
    notebook = _load("qwen_lora_colab.ipynb")
    cell = _cell(notebook, "doctor")
    cell["execution_count"] = 1
    cell["outputs"] = [{"output_type": "stream", "name": "stdout", "text": "ok"}]
    path = _write(tmp_path, "qwen_lora_colab.ipynb", notebook)
    assert "executed-notebook" in _codes(path)


def test_mode_specific_pins_and_positive_commands_are_exact() -> None:
    lora = _load("qwen_lora_colab.ipynb")
    qlora = _load("qwen_qlora_colab.ipynb")
    phobert = _load("phobert_colab.ipynb")
    lora_code = "\n".join(
        _source(cell) for cell in lora["cells"] if cell["cell_type"] == "code"  # type: ignore[index]
    )
    qlora_code = "\n".join(
        _source(cell) for cell in qlora["cells"] if cell["cell_type"] == "code"  # type: ignore[index]
    )
    phobert_code = "\n".join(
        _source(cell) for cell in phobert["cells"] if cell["cell_type"] == "code"  # type: ignore[index]
    )
    assert '"phase40-train-qwen", "--adaptation-mode", "lora"' in lora_code
    assert '"phase40-train-qwen", "--adaptation-mode", "qlora"' in qlora_code
    assert '"phase40-train-phobert"' in phobert_code
    for code in (lora_code, qlora_code, phobert_code):
        assert "src.model_adaptation.phase40_operator" in code
        assert "src.model_adaptation.cli" not in code
    assert "bitsandbytes==0.50.1" not in lora_code
    assert "bitsandbytes==0.50.1" in qlora_code
    assert "peft==0.19.1" not in phobert_code
    assert "bitsandbytes==0.50.1" not in phobert_code
    assert "underthesea==9.5.0" in phobert_code


def test_notebooks_contain_no_local_trainer_metric_graph_or_external_inference() -> None:
    forbidden = (
        "Trainer(",
        "TrainingArguments(",
        "AutoModel",
        "AutoTokenizer",
        "compute_metrics",
        "confusion_matrix(",
        "matplotlib.pyplot",
        "openai",
        "anthropic",
        "http://",
        "data/splits",
        "recovered-balanced",
    )
    for name in CANONICAL_NAMES:
        notebook = _load(name)
        code = "\n".join(
            _source(cell)
            for cell in notebook["cells"]  # type: ignore[index]
            if cell["cell_type"] == "code"  # type: ignore[index]
        )
        for needle in forbidden:
            assert needle not in code
        without_torch_index = code.replace(
            "https://download.pytorch.org/whl/cu132", ""
        )
        assert "https://" not in without_torch_index


def test_full_profiles_logs_fresh_runtime_and_qwen_gguf_download_are_closed() -> None:
    for name in CANONICAL_NAMES:
        notebook = _load(name)
        phase = notebook["metadata"]["phase40"]  # type: ignore[index]
        expected_steps = 1245 if phase["model_family"] == "qwen" else 312
        assert phase["full_optimizer_steps"] == expected_steps
        code = "\n".join(
            _source(cell)
            for cell in notebook["cells"]  # type: ignore[index]
            if cell["cell_type"] == "code"  # type: ignore[index]
        )
        assert "FRESH_RUNTIME_REQUIRED = True" in code
        assert "subprocess.Popen" in code
        assert "OPERATOR_LOG_ROOT" in code
        assert f"FULL_OPTIMIZER_STEPS = {expected_steps}" in code
        if phase["model_family"] == "qwen":
            assert "phase40-gguf-export-v1" in code
            assert "GGUF_MANIFEST_VERIFIED = True" in code
            assert "ENABLE_BROWSER_DOWNLOAD = False" in code
            assert "files.download" in code
            assert "gguf==0.19.0" in code
            assert "llama-cpp-python==0.3.23" in code
        else:
            assert "files.download" not in code


def test_lora_existing_operator_logs_defer_to_explicit_exact_resume_gate() -> None:
    notebook = _load("qwen_lora_colab.ipynb")
    request_source = _source(_cell(notebook, "request-verify"))
    resume_source = _source(_cell(notebook, "resume-policy"))

    assert "OPERATOR_LOG_ROOT_PREEXISTED = OPERATOR_LOG_ROOT.exists()" in request_source
    assert "if OPERATOR_LOG_ROOT.exists():\n    raise RuntimeError" not in request_source
    assert "resume-attempt-{uuid.uuid4().hex}" in request_source
    assert (
        "OPERATOR_LOG_ATTEMPT_ROOT.mkdir(parents=False, exist_ok=False)"
        in request_source
    )
    assert 'log_path = OPERATOR_LOG_ATTEMPT_ROOT /' in request_source
    assert 'log_path.open("x"' in request_source

    existing_log_gate = resume_source.index("if OPERATOR_LOG_ROOT_PREEXISTED:")
    exact_verifier = resume_source.index('run_cli(("phase40-verify-resume"')
    assert existing_log_gate < exact_verifier
    assert "automatic or latest resume is forbidden" in resume_source
    assert "exact resume requires the original append-only operator-log root" in resume_source
    assert "EXACT_RESUME_VERIFIED = False" in resume_source
    assert "EXACT_RESUME_CHECKPOINT = Path(EXACT_RESUME_CHECKPOINT)" in resume_source
    assert "EXACT_RESUME_CHECKPOINT.is_absolute()" in resume_source


@pytest.mark.parametrize(
    ("role", "old", "new", "expected_code"),
    (
        (
            "request-verify",
            "OPERATOR_LOG_ATTEMPT_ROOT.mkdir(parents=False, exist_ok=False)",
            "OPERATOR_LOG_ATTEMPT_ROOT.mkdir(parents=False, exist_ok=True)",
            "missing-request-verify-contract",
        ),
        (
            "request-verify",
            "log_path = OPERATOR_LOG_ATTEMPT_ROOT /",
            "log_path = OPERATOR_LOG_ROOT /",
            "missing-request-verify-contract",
        ),
        (
            "resume-policy",
            "automatic or latest resume is forbidden",
            "implicit resume is allowed",
            "missing-resume-policy-contract",
        ),
    ),
)
def test_lora_resume_log_safety_mutations_fail_closed(
    tmp_path: Path,
    role: str,
    old: str,
    new: str,
    expected_code: str,
) -> None:
    path = _mutate_role(tmp_path, role=role, old=old, new=new)
    assert expected_code in _codes(path)


def test_malformed_or_duplicate_key_json_fails_without_execution(tmp_path: Path) -> None:
    path = tmp_path / "qwen_lora_colab.ipynb"
    path.write_text('{"nbformat":4,"nbformat":4}', encoding="utf-8")
    assert _codes(path) == {"invalid-notebook-json"}
