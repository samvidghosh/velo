"""
exercise_rules.py — Configurable technique observation engine
=============================================================

Design principles
-----------------
* Each rule is an independent function that returns an ``Observation``.
* Rules return an ``UNCERTAIN`` status when relevant landmarks are missing
  or evidence quality is below the configured minimum.
* Rules **never** flag errors for absent or low-confidence landmarks.
* Rules **do not** make clinical or injury-related conclusions.
* All thresholds are configurable via ``SquatRuleConfig``.

Observation status
------------------
``VALID``     — measurement is within acceptable range (no issue detected).
``FLAGGED``   — measurement deviates from the configured reference range.
``UNCERTAIN`` — insufficient data to make a reliable determination.

Evidence quality
----------------
A float in [0, 1] reflecting how much of the required data was available and
above the confidence threshold.  Observations with quality below
``cfg.min_evidence_quality`` are automatically set to ``UNCERTAIN``.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

from .config import SquatRuleConfig
from .rep_counter import RepRecord


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ObservationStatus(Enum):
    VALID     = auto()
    FLAGGED   = auto()
    UNCERTAIN = auto()


class ObservationCategory(Enum):
    RANGE_OF_MOTION   = auto()
    TEMPO             = auto()
    DEPTH_CONSISTENCY = auto()
    TORSO_ANGLE       = auto()
    ASYMMETRY         = auto()
    KNEE_ALIGNMENT    = auto()
    DATA_QUALITY      = auto()
    COMPLETENESS      = auto()


# ---------------------------------------------------------------------------
# Observation dataclass
# ---------------------------------------------------------------------------

@dataclass
class Observation:
    """A single technique observation from a rule evaluation."""

    rule_id:          str
    category:         ObservationCategory
    status:           ObservationStatus
    measured_value:   float                    # NaN when unavailable
    reference_value:  float                    # threshold or target range midpoint
    reference_label:  str                      # human-readable description of reference
    explanation:      str                      # human-readable finding
    evidence_quality: float                    # [0, 1]
    rep_indices:      list[int] = field(default_factory=list)   # 1-based cycle indices
    timestamps:       list[float] = field(default_factory=list) # relevant timestamps


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _quality(available: int, required: int) -> float:
    if required == 0:
        return 1.0
    return min(1.0, available / required)


def _uncertain(
    rule_id: str,
    category: ObservationCategory,
    reason: str,
    quality: float = 0.0,
) -> Observation:
    return Observation(
        rule_id         = rule_id,
        category        = category,
        status          = ObservationStatus.UNCERTAIN,
        measured_value  = float("nan"),
        reference_value = float("nan"),
        reference_label = "n/a",
        explanation     = reason,
        evidence_quality= quality,
    )


# ---------------------------------------------------------------------------
# Individual rules
# ---------------------------------------------------------------------------

def rule_range_of_motion(
    records: list[RepRecord],
    cfg: SquatRuleConfig,
) -> Observation:
    """Observe whether the average range of motion is below the threshold.

    Only uses records that have a valid finite range-of-motion measurement.
    """
    rule_id  = "ROM_001"
    category = ObservationCategory.RANGE_OF_MOTION

    valid_roms = [
        r.range_of_motion
        for r in records
        if r.valid and math.isfinite(r.range_of_motion)
    ]
    quality = _quality(len(valid_roms), max(1, len(records)))

    if not valid_roms:
        return _uncertain(rule_id, category,
                          "No valid repetitions available for ROM assessment.",
                          quality)

    mean_rom    = statistics.mean(valid_roms)
    threshold   = cfg.shallow_squat_threshold_deg  # bottom angle, not ROM
    # Convert: a shallow squat is one where bottom angle stays too HIGH,
    # i.e. ROM is smaller than expected.  We flag small ROM indirectly by
    # looking at bottom angle via peak_angle.
    valid_peaks = [
        r.peak_angle
        for r in records
        if r.valid and math.isfinite(r.peak_angle)
    ]
    if not valid_peaks:
        return _uncertain(rule_id, category,
                          "No bottom-angle data available.", quality)

    mean_peak = statistics.mean(valid_peaks)

    if quality < cfg.min_evidence_quality:
        return _uncertain(rule_id, category,
                          f"Evidence quality too low ({quality:.2f}).", quality)

    if mean_peak >= threshold:
        return Observation(
            rule_id         = rule_id,
            category        = category,
            status          = ObservationStatus.FLAGGED,
            measured_value  = mean_peak,
            reference_value = threshold,
            reference_label = f"bottom angle < {threshold}° for adequate depth",
            explanation     = (
                f"Mean bottom angle {mean_peak:.1f}° is at or above the "
                f"{threshold}° shallow-squat threshold across "
                f"{len(valid_peaks)} rep(s).  Consider whether the target "
                f"depth is appropriate for the individual."
            ),
            evidence_quality= quality,
            rep_indices     = [r.index for r in records if r.valid],
        )

    return Observation(
        rule_id         = rule_id,
        category        = category,
        status          = ObservationStatus.VALID,
        measured_value  = mean_peak,
        reference_value = threshold,
        reference_label = f"bottom angle < {threshold}°",
        explanation     = f"Mean bottom angle {mean_peak:.1f}° meets depth threshold.",
        evidence_quality= quality,
        rep_indices     = [r.index for r in records if r.valid],
    )


def rule_tempo_consistency(
    records: list[RepRecord],
    cfg: SquatRuleConfig,
) -> Observation:
    """Observe whether rep tempos are consistent."""
    rule_id  = "TEMPO_001"
    category = ObservationCategory.TEMPO

    tempos  = [r.tempo for r in records if r.valid and math.isfinite(r.tempo) and r.tempo > 0]
    quality = _quality(len(tempos), max(1, len(records)))

    if len(tempos) < 2:
        return _uncertain(rule_id, category,
                          "Fewer than 2 valid reps — cannot assess tempo consistency.",
                          quality)

    if quality < cfg.min_evidence_quality:
        return _uncertain(rule_id, category,
                          f"Evidence quality too low ({quality:.2f}).", quality)

    mean_tempo = statistics.mean(tempos)
    stdev      = statistics.stdev(tempos)
    cv         = stdev / mean_tempo  # coefficient of variation

    if cv > cfg.tempo_variation_threshold:
        return Observation(
            rule_id         = rule_id,
            category        = category,
            status          = ObservationStatus.FLAGGED,
            measured_value  = cv,
            reference_value = cfg.tempo_variation_threshold,
            reference_label = f"CV ≤ {cfg.tempo_variation_threshold:.0%}",
            explanation     = (
                f"Tempo coefficient of variation {cv:.0%} exceeds "
                f"{cfg.tempo_variation_threshold:.0%} threshold.  "
                f"Mean={mean_tempo:.1f}s, SD={stdev:.1f}s across {len(tempos)} reps."
            ),
            evidence_quality= quality,
        )

    return Observation(
        rule_id         = rule_id,
        category        = category,
        status          = ObservationStatus.VALID,
        measured_value  = cv,
        reference_value = cfg.tempo_variation_threshold,
        reference_label = f"CV ≤ {cfg.tempo_variation_threshold:.0%}",
        explanation     = (
            f"Tempo variation {cv:.0%} within acceptable range "
            f"(mean={mean_tempo:.1f}s)."
        ),
        evidence_quality= quality,
    )


def rule_depth_consistency(
    records: list[RepRecord],
    cfg: SquatRuleConfig,
) -> Observation:
    """Observe whether bottom-angle depth is consistent across repetitions."""
    rule_id  = "DEPTH_001"
    category = ObservationCategory.DEPTH_CONSISTENCY

    depths  = [r.peak_angle for r in records if r.valid and math.isfinite(r.peak_angle)]
    quality = _quality(len(depths), max(1, len(records)))

    if len(depths) < 2:
        return _uncertain(rule_id, category,
                          "Fewer than 2 valid reps — cannot assess depth consistency.",
                          quality)

    if quality < cfg.min_evidence_quality:
        return _uncertain(rule_id, category, f"Evidence quality too low ({quality:.2f}).", quality)

    depth_range = max(depths) - min(depths)

    if depth_range > cfg.depth_variation_threshold_deg:
        return Observation(
            rule_id         = rule_id,
            category        = category,
            status          = ObservationStatus.FLAGGED,
            measured_value  = depth_range,
            reference_value = cfg.depth_variation_threshold_deg,
            reference_label = f"depth variation ≤ {cfg.depth_variation_threshold_deg}°",
            explanation     = (
                f"Bottom-angle range {depth_range:.1f}° across {len(depths)} reps "
                f"exceeds the {cfg.depth_variation_threshold_deg}° consistency threshold."
            ),
            evidence_quality= quality,
        )

    return Observation(
        rule_id         = rule_id,
        category        = category,
        status          = ObservationStatus.VALID,
        measured_value  = depth_range,
        reference_value = cfg.depth_variation_threshold_deg,
        reference_label = f"depth variation ≤ {cfg.depth_variation_threshold_deg}°",
        explanation     = f"Bottom-angle depth variation {depth_range:.1f}° is consistent.",
        evidence_quality= quality,
    )


def rule_left_right_asymmetry(
    knee_angles_left: list[float],
    knee_angles_right: list[float],
    timestamps: list[float],
    cfg: SquatRuleConfig,
) -> Observation:
    """Observe left-right knee-angle asymmetry over the session.

    Only frames where both sides have finite angles are used.
    """
    rule_id  = "ASYM_001"
    category = ObservationCategory.ASYMMETRY

    paired = [
        (l, r, t)
        for l, r, t in zip(knee_angles_left, knee_angles_right, timestamps)
        if math.isfinite(l) and math.isfinite(r)
    ]
    quality = _quality(len(paired), max(1, len(timestamps)))

    if not paired:
        return _uncertain(rule_id, category,
                          "No frames with bilateral knee-angle data.", quality)

    if quality < cfg.min_evidence_quality:
        return _uncertain(rule_id, category, f"Evidence quality too low ({quality:.2f}).", quality)

    diffs     = [abs(l - r) for l, r, _ in paired]
    mean_diff = statistics.mean(diffs)

    if mean_diff > cfg.asymmetry_threshold_deg:
        worst_frame_idx = diffs.index(max(diffs))
        worst_ts = paired[worst_frame_idx][2]
        return Observation(
            rule_id         = rule_id,
            category        = category,
            status          = ObservationStatus.FLAGGED,
            measured_value  = mean_diff,
            reference_value = cfg.asymmetry_threshold_deg,
            reference_label = f"L–R difference ≤ {cfg.asymmetry_threshold_deg}°",
            explanation     = (
                f"Mean left-right knee angle difference {mean_diff:.1f}° exceeds "
                f"{cfg.asymmetry_threshold_deg}° threshold over {len(paired)} frames."
            ),
            evidence_quality= quality,
            timestamps      = [worst_ts],
        )

    return Observation(
        rule_id         = rule_id,
        category        = category,
        status          = ObservationStatus.VALID,
        measured_value  = mean_diff,
        reference_value = cfg.asymmetry_threshold_deg,
        reference_label = f"L–R difference ≤ {cfg.asymmetry_threshold_deg}°",
        explanation     = f"Left-right knee symmetry acceptable ({mean_diff:.1f}°).",
        evidence_quality= quality,
    )


def rule_torso_variation(
    torso_angles: list[float],
    timestamps: list[float],
    records: list[RepRecord],
    cfg: SquatRuleConfig,
) -> Observation:
    """Observe variation in torso lean angle across the session."""
    rule_id  = "TORSO_001"
    category = ObservationCategory.TORSO_ANGLE

    valid_angles = [a for a in torso_angles if math.isfinite(a)]
    quality      = _quality(len(valid_angles), max(1, len(torso_angles)))

    if len(valid_angles) < 2:
        return _uncertain(rule_id, category,
                          "Insufficient torso-angle data (requires bilateral shoulder +hip landmarks).",
                          quality)

    if quality < cfg.min_evidence_quality:
        return _uncertain(rule_id, category, f"Evidence quality too low ({quality:.2f}).", quality)

    angle_range = max(valid_angles) - min(valid_angles)

    if angle_range > cfg.torso_variation_threshold_deg:
        return Observation(
            rule_id         = rule_id,
            category        = category,
            status          = ObservationStatus.FLAGGED,
            measured_value  = angle_range,
            reference_value = cfg.torso_variation_threshold_deg,
            reference_label = f"torso variation ≤ {cfg.torso_variation_threshold_deg}°",
            explanation     = (
                f"Observable torso lean varies by {angle_range:.1f}° — this may "
                f"reflect intentional technique or camera-induced perspective effects.  "
                f"Threshold: {cfg.torso_variation_threshold_deg}°."
            ),
            evidence_quality= quality,
        )

    return Observation(
        rule_id         = rule_id,
        category        = category,
        status          = ObservationStatus.VALID,
        measured_value  = angle_range,
        reference_value = cfg.torso_variation_threshold_deg,
        reference_label = f"torso variation ≤ {cfg.torso_variation_threshold_deg}°",
        explanation     = f"Torso lean variation {angle_range:.1f}° within range.",
        evidence_quality= quality,
    )


def rule_incomplete_reps(
    records: list[RepRecord],
    cfg: SquatRuleConfig,
) -> Observation:
    """Observe whether incomplete movement cycles were detected."""
    rule_id  = "COMP_001"
    category = ObservationCategory.COMPLETENESS

    total    = len(records)
    invalid  = [r for r in records if not r.valid]
    quality  = 1.0 if total > 0 else 0.0

    if total == 0:
        return _uncertain(rule_id, category,
                          "No movement cycles detected.", quality)

    if invalid:
        return Observation(
            rule_id         = rule_id,
            category        = category,
            status          = ObservationStatus.FLAGGED,
            measured_value  = float(len(invalid)),
            reference_value = 0.0,
            reference_label = "0 incomplete cycles",
            explanation     = (
                f"{len(invalid)} of {total} detected movement cycle(s) did not "
                f"meet counting criteria: " +
                "; ".join(r.rejection_reasons[0] for r in invalid if r.rejection_reasons)
            ),
            evidence_quality= quality,
            rep_indices     = [r.index for r in invalid],
        )

    return Observation(
        rule_id         = rule_id,
        category        = category,
        status          = ObservationStatus.VALID,
        measured_value  = 0.0,
        reference_value = 0.0,
        reference_label = "0 incomplete cycles",
        explanation     = f"All {total} detected cycle(s) met counting criteria.",
        evidence_quality= quality,
    )


def rule_data_quality(
    frame_results: list[Any],        # list of FrameResult from preprocessing
    cfg: SquatRuleConfig,
) -> Observation:
    """Observe overall data quality across the session."""
    rule_id  = "DATA_001"
    category = ObservationCategory.DATA_QUALITY

    total = len(frame_results)
    if total == 0:
        return _uncertain(rule_id, category, "No frame data available.", 0.0)

    valid  = sum(1 for f in frame_results if getattr(f, "valid", False))
    frac   = valid / total
    quality = frac

    threshold = 0.7  # a reasonable floor; not in cfg currently

    if frac < threshold:
        return Observation(
            rule_id         = rule_id,
            category        = category,
            status          = ObservationStatus.FLAGGED,
            measured_value  = frac,
            reference_value = threshold,
            reference_label = f"≥ {threshold:.0%} valid frames",
            explanation     = (
                f"Only {frac:.0%} of frames ({valid}/{total}) had valid pose data.  "
                f"Results may be unreliable."
            ),
            evidence_quality= quality,
        )

    return Observation(
        rule_id         = rule_id,
        category        = category,
        status          = ObservationStatus.VALID,
        measured_value  = frac,
        reference_value = threshold,
        reference_label = f"≥ {threshold:.0%} valid frames",
        explanation     = f"Data quality acceptable: {frac:.0%} valid frames.",
        evidence_quality= quality,
    )


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------

class SquatRuleEngine:
    """Apply all squat technique rules and collect observations.

    Parameters
    ----------
    cfg:
        Technique rule thresholds.
    """

    def __init__(self, cfg: SquatRuleConfig = SquatRuleConfig()) -> None:
        self._cfg = cfg

    def evaluate(
        self,
        records: list[RepRecord],
        frame_results: list[Any],
        angle_series: dict[str, list[float]],
        timestamps: list[float],
    ) -> list[Observation]:
        """Run all rules and return a list of Observation objects.

        Parameters
        ----------
        records:
            Per-rep records from the counter.
        frame_results:
            FrameResult list from the preprocessor.
        angle_series:
            Dict of joint-name → time series (one float per frame).
        timestamps:
            Timestamps aligned with *angle_series*.
        """
        obs: list[Observation] = []
        cfg = self._cfg

        obs.append(rule_range_of_motion(records, cfg))
        obs.append(rule_tempo_consistency(records, cfg))
        obs.append(rule_depth_consistency(records, cfg))
        obs.append(rule_incomplete_reps(records, cfg))
        obs.append(rule_data_quality(frame_results, cfg))

        left_knee  = angle_series.get("LEFT_KNEE", [])
        right_knee = angle_series.get("RIGHT_KNEE", [])
        torso      = angle_series.get("TORSO", [])

        if left_knee and right_knee:
            obs.append(rule_left_right_asymmetry(
                left_knee, right_knee, timestamps, cfg
            ))

        if torso:
            obs.append(rule_torso_variation(torso, timestamps, records, cfg))

        return obs
