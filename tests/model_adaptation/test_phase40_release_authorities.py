"""Synthetic-only tests for Phase 40 release runtime authorities."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import threading

import pytest

from src.model_adaptation import phase40_release_authorities as release


def _write_fixture_file(root: Path, relative: str, payload: bytes) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _synthetic_inputs(tmp_path: Path):
    python_root = tmp_path / "synthetic-python"
    torch_root = tmp_path / "synthetic-torch-distribution"
    underthesea_root = tmp_path / "synthetic-underthesea-distribution"
    python_root.mkdir()
    torch_root.mkdir()
    underthesea_root.mkdir()
    _write_fixture_file(python_root, "python.exe", b"MZ-synthetic-python-3.13.7")
    _write_fixture_file(python_root, "python313.dll", b"synthetic-python-runtime-dll")
    _write_fixture_file(
        python_root,
        "Lib/encodings/utf_8.py",
        b"synthetic-stdlib-codec\n",
    )

    torch_files = (
        Path("torch/__init__.py"),
        Path("torch/_C.pyd"),
        Path("torch-2.8.0.dist-info/METADATA"),
    )
    _write_fixture_file(torch_root, torch_files[0].as_posix(), b"__version__='2.8.0'\n")
    _write_fixture_file(torch_root, torch_files[1].as_posix(), b"synthetic-native-torch")
    _write_fixture_file(
        torch_root,
        torch_files[2].as_posix(),
        b"Name: torch\nVersion: 2.8.0\n",
    )

    underthesea_files = (
        Path("underthesea/__init__.py"),
        Path("underthesea/word_tokenize.py"),
        Path("underthesea-9.5.0.dist-info/RECORD"),
    )
    _write_fixture_file(
        underthesea_root,
        underthesea_files[0].as_posix(),
        b"from .word_tokenize import word_tokenize\n",
    )
    _write_fixture_file(
        underthesea_root,
        underthesea_files[1].as_posix(),
        b"def word_tokenize(text, format='text'): return text\n",
    )
    _write_fixture_file(
        underthesea_root,
        underthesea_files[2].as_posix(),
        b"synthetic complete RECORD\n",
    )

    python = release.PythonCaptureInput(
        implementation="CPython",
        version="3.13.7",
        cache_tag="cpython-313",
        abi_flags="",
        platform="win-amd64-synthetic",
        executable_root=python_root.absolute(),
        executable=Path("python.exe"),
    )
    distributions = (
        release.DistributionCaptureInput(
            name="UnderTheSea",
            version="9.5.0",
            install_root=underthesea_root.absolute(),
            import_origin=Path("underthesea/__init__.py"),
            declared_files=underthesea_files,
        ),
        release.DistributionCaptureInput(
            name="Torch",
            version="2.8.0",
            install_root=torch_root.absolute(),
            import_origin=Path("torch/__init__.py"),
            declared_files=torch_files,
        ),
    )
    expected = {"torch": "2.8.0", "underthesea": "9.5.0"}
    package_roots = {"torch": torch_root, "underthesea": underthesea_root}
    return python, distributions, expected, python_root, package_roots


def _capture(tmp_path: Path):
    python, distributions, expected, python_root, package_roots = _synthetic_inputs(
        tmp_path
    )
    authority = release.capture_runtime_dependency_authority(
        python,
        distributions,
        expected_distributions=expected,
    )
    return authority, python, distributions, expected, python_root, package_roots


def test_capture_binds_python_closure_files_and_independent_segmenter(tmp_path):
    authority, _, _, _, _, _ = _capture(tmp_path)

    assert authority.schema_version == release.RUNTIME_AUTHORITY_SCHEMA_VERSION
    assert tuple(item.name for item in authority.distributions) == (
        "torch",
        "underthesea",
    )
    assert authority.python.executable.relative_path == "python.exe"
    assert authority.python.executable.bytes == len(b"MZ-synthetic-python-3.13.7")
    assert tuple(item.relative_path for item in authority.python.files) == (
        "Lib/encodings/utf_8.py",
        "python.exe",
        "python313.dll",
    )
    assert len(authority.python.tree_sha256) == 64
    segmenter_distribution = authority.distributions[1]
    assert authority.segmenter.distribution_name == "underthesea"
    assert (
        authority.segmenter.distribution_tree_sha256
        == segmenter_distribution.tree_sha256
    )
    assert (
        authority.segmenter.distribution_authority_sha256
        == segmenter_distribution.authority_sha256
    )
    assert authority.segmenter_sha256 == authority.segmenter.authority_sha256
    assert authority.segmenter_sha256 != authority.authority_sha256
    assert tuple(
        file.relative_path for file in segmenter_distribution.files
    ) == tuple(
        sorted(
            (
                "underthesea/__init__.py",
                "underthesea/word_tokenize.py",
                "underthesea-9.5.0.dist-info/RECORD",
            )
        )
    )


def test_write_load_and_verify_round_trip_is_canonical_and_durable(
    tmp_path, monkeypatch
):
    authority, python, distributions, expected, _, _ = _capture(tmp_path)
    output_root = tmp_path / "authority"
    output_root.mkdir()
    output = output_root / release.RUNTIME_AUTHORITY_FILENAME
    fsync_calls: list[int] = []
    original_fsync = os.fsync

    def record_fsync(descriptor: int) -> None:
        fsync_calls.append(descriptor)
        original_fsync(descriptor)

    monkeypatch.setattr(os, "fsync", record_fsync)
    assert release.write_runtime_dependency_authority(output, authority) == output
    payload = output.read_bytes()
    assert payload == release.canonical_json_bytes(authority.as_dict())
    assert fsync_calls
    loaded = release.load_runtime_dependency_authority(output)
    assert loaded == authority
    assert (
        release.verify_runtime_dependency_authority(
            output,
            python,
            distributions,
            expected_distributions=expected,
        )
        == authority
    )
    assert release.write_runtime_dependency_authority(output, authority) == output


@pytest.mark.parametrize("drift", ("python", "distribution"))
def test_verify_rejects_same_version_byte_drift(tmp_path, drift):
    authority, python, distributions, expected, python_root, package_roots = _capture(
        tmp_path
    )
    if drift == "python":
        (python_root / "python.exe").write_bytes(b"MZ-drifted-python-3.13.7")
    else:
        (package_roots["underthesea"] / "underthesea/word_tokenize.py").write_bytes(
            b"def word_tokenize(*args): return 'drift'\n"
        )
    with pytest.raises(release.ReleaseAuthorityError, match="verification drifted"):
        release.verify_runtime_dependency_authority(
            authority,
            python,
            distributions,
            expected_distributions=expected,
        )


def test_omitted_importable_or_native_file_can_never_escape_verification(tmp_path):
    authority, python, distributions, expected, python_root, package_roots = _capture(
        tmp_path
    )
    omitted_native = _write_fixture_file(
        package_roots["underthesea"],
        "underthesea/undeclared_native.pyd",
        b"first-native-bytes",
    )
    omitted_native.write_bytes(b"mutated-native-bytes")
    with pytest.raises(release.ReleaseAuthorityError, match="declared inventory"):
        release.verify_runtime_dependency_authority(
            authority,
            python,
            distributions,
            expected_distributions=expected,
        )

    omitted_native.unlink()
    _write_fixture_file(
        python_root,
        "DLLs/undeclared_runtime.pyd",
        b"unlisted-python-runtime-native",
    )
    with pytest.raises(release.ReleaseAuthorityError, match="verification drifted"):
        release.verify_runtime_dependency_authority(
            authority,
            python,
            distributions,
            expected_distributions=expected,
        )


def test_capture_rejects_closed_tree_membership_change_during_hashing(
    tmp_path, monkeypatch
):
    python, distributions, expected, _, package_roots = _synthetic_inputs(tmp_path)
    underthesea_root = package_roots["underthesea"].absolute()
    original_capture = release._capture_regular_file
    injected = False

    def capture_then_add(root, candidate, description):
        nonlocal injected
        captured = original_capture(root, candidate, description)
        if root == underthesea_root and not injected:
            injected = True
            _write_fixture_file(
                underthesea_root,
                "underthesea/late_module.py",
                b"transient capture-time addition\n",
            )
        return captured

    monkeypatch.setattr(release, "_capture_regular_file", capture_then_add)
    with pytest.raises(release.ReleaseAuthorityError, match="changed (while|during)"):
        release.capture_runtime_dependency_authority(
            python,
            distributions,
            expected_distributions=expected,
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows ancestry handles required")
def test_equal_shape_root_swap_cannot_feed_untrusted_capture_bytes(
    tmp_path, monkeypatch
):
    python, distributions, expected, _, package_roots = _synthetic_inputs(tmp_path)
    trusted_root = package_roots["underthesea"].absolute()
    malicious_root = (tmp_path / "malicious-underthesea").absolute()
    parked_root = (tmp_path / "parked-underthesea").absolute()
    malicious_root.mkdir()
    trusted_word_tokenizer = trusted_root / "underthesea/word_tokenize.py"
    trusted_payload = trusted_word_tokenizer.read_bytes()
    for relative in distributions[0].declared_files:
        payload = (trusted_root / relative).read_bytes()
        if relative.as_posix() == "underthesea/word_tokenize.py":
            payload = b"X" * len(payload)
        _write_fixture_file(malicious_root, relative.as_posix(), payload)

    begin_swap = threading.Event()
    swap_finished = threading.Event()
    request_restore = threading.Event()
    restore_finished = threading.Event()
    attack_errors: list[OSError] = []
    rename_succeeded: list[bool] = []

    def attacker() -> None:
        assert begin_swap.wait(5), "capture never reached the swap point"
        try:
            trusted_root.rename(parked_root)
        except OSError as exc:
            attack_errors.append(exc)
            swap_finished.set()
            restore_finished.set()
            return
        rename_succeeded.append(True)
        malicious_root.rename(trusted_root)
        swap_finished.set()
        assert request_restore.wait(5), "capture never requested root restoration"
        trusted_root.rename(malicious_root)
        parked_root.rename(trusted_root)
        restore_finished.set()

    original_inventory = release._closed_tree_inventory
    trusted_inventory_calls = 0

    def synchronized_inventory(root: Path, description: str):
        nonlocal trusted_inventory_calls
        if Path(root) == trusted_root:
            trusted_inventory_calls += 1
            if trusted_inventory_calls == 1:
                observed = original_inventory(root, description)
                begin_swap.set()
                assert swap_finished.wait(5), "root-swap attack did not finish"
                return observed
            if trusted_inventory_calls == 3:
                request_restore.set()
                assert restore_finished.wait(5), "trusted root was not restored"
        return original_inventory(root, description)

    monkeypatch.setattr(release, "_closed_tree_inventory", synchronized_inventory)
    attack = threading.Thread(target=attacker, daemon=True)
    attack.start()
    authority = release.capture_runtime_dependency_authority(
        python,
        distributions,
        expected_distributions=expected,
    )
    attack.join(5)

    assert not attack.is_alive()
    assert attack_errors and isinstance(attack_errors[0], PermissionError)
    assert rename_succeeded == []
    underthesea = next(
        item for item in authority.distributions if item.name == "underthesea"
    )
    captured = next(
        item
        for item in underthesea.files
        if item.relative_path == "underthesea/word_tokenize.py"
    )
    assert captured.sha256 == hashlib.sha256(trusted_payload).hexdigest()


@pytest.mark.skipif(os.name != "nt", reason="Windows change fence required")
def test_same_size_write_between_inventory_and_entry_handles_is_rejected(
    tmp_path, monkeypatch
):
    python, distributions, expected, _, package_roots = _synthetic_inputs(tmp_path)
    underthesea_root = package_roots["underthesea"].absolute()
    target = underthesea_root / "underthesea/word_tokenize.py"
    trusted_payload = target.read_bytes()
    malicious_payload = b"X" * len(trusted_payload)
    original_inventory = release._closed_tree_inventory
    mutation_executed = False

    def inventory_then_overwrite(root: Path, description: str):
        nonlocal mutation_executed
        observed = original_inventory(root, description)
        if Path(root) == underthesea_root and not mutation_executed:
            target.write_bytes(malicious_payload)
            mutation_executed = True
        return observed

    monkeypatch.setattr(
        release,
        "_closed_tree_inventory",
        inventory_then_overwrite,
    )
    with pytest.raises(release.ReleaseAuthorityError, match="changed during"):
        release.capture_runtime_dependency_authority(
            python,
            distributions,
            expected_distributions=expected,
        )

    assert mutation_executed is True
    assert target.read_bytes() == malicious_payload


@pytest.mark.skipif(os.name != "nt", reason="Windows closure handles required")
def test_earlier_runtime_root_stays_locked_until_full_closure_is_built(
    tmp_path, monkeypatch
):
    python, distributions, expected, python_root, _ = _synthetic_inputs(tmp_path)
    runtime_dll = python_root / "python313.dll"
    trusted_payload = runtime_dll.read_bytes()
    original_builder = release._build_distribution_authority
    attack_errors: list[OSError] = []
    attempted = False

    def build_after_runtime_attack(capture, *, lease=None):
        nonlocal attempted
        if not attempted:
            attempted = True
            try:
                runtime_dll.write_bytes(b"malicious-runtime-drift")
            except OSError as exc:
                attack_errors.append(exc)
        return original_builder(capture, lease=lease)

    monkeypatch.setattr(
        release,
        "_build_distribution_authority",
        build_after_runtime_attack,
    )
    authority = release.capture_runtime_dependency_authority(
        python,
        distributions,
        expected_distributions=expected,
    )

    assert attempted is True
    assert attack_errors and isinstance(attack_errors[0], PermissionError)
    runtime_file = next(
        item for item in authority.python.files if item.relative_path == "python313.dll"
    )
    assert runtime_file.sha256 == hashlib.sha256(trusted_payload).hexdigest()


@pytest.mark.parametrize(
    "problem",
    ("missing", "out_of_root", "origin_out_of_root", "origin_not_declared"),
)
def test_capture_rejects_missing_out_of_root_and_unowned_import_origin(
    tmp_path, problem
):
    python, distributions, expected, _, package_roots = _synthetic_inputs(tmp_path)
    underthesea = distributions[0]
    if problem == "missing":
        bad = replace(
            underthesea,
            declared_files=(*underthesea.declared_files, Path("underthesea/missing.py")),
        )
    elif problem == "out_of_root":
        escape = _write_fixture_file(tmp_path, "escape.py", b"outside")
        bad = replace(
            underthesea,
            declared_files=(*underthesea.declared_files, escape.absolute()),
        )
    elif problem == "origin_out_of_root":
        origin = _write_fixture_file(tmp_path, "outside_origin.py", b"outside")
        bad = replace(underthesea, import_origin=origin.absolute())
    else:
        _write_fixture_file(
            package_roots["underthesea"],
            "underthesea/private_origin.py",
            b"private",
        )
        bad = replace(
            underthesea,
            import_origin=Path("underthesea/private_origin.py"),
        )
    with pytest.raises(release.ReleaseAuthorityError, match="missing|out-of-root|declared"):
        release.capture_runtime_dependency_authority(
            python,
            (bad, distributions[1]),
            expected_distributions=expected,
        )


def test_capture_rejects_symlink_or_reparse_declared_entry(tmp_path, monkeypatch):
    python, distributions, expected, _, package_roots = _synthetic_inputs(tmp_path)
    redirecting = package_roots["underthesea"] / "underthesea/word_tokenize.py"
    original = release._path_is_redirecting
    monkeypatch.setattr(
        release,
        "_path_is_redirecting",
        lambda path: Path(path) == redirecting or original(path),
    )
    with pytest.raises(release.ReleaseAuthorityError, match="symlink/reparse"):
        release.capture_runtime_dependency_authority(
            python,
            distributions,
            expected_distributions=expected,
        )


def test_capture_rejects_symlink_or_reparse_trusted_root(tmp_path, monkeypatch):
    python, distributions, expected, _, _ = _synthetic_inputs(tmp_path)
    redirecting_root = distributions[0].install_root
    original = release._path_is_redirecting
    monkeypatch.setattr(
        release,
        "_path_is_redirecting",
        lambda path: Path(path) == redirecting_root or original(path),
    )
    with pytest.raises(release.ReleaseAuthorityError, match="ancestry is symlink/reparse"):
        release.capture_runtime_dependency_authority(
            python,
            distributions,
            expected_distributions=expected,
        )


def test_capture_rejects_duplicate_normalized_distribution_names(tmp_path):
    python, distributions, _, _, _ = _synthetic_inputs(tmp_path)
    duplicate = replace(distributions[1], name="torch")
    with pytest.raises(release.ReleaseAuthorityError, match="duplicate normalized"):
        release.capture_runtime_dependency_authority(
            python,
            (distributions[1], duplicate, distributions[0]),
            expected_distributions={"torch": "2.8.0", "underthesea": "9.5.0"},
        )


def test_capture_rejects_duplicate_file_ownership_across_distributions(tmp_path):
    python, distributions, _, _, _ = _synthetic_inputs(tmp_path)
    shared = Path("torch/__init__.py")
    alias = release.DistributionCaptureInput(
        name="torch-addon",
        version="1.0.0",
        install_root=distributions[1].install_root,
        import_origin=shared,
        declared_files=distributions[1].declared_files,
    )
    with pytest.raises(release.ReleaseAuthorityError, match="duplicate file ownership"):
        release.capture_runtime_dependency_authority(
            python,
            (*distributions, alias),
            expected_distributions={
                "torch": "2.8.0",
                "torch-addon": "1.0.0",
                "underthesea": "9.5.0",
            },
        )


def test_capture_rejects_duplicate_declared_path_and_hardlink(tmp_path):
    python, distributions, expected, _, package_roots = _synthetic_inputs(tmp_path)
    duplicate = replace(
        distributions[0],
        declared_files=(
            *distributions[0].declared_files,
            distributions[0].declared_files[0],
        ),
    )
    with pytest.raises(release.ReleaseAuthorityError, match="ownership is duplicate"):
        release.capture_runtime_dependency_authority(
            python,
            (duplicate, distributions[1]),
            expected_distributions=expected,
        )

    underthesea_root = package_roots["underthesea"]
    hardlink = underthesea_root / "underthesea/hardlink.py"
    try:
        os.link(underthesea_root / "underthesea/word_tokenize.py", hardlink)
    except OSError:
        pytest.skip("fixture filesystem does not support hardlinks")
    linked = replace(
        distributions[0],
        declared_files=(*distributions[0].declared_files, Path("underthesea/hardlink.py")),
    )
    with pytest.raises(release.ReleaseAuthorityError, match="duplicate physical"):
        release.capture_runtime_dependency_authority(
            python,
            (linked, distributions[1]),
            expected_distributions=expected,
        )


@pytest.mark.parametrize("problem", ("missing", "version", "duplicate_expected"))
def test_capture_requires_exact_normalized_dependency_closure(tmp_path, problem):
    python, distributions, expected, _, _ = _synthetic_inputs(tmp_path)
    if problem == "missing":
        closure = {"underthesea": "9.5.0"}
    elif problem == "version":
        closure = {**expected, "torch": "2.8.1"}
    else:
        closure = {
            "underthesea": "9.5.0",
            "Demo_Package": "1.0.0",
            "demo-package": "1.0.0",
        }
    with pytest.raises(release.ReleaseAuthorityError, match="closure|duplicate"):
        release.capture_runtime_dependency_authority(
            python,
            distributions,
            expected_distributions=closure,
        )


@pytest.mark.parametrize(
    "corruption",
    ("duplicate_key", "noncanonical", "self_hash", "extra_field", "nonfinite"),
)
def test_loader_rejects_malformed_noncanonical_and_self_hash_drift(
    tmp_path, corruption
):
    authority, _, _, _, _, _ = _capture(tmp_path)
    output_root = tmp_path / "corrupt-authority"
    output_root.mkdir()
    path = output_root / release.RUNTIME_AUTHORITY_FILENAME
    valid = release.canonical_json_bytes(authority.as_dict())
    if corruption == "duplicate_key":
        payload = valid.replace(
            b'"authority_sha256":',
            b'"authority_sha256":"0","authority_sha256":',
            1,
        )
    else:
        raw = json.loads(valid)
        if corruption == "noncanonical":
            payload = (json.dumps(raw, indent=2) + "\n").encode()
        elif corruption == "self_hash":
            raw["authority_sha256"] = "0" * 64
            payload = release.canonical_json_bytes(raw)
        elif corruption == "extra_field":
            raw["unexpected"] = True
            payload = release.canonical_json_bytes(raw)
        else:
            payload = valid.replace(
                b'"authority_sha256":',
                b'"unexpected_number":NaN,"authority_sha256":',
                1,
            )
    path.write_bytes(payload)
    with pytest.raises(release.ReleaseAuthorityError):
        release.load_runtime_dependency_authority(path)


def test_distribution_and_segmenter_subhash_mismatch_fail_closed(tmp_path):
    authority, _, _, _, _, _ = _capture(tmp_path)
    raw = authority.as_dict()
    raw["distributions"][1]["tree_sha256"] = "0" * 64
    with pytest.raises(release.ReleaseAuthorityError, match="tree hash mismatch"):
        release.RuntimeDependencyAuthority.from_dict(raw)

    raw = authority.as_dict()
    raw["segmenter"]["distribution_tree_sha256"] = "0" * 64
    segmenter_body = dict(raw["segmenter"])
    del segmenter_body["authority_sha256"]
    raw["segmenter"]["authority_sha256"] = hashlib.sha256(
        release.canonical_json_bytes(segmenter_body)
    ).hexdigest()
    with pytest.raises(release.ReleaseAuthorityError, match="does not match"):
        release.RuntimeDependencyAuthority.from_dict(raw)


def test_writer_refuses_to_replace_different_existing_bytes(tmp_path):
    authority, _, _, _, _, _ = _capture(tmp_path)
    output_root = tmp_path / "immutable-authority"
    output_root.mkdir()
    path = output_root / release.RUNTIME_AUTHORITY_FILENAME
    path.write_bytes(b"occupied")
    with pytest.raises(FileExistsError, match="refusing to replace"):
        release.write_runtime_dependency_authority(path, authority)
