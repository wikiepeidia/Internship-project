from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.model_adaptation import phase40_release_authorities as release
from src.model_adaptation import phase40_runtime_materialize as materialize


class FakeDistribution:
    def __init__(
        self,
        *,
        name: str,
        version: str,
        base: Path,
        files: tuple[Path, ...],
        requires: tuple[str, ...] = (),
        locate_overrides: dict[str, Path] | None = None,
    ) -> None:
        self.metadata = {"Name": name}
        self.version = version
        self.base = base
        self.files = files
        self.requires = requires
        self.locate_overrides = locate_overrides or {}

    def locate_file(self, path):  # noqa: ANN001, ANN201 - importlib.metadata seam
        text = Path(path).as_posix()
        return self.locate_overrides.get(text, self.base / Path(path))


def _write(root: Path, relative: str, payload: bytes) -> Path:
    path = root / Path(relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


class Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 8, 26, 1, 2, 3, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        observed = self.value
        self.value += timedelta(minutes=1, seconds=1)
        return observed


def _passing_smoke(stage, expected, python):  # noqa: ANN001, ANN201
    del stage
    return {
        "schema_version": materialize.SMOKE_SCHEMA_VERSION,
        "status": "passed",
        "python": python.version,
        "packages": dict(sorted(expected.items())),
        "checks": {key: True for key in sorted(materialize._SMOKE_CHECK_KEYS)},
        "host_prerequisites": {
            "binding": "observed-not-byte-bound",
            "os_name": "nt",
            "sys_platform": "win32",
            "machine": "AMD64",
            "cuda_runtime": "13.2",
            "cuda_device_count": 1,
            "cuda_device_name_sha256": ["a" * 64],
            "cuda_capabilities": ["12.0"],
        },
    }


def _fixture(tmp_path: Path):
    repository = tmp_path / "repo"
    output_parent = repository / "data/models/phase40"
    output_parent.mkdir(parents=True)
    staging = tmp_path / "external-staging"
    staging.mkdir()
    prefix = tmp_path / "python313"
    site_packages = prefix / "Lib/site-packages"
    site_packages.mkdir(parents=True)
    executable = _write(prefix, "python.exe", b"MZ-synthetic-python-3.13.13")
    _write(prefix, "python313.dll", b"synthetic-python-dll")
    _write(prefix, "Lib/os.py", b"def f(): return 'stdlib'\n")

    modules = {
        "accelerate": "accelerate",
        "bitsandbytes": "bitsandbytes",
        "gguf": "gguf",
        "huggingface-hub": "huggingface_hub",
        "llama-cpp-python": "llama_cpp",
        "matplotlib": "matplotlib",
        "peft": "peft",
        "scikit-learn": "sklearn",
        "torch": "torch",
        "transformers": "transformers",
        "underthesea": "underthesea",
        "runtime-helper": "runtime_helper",
    }
    versions = {
        **dict(materialize.FIXED_DIRECT_DISTRIBUTIONS),
        "runtime-helper": "1.2.0",
    }
    distributions: dict[str, FakeDistribution] = {}
    origins: dict[str, Path] = {}
    package_map: dict[str, list[str]] = {}
    for name, module in modules.items():
        version = versions[name]
        origin_relative = Path(module) / "__init__.py"
        metadata_relative = Path(f"{name}-{version}.dist-info") / "METADATA"
        origin = _write(
            site_packages,
            origin_relative.as_posix(),
            f"NAME={name!r}\n".encode(),
        )
        _write(
            site_packages,
            metadata_relative.as_posix(),
            f"Name: {name}\nVersion: {version}\n".encode(),
        )
        files = [origin_relative, metadata_relative]
        requires: tuple[str, ...] = ()
        if name == "underthesea":
            requires = (
                "runtime-helper>=1; sys_platform == 'win32'",
                "never-installed; sys_platform == 'not-win32'",
            )
        if name == "gguf":
            script = _write(prefix, "Scripts/gguf-dump.exe", b"synthetic-script")
            assert script.is_file()
            files.append(Path("../../Scripts/gguf-dump.exe"))
        distributions[name] = FakeDistribution(
            name=name,
            version=version,
            base=site_packages,
            files=tuple(files),
            requires=requires,
        )
        origins[module] = origin
        package_map[module] = [name]

    def distribution(name: str) -> FakeDistribution:
        normalized = release.normalize_distribution_name(name)
        if normalized not in distributions:
            raise LookupError(normalized)
        return distributions[normalized]

    metadata = materialize.MetadataHooks(
        distribution=distribution,
        packages_distributions=lambda: package_map,
        find_spec=lambda module: (
            SimpleNamespace(origin=str(origins[module])) if module in origins else None
        ),
        marker_environment=lambda: {
            "implementation_name": "cpython",
            "implementation_version": "3.13.13",
            "os_name": "nt",
            "platform_machine": "AMD64",
            "platform_python_implementation": "CPython",
            "platform_release": "synthetic",
            "platform_system": "Windows",
            "platform_version": "synthetic",
            "python_full_version": "3.13.13",
            "python_version": "3.13",
            "sys_platform": "win32",
            "extra": "",
        },
    )
    python = materialize.PythonSource(
        implementation="cpython",
        version="3.13.13",
        cache_tag="cpython-313",
        abi_flags="",
        platform="win32",
        prefix=prefix,
        site_packages=site_packages,
        executable=executable,
    )
    services = materialize._MaterializationServices(
        metadata=metadata,
        discover_python=lambda: python,
        path_is_redirecting=materialize._default_path_is_redirecting,
        smoke_runner=_passing_smoke,
        now=Clock(),
        capture_authority=release.capture_runtime_dependency_authority,
        verify_authority=release.verify_runtime_dependency_authority,
        publication_hook=lambda _: None,
    )
    return SimpleNamespace(
        repository=repository,
        staging=staging,
        prefix=prefix,
        site_packages=site_packages,
        executable=executable,
        distributions=distributions,
        origins=origins,
        package_map=package_map,
        metadata=metadata,
        python=python,
        services=services,
    )


def _rewrite_receipt_and_completion(result, payload):  # noqa: ANN001, ANN201
    core = {key: value for key, value in payload.items() if key != "receipt_sha256"}
    payload["receipt_sha256"] = materialize._sha256_bytes(
        materialize._canonical_json_bytes(core)
    )
    result.receipt_path.write_bytes(materialize._canonical_json_bytes(payload))
    completion = materialize._build_completion_marker(
        authority=result.authority,
        receipt=payload,
    )
    result.completion_path.write_bytes(materialize._canonical_json_bytes(completion))


def test_materializes_two_pass_closed_trees_and_portable_fixed_receipt(tmp_path):
    fixture = _fixture(tmp_path)

    result = materialize._materialize_runtime_dependency_authority(
        repo_root=fixture.repository.absolute(),
        staging_parent=fixture.staging.absolute(),
        services=fixture.services,
    )

    assert result.authority_path == (
        fixture.repository / materialize.RUNTIME_AUTHORITY_RELATIVE_PATH
    )
    assert result.receipt_path == (
        fixture.repository / materialize.MATERIALIZATION_RECEIPT_RELATIVE_PATH
    )
    assert result.completion_path == (
        fixture.repository / materialize.MATERIALIZATION_COMPLETE_RELATIVE_PATH
    )
    assert result.completion_path.is_file()
    assert tuple(item.name for item in result.authority.distributions) == tuple(
        sorted((*materialize.FIXED_DIRECT_DISTRIBUTIONS, "runtime-helper"))
    )
    assert materialize.load_runtime_materialization_receipt(
        repo_root=fixture.repository.absolute()
    ) == dict(result.receipt)
    receipt_bytes = result.receipt_path.read_bytes()
    assert str(fixture.staging).encode() not in receipt_bytes
    assert str(fixture.prefix).encode() not in receipt_bytes
    assert b'"path_disclosure":"sha256-only"' in receipt_bytes
    assert result.receipt["capture_started_at_utc"] == "2026-08-26T01:02:03Z"
    assert result.receipt["capture_completed_at_utc"] == "2026-08-26T01:03:04Z"
    authority_files = len(result.authority.python.files) + sum(
        len(item.files) for item in result.authority.distributions
    )
    authority_bytes = sum(item.bytes for item in result.authority.python.files) + sum(
        file.bytes
        for item in result.authority.distributions
        for file in item.files
    )
    assert result.receipt["closure_inventory"] == {
        "files": authority_files,
        "bytes": authority_bytes,
    }
    assert result.receipt["scope"]["claim"] == (
        "closed-python-package-prefix-byte-closure"
    )
    assert result.receipt["scope"]["network_isolation"] is False
    assert result.receipt["scope"]["process_sandbox"] is False
    assert result.receipt["staging"]["two_pass_byte_stable"] is True
    assert result.receipt["staging"]["independent_source_provenance"] is False
    for record in result.receipt["staging"]["captures"]:
        assert record["smoke"] == _passing_smoke(
            None,
            {item.name: item.version for item in result.authority.distributions},
            fixture.python,
        )
        assert record["files"] == authority_files
        assert record["bytes"] == authority_bytes

    for capture in materialize.CAPTURE_ROOT_NAMES:
        root = fixture.staging / capture
        assert (root / "python-runtime/python.exe").is_file()
        assert not (root / "python-runtime/Scripts/gguf-dump.exe").exists()
        assert (
            root
            / "distributions/gguf/python-prefix/Scripts/gguf-dump.exe"
        ).is_file()
        assert (
            root / "distributions/llama-cpp-python/site-packages/llama_cpp/__init__.py"
        ).is_file()


def test_capture_b_is_rebuilt_from_live_source_and_detects_between_copy_drift(tmp_path):
    fixture = _fixture(tmp_path)
    target = fixture.origins["runtime_helper"]

    def mutate_live_after_a(stage, expected, python):  # noqa: ANN001, ANN201
        result = _passing_smoke(stage, expected, python)
        if stage.capture_id == "capture-a":
            target.write_bytes(b"NAME='runtime-helper-mutated'\n")
        return result

    services = replace(fixture.services, smoke_runner=mutate_live_after_a)
    with pytest.raises(
        materialize.RuntimeMaterializationError,
        match="A/B runtime authorities",
    ):
        materialize._materialize_runtime_dependency_authority(
            repo_root=fixture.repository.absolute(),
            staging_parent=fixture.staging.absolute(),
            services=services,
        )
    assert not (
        fixture.repository / materialize.RUNTIME_AUTHORITY_RELATIVE_PATH
    ).exists()
    assert not (
        fixture.repository / materialize.MATERIALIZATION_RECEIPT_RELATIVE_PATH
    ).exists()


def test_capture_b_rediscovers_live_metadata_membership(tmp_path):
    fixture = _fixture(tmp_path)
    added = _write(
        fixture.site_packages,
        "runtime_helper/new_runtime_member.py",
        b"MEMBERSHIP='added-after-a'\n",
    )
    assert added.is_file()

    def add_record_member_after_a(stage, expected, python):  # noqa: ANN001, ANN201
        result = _passing_smoke(stage, expected, python)
        if stage.capture_id == "capture-a":
            helper = fixture.distributions["runtime-helper"]
            helper.files = (*helper.files, Path("runtime_helper/new_runtime_member.py"))
        return result

    with pytest.raises(
        materialize.RuntimeMaterializationError,
        match="A/B runtime authorities",
    ):
        materialize._materialize_runtime_dependency_authority(
            repo_root=fixture.repository.absolute(),
            staging_parent=fixture.staging.absolute(),
            services=replace(
                fixture.services,
                smoke_runner=add_record_member_after_a,
            ),
        )


def test_smoke_must_not_add_or_mutate_any_staged_file(tmp_path):
    fixture = _fixture(tmp_path)

    def writing_smoke(stage, expected, python):  # noqa: ANN001, ANN201
        (stage.root / "smoke-side-effect.txt").write_text("forbidden", encoding="utf-8")
        return _passing_smoke(stage, expected, python)

    with pytest.raises(
        materialize.RuntimeMaterializationError,
        match="staged tree",
    ):
        materialize._materialize_runtime_dependency_authority(
            repo_root=fixture.repository.absolute(),
            staging_parent=fixture.staging.absolute(),
            services=replace(fixture.services, smoke_runner=writing_smoke),
        )


def test_capture_b_smoke_cannot_reach_across_and_mutate_capture_a(tmp_path):
    fixture = _fixture(tmp_path)

    def cross_capture_smoke(stage, expected, python):  # noqa: ANN001, ANN201
        result = _passing_smoke(stage, expected, python)
        if stage.capture_id == "capture-b":
            (stage.root.parent / "capture-a/cross-capture.txt").write_text(
                "forbidden",
                encoding="utf-8",
            )
        return result

    with pytest.raises(
        materialize.RuntimeMaterializationError,
        match="staged tree",
    ):
        materialize._materialize_runtime_dependency_authority(
            repo_root=fixture.repository.absolute(),
            staging_parent=fixture.staging.absolute(),
            services=replace(fixture.services, smoke_runner=cross_capture_smoke),
        )


@pytest.mark.parametrize("placement", ("inside-repository", "inside-python"))
def test_external_staging_parent_must_be_disjoint(tmp_path, placement):
    fixture = _fixture(tmp_path)
    if placement == "inside-repository":
        staging = fixture.repository / "staging"
    else:
        staging = fixture.prefix / "staging"
    staging.mkdir()

    with pytest.raises(
        materialize.RuntimeMaterializationError,
        match="roots must be disjoint",
    ):
        materialize._materialize_runtime_dependency_authority(
            repo_root=fixture.repository.absolute(),
            staging_parent=staging.absolute(),
            services=fixture.services,
        )


def test_existing_fixed_staging_child_is_never_reused_or_deleted(tmp_path):
    fixture = _fixture(tmp_path)
    existing = fixture.staging / materialize.CAPTURE_ROOT_NAMES[0]
    existing.mkdir()
    marker = _write(existing, "operator-file.txt", b"preserve")

    with pytest.raises(FileExistsError, match="pre-authority capture"):
        materialize._materialize_runtime_dependency_authority(
            repo_root=fixture.repository.absolute(),
            staging_parent=fixture.staging.absolute(),
            services=fixture.services,
        )
    assert marker.read_bytes() == b"preserve"


def test_distribution_file_cannot_escape_live_python_prefix(tmp_path):
    fixture = _fixture(tmp_path)
    outside = _write(tmp_path, "outside.py", b"outside")
    torch = fixture.distributions["torch"]
    torch.files = (*torch.files, Path("escape.py"))
    torch.locate_overrides["escape.py"] = outside

    with pytest.raises(
        materialize.RuntimeMaterializationError,
        match="escapes the Python prefix",
    ):
        materialize._materialize_runtime_dependency_authority(
            repo_root=fixture.repository.absolute(),
            staging_parent=fixture.staging.absolute(),
            services=fixture.services,
        )


def test_cross_distribution_source_ownership_collision_is_rejected(tmp_path):
    fixture = _fixture(tmp_path)
    shared = fixture.origins["torch"]
    peft = fixture.distributions["peft"]
    peft.files = (*peft.files, Path("shared.py"))
    peft.locate_overrides["shared.py"] = shared

    with pytest.raises(
        materialize.RuntimeMaterializationError,
        match="ownership collides",
    ):
        materialize._materialize_runtime_dependency_authority(
            repo_root=fixture.repository.absolute(),
            staging_parent=fixture.staging.absolute(),
            services=fixture.services,
        )


def test_redirecting_or_missing_distribution_file_fails_before_staging(tmp_path):
    fixture = _fixture(tmp_path)
    blocked = fixture.origins["torch"]
    services = replace(
        fixture.services,
        path_is_redirecting=lambda path: (
            Path(path) == blocked
            or materialize._default_path_is_redirecting(Path(path))
        ),
    )
    with pytest.raises(
        materialize.RuntimeMaterializationError,
        match="symlink/reparse",
    ):
        materialize._materialize_runtime_dependency_authority(
            repo_root=fixture.repository.absolute(),
            staging_parent=fixture.staging.absolute(),
            services=services,
        )

    fixture = _fixture(tmp_path / "missing-case")
    torch = fixture.distributions["torch"]
    torch.files = (*torch.files, Path("missing.pyd"))
    with pytest.raises(materialize.RuntimeMaterializationError, match="missing"):
        materialize._materialize_runtime_dependency_authority(
            repo_root=fixture.repository.absolute(),
            staging_parent=fixture.staging.absolute(),
            services=fixture.services,
        )


def test_redirecting_fixed_output_parent_is_rejected(tmp_path):
    fixture = _fixture(tmp_path)
    output_parent = fixture.repository / "data/models/phase40"
    services = replace(
        fixture.services,
        path_is_redirecting=lambda path: (
            Path(path) == output_parent
            or materialize._default_path_is_redirecting(Path(path))
        ),
    )
    with pytest.raises(
        materialize.RuntimeMaterializationError,
        match="ancestry is symlink/reparse",
    ):
        materialize._materialize_runtime_dependency_authority(
            repo_root=fixture.repository.absolute(),
            staging_parent=fixture.staging.absolute(),
            services=services,
        )


def test_import_origin_must_be_uniquely_owned_and_override_is_explicit(tmp_path):
    fixture = _fixture(tmp_path)
    assert materialize.IMPORT_ORIGIN_OVERRIDES["llama-cpp-python"] == "llama_cpp"
    alien = _write(fixture.site_packages, "alien/__init__.py", b"alien")
    bad_metadata = replace(
        fixture.metadata,
        find_spec=lambda module: (
            SimpleNamespace(origin=str(alien))
            if module == "llama_cpp"
            else fixture.metadata.find_spec(module)
        ),
    )
    with pytest.raises(
        materialize.RuntimeMaterializationError,
        match="not uniquely owned",
    ):
        materialize._materialize_runtime_dependency_authority(
            repo_root=fixture.repository.absolute(),
            staging_parent=fixture.staging.absolute(),
            services=replace(fixture.services, metadata=bad_metadata),
        )


def test_fixed_direct_version_and_transitive_specifier_are_fail_closed(tmp_path):
    fixture = _fixture(tmp_path)
    fixture.distributions["torch"].version = "2.12.1"
    with pytest.raises(
        materialize.RuntimeMaterializationError,
        match="fixed direct distribution version drifted",
    ):
        materialize.resolve_dependency_closure(metadata=fixture.metadata)

    fixture = _fixture(tmp_path / "specifier")
    fixture.distributions["runtime-helper"].version = "0.5.0"
    with pytest.raises(
        materialize.RuntimeMaterializationError,
        match="does not satisfy",
    ):
        materialize.resolve_dependency_closure(metadata=fixture.metadata)


def test_untrusted_partial_authority_without_capture_trees_is_refused(tmp_path):
    fixture = _fixture(tmp_path)
    output = fixture.repository / materialize.RUNTIME_AUTHORITY_RELATIVE_PATH
    output.write_bytes(b"operator-owned")

    with pytest.raises(
        materialize.RuntimeMaterializationError,
        match="cannot recover without both fixed capture trees",
    ):
        materialize._materialize_runtime_dependency_authority(
            repo_root=fixture.repository.absolute(),
            staging_parent=fixture.staging.absolute(),
            services=fixture.services,
        )
    assert output.read_bytes() == b"operator-owned"
    assert not (fixture.staging / "capture-a").exists()


def test_receipt_loader_rejects_self_hashed_absolute_path_leakage(tmp_path):
    fixture = _fixture(tmp_path)
    result = materialize._materialize_runtime_dependency_authority(
        repo_root=fixture.repository.absolute(),
        staging_parent=fixture.staging.absolute(),
        services=fixture.services,
    )
    payload = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    payload["staging"]["captures"][0]["root_name"] = r"C:\Users\private\capture-a"
    core = {key: value for key, value in payload.items() if key != "receipt_sha256"}
    payload["receipt_sha256"] = materialize._sha256_bytes(
        materialize._canonical_json_bytes(core)
    )
    result.receipt_path.write_bytes(materialize._canonical_json_bytes(payload))

    with pytest.raises(materialize.RuntimeMaterializationError, match="absolute path"):
        materialize.load_runtime_materialization_receipt(
            repo_root=fixture.repository.absolute()
        )


def test_cli_surface_accepts_only_repo_and_external_staging_paths():
    parser = materialize.build_parser()
    args = parser.parse_args(
        ["--repo-root", r"C:\repo", "--staging-parent", r"D:\runtime-stage"]
    )
    assert args.repo_root == Path(r"C:\repo")
    assert args.staging_parent == Path(r"D:\runtime-stage")
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--repo-root",
                r"C:\repo",
                "--staging-parent",
                r"D:\runtime-stage",
                "--output",
                r"D:\redirect.json",
            ]
        )


