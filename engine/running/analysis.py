"""Pose-only running analysis; values are projected estimates, not clinical metrics."""
from __future__ import annotations
from collections import defaultdict
import numpy as np
from .schema import validate_pose_sequence, REQUIRED_LANDMARKS
from .geometry import projected_angles, get_point
from .signals import smooth, detect_cycle_candidates

def analyze_pose_sequence(payload: dict) -> dict:
    frames = validate_pose_sequence(payload)
    times = np.asarray([f.timestamp for f in frames], float)
    series: dict[str, list] = defaultdict(list)
    quality = []
    confidences = []
    for frame in frames:
        angles = projected_angles(frame.landmarks)
        for name, value in angles.items(): series[name].append(value)
        quality.append(sum(1 for name in REQUIRED_LANDMARKS if get_point(frame.landmarks, name) is not None) / len(REQUIRED_LANDMARKS))
        confidences.extend(float(frame.landmarks[name].get("confidence", 1.0)) for name in REQUIRED_LANDMARKS if get_point(frame.landmarks, name) is not None and np.isfinite(float(frame.landmarks[name].get("confidence", 1.0))))
    summaries = {}
    for name, values in series.items():
        valid = np.isfinite(np.asarray([np.nan if x is None else x for x in values], float))
        vals = np.asarray([np.nan if x is None else x for x in values], float)
        summaries[name] = ({"mean": float(np.nanmean(vals)), "range": float(np.nanmax(vals)-np.nanmin(vals)), "valid_fraction": float(valid.mean()), "unit": "degrees"} if valid.any() else {"mean": None,"range":None,"valid_fraction":0.0,"unit":"degrees","reason":"required landmarks missing or unreliable"})
    for side in ("left", "right"):
        key = f"{side}_knee_flexion_projected_deg"
        vals = np.asarray([np.nan if x is None else x for x in series[key]], float)
        series[f"{side}_knee_smoothed"] = smooth(vals).tolist() if np.isfinite(vals).sum() >= 3 else vals.tolist()
    left, right = summaries["left_knee_flexion_projected_deg"], summaries["right_knee_flexion_projected_deg"]
    symmetry = abs(left["mean"] - right["mean"]) if left["mean"] is not None and right["mean"] is not None else None
    gait = detect_cycle_candidates(times, series["left_knee_smoothed"])
    cycle_windows=[]
    event_times=[e["timestamp"] for e in gait["events"]]
    for start,end in zip(event_times,event_times[1:]):
        if end>start:
            cycle_windows.append({"start_s":start,"end_s":end,"duration_s":end-start,"phase_reference":"0–100% peak-to-peak projected knee cycle; not stance/swing"})
    frame_measurements=[]
    for i,timestamp in enumerate(times):
        frame_measurements.append({"timestamp":float(timestamp),"angles_projected_deg":{name:(None if value is None else float(value)) for name,values in series.items() if name.endswith("_projected_deg") for value in [values[i]]}})
    usable = float(np.mean(quality)) >= .5 and max(left["valid_fraction"], right["valid_fraction"]) >= .5
    findings = []
    if symmetry is not None:
        findings.append({"feature":"left_right_knee_projected_mean_difference","observed_deg":symmetry,"confidence":"low","message":"Projected knee-angle means are available for both sides; camera perspective can affect this comparison.","limitation":"This is a 2D image-plane estimate, not a 3D biomechanical angle."})
    else:
        findings.append({"feature":"left_right_knee_projected_mean_difference","observed_deg":None,"confidence":"unavailable","message":"Knee comparison unavailable because reliable landmarks were not present on both sides."})
    return {"schema_version":"1.0","status":"analysis_ready" if usable else "insufficient_evidence","input_quality":{"mean_landmark_fraction":float(np.mean(quality)),"mean_landmark_confidence":float(np.mean(confidences)) if confidences else None,"frame_count":len(frames),"duration_s":float(times[-1]-times[0]),"limitations":["2D Vision-style landmarks cannot provide absolute 3D joint angles.","Foot-ground contact is not established by these estimates."]},"measurements":summaries,"frame_measurements":frame_measurements,"gait":{"method":"projected knee-angle periodicity","events":gait["events"],"cycle_periods_s":gait["periods_s"],"cycle_windows":cycle_windows,"cadence_spm_estimate":gait["cadence_spm"],"phase_note":"Stance and swing are not assigned because these observations do not prove foot-ground contact.","status":gait["status"]},"findings":findings,"model":{"status":"not_trained","reason":"No expert-labelled running-form video targets are configured."},"reference":{"status":"not_compared","meaning":"Laboratory reference similarity is not proof of correct technique."}}
