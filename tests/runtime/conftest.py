"""Shared fixtures for Phase 2 runtime tests."""

import pytest

from src.runtime.contracts import SuspiciousCue


@pytest.fixture
def sample_mixed_vn_en_message() -> str:
    return (
        "VPBank cảnh báo account Internet Banking của bạn sẽ bị khóa trong 24h. "
        "Không chia sẻ mã OTP hoặc Smart OTP và không bấm vào link đăng nhập "
        "https://vpbank-secure.example để xác minh ngay."
    )


@pytest.fixture
def sample_benign_message() -> str:
    return (
        "Chào bạn, lịch họp nhóm được dời sang 9h sáng mai tại phòng học tầng 3. "
        "Nếu bận thì báo lại giúp mình trước tối nay."
    )


@pytest.fixture
def sample_short_message() -> str:
    return "OTP?"


@pytest.fixture
def sample_non_text_placeholder() -> str:
    return "[image attached]"


@pytest.fixture
def expected_runtime_cues() -> list[SuspiciousCue]:
    return [
        SuspiciousCue(span="mã OTP", reason="Yêu cầu mã xác thực nhạy cảm"),
        SuspiciousCue(span="Smart OTP", reason="Nhắc tới công cụ xác thực ngân hàng"),
        SuspiciousCue(span="link đăng nhập", reason="Dẫn người dùng tới liên kết đăng nhập"),
        SuspiciousCue(span="trong 24h", reason="Tạo áp lực thời gian"),
    ]