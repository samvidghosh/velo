# Running posture video dataset experiment

The local Running Posture Analysis Dataset is a separate download containing 93 MOV clips. The experiment uses MediaPipe Pose Landmarker Lite to extract 2D landmarks and passes them to Velo's running-only analysis engine. It does not train a form-quality classifier because the videos have no expert posture labels.

## Run on macOS

Use Python 3.11 or newer. Install the optional video tools:

```sh
python3 -m pip install -e ".[video-analysis]"
```

Download the [MediaPipe Pose Landmarker Lite task model](https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task) to `data/models/pose_landmarker_lite.task`:

```sh
mkdir -p data/models
curl -L "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task" \
  -o data/models/pose_landmarker_lite.task
```

Set `VIDEO_DIR` to the folder containing the MOV files, then process one clip followed by the full dataset:

```sh
VIDEO_DIR="/path/to/Running Posture Analysis Dataset"

python3 -m engine.running.video_dataset "$VIDEO_DIR" \
  --limit 1 \
  --output-dir data/processed/running_posture_dataset_smoke

python3 -m engine.running.video_dataset "$VIDEO_DIR" \
  --sample-rate 10 \
  --max-long-edge 960 \
  --output-dir data/processed/running_posture_dataset_10hz
```

Each clip produces a `.pose.json` sequence and `.analysis.json` result. The output folder also contains aggregate JSON and CSV summaries. These outputs and the model are ignored by Git.

## Interpretation

- Filename speeds are recorded as weak metadata only. They are not measured from video and do not label running form.
- The eight principal joints plus heels and toes use normalized image-plane coordinates. Angles remain 2D projections affected by camera placement and occlusion.
- Cadence is a candidate estimated from periodic projected knee motion. It is not ground-truth foot contact or a validated measurement.
- A 5 Hz experiment yielded a median cadence candidate of 85.7 steps/min, while the 10 Hz experiment yielded 171.4. This sampling sensitivity indicates aliasing in the current detector. Do not present cadence candidates as user-facing measurements until calibrated against known contacts.
- `analysis_ready` means enough landmarks were visible for the current calculation, not that the runner's form is correct or safe.
- The results are exploratory. Review them against annotated video and independent measurements before using them for coaching feedback.

The videos are from the [Running Posture Analysis Dataset](https://data.mendeley.com/datasets/9cr3fjhrzy/1), listed as CC BY 4.0. The MediaPipe model has its own licensing terms; check those before redistributing model files or derived artifacts.
