"""
test_geometry.py — Tests for engine.geometry
"""
from __future__ import annotations

import math
import pytest
import numpy as np

from engine.geometry import (
    calculate_angle,
    calculate_signed_angle,
    calculate_joint_angles,
    calculate_distance,
    calculate_angle_velocity,
    calculate_angle_acceleration,
    normalize_pose,
)


# ---------------------------------------------------------------------------
# calculate_angle
# ---------------------------------------------------------------------------

class TestCalculateAngle:
    def test_right_angle(self):
        """A right angle at origin should return 90°."""
        a = [1.0, 0.0]
        b = [0.0, 0.0]
        c = [0.0, 1.0]
        result = calculate_angle(a, b, c)
        assert math.isclose(result, 90.0, abs_tol=1e-6)

    def test_straight_line(self):
        """Points on a straight line produce a 180° angle."""
        a = [-1.0, 0.0]
        b = [0.0, 0.0]
        c = [1.0, 0.0]
        result = calculate_angle(a, b, c)
        assert math.isclose(result, 180.0, abs_tol=1e-6)

    def test_45_degrees(self):
        a = [1.0, 0.0]
        b = [0.0, 0.0]
        c = [1.0, 1.0]
        result = calculate_angle(a, b, c)
        assert math.isclose(result, 45.0, abs_tol=1e-5)

    def test_known_knee_angle(self):
        """Simulate a knee at ~90°: hip above, knee at origin, ankle below-forward."""
        hip   = [0.0, -1.0]
        knee  = [0.0,  0.0]
        ankle = [1.0,  1.0]
        result = calculate_angle(hip, knee, ankle)
        assert 80.0 < result < 100.0

    def test_degenerate_zero_vector_b_equals_a(self):
        """B == A gives a zero-length vector; should return NaN."""
        assert math.isnan(calculate_angle([0, 0], [0, 0], [1, 1]))

    def test_degenerate_zero_vector_b_equals_c(self):
        assert math.isnan(calculate_angle([1, 1], [0, 0], [0, 0]))

    def test_none_input(self):
        assert math.isnan(calculate_angle(None, [0, 0], [1, 1]))
        assert math.isnan(calculate_angle([0, 0], None, [1, 1]))
        assert math.isnan(calculate_angle([0, 0], [1, 1], None))

    def test_nan_in_coordinate(self):
        assert math.isnan(calculate_angle([float("nan"), 0], [0, 0], [1, 1]))

    def test_inf_in_coordinate(self):
        assert math.isnan(calculate_angle([float("inf"), 0], [0, 0], [1, 1]))

    def test_3d_points(self):
        """3-D points should work; angle at origin."""
        a = [1.0, 0.0, 0.0]
        b = [0.0, 0.0, 0.0]
        c = [0.0, 1.0, 0.0]
        result = calculate_angle(a, b, c)
        assert math.isclose(result, 90.0, abs_tol=1e-6)

    def test_numpy_arrays(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 0.0])
        c = np.array([0.0, 1.0])
        assert math.isclose(calculate_angle(a, b, c), 90.0, abs_tol=1e-6)

    def test_result_in_valid_range(self):
        """Angle must always lie in [0, 180]."""
        for _ in range(50):
            pts = np.random.default_rng(0).uniform(-5, 5, (3, 2))
            a = pts[0].tolist()
            b = pts[1].tolist()
            c = pts[2].tolist()
            ang = calculate_angle(a, b, c)
            if not math.isnan(ang):
                assert 0.0 <= ang <= 180.0 + 1e-9


# ---------------------------------------------------------------------------
# calculate_signed_angle
# ---------------------------------------------------------------------------

class TestCalculateSignedAngle:
    def test_ccw_is_positive(self):
        """Counter-clockwise rotation in XY plane → positive."""
        a = [1.0, 0.0]
        b = [0.0, 0.0]
        c = [0.0, 1.0]   # CCW from BA to BC in image coords
        result = calculate_signed_angle(a, b, c)
        assert result > 0

    def test_cw_is_negative(self):
        a = [0.0, 1.0]
        b = [0.0, 0.0]
        c = [1.0, 0.0]
        result = calculate_signed_angle(a, b, c)
        assert result < 0

    def test_straight_line_signed(self):
        a = [-1.0, 0.0]
        b = [0.0,  0.0]
        c = [1.0,  0.0]
        result = calculate_signed_angle(a, b, c)
        assert math.isclose(abs(result), 180.0, abs_tol=1e-6)

    def test_nan_on_missing(self):
        assert math.isnan(calculate_signed_angle(None, [0, 0], [1, 1]))

    def test_degenerate_zero_vector(self):
        assert math.isnan(calculate_signed_angle([0, 0], [0, 0], [1, 1]))


