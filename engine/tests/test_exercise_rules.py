"""
test_exercise_rules.py — Tests for engine.exercise_rules
"""
from __future__ import annotations

import math
import pytest

from engine.exercise_rules import (
    Observation,
    ObservationStatus,
    SquatRuleEngine,
    rule_data_quality,
    rule_depth_consistency,
    rule_incomplete_reps,
    rule_left_right_asymmetry,
    rule_range_of_motion,
    rule_tempo_consistency,
    rule_torso_variation,
)
from engine.config import SquatRuleConfig
from engine.rep_counter import RepRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(
    index: int = 1,
    valid: bool = True,
    peak_angle: float = 90.0,
    top_angle: float = 170.0,
    tempo: float = 3.0,
    rejection_reasons: list[str] | None = None,
) -> RepRecord:
    rom = top_angle - peak_angle
    return RepRecord(
        index             = index,
        start_time        = (index - 1) * tempo,
        bottom_time       = (index - 1) * tempo + tempo * 0.5,
        end_time          = index * tempo,
        peak_angle        = peak_angle,
        top_angle         = top_angle,
        range_of_motion   = rom,
        tempo             = tempo,
        valid             = valid,
        rejection_reasons = rejection_reasons or [],
        data_quality      = 1.0,
    )


class _FakeFrame:
    def __init__(self, valid: bool = True):
        self.valid = valid


def _default_cfg(**kwargs) -> SquatRuleConfig:
    return SquatRuleConfig(**kwargs)


# ---------------------------------------------------------------------------
# rule_range_of_motion
# ---------------------------------------------------------------------------

class TestRuleRangeOfMotion:
    def test_adequate_depth_valid(self):
        records = [_make_record(i+1, peak_angle=95.0) for i in range(3)]
        cfg     = _default_cfg(shallow_squat_threshold_deg=120.0)
        obs     = rule_range_of_motion(records, cfg)
        assert obs.status == ObservationStatus.VALID

    def test_shallow_squat_flagged(self):
        records = [_make_record(i+1, peak_angle=135.0) for i in range(3)]
        cfg     = _default_cfg(shallow_squat_threshold_deg=120.0)
        obs     = rule_range_of_motion(records, cfg)
        assert obs.status == ObservationStatus.FLAGGED

    def test_no_valid_reps_uncertain(self):
        records = [_make_record(1, valid=False)]
        obs     = rule_range_of_motion(records, _default_cfg())
        assert obs.status == ObservationStatus.UNCERTAIN

    def test_empty_records_uncertain(self):
        obs = rule_range_of_motion([], _default_cfg())
        assert obs.status == ObservationStatus.UNCERTAIN

    def test_never_flags_missing_landmarks(self):
        """If peak_angle is NaN (landmark missing), result is uncertain, not flagged."""
        records = [_make_record(1, peak_angle=float("nan"))]
        obs     = rule_range_of_motion(records, _default_cfg())
        assert obs.status in (ObservationStatus.UNCERTAIN, ObservationStatus.VALID)
        assert obs.status != ObservationStatus.FLAGGED


# ---------------------------------------------------------------------------
# rule_tempo_consistency
# ---------------------------------------------------------------------------

class TestRuleTempoConsistency:
    def test_consistent_tempo_valid(self):
        records = [_make_record(i+1, tempo=3.0) for i in range(4)]
        obs     = rule_tempo_consistency(records, _default_cfg())
        assert obs.status == ObservationStatus.VALID

    def test_inconsistent_tempo_flagged(self):
        records = [
            _make_record(1, tempo=2.0),
            _make_record(2, tempo=5.0),
            _make_record(3, tempo=1.0),
            _make_record(4, tempo=6.0),
        ]
        cfg = _default_cfg(tempo_variation_threshold=0.1)
        obs = rule_tempo_consistency(records, cfg)
        assert obs.status == ObservationStatus.FLAGGED

    def test_single_rep_uncertain(self):
        records = [_make_record(1)]
        obs     = rule_tempo_consistency(records, _default_cfg())
        assert obs.status == ObservationStatus.UNCERTAIN

    def test_no_reps_uncertain(self):
        obs = rule_tempo_consistency([], _default_cfg())
        assert obs.status == ObservationStatus.UNCERTAIN


# ---------------------------------------------------------------------------
# rule_depth_consistency
# ---------------------------------------------------------------------------

class TestRuleDepthConsistency:
    def test_consistent_depth_valid(self):
        records = [_make_record(i+1, peak_angle=90.0) for i in range(3)]
        obs     = rule_depth_consistency(records, _default_cfg())
        assert obs.status == ObservationStatus.VALID

    def test_inconsistent_depth_flagged(self):
        records = [
            _make_record(1, peak_angle=85.0),
            _make_record(2, peak_angle=130.0),  # 45° difference
        ]
        cfg = _default_cfg(depth_variation_threshold_deg=20.0)
        obs = rule_depth_consistency(records, cfg)
        assert obs.status == ObservationStatus.FLAGGED

    def test_single_rep_uncertain(self):
        obs = rule_depth_consistency([_make_record(1)], _default_cfg())
        assert obs.status == ObservationStatus.UNCERTAIN


# ---------------------------------------------------------------------------
# rule_left_right_asymmetry
# ---------------------------------------------------------------------------