def test_embedded_staged_smoke_program_compiles():
    compile(
        materialize._STAGED_SMOKE_PROGRAM,
        "<phase40-runtime-staged-smoke>",
        "exec",
    )


def test_evidence_pinned_direct_roots_and_smoke_operations_are_exact():
    assert dict(materialize.FIXED_DIRECT_DISTRIBUTIONS) == {
        "accelerate": "1.13.0",
        "bitsandbytes": "0.50.1",
        "gguf": "0.19.0",
        "huggingface-hub": "1.16.1",
        "llama-cpp-python": "0.3.23",
        "matplotlib": "3.11.1",
        "peft": "0.19.1",
        "scikit-learn": "1.8.0",
        "torch": "2.12.0+cu132",
        "transformers": "5.9.0",
        "underthesea": "9.5.0",
    }
    assert materialize._DIRECT_IMPORT_MODULES["scikit-learn"] == "sklearn"
    assert materialize._DIRECT_IMPORT_MODULES["matplotlib"] == "matplotlib"
    assert "sklearn.metrics" in materialize._STAGED_SMOKE_PROGRAM
    assert "accuracy_score" in materialize._STAGED_SMOKE_PROGRAM
    assert "confusion_matrix" in materialize._STAGED_SMOKE_PROGRAM
    assert 'matplotlib.use("Agg", force=True)' in materialize._STAGED_SMOKE_PROGRAM
    assert "FigureCanvasAgg" in materialize._STAGED_SMOKE_PROGRAM
    assert {"sklearn_metrics", "matplotlib_agg_render"} <= (
        materialize._SMOKE_CHECK_KEYS
    )


