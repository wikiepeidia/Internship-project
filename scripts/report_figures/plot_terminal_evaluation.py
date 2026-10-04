"""Figure: confusion matrices from the frozen terminal evaluation, both models.

Source (read-only): the frozen verified-export results.md. Parsed rather than retyped,
so the figure cannot drift from the artifact.

The 220-row held-out partition, one post-freeze evaluation pass. Verified totals:
  Qwen    macro-F1 0.980493, accuracy 0.981818 -> 4 errors in 220
  PhoBERT macro-F1 0.990892, accuracy 0.990909 -> 2 errors in 220
  Both:   invalid_output_count 0, risky_to_benign_count 1

The risky->benign tie is the honest headline. PhoBERT scores higher overall, but on the
one metric that matters for a phishing detector -- a dangerous message called safe --
the two models are identical at one each. This is a single-seed descriptive result and
is not evidence of stable superiority.
"""
import re

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from vnphish_figs import (
    BASELINE, GRIDLINE, INK_MUTED, INK_PRIMARY, INK_SECONDARY, PROJECT_ROOT, SERIES,
    SURFACE, save, titles,
)

EXPORT_DIR = PROJECT_ROOT / "data/models/phase41/verified-export"
results_md = next(EXPORT_DIR.glob("*/results.md"))
text = results_md.read_text(encoding="utf-8")

SHORT = {
    "bank_impersonation": "Bank imp.",
    "zalo_social_engineering": "Zalo SE",
    "task_scam": "Task scam",
    "benign": "Benign",
    "invalid_output": "Invalid",
}
GOLD = ["bank_impersonation", "zalo_social_engineering", "task_scam", "benign"]
PRED = GOLD + ["invalid_output"]


def parse_model(block):
    """Pull macro_f1, accuracy, risky_to_benign and the confusion matrix out of one
    '## <model>' section of results.md."""
    macro = float(re.search(r"macro_f1: ([\d.]+)", block).group(1))
    acc = float(re.search(r"accuracy: ([\d.]+)", block).group(1))
    risky = int(re.search(r"risky_to_benign_count: (\d+)", block).group(1))
    invalid = int(re.search(r"invalid_output_count: (\d+)", block).group(1))
    # scope to the confusion-matrix section: the per-class metrics table above it has
    # rows with the same leading label but float cells
    cm_block = block.split("### Confusion matrix", 1)[1]
    matrix = []
    for gold in GOLD:
        row = re.search(rf"^\| {gold} \|(.+)$", cm_block, re.M).group(1)
        cells = [c.strip() for c in row.split("|") if c.strip()]
        matrix.append([int(c) for c in cells[:5]])
    return {"macro": macro, "acc": acc, "risky": risky, "invalid": invalid, "m": matrix}


sections = text.split("\n## ")
qwen = parse_model(next(s for s in sections if s.startswith("qwen")))
phobert = parse_model(next(s for s in sections if s.startswith("phobert")))
total = sum(sum(r) for r in qwen["m"])

fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.9), dpi=120)
fig.patch.set_facecolor(SURFACE)

for ax, (name, d) in zip(axes, [("Qwen3-4B (NF4 QLoRA)", qwen), ("PhoBERT", phobert)]):
    ax.set_facecolor(SURFACE)
    ax.set_xlim(-0.5, len(PRED) - 0.5)
    ax.set_ylim(len(GOLD) - 0.5, -0.5)
    ax.set_xticks(range(len(PRED)), [SHORT[p] for p in PRED], fontsize=8.5,
                  color=INK_SECONDARY, rotation=30, ha="right")
    ax.set_yticks(range(len(GOLD)), [SHORT[g] for g in GOLD], fontsize=8.5,
                  color=INK_SECONDARY)
    ax.tick_params(length=0, colors=INK_MUTED)
    for spine in ax.spines.values():
        spine.set_visible(False)

    peak = max(max(r) for r in d["m"])
    errors = 0
    for i in range(len(GOLD)):
        for j in range(len(PRED)):
            v = d["m"][i][j]
            correct = i == j
            if v == 0:
                face, edge, ink = SURFACE, GRIDLINE, "#c9c8c2"
            elif correct:
                # sequential blue, scaled by count
                face = plt.matplotlib.colors.to_hex(
                    plt.matplotlib.colors.LinearSegmentedColormap.from_list(
                        "b", ["#cde2fb", "#1c5cab"])(0.35 + 0.65 * v / peak))
                edge, ink = face, "#ffffff"
            else:
                face, edge, ink = "#eb6834", "#eb6834", "#ffffff"
                errors += v
            ax.add_patch(Rectangle((j - 0.46, i - 0.46), 0.92, 0.92, facecolor=face,
                                   edgecolor=edge, linewidth=1.0, zorder=2))
            ax.text(j, i, str(v), ha="center", va="center", fontsize=9,
                    color=ink, zorder=3)

    ax.set_title(
        f"{name}\n{errors} mistakes out of {total}",
        fontsize=9.5, color=INK_PRIMARY, loc="left", pad=9, linespacing=1.5)
    ax.set_xlabel("what the model said", color=INK_MUTED, fontsize=9)

axes[0].set_ylabel("what it really was", color=INK_MUTED, fontsize=9)

titles(
    fig,
    "Where each model got it wrong, on the 220 held-out messages",
    "One evaluation pass, seed 42  ·  neither model produced an unreadable answer  ·  "
    "orange cells are mistakes",
    y=0.975, sub_y=0.912,
)
fig.text(
    0.015, 0.028,
    f"Each model called exactly {qwen['risky']} dangerous message safe. "
    "One run each; this does not show that either model is reliably better.",
    fontsize=8.5, color=INK_MUTED, ha="left",
)
fig.subplots_adjust(left=0.115, right=0.99, top=0.70, bottom=0.235, wspace=0.30)

save(fig, "terminal_evaluation_confusion.png")
print(f"qwen  macro {qwen['macro']} acc {qwen['acc']} risky_to_benign {qwen['risky']} invalid {qwen['invalid']}")
print(f"pho   macro {phobert['macro']} acc {phobert['acc']} risky_to_benign {phobert['risky']} invalid {phobert['invalid']}")
print(f"total rows {total}")
