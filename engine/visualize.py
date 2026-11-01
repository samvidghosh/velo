"""
visualize.py — Diagnostic plots for Velo engine analysis results
=================================================================

Usage
-----
    python engine/visualize.py --scenario three_complete_squats
    python engine/visualize.py --scenario noisy_joints --save

Requirements: matplotlib (optional dependency)

NOTE: This file requires matplotlib.  If it is not installed, run:
    pip install matplotlib
"""

from __future__ import annotations

import argparse
import math
import sys
from typing import Optional

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


# Phase colours
_PHASE_COLORS = {
    "UNKNOWN":    "#888888",
    "STANDING":   "#4CAF50",
    "DESCENDING": "#2196F3",
    "BOTTOM":     "#9C27B0",
    "ASCENDING":  "#FF9800",
}


def plot_analysis(result, title: str = "Velo Analysis", save_path: Optional[str] = None):
    """Generate a 4-panel diagnostic plot for an AnalysisResult.

    Panels
    ------
    1. Knee angle vs time (left/right if available) with phase background.
    2. Hip angle vs time.
    3. Phase timeline (colour strip).
    4. Missing-data intervals + rep boundaries.
    """
    if not HAS_MPL:
        print("matplotlib is not installed.  Run: pip install matplotlib")
        return

    ts       = result.timestamps
    angles   = result.angle_series
    events   = result.phase_events
    timeline = result.phase_timeline
    reps     = result.reps

    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
    fig.suptitle(title, fontsize=14, fontweight="bold")

    # --- Panel 1: Knee angles ---
    ax1 = axes[0]
    _shade_phases(ax1, timeline)
    for side, color, ls in [("LEFT_KNEE", "#1565C0", "-"), ("RIGHT_KNEE", "#C62828", "--")]:
        series = angles.get(side, [])
        if series:
            finite_ts  = [t for t, a in zip(ts, series) if math.isfinite(a)]
            finite_ang = [a for a in series if math.isfinite(a)]
            if finite_ts:
                ax1.plot(finite_ts, finite_ang, color=color, ls=ls, lw=1.5,
                         label=side.replace("_", " ").title())
    # Rep boundaries
    for r in reps:
        color = "#43A047" if r.valid else "#E53935"
        ax1.axvline(r.start_time,  color=color, lw=0.8, ls=":", alpha=0.7)
        ax1.axvline(r.end_time,    color=color, lw=1.2, ls="--", alpha=0.9)
        ax1.axvline(r.bottom_time, color="#6A1B9A", lw=0.8, ls=":", alpha=0.7)
    ax1.set_ylabel("Knee angle (°)")
    ax1.legend(loc="upper right", fontsize=8)
    ax1.grid(alpha=0.3)

    # --- Panel 2: Hip angles ---
    ax2 = axes[1]
    _shade_phases(ax2, timeline)
    for side, color, ls in [("LEFT_HIP", "#1B5E20", "-"), ("RIGHT_HIP", "#B71C1C", "--")]:
        series = angles.get(side, [])
        if series:
            finite_ts  = [t for t, a in zip(ts, series) if math.isfinite(a)]
            finite_ang = [a for a in series if math.isfinite(a)]
            if finite_ts:
                ax2.plot(finite_ts, finite_ang, color=color, ls=ls, lw=1.5,
                         label=side.replace("_", " ").title())
    ax2.set_ylabel("Hip angle (°)")
    ax2.legend(loc="upper right", fontsize=8)
    ax2.grid(alpha=0.3)

    # --- Panel 3: Phase colour strip ---
    ax3 = axes[2]
    if ts:
        phase_colors_seq = []
        for ev in events:
            phase_colors_seq.append(_PHASE_COLORS.get(ev.phase.name, "#CCCCCC"))
        # Draw as an image strip
        xmin, xmax = ts[0], ts[-1]
        ax3.set_xlim(xmin, xmax)
        for i, (ev, color) in enumerate(zip(events, phase_colors_seq)):
            x0 = ev.timestamp
            x1 = events[i + 1].timestamp if i + 1 < len(events) else x0 + 0.033
            ax3.axvspan(x0, x1, facecolor=color, alpha=0.7, linewidth=0)
    # Legend patches
    patches = [
        mpatches.Patch(color=c, label=p)
        for p, c in _PHASE_COLORS.items()
    ]
    ax3.legend(handles=patches, loc="upper right", fontsize=7, ncol=3)
    ax3.set_ylabel("Phase")
    ax3.set_yticks([])

    # --- Panel 4: Missing-data intervals + rep boundaries ---
    ax4 = axes[3]
    missing_ts = [t for t, fr in zip(ts, events) if fr.uncertain]
    if missing_ts:
        ax4.scatter(missing_ts, [0.5] * len(missing_ts),
                    marker="|", color="red", s=200, label="Uncertain frame")
    for r in reps:
        color = "#43A047" if r.valid else "#E53935"
        label = f"Rep {r.index} ({'valid' if r.valid else 'invalid'})"
        ax4.axvspan(r.start_time, r.end_time, alpha=0.2, color=color, label=label)
    ax4.set_ylabel("Rep events")
    ax4.set_yticks([])
    ax4.set_xlabel("Time (s)")
    ax4.legend(loc="upper right", fontsize=7)
    ax4.grid(alpha=0.2)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Plot saved to {save_path}")
    else:
        plt.show()

    plt.close(fig)


def plot_filtered_vs_unfiltered(
    timestamps: list[float],
    raw_angles: list[float],
    filtered_angles: list[float],
    joint_name: str = "LEFT_KNEE",
    save_path: Optional[str] = None,
):
    """Plot filtered vs unfiltered angle signals."""
    if not HAS_MPL:
        print("matplotlib is not installed.")
        return

    fig, ax = plt.subplots(figsize=(12, 4))

    def _plot_finite(ts, ang, **kwargs):
        pts = [(t, a) for t, a in zip(ts, ang) if math.isfinite(a)]
        if pts:
            t_p, a_p = zip(*pts)
            ax.plot(t_p, a_p, **kwargs)

    _plot_finite(timestamps, raw_angles,      color="gray",    lw=0.8, alpha=0.7, label="Raw")
    _plot_finite(timestamps, filtered_angles, color="#1565C0", lw=1.5,            label="Filtered")

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Angle (°)")
    ax.set_title(f"{joint_name} — filtered vs unfiltered")
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved to {save_path}")
    else:
        plt.show()
    plt.close(fig)


def _shade_phases(ax, timeline):
    for interval in timeline:
        color = _PHASE_COLORS.get(interval.phase.name, "#EEEEEE")
        ax.axvspan(interval.start_time, interval.end_time,
                   facecolor=color, alpha=0.15, linewidth=0)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if not HAS_MPL:
        print("ERROR: matplotlib is required for visualisation.")
        print("Install it with:  pip install matplotlib")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Velo diagnostic visualiser",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--scenario",
        default="three_complete_squats",
        help="Scenario name from generate_synthetic_data.SCENARIOS",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save plot to file instead of displaying interactively",
    )
    args = parser.parse_args()

    from engine.examples.generate_synthetic_data import get_scenario
    from engine.analyzer import analyze_movement

    print(f"Running scenario: {args.scenario}")
    frames = get_scenario(args.scenario)
    result = analyze_movement(frames, exercise="squat")

    print(result.summary_text())

    save_path = f"{args.scenario}_plot.png" if args.save else None
    plot_analysis(result, title=f"Velo — {args.scenario}", save_path=save_path)


if __name__ == "__main__":
    main()
