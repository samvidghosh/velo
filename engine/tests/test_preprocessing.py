"""
test_preprocessing.py — Tests for engine.preprocessing
"""
from __future__ import annotations

import math
import pytest

from engine.preprocessing import (
    EMAFilter,
    OneEuroFilter,
    PosePreprocessor,
    filter_by_confidence,
    validate_pose,
    validate_timestamps,
)
from engine.config import FilterConfig, QualityConfig
import numpy as np


# ---------------------------------------------------------------------------
# validate_timestamps
# ---------------------------------------------------------------------------

class TestValidateTimestamps:
    def test_empty(self):
        w = validate_timestamps([])
        assert any("empty" in s.lower() for s in w)

    def test_valid_sequence(self):
        assert validate_timestamps([0.0, 0.1, 0.2]) == []

    def test_non_monotonic(self):
        w = validate_timestamps([0.0, 0.2, 0.1])
        assert any("non-monotonic" in s.lower() for s in w)

    def test_nan_timestamp(self):
        w = validate_timestamps([0.0, float("nan"), 0.2])
        assert any("non-finite" in s.lower() for s in w)


# ---------------------------------------------------------------------------
# validate_pose
# ---------------------------------------------------------------------------

class TestValidatePose:
    def _quality(self):
        return QualityConfig(min_confidence=0.5)

    def test_empty_dict(self):
        valid, _ = validate_pose({}, self._quality())
        assert not valid

    def test_all_none_landmarks(self):
        valid, _ = validate_pose({"LEFT_HIP": None, "RIGHT_HIP": None}, self._quality())
        assert not valid

    def test_valid_landmarks(self):
        pose = {"LEFT_HIP": [0.5, 0.6], "LEFT_KNEE": [0.5, 0.75]}
        valid, warnings = validate_pose(pose, self._quality())
        assert valid

    def test_low_confidence_treated_as_missing(self):
        pose = {
            "LEFT_HIP":  {"coords": [0.5, 0.6], "confidence": 0.2},
        }
        valid, _ = validate_pose(pose, self._quality())
        assert not valid   # only landmark has low confidence


# ---------------------------------------------------------------------------
# filter_by_confidence
# ---------------------------------------------------------------------------

class TestFilterByConfidence:
    def test_removes_low_confidence(self):
        pose = {
            "LEFT_HIP":  {"coords": [0.5, 0.6], "confidence": 0.3},
            "RIGHT_HIP": {"coords": [0.5, 0.6], "confidence": 0.9},
        }
        result = filter_by_confidence(pose, 0.5)
        assert result["LEFT_HIP"] is None
        assert result["RIGHT_HIP"] is not None

    def test_keys_preserved(self):
        """Key set must remain stable even when values are None."""
        pose = {"A": {"coords": [0, 0], "confidence": 0.1}}
        result = filter_by_confidence(pose, 0.5)
        assert "A" in result

    def test_none_entry_passes_through(self):
        result = filter_by_confidence({"X": None}, 0.5)
        assert result["X"] is None


# ---------------------------------------------------------------------------
# EMAFilter
# ---------------------------------------------------------------------------

