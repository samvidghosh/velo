"""
generate_synthetic_data.py
==========================
Generates deterministic synthetic pose sequences for Velo engine testing.

IMPORTANT: All data produced by this script is **simulated**.
It does NOT represent real human performance, and should NOT be used
to draw conclusions about actual exercise technique or safety.

Usage
-----
    python engine/examples/generate_synthetic_data.py

Each scenario is returned as a list of frame dicts compatible with
``analyze_movement(frames, exercise="squat")``.

Generation strategy
-------------------
Knee angles follow smooth sinusoidal arcs between standing and bottom
positions, parameterised by tempo, depth, and noise level.  Hip and torso
angles are derived from the knee angle via heuristic ratios that approximate
typical kinematic coupling — they are NOT biomechanical ground truth.
"""

from __future__ import annotations

import math
import random
from typing import Any

import numpy as np

# ── deterministic seed ────────────────────────────────────────────────────
_RNG = random.Random(42)
_NP_RNG = np.random.default_rng(42)


# ---------------------------------------------------------------------------
# Core pose builder
# ---------------------------------------------------------------------------

def _build_pose(
    knee_angle_deg: float,
    *,
    side: str = "bilateral",   # "left", "right", or "bilateral"
    confidence: float = 1.0,
    left_knee_override: float | None = None,
    right_knee_override: float | None = None,
    missing: set[str] | None = None,
) -> dict[str, Any]:
    """Build a synthetic MediaPipe-style pose from a knee angle.

    Coordinates are normalised image fractions (x ∈ [0,1], y ∈ [0,1]).
    The body is placed roughly centred in the frame.

    Approximate kinematic coupling
    --------------------------------
    *  Hip angle ≈ 0.6 × knee_angle + 30  (heuristic, not biomechanical truth)
    *  Torso lean grows as the person squats

    Parameters
    ----------
    knee_angle_deg:
        Primary knee angle (both sides unless overrides are given).
    confidence:
        Landmark confidence applied to all produced landmarks.
    missing:
        Set of landmark names to omit from the pose entirely.
    """
    missing = missing or set()
    ka_l = left_knee_override  if left_knee_override  is not None else knee_angle_deg
    ka_r = right_knee_override if right_knee_override is not None else knee_angle_deg

    # Derived hip angle (rough coupling)
    ha_l = 0.6 * ka_l + 30.0
    ha_r = 0.6 * ka_r + 30.0

    # Build coordinate layout from joint angles
    # Origin: mid-hip at (0.5, 0.65)
    MID_HIP_X, MID_HIP_Y = 0.5, 0.65
    PELVIS_HALF_W         = 0.05   # half hip width (normalised)
    SHOULDER_HALF_W       = 0.06
    TORSO_LEN             = 0.20   # trunk length (normalised)

    # Squat depth changes hip height (body descends)
    squat_frac    = max(0.0, (180.0 - knee_angle_deg) / 90.0)  # 0 = standing, 1 = deep
    hip_y_offset  = squat_frac * 0.08    # 8% of frame height descent

    # Hip positions
    lhip = np.array([MID_HIP_X - PELVIS_HALF_W, MID_HIP_Y + hip_y_offset])
    rhip = np.array([MID_HIP_X + PELVIS_HALF_W, MID_HIP_Y + hip_y_offset])

    # Torso lean (small forward lean during squat, rightward in image = +x)
    torso_lean_deg = 10.0 + squat_frac * 15.0   # 10–25° forward lean
    torso_rad      = math.radians(torso_lean_deg)
    trunk_dx       =  math.sin(torso_rad) * TORSO_LEN
    trunk_dy       = -math.cos(torso_rad) * TORSO_LEN

    # Shoulder positions
    lshoulder = lhip + np.array([-SHOULDER_HALF_W + trunk_dx / 2, trunk_dy])
    rshoulder = rhip + np.array([ SHOULDER_HALF_W + trunk_dx / 2, trunk_dy])

    def _knee_ankle_from_angle(hip: np.ndarray, angle_deg: float, side_sign: float):
        """Compute knee + ankle from hip position and knee angle."""
        thigh_len  = 0.18
        shin_len   = 0.17
        # Thigh angle from vertical (increases with squat depth)
        thigh_angle_rad = math.radians(20.0 + squat_frac * 35.0)
        knee = hip + np.array([
            side_sign * math.sin(thigh_angle_rad) * thigh_len,
            math.cos(thigh_angle_rad) * thigh_len,
        ])
        # Shin angle
        shin_angle_rad = math.radians(angle_deg)
        # Convert knee angle to shin direction: shin leans back toward ankle
        ankle = knee + np.array([
            -side_sign * math.sin(math.pi - shin_angle_rad) * shin_len * 0.5,
            math.cos(math.pi - shin_angle_rad) * shin_len * 0.5 + shin_len * 0.85,
        ])
        # Clamp to valid range
        ankle = np.clip(ankle, 0.0, 1.0)
        return knee, ankle

    lknee, lankle = _knee_ankle_from_angle(lhip, ka_l, -1.0)
    rknee, rankle = _knee_ankle_from_angle(rhip, ka_r,  1.0)

    # Arms (simplified: hanging by sides)
    lelbow  = lshoulder + np.array([-0.02, 0.10])
    relbow  = rshoulder + np.array([ 0.02, 0.10])
    lwrist  = lelbow    + np.array([-0.01, 0.09])
    rwrist  = relbow    + np.array([ 0.01, 0.09])

    def _entry(coords: np.ndarray) -> dict[str, Any]:
        return {"coords": coords.tolist(), "confidence": confidence}

    all_landmarks: dict[str, Any] = {
        "LEFT_HIP":       _entry(lhip),
        "RIGHT_HIP":      _entry(rhip),
        "LEFT_KNEE":      _entry(lknee),
        "RIGHT_KNEE":     _entry(rknee),
        "LEFT_ANKLE":     _entry(lankle),
        "RIGHT_ANKLE":    _entry(rankle),
        "LEFT_SHOULDER":  _entry(lshoulder),
        "RIGHT_SHOULDER": _entry(rshoulder),
        "LEFT_ELBOW":     _entry(lelbow),
        "RIGHT_ELBOW":    _entry(relbow),
        "LEFT_WRIST":     _entry(lwrist),
        "RIGHT_WRIST":    _entry(rwrist),
    }

    for name in missing:
        all_landmarks.pop(name, None)

    return all_landmarks


