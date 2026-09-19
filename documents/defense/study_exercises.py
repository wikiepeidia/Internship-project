"""Small hands-on exercises for the 7-day study guide.

Run one at a time:  python documents/defense/study_exercises.py 1
Run all of them:    python documents/defense/study_exercises.py

Nothing here loads a model, calls an API, or opens a data file except the two
training config files in exercise 5, which are only read.
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

# The Windows-level MODEL_* variables point at the old D: layout and make the
# settings refuse to load, so point them at the local copy for this process.
os.environ["MODEL_STORAGE_ROOT"] = str(ROOT / "data" / "runtime")
os.environ["MODEL_ARTIFACT_ROOT"] = str(ROOT / "data" / "runtime" / "models")
os.environ["MODEL_REGISTRY_PATH"] = str(ROOT / "data" / "runtime" / "manifests" / "model-registry.json")

GOOD_RECORD = dict(
    text="Vietcombank: tai khoan cua ban bi khoa, bam vao http://vcb-fake.test de mo khoa ngay.",
    label="bank_impersonation",
    risk_tier="high-risk",
    suspicious_spans=["http://vcb-fake.test"],
    xai_explanation="Tin nhan gia mao ngan hang va yeu cau bam vao lien ket la.",
    source="synthetic_claude",
    seed_id="seed_demo000001",
)


def exercise_1_record_rules():
    """Day 1: what a valid dataset row must look like."""
    from pydantic import ValidationError

    from src.data_pipeline.core.records import DatasetRecord

    print("A good row is accepted, label =", DatasetRecord.model_validate(GOOD_RECORD).label)
    try:
        DatasetRecord.model_validate(dict(GOOD_RECORD, suspicious_spans=["http://not-in-the-text.test"]))
    except ValidationError as error:
        print("A span that is not copied from the text is rejected:", error.errors()[0]["msg"])
    try:
        DatasetRecord.model_validate(dict(GOOD_RECORD, label="phishing"))
    except ValidationError as error:
        print("A label outside the four classes is rejected:", error.errors()[0]["type"])


def exercise_2_cleaning():
    """Day 4: text clean-up and near-duplicate removal."""
    from src.data_pipeline.core.text import lexical_dedup, normalize_text

    print("Extra spaces and line breaks collapse:", repr(normalize_text("  Xin   chào  \n bạn  ")))
    rows = [
        {"text": "Vietcombank: tai khoan cua ban bi khoa, bam vao link de mo khoa ngay."},
        {"text": "Vietcombank: tai khoan cua ban bi khoa, bam vao link de mo khoa ngay!"},
        {"text": "Ban duoc tuyen lam cong tac vien, nap tien 500k de nhan nhiem vu."},
    ]
    print("3 rows, 2 of them almost identical ->", len(lexical_dedup(rows, 0.95)), "rows kept")


def _fake_row(label, seed_id, number):
    row = dict(GOOD_RECORD)
    row["label"] = label
    row["risk_tier"] = "benign" if label == "benign" else "high-risk"
    row["seed_id"] = seed_id
    row["text"] = f"Vietcombank: tai khoan cua ban bi khoa so {number}, bam vao http://vcb-fake.test de mo khoa."
    return row


def exercise_3_split():
    """Day 4: whole scenarios go to one split, never spread across splits."""
    from src.data_pipeline.core.splits import split_dataset

    rows, number = [], 0
    for label in ("bank_impersonation", "benign"):
        for scenario in range(10):
            for variant in range(4):
                number += 1
                rows.append(_fake_row(label, f"seed_{label[:4]}_{scenario:02d}", number))
    result = split_dataset(rows)
    print("Split sizes:", {name: len(part) for name, part in result.items()})
    where = {}
    for name, part in result.items():
        for row in part:
            where.setdefault(row["seed_id"], set()).add(name)
    print("Is any scenario in more than one split?", any(len(names) > 1 for names in where.values()))

    rows.append(_fake_row("benign", "seed_bank_00", 999))
    try:
        split_dataset(rows)
    except ValueError as error:
        print("One scenario carrying two labels is refused:", error)


def exercise_4_rules_after_the_model():
    """Day 7: the app is the model PLUS hand-written rules. Fake model answers, no model loaded."""
    from src.runtime.analyzers.local_model import build_analysis_result
    from src.runtime.contracts import AnalysisRequest

    def run(title, text, model_says):
        payload = {
            "risk_tier": model_says,
            "threat_labels": ["benign"] if model_says == "benign" else ["bank_impersonation"],
            "decision_summary": "fake model answer for the exercise",
            "suspicious_spans": [],
        }
        result = build_analysis_result(payload, AnalysisRequest(text=text, channel="sms"), "exercise")
        print(f"{title}\n    model said {model_says!r} -> app says {result.risk_tier!r}, labels {result.threat_labels}")

    run(
        "A) The model misses a scam that has a bank name and a link",
        "Vietcombank: tai khoan cua ban bi khoa. Dang nhap http://vcb-fake.test de xac minh ngay.",
        "benign",
    )
    run(
        "B) A plain OTP notice that the model over-reacts to",
        "VPBank Smart OTP: Ma xac thuc cua ban la 847291. Ma co hieu luc 90 giay. Khong chia se ma nay voi bat ky ai.",
        "suspicious",
    )
    run(
        "C) The Input 3 message from the report (it mentions Internet Banking)",
        "VPBank Smart OTP: Mã xác thực của bạn là 847291. Mã này có hiệu lực trong 90 giây để xác nhận đăng nhập "
        "Internet Banking. Tuyệt đối KHÔNG chia sẻ mã này với bất kỳ ai, kể cả nhân viên ngân hàng.",
        "suspicious",
    )
    print("\nC stays 'suspicious' because the words 'Internet Banking' count as a credential cue, which blocks the")
    print("OTP-notice rule. That is why Input 3 is still a false alarm, and why one unit test for it fails.")


def exercise_5_training_settings():
    """Day 5: the real training settings, read from the saved config files."""
    qwen = json.loads((ROOT / "data/models/phase40/matched-qwen-config.json").read_text(encoding="utf-8"))
    phobert = json.loads((ROOT / "data/models/phase40/phobert-config.json").read_text(encoding="utf-8"))
    q = qwen["qlora"]
    p = phobert["control"]
    rows = [
        ("base model", q["model_id"], p["model_id"]),
        ("how it learns", "LoRA adapters on a 4-bit (NF4) base", "every weight + a 4-way classifier head"),
        ("LoRA rank / alpha / dropout", f'{q["lora_rank"]} / {q["lora_alpha"]} / {q["lora_dropout"]}', "-"),
        ("learning rate", q["optimizer"]["learning_rate"], p["optimizer"]["learning_rate"]),
        ("batch (per step x accumulation)", f'{q["per_device_train_batch_size"]} x {q["gradient_accumulation_steps"]}', f'{p["per_device_train_batch_size"]} x {p["gradient_accumulation_steps"]}'),
        ("epochs", q["num_train_epochs"], p["num_train_epochs"]),
        ("total steps", q["max_optimizer_steps"], p["max_optimizer_steps"]),
        ("longest input (tokens)", q["max_sequence_length"], p["max_sequence_length"]),
        ("seed", q["seed"], p["seed"]),
        ("checkpoint every N steps", q["cadence"]["save_steps"], p["cadence"]["save_steps"]),
    ]
    print(f'{"":34s}{"Qwen QLoRA":42s}PhoBERT')
    for name, left, right in rows:
        print(f"{name:34s}{str(left):42s}{right}")
    print("label order (also PhoBERT's output positions):", q["label_order"])
    proof = q["quantization_proof"]
    print(
        "QLoRA proof kept with the run:",
        f'{proof["linear4bit_modules"]} layers really were 4-bit, only',
        f'{proof["adapter_trainable_count"]} adapter tensors trainable, base frozen = {proof["base_weights_frozen"]}',
    )


EXERCISES = {
    "1": exercise_1_record_rules,
    "2": exercise_2_cleaning,
    "3": exercise_3_split,
    "4": exercise_4_rules_after_the_model,
    "5": exercise_5_training_settings,
}


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    chosen = sys.argv[1:] or list(EXERCISES)
    for key in chosen:
        print(f"\n=== Exercise {key}: {EXERCISES[key].__doc__.splitlines()[0]}")
        EXERCISES[key]()
