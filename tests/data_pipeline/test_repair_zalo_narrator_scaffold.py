"""Tests for the Phase 39 zalo narrator-scaffold repair script."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.data_pipeline.repair_zalo_narrator_scaffold import (
    drop_near_duplicate_zalo_rows,
    extract_quoted_message,
    find_new_near_duplicates,
    main,
    repair_zalo_rows,
)


def _zalo_row(text: str, seed_id: str = "seed_1", spans: list[str] | None = None) -> dict:
    return {
        "text": text,
        "label": "zalo_social_engineering",
        "risk_tier": "high-risk",
        "suspicious_spans": spans or [],
        "xai_explanation": "Explanation long enough to satisfy the schema minimum length.",
        "source": "synthetic_openai_compatible",
        "seed_id": seed_id,
    }


def _other_row(label: str = "benign", seed_id: str = "seed_2") -> dict:
    return {
        "text": "Mot tin nhan binh thuong khong lien quan den lua dao chut nao.",
        "label": label,
        "risk_tier": "benign",
        "suspicious_spans": [],
        "xai_explanation": "Explanation long enough to satisfy the schema minimum length.",
        "source": "synthetic_claude",
        "seed_id": seed_id,
    }


# --- extract_quoted_message --------------------------------------------------


def test_extract_quoted_message_pulls_single_quote():
    text = 'Tin Zalo tu bac si: "Con trai ban dang cap cuu, chuyen tien gap."'.replace(
        '"', "“", 1
    ).replace('"', "”", 1)
    result = extract_quoted_message(text)
    assert result == "Con trai ban dang cap cuu, chuyen tien gap."


def test_extract_quoted_message_joins_multiple_quotes():
    text = "Nguoi nay noi “Cau dau tien.” va dan “Cau thu hai.”"
    result = extract_quoted_message(text)
    assert result == "Cau dau tien. Cau thu hai."


def test_extract_quoted_message_returns_none_without_quotes():
    assert extract_quoted_message("Khong co dau ngoac kep nao trong doan nay ca.") is None


def test_extract_quoted_message_returns_none_for_too_short_result():
    assert extract_quoted_message("Scaffold noi “ok” thoi.") is None


# --- repair_zalo_rows ---------------------------------------------------------


def test_repair_zalo_rows_replaces_text_for_zalo_rows_only():
    zalo = _zalo_row(
        "Tin Zalo tu bac si: “Con trai ban dang cap cuu, chuyen tien gap qua vi dien tu.”"
    )
    other = _other_row()
    repaired, stats = repair_zalo_rows([zalo, other])

    assert stats["zalo_rows_repaired"] == 1
    assert stats["zalo_rows_unrepairable"] == 0
    assert repaired[0]["text"] == "Con trai ban dang cap cuu, chuyen tien gap qua vi dien tu."
    assert repaired[1] == other  # untouched


def test_repair_zalo_rows_keeps_original_when_no_quotes_present():
    zalo = _zalo_row("Mot dong tin nhan Zalo khong co dau ngoac kep gi ca trong noi dung.")
    repaired, stats = repair_zalo_rows([zalo])

    assert stats["zalo_rows_repaired"] == 0
    assert stats["zalo_rows_unrepairable"] == 1
    assert repaired[0]["text"] == zalo["text"]


def test_repair_zalo_rows_preserves_valid_suspicious_spans():
    zalo = _zalo_row(
        "Tin Zalo tu admin: “Quet ma QR de nhan qua tang mien phi ngay hom nay.”",
        spans=["Quet ma QR"],
    )
    repaired, stats = repair_zalo_rows([zalo])

    assert stats["zalo_rows_repaired"] == 1
    assert repaired[0]["suspicious_spans"] == ["Quet ma QR"]
    assert repaired[0]["suspicious_spans"][0] in repaired[0]["text"]


def test_repair_zalo_rows_drops_original_and_keeps_row_when_span_would_break():
    zalo = _zalo_row(
        "Tin nhan tu ke gian: “Chuyen tien ngay lap tuc qua tai khoan nay.”",
        spans=["tu ke gian"],  # only present in the narrator scaffold, not the quote
    )
    repaired, stats = repair_zalo_rows([zalo])

    # extraction would break the span -> row is left completely untouched
    assert stats["zalo_rows_repaired"] == 0
    assert stats["zalo_rows_unrepairable"] == 1
    assert repaired[0]["text"] == zalo["text"]
    assert repaired[0]["suspicious_spans"] == ["tu ke gian"]


# --- find_new_near_duplicates -------------------------------------------------


def test_find_new_near_duplicates_flags_identical_zalo_rows():
    rows = [
        _zalo_row("Chuyen tien gap qua vi dien tu de cuu nguoi than dang cap cuu.", seed_id="s1"),
        _zalo_row("Chuyen tien gap qua vi dien tu de cuu nguoi than dang cap cuu.", seed_id="s2"),
        _other_row(),
    ]
    pairs = find_new_near_duplicates(rows)
    assert pairs == [(0, 1)]


def test_find_new_near_duplicates_ignores_distinct_rows():
    rows = [
        _zalo_row("Chuyen tien gap qua vi dien tu de cuu nguoi than dang cap cuu.", seed_id="s1"),
        _zalo_row("Xe cuu ho can dat coc truoc khi keo xe ve gara sua chua.", seed_id="s2"),
    ]
    assert find_new_near_duplicates(rows) == []


# --- drop_near_duplicate_zalo_rows -------------------------------------------


def test_drop_near_duplicate_zalo_rows_drops_later_same_seed_duplicate():
    rows = [
        _zalo_row("Chuyen tien gap qua vi dien tu de cuu nguoi than dang cap cuu.", seed_id="s1"),
        _zalo_row("Chuyen tien gap qua vi dien tu de cuu nguoi than dang cap cuu.", seed_id="s1"),
        _other_row(seed_id="s2"),
    ]
    survivors, stats = drop_near_duplicate_zalo_rows(rows)

    assert stats["zalo_near_duplicates_dropped"] == 1
    assert len(survivors) == 2
    assert survivors[0]["text"] == rows[0]["text"]
    assert survivors[1] is rows[2]


def test_drop_near_duplicate_zalo_rows_keeps_distinct_rows():
    rows = [
        _zalo_row("Chuyen tien gap qua vi dien tu de cuu nguoi than dang cap cuu.", seed_id="s1"),
        _zalo_row("Xe cuu ho can dat coc truoc khi keo xe ve gara sua chua.", seed_id="s2"),
    ]
    survivors, stats = drop_near_duplicate_zalo_rows(rows)

    assert stats["zalo_near_duplicates_dropped"] == 0
    assert len(survivors) == 2


def test_drop_near_duplicate_zalo_rows_raises_on_cross_seed_duplicate():
    rows = [
        _zalo_row("Chuyen tien gap qua vi dien tu de cuu nguoi than dang cap cuu.", seed_id="s1"),
        _zalo_row("Chuyen tien gap qua vi dien tu de cuu nguoi than dang cap cuu.", seed_id="s2"),
    ]
    with pytest.raises(ValueError, match="DIFFERENT"):
        drop_near_duplicate_zalo_rows(rows)


# --- end-to-end CLI ------------------------------------------------------------


def test_main_repairs_splits_on_disk(tmp_path: Path, monkeypatch, capsys):
    splits_dir = tmp_path / "splits"
    splits_dir.mkdir()

    import json

    train_rows = [
        _zalo_row(
            "Tin Zalo tu bac si: “Con trai ban dang cap cuu, chuyen tien gap qua vi dien tu.”",
            seed_id="s1",
        ),
        _other_row(seed_id="s2"),
    ]
    val_rows = [
        _zalo_row(
            "Mot tai khoan moi tu xung nhan vien: “Dat coc truoc de nhan qua khuyen mai lon.”",
            seed_id="s3",
        )
    ]
    test_rows = [_other_row(seed_id="s4")]

    for name, rows in (("train", train_rows), ("val", val_rows), ("test", test_rows)):
        with (splits_dir / f"{name}.jsonl").open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    monkeypatch.setattr(
        "sys.argv", ["repair_zalo_narrator_scaffold.py", "--splits-dir", str(splits_dir)]
    )
    main()

    with (splits_dir / "train.jsonl").open(encoding="utf-8") as handle:
        repaired_train = [json.loads(line) for line in handle if line.strip()]
    assert repaired_train[0]["text"] == (
        "Con trai ban dang cap cuu, chuyen tien gap qua vi dien tu."
    )
    assert repaired_train[1]["text"] == train_rows[1]["text"]

    captured = capsys.readouterr()
    assert "repaired 1" in captured.out