def _squat_arc(
    t: float,
    period: float,
    standing_angle: float = 170.0,
    bottom_angle:   float = 90.0,
) -> float:
    """Return the knee angle at normalised phase t (0=top, 0.5=bottom, 1=top).

    Uses a cosine arc for smooth, continuous motion.
    """
    phase = (t % period) / period          # 0 → 1
    cos_val = math.cos(2.0 * math.pi * phase)    # 1 at top, -1 at bottom
    return bottom_angle + (standing_angle - bottom_angle) * (cos_val + 1.0) / 2.0


def _add_noise(angle: float, sigma: float, rng: np.random.Generator) -> float:
    return float(angle + rng.normal(0.0, sigma))


# ---------------------------------------------------------------------------
# Scenario builders
# ---------------------------------------------------------------------------

def _frames_from_angles(
    angles: list[float],
    timestamps: list[float],
    *,
    confidence: float = 1.0,
    left_override: list[float | None] | None = None,
    right_override: list[float | None] | None = None,
    missing_per_frame: list[set[str]] | None = None,
) -> list[dict[str, Any]]:
    n = len(angles)
    frames = []
    for i in range(n):
        lo = left_override[i]  if left_override  else None
        ro = right_override[i] if right_override else None
        ms = missing_per_frame[i] if missing_per_frame else set()
        pose = _build_pose(
            angles[i],
            confidence          = confidence,
            left_knee_override  = lo,
            right_knee_override = ro,
            missing             = ms,
        )
        frames.append({"timestamp": timestamps[i], "pose": pose})
    return frames


def scenario_three_complete_squats(fps: float = 30.0) -> list[dict[str, Any]]:
    """Three clean, complete squat repetitions at a moderate pace."""
    period   = 3.0   # seconds per rep
    n_reps   = 3
    duration = n_reps * period + 1.0   # extra second at standing
    n        = int(duration * fps)
    times    = [i / fps for i in range(n)]
    # Stand for the first 0.5s before starting
    stand_frames = int(0.5 * fps)
    angles = []
    for i, t in enumerate(times):
        if i < stand_frames:
            angles.append(170.0)
        else:
            angles.append(_squat_arc(t - 0.5, period, 170.0, 90.0))
    return _frames_from_angles(angles, times)