class TestRuleAsymmetry:
    def test_symmetric_valid(self):
        n   = 30
        ts  = [i * 0.033 for i in range(n)]
        l   = [90.0] * n
        r   = [90.0] * n
        obs = rule_left_right_asymmetry(l, r, ts, _default_cfg())
        assert obs.status == ObservationStatus.VALID

    def test_asymmetric_flagged(self):
        n   = 30
        ts  = [i * 0.033 for i in range(n)]
        l   = [90.0] * n
        r   = [115.0] * n   # 25° difference
        cfg = _default_cfg(asymmetry_threshold_deg=15.0)
        obs = rule_left_right_asymmetry(l, r, ts, cfg)
        assert obs.status == ObservationStatus.FLAGGED

    def test_all_nan_angles_uncertain(self):
        n   = 10
        ts  = [i * 0.033 for i in range(n)]
        l   = [float("nan")] * n
        r   = [float("nan")] * n
        obs = rule_left_right_asymmetry(l, r, ts, _default_cfg())
        assert obs.status == ObservationStatus.UNCERTAIN

    def test_no_flag_when_all_missing(self):
        """When both sides are NaN, observation must NOT be FLAGGED."""
        n   = 10
        ts  = [i * 0.033 for i in range(n)]
        l   = [float("nan")] * n
        r   = [float("nan")] * n
        obs = rule_left_right_asymmetry(l, r, ts, _default_cfg())
        assert obs.status != ObservationStatus.FLAGGED


# ---------------------------------------------------------------------------
# rule_torso_variation
# ---------------------------------------------------------------------------

class TestRuleTorsoVariation:
    def test_stable_torso_valid(self):
        n       = 30
        ts      = [i * 0.033 for i in range(n)]
        angles  = [15.0] * n
        records = [_make_record(1)]
        obs     = rule_torso_variation(angles, ts, records, _default_cfg())
        assert obs.status == ObservationStatus.VALID

    def test_varying_torso_flagged(self):
        n       = 30
        ts      = [i * 0.033 for i in range(n)]
        angles  = [10.0 if i < 15 else 40.0 for i in range(n)]  # 30° variation
        records = [_make_record(1)]
        cfg     = _default_cfg(torso_variation_threshold_deg=20.0)
        obs     = rule_torso_variation(angles, ts, records, cfg)
        assert obs.status == ObservationStatus.FLAGGED

    def test_all_nan_uncertain(self):
        n       = 10
        ts      = [i * 0.033 for i in range(n)]
        angles  = [float("nan")] * n
        obs     = rule_torso_variation(angles, ts, [], _default_cfg())
        assert obs.status == ObservationStatus.UNCERTAIN


# ---------------------------------------------------------------------------
# rule_incomplete_reps
# ---------------------------------------------------------------------------

class TestRuleIncompleteReps:
    def test_all_valid_no_flag(self):
        records = [_make_record(i+1, valid=True) for i in range(3)]
        obs     = rule_incomplete_reps(records, _default_cfg())
        assert obs.status == ObservationStatus.VALID

    def test_some_invalid_flagged(self):
        records = [
            _make_record(1, valid=True),
            _make_record(2, valid=False, rejection_reasons=["Too short"]),
        ]
        obs = rule_incomplete_reps(records, _default_cfg())
        assert obs.status == ObservationStatus.FLAGGED

    def test_no_cycles_uncertain(self):
        obs = rule_incomplete_reps([], _default_cfg())
        assert obs.status == ObservationStatus.UNCERTAIN


# ---------------------------------------------------------------------------
# rule_data_quality
# ---------------------------------------------------------------------------

class TestRuleDataQuality:
    def test_all_valid_frames(self):
        frames = [_FakeFrame(valid=True) for _ in range(100)]
        obs    = rule_data_quality(frames, _default_cfg())
        assert obs.status == ObservationStatus.VALID

    def test_mostly_invalid_flagged(self):
        frames = [_FakeFrame(valid=i % 5 == 0) for i in range(100)]
        obs    = rule_data_quality(frames, _default_cfg())
        assert obs.status == ObservationStatus.FLAGGED

    def test_no_frames_uncertain(self):
        obs = rule_data_quality([], _default_cfg())
        assert obs.status == ObservationStatus.UNCERTAIN


# ---------------------------------------------------------------------------
# SquatRuleEngine — integration
# ---------------------------------------------------------------------------

class TestSquatRuleEngine:
    def test_evaluate_returns_list(self):
        engine  = SquatRuleEngine()
        records = [_make_record(i+1) for i in range(3)]
        frames  = [_FakeFrame(True) for _ in range(90)]
        n       = 90
        ts      = [i * 0.033 for i in range(n)]
        angle_series = {
            "LEFT_KNEE":  [90.0 + i * 0.5 % 80 for i in range(n)],
            "RIGHT_KNEE": [90.0 + i * 0.5 % 80 for i in range(n)],
            "TORSO":      [15.0] * n,
        }
        obs = engine.evaluate(records, frames, angle_series, ts)
        assert isinstance(obs, list)
        assert len(obs) > 0
        for o in obs:
            assert isinstance(o, Observation)
            assert math.isfinite(o.evidence_quality) or math.isnan(o.evidence_quality)

    def test_threshold_config_respected(self):
        """With very tight thresholds, rules that would otherwise pass should flag."""
        cfg = SquatRuleConfig(
            asymmetry_threshold_deg=1.0,   # extreme tightness
            min_evidence_quality=0.0,
        )
        engine  = SquatRuleEngine(cfg=cfg)
        records = [_make_record(i+1) for i in range(3)]
        frames  = [_FakeFrame(True) for _ in range(30)]
        n       = 30
        ts      = [i * 0.033 for i in range(n)]
        angle_series = {
            "LEFT_KNEE":  [90.0] * n,
            "RIGHT_KNEE": [100.0] * n,  # 10° asymmetry > 1.0° threshold
        }
        obs = engine.evaluate(records, frames, angle_series, ts)
        asym_obs = [o for o in obs if o.rule_id == "ASYM_001"]
        assert asym_obs
        assert asym_obs[0].status == ObservationStatus.FLAGGED
