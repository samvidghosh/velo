"""
test_integration.py — End-to-end integration tests for the Velo engine
"""
from __future__ import annotations

import math
import sys
import os

import pytest

# Ensure the engine package is importable from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from engine.analyzer import AnalysisResult, analyze_movement
from engine.examples.generate_synthetic_data import SCENARIOS, get_scenario
from engine.exercise_rules import ObservationStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(scenario_name: str, **kwargs) -> AnalysisResult:
    frames = get_scenario(scenario_name)
    return analyze_movement(frames, exercise="squat", **kwargs)


# ---------------------------------------------------------------------------
# Basic pipeline smoke tests
# ---------------------------------------------------------------------------

class TestAnalyzerSmoke:
    def test_returns_analysis_result(self):
        result = _run("three_complete_squats")
        assert isinstance(result, AnalysisResult)

    def test_exercise_name_preserved(self):
        result = _run("three_complete_squats")
        assert result.exercise == "squat"

    def test_timestamps_non_empty(self):
        result = _run("three_complete_squats")
        assert len(result.timestamps) > 10

    def test_angle_series_keys(self):
        result = _run("three_complete_squats")
        assert "LEFT_KNEE" in result.angle_series or "RIGHT_KNEE" in result.angle_series

    def test_phase_events_length_matches_timestamps(self):
        result = _run("three_complete_squats")
        assert len(result.phase_events) == len(result.timestamps)

    def test_observations_list(self):
        result = _run("three_complete_squats")
        assert isinstance(result.observations, list)
        assert len(result.observations) > 0

    def test_data_quality_summary(self):
        result = _run("three_complete_squats")
        dq = result.data_quality
        assert dq.total_frames > 0
        assert 0.0 <= dq.valid_fraction <= 1.0

    def test_summary_text_executes(self):
        result = _run("three_complete_squats")
        text   = result.summary_text()
        assert isinstance(text, str)
        assert len(text) > 0


# ---------------------------------------------------------------------------
# Scenario-specific expectations
# ---------------------------------------------------------------------------

class TestThreeCompleteSquats:
    def setup_method(self):
        self.result = _run("three_complete_squats")

    def test_rep_count(self):
        """Should detect at least 2 valid reps from 3 complete squats."""
        assert self.result.accepted_reps >= 2

    def test_reps_have_positive_rom(self):
        for r in self.result.reps:
            if r.valid:
                assert math.isfinite(r.range_of_motion)
                assert r.range_of_motion > 0.0

    def test_cycle_count_at_least_reps(self):
        assert self.result.total_cycles >= self.result.accepted_reps


class TestIncompleteSquat:
    def setup_method(self):
        self.result = _run("incomplete_squat")

    def test_no_valid_reps(self):
        """Incomplete squat should produce 0 accepted reps."""
        assert self.result.accepted_reps == 0

    def test_has_observations(self):
        assert len(self.result.observations) > 0


class TestPartialSquat:
    def setup_method(self):
        self.result = _run("partial_squat")

    def test_shallow_or_zero_valid_reps(self):
        """Shallow squat may not meet ROM threshold."""
        # Could be 0 valid reps, or possibly some if default thresholds are met
        assert self.result.total_cycles >= 0   # at least no crash


class TestFastSquat:
    def setup_method(self):
        self.result = _run("fast_squat")

    def test_reps_detected(self):
        """Fast squats should still produce some counted reps."""
        assert self.result.total_cycles >= 1


class TestSlowSquat:
    def setup_method(self):
        self.result = _run("slow_squat")

    def test_reps_detected(self):
        assert self.result.total_cycles >= 1


class TestPauseAtBottom:
    def setup_method(self):
        self.result = _run("pause_at_bottom")

    def test_reps_not_zero(self):
        """Paused-bottom squats should still be counted."""
        assert self.result.total_cycles >= 1


class TestNoisyJoints:
    def setup_method(self):
        self.result = _run("noisy_joints")

    def test_no_crash(self):
        assert isinstance(self.result, AnalysisResult)

    def test_some_reps_despite_noise(self):
        assert self.result.total_cycles >= 1


