"""Weighted scam and credential-theft cues for local phishing-risk analysis."""

from dataclasses import dataclass
import re
from typing import Pattern

from src.runtime.contracts import RiskTier


@dataclass(frozen=True)
class CueRule:
    """One weighted rule for suspicious text matching."""

    cue_type: str
    pattern: Pattern[str]
    reason: str
    weight: int
    tier_override: RiskTier | None = None


def _compile(pattern: str) -> Pattern[str]:
    return re.compile(pattern)


def build_default_rules() -> list[CueRule]:
    """Build the default weighted cue catalog for local heuristic analysis."""

    return [
        CueRule(
            cue_type="credential_request",
            pattern=_compile(r"\b(?:otp|mã otp|smart otp|internet banking|mật khẩu|password)\b"),
            reason="Yêu cầu mã xác thực hoặc thông tin đăng nhập nhạy cảm.",
            weight=3,
            tier_override="high-risk",
        ),
        CueRule(
            cue_type="link_prompt",
            pattern=_compile(r"\b(?:http://|https://|bit\.ly|tinyurl|đăng nhập|login|xác minh|cập nhật|mở khóa)\b"),
            reason="Dẫn người dùng tới thao tác xác minh hoặc liên kết đăng nhập.",
            weight=2,
        ),
        CueRule(
            cue_type="urgency",
            pattern=_compile(r"\b(?:khẩn cấp|ngay|gấp|urgent|trong 24h|nếu không)\b"),
            reason="Tạo áp lực thời gian để thúc ép hành động nhanh.",
            weight=2,
        ),
        CueRule(
            cue_type="bank_impersonation",
            pattern=_compile(
                r"\b(?:vpbank|vietcombank|techcombank|mb bank|agribank)\b(?=[^\n]{0,60}\b(?:xác minh|cập nhật|mở khóa|đăng nhập)\b)"
            ),
            reason="Giả mạo thương hiệu ngân hàng kèm yêu cầu hành động.",
            weight=4,
            tier_override="high-risk",
        ),
        CueRule(
            cue_type="task_scam",
            pattern=_compile(r"\b(?:việc nhẹ lương cao|nhiệm vụ|hoa hồng|cộng tác viên|nạp tiền)\b"),
            reason="Cấu trúc quen thuộc của lừa đảo nhiệm vụ hoặc việc nhẹ lương cao.",
            weight=3,
        ),
    ]
