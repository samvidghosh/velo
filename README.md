# Velo

Velo is an Expo / React Native iOS-first app prototype for running-form analysis. This repository contains the mobile UI, a running-only pose analysis package, and an unintegrated Swift Vision reference implementation.

## Current state

- Expo SDK 57, Expo Router, React Native 0.86.3.
- Onboarding, login/signup prototype screens, and local video selection/playback review.
- Login and signup are not connected to an authentication provider.
- The iOS Vision source in `native/ios/VeloVisionPoseExtractor.swift` is a reference only. It is not an Expo native module and the app's **Start analysis** action does not run pose detection yet.
- `engine/running/` validates normalized pose sequences and calculates projected 2D measurements and cautious gait-cycle candidates. It does not classify running form as correct or incorrect.
- Local datasets, downloaded model files, and generated analysis output are intentionally excluded from Git. See `docs/running-video-dataset.md` to reproduce the desktop video experiment with a separately downloaded dataset.

## Run the app on macOS

Install Node.js and Xcode command-line tools, clone this repository, then run:

```sh
cd /path/to/velo
npm ci
npx expo start
```

This starts the JavaScript app for Expo Go. To build and run the generated iOS project locally, use a Mac with Xcode:

```sh
npx expo run:ios
```

The iOS project is generated through Expo Continuous Native Generation. Do not hand-edit generated `ios/` files. Once the Vision extractor is integrated as an Expo module/config plugin, create a development build and test on an iPhone; Expo Go does not contain custom native Vision code.

## Running analysis package

The Python package can be installed separately from the mobile app. Use Python 3.11 or newer:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

For video pose extraction on a separately downloaded running video dataset, install the optional dependencies and follow [the video dataset instructions](docs/running-video-dataset.md).

## Important limitations

Monocular video yields camera-plane estimates, not absolute 3D joint angles or confirmed foot-ground contact. The local video set has no expert form labels, so it cannot train a supervised “good/bad form” model. Cadence candidates are sensitive to temporal sampling and are not ready to present as validated measurements.