def test_public_producer_and_verifier_have_no_injection_surface():
    assert tuple(inspect.signature(
        materialize.materialize_runtime_dependency_authority
    ).parameters) == ("repo_root", "staging_parent")
    assert tuple(inspect.signature(
        materialize.verify_runtime_dependency_materialization
    ).parameters) == ("repo_root", "staging_parent")
    assert "_MaterializationServices" not in materialize.__all__


@pytest.mark.parametrize("drift", ("python", "missing-check", "extra-check"))
def test_smoke_schema_requires_exact_python_and_check_keys(drift):
    expected = dict(materialize.FIXED_DIRECT_DISTRIBUTIONS)
    smoke = _passing_smoke(None, expected, SimpleNamespace(version="3.13.13"))
    if drift == "python":
        smoke["python"] = "3.12.0"
    elif drift == "missing-check":
        smoke["checks"].pop("sklearn_metrics")
    else:
        smoke["checks"]["unapproved"] = True
    with pytest.raises(materialize.RuntimeMaterializationError, match="smoke"):
        materialize._validate_smoke_result(
            smoke,
            expected_versions=expected,
            expected_python_version="3.13.13",
        )


def test_strict_smoke_environment_drops_unallowlisted_host_values(tmp_path):
    environment = materialize._build_smoke_environment(
        executable=tmp_path / "python.exe",
        temporary=tmp_path / "temporary",
        source_environment={
            "SYSTEMROOT": r"C:\Windows",
            "COMSPEC": r"C:\Windows\System32\cmd.exe",
            "CUDA_VISIBLE_DEVICES": "0",
            "AWS_SECRET_ACCESS_KEY": "forbidden",
            "PYTHONPATH": r"C:\live-site-packages",
            "CONDA_PREFIX": r"C:\conda",
        },
    )
    assert environment["SYSTEMROOT"] == r"C:\Windows"
    assert environment["COMSPEC"] == r"C:\Windows\System32\cmd.exe"
    assert environment["CUDA_VISIBLE_DEVICES"] == "0"
    assert "AWS_SECRET_ACCESS_KEY" not in environment
    assert "PYTHONPATH" not in environment
    assert "CONDA_PREFIX" not in environment
    assert environment["HF_HUB_OFFLINE"] == "1"
    assert environment["MPLCONFIGDIR"].endswith("temporary\\mpl")


