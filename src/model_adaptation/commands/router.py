"""Closed lazy routes for the model-adaptation compatibility CLI."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from types import MappingProxyType
from typing import Callable, Mapping


@dataclass(frozen=True, slots=True)
class CommandRoute:
    """One literal command-to-handler import route."""

    module: str
    symbol: str


_ROUTE_ROWS = (
    ("pilot", "src.model_adaptation.commands.adaptation", "handle_pilot"),
    ("train", "src.model_adaptation.commands.adaptation", "handle_train"),
    ("convert", "src.model_adaptation.commands.adaptation", "handle_convert"),
    ("doctor", "src.model_adaptation.commands.adaptation", "handle_doctor"),
    ("phase40-preflight", "src.model_adaptation.commands.legacy_phase40", "handle_phase40_preflight"),
    ("phase40-build-source-bundle", "src.model_adaptation.commands.legacy_phase40", "handle_phase40_build_source_bundle"),
    ("phase40-build-input-bundle", "src.model_adaptation.commands.legacy_phase40", "handle_phase40_build_input_bundle"),
    ("phase40-verify-input-bundle", "src.model_adaptation.commands.legacy_phase40", "handle_phase40_verify_input_bundle"),
    ("phase40-verify-run-request", "src.model_adaptation.commands.legacy_phase40", "handle_phase40_verify_run_request"),
    ("phase40-verify-run-evidence", "src.model_adaptation.commands.legacy_phase40", "handle_phase40_verify_run_evidence"),
    ("phase40-render-graphs", "src.model_adaptation.commands.legacy_phase40", "handle_phase40_render_graphs"),
    ("phase40-validate-notebooks", "src.model_adaptation.commands.legacy_phase40", "handle_phase40_validate_notebooks"),
    ("phase40-finalize-comparison", "src.model_adaptation.commands.legacy_phase40", "handle_phase40_finalize_comparison"),
    ("phase40-freeze-scope-amendment", "src.model_adaptation.commands.legacy_phase40", "handle_phase40_freeze_scope_amendment"),
    ("phase40-verify-review-queue", "src.model_adaptation.commands.legacy_phase40", "handle_phase40_verify_review_queue"),
    ("phase40-finalize-human-review", "src.model_adaptation.commands.legacy_phase40", "handle_phase40_finalize_human_review"),
    ("phase41-prepare-evaluation", "src.model_adaptation.commands.legacy_phase41", "handle_phase41_prepare_evaluation"),
    ("phase41-verify-preauthorization", "src.model_adaptation.commands.legacy_phase41", "handle_phase41_verify_preauthorization"),
    ("phase41-authorize-evaluation", "src.model_adaptation.commands.legacy_phase41", "handle_phase41_authorize_evaluation"),
    ("phase41-run-once", "src.model_adaptation.commands.legacy_phase41", "handle_phase41_run_once"),
    ("phase41-freeze-deployment-fit-disposition", "src.model_adaptation.commands.legacy_phase41", "handle_phase41_freeze_deployment_fit_disposition"),
    ("phase41-export-evidence", "src.model_adaptation.commands.legacy_phase41", "handle_phase41_export_evidence"),
    ("phase41-verify-evidence", "src.model_adaptation.commands.legacy_phase41", "handle_phase41_verify_evidence"),
)

COMMAND_ROUTES: Mapping[str, CommandRoute] = MappingProxyType(
    {command: CommandRoute(module, symbol) for command, module, symbol in _ROUTE_ROWS}
)


def lazy_handler(command: str) -> Callable[[object], int]:
    """Resolve one allowlisted handler only when its parsed command is invoked."""

    try:
        route = COMMAND_ROUTES[command]
    except KeyError as exc:
        raise ValueError(f"unsupported model-adaptation command: {command}") from exc

    def invoke(args: object) -> int:
        module = import_module(route.module)
        handler = getattr(module, route.symbol)
        return handler(args)

    return invoke


def dispatch(command: str, args: object) -> int:
    """Dispatch one parsed literal command through the closed route table."""

    return lazy_handler(command)(args)
