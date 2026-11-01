"""
preprocessing.py — Pose validation, filtering, and gap handling
===============================================================

Design goals
------------
* Reduce pose-estimation jitter without erasing genuine fast movements.
* Never interpolate across long gaps.
* Preserve original timestamps and missing-data information.
* Treat low-confidence estimates as missing, not as noise.
* Reset filter state whenever a long gap is detected.

Filters implemented
-------------------
EMA (Exponential Moving Average)
    Simple, low-latency, one-parameter filter.  Good baseline.

One-Euro Filter
    Adaptive low-pass filter that reduces lag at low speeds.
    Reference: Casiez et al., "1€ Filter: A Simple Speed-based
    Low-pass Filter for Noisy Input in Interactive Systems", CHI 2012.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from .config import FilterConfig, QualityConfig
from .geometry import _to_array


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_timestamps(timestamps: list[float]) -> list[str]:
    """Check a list of frame timestamps for common problems.

    Parameters
    ----------
    timestamps:
        Monotonically non-decreasing float values (seconds).

    Returns
    -------
    list[str]
        Zero or more human-readable warning strings.
    """
    warnings: list[str] = []
    if len(timestamps) == 0:
        warnings.append("Empty timestamp list.")
        return warnings

    for i, t in enumerate(timestamps):
        if not math.isfinite(t):
            warnings.append(f"Non-finite timestamp at index {i}: {t}")

    prev = -math.inf
    for i, t in enumerate(timestamps):
        if math.isfinite(t):
            if t < prev:
                warnings.append(
                    f"Non-monotonic timestamp at index {i}: "
                    f"{t:.4f} < {prev:.4f}"
                )
            prev = t

    return warnings


def validate_pose(
    pose: dict[str, Any],
    quality: QualityConfig,
) -> tuple[bool, list[str]]:
    """Validate a single pose frame.

    Returns
    -------
    (valid, warnings)
        *valid* is ``True`` if the pose is usable (may have partial landmarks).
        *warnings* is a list of human-readable strings describing issues.
    """
    warnings: list[str] = []
    if not isinstance(pose, dict) or len(pose) == 0:
        return False, ["Pose is empty or not a dictionary."]

    valid_count = 0
    for name, entry in pose.items():
        if entry is None:
            continue
        if isinstance(entry, dict):
            conf = entry.get("confidence", 1.0)
            if conf < quality.min_confidence:
                continue  # treated as missing
            coords = entry.get("coords") or entry.get("coordinates")
            arr = _to_array(coords)
        else:
            arr = _to_array(entry)
        if arr is not None:
            valid_count += 1

    if valid_count == 0:
        warnings.append("No valid landmarks in pose.")
        return False, warnings
    return True, warnings


def get_landmark_confidence(entry: Any) -> float:
    """Return the confidence score for a landmark entry.

    Returns 1.0 if no confidence information is available, 0.0 if the entry
    is None.
    """
    if entry is None:
        return 0.0
    if isinstance(entry, dict):
        return float(entry.get("confidence", 1.0))
    arr = _to_array(entry)
    return 1.0 if arr is not None else 0.0


def filter_by_confidence(
    pose: dict[str, Any],
    min_confidence: float,
) -> dict[str, Any]:
    """Return a new pose dict with low-confidence landmarks set to ``None``.

    Landmarks are **not** deleted so the key set stays stable.
    """
    filtered: dict[str, Any] = {}
    for name, entry in pose.items():
        conf = get_landmark_confidence(entry)
        filtered[name] = entry if conf >= min_confidence else None
    return filtered


# ---------------------------------------------------------------------------
# One-Euro filter (per-channel)
# ---------------------------------------------------------------------------

def _smoothing_factor(cutoff: float, dt: float) -> float:
    tau   = 1.0 / (2.0 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class _OneEuroChannel:
    """One-Euro filter for a single scalar channel."""

    def __init__(self, min_cutoff: float, beta: float, d_cutoff: float) -> None:
        self._min_cutoff = min_cutoff
        self._beta       = beta
        self._d_cutoff   = d_cutoff
        self._x: Optional[float]  = None
        self._dx: Optional[float] = None

    def reset(self) -> None:
        self._x  = None
        self._dx = None

    def filter(self, x: float, dt: float) -> float:
        if not math.isfinite(x):
            return float("nan")
        if self._x is None or not math.isfinite(self._x):
            self._x  = x
            self._dx = 0.0
            return x

        # Derivative estimate
        dx = (x - self._x) / dt
        a_d = _smoothing_factor(self._d_cutoff, dt)
        dx_hat = a_d * dx + (1.0 - a_d) * (self._dx or 0.0)

        # Adaptive cutoff
        cutoff = self._min_cutoff + self._beta * abs(dx_hat)
        a = _smoothing_factor(cutoff, dt)
        x_hat = a * x + (1.0 - a) * self._x

        self._x  = x_hat
        self._dx = dx_hat
        return x_hat


class OneEuroFilter:
    """One-Euro filter for a fixed-size vector (one channel per element)."""

    def __init__(self, n_channels: int, cfg: FilterConfig) -> None:
        self._channels = [
            _OneEuroChannel(cfg.one_euro_min_cutoff, cfg.one_euro_beta, cfg.one_euro_d_cutoff)
            for _ in range(n_channels)
        ]

    def reset(self) -> None:
        for ch in self._channels:
            ch.reset()

    def filter(self, values: np.ndarray, dt: float) -> np.ndarray:
        """Filter a 1-D array of *n_channels* values."""
        out = np.empty_like(values, dtype=float)
        for i, ch in enumerate(self._channels):
            out[i] = ch.filter(float(values[i]), dt)
        return out


# ---------------------------------------------------------------------------
# EMA filter (per-channel)
# ---------------------------------------------------------------------------

class EMAFilter:
    """Exponential moving average filter for a fixed-size vector."""

    def __init__(self, n_channels: int, alpha: float) -> None:
        if not (0.0 < alpha <= 1.0):
            raise ValueError(f"EMA alpha must be in (0, 1], got {alpha}")
        self._alpha = alpha
        self._state: Optional[np.ndarray] = None
        self._n = n_channels

    def reset(self) -> None:
        self._state = None

    def filter(self, values: np.ndarray, _dt: float = 0.0) -> np.ndarray:
        """Filter a 1-D array returning an EMA-smoothed array."""
        finite_mask = np.isfinite(values)
        if self._state is None:
            self._state = np.where(finite_mask, values, np.nan)
            return self._state.copy()

        # Only update channels that have finite new values
        new_state = np.where(
            finite_mask,
            self._alpha * values + (1.0 - self._alpha) * np.where(np.isfinite(self._state),
                                                                    self._state, values),
            self._state,
        )
        self._state = new_state
        return new_state.copy()


# ---------------------------------------------------------------------------
# Pose sequence preprocessor
# ---------------------------------------------------------------------------

@dataclass
class FrameResult:
    """Validated, filtered result for a single frame."""
    timestamp:        float
    pose:             dict[str, Any]   # filtered (low-conf → None)
    angles:           dict[str, float] # joint angles for this frame
    valid:            bool             # frame usable?
    gap_before:       bool             # long gap before this frame?
    warnings:         list[str]        = field(default_factory=list)


class PosePreprocessor:
    """Stateful preprocessor for a streaming pose sequence.

    Parameters
    ----------
    filter_cfg:
        Filtering parameters.
    quality_cfg:
        Data-quality thresholds.
    """

    def __init__(
        self,
        filter_cfg: FilterConfig = FilterConfig(),
        quality_cfg: QualityConfig = QualityConfig(),
    ) -> None:
        self._fcfg  = filter_cfg
        self._qcfg  = quality_cfg
        self._landmark_filters: dict[str, Any] = {}
        self._last_ts: Optional[float] = None

    def reset(self) -> None:
        """Reset all filter states (e.g. before a new exercise set)."""
        self._landmark_filters.clear()
        self._last_ts = None

    def _get_filter(self, name: str, n_ch: int) -> Any:
        """Lazily create a filter for landmark *name* with *n_ch* channels."""
        if name not in self._landmark_filters:
            mode = self._fcfg.angle_filter
            if mode == "one_euro":
                self._landmark_filters[name] = OneEuroFilter(n_ch, self._fcfg)
            elif mode == "ema":
                self._landmark_filters[name] = EMAFilter(n_ch, self._fcfg.ema_alpha)
            else:
                self._landmark_filters[name] = None  # pass-through
        return self._landmark_filters[name]

    def _extract_coords(self, entry: Any) -> Optional[np.ndarray]:
        """Extract coordinate array from a landmark entry dict or sequence."""
        if entry is None:
            return None
        if isinstance(entry, dict):
            raw = entry.get("coords") or entry.get("coordinates")
        else:
            raw = entry
        return _to_array(raw)

    def _rebuild_entry(self, entry: Any, filtered_coords: np.ndarray) -> Any:
        """Rebuild the landmark entry with updated coordinates."""
        if isinstance(entry, dict):
            key = "coords" if "coords" in entry else "coordinates"
            return {**entry, key: filtered_coords.tolist()}
        return filtered_coords.tolist()

    def process_frame(
        self,
        timestamp: float,
        pose: dict[str, Any],
    ) -> FrameResult:
        """Validate and filter a single pose frame.

        Parameters
        ----------
        timestamp:
            Time of this frame in seconds.
        pose:
            Raw pose dictionary.

        Returns
        -------
        FrameResult
            Filtered frame data with validity flags and warnings.
        """
        from .geometry import calculate_joint_angles

        warnings: list[str] = []

        # --- timestamp validation ---
        if not math.isfinite(timestamp):
            return FrameResult(
                timestamp=timestamp, pose={}, angles={},
                valid=False, gap_before=False,
                warnings=["Non-finite timestamp; frame skipped."],
            )

        gap_before = False
        if self._last_ts is not None:
            dt = timestamp - self._last_ts
            if dt < 0.0:
                warnings.append(
                    f"Non-monotonic timestamp ({timestamp:.4f} < {self._last_ts:.4f}); "
                    "frame skipped."
                )
                return FrameResult(
                    timestamp=timestamp, pose={}, angles={},
                    valid=False, gap_before=False, warnings=warnings,
                )
            if dt > self._qcfg.max_frame_gap_s:
                gap_before = True
                warnings.append(
                    f"Frame gap {dt:.3f}s exceeds threshold "
                    f"({self._qcfg.max_frame_gap_s}s); filter states reset."
                )
                for flt in self._landmark_filters.values():
                    if flt is not None:
                        flt.reset()

        # --- confidence filtering ---
        clean_pose = filter_by_confidence(pose, self._qcfg.min_confidence)

        # --- coordinate filtering ---
        filtered_pose: dict[str, Any] = {}
        dt_for_filter = max(
            (timestamp - self._last_ts) if self._last_ts is not None else 1.0 / 30.0,
            1e-6,
        )
        for name, entry in clean_pose.items():
            if entry is None:
                filtered_pose[name] = None
                continue
            coords = self._extract_coords(entry)
            if coords is None:
                filtered_pose[name] = None
                continue
            flt = self._get_filter(name, len(coords))
            if flt is None:
                filtered_pose[name] = entry
            else:
                smoothed = flt.filter(coords, dt_for_filter)
                filtered_pose[name] = self._rebuild_entry(entry, smoothed)

        # --- pose validity ---
        valid, pose_warnings = validate_pose(filtered_pose, self._qcfg)
        warnings.extend(pose_warnings)

        # --- joint angles ---
        angles = calculate_joint_angles(filtered_pose)

        self._last_ts = timestamp
        return FrameResult(
            timestamp=timestamp,
            pose=filtered_pose,
            angles=angles,
            valid=valid,
            gap_before=gap_before,
            warnings=warnings,
        )

    def process_sequence(
        self,
        timestamps: list[float],
        poses: list[dict[str, Any]],
    ) -> list[FrameResult]:
        """Process a batch sequence of (timestamp, pose) pairs.

        Resets filter state at the start so this can be called multiple
        times independently on different sequences.
        """
        self.reset()
        ts_warnings = validate_timestamps(timestamps)
        results: list[FrameResult] = []
        for ts, pose in zip(timestamps, poses):
            result = self.process_frame(ts, pose)
            if ts_warnings:
                result.warnings = ts_warnings + result.warnings
                ts_warnings = []  # emit once
            results.append(result)
        return results
