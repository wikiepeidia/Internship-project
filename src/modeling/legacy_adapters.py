"""Sole lazy bridge from active training services to historical implementations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


Forwarder = Callable[..., object]


@dataclass(frozen=True, slots=True)
class LegacyQwenTrainingAdapter:
    """Forward Qwen configuration and execution without importing history eagerly."""

    config_builder: Forwarder | None = None
    runner: Forwarder | None = None

    def build_config(
        self,
        candidate_id: str,
        train_split_path: Path,
        val_split_path: Path,
        version_tag: str,
        output_root: Path,
        *,
        adaptation_mode: object,
        selection: object | None = None,
        registry_path: Path | None = None,
        **options: object,
    ) -> object:
        implementation = self.config_builder
        if implementation is None:
            from src.model_adaptation.training import build_training_config

            implementation = build_training_config
        return implementation(
            candidate_id,
            train_split_path,
            val_split_path,
            version_tag,
            output_root,
            adaptation_mode=adaptation_mode,
            selection=selection,
            registry_path=registry_path,
            **options,
        )

    def train(
        self,
        config: object,
        *,
        data_contract: object,
        selection: object | None = None,
    ) -> object:
        implementation = self.runner
        if implementation is None:
            from src.model_adaptation.training import run_training

            implementation = run_training
        return implementation(
            config,
            data_contract=data_contract,
            selection=selection,
        )


@dataclass(frozen=True, slots=True)
class LegacyPhoBertTrainingAdapter:
    """Forward PhoBERT configuration and execution through fixed lazy imports."""

    config_factory: Forwarder | None = None
    runner: Forwarder | None = None

    def build_config(self, **options: object) -> object:
        implementation = self.config_factory
        if implementation is None:
            from src.model_adaptation.phobert_training import PhoBertTrainingConfig

            implementation = PhoBertTrainingConfig
        return implementation(**options)

    def train(
        self,
        config: object,
        data_contract: object,
        *,
        dependencies: object | None = None,
        requested_control_template: object | None = None,
    ) -> object:
        implementation = self.runner
        if implementation is None:
            from src.model_adaptation.phobert_training import run_phobert_training

            implementation = run_phobert_training
        return implementation(
            config,
            data_contract,
            dependencies=dependencies,
            requested_control_template=requested_control_template,
        )
