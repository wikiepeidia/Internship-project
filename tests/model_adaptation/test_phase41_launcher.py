"""Static synthetic tests for the self-bound Phase 41 Windows launcher."""

from __future__ import annotations

from pathlib import Path
import re


LAUNCHER = Path("scripts/phase41_one_shot_launcher.ps1")


def test_launcher_is_clean_runtime_self_bound_and_has_no_authority_overrides():
    source = LAUNCHER.read_text(encoding="utf-8")
    lowered = source.casefold()
    assert "%programdata%" in lowered or "programdata" in lowered
    assert "phase41-one-shot-claims" in lowered
    assert "-i" in lowered and "-s" in lowered and "-b" in lowered
    assert "pythonpath" in lowered
    assert "execution-source-manifest.json" in lowered
    assert "phase41_one_shot_launcher.ps1" in lowered
    assert "createfile" in lowered or "fileshare" in lowered
    assert not re.search(
        r"param\s*\([^)]*\$(?:split|model|claim|registry|retry)",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )


def test_launcher_exposes_only_output_root_and_requires_canonical_run_command():
    source = LAUNCHER.read_text(encoding="utf-8")
    assert re.search(r"param\s*\([^)]*\$OutputRoot", source, flags=re.IGNORECASE | re.DOTALL)
    assert "phase41-run-once" in source
    for forbidden in ("--split-path", "--model-path", "--registry-root", "--retry"):
        assert forbidden not in source
