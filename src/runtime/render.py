"""Terminal rendering for phishing-risk analysis results and runtime errors."""

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


def render_analysis_result(result: AnalysisResult) -> str:
    """Render a short human-readable result with up to three quoted cues."""

    if not result.top_cues and not result.threat_labels and not result.recommendations:
        return result.summary

    lines = [result.summary]

    if result.threat_labels or result.recommendations:
        lines.append(f"Risk tier: {_RISK_TIER_DISPLAY[result.risk_tier]}")

    if result.threat_labels:
        label_text = ", ".join(_THREAT_LABEL_DISPLAY.get(label, label.replace("_", " ").title()) for label in result.threat_labels)
        lines.append(f"Threat labels: {label_text}")

    if result.top_cues:
        if result.threat_labels or result.recommendations:
            lines.append("Grounded cues:")
            lines.extend(f'- "{cue.span}" - {cue.reason}' for cue in result.top_cues[:3])
        else:
            lines.extend(f'"{cue.span}" - {cue.reason}' for cue in result.top_cues[:3])

    if result.recommendations:
        lines.append("Next steps:")
        lines.extend(f"- {recommendation}" for recommendation in result.recommendations[:3])

    return "\n".join(lines)


def render_runtime_error(message: str, steps: list[str]) -> str:
    """Render a privacy-safe runtime failure message and local remediation steps."""

    lines = [message]
    if steps:
        lines.append("Next steps:")
        lines.extend(f"- {step}" for step in steps)
    return "\n".join(lines)
