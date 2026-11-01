"""
phase_detector.py — Movement-phase finite-state machine
========================================================

Architecture
------------
The module separates two concerns:

1. **StateMachine** — a generic FSM that manages state, transition guards,
   hysteresis, and minimum-duration constraints.

2. **SquatPhaseDetector** — a squat-specific wrapper that feeds knee-angle
   observations into the FSM and maps angle values to transitions.

Design notes
------------
* State transitions are driven by **angle values and their temporal
  derivatives** rather than heuristic frame counts.
* Hysteresis is implemented as a "dead-band": once a threshold is crossed in
  one direction it must be crossed by an additional hysteresis amount before
  transitioning back.
* Minimum-duration guards prevent noise-induced micro-transitions.
* A dedicated ``UNKNOWN`` state marks frames where the available data is
  insufficient for confident phase classification.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from .config import SquatPhaseConfig


# ---------------------------------------------------------------------------
# Phase enumeration
# ---------------------------------------------------------------------------

class SquatPhase(Enum):
    UNKNOWN    = auto()
    STANDING   = auto()
    DESCENDING = auto()
    BOTTOM     = auto()
    ASCENDING  = auto()


# ---------------------------------------------------------------------------
# Phase event (one per processed frame)
# ---------------------------------------------------------------------------

@dataclass
class PhaseEvent:
    """The phase classification result for a single frame."""
    timestamp:   float
    phase:       SquatPhase
    angle:       float          # measured knee angle (degrees)
    velocity:    float          # angular velocity (deg/s)
    confidence:  float          # classification confidence in [0, 1]
    uncertain:   bool           # True when data is insufficient
    note:        str = ""


# ---------------------------------------------------------------------------
# Generic finite-state machine
# ---------------------------------------------------------------------------

class StateMachine:
    """Minimal generic FSM for time-series state tracking.

    States are arbitrary comparable objects (e.g. enum members).
    Transitions are guarded by a callable that returns True when the
    transition should fire.

    Parameters
    ----------
    initial_state:
        The state assigned before the first measurement.
    min_duration_s:
        A transition is only accepted if the candidate new state persists
        for at least this many seconds.
    min_stable_frames:
        Minimum consecutive frames in the candidate state before committing.
    """

    def __init__(
        self,
        initial_state: object,
        min_duration_s: float = 0.15,
        min_stable_frames: int = 3,
    ) -> None:
        self.state               = initial_state
        self._min_duration_s     = min_duration_s
        self._min_stable_frames  = min_stable_frames
        self._state_entry_time:  float = -math.inf
        self._candidate:         object= initial_state
        self._candidate_since:   float = -math.inf
        self._candidate_frames:  int   = 0
        self._history:           list[tuple[float, object]] = []

    def transition_to(self, new_state: object, timestamp: float) -> bool:
        """Suggest a state change.  Returns True if a commit happened."""
        if new_state == self._candidate:
            self._candidate_frames += 1
        else:
            self._candidate         = new_state
            self._candidate_since   = timestamp
            self._candidate_frames  = 1

        duration_ok = (timestamp - self._candidate_since) >= self._min_duration_s
        frames_ok   = self._candidate_frames >= self._min_stable_frames

        if (duration_ok or frames_ok) and self._candidate != self.state:
            self.state             = self._candidate
            self._state_entry_time = timestamp
            self._history.append((timestamp, self.state))
            return True
        return False

    def time_in_state(self, now: float) -> float:
        """Seconds spent in the current state."""
        return now - self._state_entry_time if math.isfinite(self._state_entry_time) else 0.0

    @property
    def history(self) -> list[tuple[float, object]]:
        return list(self._history)


# ---------------------------------------------------------------------------
# Squat phase detector
# ---------------------------------------------------------------------------

class SquatPhaseDetector:
    """Detect squat phases from a stream of knee-angle observations.

    Parameters
    ----------
    cfg:
        Squat phase configuration.
    """

    def __init__(self, cfg: SquatPhaseConfig = SquatPhaseConfig()) -> None:
        self._cfg = cfg
        self._fsm = StateMachine(
            initial_state=SquatPhase.UNKNOWN,
            min_duration_s=cfg.min_state_duration_s,
            min_stable_frames=cfg.min_stable_frames,
        )
        self._prev_angle: Optional[float] = None
        self._prev_ts:    Optional[float] = None
        self._velocity_buffer: list[float] = []   # small ring for smoothing
        self._events: list[PhaseEvent] = []

    @property
    def current_phase(self) -> SquatPhase:
        return self._fsm.state

    @property
    def events(self) -> list[PhaseEvent]:
        return list(self._events)

    def reset(self) -> None:
        self.__init__(self._cfg)   # type: ignore[misc]

    def _estimate_velocity(self, angle: float, timestamp: float) -> float:
        """Return smoothed angular velocity (deg/s), NaN when unavailable."""
        if (
            self._prev_angle is not None
            and self._prev_ts is not None
            and math.isfinite(angle)
            and math.isfinite(self._prev_angle)
        ):
            dt = timestamp - self._prev_ts
            if dt > 1e-6:
                v = (angle - self._prev_angle) / dt
                self._velocity_buffer.append(v)
                # Keep only velocities inside the window
                self._velocity_buffer = self._velocity_buffer[-5:]
                return float(sum(self._velocity_buffer) / len(self._velocity_buffer))
        return float("nan")

    def _classify(
        self,
        angle: float,
        velocity: float,
        timestamp: float,
    ) -> tuple[SquatPhase, float, bool]:
        """Map angle + velocity → candidate phase, confidence, uncertainty."""
        cfg = self._cfg
        uncertain = False

        if not math.isfinite(angle):
            return SquatPhase.UNKNOWN, 0.0, True

        # Determine kinematic direction
        vel_valid  = math.isfinite(velocity)
        moving     = vel_valid and abs(velocity) >= cfg.min_velocity_deg_s
        descending = vel_valid and velocity < -cfg.min_velocity_deg_s  # angle decreasing
        ascending  = vel_valid and velocity > cfg.min_velocity_deg_s   # angle increasing

        current    = self._fsm.state
        h          = cfg.hysteresis_deg

        # --- STANDING --- (angle near full extension)
        standing_thresh = cfg.standing_threshold_deg
        if current == SquatPhase.STANDING:
            standing_thresh -= h  # harder to leave standing
        if angle >= standing_thresh and not descending:
            conf = min(1.0, (angle - cfg.standing_threshold_deg + h) / (h + 1.0))
            return SquatPhase.STANDING, max(0.3, conf), False

        # --- BOTTOM --- (deep squat, low angle)
        bottom_thresh = cfg.bottom_threshold_deg
        if current == SquatPhase.BOTTOM:
            bottom_thresh += h  # harder to leave bottom
        if angle <= bottom_thresh and not ascending:
            conf = min(1.0, (cfg.bottom_threshold_deg + h - angle) / (h + 1.0))
            return SquatPhase.BOTTOM, max(0.3, conf), False

        # --- DESCENDING / ASCENDING (mid-range) ---
        if descending:
            return SquatPhase.DESCENDING, 0.7, False
        if ascending:
            return SquatPhase.ASCENDING, 0.7, False

        # Mid-range, no clear velocity
        if current in (SquatPhase.DESCENDING, SquatPhase.ASCENDING):
            return current, 0.4, True   # keep current phase, uncertain
        if current == SquatPhase.BOTTOM:
            return SquatPhase.BOTTOM, 0.5, True

        uncertain = True
        return SquatPhase.UNKNOWN, 0.2, uncertain

    def update(self, angle: float, timestamp: float) -> PhaseEvent:
        """Feed one angle observation at *timestamp*.

        Parameters
        ----------
        angle:
            Knee angle in degrees (float('nan') when unavailable).
        timestamp:
            Frame timestamp in seconds.

        Returns
        -------
        PhaseEvent
            The phase classification for this frame.
        """
        velocity = self._estimate_velocity(angle, timestamp)

        candidate, confidence, uncertain = self._classify(angle, velocity, timestamp)
        self._fsm.transition_to(candidate, timestamp)

        if math.isfinite(angle):
            self._prev_angle = angle
        self._prev_ts = timestamp

        event = PhaseEvent(
            timestamp=timestamp,
            phase=self._fsm.state,
            angle=angle,
            velocity=velocity,
            confidence=confidence,
            uncertain=uncertain,
        )
        self._events.append(event)
        return event

    def process_sequence(
        self,
        angles: list[float],
        timestamps: list[float],
    ) -> list[PhaseEvent]:
        """Process a batch of angle observations.

        Resets detector state before processing.
        """
        self.reset()
        return [self.update(a, t) for a, t in zip(angles, timestamps)]


# ---------------------------------------------------------------------------
# Phase timeline summary
# ---------------------------------------------------------------------------

@dataclass
class PhaseInterval:
    """A contiguous interval with the same phase label."""
    phase:      SquatPhase
    start_time: float
    end_time:   float

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


def build_phase_timeline(events: list[PhaseEvent]) -> list[PhaseInterval]:
    """Compress a per-frame event list into contiguous phase intervals."""
    if not events:
        return []
    intervals: list[PhaseInterval] = []
    current_phase = events[0].phase
    start_time    = events[0].timestamp

    for ev in events[1:]:
        if ev.phase != current_phase:
            intervals.append(PhaseInterval(
                phase=current_phase,
                start_time=start_time,
                end_time=ev.timestamp,
            ))
            current_phase = ev.phase
            start_time    = ev.timestamp

    # Final interval
    intervals.append(PhaseInterval(
        phase=current_phase,
        start_time=start_time,
        end_time=events[-1].timestamp,
    ))
    return intervals
