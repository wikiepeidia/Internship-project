"""Terminal rendering for phishing-risk analysis results and runtime errors."""

import re

from src.runtime.contracts import AnalysisResult


_RISK_TIER_DISPLAY = {
    "benign": "Benign",
    "suspicious": "Suspicious",
    "high-risk": "High risk",
}

_THREAT_LABEL_DISPLAY = {
    "bank_impersonation": "Bank impersonation",
    "zalo_social_engineering": "Zalo social engineering",
    "task_scam": "Task scam",
    "benign": "Benign",
}

# C0/C1 control characters (excluding the ones already normalized out of
# pasted text, e.g. \t \n) plus DEL. This blocks ANSI CSI/OSC escape
# injection (\x1b[... , \x1b]...\x07) and other terminal control sequences
# from reaching stdout via user-controlled analysis text (CR-01).
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def _terminal_safe(text: str) -> str:
    """Strip control/escape characters before user-derived text reaches the terminal."""

    return _CONTROL_CHARS.sub("", text)


def render_analysis_result(result: AnalysisResult) -> str:
    """Render a short human-readable result with up to three quoted cues."""

    if not result.top_cues and not result.threat_labels and not result.recommendations:
        return _terminal_safe(result.summary)

    lines = [_terminal_safe(result.summary)]

    if result.threat_labels or result.recommendations:
        lines.append(f"Risk tier: {_RISK_TIER_DISPLAY[result.risk_tier]}")

    if result.threat_labels:
        label_text = ", ".join(
            _terminal_safe(_THREAT_LABEL_DISPLAY.get(label, label.replace("_", " ").title()))
            for label in result.threat_labels
        )
        lines.append(f"Threat labels: {label_text}")

    if result.top_cues:
        if result.threat_labels or result.recommendations:
            lines.append("Grounded cues:")
            lines.extend(
                f'- "{_terminal_safe(cue.span)}" - {_terminal_safe(cue.reason)}' for cue in result.top_cues[:3]
            )
        else:
            lines.extend(
                f'"{_terminal_safe(cue.span)}" - {_terminal_safe(cue.reason)}' for cue in result.top_cues[:3]
            )

    if result.recommendations:
        lines.append("Next steps:")
        lines.extend(f"- {_terminal_safe(recommendation)}" for recommendation in result.recommendations[:3])

    return "\n".join(lines)


def render_runtime_error(message: str, steps: list[str]) -> str:
    """Render a privacy-safe runtime failure message and local remediation steps."""

    lines = [_terminal_safe(message)]
    if steps:
        lines.append("Next steps:")
        lines.extend(f"- {_terminal_safe(step)}" for step in steps)
    return "\n".join(lines)
