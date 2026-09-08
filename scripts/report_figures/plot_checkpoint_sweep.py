"""Figure: validation macro-F1 at every retained checkpoint, both models.

Sources (all read-only):
  data/models/phase40/full/<model>/checkpoints/step-*/validation-metrics.json
  data/models/phase40/full/qwen-qlora/validation-metrics.json   (the SELECTED model)

PROVENANCE NOTE, important and defensible:
The Qwen run evaluated every 50 optimizer steps, step 50 through 1245 -- 25 evaluations,
each recorded as an `evaluation` event in events.jsonl. Only 24 checkpoint DIRECTORIES
survive, because the selected step-200 checkpoint was promoted out of checkpoints/ into
adapter-or-model/. Its validation metrics live in the run-root validation-metrics.json
(macro_f1 0.9885153110318673), which comparison-report.md independently records as
selected_step=200, macro_F1=0.9885. So the step-200 point below is real and sourced --
it simply lives in a different file from the other 24.
"""
import glob
import json
import re

import matplotlib.pyplot as plt

from vnphish_figs import (
    INK_PRIMARY,
    INK_MUTED, INK_SECONDARY, PROJECT_ROOT, SERIES, SURFACE,
    save, style_axes, titles,
)


def sweep(model):
    pts = []
    pattern = str(PROJECT_ROOT / f"data/models/phase40/full/{model}/checkpoints/*/validation-metrics.json")
    for path in glob.glob(pattern):
        step = int(re.search(r"step-(\d+)-", path.replace("\\", "/")).group(1))
        pts.append((step, json.load(open(path, encoding="utf-8"))["macro_f1"]))
    return pts


qwen = sweep("qwen-qlora")
# the promoted, selected checkpoint -- absent from checkpoints/, present at the run root
selected_qwen = json.load(
    open(PROJECT_ROOT / "data/models/phase40/full/qwen-qlora/validation-metrics.json", encoding="utf-8")
)["macro_f1"]
qwen.append((200, selected_qwen))
qwen.sort()

phobert = sorted(sweep("phobert"))

PANELS = [
    # name, points, selected step, colour, last step, label position (data coords)
    ("Qwen3-4B (NF4 QLoRA adapter)", qwen, 200, SERIES[0], 1245, (300, 0.885)),
    ("PhoBERT (classification head)", phobert, 100, SERIES[1], 312, (118, 0.905)),
]

fig, axes = plt.subplots(2, 1, figsize=(8, 5.6), dpi=120)
fig.patch.set_facecolor(SURFACE)

for ax, (name, pts, sel_step, colour, last_step, label_xy) in zip(axes, PANELS):
    style_axes(ax)
    steps = [s for s, _ in pts]
    f1s = [f for _, f in pts]
    ax.plot(steps, f1s, color=colour, linewidth=1.8, marker="o", markersize=4.5,
            solid_capstyle="round", zorder=3)
    ax.set_ylim(0.76, 1.02)
    ax.set_yticks([0.80, 0.85, 0.90, 0.95, 1.00])
    ax.set_xlim(0, last_step * 1.05)
    ax.set_ylabel("validation macro-F1", color=INK_SECONDARY, fontsize=9.5)
    ax.text(0.995, 0.06, name, transform=ax.transAxes, ha="right", va="bottom",
            fontsize=9.5, color=INK_SECONDARY)

    sel_f1 = dict(pts)[sel_step]
    ax.plot([sel_step], [sel_f1], marker="o", markersize=6.5, color=INK_PRIMARY, zorder=5)
    ax.annotate(
        f"selected: step {sel_step}  (macro-F1 {sel_f1:.4f})",
        xy=(sel_step, sel_f1), xytext=label_xy, textcoords="data",
        fontsize=9, color=INK_PRIMARY, va="center", ha="left", zorder=6,
        arrowprops=dict(arrowstyle="-", color=INK_MUTED, linewidth=0.8,
                        connectionstyle="angle3,angleA=0,angleB=80"),
    )

axes[0].annotate(
    "real dip at step 150",
    xy=(150, dict(qwen)[150]), xytext=(215, 0.812),
    fontsize=8.5, color=INK_MUTED,
    arrowprops=dict(arrowstyle="-", color=INK_MUTED, linewidth=0.8,
                    connectionstyle="angle3,angleA=0,angleB=70"),
)
axes[1].set_xlabel("optimizer step", color=INK_SECONDARY, fontsize=10)

titles(
    fig,
    "Which checkpoint was kept, and why",
    "Scored on the same 219 validation messages  ·  seed 42  ·  no unreadable "
    "answers at any checkpoint",
)
fig.subplots_adjust(left=0.095, right=0.985, top=0.855, bottom=0.10, hspace=0.28)

save(fig, "checkpoint_selection_sweep.png")
print("qwen points:", len(qwen), "| phobert points:", len(phobert))
print("qwen min/max:", min(f for _, f in qwen), max(f for _, f in qwen))
print("selected qwen:", dict(qwen)[200], "| selected phobert:", dict(phobert)[100])
