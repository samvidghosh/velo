import numpy as np
import pytest
from engine.running.geometry import angle_at, projected_angles
from engine.running.signals import smooth, detect_cycle_candidates
from engine.running.schema import validate_pose_sequence
from engine.running.analysis import analyze_pose_sequence
from engine.running.dataset import read_opensim_table
from engine.running.dataset import read_excel_events
from engine.running.inventory import _xlsx_info
from engine.running.gait import summarize_lab_events
from engine.running.modeling import grouped_train_test, save_model, load_model, predict_features

def test_angles_known_and_degenerate():
    assert angle_at([1,0],[0,0],[0,1]) == pytest.approx(90)
    assert angle_at([0,0],[0,0],[1,0]) is None
    assert angle_at([float('nan'),0],[0,0],[1,0]) is None

def test_projected_knee_missing_landmark():
    result=projected_angles({"left_hip":{"coordinates":[0,0],"confidence":1},"left_knee":{"coordinates":[0,1],"confidence":1}})
    assert result["left_knee_flexion_projected_deg"] is None

def test_projected_bilateral_symmetry():
    from engine.running.geometry import projected_angles
    pose={
      "left_hip":{"coordinates":[.3,.2]}, "left_knee":{"coordinates":[.3,.5]}, "left_ankle":{"coordinates":[.4,.8]},
      "right_hip":{"coordinates":[.7,.2]}, "right_knee":{"coordinates":[.7,.5]}, "right_ankle":{"coordinates":[.7,.8]},
    }
    angles=projected_angles(pose)
    assert angles["left_knee_flexion_projected_deg"] != angles["right_knee_flexion_projected_deg"]

def test_smoothing_reduces_spike_and_handles_nan():
    x=np.sin(np.linspace(0,8,101)); x[50]=8; x[12]=np.nan
    y=smooth(x,7)
    assert len(y)==len(x) and np.isfinite(y).all() and abs(y[50])<2

def test_synthetic_periodic_candidates_and_cadence():
    t=np.arange(0,8,.01); x=np.cos(2*np.pi*t/0.8)
    result=detect_cycle_candidates(t,x)
    assert len(result["events"]) >= 8
    assert result["cadence_spm"] == pytest.approx(150,abs=5)

def test_pose_schema_and_insufficient_evidence():
    payload={"schema_version":"1.0","frames":[{"timestamp":0,"landmarks":{}},{"timestamp":.1,"landmarks":{}}]}
    assert len(validate_pose_sequence(payload))==2
    assert analyze_pose_sequence(payload)["status"]=="insufficient_evidence"
    with pytest.raises(ValueError): validate_pose_sequence({"schema_version":"1.0","frames":[{"timestamp":1,"landmarks":{}},{"timestamp":1,"landmarks":{}}]})

def test_opensim_fixture(tmp_path):
    p=tmp_path/"Sub_01_3ms_IK.mot"
    p.write_text("Coordinates\nversion=1\nnRows=2\nnColumns=3\ninDegrees=yes\nendheader\ntime\tknee_angle_r\tknee_angle_l\n0\t10\t11\n0.1\t12\t13\n")
    trial=read_opensim_table(p)
    assert trial.participant_id=="Sub_01" and trial.condition=="3ms"
    assert trial.columns["knee_angle_r"].tolist()==[10,12]

def test_opensim_declared_schema_mismatch(tmp_path):
    p=tmp_path/"bad.mot"
    p.write_text("Coordinates\nnRows=1\nnColumns=4\nendheader\ntime\tknee_angle_r\n0\t10\n")
    with pytest.raises(ValueError,match="nColumns"): read_opensim_table(p)

def test_excel_event_sheet_fixture_and_inventory(tmp_path):
    import zipfile
    from pathlib import PurePosixPath
    p=tmp_path/"Sub_02_3ms_rawData.xlsx"
    files={
      "xl/workbook.xml":'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Events" sheetId="1" r:id="rId1"/><sheet name="GRF" sheetId="2" r:id="rId2"/></sheets></workbook>',
      "xl/_rels/workbook.xml.rels":'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Target="worksheets/sheet2.xml"/></Relationships>',
      "xl/sharedStrings.xml":'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>IC R</t></si><si><t>TO L</t></si><si><t>time</t></si><si><t>L_ground_force_vy</t></si></sst>',
      "xl/worksheets/sheet1.xml":'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="A1:C2"/><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1"><v>1.25</v></c><c r="C1"><v>2.1</v></c></row><row r="2"><c r="A2" t="s"><v>1</v></c><c r="B2"><v>1.5</v></c></row></sheetData></worksheet>',
      "xl/worksheets/sheet2.xml":'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="A1:B1"/><sheetData><row r="1"><c r="A1" t="s"><v>2</v></c><c r="B1" t="s"><v>3</v></c></row></sheetData></worksheet>'}
    with zipfile.ZipFile(p,"w") as z:
        for name,content in files.items(): z.writestr(PurePosixPath(name).as_posix(),content)
    result=read_excel_events(p)
    assert [(e["event"],e["side"],e["timestamp_s"]) for e in result["events"]]==[("initial_contact","right",1.25),("toe_off","left",1.5),("initial_contact","right",2.1)]
    info=_xlsx_info(p)
    assert info["laboratory_gait_events"]["event_rows"][0]["candidate_event_count"]==2
    assert info["contains_ground_reaction_force_columns"]

def test_ground_truth_event_cadence_stance_and_symmetry():
    events=[]
    for side,offset in (("left",0),("right",.5)):
        for start in (0,1,2): events.append({"event":"initial_contact","side":side,"timestamp_s":start+offset})
        for start in (0,1): events.append({"event":"toe_off","side":side,"timestamp_s":start+offset+.6})
    result=summarize_lab_events(events)
    assert result["cadence_spm"]==pytest.approx(120)
    assert result["left_right_stride_interval_difference_s"]==pytest.approx(0)
    assert result["stance_duration_median_s"]["right"]==pytest.approx(.6)

def test_grouped_model_has_no_participant_leakage_and_serializes(tmp_path):
    features=[]; labels=[]; groups=[]
    for participant in range(12):
        for rep in range(4):
            label=rep % 2
            features.append([float(label), float(participant % 3)])
            labels.append(label); groups.append(f"runner-{participant}")
    model, report=grouped_train_test(features,labels,groups)
    assert not (set(report["train_participants"]) & set(report["test_participants"]))
    assert report["train_trials"] + report["test_trials"] == len(labels)
    target=tmp_path/"baseline.joblib"
    save_model(model,report,["feature_a","feature_b"],target)
    loaded=load_model(target,["feature_a","feature_b"])
    prediction=predict_features(loaded,{"feature_a":0,"feature_b":1},["feature_a","feature_b"])
    assert prediction["prediction"] == 0
    assert prediction["confidence_status"] == "uncalibrated_model_probability"
    with pytest.raises(ValueError): load_model(target,["feature_b","feature_a"])
    with pytest.raises(ValueError,match="missing model features"): predict_features(loaded,{"feature_a":0},["feature_a","feature_b"])

