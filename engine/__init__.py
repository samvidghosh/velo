"""
Velo Movement Analysis Engine
==============================
A pure Python library for analyzing exercise movements from
timestamped human body-joint coordinates.

Sub-modules
-----------
geometry        - Joint-angle calculations and kinematics
preprocessing   - Pose filtering and validation
phase_detector  - Movement-phase finite-state machine
rep_counter     - Repetition counting FSM
exercise_rules  - Configurable technique observation engine
analyzer        - Top-level orchestration
config          - Default exercise profiles and parameters
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("velo-engine")
except PackageNotFoundError:
    __version__ = "0.1.0"

__all__ = [
    "geometry",
    "preprocessing",
    "phase_detector",
    "rep_counter",
    "exercise_rules",
    "analyzer",
    "config",
]
