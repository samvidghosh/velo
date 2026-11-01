"""Experimental labelled-video model helpers with participant-grouped holdout.

These functions require optional scikit-learn and must not be run against
unlabelled lab condition names as if they were technique outcomes.
"""
from __future__ import annotations
import json
from pathlib import Path

MODEL_SCHEMA_VERSION = "1.0"

def grouped_train_test(features, labels, participant_ids, *, test_size=.25, random_state=17):
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.impute import SimpleImputer
        from sklearn.model_selection import GroupShuffleSplit
        from sklearn.pipeline import make_pipeline
        from sklearn.metrics import classification_report
        import numpy as np
    except ImportError as exc: raise RuntimeError("Install the optional ml dependencies to train a model") from exc
    X=np.asarray(features,float); y=np.asarray(labels); groups=np.asarray(participant_ids)
    if X.ndim != 2 or len(X)!=len(y) or len(y)!=len(groups): raise ValueError("feature, label, and participant row counts must match")
    if len(set(groups)) < 4: raise ValueError("at least four distinct participants are required for grouped holdout")
    splitter=GroupShuffleSplit(n_splits=1,test_size=test_size,random_state=random_state)
    train,test=next(splitter.split(X,y,groups))
    if set(groups[train]) & set(groups[test]): raise AssertionError("participant leakage detected")
    if len(set(y[train]))<2 or len(set(y[test]))<2: raise ValueError("grouped holdout must contain at least two classes in each partition")
    model=make_pipeline(SimpleImputer(strategy="median"),RandomForestClassifier(n_estimators=200,class_weight="balanced",random_state=random_state))
    model.fit(X[train],y[train]); pred=model.predict(X[test])
    report=classification_report(y[test],pred,output_dict=True,zero_division=0)
    result={"schema_version":MODEL_SCHEMA_VERSION,"task":"experimental expert-labelled running-form classification","train_participants":sorted(set(groups[train].tolist())),"test_participants":sorted(set(groups[test].tolist())),"train_trials":len(train),"test_trials":len(test),"metrics":report,"feature_count":X.shape[1],"warning":"Metrics apply only to supplied expert-labelled data and this participant-grouped split."}
    return model,result

def save_model(model, result, feature_names, path):
    try: import joblib
    except ImportError as exc: raise RuntimeError("Install scikit-learn to save its model") from exc
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    joblib.dump(model,path)
    path.with_suffix(path.suffix+".json").write_text(json.dumps({"schema_version":MODEL_SCHEMA_VERSION,"feature_names":list(feature_names),"evaluation":result},indent=2),encoding="utf-8")

def load_model(path, feature_names):
    import joblib
    path=Path(path); metadata=json.loads(path.with_suffix(path.suffix+".json").read_text(encoding="utf-8"))
    if metadata.get("schema_version")!=MODEL_SCHEMA_VERSION or metadata.get("feature_names")!=list(feature_names): raise ValueError("model schema or feature order does not match inference input")
    return joblib.load(path)

def predict_features(model, values: dict, feature_names):
    """Run one schema-ordered model inference; class probabilities are uncalibrated."""
    import numpy as np
    names=list(feature_names)
    missing=[name for name in names if name not in values]
    if missing: raise ValueError(f"missing model features: {', '.join(missing)}")
    row=np.asarray([[values[name] for name in names]],dtype=float)
    prediction=model.predict(row)[0]
    probabilities=model.predict_proba(row)[0] if hasattr(model,"predict_proba") else None
    classes=getattr(model,"classes_",[])
    return {"prediction":prediction.item() if hasattr(prediction,"item") else prediction,"probabilities":({str(label):float(prob) for label,prob in zip(classes,probabilities)} if probabilities is not None else None),"confidence_status":"uncalibrated_model_probability" if probabilities is not None else "unavailable"}
