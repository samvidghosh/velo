"""
analyzer.py — Top-level analysis orchestrator
==============================================

Public API
----------
``analyze_movement(frames, exercise, config)``

    Accepts a list of frame dictionaries and an exercise name, runs the full
    pipeline, and returns an ``AnalysisResult``.

Pipeline stages
---------------
1. Input validation
2. Pose preprocessing + filtering
3. Joint-angle extraction (part of preprocessing)
4. Phase detection (angle time series → PhaseEvent list)
5. Repetition counting (PhaseEvent list → RepRecord list)
6. Technique rules (RepRecords + angle series → Observation list)
7. Result assembly

No HTTP endpoints, web frameworks, file upload, authentication, or database
logic is included here or anywhere in this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

from .config import SquatProfile, get_profile
from .exercise_rules import Observation, ObservationStatus, SquatRuleEngine
from .phase_detector import (
    PhaseEvent,
    PhaseInterval,
    SquatPhaseDetector,
    build_phase_timeline,
)
from .preprocessing import FrameResult, PosePreprocessor
from .rep_counter import CounterResult, RepRecord, SquatRepCounter


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DataQualitySummary:
    total_frames:        int
    valid_frames:        int
    valid_fraction:      float
    gap_events:          int       # frames where a long gap was detected
    low_confidence_frames: int     # frames filtered for confidence


@dataclass
class AnalysisResult:
    """Complete output of one analysis run."""

    exercise:            str
    config_description:  str

    # Counting summary
    total_cycles:        int
    accepted_reps:       int

    # Per-repetition detail
    reps:                list[RepRecord]

    # Time series
    timestamps:          list[float]
    angle_series:        dict[str, list[float]]   # joint → [angle_per_frame]

    # Phase data
    phase_events:        list[PhaseEvent]
    phase_timeline:      list[PhaseInterval]

    # Technique observations
    observations:        list[Observation]

    # Quality
    data_quality:        DataQualitySummary
    uncertainty_flags:   list[str]
    warnings:            list[str]

    # ----------------------------------------------------------------
    # Convenience accessors
    # ----------------------------------------------------------------

    @property
    def flagged_observations(self) -> list[Observation]:
        return [o for o in self.observations if o.status == ObservationStatus.FLAGGED]

    @property
    def uncertain_observations(self) -> list[Observation]:
        return [o for o in self.observations if o.status == ObservationStatus.UNCERTAIN]

    def summary_text(self) -> str:
        """Return a compact human-readable summary string."""
        lines = [
            f"Exercise:     {self.exercise}",
            f"Valid reps:   {self.accepted_reps} / {self.total_cycles} cycles",
            f"Data quality: {self.data_quality.valid_fraction:.0%} valid frames",
            f"Flagged:      {len(self.flagged_observations)} observation(s)",
            f"Uncertain:    {len(self.uncertain_observations)} observation(s)",
        ]
        if self.warnings:
            lines.append(f"Warnings:     {len(self.warnings)}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Frame input schema
# ---------------------------------------------------------------------------

def _validate_frame_input(frames: list[dict[str, Any]]) -> list[str]:
    """Validate the top-level list of frame dicts.

    Returns a (possibly empty) list of warning strings.
    Raises ValueError for unrecoverable structural problems.
    """
    if not isinstance(frames, list):
        raise ValueError("'frames' must be a list of frame dictionaries.")
    if len(frames) == 0:
        raise ValueError("'frames' is empty — no data to analyse.")

    warnings: list[str] = []
    for i, f in enumerate(frames):
        if not isinstance(f, dict):
            raise ValueError(f"Frame {i} is not a dictionary.")
        if "timestamp" not in f:
            raise ValueError(f"Frame {i} is missing the 'timestamp' key.")
        if "pose" not in f:
            raise ValueError(f"Frame {i} is missing the 'pose' key.")
        ts = f["timestamp"]
        if not isinstance(ts, (int, float)) or not math.isfinite(ts):
            warnings.append(f"Frame {i}: non-finite timestamp {ts!r}.")

    return warnings


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def analyze_movement(
    frames: list[dict[str, Any]],
    exercise: str = "squat",
    config: Optional[Any] = None,
) -> AnalysisResult:
    """Analyse a sequence of pose frames for a given exercise.

    Parameters
    ----------
    frames:
        List of frame dictionaries, each with keys:
        * ``"timestamp"`` — float, seconds
        * ``"pose"``      — dict of landmark_name → coordinate/entry
    exercise:
        Exercise name.  Currently only ``"squat"`` is supported.
    config:
        Optional :class:`SquatProfile` (or compatible dataclass) to override
        defaults.  Pass ``None`` to use the default profile.

    Returns
    -------
    AnalysisResult
        Complete analysis output.

    Raises
    ------
    ValueError
        On invalid input structure.
    """
    # ----------------------------------------------------------------
    # 1. Load profile
    # ----------------------------------------------------------------
    profile: SquatProfile = config if config is not None else get_profile(exercise)

    # ----------------------------------------------------------------
    # 2. Input validation
    # ----------------------------------------------------------------
    warnings = _validate_frame_input(frames)

    timestamps = [float(f["timestamp"]) for f in frames]
    raw_poses  = [f["pose"] for f in frames]

    # ----------------------------------------------------------------
    # 3. Preprocessing: validation + filtering + angle extraction
    # ----------------------------------------------------------------
    preprocessor = PosePreprocessor(
        filter_cfg  = profile.filter,
        quality_cfg = profile.quality,
    )
    frame_results: list[FrameResult] = preprocessor.process_sequence(timestamps, raw_poses)
    warnings.extend(
        w for fr in frame_results for w in fr.warnings
    )

    # Build per-joint angle time series aligned to timestamps
    all_joints = set()
    for fr in frame_results:
        all_joints.update(fr.angles.keys())

    angle_series: dict[str, list[float]] = {j: [] for j in all_joints}
    valid_timestamps: list[float] = []

    for fr in frame_results:
        valid_timestamps.append(fr.timestamp)
        for joint in all_joints:
            angle_series[joint].append(fr.angles.get(joint, float("nan")))

    # ----------------------------------------------------------------
    # 4. Phase detection
    # ----------------------------------------------------------------
    # Use the primary angle: prefer LEFT_KNEE, fall back to RIGHT_KNEE
    left_knee_series  = angle_series.get("LEFT_KNEE", [])
    right_knee_series = angle_series.get("RIGHT_KNEE", [])

    if left_knee_series:
        primary_angles = left_knee_series
    elif right_knee_series:
        primary_angles = right_knee_series
        warnings.append("LEFT_KNEE unavailable — using RIGHT_KNEE for phase detection.")
    else:
        primary_angles = [float("nan")] * len(valid_timestamps)
        warnings.append("No knee-angle data available; phase detection will be UNKNOWN.")

    detector = SquatPhaseDetector(cfg=profile.phase)
    phase_events: list[PhaseEvent] = detector.process_sequence(
        primary_angles, valid_timestamps
    )
    phase_timeline = build_phase_timeline(phase_events)

    # ----------------------------------------------------------------
    # 5. Repetition counting
    # ----------------------------------------------------------------
    counter = SquatRepCounter(cfg=profile.rep)
    counter_result: CounterResult = counter.process_sequence(phase_events)
    warnings.extend(counter_result.warnings)

    # ----------------------------------------------------------------
    # 6. Technique rules
    # ----------------------------------------------------------------
    rule_engine = SquatRuleEngine(cfg=profile.rule)
    observations = rule_engine.evaluate(
        records       = counter_result.records,
        frame_results = frame_results,
        angle_series  = angle_series,
        timestamps    = valid_timestamps,
    )

    # ----------------------------------------------------------------
    # 7. Data quality summary
    # ----------------------------------------------------------------
    gap_events = sum(1 for fr in frame_results if fr.gap_before)
    low_conf   = sum(1 for fr in frame_results if not fr.valid)

    quality = DataQualitySummary(
        total_frames         = len(frame_results),
        valid_frames         = sum(1 for fr in frame_results if fr.valid),
        valid_fraction       = (
            sum(1 for fr in frame_results if fr.valid) / len(frame_results)
            if frame_results else 0.0
        ),
        gap_events           = gap_events,
        low_confidence_frames= low_conf,
    )

    # ----------------------------------------------------------------
    # 8. Uncertainty flags
    # ----------------------------------------------------------------
    uncertainty_flags: list[str] = []
    if quality.valid_fraction < profile.quality.min_valid_frame_fraction:
        uncertainty_flags.append(
            f"Valid-frame fraction {quality.valid_fraction:.0%} is below "
            f"the {profile.quality.min_valid_frame_fraction:.0%} minimum — "
            f"results are unreliable."
        )
    if gap_events > 0:
        uncertainty_flags.append(
            f"{gap_events} frame gap(s) detected; filter state was reset."
        )
    uncertain_reps = [r for r in counter_result.records if r.uncertain]
    if uncertain_reps:
        uncertainty_flags.append(
            f"{len(uncertain_reps)} rep cycle(s) had data gaps and may be misclassified."
        )

    # ----------------------------------------------------------------
    # 9. Assemble result
    # ----------------------------------------------------------------
    return AnalysisResult(
        exercise            = exercise,
        config_description  = profile.description,
        total_cycles        = counter_result.total_cycles,
        accepted_reps       = counter_result.accepted_reps,
        reps                = counter_result.records,
        timestamps          = valid_timestamps,
        angle_series        = angle_series,
        phase_events        = phase_events,
        phase_timeline      = phase_timeline,
        observations        = observations,
        data_quality        = quality,
        uncertainty_flags   = uncertainty_flags,
        warnings            = warnings,
    )
