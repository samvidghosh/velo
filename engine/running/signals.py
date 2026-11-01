"""NaN-aware smoothing and cautious periodic gait-event candidates."""
from __future__ import annotations
import numpy as np
from scipy.signal import find_peaks, savgol_filter
from scipy.ndimage import median_filter

def smooth(values, window=5):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or window < 1:
        raise ValueError("values must be 1D and window positive")
    valid = np.isfinite(x)
    if valid.sum() < 3:
        return x.copy()
    idx = np.arange(len(x))
    filled = np.interp(idx, idx[valid], x[valid])
    # A short median pass suppresses isolated pose-estimator jumps before the
    # low-pass polynomial fit, while preserving the gait-cycle waveform.
    median_size = min(3, len(filled) if len(filled) % 2 else len(filled)-1)
    if median_size >= 3:
        filled = median_filter(filled, size=median_size, mode="nearest")
    size = min(window if window % 2 else window + 1, len(x) if len(x) % 2 else len(x)-1)
    return savgol_filter(filled, size, min(2, size-1), mode="interp") if size >= 3 else filled

def detect_cycle_candidates(times, signal, min_period=0.25, max_period=2.0):
    """Find recurring maxima/minima of a quality-filtered periodic signal.

    Events are candidates only: without camera-calibrated contact evidence these
    are not physical initial-contact labels.
    """
    t, x = np.asarray(times, float), np.asarray(signal, float)
    if len(t) != len(x) or len(t) < 5 or not np.isfinite(t).all() or np.any(np.diff(t) <= 0):
        return {"events": [], "periods_s": [], "cadence_spm": None, "status": "insufficient_evidence"}
    valid = np.isfinite(x)
    if valid.sum() < max(5, int(.6 * len(x))):
        return {"events": [], "periods_s": [], "cadence_spm": None, "status": "insufficient_evidence"}
    y = smooth(x)
    prominence = max(float(np.nanstd(y)) * .2, 1e-6)
    peaks, _ = find_peaks(y, prominence=prominence, distance=max(1, int(min_period / np.median(np.diff(t)))))
    periods = np.diff(t[peaks])
    periods = periods[(periods >= min_period) & (periods <= max_period)]
    cadence = float(120 / np.median(periods)) if len(periods) >= 1 else None
    return {"events": [{"timestamp": float(t[i]), "kind": "cycle_peak_candidate", "confidence": "low" if len(periods) < 2 else "moderate"} for i in peaks],
            "periods_s": periods.tolist(), "cadence_spm": cadence,
            "status": "candidate_events" if len(peaks) >= 2 else "insufficient_evidence"}