def scenario_incomplete_squat(fps: float = 30.0) -> list[dict[str, Any]]:
    """Person begins a squat but stops mid-descent and returns to standing."""
    period   = 3.0
    duration = 5.0
    n        = int(duration * fps)
    times    = [i / fps for i in range(n)]
    angles   = []
    for t in times:
        if t < 0.5:
            angles.append(170.0)
        elif t < 1.5:
            # descend partway
            frac = (t - 0.5) / 1.0
            angles.append(170.0 - frac * 30.0)  # only goes to 140°
        else:
            # return to standing
            frac = min(1.0, (t - 1.5) / 1.5)
            angles.append(140.0 + frac * 30.0)
    return _frames_from_angles(angles, times)


def scenario_partial_squat(fps: float = 30.0) -> list[dict[str, Any]]:
    """Shallow squat — never reaches depth threshold (stays above 120°)."""
    period   = 3.0
    n_reps   = 2
    duration = n_reps * period + 0.5
    n        = int(duration * fps)
    times    = [i / fps for i in range(n)]
    angles   = [_squat_arc(t, period, 170.0, 130.0) for t in times]
    return _frames_from_angles(angles, times)


def scenario_fast_squat(fps: float = 30.0) -> list[dict[str, Any]]:
    """Fast repetitions (1 s per rep cycle)."""
    period   = 1.0
    n_reps   = 4
    duration = n_reps * period + 0.5
    n        = int(duration * fps)
    times    = [i / fps for i in range(n)]
    angles   = [_squat_arc(t, period, 170.0, 90.0) for t in times]
    return _frames_from_angles(angles, times)


def scenario_slow_squat(fps: float = 30.0) -> list[dict[str, Any]]:
    """Slow repetitions (6 s per rep cycle)."""
    period   = 6.0
    n_reps   = 2
    duration = n_reps * period + 1.0
    n        = int(duration * fps)
    times    = [i / fps for i in range(n)]
    angles   = [_squat_arc(t, period, 170.0, 90.0) for t in times]
    return _frames_from_angles(angles, times)


def scenario_pause_at_bottom(fps: float = 30.0) -> list[dict[str, Any]]:
    """Two squats with a 2-second pause at the bottom position."""
    frames: list[dict[str, Any]] = []
    t = 0.0
    dt = 1.0 / fps

    for _ in range(2):
        # Descent: 1.5 s
        n_descent = int(1.5 * fps)
        for i in range(n_descent):
            frac   = i / n_descent
            angle  = 170.0 - frac * 80.0       # 170° → 90°
            pose   = _build_pose(angle)
            frames.append({"timestamp": t, "pose": pose})
            t += dt

        # Pause at bottom: 2 s
        n_pause = int(2.0 * fps)
        for _ in range(n_pause):
            pose = _build_pose(90.0)
            frames.append({"timestamp": t, "pose": pose})
            t += dt

        # Ascent: 1.5 s
        n_ascent = int(1.5 * fps)
        for i in range(n_ascent):
            frac   = i / n_ascent
            angle  = 90.0 + frac * 80.0         # 90° → 170°
            pose   = _build_pose(angle)
            frames.append({"timestamp": t, "pose": pose})
            t += dt

        # Standing pause between reps: 1 s
        n_stand = int(1.0 * fps)
        for _ in range(n_stand):
            pose = _build_pose(170.0)
            frames.append({"timestamp": t, "pose": pose})
            t += dt

    return frames


def scenario_noisy_joints(fps: float = 30.0, noise_sigma: float = 5.0) -> list[dict[str, Any]]:
    """Three squats with Gaussian noise added to knee angles."""
    period   = 3.0
    n_reps   = 3
    duration = n_reps * period + 0.5
    n        = int(duration * fps)
    times    = [i / fps for i in range(n)]
    rng      = np.random.default_rng(7)
    angles   = [
        _add_noise(_squat_arc(t, period, 170.0, 90.0), noise_sigma, rng)
        for t in times
    ]
    # Clamp to plausible range
    angles = [max(60.0, min(180.0, a)) for a in angles]
    return _frames_from_angles(angles, times)


