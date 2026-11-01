"""Build a reproducible, non-destructive inventory of daataset files."""
from __future__ import annotations
from pathlib import Path
import json, re, zipfile, xml.etree.ElementTree as ET

def _opensim_info(path: Path):
    with path.open("r", encoding="utf-8-sig", errors="replace") as f:
        metadata=[]
        for line in f:
            metadata.append(line.rstrip("\r\n"))
            if line.strip().lower()=="endheader": break
        header=f.readline().strip()
    fields=[x for x in (header.split("\t") if "\t" in header else re.split(r"\s+",header)) if x]
    meta="\n".join(metadata)
    nr=re.search(r"nRows\s*=\s*(\d+)",meta,re.I); nc=re.search(r"nColumns\s*=\s*(\d+)",meta,re.I)
    return {"readable":bool(fields and fields[0].lower()=="time"),"columns":fields,"n_rows_declared":int(nr.group(1)) if nr else None,"n_columns_declared":int(nc.group(1)) if nc else len(fields),"missing_value_counts":None,"missing_scan":"not_scanned (large time-series; run full scan explicitly)","units":"degrees" if re.search(r"inDegrees\s*=\s*yes",meta,re.I) else None}

def _xlsx_info(path: Path):
    try:
        with zipfile.ZipFile(path) as z:
            wb=ET.fromstring(z.read("xl/workbook.xml")); ns={"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main","r":"http://schemas.openxmlformats.org/officeDocument/2006/relationships","p":"http://schemas.openxmlformats.org/package/2006/relationships"}
            rels=ET.fromstring(z.read("xl/_rels/workbook.xml.rels")); relmap={r.attrib["Id"]:r.attrib["Target"] for r in rels}
            sheets=[]
            for s in wb.findall("m:sheets/m:sheet",ns):
                target=relmap.get(s.attrib.get("{%s}id"%ns["r"]),"")
                target=target.lstrip("/") if target.startswith("/") else "xl/"+target
                sheets.append({"name":s.attrib.get("name"),"path":target})
            strings=[]
            if "xl/sharedStrings.xml" in z.namelist():
                for _, item in ET.iterparse(z.open("xl/sharedStrings.xml"),events=("end",)):
                    if item.tag.endswith("}si"): strings.append("".join(t.text or "" for t in item.iter() if t.tag.endswith("}t"))); item.clear()
            sheet_infos=[]; events_summary=None
            first_columns=[]; total_rows=total_cols=0
            for sheet in sheets:
                if sheet["path"] not in z.namelist(): continue
                dim=None; columns=[]
                with z.open(sheet["path"]) as stream:
                    for event, el in ET.iterparse(stream,events=("start","end")):
                        if event=="start" and el.tag.endswith("}dimension"):
                            dim=el.attrib.get("ref")
                        if event=="end" and el.tag.endswith("}row"):
                            row_values=[]
                            for cell in el:
                                if not cell.tag.endswith("}c"): continue
                                value=cell.find("m:v",ns)
                                if value is None: row_values.append(None); continue
                                raw=value.text or ""
                                if cell.attrib.get("t")=="s":
                                    try: raw=strings[int(raw)]
                                    except (ValueError,IndexError): pass
                                row_values.append(raw)
                            if not columns: columns=[value for value in row_values if value is not None]
                            if sheet["name"].lower()=="events" and row_values and row_values[0]:
                                label=str(row_values[0]).strip().upper()
                                if re.fullmatch(r"(?:IC|TO)\s+[LR]",label):
                                    events_summary=events_summary or {"sheet":"Events","event_rows":[]}
                                    events_summary["event_rows"].append({"label":label,"candidate_event_count":sum(1 for value in row_values[1:] if value is not None)})
                            el.clear()
                            if dim and columns and sheet["name"].lower()!="events": break
                rows=cols=0
                if dim and dim!="A1":
                    match=re.search(r"([A-Z]+)(\d+)$",dim)
                    if match:
                        cols=0
                        for c in match.group(1): cols=cols*26+ord(c)-64
                        rows=int(match.group(2))
                        total_rows+=rows; total_cols=max(total_cols,cols)
                else: rows=cols=0
                if not first_columns and columns: first_columns=columns
                sheet_infos.append({"name":sheet["name"],"dimension":dim,"n_rows_estimate":rows,"n_columns_estimate":cols,"columns":columns})
        all_columns=" ".join(" ".join(str(c) for c in sheet.get("columns",[])) for sheet in sheet_infos).lower()
        return {"readable":True,"sheets":sheet_infos,"columns":first_columns,"n_rows_estimate":total_rows or None,"n_columns_estimate":total_cols or None,"missing_value_counts":None,"missing_scan":"not_scanned","laboratory_gait_events":events_summary,"contains_ground_reaction_force_columns":("ground_force" in all_columns or "ground force" in all_columns)}
    except Exception as exc: return {"readable":False,"error":str(exc)}

