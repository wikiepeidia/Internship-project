"""Figures: Qwen against PhoBERT, on validation and on the held-out messages.

Two figures in one style, so Chapter V stops mixing a hand-drawn TikZ bar chart
with a plain table.

Sources (read-only, values transcribed from the verified records):
  .planning/phases/40-multi-model-training-evidence/40-VALIDATION-COMPARISON.md
      qwen    selected_step=200 macro_F1=0.9885
              risky_recall bank=0.9868 zalo=1.0000 task=1.0000
      phobert selected_step=100 macro_F1=0.9849
              risky_recall bank=1.0000 zalo=0.9545 task=1.0000
  data/models/phase41/verified-export/*/results.md  (via CLAUDE.md anchors)
      qwen    0.981818 / 0.980493 / 0.981848
      phobert 0.990909 / 0.990892 / 0.990925

The y axis starts at 0.90 on purpose: every value sits between 0.95 and 1.00 and
a full 0-1 axis renders them as five identical bars. The axis floor is drawn and
labelled, and every bar carries its value, so the truncation cannot mislead.
"""
import matplotlib.pyplot as plt

from vnphish_figs import (
    BASELINE, GRIDLINE, INK_MUTED, INK_PRIMARY, INK_SECONDARY, SERIES, SURFACE,
    save, style_axes, titles,
)

QWEN, PHO = SERIES[0], SERIES[1]
FLOOR = 0.90

VAL_OVERALL = [("Accuracy", 0.990868, 0.986301), ("Macro F1", 0.988515, 0.984893)]
VAL_RECALL = [
    ("Bank\nimpersonation", 0.9868, 1.0000),
    ("Zalo social\nengineering", 1.0000, 0.9545),
    ("Task\nscam", 1.0000, 1.0000),
]
TERMINAL = [
    ("Accuracy", 0.981818, 0.990909),
    ("Macro F1", 0.980493, 0.990892),
    ("Weighted F1", 0.981848, 0.990925),
]


def grouped(ax, rows, *, ylabel, title, fs=8.4):
    """One grouped bar panel: Qwen left, PhoBERT right, value printed on each bar."""
    style_axes(ax)
    n = len(rows)
    xs = range(n)
    w = 0.34
    for i, (_, q, p) in enumerate(rows):
        ax.bar(i - w / 2, q - FLOOR, width=w, bottom=FLOOR, color=QWEN, zorder=3)
        ax.bar(i + w / 2, p - FLOOR, width=w, bottom=FLOOR, color=PHO, zorder=3)
        for x, v in ((i - w / 2, q), (i + w / 2, p)):
            ax.text(x, v + 0.0022, f"{v:.4f}",
                    ha="center", va="bottom", fontsize=fs, color=INK_PRIMARY,
                    rotation=90, zorder=4)
    ax.set_xticks(list(xs), [r[0] for r in rows], fontsize=9, color=INK_SECONDARY)
    ax.set_ylim(FLOOR, 1.055)
    ax.set_yticks([0.90, 0.925, 0.95, 0.975, 1.0])
    ax.set_ylabel(ylabel, color=INK_SECONDARY, fontsize=9.5)
    ax.axhline(FLOOR, color=BASELINE, linewidth=1.0, zorder=2)
    ax.set_title(title, fontsize=10, color=INK_PRIMARY, loc="left", pad=8)


def legend(fig, y):
    fig.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=QWEN),
                        plt.Rectangle((0, 0), 1, 1, color=PHO)],
               labels=["Qwen QLoRA", "PhoBERT"], loc="upper right",
               bbox_to_anchor=(0.995, y), ncol=2, frameon=False, fontsize=9,
               labelcolor=INK_SECONDARY)


# ── validation ────────────────────────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.8, 3.6), dpi=120,
                               gridspec_kw={"width_ratios": [1, 1.45]})
fig.patch.set_facecolor(SURFACE)
grouped(ax1, VAL_OVERALL, ylabel="score", title="Overall")
grouped(ax2, VAL_RECALL, ylabel="recall", title="Risky messages caught, per class")
titles(fig, "Validation: the same 219 messages, both models",
       "Seed 42  ·  Qwen checkpoint 200, PhoBERT checkpoint 100  ·  one run each",
       y=0.975, sub_y=0.906)
legend(fig, 0.955)
fig.subplots_adjust(left=0.075, right=0.995, top=0.70, bottom=0.145, wspace=0.28)
save(fig, "validation_comparison.png")

# ── held-out ──────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8.0, 3.5), dpi=120)
fig.patch.set_facecolor(SURFACE)
grouped(ax, TERMINAL, ylabel="score", title="")
titles(fig, "The 220 messages neither model had seen",
       "One run each  ·  no unreadable answers",
       y=0.975, sub_y=0.900)
legend(fig, 0.95)
fig.subplots_adjust(left=0.085, right=0.995, top=0.72, bottom=0.115)
save(fig, "terminal_comparison.png")

print("validation qwen/phobert macro F1:", VAL_OVERALL[1][1], VAL_OVERALL[1][2])
print("terminal  qwen/phobert macro F1:", TERMINAL[1][1], TERMINAL[1][2])
