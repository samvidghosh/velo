"""
rep_counter.py — Repetition counting finite-state machine
==========================================================

Design
------
The counter tracks the full cycle:

    IDLE → STANDING → DESCENDING → BOTTOM → ASCENDING → STANDING (count++)

Validity gates
--------------
A rep is **counted** only when ALL of the following hold:

1. The cycle passed through every required phase in order.
2. The minimum range of motion was achieved.
3. The total cycle duration is within the configured bounds.
4. The bottom pause did not exceed the maximum allowed.
5. No long data gap interrupted the cycle.

Rep data
--------
Each completed cycle (whether counted or not) is recorded as a ``RepRecord``
with start/end timestamps, peak angle, range of motion, tempo, and a flag
indicating whether it was accepted as a valid rep.

The counter explicitly does NOT depend on a fixed frame rate — all durations
are computed from actual timestamps.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from .config import SquatRepConfig
from .phase_detector import PhaseEvent, SquatPhase


# ---------------------------------------------------------------------------
# Internal FSM states
# ---------------------------------------------------------------------------

class _RepState(Enum):
    IDLE       = auto()  # waiting for valid starting position
    STANDING   = auto()  # confirmed starting position
    DESCENDING = auto()
    BOTTOM     = auto()
    ASCENDING  = auto()
    COMPLETE   = auto()  # cycle ended; evaluate validity


# ---------------------------------------------------------------------------
# Per-repetition record
# ---------------------------------------------------------------------------

@dataclass
class RepRecord:
    """All measurements for one detected movement cycle."""

    index:          int           # 1-based cycle index (all cycles, not just valid)
    start_time:     float         # timestamp of descent start
    bottom_time:    float         # timestamp of deepest point
    end_time:       float         # timestamp of return to standing
    peak_angle:     float         # minimum knee angle at bottom (degrees)
    top_angle:      float         # knee angle at standing (degrees)
    range_of_motion: float        # top_angle − peak_angle (degrees)
    tempo:          float         # total cycle duration (seconds)

    #: True = meets all counting criteria; False = detected but invalid
    valid:          bool

    #: Human-readable reasons this cycle was NOT counted (empty if valid).
    rejection_reasons: list[str]  = field(default_factory=list)

    #: Fraction of frames in this cycle that were valid (data quality).
    data_quality:   float         = 1.0

    #: True if a data gap interrupted this cycle.
    had_gap:        bool          = False

    #: True if the evidence for this rep has low confidence.
    uncertain:      bool          = False


# ---------------------------------------------------------------------------
# Counter result summary
# ---------------------------------------------------------------------------

@dataclass
class CounterResult:
    """Summary returned after processing a complete sequence."""

    total_cycles:      int              # all detected cycles
    accepted_reps:     int              # cycles meeting validity criteria
    records:           list[RepRecord]  # one per cycle
    warnings:          list[str]
    data_quality:      float            # overall fraction valid frames


# ---------------------------------------------------------------------------
# Rep counter
# ---------------------------------------------------------------------------

class SquatRepCounter:
    """Count squat repetitions from a stream of PhaseEvents.

    Parameters
    ----------
    cfg:
        Rep-counting configuration.
    """

    def __init__(self, cfg: SquatRepConfig = SquatRepConfig()) -> None:
        self._cfg              = cfg
        self._state            = _RepState.IDLE
        self._cycle_index      = 0
        self._records:         list[RepRecord] = []
        self._warnings:        list[str] = []
        self._valid_frames     = 0
        self._total_frames     = 0

        # Per-cycle accumulators
        self._cycle_start:     Optional[float] = None
        self._bottom_time:     Optional[float] = None
        self._bottom_angle:    Optional[float] = None  # min angle seen at bottom
        self._top_angle:       Optional[float] = None  # angle at start of descent
        self._bottom_entry_ts: Optional[float] = None  # when BOTTOM phase began
        self._cycle_had_gap    = False
        self._cycle_valid_frames = 0
        self._cycle_total_frames = 0
        self._prev_angle:      Optional[float] = None

    def reset(self) -> None:
        self.__init__(self._cfg)   # type: ignore[misc]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _start_cycle(self, event: PhaseEvent) -> None:
        self._cycle_index        += 1
        self._state               = _RepState.DESCENDING
        self._cycle_start         = event.timestamp
        self._bottom_time         = None
        self._bottom_angle        = None
        self._bottom_entry_ts     = None
        self._cycle_had_gap       = event.uncertain   # uncertain start
        self._cycle_valid_frames  = 1
        self._cycle_total_frames  = 1

    def _track_bottom(self, event: PhaseEvent) -> None:
        """Record the deepest angle seen while in BOTTOM phase."""
        a = event.angle
        if math.isfinite(a):
            if self._bottom_angle is None or a < self._bottom_angle:
                self._bottom_angle = a
                self._bottom_time  = event.timestamp
        if self._bottom_entry_ts is None:
            self._bottom_entry_ts = event.timestamp

    def _reset_cycle(self) -> None:
        """Abandon the current cycle without recording it."""
        self._state              = _RepState.IDLE
        self._cycle_start        = None
        self._bottom_time        = None
        self._bottom_angle       = None
        self._top_angle          = None
        self._bottom_entry_ts    = None
        self._cycle_had_gap      = False
        self._cycle_valid_frames = 0
        self._cycle_total_frames = 0

    def _evaluate_cycle(self, end_time: float, end_angle: float) -> RepRecord:
        """Validate and record the completed cycle."""
        rejections: list[str] = []
        cfg = self._cfg

        start_time   = self._cycle_start or end_time
        bottom_time  = self._bottom_time or end_time
        peak_angle   = self._bottom_angle if self._bottom_angle is not None else float("nan")
        top_angle    = self._top_angle    if self._top_angle    is not None else end_angle
        rom          = top_angle - peak_angle if math.isfinite(top_angle) and math.isfinite(peak_angle) else float("nan")
        tempo        = end_time - start_time

        # Validity checks
        if not math.isfinite(rom) or rom < cfg.min_rom_deg:
            rejections.append(
                f"Insufficient range of motion: {rom:.1f}° < {cfg.min_rom_deg}°"
            )
        if tempo < cfg.min_rep_duration_s:
            rejections.append(
                f"Cycle too short: {tempo:.2f}s < {cfg.min_rep_duration_s}s"
            )
        if tempo > cfg.max_rep_duration_s:
            rejections.append(
                f"Cycle too long: {tempo:.2f}s > {cfg.max_rep_duration_s}s"
            )
        if self._bottom_entry_ts is not None:
            pause = bottom_time - self._bottom_entry_ts
            if pause > cfg.max_bottom_pause_s:
                rejections.append(
                    f"Bottom pause too long: {pause:.2f}s > {cfg.max_bottom_pause_s}s"
                )
        if self._cycle_had_gap:
            rejections.append("Data gap during cycle — quality uncertain.")

        frac = (
            self._cycle_valid_frames / self._cycle_total_frames
            if self._cycle_total_frames > 0 else 0.0
        )

        rec = RepRecord(
            index            = self._cycle_index,
            start_time       = start_time,
            bottom_time      = bottom_time,
            end_time         = end_time,
            peak_angle       = peak_angle,
            top_angle        = top_angle,
            range_of_motion  = rom if math.isfinite(rom) else float("nan"),
            tempo            = tempo,
            valid            = len(rejections) == 0,
            rejection_reasons= rejections,
            data_quality     = frac,
            had_gap          = self._cycle_had_gap,
            uncertain        = len(rejections) > 0 and self._cycle_had_gap,
        )
        return rec

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def update(self, event: PhaseEvent) -> Optional[RepRecord]:
        """Feed one PhaseEvent.

        Returns a RepRecord when a cycle completes, else None.
        """
        self._total_frames += 1
        self._cycle_total_frames += 1

        if event.valid if hasattr(event, "valid") else True:
            self._valid_frames += 1

        if math.isfinite(event.angle):
            self._cycle_valid_frames += 1

        if event.uncertain:
            self._cycle_had_gap = True

        phase = event.phase
        angle = event.angle
        ts    = event.timestamp

        # ----- IDLE: wait for a standing position -----
        if self._state == _RepState.IDLE:
            if phase == SquatPhase.STANDING:
                self._state     = _RepState.STANDING
                self._top_angle = angle if math.isfinite(angle) else None
            return None

        # ----- STANDING: ready to begin a rep -----
        if self._state == _RepState.STANDING:
            if phase == SquatPhase.DESCENDING:
                self._start_cycle(event)
            elif phase == SquatPhase.STANDING and math.isfinite(angle):
                self._top_angle = angle  # update with latest standing angle
            elif phase == SquatPhase.UNKNOWN:
                pass  # brief unknown, remain standing
            return None

        # ----- DESCENDING -----
        if self._state == _RepState.DESCENDING:
            if phase == SquatPhase.BOTTOM:
                self._state = _RepState.BOTTOM
                self._track_bottom(event)
            elif phase == SquatPhase.ASCENDING:
                # Missed bottom transition — treat current position as bottom
                if math.isfinite(angle):
                    self._bottom_angle = angle
                    self._bottom_time  = ts
                self._state = _RepState.ASCENDING
            elif phase == SquatPhase.STANDING:
                # Aborted descent — reset
                self._warnings.append(
                    f"Descent aborted at t={ts:.2f}s; cycle discarded."
                )
                self._reset_cycle()
                self._state     = _RepState.STANDING
                self._top_angle = angle if math.isfinite(angle) else None
            return None

        # ----- BOTTOM -----
        if self._state == _RepState.BOTTOM:
            self._track_bottom(event)
            if phase == SquatPhase.ASCENDING:
                self._state = _RepState.ASCENDING
            elif phase == SquatPhase.STANDING:
                # Very short bottom; transition directly
                self._state = _RepState.ASCENDING
            return None

        # ----- ASCENDING -----
        if self._state == _RepState.ASCENDING:
            if phase == SquatPhase.STANDING:
                self._state = _RepState.COMPLETE
                rec = self._evaluate_cycle(ts, angle)
                self._records.append(rec)
                self._reset_cycle()
                self._state     = _RepState.STANDING
                self._top_angle = angle if math.isfinite(angle) else None
                return rec
            elif phase == SquatPhase.DESCENDING:
                # Started descending again without reaching standing
                # Evaluate the abbreviated cycle as incomplete
                self._warnings.append(
                    f"Ascent incomplete at t={ts:.2f}s; cycle recorded as invalid."
                )
                if self._cycle_start is not None and self._bottom_angle is not None:
                    self._cycle_had_gap = True
                    rec = self._evaluate_cycle(ts, angle)
                    self._records.append(rec)
                self._reset_cycle()
                self._start_cycle(event)  # begin a new cycle
            return None

        return None

    def process_sequence(self, events: list[PhaseEvent]) -> CounterResult:
        """Process a complete phase-event sequence.

        Resets counter state before processing.
        """
        self.reset()
        for ev in events:
            self.update(ev)

        total  = len(self._records)
        valid  = sum(1 for r in self._records if r.valid)
        frac   = self._valid_frames / self._total_frames if self._total_frames else 0.0

        return CounterResult(
            total_cycles  = total,
            accepted_reps = valid,
            records       = list(self._records),
            warnings      = list(self._warnings),
            data_quality  = frac,
        )