@pytest.mark.parametrize("semantic_target", ("closure", "python", "inventory", "smoke"))
def test_receipt_semantics_are_derived_from_bound_authority(tmp_path, semantic_target):
    fixture = _fixture(tmp_path)
    result = materialize._materialize_runtime_dependency_authority(
        repo_root=fixture.repository.absolute(),
        staging_parent=fixture.staging.absolute(),
        services=fixture.services,
    )
    payload = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    if semantic_target == "closure":
        payload["dependency_resolution"]["distributions"][0]["version"] = "99.0"
    elif semantic_target == "python":
        payload["python"]["version"] = "3.12.0"
    elif semantic_target == "inventory":
        payload["closure_inventory"]["files"] += 1
    else:
        smoke = payload["staging"]["captures"][0]["smoke"]
        smoke["checks"]["sklearn_metrics"] = False
        payload["staging"]["captures"][0]["smoke_record_sha256"] = (
            materialize._sha256_bytes(materialize._canonical_json_bytes(smoke))
        )
    _rewrite_receipt_and_completion(result, payload)

    with pytest.raises(materialize.RuntimeMaterializationError):
        materialize.load_runtime_materialization_receipt(
            repo_root=fixture.repository.absolute()
        )


def test_completion_marker_is_required_and_is_published_last(tmp_path):
    fixture = _fixture(tmp_path)
    observed: list[tuple[str, bool, bool, bool]] = []

    def hook(step: str) -> None:
        observed.append(
            (
                step,
                (fixture.repository / materialize.RUNTIME_AUTHORITY_RELATIVE_PATH).is_file(),
                (fixture.repository / materialize.MATERIALIZATION_RECEIPT_RELATIVE_PATH).is_file(),
                (fixture.repository / materialize.MATERIALIZATION_COMPLETE_RELATIVE_PATH).is_file(),
            )
        )

    result = materialize._materialize_runtime_dependency_authority(
        repo_root=fixture.repository.absolute(),
        staging_parent=fixture.staging.absolute(),
        services=replace(fixture.services, publication_hook=hook),
    )
    assert observed == [
        ("authority-published", True, False, False),
        ("receipt-published", True, True, False),
        ("completion-published", True, True, True),
    ]
    result.completion_path.unlink()
    with pytest.raises(
        materialize.RuntimeMaterializationError,
        match="completion marker",
    ):
        materialize.load_runtime_materialization_receipt(
            repo_root=fixture.repository.absolute()
        )


