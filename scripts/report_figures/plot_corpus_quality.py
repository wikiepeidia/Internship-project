"""Figure: independent judge review of the corpus -- rubric scores and per-class pass rates.

Sources (read-only):
  data/processed/judge-summary.json   -- the five average rubric scores, totals
  data/processed/judge-merged.jsonl   -- per-row verdicts, aggregated here by label

Verified: 1,395 / 2,097 rows pass (66.52%). A row passes only if ALL FIVE rubric
dimensions score >= 3. Class totals 741 / 655 / 404 / 297 match the project's anchors.

This figure is deliberately unflattering. The weak dimensions (realism 4.02,
risk-tier correctness 4.12) and the weak classes (task scam 47.5%, benign 50.5%)
are the reason the corpus repair work exists, and showing them is the point.
"""
import json
from collections import defaultdict

import matplotlib.pyplot as plt

from vnphish_figs import (
    BASELINE, INK_MUTED, INK_PRIMARY, INK_SECONDARY, PROJECT_ROOT, SERIES, SURFACE,
    save, style_axes, titles,
)

PROCESSED = PROJECT_ROOT / "data/processed"
summary = json.loads((PROCESSED / "judge-summary.json").read_text(encoding="utf-8"))

RUBRIC = [
    ("avg_label_correctness", "Is the label right?"),
    ("avg_suspicious_span_accuracy", "Are the highlighted\nphrases right?"),
    ("avg_code_switch_naturalness", "Is the Vietnamese-English\nmix natural?"),
    ("avg_risk_tier_correctness", "Is the risk level right?"),
    ("avg_realism", "Does it read like\na real scam?"),
]
rubric = sorted(((summary[k], name) for k, name in RUBRIC), reverse=True)

CLASS_NAMES = {
    "bank_impersonation": "Bank impersonation",
    "benign": "Benign",
    "task_scam": "Task scam",
    "zalo_social_engineering": "Zalo social engineering",
}
tot, passed = defaultdict(int), defaultdict(int)
for line in (PROCESSED / "judge-merged.jsonl").read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    row = json.loads(line)
    tot[row["label"]] += 1
    passed[row["label"]] += 1 if row.get("judge_pass") else 0
classes = sorted(
    ((passed[k] / tot[k], CLASS_NAMES.get(k, k), passed[k], tot[k]) for k in tot),
    reverse=True,
)
overall = summary["passed"] / summary["total"]

fig, (ax_r, ax_c) = plt.subplots(1, 2, figsize=(8.6, 3.5), dpi=120)
fig.patch.set_facecolor(SURFACE)

# left: average rubric score out of 5
style_axes(ax_r, xgrid=True)
ax_r.grid(axis="y", visible=False)
names = [n for _, n in rubric]
vals = [v for v, _ in rubric]
ypos = range(len(vals))
ax_r.barh(ypos, vals, height=0.62, color=SERIES[0], zorder=3)
ax_r.set_yticks(list(ypos), names, fontsize=8.2, color=INK_SECONDARY)
ax_r.invert_yaxis()
ax_r.set_xlim(0, 5.55)
ax_r.set_xticks([0, 1, 2, 3, 4, 5])
ax_r.set_xlabel("average score out of 5", color=INK_SECONDARY, fontsize=9.5)
ax_r.axvline(3, color=BASELINE, linewidth=1.2, linestyle=(0, (4, 3)), zorder=4)
ax_r.text(3.06, len(vals) - 0.42, "below 3 fails", fontsize=8, color=INK_MUTED, va="top")
for y, v in zip(ypos, vals):
    ax_r.text(v + 0.1, y, f"{v:.2f}", va="center", fontsize=8.5, color=INK_PRIMARY)
ax_r.set_title("Average score on each of the five checks", fontsize=10, color=INK_PRIMARY,
               loc="left", pad=8)

# right: per-class pass rate
style_axes(ax_c, xgrid=True)
ax_c.grid(axis="y", visible=False)
cnames = [n for _, n, _, _ in classes]
crates = [r for r, _, _, _ in classes]
cy = range(len(crates))
ax_c.barh(cy, crates, height=0.62, color=SERIES[0], zorder=3)
ax_c.set_yticks(list(cy), cnames, fontsize=9, color=INK_SECONDARY)
ax_c.invert_yaxis()
ax_c.set_xlim(0, 1.52)
ax_c.set_xticks([0, 0.25, 0.5, 0.75, 1.0], ["0%", "25%", "50%", "75%", "100%"])
ax_c.set_xlabel("messages passing all five checks", color=INK_SECONDARY, fontsize=9.5)
ax_c.axvline(overall, color=BASELINE, linewidth=1.2, linestyle=(0, (4, 3)), zorder=4)
ax_c.text(overall + 0.018, len(crates) - 0.48, f"whole set: {overall:.1%}",
          fontsize=8, color=INK_MUTED, va="bottom")
for y, (r, _, p, t) in zip(cy, classes):
    ax_c.text(r + 0.025, y, f"{r:.1%}  ({p:,}/{t:,})", va="center", fontsize=8.5,
              color=INK_PRIMARY)
ax_c.set_title("How many passed, per class", fontsize=10, color=INK_PRIMARY, loc="left", pad=8)

titles(
    fig,
    "Quality scores across the whole set of messages",
    f"A message passes only if all five scores are 3 or higher  ·  "
    f"{summary['passed']:,} of {summary['total']:,} pass ({overall:.2%})",
    y=0.975, sub_y=0.905,
)
fig.subplots_adjust(left=0.20, right=0.995, top=0.70, bottom=0.195, wspace=0.66)

save(fig, "corpus_judge_quality.png")
for r, n, p, t in classes:
    print(f"{n:26s} {p:5d}/{t:5d} = {r:.4f}")
print("overall", summary["passed"], "/", summary["total"], "=", round(overall, 4))