def inventory(root: str | Path):
    root=Path(root); records=[]
    for p in sorted(x for x in root.rglob("*") if x.is_file()):
        rel=p.relative_to(root).as_posix(); ext=p.suffix.lower()
        record={"relative_path":rel,"extension":ext,"size_bytes":p.stat().st_size,"participant_id":None,"trial_id":p.stem,"condition":None,"speed_m_s":None,"cadence":None,"slope":None,"posture":None,"data_kind":"unknown"}
        m=re.search(r"Sub_(\d+)_((?:\d+ms)|(?:\d+deg_(?:up|down))|highfreq|lowfreq|trunklean)",p.stem,re.I)
        if m:
            record["participant_id"]=f"Sub_{m.group(1)}"; record["condition"]=m.group(2)
            speed=re.fullmatch(r"([3-6])ms",m.group(2)); interval=re.fullmatch(r"(\d{3})ms",m.group(2)); slope=re.fullmatch(r"(\d+)deg_(up|down)",m.group(2))
            if speed: record["speed_m_s"]=int(speed.group(1))
            if interval: record["condition_interval_ms"]=int(interval.group(1))
            if slope: record["slope"]=record["slope_degrees"]=(1 if slope.group(2)=="up" else -1)*int(slope.group(1))
        if ext in (".mot",".sto"):
            try:
                info=_opensim_info(p); record.update(info)
                low=" ".join(record.get("columns",[])).lower()+" "+p.name.lower()
                if ext==".mot" and "knee_angle" in low: record["data_kind"]="processed_joint_angles"
                elif "ground_force" in low or "grf" in low: record["data_kind"]="ground_reaction_force_or_external_load"
                elif "moment" in low or "force" in low: record["data_kind"]="inverse_dynamics_or_force_time_series"
                else: record["data_kind"]="processed_time_series"
            except Exception as exc: record.update({"readable":False,"error":str(exc)})
        elif ext==".xlsx":
            record.update(_xlsx_info(p))
            folder=p.parent.name.lower(); low=" ".join(record.get("columns",[])).lower()
            if "tissue loading" in folder: record["data_kind"]="tissue_loading_processed"
            elif "time-normalized" in folder: record["data_kind"]="time_normalized_gait_cycle"
            else: record["data_kind"]="non_normalized_workbook"
        elif ext==".c3d": record.update({"readable":False,"data_kind":"raw_motion_capture_binary","note":"C3D parser is not installed; file preserved."})
        records.append(record)
    return {"schema_version":"1.0","source_root":str(root.resolve()),"file_count":len(records),"files":records}

def main():
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument("root",nargs="?",default="daataset"); parser.add_argument("--output",default="data/processed/dataset_inventory.json"); args=parser.parse_args()
    result=inventory(args.root); dest=Path(args.output); dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(f"Wrote {result['file_count']} file records to {dest}")
if __name__=="__main__": main()
