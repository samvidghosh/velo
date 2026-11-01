"""
geometry.py — Joint-angle calculations and kinematics
======================================================

Coordinate conventions
-----------------------
* Points are NumPy arrays of shape ``(2,)`` or ``(3,)``.
* Angles are computed **at the middle point B** of the triplet (A, B, C):
  the angle between vector B→A and vector B→C.
* Returned angles are in **degrees**.
* Unsigned angles are in [0°, 180°].
* Signed angles are in (-180°, 180°] using the right-hand (cross-product)
  convention: positive when rotating from BA to BC counter-clockwise in the
  XY plane.

Landmark naming
---------------
Pose dictionaries use string keys matching MediaPipe Pose landmark names,
e.g. ``"LEFT_KNEE"``, ``"RIGHT_HIP"``.  A ``None`` value or a missing key
indicates an absent landmark.  Coordinate arrays that contain ``NaN`` or
``Inf`` are also treated as invalid.

Missing-data policy
-------------------
Functions **never** silently replace missing coordinates with zeros.
When a required landmark is absent, the function returns ``float('nan')``
or ``None`` so callers can distinguish "computed zero" from "unavailable".
"""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
Point = np.ndarray          # shape (2,) or (3,)
Pose  = dict[str, Any]      # landmark_name → coords or None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_array(point: Any) -> Optional[np.ndarray]:
    """Convert *point* to a float64 NumPy array, or return ``None``.

    Returns ``None`` if *point* is ``None``, not numeric, or contains
    non-finite values.
    """
    if point is None:
        return None
    try:
        arr = np.asarray(point, dtype=np.float64).ravel()
    except (TypeError, ValueError):
        return None
    if arr.size < 2:
        return None
    if not np.all(np.isfinite(arr)):
        return None
    return arr


def _get_xy(point: Any) -> Optional[np.ndarray]:
    """Return the first two (x, y) components of *point* as a 2-D array."""
    arr = _to_array(point)
    if arr is None:
        return None
    return arr[:2]


# ---------------------------------------------------------------------------
# Core angle functions
# ---------------------------------------------------------------------------

def calculate_angle(
    a: Any,
    b: Any,
    c: Any,
) -> float:
    """Calculate the unsigned angle at **B** between vectors B→A and B→C.

    Parameters
    ----------
    a, b, c:
        Points (sequences / arrays of at least 2 numeric values).
        The angle is computed **at B**.

    Returns
    -------
    float
        Angle in degrees, in [0°, 180°], or ``float('nan')`` when any
        coordinate is missing, infinite, or the vectors are zero-length.
    """
    pa = _to_array(a)
    pb = _to_array(b)
    pc = _to_array(c)
    if pa is None or pb is None or pc is None:
        return float("nan")

    # Use the same number of dimensions as the shortest array
    n = min(pa.size, pb.size, pc.size)
    ba = pa[:n] - pb[:n]
    bc = pc[:n] - pb[:n]

    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    if norm_ba < 1e-9 or norm_bc < 1e-9:
        return float("nan")   # degenerate; vectors have no direction

    cos_angle = np.dot(ba, bc) / (norm_ba * norm_bc)
    cos_angle = float(np.clip(cos_angle, -1.0, 1.0))  # guard floating-point drift
    return math.degrees(math.acos(cos_angle))


def calculate_signed_angle(
    a: Any,
    b: Any,
    c: Any,
) -> float:
    """Calculate the **signed** angle at B between B→A and B→C.

    The sign is determined by the z-component of the cross product B→A × B→C
    in the XY plane:
    * Positive  → counter-clockwise rotation from BA to BC.
    * Negative  → clockwise rotation.

    Only the XY plane is used regardless of input dimensionality.

    Returns
    -------
    float
        Angle in degrees in (-180°, 180°], or ``float('nan')`` on error.
    """
    pa = _get_xy(a)
    pb = _get_xy(b)
    pc = _get_xy(c)
    if pa is None or pb is None or pc is None:
        return float("nan")

    ba = pa - pb
    bc = pc - pb

    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    if norm_ba < 1e-9 or norm_bc < 1e-9:
        return float("nan")

    # atan2 of the z-component of the 2-D cross product
    cross_z = float(ba[0] * bc[1] - ba[1] * bc[0])
    dot     = float(np.dot(ba, bc))
    return math.degrees(math.atan2(cross_z, dot))


