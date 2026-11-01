"""Adapters for OpenSim .mot/.sto tables and optional Excel workbooks."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv, re
import numpy as np

@dataclass
class Trial:
    participant_id: str | None
    trial_id: str
    condition: str | None
    time_s: np.ndarray
    columns: dict[str, np.ndarray]
    units: str | None
    source: str

def read_opensim_table(path: str | Path) -> Trial:
    path = Path(path)
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    end = next((i for i, line in enumerate(lines) if line.strip().lower() == "endheader"), None)
    metadata = "\n".join(lines[:end]) if end is not None else ""
    header_index = end + 1 if end is not None else next((i for i,l in enumerate(lines) if l.strip().lower().startswith("time\t") or l.strip().lower() == "time"), None)
    if header_index is None or header_index >= len(lines): raise ValueError(f"{path}: missing endheader/column header")
    header_line = lines[header_index].strip()
    delim = "\t" if "\t" in header_line else None
    names = [x for x in (header_line.split("\t") if delim else re.split(r"\s+", header_line)) if x]
    if not names or names[0].lower() != "time": raise ValueError(f"{path}: first column must be time")
    rows=[]
    for line_no, line in enumerate(lines[header_index+1:], header_index+2):
        if not line.strip(): continue
        vals = line.split("\t") if delim else re.split(r"\s+", line.strip())
        if len(vals) != len(names): raise ValueError(f"{path}:{line_no}: expected {len(names)} values, got {len(vals)}")
        try: rows.append([float(v) if v.lower() not in ("nan", "na", "-nan") else np.nan for v in vals])
        except ValueError as exc: raise ValueError(f"{path}:{line_no}: non-numeric table value") from exc
    data=np.asarray(rows,float)
    if data.ndim != 2 or data.shape[1] != len(names): raise ValueError(f"{path}: no table rows")
    declared = re.search(r"nRows\s*=\s*(\d+)", metadata, re.I)
    if declared and int(declared.group(1)) != len(data): raise ValueError(f"{path}: declared nRows does not match parsed rows")
    declared_columns = re.search(r"nColumns\s*=\s*(\d+)", metadata, re.I)
    if declared_columns and int(declared_columns.group(1)) != len(names): raise ValueError(f"{path}: declared nColumns does not match parsed columns")
    m = re.search(r"Sub_(\d+)_((?:\d+ms)|(?:\d+deg_(?:up|down))|highfreq|lowfreq|trunklean)", path.stem, re.I)
    return Trial(f"Sub_{m.group(1)}" if m else None, path.stem, m.group(2) if m else None, data[:,0], {k:data[:,i] for i,k in enumerate(names[1:],1)}, "degrees" if re.search(r"inDegrees\s*=\s*yes", metadata, re.I) else None, str(path))

def trial_angle_features(trial: Trial) -> dict:
    features={"participant_id":trial.participant_id,"trial_id":trial.trial_id,"condition":trial.condition,"source":trial.source,"sample_count":len(trial.time_s),"duration_s":float(trial.time_s[-1]-trial.time_s[0])}
    for key in ("knee_angle_r","knee_angle_l","hip_flexion_r","hip_flexion_l","ankle_angle_r","ankle_angle_l","lumbar_extension"):
        v=trial.columns.get(key)
        if v is not None:
            features[f"{key}_mean"] = float(np.nanmean(v)) if np.isfinite(v).any() else None
            features[f"{key}_std"] = float(np.nanstd(v)) if np.isfinite(v).any() else None
    if features.get("knee_angle_r_mean") is not None and features.get("knee_angle_l_mean") is not None:
        features["knee_mean_difference_deg"] = abs(features["knee_angle_r_mean"]-features["knee_angle_l_mean"])
    return features

def load_excel_trial(path: str | Path):
    """Optional Excel adapter, enabled when pandas + openpyxl are installed."""
    try: import pandas as pd
    except ImportError as exc: raise RuntimeError("Excel loading requires pandas and openpyxl") from exc
    sheets = pd.read_excel(path, sheet_name=None)
    return {name: frame for name,frame in sheets.items()}

def read_excel_events(path: str | Path) -> dict:
    """Read an Open XML workbook's laboratory Events sheet without pandas.

    Returns participant/trial provenance and IC/TO event timestamps in seconds.
    These are laboratory annotations, unlike video-derived event candidates.
    """
    import zipfile
    import xml.etree.ElementTree as ET
    path=Path(path)
    ns={"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main","r":"http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    with zipfile.ZipFile(path) as z:
        workbook=ET.fromstring(z.read("xl/workbook.xml"))
        relationships=ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        relmap={item.attrib["Id"]:item.attrib["Target"] for item in relationships}
        sheet=next((s for s in workbook.findall("m:sheets/m:sheet",ns) if s.attrib.get("name","").lower()=="events"),None)
        if sheet is None: raise ValueError(f"{path}: workbook has no Events sheet")
        target=relmap[sheet.attrib["{%s}id"%ns["r"]]]
        target=target.lstrip("/") if target.startswith("/") else "xl/"+target
        shared=[]
        if "xl/sharedStrings.xml" in z.namelist():
            for _, item in ET.iterparse(z.open("xl/sharedStrings.xml"),events=("end",)):
                if item.tag.endswith("}si"):
                    shared.append("".join(t.text or "" for t in item.iter() if t.tag.endswith("}t")))
                    item.clear()
        root=ET.fromstring(z.read(target))
    events=[]
    for row in root.findall(".//m:sheetData/m:row",ns):
        values=[]
        for cell in row.findall("m:c",ns):
            value=cell.find("m:v",ns)
            raw=value.text if value is not None else None
            if raw is not None and cell.attrib.get("t")=="s":
                try: raw=shared[int(raw)]
                except (ValueError,IndexError): pass
            values.append(raw)
        if not values or values[0] is None: continue
        label=str(values[0]).strip().upper()
        match=re.fullmatch(r"(IC|TO)\s+([LR])",label)
        if not match: continue
        for value in values[1:]:
            try: timestamp=float(value)
            except (TypeError,ValueError): continue
            if np.isfinite(timestamp):
                events.append({"timestamp_s":timestamp,"event":"initial_contact" if match.group(1)=="IC" else "toe_off","side":"left" if match.group(2)=="L" else "right","provenance":"laboratory_events_sheet","confidence":"ground_truth_source"})
    events.sort(key=lambda e:e["timestamp_s"])
    participant=re.search(r"Sub_(\d+)_",path.stem)
    condition=re.search(r"Sub_\d+_((?:\d+ms)|(?:\d+deg_(?:up|down))|highfreq|lowfreq|trunklean)",path.stem,re.I)
    return {"participant_id":f"Sub_{participant.group(1)}" if participant else None,"trial_id":path.stem,"condition":condition.group(1) if condition else None,"source":str(path),"events":events}
