"""
config.py — Configurable exercise profiles and analysis parameters
==================================================================

ALL numerical thresholds in this file are **initial engineering defaults**.
They must be validated against labelled videos and expert-defined criteria
before use in any production or clinical context.

Coordinate conventions
----------------------
Poses are represented as dictionaries mapping landmark names (strings) to
coordinate tuples ``(x, y [, z])`` and an optional confidence score.

The canonical landmark names follow MediaPipe Pose 33-landmark topology:
  LEFT_HIP, RIGHT_HIP, LEFT_KNEE, RIGHT_KNEE, LEFT_ANKLE, RIGHT_ANKLE,
  LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_ELBOW, RIGHT_ELBOW,
  LEFT_WRIST, RIGHT_WRIST, NOSE, LEFT_EAR, RIGHT_EAR, etc.

``x`` and ``y`` are typically normalised to [0.0, 1.0] image coordinates.
``z`` is depth (optional); many 2-D poses omit it.

A missing landmark is represented as ``None`` or a dict entry with
``confidence`` below the configured minimum threshold.

Angle definitions
-----------------
All angles are computed **at the middle point B** of the triplet (A, B, C):
the angle is between vector B→A and vector B→C.  Unit: degrees.
Range: [0°, 180°] for unsigned; (-180°, 180°] for signed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Low-level data-quality thresholds
# ---------------------------------------------------------------------------

@dataclass
class QualityConfig:
    """Parameters controlling how pose data quality is assessed."""

    #: Landmark confidence below this value is treated as missing.
    min_confidence: float = 0.5

    #: Maximum allowed gap between consecutive frames (seconds).
    #: Gaps longer than this trigger filter resets and missing-data markers.
    max_frame_gap_s: float = 0.5

    #: Minimum number of valid frames required to attempt analysis.
    min_valid_frames: int = 10

    #: Minimum fraction of frames that must be valid for a rep to be trusted.
    min_valid_frame_fraction: float = 0.7


# ---------------------------------------------------------------------------
# Filtering / smoothing parameters
# ---------------------------------------------------------------------------

@dataclass
class FilterConfig:
    """Parameters for pose-coordinate and angle filtering."""

    #: Alpha for exponential moving average (EMA).  Range (0, 1].
    #: Closer to 1 → less smoothing; closer to 0 → heavier smoothing.
    ema_alpha: float = 0.3

    #: One-Euro filter minimum cutoff frequency (Hz).
    one_euro_min_cutoff: float = 1.0

    #: One-Euro filter speed coefficient (beta).
    one_euro_beta: float = 0.007

    #: One-Euro filter derivative cutoff frequency (Hz).
    one_euro_d_cutoff: float = 1.0

    #: Which filter to apply to joint angles after computing them.
    #: Allowed values: "ema", "one_euro", "none".
    angle_filter: str = "one_euro"


# ---------------------------------------------------------------------------
# Phase-detection thresholds (exercise-specific, example: squat)
# ---------------------------------------------------------------------------

@dataclass
class SquatPhaseConfig:
    """Thresholds for squat phase detection.

    All angle values are knee angles (degrees, measured at the knee joint).
    A fully extended standing knee is near 170–180°; a deep squat knee may
    be near 70–90°.
    """

    #: Knee angle above which a pose is considered "standing".
    standing_threshold_deg: float = 160.0

    #: Knee angle below which a pose is considered at the "bottom".
    bottom_threshold_deg: float = 100.0

    #: Hysteresis band (degrees) applied to prevent rapid state oscillation.
    hysteresis_deg: float = 8.0

    #: Minimum duration (seconds) a state must persist before transition.
    min_state_duration_s: float = 0.15

    #: Minimum angular velocity (deg/s) to be considered "moving".
    min_velocity_deg_s: float = 10.0

    #: Window (seconds) used to estimate instantaneous velocity.
    velocity_window_s: float = 0.2

    #: Minimum number of consecutive frames in a state before it is accepted.
    min_stable_frames: int = 3


# ---------------------------------------------------------------------------
# Repetition-counting thresholds
# ---------------------------------------------------------------------------

@dataclass
class SquatRepConfig:
    """Thresholds for squat repetition counting."""

    #: Minimum range of motion (knee angle change, degrees) for a valid rep.
    min_rom_deg: float = 40.0

    #: Minimum total duration of a rep cycle (seconds).
    min_rep_duration_s: float = 0.8

    #: Maximum total duration of a rep cycle (seconds) — sanity cap.
    max_rep_duration_s: float = 20.0

    #: Maximum allowable pause at the bottom before the cycle is rejected (s).
    max_bottom_pause_s: float = 5.0

    #: Angle jitter guard: ignore angle changes smaller than this (degrees).
    jitter_guard_deg: float = 3.0

    #: Factor by which two bottom angles must differ to count as a new rep.
    distinct_bottom_factor: float = 0.5  # not currently used in counting


# ---------------------------------------------------------------------------
# Technique-rule thresholds
# ---------------------------------------------------------------------------

@dataclass
class SquatRuleConfig:
    """Thresholds for squat technique-observation rules."""

    #: Knee angle at or above which range-of-motion is considered insufficient.
    shallow_squat_threshold_deg: float = 120.0

    #: Maximum acceptable left-right knee-angle difference (degrees).
    asymmetry_threshold_deg: float = 15.0

    #: Maximum acceptable torso-lean variation across reps (degrees).
    torso_variation_threshold_deg: float = 20.0

    #: Maximum acceptable rep-to-rep tempo variation (fraction of mean tempo).
    tempo_variation_threshold: float = 0.40  # 40 %

    #: Maximum acceptable rep-to-rep depth variation (degrees).
    depth_variation_threshold_deg: float = 20.0

    #: Knee-valgus flag: inward deviation threshold.
    #: Only flagged when horizontal landmark data supports the comparison.
    knee_valgus_threshold_ratio: float = 0.05  # fraction of hip width

    #: Minimum evidence quality required to issue a technique observation.
    min_evidence_quality: float = 0.5


# ---------------------------------------------------------------------------
# Composite exercise profile
# ---------------------------------------------------------------------------

@dataclass
class SquatProfile:
    """Complete configuration profile for squat analysis."""

    quality: QualityConfig = field(default_factory=QualityConfig)
    filter: FilterConfig = field(default_factory=FilterConfig)
    phase: SquatPhaseConfig = field(default_factory=SquatPhaseConfig)
    rep: SquatRepConfig = field(default_factory=SquatRepConfig)
    rule: SquatRuleConfig = field(default_factory=SquatRuleConfig)

    #: Human-readable description of this profile.
    description: str = (
        "Default squat profile — engineering defaults, unvalidated against "
        "labelled video datasets."
    )

    def override(self, **kwargs: Any) -> "SquatProfile":
        """Return a shallow copy with the given top-level fields overridden."""
        import dataclasses
        return dataclasses.replace(self, **kwargs)


# ---------------------------------------------------------------------------
# Registry of known exercise profiles
# ---------------------------------------------------------------------------

EXERCISE_PROFILES: dict[str, Any] = {
    "squat": SquatProfile(),
}


def get_profile(exercise: str) -> Any:
    """Return the default profile for *exercise*.

    Parameters
    ----------
    exercise:
        Exercise name (case-insensitive).

    Raises
    ------
    ValueError
        If the exercise is not recognised.
    """
    key = exercise.lower()
    if key not in EXERCISE_PROFILES:
        raise ValueError(
            f"Unknown exercise '{exercise}'. "
            f"Available: {list(EXERCISE_PROFILES)}"
        )
    return EXERCISE_PROFILES[key]
