"""Figure: GPU telemetry during the QLoRA resource probe.

Source: data/models/phase40/probes/rtx5050-qlora-session-20260825/qlora/telemetry.jsonl
126 rows = 125 real nvidia-smi samples + 1 terminal sentinel row.
Read-only: reads that file, writes a new PNG into the report's figures/ directory.
Nothing under data/models is modified.
"""
import json
import sys

import matplotlib.pyplot as plt

from vnphish_figs import (
    BASELINE, INK_SECONDARY, PROJECT_ROOT, SERIES, SURFACE,
    peak_label, save, style_axes, titles,
)

TELEMETRY = (
    PROJECT_ROOT
    / "data/models/phase40/probes/rtx5050-qlora-session-20260825/qlora/telemetry.jsonl"
)

all_rows = [json.loads(l) for l in TELEMETRY.read_text(encoding="utf-8").splitlines() if l.strip()]
rows = [r for r in all_rows if r.get("gpu_utilization_percent") is not None]

t0 = rows[0]["monotonic_seconds"]
elapsed = [r["monotonic_seconds"] - t0 for r in rows]
util = [r["gpu_utilization_percent"] for r in rows]
vram = [r["device_vram_used_mib"] for r in rows]
vram_total = rows[0]["device_vram_total_mib"]

peak_util = max(util)
peak_util_t = elapsed[util.index(peak_util)]
peak_vram = max(vram)
peak_vram_t = elapsed[vram.index(peak_vram)]

fig, (ax_u, ax_v) = plt.subplots(2, 1, figsize=(8, 5.4), dpi=120, sharex=True)
fig.patch.set_facecolor(SURFACE)
for ax in (ax_u, ax_v):
    style_axes(ax)

ax_u.plot(elapsed, util, color=SERIES[0], linewidth=1.8, solid_capstyle="round", zorder=3)
ax_u.set_ylim(0, 112)
ax_u.set_yticks([0, 25, 50, 75, 100])
ax_u.set_ylabel("GPU utilisation (%)", color=INK_SECONDARY, fontsize=10)
peak_label(ax_u, peak_util_t, peak_util, f"peak {peak_util}%", dx=7, dy=3)

ax_v.plot(elapsed, vram, color=SERIES[0], linewidth=1.8, solid_capstyle="round",
          zorder=3, label="video memory in use")
ax_v.axhline(vram_total, color=BASELINE, linewidth=1.4, linestyle=(0, (5, 3)), zorder=2,
             label=f"whole card ({vram_total:,} MiB)")
ax_v.set_ylim(0, vram_total * 1.14)
ax_v.set_yticks([0, 2000, 4000, 6000, 8000])
ax_v.set_ylabel("Video memory (MiB)", color=INK_SECONDARY, fontsize=10)
ax_v.set_xlabel("Seconds since the run started", color=INK_SECONDARY, fontsize=10)
ax_v.set_xlim(-6, max(elapsed) + 6)
peak_label(ax_v, peak_vram_t, peak_vram, f"peak {peak_vram:,} MiB", dx=7, dy=4)
ax_v.legend(loc="lower right", frameon=False, fontsize=9, labelcolor=INK_SECONDARY)

# The UTC window is real and stays available, but it reads as a log dump in the
# report, so it is only printed when explicitly asked for.
subtitle = ("NVIDIA GeForce RTX 5050 Laptop GPU  ·  45 optimizer steps  ·  "
            "125 nvidia-smi samples over 261 seconds")
if "--with-timestamp" in sys.argv:
    subtitle += "  ·  2026-08-25, 00:54–00:59 UTC"

titles(fig, "GPU load during the 45-step QLoRA measurement run", subtitle)
fig.subplots_adjust(left=0.095, right=0.985, top=0.855, bottom=0.11, hspace=0.16)

save(fig, "gpu_telemetry_probe.png")
print(f"peak_util {peak_util}% @ {peak_util_t:.1f}s | peak_vram {peak_vram} MiB @ {peak_vram_t:.1f}s")
print(f"samples {len(rows)} | span {elapsed[-1]:.1f}s | headroom {vram_total - peak_vram} MiB")