def scenario_missing_landmarks(fps: float = 30.0) -> list[dict[str, Any]]:
    """Three squats where LEFT_KNEE is intermittently absent."""
    period   = 3.0
    n_reps   = 3
    duration = n_reps * period + 0.5
    n        = int(duration * fps)
    times    = [i / fps for i in range(n)]
    angles   = [_squat_arc(t, period, 170.0, 90.0) for t in times]

    missing_per_frame: list[set[str]] = []
    rng = random.Random(99)
    for _ in range(n):
        # 25 % of frames drop LEFT_KNEE
        missing_per_frame.append({"LEFT_KNEE"} if rng.random() < 0.25 else set())

    return _frames_from_angles(angles, times, missing_per_frame=missing_per_frame)


def scenario_low_confidence(fps: float = 30.0) -> list[dict[str, Any]]:
    """Three squats where every other frame has low-confidence landmarks."""
    period   = 3.0
    n_reps   = 3
    duration = n_reps * period + 0.5
    n        = int(duration * fps)
    times    = [i / fps for i in range(n)]
    angles   = [_squat_arc(t, period, 170.0, 90.0) for t in times]
    frames   = []
    for i, (t, a) in enumerate(zip(times, angles)):
        conf = 0.3 if i % 2 == 0 else 0.95   # alternating low/high confidence
        pose = _build_pose(a, confidence=conf)
        frames.append({"timestamp": t, "pose": pose})
    return frames


def scenario_irregular_frame_intervals(fps_base: float = 30.0) -> list[dict[str, Any]]:
    """Three squats with randomly jittered frame intervals (±50 %)."""
    period   = 3.0
    n_reps   = 3
    n        = int((n_reps * period + 0.5) * fps_base)
    rng      = np.random.default_rng(13)
    # Build irregular timestamps (still monotonic)
    dts   = rng.uniform(0.5 / fps_base, 2.0 / fps_base, size=n)
    times = list(np.cumsum(dts).astype(float))
    angles = [_squat_arc(t, period, 170.0, 90.0) for t in times]
    return _frames_from_angles(angles, times)


def scenario_interrupted_sequence(fps: float = 30.0) -> list[dict[str, Any]]:
    """Two squats, a long gap (2 s of missing frames), then one more squat."""
    frames: list[dict[str, Any]] = []
    period = 3.0
    dt = 1.0 / fps

    # First two reps
    n1 = int(2 * period * fps)
    for i in range(n1):
        t    = i * dt
        angle = _squat_arc(t, period, 170.0, 90.0)
        frames.append({"timestamp": t, "pose": _build_pose(angle)})

    # 2-second gap (missing frames — simply advance timestamp)
    gap_start = frames[-1]["timestamp"] + 2.0 + dt

    # Third rep starting after the gap
    n2 = int(period * fps) + 30   # one rep + standing buffer
    for i in range(n2):
        t     = gap_start + i * dt
        angle = _squat_arc(i * dt, period, 170.0, 90.0)  # reset time within rep
        frames.append({"timestamp": t, "pose": _build_pose(angle)})

    return frames


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, Any] = {
    "three_complete_squats"    : scenario_three_complete_squats,
    "incomplete_squat"         : scenario_incomplete_squat,
    "partial_squat"            : scenario_partial_squat,
    "fast_squat"               : scenario_fast_squat,
    "slow_squat"               : scenario_slow_squat,
    "pause_at_bottom"          : scenario_pause_at_bottom,
    "noisy_joints"             : scenario_noisy_joints,
    "missing_landmarks"        : scenario_missing_landmarks,
    "low_confidence"           : scenario_low_confidence,
    "irregular_frame_intervals": scenario_irregular_frame_intervals,
    "interrupted_sequence"     : scenario_interrupted_sequence,
}


def get_scenario(name: str) -> list[dict[str, Any]]:
    """Return frames for the named scenario.

    Raises KeyError if the scenario is not found.
    """
    if name not in SCENARIOS:
        raise KeyError(f"Unknown scenario '{name}'.  Available: {list(SCENARIOS)}")
    return SCENARIOS[name]()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Velo Synthetic Data Generator")
    print("ALL DATA IS SIMULATED — not real human performance.")
    print("=" * 60)
    for name, fn in SCENARIOS.items():
        frames = fn()
        print(f"  {name:<35}  {len(frames):>4} frames")
    print("\nDone.  Import get_scenario() or SCENARIOS to use in tests.")
