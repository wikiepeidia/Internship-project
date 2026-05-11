"""Local heuristic analyzer for the Phase 2 runtime."""

from dataclasses import dataclass, field

from src.runtime.analyzers.rules import CueRule, build_default_rules
from src.runtime.contracts import AnalysisRequest, AnalysisResult, DoctorCheck, DoctorStatus, SuspiciousCue


HIGH_RISK_THRESHOLD = 7
SUSPICIOUS_THRESHOLD = 3


@dataclass
class HeuristicAnalyzer:
    """Rule-based local analyzer used before the trained runtime exists."""

    rules: list[CueRule] = field(default_factory=build_default_rules)
    backend_name: str = "heuristic"

    def doctor(self) -> DoctorStatus:
        checks = [
            DoctorCheck(
                name="heuristic-rules",
                passed=bool(self.rules),
                detail="Weighted local heuristic rules are loaded.",
                remediation_command=None if self.rules else "python -m pip install -e .[dev]",
            )
        ]
        ready = all(check.passed for check in checks)
        steps = [] if ready else ["python -m pip install -e .[dev]", "python -m src.runtime.cli doctor"]
        return DoctorStatus(
            ready=ready,
            backend_name=self.backend_name,
            checks=checks,
            setup_steps=steps,
        )

    def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        normalized_text = request.text
        shadow_text = normalized_text.casefold()

        ranked_matches: list[tuple[int, int, SuspiciousCue, str | None]] = []
        seen: set[tuple[str, str]] = set()

        for rule in self.rules:
            for match in rule.pattern.finditer(shadow_text):
                span = normalized_text[match.start() : match.end()]
                if not span.strip():
                    continue

                dedupe_key = (span, rule.reason)
                if dedupe_key in seen:
                    continue

                seen.add(dedupe_key)
                ranked_matches.append(
                    (
                        rule.weight,
                        match.start(),
                        SuspiciousCue(span=span, reason=rule.reason, cue_type=rule.cue_type),
                        rule.tier_override,
                    )
                )

        ranked_matches.sort(key=lambda item: (-item[0], item[1]))

        score = sum(weight for weight, _, _, _ in ranked_matches)
        tier_overrides = [tier for _, _, _, tier in ranked_matches if tier is not None]

        if "high-risk" in tier_overrides or score >= HIGH_RISK_THRESHOLD:
            risk_tier = "high-risk"
        elif score >= SUSPICIOUS_THRESHOLD:
            risk_tier = "suspicious"
        else:
            risk_tier = "benign"

        if risk_tier == "high-risk":
            summary = "Provisional high-risk result from local heuristic analysis."
        elif risk_tier == "suspicious":
            summary = "Provisional suspicious result from local heuristic analysis."
        else:
            summary = "Provisional benign result from local heuristic analysis."

        return AnalysisResult(
            risk_tier=risk_tier,
            summary=summary,
            top_cues=[cue for _, _, cue, _ in ranked_matches[:3]],
            backend_name=self.backend_name,
            normalized_text=normalized_text,
        )