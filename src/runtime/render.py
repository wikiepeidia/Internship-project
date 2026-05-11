"""Terminal-friendly rendering for Phase 2 runtime results."""

from src.runtime.contracts import AnalysisResult


def render_analysis_result(result: AnalysisResult) -> str:
    """Render a short human-readable result with up to three quoted cues."""

    lines = [result.summary]
    lines.extend(f'"{cue.span}" - {cue.reason}' for cue in result.top_cues[:3])
    return "\n".join(lines)


def render_runtime_error(message: str, steps: list[str]) -> str:
    """Render a privacy-safe runtime failure message and local remediation steps."""

    lines = [message]
    if steps:
        lines.append("Next steps:")
        lines.extend(f"- {step}" for step in steps)
    return "\n".join(lines)