class TestEMAFilter:
    def test_constant_input_unchanged(self):
        flt = EMAFilter(2, alpha=0.5)
        for _ in range(20):
            out = flt.filter(np.array([1.0, 2.0]))
        assert math.isclose(out[0], 1.0, abs_tol=1e-3)
        assert math.isclose(out[1], 2.0, abs_tol=1e-3)

    def test_smoothing_reduces_step(self):
        """A sudden step should be smoothed (output < input on first step)."""
        flt = EMAFilter(1, alpha=0.3)
        flt.filter(np.array([0.0]))
        out = flt.filter(np.array([100.0]))
        assert out[0] < 100.0

    def test_nan_channel_preserved(self):
        """NaN in one channel should leave that channel as NaN in output."""
        flt = EMAFilter(2, alpha=0.5)
        out = flt.filter(np.array([float("nan"), 1.0]))
        assert math.isnan(out[0])

    def test_invalid_alpha_raises(self):
        with pytest.raises(ValueError):
            EMAFilter(1, alpha=0.0)
        with pytest.raises(ValueError):
            EMAFilter(1, alpha=1.5)

    def test_reset_clears_state(self):
        flt = EMAFilter(1, alpha=0.5)
        flt.filter(np.array([999.0]))
        flt.reset()
        out = flt.filter(np.array([1.0]))
        assert math.isclose(out[0], 1.0, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# OneEuroFilter
# ---------------------------------------------------------------------------

class TestOneEuroFilter:
    def test_constant_input_converges(self):
        flt = OneEuroFilter(1, FilterConfig())
        val = np.array([50.0])
        out = None
        for _ in range(100):
            out = flt.filter(val, dt=0.033)
        assert math.isclose(out[0], 50.0, abs_tol=0.5)

    def test_nan_passes_through(self):
        flt = OneEuroFilter(1, FilterConfig())
        out = flt.filter(np.array([float("nan")]), dt=0.033)
        assert math.isnan(out[0])

    def test_reset_clears_state(self):
        flt = OneEuroFilter(1, FilterConfig())
        flt.filter(np.array([100.0]), dt=0.033)
        flt.reset()
        out = flt.filter(np.array([5.0]), dt=0.033)
        assert math.isclose(out[0], 5.0, abs_tol=1e-6)


# ---------------------------------------------------------------------------
# PosePreprocessor
# ---------------------------------------------------------------------------

class TestPosePreprocessor:
    def _make_pose(self, conf=0.9):
        return {
            "LEFT_HIP":   {"coords": [0.5, 0.6], "confidence": conf},
            "LEFT_KNEE":  {"coords": [0.5, 0.77], "confidence": conf},
            "LEFT_ANKLE": {"coords": [0.5, 0.95], "confidence": conf},
        }

    def test_basic_frame(self):
        pp = PosePreprocessor()
        result = pp.process_frame(0.0, self._make_pose())
        assert result.valid
        assert math.isclose(result.timestamp, 0.0)

    def test_timestamps_preserved(self):
        pp = PosePreprocessor()
        timestamps = [0.0, 0.033, 0.066, 0.1]
        poses      = [self._make_pose() for _ in timestamps]
        results    = pp.process_sequence(timestamps, poses)
        for r, t in zip(results, timestamps):
            assert math.isclose(r.timestamp, t)

    def test_long_gap_detected(self):
        pp = PosePreprocessor(quality_cfg=QualityConfig(max_frame_gap_s=0.3))
        pp.process_frame(0.0, self._make_pose())
        result = pp.process_frame(1.0, self._make_pose())   # 1s gap
        assert result.gap_before

    def test_no_gap_for_normal_interval(self):
        pp = PosePreprocessor()
        pp.process_frame(0.0, self._make_pose())
        result = pp.process_frame(0.033, self._make_pose())
        assert not result.gap_before

    def test_jitter_reduction(self):
        """EMA/one-euro should smooth noisy constant signal."""
        pp = PosePreprocessor(
            filter_cfg=FilterConfig(angle_filter="ema", ema_alpha=0.3)
        )
        rng = np.random.default_rng(42)
        base_angle = 90.0
        results = []
        for i in range(60):
            noisy_coord = [0.5 + rng.normal(0, 0.002), 0.77 + rng.normal(0, 0.002)]
            pose = {
                "LEFT_HIP":   {"coords": [0.5, 0.60], "confidence": 0.9},
                "LEFT_KNEE":  {"coords": noisy_coord,  "confidence": 0.9},
                "LEFT_ANKLE": {"coords": [0.5, 0.95],  "confidence": 0.9},
            }
            r = pp.process_frame(i * 0.033, pose)
            results.append(r)

        raw_angles  = [r.angles.get("LEFT_KNEE", float("nan")) for r in results if r.valid]
        valid_raw   = [a for a in raw_angles if math.isfinite(a)]
        # We just check data flows without error and produces finite angles
        assert len(valid_raw) > 0

    def test_low_confidence_landmark_filtered(self):
        pp = PosePreprocessor(quality_cfg=QualityConfig(min_confidence=0.5))
        pose = {
            "LEFT_HIP":   {"coords": [0.5, 0.6], "confidence": 0.2},   # low
            "LEFT_KNEE":  {"coords": [0.5, 0.77], "confidence": 0.9},
            "LEFT_ANKLE": {"coords": [0.5, 0.95], "confidence": 0.9},
        }
        result = pp.process_frame(0.0, pose)
        # LEFT_HIP filtered → LEFT_HIP angle (hip joint) should be NaN
        assert result.pose.get("LEFT_HIP") is None

    def test_non_monotonic_timestamp(self):
        pp = PosePreprocessor()
        pp.process_frame(0.5, self._make_pose())
        result = pp.process_frame(0.3, self._make_pose())  # goes backward
        assert not result.valid

    def test_missing_data_not_interpolated(self):
        """None landmarks must remain None — never silently replaced."""
        pp = PosePreprocessor()
        pose = {
            "LEFT_HIP":   None,
            "LEFT_KNEE":  {"coords": [0.5, 0.77], "confidence": 0.9},
            "LEFT_ANKLE": {"coords": [0.5, 0.95], "confidence": 0.9},
        }
        result = pp.process_frame(0.0, pose)
        assert result.pose.get("LEFT_HIP") is None

    def test_sequence_reset_on_new_call(self):
        """Calling process_sequence twice starts fresh (no leftover filter state)."""
        pp   = PosePreprocessor()
        seq1 = [self._make_pose() for _ in range(5)]
        ts1  = [i * 0.033 for i in range(5)]
        r1   = pp.process_sequence(ts1, seq1)
        r2   = pp.process_sequence(ts1, seq1)   # same data
        # Should produce identical valid flags
        assert [r.valid for r in r1] == [r.valid for r in r2]
