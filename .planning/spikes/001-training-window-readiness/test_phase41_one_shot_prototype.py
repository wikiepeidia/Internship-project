"""Synthetic-only tests for the Phase 41 one-shot spike."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest


MODULE_PATH = Path(__file__).with_name("phase41_one_shot_prototype.py")
SPEC = importlib.util.spec_from_file_location("phase41_one_shot_prototype", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
prototype = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = prototype
SPEC.loader.exec_module(prototype)


LABELS = prototype.LABEL_ORDER
FIXED_TIME = "2026-08-25T12:00:00Z"


def _record(label: str, index: int) -> dict[str, object]:
    return {
        "text": f"Synthetic held-out fixture message {index} for {label}.",
        "label": label,
        "risk_tier": "benign" if label == "benign" else "high-risk",
        "suspicious_spans": [] if label == "benign" else ["fixture"],
        "xai_explanation": "Synthetic fixture explanation.",
        "source": "unit-test-fixture",
        "seed_id": f"fixture-seed-{index}",
    }


def _payload(labels: tuple[str, ...]) -> bytes:
    return b"".join(
        (
            json.dumps(
                _record(label, index),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        for index, label in enumerate(labels)
    )


def _models() -> tuple[object, object]:
    return (
        prototype.ModelIdentity(
            role="qwen",
            run_id="fixture-qwen-qlora",
            model_family="qwen",
            adaptation_mode="qlora",
            artifact_sha256="1" * 64,
            selected_checkpoint_identity="adapter-state-sha256:" + "2" * 64,
        ),
        prototype.ModelIdentity(
            role="phobert",
            run_id="fixture-phobert",
            model_family="phobert",
            adaptation_mode="classification_head",
            artifact_sha256="3" * 64,
            selected_checkpoint_identity="model-state-sha256:" + "4" * 64,
        ),
    )


def _counts(labels: tuple[str, ...]) -> dict[str, int]:
    return {label: labels.count(label) for label in LABELS}


def _prepare_and_authorize(
    root: Path,
    split: Path,
    payload: bytes,
    labels: tuple[str, ...],
    *,
    expected_sha256: str | None = None,
    expected_records: int | None = None,
    expected_counts: dict[str, int] | None = None,
) -> None:
    prototype.prepare_evaluation(
        root,
        reserved_split_path=split,
        expected_records=len(labels) if expected_records is None else expected_records,
        expected_bytes=len(payload),
        expected_sha256=expected_sha256 or hashlib.sha256(payload).hexdigest(),
        expected_label_counts=expected_counts or _counts(labels),
        models=_models(),
        prepared_at_utc=FIXED_TIME,
    )
    prototype.authorize_evaluation(
        root,
        operator_id="fixture-operator",
        statement=prototype.EXPLICIT_AUTHORIZATION_STATEMENT,
        authorized_at_utc=FIXED_TIME,
    )


def _predict(states: tuple[str, ...], snapshot: object) -> tuple[object, ...]:
    return tuple(
        prototype.Prediction(
            row_id=row.row_id,
            predicted_state=state,
            raw_output=json.dumps({"label": state}) if state != "invalid_output" else "not-json",
            parser_error="strict_parse_failure" if state == "invalid_output" else None,
        )
        for row, state in zip(snapshot.rows, states, strict=True)
    )


class OneShotPrototypeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="phase41-spike-")
        self.addCleanup(self.temporary.cleanup)
        original_registry = prototype._CANONICAL_CLAIM_REGISTRY_ROOT
        prototype._CANONICAL_CLAIM_REGISTRY_ROOT = (
            Path(self.temporary.name) / "canonical-claim-registry"
        )
        self.addCleanup(
            setattr,
            prototype,
            "_CANONICAL_CLAIM_REGISTRY_ROOT",
            original_registry,
        )
        self.root = Path(self.temporary.name) / "evidence"
        self.split = Path(self.temporary.name) / "synthetic-held-out.jsonl"
        self.labels = (
            "bank_impersonation",
            "bank_impersonation",
            "zalo_social_engineering",
            "zalo_social_engineering",
            "task_scam",
            "task_scam",
            "benign",
            "benign",
        )
        self.payload = _payload(self.labels)
        self.split.write_bytes(self.payload)

    def _opener(self, calls: list[Path]):
        def open_once(path: Path):
            calls.append(path)
            return path.open("rb")

        return open_once

    def _run(self, calls: list[Path], seen: list[int] | None = None):
        qwen_states = (
            "bank_impersonation",
            "benign",
            "zalo_social_engineering",
            "invalid_output",
            "task_scam",
            "task_scam",
            "benign",
            "bank_impersonation",
        )
        phobert_states = (
            "bank_impersonation",
            "bank_impersonation",
            "zalo_social_engineering",
            "zalo_social_engineering",
            "task_scam",
            "benign",
            "benign",
            "benign",
        )

        def qwen(snapshot):
            if seen is not None:
                seen.append(id(snapshot))
            self.assertFalse(hasattr(snapshot, "split_sha256"))
            self.assertTrue(all(not hasattr(row, "source_row_sha256") for row in snapshot.rows))
            return _predict(qwen_states, snapshot)

        def phobert(snapshot):
            if seen is not None:
                seen.append(id(snapshot))
            return _predict(phobert_states, snapshot)

        return prototype.run_once(
            self.root,
            opener=self._opener(calls),
            qwen_predictor=qwen,
            phobert_predictor=phobert,
            clock=lambda: FIXED_TIME,
        )

    def test_prepare_and_explicit_authorization_make_zero_opener_calls(self):
        calls: list[Path] = []
        _prepare_and_authorize(self.root, self.split, self.payload, self.labels)

        self.assertEqual(calls, [])
        prepared = json.loads((self.root / prototype.PREPARED_NAME).read_text(encoding="utf-8"))
        authorization = json.loads(
            (self.root / prototype.AUTHORIZATION_NAME).read_text(encoding="utf-8")
        )
        self.assertEqual(prepared["state"], "prepared")
        self.assertEqual(authorization["state"], "explicitly_authorized")
        self.assertEqual(authorization["authorization_method"], "explicit_local_attestation")

    def test_success_uses_exactly_one_opener_and_one_shared_immutable_snapshot(self):
        _prepare_and_authorize(self.root, self.split, self.payload, self.labels)
        calls: list[Path] = []
        seen: list[int] = []

        result = self._run(calls, seen)

        self.assertEqual(calls, [self.split])
        self.assertEqual(len(seen), 2)
        self.assertEqual(seen[0], seen[1])
        self.assertEqual(result["status"], "completed")
        terminal = json.loads((self.root / prototype.TERMINAL_NAME).read_text(encoding="utf-8"))
        self.assertEqual(terminal["status"], "completed")
        self.assertFalse(terminal["rerun_permitted"])
        for artifact_name in (
            prototype.QWEN_PREDICTIONS_NAME,
            prototype.PHOBERT_PREDICTIONS_NAME,
        ):
            artifact = (self.root / artifact_name).read_text(encoding="utf-8")
            self.assertNotIn('"raw_output":', artifact)
            self.assertNotIn("Synthetic held-out fixture message", artifact)
            self.assertIn('"raw_output_sha256":', artifact)
        with self.assertRaises(prototype.AlreadySpentError):
            self._run(calls)
        self.assertEqual(calls, [self.split])

    def test_preexisting_and_concurrent_claims_block_without_a_second_open(self):
        # Preexisting claim.
        first_root = self.root / "preexisting"
        _prepare_and_authorize(first_root, self.split, self.payload, self.labels)
        identity = prototype.SplitIdentity(
            path=str(self.split),
            records=len(self.labels),
            bytes=len(self.payload),
            sha256=hashlib.sha256(self.payload).hexdigest(),
            label_counts=tuple((label, _counts(self.labels)[label]) for label in LABELS),
        )
        preexisting_claim = prototype._global_claim_path(identity)
        preexisting_claim.parent.mkdir(parents=True, exist_ok=True)
        preexisting_claim.write_text("already spent", encoding="utf-8")
        forbidden_calls: list[Path] = []
        with self.assertRaises(prototype.AlreadySpentError):
            prototype.run_once(
                first_root,
                opener=self._opener(forbidden_calls),
                qwen_predictor=lambda snapshot: (),
                phobert_predictor=lambda snapshot: (),
                clock=lambda: FIXED_TIME,
            )
        self.assertEqual(forbidden_calls, [])

        # Concurrent claim: hold the first attempt inside its sole opener.
        second_root = self.root / "concurrent"
        concurrent_labels = tuple(reversed(self.labels))
        concurrent_payload = _payload(concurrent_labels)
        concurrent_split = Path(self.temporary.name) / "concurrent-held-out.jsonl"
        concurrent_split.write_bytes(concurrent_payload)
        _prepare_and_authorize(
            second_root,
            concurrent_split,
            concurrent_payload,
            concurrent_labels,
        )
        entered = threading.Event()
        release = threading.Event()
        first_calls: list[Path] = []
        first_error: list[BaseException] = []

        def blocking_opener(path: Path):
            first_calls.append(path)
            entered.set()
            release.wait(timeout=5)
            return path.open("rb")

        def all_gold(snapshot):
            return _predict(concurrent_labels, snapshot)

        def first_attempt():
            try:
                prototype.run_once(
                    second_root,
                    opener=blocking_opener,
                    qwen_predictor=all_gold,
                    phobert_predictor=all_gold,
                    clock=lambda: FIXED_TIME,
                )
            except BaseException as exc:  # pragma: no cover - asserted after join
                first_error.append(exc)

        worker = threading.Thread(target=first_attempt)
        worker.start()
        self.assertTrue(entered.wait(timeout=5))
        second_calls: list[Path] = []
        with self.assertRaises(prototype.AlreadySpentError):
            prototype.run_once(
                second_root,
                opener=self._opener(second_calls),
                qwen_predictor=all_gold,
                phobert_predictor=all_gold,
                clock=lambda: FIXED_TIME,
            )
        release.set()
        worker.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(first_error, [])
        self.assertEqual(first_calls, [concurrent_split])
        self.assertEqual(second_calls, [])

    def test_global_claim_blocks_replay_from_a_different_output_root(self):
        first_root = self.root / "first-output"
        second_root = self.root / "copied-output"
        copied_split = Path(self.temporary.name) / "copied-held-out.jsonl"
        copied_split.write_bytes(self.payload)
        _prepare_and_authorize(first_root, self.split, self.payload, self.labels)
        _prepare_and_authorize(second_root, copied_split, self.payload, self.labels)
        first_calls: list[Path] = []
        second_calls: list[Path] = []

        def all_gold(snapshot):
            return _predict(self.labels, snapshot)

        prototype.run_once(
            first_root,
            opener=self._opener(first_calls),
            qwen_predictor=all_gold,
            phobert_predictor=all_gold,
            clock=lambda: FIXED_TIME,
        )
        with self.assertRaises(prototype.AlreadySpentError):
            prototype.run_once(
                second_root,
                opener=self._opener(second_calls),
                qwen_predictor=all_gold,
                phobert_predictor=all_gold,
                clock=lambda: FIXED_TIME,
            )

        self.assertEqual(first_calls, [self.split])
        self.assertEqual(second_calls, [])

    def _rewrite_result_and_terminal(self, mutate) -> None:
        result_path = self.root / prototype.RESULTS_NAME
        report_path = self.root / prototype.REPORT_NAME
        terminal_path = self.root / prototype.TERMINAL_NAME
        result = json.loads(result_path.read_text(encoding="utf-8"))
        mutate(result)
        result_bytes = prototype._canonical_json_bytes(result)
        report_bytes = prototype._render_report(result)
        result_path.write_bytes(result_bytes)
        report_path.write_bytes(report_bytes)
        terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
        terminal["results_sha256"] = hashlib.sha256(result_bytes).hexdigest()
        terminal["report_sha256"] = hashlib.sha256(report_bytes).hexdigest()
        terminal_path.write_bytes(prototype._canonical_json_bytes(terminal))

    def _rewrite_prediction_gold_and_reseal(self) -> None:
        result_path = self.root / prototype.RESULTS_NAME
        report_path = self.root / prototype.REPORT_NAME
        terminal_path = self.root / prototype.TERMINAL_NAME
        result = json.loads(result_path.read_text(encoding="utf-8"))
        prediction_payloads = []
        metrics = []
        for artifact_name in (
            prototype.QWEN_PREDICTIONS_NAME,
            prototype.PHOBERT_PREDICTIONS_NAME,
        ):
            artifact_path = self.root / artifact_name
            rows = [
                json.loads(line)
                for line in artifact_path.read_text(encoding="utf-8").splitlines()
            ]
            rows[0]["gold_label"] = "benign"
            payload = b"".join(prototype._canonical_json_bytes(row) for row in rows)
            artifact_path.write_bytes(payload)
            prediction_payloads.append(payload)
            predictions = tuple(
                prototype.Prediction(
                    row_id=row["row_id"],
                    predicted_state=row["predicted_state"],
                    raw_output="",
                    parser_error=row["parser_error"],
                )
                for row in rows
            )
            metrics.append(
                prototype.compute_metrics(
                    tuple(row["gold_label"] for row in rows),
                    predictions,
                )
            )
        for model, metric, payload in zip(
            result["models"], metrics, prediction_payloads, strict=True
        ):
            model["metrics"] = metric
            model["predictions_sha256"] = hashlib.sha256(payload).hexdigest()
        result["comparison_statements"] = list(
            prototype.comparison_statements(metrics[0], metrics[1])
        )
        result_bytes = prototype._canonical_json_bytes(result)
        report_bytes = prototype._render_report(result)
        result_path.write_bytes(result_bytes)
        report_path.write_bytes(report_bytes)
        terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
        terminal["qwen_predictions_sha256"] = hashlib.sha256(
            prediction_payloads[0]
        ).hexdigest()
        terminal["phobert_predictions_sha256"] = hashlib.sha256(
            prediction_payloads[1]
        ).hexdigest()
        terminal["results_sha256"] = hashlib.sha256(result_bytes).hexdigest()
        terminal["report_sha256"] = hashlib.sha256(report_bytes).hexdigest()
        terminal_path.write_bytes(prototype._canonical_json_bytes(terminal))

    def test_verify_only_rejects_added_winner_even_when_hashes_are_resealed(self):
        _prepare_and_authorize(self.root, self.split, self.payload, self.labels)
        self._run([])
        self._rewrite_result_and_terminal(lambda result: result.__setitem__("winner", "qwen"))

        with self.assertRaisesRegex(prototype.ContractError, "authority fields drifted"):
            prototype.verify_only(self.root)

    def test_verify_only_rejects_terminal_policy_drift(self):
        _prepare_and_authorize(self.root, self.split, self.payload, self.labels)
        self._run([])

        def permit_rerun(result):
            result["terminal_policy"]["rerun_permitted"] = True

        self._rewrite_result_and_terminal(permit_rerun)
        with self.assertRaisesRegex(prototype.ContractError, "terminal result policy drifted"):
            prototype.verify_only(self.root)

    def test_verify_only_rejects_held_out_identity_drift(self):
        _prepare_and_authorize(self.root, self.split, self.payload, self.labels)
        self._run([])

        def change_held_out(result):
            result["held_out"]["records"] += 1

        self._rewrite_result_and_terminal(change_held_out)
        with self.assertRaisesRegex(prototype.ContractError, "held-out identity drifted"):
            prototype.verify_only(self.root)

    def test_verify_only_rejects_resealed_gold_support_drift(self):
        _prepare_and_authorize(self.root, self.split, self.payload, self.labels)
        self._run([])
        self._rewrite_prediction_gold_and_reseal()

        with self.assertRaisesRegex(prototype.ContractError, "gold-label support differs"):
            prototype.verify_only(self.root)

    def test_verify_only_rejects_terminal_schema_and_rerun_drift(self):
        _prepare_and_authorize(self.root, self.split, self.payload, self.labels)
        self._run([])
        terminal_path = self.root / prototype.TERMINAL_NAME
        terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
        terminal["schema_version"] = "phase41-terminal-v0"
        terminal["rerun_permitted"] = True
        terminal_path.write_bytes(prototype._canonical_json_bytes(terminal))

        with self.assertRaisesRegex(prototype.ContractError, "not terminal-complete"):
            prototype.verify_only(self.root)

    def test_post_claim_failure_is_terminal_and_remains_spent(self):
        _prepare_and_authorize(self.root, self.split, self.payload, self.labels)
        calls: list[Path] = []

        def failing_predictor(snapshot):
            raise RuntimeError("synthetic predictor failure")

        with self.assertRaisesRegex(RuntimeError, "synthetic predictor failure"):
            prototype.run_once(
                self.root,
                opener=self._opener(calls),
                qwen_predictor=failing_predictor,
                phobert_predictor=lambda snapshot: (),
                clock=lambda: FIXED_TIME,
            )
        self.assertEqual(calls, [self.split])
        terminal = json.loads((self.root / prototype.TERMINAL_NAME).read_text(encoding="utf-8"))
        self.assertEqual(terminal["status"], "spent_failed")
        self.assertEqual(terminal["failure_stage"], "qwen_prediction")
        self.assertFalse(terminal["rerun_permitted"])

        retry_calls: list[Path] = []
        with self.assertRaises(prototype.AlreadySpentError):
            prototype.run_once(
                self.root,
                opener=self._opener(retry_calls),
                qwen_predictor=lambda snapshot: (),
                phobert_predictor=lambda snapshot: (),
                clock=lambda: FIXED_TIME,
            )
        self.assertEqual(retry_calls, [])

    def test_malformed_hash_and_count_failures_each_open_once_and_spend(self):
        cases: list[tuple[str, bytes, str | None, int | None, dict[str, int] | None]] = []
        malformed = b'{"text":"broken"\n'
        cases.append(("malformed", malformed, None, len(LABELS), _counts(LABELS)))
        cases.append(("hash", self.payload, "f" * 64, None, None))
        wrong_counts = _counts(self.labels)
        wrong_counts["benign"] += 1
        cases.append(("count", self.payload, None, len(self.labels) + 1, wrong_counts))

        for name, payload, expected_sha, expected_records, expected_counts in cases:
            with self.subTest(name=name):
                root = self.root / name
                split = Path(self.temporary.name) / f"{name}-fixture.jsonl"
                split.write_bytes(payload)
                labels = LABELS if name == "malformed" else self.labels
                _prepare_and_authorize(
                    root,
                    split,
                    payload,
                    labels,
                    expected_sha256=expected_sha,
                    expected_records=expected_records,
                    expected_counts=expected_counts,
                )
                calls: list[Path] = []
                with self.assertRaises(prototype.ContractError):
                    prototype.run_once(
                        root,
                        opener=self._opener(calls),
                        qwen_predictor=lambda snapshot: (),
                        phobert_predictor=lambda snapshot: (),
                        clock=lambda: FIXED_TIME,
                    )
                self.assertEqual(calls, [split])
                terminal = json.loads(
                    (root / prototype.TERMINAL_NAME).read_text(encoding="utf-8")
                )
                self.assertEqual(terminal["status"], "spent_failed")
                self.assertTrue((root / prototype.CLAIM_NAME).is_file())

    def test_golden_metrics_and_plain_phobert_qwen_tie_wording(self):
        _prepare_and_authorize(self.root, self.split, self.payload, self.labels)
        result = self._run([])
        qwen = result["models"][0]["metrics"]
        phobert = result["models"][1]["metrics"]

        self.assertAlmostEqual(qwen["macro_f1"], 2 / 3)
        self.assertAlmostEqual(qwen["weighted_f1"], 2 / 3)
        self.assertAlmostEqual(qwen["accuracy"], 5 / 8)
        self.assertEqual(qwen["invalid_output_count"], 1)
        self.assertEqual(qwen["risky_to_benign_count"], 1)
        self.assertEqual(qwen["risky_to_invalid_count"], 1)
        self.assertEqual(
            qwen["confusion_matrix"],
            [
                [1, 0, 0, 1, 0],
                [0, 1, 0, 0, 1],
                [0, 0, 2, 0, 0],
                [1, 0, 0, 1, 0],
            ],
        )
        self.assertAlmostEqual(phobert["macro_f1"], 13 / 15)
        self.assertAlmostEqual(phobert["weighted_f1"], 13 / 15)
        self.assertAlmostEqual(phobert["accuracy"], 7 / 8)
        statements = result["comparison_statements"]
        self.assertEqual(
            statements,
            [
                "PhoBERT higher on: macro_f1, weighted_f1, accuracy, bank_impersonation.precision, bank_impersonation.recall, bank_impersonation.f1, zalo_social_engineering.recall, zalo_social_engineering.f1, benign.precision, benign.recall, benign.f1, invalid_output_count(lower_is_better), risky_to_invalid_count(lower_is_better).",
                "Qwen higher on: task_scam.recall, task_scam.f1.",
                "Ties: zalo_social_engineering.precision, task_scam.precision, risky_to_benign_count(lower_is_better).",
            ],
        )
        report = (self.root / prototype.REPORT_NAME).read_text(encoding="utf-8")
        confusion_header = (
            "| gold label / predicted state | bank_impersonation | "
            "zalo_social_engineering | task_scam | benign | invalid_output |"
        )
        qwen_confusion = "\n".join(
            [
                "### Confusion matrix",
                "",
                "Rows are gold labels; columns are predicted states.",
                "",
                confusion_header,
                "|---|---:|---:|---:|---:|---:|",
                "| bank_impersonation | 1 | 0 | 0 | 1 | 0 |",
                "| zalo_social_engineering | 0 | 1 | 0 | 0 | 1 |",
                "| task_scam | 0 | 0 | 2 | 0 | 0 |",
                "| benign | 1 | 0 | 0 | 1 | 0 |",
            ]
        )
        phobert_confusion = "\n".join(
            [
                "### Confusion matrix",
                "",
                "Rows are gold labels; columns are predicted states.",
                "",
                confusion_header,
                "|---|---:|---:|---:|---:|---:|",
                "| bank_impersonation | 2 | 0 | 0 | 0 | 0 |",
                "| zalo_social_engineering | 0 | 2 | 0 | 0 | 0 |",
                "| task_scam | 0 | 0 | 1 | 1 | 0 |",
                "| benign | 0 | 0 | 0 | 2 | 0 |",
            ]
        )
        self.assertEqual(report.count(confusion_header), 2)
        self.assertIn(qwen_confusion, report)
        self.assertIn(phobert_confusion, report)
        self.assertLess(report.index(qwen_confusion), report.index("## phobert"))
        self.assertGreater(report.index(phobert_confusion), report.index("## phobert"))
        serialized = json.dumps(result, sort_keys=True).casefold()
        self.assertNotIn('"winner"', serialized)
        self.assertNotIn('"model_selection"', serialized)
        self.assertNotIn("retrain", serialized)

    def test_verify_only_is_byte_stable_and_needs_no_opener_or_predictor(self):
        _prepare_and_authorize(self.root, self.split, self.payload, self.labels)
        self._run([])
        before = {
            path.name: path.read_bytes()
            for path in sorted(self.root.iterdir())
            if path.is_file()
        }

        first = prototype.verify_only(self.root)
        second = prototype.verify_only(self.root)
        after = {
            path.name: path.read_bytes()
            for path in sorted(self.root.iterdir())
            if path.is_file()
        }

        self.assertEqual(first, second)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