# ---------------------------------------------------------------------------
# calculate_joint_angles
# ---------------------------------------------------------------------------

class TestCalculateJointAngles:
    def _standing_pose(self):
        """Fabricate a simple standing pose using known coordinates."""
        return {
            "LEFT_HIP":       [0.45, 0.60],
            "RIGHT_HIP":      [0.55, 0.60],
            "LEFT_KNEE":      [0.43, 0.78],
            "RIGHT_KNEE":     [0.57, 0.78],
            "LEFT_ANKLE":     [0.42, 0.95],
            "RIGHT_ANKLE":    [0.58, 0.95],
            "LEFT_SHOULDER":  [0.42, 0.40],
            "RIGHT_SHOULDER": [0.58, 0.40],
            "LEFT_ELBOW":     [0.38, 0.52],
            "RIGHT_ELBOW":    [0.62, 0.52],
            "LEFT_WRIST":     [0.36, 0.63],
            "RIGHT_WRIST":    [0.64, 0.63],
        }

    def test_returns_dict_with_expected_keys(self):
        pose = self._standing_pose()
        angles = calculate_joint_angles(pose)
        for key in ("LEFT_KNEE", "RIGHT_KNEE", "LEFT_HIP", "RIGHT_HIP"):
            assert key in angles

    def test_missing_landmark_gives_nan(self):
        pose = self._standing_pose()
        del pose["LEFT_KNEE"]
        angles = calculate_joint_angles(pose)
        assert math.isnan(angles["LEFT_KNEE"])

    def test_bilateral_independence(self):
        """Left and right angles are computed independently from their own landmarks."""
        pose = self._standing_pose()
        # Perturb only the LEFT side
        pose["LEFT_KNEE"] = [0.43, 0.80]   # slightly different
        angles = calculate_joint_angles(pose)
        assert not math.isnan(angles["LEFT_KNEE"])
        assert not math.isnan(angles["RIGHT_KNEE"])
        # They should differ
        assert angles["LEFT_KNEE"] != angles["RIGHT_KNEE"]

    def test_empty_pose(self):
        angles = calculate_joint_angles({})
        # All angles should be NaN since no landmarks
        for v in angles.values():
            assert math.isnan(v)

    def test_none_landmark_gives_nan(self):
        pose = self._standing_pose()
        pose["LEFT_HIP"] = None
        angles = calculate_joint_angles(pose)
        assert math.isnan(angles["LEFT_HIP"])

    def test_confidence_dict_entry(self):
        """Landmarks stored as dicts with 'coords' key are handled."""
        pose = {
            "LEFT_HIP":   {"coords": [0.45, 0.60], "confidence": 0.9},
            "LEFT_KNEE":  {"coords": [0.43, 0.78], "confidence": 0.9},
            "LEFT_ANKLE": {"coords": [0.42, 0.95], "confidence": 0.9},
        }
        angles = calculate_joint_angles(pose)
        assert not math.isnan(angles["LEFT_KNEE"])


# ---------------------------------------------------------------------------
# calculate_distance
# ---------------------------------------------------------------------------

class TestCalculateDistance:
    def test_unit_distance(self):
        assert math.isclose(calculate_distance([0, 0], [1, 0]), 1.0)

    def test_diagonal(self):
        assert math.isclose(calculate_distance([0, 0], [3, 4]), 5.0)

    def test_3d(self):
        assert math.isclose(calculate_distance([0, 0, 0], [1, 1, 1]), math.sqrt(3))

    def test_none_returns_nan(self):
        assert math.isnan(calculate_distance(None, [1, 0]))
        assert math.isnan(calculate_distance([1, 0], None))

    def test_nan_coord_returns_nan(self):
        assert math.isnan(calculate_distance([float("nan"), 0], [1, 0]))


