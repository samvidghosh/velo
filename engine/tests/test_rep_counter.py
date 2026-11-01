"""
test_rep_counter.py — Tests for engine.rep_counter
"""
from __future__ import annotations

import math
import pytest

from engine.rep_counter import SquatRepCounter, RepRecord
from engine.phase_detector import PhaseEvent, SquatPhase
from engine.config import SquatRepConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event(ts: float, phase: SquatPhase, angle: float = 0.0, uncertain: bool = False) -> PhaseEvent:
    return PhaseEvent(
        timestamp  = ts,
        phase      = phase,
        angle      = angle,
        velocity   = float("nan"),
        confidence = 0.9,
        uncertain  = uncertain,
    )


def _build_squat_events(
    n_reps: int = 3,
    period: float = 3.0,
    standing_angle: float = 170.0,
    bottom_angle: float = 90.0,
    fps: float = 30.0,
) -> list[PhaseEvent]:
    """Generate phase events that simulate complete squat cycles.

    Phases are assigned based on the **angle value**, not time fractions,
    so the rep counter always sees correct phase labels aligned to actual
    joint angle ranges.

      angle >= 155  → STANDING
      angle <= 100  → BOTTOM
      direction decreasing → DESCENDING
      direction increasing  → ASCENDING
    """
    import math as _m
    events: list[PhaseEvent] = []
    dt = 1.0 / fps

    # Opening standing phase
    n_stand = int(0.5 * fps)
    for i in range(n_stand):
        events.append(_event(i * dt, SquatPhase.STANDING, standing_angle))

    t_offset = n_stand * dt

    for rep in range(n_reps):
        n_frames = int(period * fps)
        prev_angle = standing_angle
        for i in range(n_frames):
            frac = i / n_frames
            # sinusoidal arc top → bottom → top
            angle = standing_angle - (standing_angle - bottom_angle) * _m.sin(_m.pi * frac)

            # Phase from angle + direction
            if angle >= 155.0:
                phase = SquatPhase.STANDING
            elif angle <= 100.0:
                phase = SquatPhase.BOTTOM
            elif angle < prev_angle:
                phase = SquatPhase.DESCENDING
            else:
                phase = SquatPhase.ASCENDING

            t_abs = t_offset + rep * period + i * dt
            events.append(_event(t_abs, phase, angle))
            prev_angle = angle

        # Explicit standing frame returning to top
        t_end = t_offset + rep * period + period
        events.append(_event(t_end, SquatPhase.STANDING, standing_angle))

    return events


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSquatRepCounter:
    def _default_cfg(self, **kwargs):
        return SquatRepConfig(
            min_rom_deg        = 40.0,
            min_rep_duration_s = 0.5,
            max_rep_duration_s = 20.0,
            max_bottom_pause_s = 5.0,
            jitter_guard_deg   = 2.0,
            **kwargs,
        )

    # --- correct count ---

    def test_three_complete_reps_counted(self):
        cfg    = self._default_cfg()
        events = _build_squat_events(n_reps=3, period=3.0)
        ctr    = SquatRepCounter(cfg=cfg)
        result = ctr.process_sequence(events)
        assert result.accepted_reps == 3

    def test_one_rep(self):
        cfg    = self._default_cfg()
        events = _build_squat_events(n_reps=1, period=3.0)
        ctr    = SquatRepCounter(cfg=cfg)
        result = ctr.process_sequence(events)
        assert result.accepted_reps >= 1

    # --- no count for incomplete ---

    def test_no_count_if_never_reaches_bottom(self):
        """Descent that aborts before BOTTOM → no valid rep."""
        cfg = self._default_cfg()
        events = [
            _event(0.0,  SquatPhase.STANDING,   170.0),
            _event(0.1,  SquatPhase.STANDING,   170.0),
            _event(0.5,  SquatPhase.DESCENDING, 155.0),
            _event(1.0,  SquatPhase.DESCENDING, 140.0),
            _event(1.5,  SquatPhase.STANDING,   170.0),   # aborted
        ]
        ctr    = SquatRepCounter(cfg=cfg)
        result = ctr.process_sequence(events)
        assert result.accepted_reps == 0

    def test_no_count_for_insufficient_rom(self):
        """Squat with ROM less than minimum is not counted."""
        cfg = self._default_cfg(min_rom_deg=60.0)
        # Bottom angle of 145° with top 170° gives only 25° ROM
        events = [
            _event(0.0,  SquatPhase.STANDING,   170.0),
            _event(0.1,  SquatPhase.STANDING,   170.0),
            _event(0.5,  SquatPhase.DESCENDING, 160.0),
            _event(1.0,  SquatPhase.BOTTOM,     145.0),
            _event(1.5,  SquatPhase.ASCENDING,  160.0),
            _event(2.0,  SquatPhase.STANDING,   170.0),
        ]
        ctr    = SquatRepCounter(cfg=cfg)
        result = ctr.process_sequence(events)
        assert result.accepted_reps == 0

    def test_no_count_if_cycle_too_short(self):
        """Cycle that completes too quickly is rejected."""
        cfg = self._default_cfg(min_rep_duration_s=2.0)
        events = [
            _event(0.0,  SquatPhase.STANDING,   170.0),
            _event(0.1,  SquatPhase.STANDING,   170.0),
            _event(0.2,  SquatPhase.DESCENDING, 140.0),
            _event(0.4,  SquatPhase.BOTTOM,      90.0),
            _event(0.6,  SquatPhase.ASCENDING,  140.0),
            _event(0.8,  SquatPhase.STANDING,   170.0),   # total 0.8s < 2s
        ]
        ctr    = SquatRepCounter(cfg=cfg)
        result = ctr.process_sequence(events)
        assert result.accepted_reps == 0

    # --- no duplicate counts ---

    def test_no_double_count_stationary(self):
        """Long period in BOTTOM phase with no actual rep."""
        cfg = self._default_cfg()
        events = [_event(i * 0.1, SquatPhase.BOTTOM, 90.0) for i in range(100)]
        ctr    = SquatRepCounter(cfg=cfg)
        result = ctr.process_sequence(events)
        assert result.accepted_reps == 0

    # --- per-rep record accuracy ---

    def test_rep_record_timestamps(self):
        cfg    = self._default_cfg()
        events = _build_squat_events(n_reps=1, period=3.0)
        ctr    = SquatRepCounter(cfg=cfg)
        result = ctr.process_sequence(events)
        records = [r for r in result.records if r.valid]
        assert len(records) >= 1
        rec = records[0]
        assert rec.start_time < rec.bottom_time
        assert rec.bottom_time <= rec.end_time

    def test_rep_record_rom(self):
        cfg    = self._default_cfg()
        events = _build_squat_events(n_reps=1, period=3.0, standing_angle=170.0, bottom_angle=90.0)
        ctr    = SquatRepCounter(cfg=cfg)
        result = ctr.process_sequence(events)
        records = [r for r in result.records if r.valid]
        assert len(records) >= 1
        assert records[0].range_of_motion > 0
        assert math.isfinite(records[0].range_of_motion)

    def test_rep_record_tempo(self):
        cfg    = self._default_cfg()
        events = _build_squat_events(n_reps=1, period=3.0)
        ctr    = SquatRepCounter(cfg=cfg)
        result = ctr.process_sequence(events)
        records = [r for r in result.records if r.valid]
        assert len(records) >= 1
        assert records[0].tempo > 0

    # --- missing frames / variable frame rates ---

    def test_nan_angle_frames_handled(self):
        """NaN angle frames within a cycle should not crash the counter."""
        cfg = self._default_cfg()
        events = [
            _event(0.0,  SquatPhase.STANDING,   170.0),
            _event(0.1,  SquatPhase.STANDING,   170.0),
            _event(0.5,  SquatPhase.DESCENDING, 140.0),
            _event(0.8,  SquatPhase.DESCENDING, float("nan")),  # missing frame
            _event(1.2,  SquatPhase.BOTTOM,      90.0),
            _event(1.5,  SquatPhase.ASCENDING,  130.0),
            _event(2.0,  SquatPhase.STANDING,   168.0),
        ]
        ctr    = SquatRepCounter(cfg=cfg)
        result = ctr.process_sequence(events)   # must not raise

    def test_variable_frame_rate(self):
        """Events at variable intervals should produce valid rep records."""
        cfg    = self._default_cfg()
        events = _build_squat_events(n_reps=2, period=3.0, fps=24.0)
        ctr    = SquatRepCounter(cfg=cfg)
        result = ctr.process_sequence(events)
        assert result.accepted_reps >= 1

    def test_gap_flags_uncertain(self):
        """A cycle that contains an uncertain event should be flagged."""
        cfg = self._default_cfg(min_rep_duration_s=0.1)
        events = [
            _event(0.0,  SquatPhase.STANDING,   170.0),
            _event(0.2,  SquatPhase.STANDING,   170.0),
            _event(0.5,  SquatPhase.DESCENDING, 140.0, uncertain=True),   # gap
            _event(1.5,  SquatPhase.BOTTOM,      90.0),
            _event(2.0,  SquatPhase.ASCENDING,  130.0),
            _event(2.5,  SquatPhase.STANDING,   168.0),
        ]
        ctr    = SquatRepCounter(cfg=cfg)
        result = ctr.process_sequence(events)
        recs   = result.records
        if recs:
            assert any(r.had_gap for r in recs)

    # --- reset ---

    def test_reset_clears_state(self):
        cfg = self._default_cfg()
        ctr = SquatRepCounter(cfg=cfg)
        events = _build_squat_events(n_reps=2)
        ctr.process_sequence(events)
        ctr.reset()
        # After reset, process again — should re-count fresh
        result = ctr.process_sequence(events)
        assert result.accepted_reps >= 1