def test_authority_only_publication_cannot_mint_recovery_receipt(tmp_path):
    fixture = _fixture(tmp_path)

    def fail_after_authority(step: str) -> None:
        if step == "authority-published":
            raise RuntimeError("synthetic-publication-failure")

    services = replace(fixture.services, publication_hook=fail_after_authority)
    with pytest.raises(RuntimeError, match="synthetic-publication-failure"):
        materialize._materialize_runtime_dependency_authority(
            repo_root=fixture.repository.absolute(),
            staging_parent=fixture.staging.absolute(),
            services=services,
        )
    assert not (
        fixture.repository / materialize.MATERIALIZATION_COMPLETE_RELATIVE_PATH
    ).exists()
    assert not (
        fixture.repository / materialize.MATERIALIZATION_RECEIPT_RELATIVE_PATH
    ).exists()
    with pytest.raises(
        materialize.RuntimeMaterializationError,
        match="cannot prove original two-pass provenance",
    ):
        materialize._materialize_runtime_dependency_authority(
            repo_root=fixture.repository.absolute(),
            staging_parent=fixture.staging.absolute(),
            services=fixture.services,
        )
    assert not (
        fixture.repository / materialize.MATERIALIZATION_RECEIPT_RELATIVE_PATH
    ).exists()


def test_receipt_publication_failure_recovers_idempotently_without_recopy(tmp_path):
    fixture = _fixture(tmp_path)
    failed = False
    events: list[str] = []

    def fail_once(step: str) -> None:
        nonlocal failed
        events.append(step)
        if step == "receipt-published" and not failed:
            failed = True
            raise RuntimeError("synthetic-publication-failure")

    services = replace(fixture.services, publication_hook=fail_once)
    with pytest.raises(RuntimeError, match="synthetic-publication-failure"):
        materialize._materialize_runtime_dependency_authority(
            repo_root=fixture.repository.absolute(),
            staging_parent=fixture.staging.absolute(),
            services=services,
        )
    sentinel = _write(fixture.staging / "capture-a", "recovery-sentinel.txt", b"x")
    with pytest.raises(materialize.RuntimeMaterializationError, match="staged tree"):
        materialize._materialize_runtime_dependency_authority(
            repo_root=fixture.repository.absolute(),
            staging_parent=fixture.staging.absolute(),
            services=services,
        )
    sentinel.unlink()
    result = materialize._materialize_runtime_dependency_authority(
        repo_root=fixture.repository.absolute(),
        staging_parent=fixture.staging.absolute(),
        services=services,
    )
    assert result.completion_path.is_file()
    replay = materialize._materialize_runtime_dependency_authority(
        repo_root=fixture.repository.absolute(),
        staging_parent=fixture.staging.absolute(),
        services=services,
    )
    assert replay.authority.authority_sha256 == result.authority.authority_sha256
    assert events[-1] == "completion-published"


