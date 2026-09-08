"""Shared style helpers for the VNPhish report figures.

Palette follows the dataviz reference palette (light mode), so every generated
figure in the report reads as one system.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = PROJECT_ROOT / "documents/reports/latex/figures"

SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # blue, orange, aqua, yellow

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Segoe UI", "DejaVu Sans", "Arial"]


def style_axes(ax, *, xgrid=False):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="both" if xgrid else "y", color=GRIDLINE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(BASELINE)
    ax.tick_params(colors=INK_MUTED, labelsize=9)


def titles(fig, title, subtitle, *, y=0.975, sub_y=0.925):
    fig.suptitle(title, fontsize=12, color=INK_PRIMARY, x=0.015, ha="left", y=y)
    fig.text(0.015, sub_y, subtitle, fontsize=8.5, color=INK_MUTED, ha="left", va="top")


def peak_label(ax, x, y, text, *, dx=6, dy=0, va="bottom", ha="left"):
    """Mark a peak with a dot and a short offset label -- no long leader line
    that could be misread as data."""
    ax.plot([x], [y], marker="o", markersize=5, color=INK_PRIMARY, zorder=5)
    ax.annotate(
        text,
        xy=(x, y),
        xytext=(dx, dy),
        textcoords="offset points",
        fontsize=9,
        color=INK_PRIMARY,
        va=va,
        ha=ha,
        zorder=6,
    )


def save(fig, name):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = FIG_DIR / name
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)
    print("wrote", name, out.stat().st_size, "bytes")
    return out
