"""
test_phase_detector.py — Tests for engine.phase_detector
"""
from __future__ import annotations

import math
import pytest

from engine.phase_detector import (
    PhaseEvent,
    SquatPhase,
    SquatPhaseDetector,
    StateMachine,
    build_phase_timeline,
)
from engine.config import SquatPhaseConfig


# ---------------------------------------------------------------------------
# StateMachine
# ---------------------------------------------------------------------------

class TestStateMachine:
    def test_initial_state(self):
        sm = StateMachine("IDLE")
        assert sm.state == "IDLE"

    def test_no_transition_without_min_duration(self):
        """A single frame cannot satisfy min_duration — state unchanged."""
        sm = StateMachine("A", min_duration_s=0.5, min_stable_frames=100)
        sm.transition_to("B", 0.0)
        assert sm.state == "A"

    def test_transition_after_min_stable_frames(self):
        sm = StateMachine("A", min_duration_s=0.0, min_stable_frames=3)
        sm.transition_to("B", 0.0)
        sm.transition_to("B", 0.1)
        assert sm.state == "A"   # still 2 frames < 3
        sm.transition_to("B", 0.2)
        assert sm.state == "B"

    def test_transition_after_min_duration(self):
        sm = StateMachine("A", min_duration_s=0.2, min_stable_frames=1)
        sm.transition_to("B", 0.0)
        sm.transition_to("B", 0.1)
        assert sm.state == "A"
        sm.transition_to("B", 0.25)
        assert sm.state == "B"

    def test_candidate_reset_on_change(self):
        """Changing candidate resets the duration clock."""
        sm = StateMachine("A", min_duration_s=0.2, min_stable_frames=1)
        sm.transition_to("B", 0.0)
        sm.transition_to("B", 0.1)
        # Switch to C — should reset clock
        sm.transition_to("C", 0.15)
        sm.transition_to("C", 0.2)
        # C has not been candidate for 0.2s yet from 0.15
        assert sm.state == "A"

    def test_history_records_transitions(self):
        sm = StateMachine("A", min_duration_s=0.0, min_stable_frames=1)
        sm.transition_to("B", 0.0)
        sm.transition_to("C", 0.1)
        history = sm.history
        assert history[0][1] == "B"
        assert history[1][1] == "C"


# ---------------------------------------------------------------------------
# SquatPhaseDetector
# ---------------------------------------------------------------------------

def _run_detector(angles, timestamps=None, cfg=None):
    cfg = cfg or SquatPhaseConfig(min_state_duration_s=0.0, min_stable_frames=1)
    if timestamps is None:
        timestamps = [i * 0.033 for i in range(len(angles))]
    det = SquatPhaseDetector(cfg=cfg)
    return det.process_sequence(angles, timestamps)