def test_unique_atomic_publication_does_not_unlink_another_attempt(tmp_path):
    fixture = _fixture(tmp_path)
    target = (
        fixture.repository / "data/models/phase40/synthetic-receipt.json"
    ).absolute()
    foreign = materialize._publish_temp_path(target, nonce="a" * 32)
    foreign.write_bytes(b'{"partial":')

    payload = b'{"complete":true}\n'
    assert materialize._write_new_or_identical(
        target,
        payload,
        services=fixture.services,
    ) == target
    assert target.read_bytes() == payload
    assert foreign.read_bytes() == b'{"partial":'


def test_partial_temp_write_never_exposes_final_path(tmp_path, monkeypatch):
    fixture = _fixture(tmp_path)
    target = (
        fixture.repository / "data/models/phase40/synthetic-completion.json"
    ).absolute()
    attempted: list[Path] = []
    original = materialize._write_publish_temp

    def partial_then_crash(path, payload):  # noqa: ANN001, ANN201
        attempted.append(path)
        with path.open("xb") as handle:
            handle.write(payload[: max(1, len(payload) // 2)])
            handle.flush()
        raise OSError("synthetic-partial-write-crash")

    monkeypatch.setattr(materialize, "_write_publish_temp", partial_then_crash)
    with pytest.raises(
        materialize.RuntimeMaterializationError,
        match="failed to atomically publish fixed output",
    ):
        materialize._write_new_or_identical(
            target,
            b'{"complete":true}\n',
            services=fixture.services,
        )
    assert not target.exists()
    assert len(attempted) == 1
    assert not attempted[0].exists()

    monkeypatch.setattr(materialize, "_write_publish_temp", original)
    materialize._write_new_or_identical(
        target,
        b'{"complete":true}\n',
        services=fixture.services,
    )
    assert target.read_bytes() == b'{"complete":true}\n'


def test_partial_authority_temp_never_exposes_authority_or_receipt(
    tmp_path,
    monkeypatch,
):
    fixture = _fixture(tmp_path)
    original = materialize._write_publish_temp
    attempted: list[Path] = []

    def partial_authority_then_crash(path, payload):  # noqa: ANN001, ANN201
        if path.name.startswith(
            f".{materialize.RUNTIME_AUTHORITY_RELATIVE_PATH.name}."
        ):
            attempted.append(path)
            with path.open("xb") as handle:
                handle.write(payload[: max(1, len(payload) // 2)])
                handle.flush()
            raise OSError("synthetic-partial-authority-write")
        return original(path, payload)

    monkeypatch.setattr(
        materialize,
        "_write_publish_temp",
        partial_authority_then_crash,
    )
    with pytest.raises(
        materialize.RuntimeMaterializationError,
        match="failed to atomically publish fixed output",
    ):
        materialize._materialize_runtime_dependency_authority(
            repo_root=fixture.repository.absolute(),
            staging_parent=fixture.staging.absolute(),
            services=fixture.services,
        )
    assert len(attempted) == 1
    assert not attempted[0].exists()
    assert not (
        fixture.repository / materialize.RUNTIME_AUTHORITY_RELATIVE_PATH
    ).exists()
    assert not (
        fixture.repository / materialize.MATERIALIZATION_RECEIPT_RELATIVE_PATH
    ).exists()
    assert not (
        fixture.repository / materialize.MATERIALIZATION_COMPLETE_RELATIVE_PATH
    ).exists()


def test_external_verifier_rechecks_both_trees_and_both_exact_smokes(tmp_path):
    fixture = _fixture(tmp_path)
    calls: list[str] = []

    def recording_smoke(stage, expected, python):  # noqa: ANN001, ANN201
        calls.append(stage.capture_id)
        return _passing_smoke(stage, expected, python)

    services = replace(fixture.services, smoke_runner=recording_smoke)
    result = materialize._materialize_runtime_dependency_authority(
        repo_root=fixture.repository.absolute(),
        staging_parent=fixture.staging.absolute(),
        services=services,
    )
    calls.clear()
    verified = materialize._verify_runtime_dependency_materialization(
        repo_root=fixture.repository.absolute(),
        staging_parent=fixture.staging.absolute(),
        services=services,
    )
    assert verified.authority.authority_sha256 == result.authority.authority_sha256
    assert calls == ["capture-a", "capture-b"]

    target = fixture.staging / "capture-b/python-runtime/python313.dll"
    target.write_bytes(b"tampered")
    with pytest.raises(materialize.RuntimeMaterializationError, match="staged tree"):
        materialize._verify_runtime_dependency_materialization(
            repo_root=fixture.repository.absolute(),
            staging_parent=fixture.staging.absolute(),
            services=services,
        )
