"""Feature extraction from supplied, timestamped gait events."""
from __future__ import annotations
import numpy as np

def summarize_lab_events(events: list[dict]) -> dict:
    """Summarize explicit initial-contact/toe-off event rows (times in seconds).

    Suitable only for annotated lab or validated ground-truth event sources.
    Video-derived candidates must not be relabelled as ground truth here.
    """
    contacts={side:sorted(float(e["timestamp_s"]) for e in events if e.get("event")=="initial_contact" and e.get("side")==side and np.isfinite(float(e.get("timestamp_s",np.nan)))) for side in ("left","right")}
    toeoffs={side:sorted(float(e["timestamp_s"]) for e in events if e.get("event")=="toe_off" and e.get("side")==side and np.isfinite(float(e.get("timestamp_s",np.nan)))) for side in ("left","right")}
    stride={side:np.diff(contacts[side]) for side in contacts}
    intervals=np.diff(sorted(contacts["left"]+contacts["right"]))
    stance={}
    for side in contacts:
        durations=[]
        for start,end in zip(contacts[side],contacts[side][1:]):
            following=[t for t in toeoffs[side] if start<t<end]
            if following: durations.append(following[0]-start)
        stance[side]=durations
    med=lambda seq: float(np.median(seq)) if len(seq) else None
    left,right=med(stride["left"]),med(stride["right"])
    return {"left_initial_contacts_s":contacts["left"],"right_initial_contacts_s":contacts["right"],"stride_interval_median_s":{"left":left,"right":right},"step_interval_median_s":med(intervals),"cadence_spm":float(60/np.median(intervals)) if len(intervals) and np.median(intervals)>0 else None,"left_right_stride_interval_difference_s":abs(left-right) if left is not None and right is not None else None,"stance_duration_median_s":{"left":med(stance["left"]),"right":med(stance["right"])},"event_source":"explicit annotated event input","status":"available" if len(intervals) else "insufficient_events"}
