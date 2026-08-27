"""Synthetic runtime-boundary tests for Phase 41.1 Plan 03."""

from __future__ import annotations

import ast
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import tomllib

import pytest

from src.core import integrity


REPO_ROOT = Path(__file__).parents[2]
RUNTIME_CLI_FIXTURE = REPO_ROOT / "tests/architecture/fixtures/runtime_cli_contract.json"
PROVIDER_DEFAULTS = {
    "anthropic_api_key": "",
    "gemini_api_key": "",
    "google_oauth_access_token": "",
    "openrouter_api_key": "",
    "deepseek_api_key": "",
    "openai_compatible_base_url": "",
    "openai_compatible_api_key": "",
    "openai_compatible_model": "",
    "google_application_credentials": "",
    "google_cloud_project": "",
    "gemini_use_adc": False,
}
DATA_DEFAULTS = {
    "data_dir": Path("data"),
    "split_ratios": (0.8, 0.1, 0.1),
    "similarity_threshold": 0.85,
    "scrape_delay_min": 2.0,
    "scrape_delay_max": 5.0,
    "ncsc_base_url": "https://canhbao.khonggianmang.vn",
}
MODELING_DEFAULTS = {
    "model_storage_root": Path("data"),
    "model_artifact_root": Path("data/models"),
    "model_registry_path": Path("data/manifests/model-registry.json"),
}
RUNTIME_DEFAULTS = {
    "runtime_backend": "gguf",
    "runtime_profile": "gguf-laptop",
    "runtime_profile_gguf": "gguf-laptop",
    "runtime_profile_gguf_runner_up": "gguf-runner-up",
    "runtime_profile_accelerated": "accelerated-local",
    "runtime_max_cues": 3,
    "runtime_min_text_chars": 8,
    "runtime_store_raw_text": False,
    "runtime_fail_closed": True,
    "runtime_allow_text_flag": True,
    "runtime_release_manifest_root": importlib.import_module(
        "src.config.settings"
    ).DEFAULT_RELEASE_MANIFEST_ROOT,
    "runtime_text_only_message": (
        "Paste extracted text manually. OCR, screenshots, and voice messages "
        "are not supported in this demo."
    ),
}
BLOCKED_IMPORT_PREFIXES = (
    "src.model_adaptation.training",
    "src.model_adaptation.phase40",
    "src.model_adaptation.phase41",
    "torch",
    "transformers",
    "sklearn",
    "accelerate",
    "peft",
    "openai",
    "google.generativeai",
)


def _write_manifest(root: Path, payload: object) -> Path:
    path = root / "manifests" / "download-manifest.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _write_strict_model_manifest(root: Path, candidate_id: str) -> Path:
    model_root = root / "base" / candidate_id
    model_root.mkdir(parents=True)
    (model_root / "config.json").write_text('{"model":"synthetic"}', encoding="utf-8")
    digest, file_count, total_bytes = integrity.artifact_digest(model_root)
    _write_manifest(
        root,
        {
            "schema_version": "model-download-manifest-v2",
            "models": [
                {
                    "candidate_id": candidate_id,
                    "local_path": model_root.relative_to(root).as_posix(),
                    "revision": "synthetic-revision",
                    "sha256": digest,
                    "file_count": file_count,
                    "total_bytes": total_bytes,
                }
            ],
        },
    )
    return model_root


