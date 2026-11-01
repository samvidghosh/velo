# Running analysis pipeline and validation boundary

## Pose input

`engine.running.validate_pose_sequence` validates schema `1.0`, nonempty frames, strictly increasing finite timestamps, and landmark dictionaries. A landmark uses normalized image-plane coordinates (`x` right, `y` down, origin top-left) and an optional confidence from 0 to 1. Confidence below 0.35 is unavailable by default.

`analyze_pose_sequence` computes projected knee angles, projected hip flexion, optional ankle angles, trunk inclination from shoulder/hip midpoints, and a pelvic-level proxy. Three-point angles are unsigned angles at the middle point. Knee angle is the included hip-knee-ankle angle (near 180° for an extended leg). Hip flexion is `180° - angle(shoulder, hip, knee)`, so a straight trunk-to-thigh line is 0°. Trunk inclination is signed from vertical in the image plane. Missing or low-confidence inputs yield unavailable measurements. Vision's standard body-pose joints do not include heel or toe points, so ankle-foot angles remain unavailable unless another estimator supplies those landmarks. Outputs include per-frame angle estimates, valid fractions, confidence summaries, candidate cycle peaks, and limitations.

The smoothing step interpolates missing samples, applies a short median pass to reject isolated landmark jumps, then a Savitzky–Golay low-pass. Cycle peaks are periodic signal candidates; candidate peaks are not ground-truth heel strikes. The output exposes peak-to-peak projected-knee cycle windows, but does not assign stance or swing phases. Cadence uses two steps per same-side cycle only as an estimate.

## Dataset adapter

`read_opensim_table` parses `.mot` and `.sto` headers, `endheader`, declared rows, column names, numeric values, time, and units. It retains participant and condition identifiers parsed from the OSF file naming convention. `read_excel_events` parses the actual `Events` sheet in `.xlsx` rawData files without an extra package; `summarize_lab_events` calculates stride intervals, stance duration, and cadence from those explicit lab events. `load_excel_trial` for full numeric workbook tables is optional and requires pandas/openpyxl. C3D support is not installed.

The generated inventory includes every relative path and identifies likely file type from actual extension, header variables, and filename. Text table dimensions come from declared OpenSim dimensions; missing-value counts are explicitly unknown where a full scan was not performed. XLSX records include workbook readability and sheet names, not parsed cell schemas.

## Dataset analysis and ML

The exploration report parses the 226 `*_IK.mot` files into per-trial bilateral angle summaries and preserves participant/trial grouping. This is descriptive analysis of laboratory trials. There are no expert technique labels, no paired phone videos, and no model evaluation. Experimental conditions must not be translated into good/bad labels.

Reference-based comparisons for camera-derived measurements are not yet enabled: laboratory kinematics and 2D pose landmarks have different coordinate systems, angle conventions, noise, and observability. A future baseline needs expert-labelled video assessments or a documented, validated mapping and participant-grouped evaluation. Reference similarity alone would not establish good technique.

## Result limitations

- 2D image-plane geometry is camera-view dependent and is not an absolute 3D biomechanical measurement.
- Occlusion, motion blur, low light, left/right swaps, camera perspective, and body parts leaving frame can make measurements unavailable or misleading.
- A single camera view usually cannot establish physical foot-ground contact. The app must present cycle events as candidates unless valid ground-truth evidence is available.
- No injury diagnosis or injury-risk claim is supported.

## Windows tests

```powershell
python -m pip install -e ".[dev]"
python -m pytest engine\running\tests -v
```

Current running-engine tests cover known geometry and degenerate coordinates, missing landmarks, smoothing with missing data/outliers, synthetic periodic-cycle cadence, timestamp/schema validation, insufficient evidence, and a representative OpenSim fixture.

The running-engine suite passes (11 tests). The repository-wide legacy suite currently has 14 failures in the untouched squat-oriented `engine/tests` code (angle expectation, phase transitions, squat cycle counts/config fixtures); 164 other tests pass. These failures are outside the new running package, but the old modules remain in the checkout and still need separate repair or retirement.

## macOS validation checklist

1. Implement the native AVFoundation decoder and Vision pose request for the configured iOS deployment target.
2. Sample at a bounded frame rate and image size; preserve presentation timestamps.
3. Export normalized landmarks and Vision confidence in pose schema 1.0.
4. Verify front/side view behavior, orientation, partial occlusion, low light, motion blur, and out-of-frame landmarks on recorded clips.
5. Connect native extraction to result serialization and show unavailable measurements and limitations.
6. Build the generated Expo iOS project on macOS, then validate on simulator and a physical iPhone. Source files created on Windows would not prove native compilation.

## Remaining blockers

- Authentication service, OAuth configuration, password recovery, and final privacy/terms URLs.
- Native Vision/AVFoundation extraction and a native-to-Python or equivalent on-device calculation boundary.
- Cell-level Excel parsing and C3D parsing are not included in the current installed environment.
- Expert-labelled running-form video dataset and modality-matched validation data.
- Results view integration and iOS native/device verification.
