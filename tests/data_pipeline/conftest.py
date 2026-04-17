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