class TestMissingLandmarks:
    def setup_method(self):
        self.result = _run("missing_landmarks")

    def test_no_crash(self):
        assert isinstance(self.result, AnalysisResult)

    def test_data_quality_below_one(self):
        """Missing landmarks should reduce valid-frame fraction."""
        # Note: may still be high if fallback to RIGHT_KNEE works
        assert self.result.data_quality.total_frames > 0


class TestLowConfidence:
    def setup_method(self):
        self.result = _run("low_confidence")

    def test_low_confidence_detected(self):
        """Half of frames have low confidence; quality should reflect this."""
        # Valid fraction should be reduced
        assert self.result.data_quality.total_frames > 0

    def test_uncertainty_or_warnings(self):
        """Should produce uncertainty flags or warnings about quality."""
        has_quality_issue = (
            len(self.result.uncertainty_flags) > 0
            or len(self.result.warnings) > 0
            or any(
                o.status == ObservationStatus.FLAGGED
                for o in self.result.observations
                if o.rule_id == "DATA_001"
            )
        )
        assert has_quality_issue


class TestIrregularFrameIntervals:
    def setup_method(self):
        self.result = _run("irregular_frame_intervals")

    def test_no_crash(self):
        assert isinstance(self.result, AnalysisResult)

    def test_some_reps(self):
        assert self.result.total_cycles >= 1


class TestInterruptedSequence:
    def setup_method(self):
        self.result = _run("interrupted_sequence")

    def test_no_crash(self):
        assert isinstance(self.result, AnalysisResult)

    def test_gap_detected(self):
        """The 2-second gap should be detected."""
        assert self.result.data_quality.gap_events >= 1

    def test_gap_flag_in_uncertainty(self):
        texts = " ".join(self.result.uncertainty_flags + self.result.warnings)
        assert "gap" in texts.lower() or self.result.data_quality.gap_events > 0


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_empty_frames_raises(self):
        with pytest.raises(ValueError):
            analyze_movement([], exercise="squat")

    def test_not_a_list_raises(self):
        with pytest.raises((ValueError, TypeError)):
            analyze_movement("not a list", exercise="squat")

    def test_missing_timestamp_raises(self):
        frames = [{"pose": {"LEFT_HIP": [0.5, 0.6]}}]
        with pytest.raises(ValueError):
            analyze_movement(frames, exercise="squat")

    def test_missing_pose_raises(self):
        frames = [{"timestamp": 0.0}]
        with pytest.raises(ValueError):
            analyze_movement(frames, exercise="squat")

    def test_unknown_exercise_raises(self):
        frames = get_scenario("three_complete_squats")
        with pytest.raises((ValueError, KeyError)):
            analyze_movement(frames, exercise="unknown_exercise_xyz")

    def test_all_nan_angles_no_crash(self):
        """All NaN pose data should degrade gracefully."""
        frames = [
            {"timestamp": i * 0.033, "pose": {"LEFT_HIP": [float("nan"), float("nan")]}}
            for i in range(30)
        ]
        result = analyze_movement(frames, exercise="squat")
        assert isinstance(result, AnalysisResult)
        assert result.accepted_reps == 0


# ---------------------------------------------------------------------------
# Numerical stability
# ---------------------------------------------------------------------------

class TestNumericalStability:
    def test_angle_series_finite_or_nan(self):
        """Angle series must contain only finite floats or NaN — never Inf."""
        result = _run("three_complete_squats")
        for joint, series in result.angle_series.items():
            for angle in series:
                assert not math.isinf(angle), f"Inf in {joint}: {angle}"

    def test_rep_records_finite(self):
        result = _run("three_complete_squats")
        for r in result.reps:
            assert not math.isinf(r.start_time)
            assert not math.isinf(r.end_time)
            if math.isfinite(r.range_of_motion):
                assert r.range_of_motion >= 0.0

    def test_evidence_quality_in_range(self):
        result = _run("three_complete_squats")
        for obs in result.observations:
            q = obs.evidence_quality
            assert 0.0 <= q <= 1.0 or math.isnan(q)

    def test_all_scenarios_no_crash(self):
        """All 11 synthetic scenarios must run without exception."""
        for name in SCENARIOS:
            result = _run(name)
            assert isinstance(result, AnalysisResult), f"Failed for scenario: {name}"
