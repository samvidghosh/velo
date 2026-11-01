"""2-D projected angles. Image origin top-left; x right, y down, normalized to frame."""
from __future__ import annotations
import numpy as np

def angle_at(a, b, c) -> float | None:
    """Unsigned projected angle in degrees at B; None for absent/degenerate points."""
    if a is None or b is None or c is None:
        return None
    try:
        ba = np.asarray(a, dtype=float)[:2] - np.asarray(b, dtype=float)[:2]
        bc = np.asarray(c, dtype=float)[:2] - np.asarray(b, dtype=float)[:2]
    except (TypeError, ValueError):
        return None
    na, nc = np.linalg.norm(ba), np.linalg.norm(bc)
    if not np.isfinite([*ba, *bc]).all() or na < 1e-8 or nc < 1e-8:
        return None
    return float(np.degrees(np.arccos(np.clip(np.dot(ba, bc) / (na * nc), -1.0, 1.0))))

def get_point(landmarks, name, min_confidence=0.35):
    item = landmarks.get(name)
    if not isinstance(item, dict) or item.get("coordinates") is None:
        return None
    try:
        point = np.asarray(item["coordinates"], dtype=float)
        confidence = float(item.get("confidence", 1.0))
    except (ValueError, TypeError):
        return None
    if len(point) < 2 or not np.isfinite(point[:2]).all() or not np.isfinite(confidence) or not 0 <= confidence <= 1 or confidence < min_confidence:
        return None
    return point[:2]

def projected_angles(landmarks, min_confidence=0.35):
    p = {n: get_point(landmarks, n, min_confidence) for n in (
        "left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle",
        "left_shoulder", "right_shoulder", "left_heel", "right_heel", "left_toe", "right_toe")}
    midpoint = lambda a, b: (a + b) / 2 if a is not None and b is not None else None
    out = {}
    for side in ("left", "right"):
        out[f"{side}_knee_flexion_projected_deg"] = angle_at(p[f"{side}_hip"], p[f"{side}_knee"], p[f"{side}_ankle"])
        hip_included = angle_at(p[f"{side}_shoulder"], p[f"{side}_hip"], p[f"{side}_knee"])
        # Straight trunk-to-thigh alignment is 0 degrees by this convention.
        out[f"{side}_hip_flexion_projected_deg"] = 180.0 - hip_included if hip_included is not None else None
        heel, ankle, toe = p[f"{side}_heel"], p[f"{side}_ankle"], p[f"{side}_toe"]
        out[f"{side}_ankle_projected_deg"] = angle_at(p[f"{side}_knee"], ankle, toe) if heel is None else angle_at(heel, ankle, toe)
    hips = midpoint(p["left_hip"], p["right_hip"])
    shoulders = midpoint(p["left_shoulder"], p["right_shoulder"])
    # Inclination from vertical in image plane; sign reflects image x displacement.
    if hips is not None and shoulders is not None:
        v = hips - shoulders
        out["trunk_inclination_projected_deg"] = float(np.degrees(np.arctan2(v[0], -v[1]))) if np.linalg.norm(v) > 1e-8 else None
    else:
        out["trunk_inclination_projected_deg"] = None
    if p["left_hip"] is not None and p["right_hip"] is not None:
        out["pelvic_tilt_proxy_deg"] = float(np.degrees(np.arctan2(*(p["right_hip"] - p["left_hip"])[::-1])))
    else:
        out["pelvic_tilt_proxy_deg"] = None
    return out
