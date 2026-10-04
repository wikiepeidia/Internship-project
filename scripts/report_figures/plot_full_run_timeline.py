"""Figure: where the 14.87 hours of the accepted Qwen run actually went.

Source (read-only): data/models/phase40/full/qwen-qlora/events.jsonl
  run_start 2026-08-25T03:22:03Z -> run_end 2026-08-25T18:14:04Z = 53,518.7 s = 14.87 h
  1,245 step_timing events, 26 evaluation events, 26 checkpoint events.

VERIFIED DECOMPOSITION (recomputed from the event timestamps, not quoted):
  optimizer steps          1.363 h   (sum of the 1,245 recorded step durations, 9.2%)
  checkpoint -> next event 13.061 h  (24 gaps of 12.426 h + the final 0.635 h gap)
  remainder                ~0.44 h   (loss evaluation, checkpoint writes, logging)

What fills the 13 h is a generation pass, not idle time: every checkpoint directory
holds a predictions.json with exactly 219 rows of generated structured output
(25 checkpoints x 219 validation rows = 5,475 generations on a laptop GPU).

NOTE ON peak_reserved_bytes: deliberately NOT plotted. The run's own hardware block
reports the card as 8,546,484,224 B while peak_reserved reaches 9,030,336,512 B --
a driver host-memory spill that nothing in this repo confirms. peak_allocated is the
defensible series and shows the same thing.
"""
import datetime as dt
import json

import matplotlib.pyplot as plt

from vnphish_figs import (
    INK_MUTED, INK_PRIMARY, INK_SECONDARY, PROJECT_ROOT, SERIES, SURFACE,
    save, style_axes, titles,
)

EVENTS = PROJECT_ROOT / "data/models/phase40/full/qwen-qlora/events.jsonl"
ev = [json.loads(l) for l in EVENTS.read_text(encoding="utf-8").splitlines() if l.strip()]
ev.sort(key=lambda e: (e["timestamp_utc"], e.get("sequence_id", 0)))


def ts(e):
    return dt.datetime.fromisoformat(e["timestamp_utc"].replace("Z", "+00:00"))


t0 = ts(next(e for e in ev if e["event_kind"] == "run_start"))
t_end = ts(next(e for e in ev if e["event_kind"] == "run_end"))
total_h = (t_end - t0).total_seconds() / 3600

steps = [e for e in ev if e["event_kind"] == "step_timing"]
step_no = [e["optimizer_step"] for e in steps]
elapsed_h = [(ts(e) - t0).total_seconds() / 3600 for e in steps]
vram_gib = [e["trainer_values"]["peak_allocated_bytes"] / 1024**3 for e in steps]

step_seconds = sum(e["trainer_values"]["duration_seconds"] for e in steps)
step_h = step_seconds / 3600
checkpoint_steps = sorted({e["optimizer_step"] for e in ev if e["event_kind"] == "checkpoint"})
# 26 checkpoint events but 25 distinct steps -- step 1245 emits twice.

fig, (ax_t, ax_m) = plt.subplots(2, 1, figsize=(8, 5.6), dpi=120, sharex=True)
fig.patch.set_facecolor(SURFACE)
for ax in (ax_t, ax_m):
    style_axes(ax)

# panel 1: cumulative wall clock -- the staircase
ax_t.plot(step_no, elapsed_h, color=SERIES[0], linewidth=1.8, solid_capstyle="round", zorder=3)
ax_t.set_ylim(0, total_h * 1.13)
ax_t.set_yticks([0, 3, 6, 9, 12, 15])
ax_t.set_ylabel("elapsed wall clock (h)", color=INK_SECONDARY, fontsize=9.5)
ax_t.annotate(
    "each riser is one validation pass:\n219 rows generated, then training resumes",
    xy=(1050, 11.1), xytext=(250, 12.6), fontsize=8.5, color=INK_MUTED,
    arrowprops=dict(arrowstyle="-", color=INK_MUTED, linewidth=0.8,
                    connectionstyle="angle3,angleA=0,angleB=60"),
)
ax_t.annotate(
    f"total {total_h:.2f} h", xy=(step_no[-1], elapsed_h[-1]),
    xytext=(-4, 8), textcoords="offset points",
    fontsize=9, color=INK_PRIMARY, ha="right",
)

# panel 2: peak allocated VRAM across the real run
ax_m.plot(step_no, vram_gib, color=SERIES[0], linewidth=1.5, solid_capstyle="round", zorder=3)
ax_m.set_ylim(0, 7.4)
ax_m.set_yticks([0, 2, 4, 6])
ax_m.set_ylabel("peak allocated VRAM (GiB)", color=INK_SECONDARY, fontsize=9.5)
ax_m.set_xlabel("optimizer step", color=INK_SECONDARY, fontsize=10)
ax_m.set_xlim(0, 1270)
ax_m.annotate(
    f"{min(vram_gib):.2f} – {max(vram_gib):.2f} GiB across all 1,245 steps",
    xy=(640, max(vram_gib)), xytext=(0, 9), textcoords="offset points",
    fontsize=8.5, color=INK_MUTED, ha="center",
)

titles(
    fig,
    "Where the 14.87-hour training run went",
    f"1,245 steps over 3 epochs, seed 42  ·  the steps themselves took {step_h:.2f} h "
    f"({100*step_h/total_h:.0f}%)  ·  the rest is {len(checkpoint_steps)} validation passes, "
    f"each writing a full answer for all 219 messages",
)
fig.subplots_adjust(left=0.095, right=0.985, top=0.855, bottom=0.10, hspace=0.16)

save(fig, "full_run_timeline.png")
print(f"total {total_h:.3f} h | steps {step_h:.3f} h ({100*step_h/total_h:.1f}%)")
print(f"vram peak_allocated {min(vram_gib):.3f} - {max(vram_gib):.3f} GiB")
print(f"checkpoints {len(checkpoint_steps)}")
