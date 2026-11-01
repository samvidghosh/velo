"""Versioned JSON-compatible input contract for pose sequences."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import math

SCHEMA_VERSION = "1.0"
REQUIRED_LANDMARKS = ("left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle", "left_shoulder", "right_shoulder")

@dataclass(frozen=True)
class PoseFrame:
    timestamp: float
    landmarks: dict[str, dict[str, Any]]

def validate_pose_sequence(value: dict[str, Any]) -> list[PoseFrame]:
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"pose schema_version must be {SCHEMA_VERSION}")
    frames = value.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("frames must be a non-empty list")
    parsed: list[PoseFrame] = []
    previous = -math.inf
    for index, frame in enumerate(frames):
        try:
            timestamp = float(frame["timestamp"])
            landmarks = frame["landmarks"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid frame at index {index}") from exc
        if not math.isfinite(timestamp) or timestamp <= previous:
            raise ValueError("timestamps must be finite and strictly increasing")
        if not isinstance(landmarks, dict):
            raise ValueError(f"landmarks at frame {index} must be an object")
        previous = timestamp
        parsed.append(PoseFrame(timestamp, landmarks))
    return parsed
