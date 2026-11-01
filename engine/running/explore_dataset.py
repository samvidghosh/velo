"""Extract per-trial descriptive features from available inverse-kinematics MOT files."""
from pathlib import Path
import json
from .dataset import read_opensim_table, trial_angle_features, read_excel_events
from .gait import summarize_lab_events

def explore(root="daataset", output="data/processed/dataset_exploration.json"):
    paths=sorted(Path(root).rglob("*_IK.mot")); trials=[]; errors=[]
    for path in paths:
        try: trials.append(trial_angle_features(read_opensim_table(path)))
        except Exception as exc: errors.append({"path":str(path),"error":str(exc)})
    event_trials=[]; event_errors=[]
    for path in sorted(Path(root).rglob("*_rawData.xlsx")):
        try:
            trial=read_excel_events(path)
            trial["gait_features"]=summarize_lab_events(trial["events"])
            event_trials.append(trial)
        except Exception as exc: event_errors.append({"path":str(path),"error":str(exc)})
    event_counts={}
    for trial in event_trials:
        for event in trial["events"]:
            key=f"{event['event']}_{event['side']}"; event_counts[key]=event_counts.get(key,0)+1
    report={"schema_version":"1.0","source":"OpenSim inverse-kinematics processed angles plus laboratory Events sheets","trial_count":len(trials),"participant_count":len({t["participant_id"] for t in trials if t["participant_id"]}),"participants":sorted({t["participant_id"] for t in trials if t["participant_id"]}),"conditions":sorted({t["condition"] for t in trials if t["condition"]}),"trials":trials,"errors":errors,"laboratory_event_trial_count":sum(bool(t["events"]) for t in event_trials),"laboratory_event_trial_count_total":len(event_trials),"laboratory_event_counts":event_counts,"laboratory_event_trials":event_trials,"event_errors":event_errors,"labels":{"good_bad_form":False,"expert_assessments":False},"interpretation":"Descriptive laboratory measurements and annotated IC/TO timings only; conditions are perturbations, not technique-quality labels. No supervised running-form classifier can be trained from these files."}
    dest=Path(output); dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(json.dumps(report,indent=2),encoding="utf-8"); return report
if __name__=="__main__":
    result=explore(); print(f"{result['trial_count']} trials; {result['participant_count']} participants; {len(result['errors'])} errors")