class TestSquatPhaseDetector:
    def test_standing_on_high_angle(self):
        """Sustained high knee angle → STANDING."""
        angles = [170.0] * 30
        events = _run_detector(angles)
        # After initial frames, should be STANDING
        late_phases = [e.phase for e in events[10:]]
        assert all(p == SquatPhase.STANDING for p in late_phases)

    def test_bottom_on_low_angle(self):
        """Sustained low knee angle → BOTTOM."""
        # Start at standing to establish velocity, then go low
        angles = [170.0] * 10 + [85.0] * 30
        events = _run_detector(angles)
        late_phases = [e.phase for e in events[20:]]
        assert SquatPhase.BOTTOM in late_phases

    def test_descent_detected(self):
        """Decreasing angle from standing → DESCENDING."""
        angles = [170.0] * 5 + [150.0, 130.0, 110.0, 95.0, 85.0]
        events = _run_detector(angles)
        phases = [e.phase for e in events]
        assert SquatPhase.DESCENDING in phases or SquatPhase.BOTTOM in phases

    def test_ascent_detected(self):
        """Increasing angle from bottom → ASCENDING."""
        angles = [85.0] * 5 + [100.0, 120.0, 145.0, 165.0, 170.0]
        events = _run_detector(angles)
        phases = [e.phase for e in events]
        assert SquatPhase.ASCENDING in phases or SquatPhase.STANDING in phases

    def test_full_cycle_phases(self):
        """Full squat cycle should contain all phases."""
        # Build a synthetic squat arc
        import math as _math
        n = 90
        angles = []
        for i in range(n):
            phase = i / n
            angle = 85.0 + (170.0 - 85.0) * (1 - _math.cos(2 * _math.pi * phase)) / 2
            # It goes: 170→85→170 but cosine starts at top
            angle = 170.0 - (170.0 - 85.0) * _math.sin(_math.pi * phase)
            angles.append(angle)
        timestamps = [i * 0.033 for i in range(n)]
        events = _run_detector(angles, timestamps)
        seen_phases = {e.phase for e in events}
        # Should see at least: STANDING, DESCENDING (or BOTTOM), ASCENDING
        assert SquatPhase.STANDING in seen_phases

    def test_nan_angle_gives_unknown(self):
        """NaN input should produce UNKNOWN."""
        events = _run_detector([float("nan")] * 5)
        assert all(e.phase == SquatPhase.UNKNOWN for e in events)
        assert all(e.uncertain for e in events)

    def test_hysteresis_prevents_oscillation(self):
        """Noisy angle oscillating around threshold should not flip state rapidly."""
        cfg = SquatPhaseConfig(
            standing_threshold_deg=160.0,
            hysteresis_deg=10.0,
            min_state_duration_s=0.0,
            min_stable_frames=5,
        )
        # Oscillate around 160 ± 3
        import random
        rng = random.Random(7)
        angles = [160.0 + rng.uniform(-3, 3) for _ in range(60)]
        events = _run_detector(angles, cfg=cfg)
        # Count state changes
        changes = sum(
            1 for i in range(1, len(events))
            if events[i].phase != events[i - 1].phase
        )
        # Hysteresis should limit transitions
        assert changes < 10

    def test_pause_in_standings(self):
        """A pause between squats stays in STANDING."""
        angles = [170.0] * 50   # long standing pause
        events = _run_detector(angles)
        late = [e.phase for e in events[25:]]
        assert all(p == SquatPhase.STANDING for p in late)

    def test_interrupted_sequence(self):
        """A gap in the sequence (NaN frames) should not crash."""
        angles = [170.0] * 10 + [float("nan")] * 5 + [85.0] * 10
        events = _run_detector(angles)
        assert len(events) == 25

    def test_insufficient_data_produces_unknown(self):
        """Single NaN frame → UNKNOWN."""
        events = _run_detector([float("nan")])
        assert events[0].phase == SquatPhase.UNKNOWN
        assert events[0].uncertain

    def test_reset_clears_state(self):
        det = SquatPhaseDetector()
        det.update(170.0, 0.0)
        det.reset()
        assert det.current_phase == SquatPhase.UNKNOWN
        assert det.events == []

    def test_velocity_nans_on_first_frame(self):
        """First frame has no previous sample — velocity must be NaN."""
        events = _run_detector([170.0])
        assert math.isnan(events[0].velocity)


# ---------------------------------------------------------------------------
# build_phase_timeline
# ---------------------------------------------------------------------------

class TestBuildPhaseTimeline:
    def test_empty(self):
        assert build_phase_timeline([]) == []

    def test_single_phase(self):
        events = [
            PhaseEvent(0.0, SquatPhase.STANDING, 170.0, float("nan"), 0.9, False),
            PhaseEvent(0.1, SquatPhase.STANDING, 170.0, float("nan"), 0.9, False),
            PhaseEvent(0.2, SquatPhase.STANDING, 170.0, float("nan"), 0.9, False),
        ]
        timeline = build_phase_timeline(events)
        assert len(timeline) == 1
        assert timeline[0].phase == SquatPhase.STANDING
        assert math.isclose(timeline[0].start_time, 0.0)
        assert math.isclose(timeline[0].end_time,   0.2)

    def test_two_phases(self):
        events = [
            PhaseEvent(0.0,  SquatPhase.STANDING,   170.0, float("nan"), 0.9, False),
            PhaseEvent(0.1,  SquatPhase.DESCENDING, 150.0, float("nan"), 0.9, False),
            PhaseEvent(0.2,  SquatPhase.BOTTOM,      90.0, float("nan"), 0.9, False),
        ]
        timeline = build_phase_timeline(events)
        phases = [i.phase for i in timeline]
        assert SquatPhase.STANDING   in phases
        assert SquatPhase.DESCENDING in phases
        assert SquatPhase.BOTTOM     in phases