# ---------------------------------------------------------------------------
# calculate_angle_velocity
# ---------------------------------------------------------------------------

class TestCalculateAngleVelocity:
    def test_constant_angle_zero_velocity(self):
        angles = [90.0] * 10
        times  = [i * 0.1 for i in range(10)]
        vel    = calculate_angle_velocity(angles, times)
        assert len(vel) == 10
        assert math.isnan(vel[0])
        for v in vel[1:]:
            assert math.isclose(v, 0.0, abs_tol=1e-9)

    def test_linear_increase(self):
        """Angle increasing by 10°/s."""
        dt     = 0.1
        angles = [i * 10.0 * dt for i in range(10)]   # 0, 1, 2, ... 9 degrees
        times  = [i * dt for i in range(10)]
        vel    = calculate_angle_velocity(angles, times)
        for v in vel[1:]:
            assert math.isclose(v, 10.0, abs_tol=1e-6)

    def test_irregular_timestamps(self):
        """Velocity calculation is timestamp-aware."""
        angles = [0.0, 10.0, 10.0]
        times  = [0.0,  0.5,  1.5]   # uneven gaps
        vel    = calculate_angle_velocity(angles, times)
        assert math.isclose(vel[1], 20.0, abs_tol=1e-6)  # 10°/0.5s
        assert math.isclose(vel[2],  0.0, abs_tol=1e-6)  # 0°/1.0s

    def test_nan_propagates(self):
        angles = [90.0, float("nan"), 100.0]
        times  = [0.0,  0.033, 0.066]
        vel    = calculate_angle_velocity(angles, times)
        assert math.isnan(vel[1])

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            calculate_angle_velocity([1, 2, 3], [0.0, 0.1])

    def test_empty(self):
        result = calculate_angle_velocity([], [])
        assert len(result) == 0


# ---------------------------------------------------------------------------
# calculate_angle_acceleration
# ---------------------------------------------------------------------------

class TestCalculateAngleAcceleration:
    def test_constant_velocity_zero_acceleration(self):
        """Linear angle → constant velocity → zero acceleration (after warmup)."""
        dt     = 0.1
        angles = [i * 1.0 for i in range(15)]
        times  = [i * dt  for i in range(15)]
        acc    = calculate_angle_acceleration(angles, times)
        assert math.isnan(acc[0])
        assert math.isnan(acc[1])
        for a in acc[2:]:
            assert math.isclose(a, 0.0, abs_tol=1e-5)

    def test_irregular_timestamps(self):
        """Acceleration respects actual time gaps."""
        angles = [0.0, 5.0, 15.0, 25.0]
        times  = [0.0, 0.5,  1.0,  1.5]
        acc    = calculate_angle_acceleration(angles, times)
        # Not all NaN
        finite_acc = [a for a in acc if math.isfinite(a)]
        assert len(finite_acc) > 0


# ---------------------------------------------------------------------------
# normalize_pose
# ---------------------------------------------------------------------------

class TestNormalizePose:
    def test_basic_scaling(self):
        pose = {"LEFT_HIP": [0.5, 0.6]}
        result = normalize_pose(pose, 2.0)
        coords = result["LEFT_HIP"]
        assert math.isclose(coords[0], 0.25)
        assert math.isclose(coords[1], 0.30)

    def test_none_landmark_preserved(self):
        pose   = {"MISSING": None}
        result = normalize_pose(pose, 1.0)
        assert result["MISSING"] is None

    def test_invalid_scale_raises(self):
        with pytest.raises(ValueError):
            normalize_pose({}, 0.0)
        with pytest.raises(ValueError):
            normalize_pose({}, -1.0)
        with pytest.raises(ValueError):
            normalize_pose({}, float("nan"))

    def test_dict_landmark_coords_updated(self):
        pose = {"LEFT_KNEE": {"coords": [0.4, 0.8], "confidence": 0.9}}
        result = normalize_pose(pose, 2.0)
        coords = result["LEFT_KNEE"]["coords"]
        assert math.isclose(coords[0], 0.2)
        assert math.isclose(coords[1], 0.4)
        # Confidence unchanged
        assert result["LEFT_KNEE"]["confidence"] == 0.9
