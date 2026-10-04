"""Import-free ownership index for retained Phase 41 implementations."""

OWNED_MODULES: tuple[str, ...] = (
    "src.model_adaptation.phase41_evaluation",
    "src.model_adaptation.phase41_protocols",
)

__all__ = ["OWNED_MODULES"]
