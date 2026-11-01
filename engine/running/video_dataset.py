"""Extract pose sequences from the local Running Posture Analysis videos.

This is an exploratory video-to-running-measurements workflow. It does not
create running-form quality labels or train a correct/incorrect classifier.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import time
from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from .analysis import analyze_pose_sequence


LANDMARKS = {
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
    "left_heel": 29,
    "right_heel": 30,
    "left_toe": 31,
    "right_toe": 32,
}
VIDEO_EXTENSIONS = {".mov", ".mp4", ".m4v", ".avi"}


def _filename_metadata(path: Path) -> dict[str, Any]:
    name = path.stem
    speed_match = re.search(r"(?<!\d)(\d{1,2})\s*km[_ -]?\s*h(?![A-Za-z0-9])", name, re.I)
    participant_match = re.search(r"\bRunner\s*(\d+)\b", name, re.I)
    named_group = re.match(r"^([A-Za-z]+)(?:[-_ ]|$)", name)
    participant_group = f"Runner{participant_match.group(1)}" if participant_match else (
        named_group.group(1) if named_group and named_group.group(1).upper() != "IMG" else None
    )
    return {
        "participant_group": participant_group,
        "filename_speed_kmh": int(speed_match.group(1)) if speed_match else None,
    }


def _confidence(landmark: Any) -> float:
    values = [getattr(landmark, key, None) for key in ("visibility", "presence")]
    usable = [float(v) for v in values if v is not None]
    return min(usable) if usable else 0.0


def _extract_video(
    path: Path,
    root: Path,
    output_dir: Path,
    landmarker: Any,
    sample_rate_hz: float,
    max_long_edge: int,
) -> dict[str, Any]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError("OpenCV could not open the video")
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if fps <= 0 or count <= 0:
        cap.release()
        raise ValueError("video has invalid frame-rate or frame-count metadata")

    duration_s = count / fps
    frame_step = max(1, round(fps / sample_rate_hz))
    frames: list[dict[str, Any]] = []
    frame_index = 0
    try:
        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            if frame_index % frame_step == 0:
                timestamp_s = frame_index / fps
                scale = min(1.0, max_long_edge / max(bgr.shape[0], bgr.shape[1]))
                if scale < 1.0:
                    bgr = cv2.resize(bgr, (round(bgr.shape[1] * scale), round(bgr.shape[0] * scale)), interpolation=cv2.INTER_AREA)
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = landmarker.detect_for_video(image, round(timestamp_s * 1000))
                pose = result.pose_landmarks[0] if result.pose_landmarks else None
                joints: dict[str, dict[str, Any]] = {}
                if pose:
                    for name, index in LANDMARKS.items():
                        point = pose[index]
                        confidence = _confidence(point)
                        if confidence > 0:
                            joints[name] = {
                                "coordinates": [float(point.x), float(point.y)],
                                "confidence": confidence,
                            }
                frames.append({"timestamp": timestamp_s, "landmarks": joints})
            frame_index += 1
    finally:
        cap.release()

    if not frames:
        raise ValueError("no frames were sampled")
    metadata = _filename_metadata(path)
    payload = {
        "schema_version": "1.0",
        "video": {
            "filename": path.name,
            "duration_seconds": duration_s,
            "source_fps": fps,
            "width": width,
            "height": height,
            "sample_rate_hz_requested": sample_rate_hz,
            "sample_rate_hz_actual": len(frames) / duration_s,
            "pose_estimator": "MediaPipe Pose Landmarker Lite",
            "filename_metadata": metadata,
        },
        "frames": frames,
    }
    analysis = analyze_pose_sequence(payload)
    relative = path.relative_to(root).with_suffix("")
    destination = output_dir / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    (destination.with_suffix(".pose.json")).write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    (destination.with_suffix(".analysis.json")).write_text(json.dumps(analysis, indent=2), encoding="utf-8")

    left = analysis["measurements"]["left_knee_flexion_projected_deg"]
    right = analysis["measurements"]["right_knee_flexion_projected_deg"]
    return {
        "video": path.name,
        "participant_group": metadata["participant_group"],
        "filename_speed_kmh": metadata["filename_speed_kmh"],
        "duration_s": round(duration_s, 3),
        "source_fps": fps,
        "frame_count": count,
        "sampled_frame_count": len(frames),
        "mean_landmark_fraction": round(analysis["input_quality"]["mean_landmark_fraction"], 4),
        "mean_landmark_confidence": round(analysis["input_quality"]["mean_landmark_confidence"], 4) if analysis["input_quality"]["mean_landmark_confidence"] is not None else None,
        "left_knee_projected_mean_deg": left["mean"],
        "right_knee_projected_mean_deg": right["mean"],
        "cadence_spm_candidate": analysis["gait"]["cadence_spm_estimate"],
        "analysis_status": analysis["status"],
        "pose_file": str((destination.with_suffix(".pose.json")).relative_to(output_dir)),
        "analysis_file": str((destination.with_suffix(".analysis.json")).relative_to(output_dir)),
    }


def process_dataset(
    input_dir: Path,
    output_dir: Path,
    model_path: Path,
    sample_rate_hz: float = 10.0,
    max_long_edge: int = 960,
    limit: int | None = None,
) -> dict[str, Any]:
    if sample_rate_hz <= 0:
        raise ValueError("sample rate must be greater than zero")
    root = input_dir.resolve()
    videos = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS)
    if limit is not None:
        videos = videos[:limit]
    if not videos:
        raise ValueError(f"no supported videos found under {root}")
    if not model_path.is_file():
        raise FileNotFoundError(f"MediaPipe model not found: {model_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    rows: list[dict[str, Any]] = []
    started = time.monotonic()
    for number, video in enumerate(videos, 1):
        try:
            # Timestamps restart at zero for each clip, so use a fresh video-mode
            # task instance per clip rather than carrying tracker state across videos.
            with vision.PoseLandmarker.create_from_options(options) as landmarker:
                row = _extract_video(video, root, output_dir, landmarker, sample_rate_hz, max_long_edge)
            row["status"] = "processed"
        except Exception as exc:  # keep the batch moving and report each failed clip
            row = {"video": video.name, "status": "error", "error": f"{type(exc).__name__}: {exc}"}
        rows.append(row)
        print(f"[{number}/{len(videos)}] {video.name}: {row['status']}" + (f", coverage={row.get('mean_landmark_fraction')}" if row["status"] == "processed" else f", {row['error']}"), flush=True)

    processed = [row for row in rows if row["status"] == "processed"]
    coverages = [row["mean_landmark_fraction"] for row in processed]
    by_status: dict[str, int] = {}
    for row in rows:
        key = row.get("analysis_status", row["status"])
        by_status[key] = by_status.get(key, 0) + 1
    summary = {
        "schema_version": "1.0",
        "input_directory": str(root),
        "video_count": len(videos),
        "processed_count": len(processed),
        "error_count": len(rows) - len(processed),
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "analysis_status_counts": by_status,
        "mean_landmark_fraction_median": statistics.median(coverages) if coverages else None,
        "limitations": [
            "This dataset has no expert running-form labels; no good/bad-form classifier was trained.",
            "Filename speeds are weak metadata, not posture labels or verified treadmill telemetry.",
            "Measurements use 2D monocular pose landmarks and are exploratory, not clinical assessments.",
            "Gait events and cadence are candidates derived from projected knee-angle periodicity, not ground-truth contacts.",
        ],
        "videos": rows,
    }
    (output_dir / "dataset_analysis.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    csv_path = output_dir / "dataset_analysis.csv"
    fields = sorted({key for row in rows for key in row})
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path, help="Folder containing running videos")
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/running_posture_dataset"))
    parser.add_argument("--model", type=Path, default=Path("data/models/pose_landmarker_lite.task"))
    parser.add_argument("--sample-rate", type=float, default=10.0, help="Pose samples per second")
    parser.add_argument("--max-long-edge", type=int, default=960)
    parser.add_argument("--limit", type=int, help="Optional clip limit for a quick trial run")
    args = parser.parse_args()
    result = process_dataset(args.input_dir, args.output_dir, args.model, args.sample_rate, args.max_long_edge, args.limit)
    print(json.dumps({key: value for key, value in result.items() if key != "videos"}, indent=2))


if __name__ == "__main__":
    main()