# ---------------------------------------------------------------------------
# Pose-level angle computation
# ---------------------------------------------------------------------------

def _landmark_coords(pose: Pose, name: str) -> Optional[np.ndarray]:
    """Extract coordinate array for *name* from *pose*.

    Returns ``None`` if the landmark is absent, has ``None`` coordinates, or
    stores an invalid dict entry.
    """
    entry = pose.get(name)
    if entry is None:
        return None
    # Support both raw sequence and dict with "coords" key
    if isinstance(entry, dict):
        coords = entry.get("coords") or entry.get("coordinates")
        if coords is None:
            return None
        return _to_array(coords)
    return _to_array(entry)


def calculate_joint_angles(pose: Pose) -> dict[str, float]:
    """Compute a dictionary of named joint angles from a pose.

    Computes angles for every joint where the required three landmarks are
    present and valid.  Missing joints produce ``float('nan')`` entries so
    the caller always receives a complete key set.

    Supported joints (and required landmarks)
    -----------------------------------------
    LEFT_KNEE        : LEFT_HIP, LEFT_KNEE, LEFT_ANKLE
    RIGHT_KNEE       : RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE
    LEFT_HIP         : LEFT_SHOULDER, LEFT_HIP, LEFT_KNEE
    RIGHT_HIP        : RIGHT_SHOULDER, RIGHT_HIP, RIGHT_KNEE
    LEFT_ELBOW       : LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST
    RIGHT_ELBOW      : RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST
    LEFT_SHOULDER    : LEFT_ELBOW, LEFT_SHOULDER, LEFT_HIP
    RIGHT_SHOULDER   : RIGHT_ELBOW, RIGHT_SHOULDER, RIGHT_HIP
    TORSO            : mid-shoulder, mid-hip projected — requires all four

    Returns
    -------
    dict[str, float]
        Angle in degrees for each joint.  ``float('nan')`` when unavailable.
    """
    def _get(name: str) -> Optional[np.ndarray]:
        return _landmark_coords(pose, name)

    triplets: list[tuple[str, str, str, str]] = [
        # (joint_name, A, B, C)
        ("LEFT_KNEE",      "LEFT_HIP",      "LEFT_KNEE",     "LEFT_ANKLE"),
        ("RIGHT_KNEE",     "RIGHT_HIP",     "RIGHT_KNEE",    "RIGHT_ANKLE"),
        ("LEFT_HIP",       "LEFT_SHOULDER", "LEFT_HIP",      "LEFT_KNEE"),
        ("RIGHT_HIP",      "RIGHT_SHOULDER","RIGHT_HIP",     "RIGHT_KNEE"),
        ("LEFT_ELBOW",     "LEFT_SHOULDER", "LEFT_ELBOW",    "LEFT_WRIST"),
        ("RIGHT_ELBOW",    "RIGHT_SHOULDER","RIGHT_ELBOW",   "RIGHT_WRIST"),
        ("LEFT_SHOULDER",  "LEFT_ELBOW",    "LEFT_SHOULDER", "LEFT_HIP"),
        ("RIGHT_SHOULDER", "RIGHT_ELBOW",   "RIGHT_SHOULDER","RIGHT_HIP"),
    ]

    angles: dict[str, float] = {}
    for joint, a_name, b_name, c_name in triplets:
        pa = _get(a_name)
        pb = _get(b_name)
        pc = _get(c_name)
        angles[joint] = calculate_angle(pa, pb, pc)

    # Torso lean: angle between vertical and the trunk vector mid-hip → mid-shoulder
    ls = _get("LEFT_SHOULDER")
    rs = _get("RIGHT_SHOULDER")
    lh = _get("LEFT_HIP")
    rh = _get("RIGHT_HIP")

    if (ls is not None and rs is not None and
            lh is not None and rh is not None):
        mid_shoulder = (ls[:2] + rs[:2]) / 2.0
        mid_hip      = (lh[:2] + rh[:2]) / 2.0
        trunk = mid_shoulder - mid_hip
        norm_t = np.linalg.norm(trunk)
        if norm_t > 1e-9:
            # Angle with the vertical (upward) direction [0, -1] in image coords
            vertical = np.array([0.0, -1.0])
            cos_t = float(np.clip(np.dot(trunk / norm_t, vertical), -1.0, 1.0))
            angles["TORSO"] = math.degrees(math.acos(cos_t))
        else:
            angles["TORSO"] = float("nan")
    else:
        angles["TORSO"] = float("nan")

    return angles


