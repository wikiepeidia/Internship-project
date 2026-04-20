"""
Shared test fixtures for all pipeline tests.

Provides reusable sample records that match the expected schema contracts.
"""

import pytest
from src.data_pipeline.schemas import SeedRecord, DatasetRecord, ManifestFile, ManifestEntry


@pytest.fixture
def sample_seed_record():
    """Valid NCSC seed record with natural Vietnamese code-switching."""
    return SeedRecord(
        text="Khẩn cấp: Tài khoản VPBank của bạn bị khóa. Vui lòng login tại http://vpbank-update.vip để xác thực OTP ngay.",
        source_url="https://canhbao.khonggianmang.vn/example-alert-123",
        scrape_timestamp="2026-04-17T10:30:00Z",
        raw_label_hint="bank_impersonation"
    )


@pytest.fixture
def sample_dataset_record():
    """Valid fully-processed dataset record with XAI artifacts."""
    return DatasetRecord(
        text="Khẩn cấp: Tài khoản VPBank của bạn bị khóa. Vui lòng login tại http://vpbank-update.vip để xác thực OTP ngay.",
        label="bank_impersonation",
        risk_tier="high-risk",
        suspicious_spans=[
            "http://vpbank-update.vip",
            "Khẩn cấp",
            "bị khóa"
        ],
        xai_explanation="Tin nhắn giả mạo ngân hàng VPBank với domain lừa đảo (vpbank-update.vip không phải tên miền chính thức). Sử dụng chiến thuật tâm lý gây cấp bách để buộc nạn nhân nhấn link và nhập thông tin đăng nhập.",
        source="ncsc_seed",
        seed_id="seed_20260417_001"
    )


@pytest.fixture
def sample_benign_record():
    """Valid benign message for negative class testing."""
    return DatasetRecord(
        text="Chúc mừng sinh nhật! Hẹn gặp bạn chiều nay nhé. Đừng quên mang theo món quà cho bé.",
        label="benign",
        risk_tier="benign",
        suspicious_spans=[],
        xai_explanation="Tin nhắn bình thường giữa bạn bè, không có dấu hiệu lừa đảo hoặc yêu cầu thông tin nhạy cảm.",
        source="synthetic_claude",
        seed_id="seed_benign_001"
    )


@pytest.fixture
def sample_manifest_entry():
    """Valid manifest entry for versioning tests."""
    return ManifestEntry(
        version="v1.0.0",
        build_timestamp="2026-04-17T12:00:00Z",
        git_commit="abc123def456",
        files={
            "train.jsonl": ManifestFile(
                sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                records=2400,
                bytes=1048576
            ),
            "val.jsonl": ManifestFile(
                sha256="d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592",
                records=300,
                bytes=131072
            ),
            "test.jsonl": ManifestFile(
                sha256="6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d",
                records=300,
                bytes=131072
            )
        }
    )


@pytest.fixture
def sample_ncsc_html():
    return """
    <html><body>
    <article>
        <h2 class="post-title"><a href="/advisory/1">Advisory 1</a></h2>
        <p>“Bạn đã trúng thưởng 1 tỷ đồng. Hãy truy cập ngay link http://phishing.com/claim để nhận thưởng”</p>
    </article>
    </body></html>
    """

@pytest.fixture
def sample_advisory_listing_html():
    return """
    <html><body>
    <div class="advisory-list">
        <h3 class="entry-title"><a href="/advisory/1">Phishing SMS 1</a></h3>
        <h3 class="entry-title"><a href="/advisory/2">Phishing SMS 2</a></h3>
        <h3 class="entry-title"><a href="https://external.com/advisory/3">External Advisory 3</a></h3>
    </div>
    </body></html>
    """

@pytest.fixture
def sample_advisory_detail_html():
    return """
    <html><body>
    <article class="post-content">
        <p>Người dùng nhận được tin nhắn lừa đảo với nội dung sau:</p>
        <blockquote>“Tài khoản của bạn đã bị khóa. Vui lòng truy cập http://scam.vn để mở khóa.”</blockquote>
    </article>
    </body></html>
    """


@pytest.fixture
def sample_validated_records():
    labels = ["bank_impersonation", "zalo_social_engineering", "task_scam", "benign"]
    risk_tiers = {
        "bank_impersonation": "high-risk",
        "zalo_social_engineering": "suspicious",
        "task_scam": "high-risk",
        "benign": "benign",
    }
    records = []
    for seed_index in range(5):
        for label_index, label in enumerate(labels):
            records.append(
                DatasetRecord(
                    text=f"Bản ghi {seed_index}-{label_index} với nội dung hợp lệ cho {label} và seed {seed_index}",
                    label=label,
                    risk_tier=risk_tiers[label],
                    suspicious_spans=[] if label == "benign" else [f"seed-{seed_index}"],
                    xai_explanation="Giải thích đủ dài để mỗi bản ghi hợp lệ và dùng cho kiểm thử pipeline.",
                    source="synthetic_gemini" if label != "bank_impersonation" else "synthetic_claude",
                    seed_id=f"seed-{seed_index}",
                ).model_dump()
            )
    return records


@pytest.fixture
def sample_validated_jsonl(tmp_path, sample_validated_records):
    jsonl_path = tmp_path / "processed" / "validated.jsonl"
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in sample_validated_records:
            handle.write(DatasetRecord.model_validate(record).model_dump_json() + "\n")
    return jsonl_path
