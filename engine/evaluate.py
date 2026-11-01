"""
evaluate.py — Repetition-counting accuracy evaluation
======================================================

Computes precision, recall, F1, and absolute count error for the engine
against manually defined ground-truth rep intervals.

Usage
-----
    python engine/evaluate.py

NOTE: All ground-truth data in this script is derived from synthetic
scenarios.  Reported accuracy metrics are **not** generalisable to real
human data.

Metrics reported
----------------
* Absolute count error   = |predicted_count − true_count|
* Precision              = TP / (TP + FP)
* Recall                 = TP / (TP + FN)
* F1                     = 2 · precision · recall / (precision + recall)

A predicted rep is a True Positive if its [start, end] interval overlaps
with a ground-truth interval by more than ``overlap_threshold`` fraction of
the shorter interval.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class GTInterval:
    """A manually defined ground-truth repetition interval."""
    start: float
    end:   float
    label: str = ""


@dataclass
class EvalMetrics:
    scenario:       str
    true_count:     int
    pred_count:     int
    tp:             int
    fp:             int
    fn:             int
    precision:      float
    recall:         float
    f1:             float
    abs_count_error: int

    def __str__(self) -> str:
        return (
            f"{self.scenario:<35}  "
            f"GT={self.true_count}  "
            f"P={self.pred_count}  "
            f"TP={self.tp}  FP={self.fp}  FN={self.fn}  "
            f"Prec={self.precision:.2f}  "
            f"Rec={self.recall:.2f}  "
            f"F1={self.f1:.2f}  "
            f"|Err|={self.abs_count_error}"
        )


def _overlaps(pred_start: float, pred_end: float,
              gt_start: float, gt_end: float,
              threshold: float = 0.5) -> bool:
    """Return True if pred and gt intervals overlap by ≥ threshold."""
    overlap = max(0.0, min(pred_end, gt_end) - max(pred_start, gt_start))
    shorter = min(pred_end - pred_start, gt_end - gt_start)
    if shorter <= 0:
        return False
    return (overlap / shorter) >= threshold


def evaluate(
    predicted: list[tuple[float, float]],   # list of (start, end)
    ground_truth: list[GTInterval],
    scenario: str = "",
    overlap_threshold: float = 0.4,
) -> EvalMetrics:
    """Compute TP/FP/FN and derived metrics."""
    matched_gt  = set()
    matched_pred = set()

    for p_i, (ps, pe) in enumerate(predicted):
        for g_i, gt in enumerate(ground_truth):
            if g_i in matched_gt:
                continue
            if _overlaps(ps, pe, gt.start, gt.end, overlap_threshold):
                matched_gt.add(g_i)
                matched_pred.add(p_i)
                break

    tp = len(matched_pred)
    fp = len(predicted) - tp
    fn = len(ground_truth) - len(matched_gt)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)

    return EvalMetrics(
        scenario        = scenario,
        true_count      = len(ground_truth),
        pred_count      = len(predicted),
        tp              = tp,
        fp              = fp,
        fn              = fn,
        precision       = precision,
        recall          = recall,
        f1              = f1,
        abs_count_error = abs(len(predicted) - len(ground_truth)),
    )


# ---------------------------------------------------------------------------
# Ground-truth definitions for synthetic scenarios
# (Derived analytically from the generation parameters)
# ---------------------------------------------------------------------------

# three_complete_squats: 3 reps × 3 s period, starting at t=0.5
_GT_THREE = [
    GTInterval(0.5,  3.5,  "rep1"),
    GTInterval(3.5,  6.5,  "rep2"),
    GTInterval(6.5,  9.5,  "rep3"),
]

# fast_squat: 4 reps × 1 s period
_GT_FAST = [
    GTInterval(i, i + 1.0, f"rep{i+1}") for i in range(4)
]

# slow_squat: 2 reps × 6 s period
_GT_SLOW = [
    GTInterval(0.0, 6.0, "rep1"),
    GTInterval(6.0, 12.0, "rep2"),
]


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------

def main():
    from engine.examples.generate_synthetic_data import get_scenario
    from engine.analyzer import analyze_movement

    test_cases = [
        ("three_complete_squats", _GT_THREE),
        ("fast_squat",            _GT_FAST),
        ("slow_squat",            _GT_SLOW),
    ]

    print("=" * 80)
    print("Velo Engine — Repetition Counting Evaluation")
    print("(Synthetic data only — NOT representative of real-world accuracy)")
    print("=" * 80)

    all_metrics: list[EvalMetrics] = []

    for scenario, gt_intervals in test_cases:
        frames = get_scenario(scenario)
        result = analyze_movement(frames, exercise="squat")

        predicted = [
            (r.start_time, r.end_time)
            for r in result.reps
            if r.valid
        ]

        metrics = evaluate(predicted, gt_intervals, scenario=scenario)
        all_metrics.append(metrics)
        print(metrics)

    print()
    # Aggregate
    if all_metrics:
        mean_f1    = sum(m.f1      for m in all_metrics) / len(all_metrics)
        mean_prec  = sum(m.precision for m in all_metrics) / len(all_metrics)
        mean_rec   = sum(m.recall  for m in all_metrics) / len(all_metrics)
        mean_err   = sum(m.abs_count_error for m in all_metrics) / len(all_metrics)
        print(f"{'AGGREGATE':<35}  "
              f"Mean Prec={mean_prec:.2f}  "
              f"Mean Rec={mean_rec:.2f}  "
              f"Mean F1={mean_f1:.2f}  "
              f"Mean |Err|={mean_err:.1f}")
    print()
    print("Disclaimer: metrics are computed on synthetic data only.")


if __name__ == "__main__":
    main()