# ---------------------------------------------------------------------------
# Distance
# ---------------------------------------------------------------------------

def calculate_distance(a: Any, b: Any) -> float:
    """Euclidean distance between points *a* and *b*.

    Returns ``float('nan')`` if either point is missing or invalid.
    """
    pa = _to_array(a)
    pb = _to_array(b)
    if pa is None or pb is None:
        return float("nan")
    n = min(pa.size, pb.size)
    return float(np.linalg.norm(pa[:n] - pb[:n]))


# ---------------------------------------------------------------------------
# Temporal derivatives
# ---------------------------------------------------------------------------

def calculate_angle_velocity(
    angles: list[float] | np.ndarray,
    timestamps: list[float] | np.ndarray,
) -> np.ndarray:
    """Compute angular velocity (degrees / second) from an angle time series.

    Parameters
    ----------
    angles:
        Sequence of joint angles (degrees).  May contain ``NaN``.
    timestamps:
        Corresponding timestamps (seconds).  Must have the same length as
        *angles* and be monotonically non-decreasing.

    Returns
    -------
    np.ndarray
        Angular velocity at each sample, shape ``(N,)``.
        The first element is always ``NaN`` (no previous sample).
        NaN propagates around gaps.

    Notes
    -----
    Irregular timestamps are handled by using the actual time delta between
    consecutive samples rather than assuming a fixed frame rate.
    """
    angles_arr = np.asarray(angles, dtype=float)
    times_arr  = np.asarray(timestamps, dtype=float)

    n = len(angles_arr)
    if n != len(times_arr):
        raise ValueError("angles and timestamps must have equal length")
    if n == 0:
        return np.array([], dtype=float)

    velocity = np.full(n, float("nan"), dtype=float)
    for i in range(1, n):
        dt = times_arr[i] - times_arr[i - 1]
        if dt <= 0.0 or not math.isfinite(angles_arr[i]) or not math.isfinite(angles_arr[i - 1]):
            continue
        velocity[i] = (angles_arr[i] - angles_arr[i - 1]) / dt
    return velocity


def calculate_angle_acceleration(
    angles: list[float] | np.ndarray,
    timestamps: list[float] | np.ndarray,
) -> np.ndarray:
    """Compute angular acceleration (degrees / second²) from an angle series.

    Derived from the first-order velocity estimate using a second finite
    difference.  The first two elements are always ``NaN``.
    """
    velocity = calculate_angle_velocity(angles, timestamps)
    return calculate_angle_velocity(velocity, timestamps)


# ---------------------------------------------------------------------------
# Pose normalisation
# ---------------------------------------------------------------------------

def normalize_pose(pose: Pose, body_scale: float) -> Pose:
    """Scale all landmark coordinates in *pose* by ``1 / body_scale``.

    This produces a body-height-normalised representation so that geometric
    measurements are independent of the subject's pixel height in the frame.

    Parameters
    ----------
    pose:
        Input pose dictionary.
    body_scale:
        Characteristic length in the same units as the stored coordinates
        (e.g., the pixel distance from hip to shoulder, or from heel to crown).
        Must be positive.

    Returns
    -------
    Pose
        New pose dictionary with scaled coordinates.  Landmarks that are
        ``None`` or invalid remain unchanged.

    Raises
    ------
    ValueError
        If *body_scale* is not a positive finite number.
    """
    if not math.isfinite(body_scale) or body_scale <= 0.0:
        raise ValueError(f"body_scale must be a positive finite number, got {body_scale}")

    new_pose: Pose = {}
    for name, entry in pose.items():
        if entry is None:
            new_pose[name] = None
            continue
        if isinstance(entry, dict):
            coords = entry.get("coords") or entry.get("coordinates")
            arr = _to_array(coords)
            if arr is None:
                new_pose[name] = entry
            else:
                scaled = {**entry, "coords": (arr / body_scale).tolist()}
                new_pose[name] = scaled
        else:
            arr = _to_array(entry)
            if arr is None:
                new_pose[name] = entry
            else:
                new_pose[name] = (arr / body_scale).tolist()
    return new_pose