def _run_isolated_lookup(root: Path, candidate_id: str) -> subprocess.CompletedProcess[str]:
    script = textwrap.dedent(
        f"""
        import importlib.abc
        import pathlib
        import sys

        blocked = {BLOCKED_IMPORT_PREFIXES!r}

        class Blocker(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if any(fullname == item or fullname.startswith(item + ".") for item in blocked):
                    raise ModuleNotFoundError("blocked optional import: " + fullname)
                return None

        sys.meta_path.insert(0, Blocker())
        module = __import__("src.runtime.analyzers.local_model", fromlist=["resolve_base_model_path"])
        resolved = module.resolve_base_model_path(sys.argv[2], pathlib.Path(sys.argv[1]))
        print(str(resolved).encode("unicode_escape").decode("ascii"))
        forbidden = sorted(
            name for name in sys.modules
            if any(name == item or name.startswith(item + ".") for item in blocked)
        )
        if forbidden:
            raise AssertionError("blocked modules loaded: " + repr(forbidden))
        """
    )
    return subprocess.run(
        [sys.executable, "-c", script, os.fspath(root), candidate_id],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_runtime_manifest_lookup_succeeds_with_optional_graph_blocked(tmp_path: Path) -> None:
    candidate_id = "qwen3-4b-instruct-2507"
    candidate = _write_strict_model_manifest(tmp_path, candidate_id)

    completed = _run_isolated_lookup(tmp_path, candidate_id)

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == os.fspath(candidate).encode(
        "unicode_escape"
    ).decode("ascii")


def test_runtime_missing_candidate_preserves_frozen_error_contract(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        {"schema_version": "model-download-manifest-v2", "models": []},
    )

    completed = _run_isolated_lookup(tmp_path, "missing-candidate")

    assert completed.returncode != 0
    assert "Missing base model manifest entry for candidate_id=missing-candidate" in completed.stderr


def test_runtime_rejects_unmanifested_base_model_fallback(tmp_path: Path) -> None:
    fallback = tmp_path / "base" / "qwen3.5-4b"
    fallback.mkdir(parents=True)
    (fallback / "config.json").write_text("{}", encoding="utf-8")

    completed = _run_isolated_lookup(tmp_path, "qwen3.5-4b")

    assert completed.returncode != 0
    assert "Missing base model manifest entry" in completed.stderr


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b"\xff", "strict UTF-8 JSON"),
        (b'{"models": [], "models": []}', "duplicate JSON key"),
        (b"[]", "must be a JSON object"),
    ],
)
def test_download_manifest_rejects_invalid_json(
    tmp_path: Path, raw: bytes, message: str
) -> None:
    artifacts = importlib.import_module("src.artifacts")
    path = tmp_path / "manifests" / "download-manifest.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)

    with pytest.raises(artifacts.ArtifactError, match=message):
        artifacts.load_download_manifest(tmp_path)


@pytest.mark.parametrize(
    "payload",
    [
        {"models": {}},
        {"schema_version": "model-download-manifest-v2", "models": ["not-an-object"]},
        {"schema_version": "model-download-manifest-v2", "models": [{}]},
        {
            "schema_version": "model-download-manifest-v2",
            "models": [{"candidate_id": "unknown", "local_path": "model"}],
        },
        {
            "schema_version": "model-download-manifest-v2",
            "models": [
                {
                    "candidate_id": "qwen3.5-4b",
                    "local_path": "first",
                    "revision": "one",
                    "sha256": "a" * 64,
                    "file_count": 1,
                    "total_bytes": 1,
                },
                {
                    "candidate_id": "qwen3.5-4b",
                    "local_path": "second",
                    "revision": "two",
                    "sha256": "b" * 64,
                    "file_count": 1,
                    "total_bytes": 1,
                },
            ]
        },
    ],
)
def test_download_manifest_rejects_malformed_candidates(
    tmp_path: Path, payload: object
) -> None:
    artifacts = importlib.import_module("src.artifacts")
    _write_manifest(tmp_path, payload)

    with pytest.raises(artifacts.ArtifactError):
        artifacts.load_download_manifest(tmp_path)


def test_absent_download_manifest_is_an_empty_mapping(tmp_path: Path) -> None:
    artifacts = importlib.import_module("src.artifacts")

    assert artifacts.load_download_manifest(tmp_path) == {}


@pytest.mark.parametrize("field,value", (("local_path", "../outside"), ("sha256", "A" * 64)))
def test_download_manifest_rejects_unbounded_paths_and_hashes(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    artifacts = importlib.import_module("src.artifacts")
    record = {
        "candidate_id": "qwen3.5-4b",
        "local_path": "base/qwen3.5-4b",
        "revision": "synthetic-revision",
        "sha256": "a" * 64,
        "file_count": 1,
        "total_bytes": 1,
    }
    record[field] = value
    _write_manifest(
        tmp_path,
        {"schema_version": "model-download-manifest-v2", "models": [record]},
    )

    with pytest.raises(artifacts.ArtifactError):
        artifacts.load_download_manifest(tmp_path)


def test_neutral_boundary_is_closed_and_within_static_budgets() -> None:
    for relative in ("src/core/integrity.py", "src/artifacts.py"):
        source = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert ".rglob(" not in source
        assert "os.walk(" not in source
        assert "src.model_adaptation" not in source
        tree = ast.parse(source)
        assert len(source.splitlines()) <= 600
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno is not None
                assert node.end_lineno - node.lineno + 1 <= 100, node.name

    local_source = (REPO_ROOT / "src/runtime/analyzers/local_model.py").read_text(
        encoding="utf-8"
    )
    assert "from src.artifacts import resolve_downloaded_model" in local_source
    assert "src.model_adaptation.training" not in local_source


def test_runtime_loaders_reverify_before_import_and_disable_remote_code() -> None:
    accelerated = (REPO_ROOT / "src/runtime/analyzers/accelerated.py").read_text(
        encoding="utf-8"
    )
    gguf = (REPO_ROOT / "src/runtime/analyzers/gguf.py").read_text(encoding="utf-8")

    accelerated_load = accelerated[accelerated.index("    def _load_runtime(") :]
    gguf_load = gguf[gguf.index("    def _load_runtime(") :]
    assert accelerated_load.index("verify_artifact_identity") < accelerated_load.index(
        'importlib.import_module("torch")'
    )
    assert gguf_load.index("verify_artifact_identity") < gguf_load.index(
        'importlib.import_module("llama_cpp")'
    )
    assert "trust_remote_code=True" not in accelerated
    assert "trust_remote_code=False" in accelerated
    assert '"trust_remote_code": False' in accelerated
    assert '"use_safetensors": True' in accelerated


def _clear_owner_caches(settings_module: object) -> None:
    for name in (
        "get_runtime_settings",
        "get_provider_settings",
        "get_data_settings",
        "get_modeling_settings",
    ):
        getter = getattr(settings_module, name)
        getter.cache_clear()


def test_settings_owners_preserve_defaults_and_legacy_composition(monkeypatch, tmp_path: Path) -> None:
    settings_module = importlib.import_module("src.config.settings")
    all_defaults = PROVIDER_DEFAULTS | DATA_DEFAULTS | MODELING_DEFAULTS | RUNTIME_DEFAULTS
    for field_name in all_defaults:
        monkeypatch.delenv(field_name.upper(), raising=False)
    monkeypatch.chdir(tmp_path)
    _clear_owner_caches(settings_module)

    assert settings_module.ENV_FILE_CANDIDATES == (".env/APIKEY.json", ".env/.env")
    assert set(settings_module.ProviderSettings.model_fields) == set(PROVIDER_DEFAULTS)
    assert set(settings_module.DataSettings.model_fields) == set(DATA_DEFAULTS)
    assert set(settings_module.ModelingSettings.model_fields) == set(MODELING_DEFAULTS)
    assert set(settings_module.RuntimeSettings.model_fields) == (
        set(RUNTIME_DEFAULTS) | set(MODELING_DEFAULTS)
    )

    legacy = settings_module.Settings(_env_file=None)
    assert legacy.model_dump() == all_defaults
    modeling = settings_module.ModelingSettings(_env_file=None)
    assert modeling.resolved_model_storage_root.is_absolute()
    assert modeling.resolved_model_artifact_root.is_relative_to(
        modeling.resolved_model_storage_root
    )
    assert modeling.resolved_model_registry_path.is_relative_to(
        modeling.resolved_model_storage_root
    )
    assert settings_module.get_settings() is not settings_module.get_settings()
    for getter_name in (
        "get_runtime_settings",
        "get_provider_settings",
        "get_data_settings",
        "get_modeling_settings",
    ):
        getter = getattr(settings_module, getter_name)
        assert getter() is getter()

    _clear_owner_caches(settings_module)


def test_runtime_settings_keep_precedence_without_loading_or_emitting_secrets(
    monkeypatch, tmp_path: Path
) -> None:
    settings_module = importlib.import_module("src.config.settings")
    env_dir = tmp_path / ".env"
    env_dir.mkdir()
    (env_dir / "APIKEY.json").write_text(
        "ANTHROPIC_API_KEY=synthetic-file-secret-a\n"
        "GEMINI_API_KEY=synthetic-file-secret-b\n"
        "RUNTIME_BACKEND=heuristic\n",
        encoding="utf-8",
    )
    (env_dir / ".env").write_text(
        "ANTHROPIC_API_KEY=synthetic-later-file-secret\n"
        "RUNTIME_PROFILE=heuristic\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-os-secret")
    monkeypatch.setenv("RUNTIME_MAX_CUES", "7")
    _clear_owner_caches(settings_module)

    runtime = settings_module.get_runtime_settings()
    legacy = settings_module.Settings()
    rendered_runtime = repr(runtime) + runtime.model_dump_json()

    assert runtime.runtime_backend == "heuristic"
    assert runtime.runtime_profile == "heuristic"
    assert runtime.runtime_max_cues == 7
    assert legacy.anthropic_api_key == "synthetic-os-secret"
    assert not set(PROVIDER_DEFAULTS).intersection(type(runtime).model_fields)
    for secret in (
        "synthetic-file-secret-a",
        "synthetic-file-secret-b",
        "synthetic-later-file-secret",
        "synthetic-os-secret",
    ):
        assert secret not in rendered_runtime

    _clear_owner_caches(settings_module)
    monkeypatch.setenv("RUNTIME_MAX_CUES", "not-an-integer")
    with pytest.raises(Exception) as error:
        settings_module.get_runtime_settings()
    assert "synthetic-os-secret" not in str(error.value)
    _clear_owner_caches(settings_module)


def test_modeling_settings_infer_one_bounded_root_for_explicit_runtime_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings_module = importlib.import_module("src.config.settings")
    monkeypatch.delenv("MODEL_STORAGE_ROOT", raising=False)
    monkeypatch.setenv("MODEL_ARTIFACT_ROOT", os.fspath(tmp_path / "models"))
    monkeypatch.setenv(
        "MODEL_REGISTRY_PATH",
        os.fspath(tmp_path / "manifests" / "model-registry.json"),
    )

    settings = settings_module.ModelingSettings(_env_file=None)

    assert settings.resolved_model_storage_root == tmp_path


def test_runtime_construction_uses_secret_free_owner_getter() -> None:
    for relative in (
        "src/runtime/service.py",
        "src/runtime/doctor.py",
        "src/runtime/analyzers/gguf.py",
        "src/runtime/analyzers/accelerated.py",
    ):
        source = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "get_runtime_settings as get_settings" in source
        assert not any(field_name in source for field_name in PROVIDER_DEFAULTS)
        assert "resolved_model_registry_path" in source


def test_runtime_minimum_python_matches_package_metadata() -> None:
    settings_module = importlib.import_module("src.config.settings")
    metadata = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = metadata["project"]["requires-python"]
    expected = ">=" + ".".join(map(str, settings_module.MINIMUM_PYTHON_VERSION))
    assert declared == expected
    doctor_module = importlib.import_module("src.runtime.doctor")
    check = doctor_module.RuntimeDoctor()._check_python_version()
    assert check.passed is (sys.version_info >= settings_module.MINIMUM_PYTHON_VERSION)


def test_runtime_doctor_fails_closed_on_unsafe_release_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doctor_module = importlib.import_module("src.runtime.doctor")
    artifact = tmp_path / "release-evaluation-synthetic.json"
    artifact.write_text("{}", encoding="utf-8")
    original = doctor_module.reject_redirecting_ancestry

    def reject_member(path: Path, *, where: str) -> Path:
        if where == "release manifest member":
            raise integrity.IntegrityError("synthetic member race")
        return original(path, where=where)

    monkeypatch.setattr(doctor_module, "reject_redirecting_ancestry", reject_member)
    check = doctor_module.RuntimeDoctor()._check_latest_release_gate_summary(tmp_path)

    assert check.passed is False
    assert "unsafe or unstable" in check.detail


@pytest.mark.parametrize(
    "text",
    (
        "Không lo, bấm vào liên kết để xác minh.",
        "Khong lo, click vao link de xac minh.",
        "Xác minh qua tổng đài; trả lời tin nhắn này để nhận mã.",
        "Tranh hoang mang, chuyen tien ngay de bao toan tai khoan.",
        "Không lo bấm vào liên kết mà chuyển tiền để xác minh",
        "Khong bam vao lien ket ma chuyen tien de xac minh",
        "Không bấm vào liên kết mà chuyển tiền để xác minh",
        "Khong click link roi transfer money de xac minh",
        "Không bấm vào liên kết và nhớ chia sẻ OTP cho họ",
        "Không bấm vào liên kết hoặc hãy chuyển tiền để xác minh",
        "Không bấm vào liên kết và sau đó cài ứng dụng này",
    ),
)
def test_recommendation_filter_rejects_mixed_clause_actions(text: str) -> None:
    module = importlib.import_module("src.runtime.analyzers.local_model")
    assert module.is_recommendation_safe(text) is False


@pytest.mark.parametrize(
    "text",
    (
        "Không bấm vào liên kết và không cài ứng dụng từ tin nhắn.",
        "Khong chia se OTP va khong cung cap CVV.",
        "Không bấm vào liên kết hoặc đừng cài ứng dụng từ tin nhắn.",
        "Xác minh qua ứng dụng chính thức.",
    ),
)
def test_recommendation_filter_accepts_bounded_safe_guidance(text: str) -> None:
    module = importlib.import_module("src.runtime.analyzers.local_model")
    assert module.is_recommendation_safe(text) is True


def _release_payload(verdict: str) -> dict[str, object]:
    labels = (
        "bank_impersonation",
        "zalo_social_engineering",
        "task_scam",
        "benign",
    )
    payload: dict[str, object] = {
        "run_id": f"synthetic-{verdict.lower()}",
        "verdict": verdict,
        "overall_metrics": {
            "macro_f1": 0.95,
            "weighted_f1": 0.95,
            "evaluated_rows": 4,
        },
        "per_label_metrics": [
            {"label": label, "precision": 0.95, "recall": 0.95, "f1": 0.95, "support": 1}
            for label in labels
        ],
        "explanation_rubric_summary": {
            "evaluated_risky_predictions": 3,
            "manual_reviewed_predictions": 3,
        },
        "readiness_audit": {
            "evaluated_split_path": os.fspath(
                REPO_ROOT / ".tmp" / "synthetic-heldout.jsonl"
            ),
            "support_by_label": {label: 1 for label in labels},
        },
    }
    if verdict == "BLOCK":
        payload["blocker_reasons"] = ["synthetic blocker"]
    elif verdict == "FLAG":
        payload["flag_reasons"] = ["synthetic flag"]
    return payload


@pytest.mark.parametrize(
    ("verdict", "expected"),
    (("PASS", True), ("BLOCK", False), ("FLAG", False)),
)
def test_runtime_doctor_uses_neutral_release_reader(
    monkeypatch, tmp_path: Path, verdict: str, expected: bool
) -> None:
    doctor_module = importlib.import_module("src.runtime.doctor")
    artifact_path = tmp_path / f"release-evaluation-{verdict.lower()}.json"
    artifact_path.write_text(
        json.dumps(_release_payload(verdict)),
        encoding="utf-8",
    )
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    check = doctor_module.RuntimeDoctor()._check_latest_release_gate_summary(tmp_path)
    source = (REPO_ROOT / "src/runtime/doctor.py").read_text(encoding="utf-8")

    assert check.passed is expected
    assert f"latest_verdict={verdict}" in check.detail
    assert "from src.artifacts import" in source
    assert "load_release_evaluation_artifact" in source
    assert "src.model_adaptation" not in source


def test_runtime_doctor_blocks_missing_release_root(tmp_path: Path) -> None:
    doctor_module = importlib.import_module("src.runtime.doctor")
    check = doctor_module.RuntimeDoctor()._check_latest_release_gate_summary(
        tmp_path / "missing"
    )
    assert check.passed is False
    assert "root is missing" in check.detail


def test_runtime_cli_contract_fixture_remains_byte_exact(tmp_path: Path) -> None:
    from tests.architecture.test_contract_baselines import _run_fresh_capture

    captured = _run_fresh_capture("runtime", tmp_path / "runtime-contract")

    assert captured == RUNTIME_CLI_FIXTURE.read_bytes()
