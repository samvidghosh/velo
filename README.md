# Velo

Velo is an Expo / React Native iOS-first app prototype for running-form analysis. This repository contains the mobile UI, a running-only pose analysis package, and an unintegrated Swift Vision reference implementation.

## Current state

- Expo SDK 57, Expo Router, React Native 0.86.3.
- Onboarding, login/signup prototype screens, and local video selection/playback review.
- Login and signup are not connected to an authentication provider.
- A local Expo native module in `modules/velo-vision/` runs Apple Vision pose detection on selected videos in the iOS app build. It samples at 8 Hz with a 720-pixel maximum edge and keeps video processing on device.
- The results screen shows projected 2D knee-angle estimates and visible-landmark coverage. It does not claim validated form scoring, 3D angles, or foot contact.
- `engine/running/` validates normalized pose sequences and calculates projected 2D measurements and cautious gait-cycle candidates. It does not classify running form as correct or incorrect.
- Local datasets, downloaded model files, and generated analysis output are intentionally excluded from Git. See `docs/running-video-dataset.md` to reproduce the desktop video experiment with a separately downloaded dataset.

## Run the app on macOS

Install Node.js and full Xcode, clone this repository, then run:

```sh
cd /path/to/velo
npm ci
npx expo start
```

Expo Go can preview the interface, but it cannot load the Apple Vision module. To build and run the generated iOS app locally, use a Mac with full Xcode:

```sh
npx expo run:ios
```

The iOS project is generated through Expo Continuous Native Generation. Do not hand-edit generated `ios/` files. Test video orientation, visibility, and performance on an iPhone before relying on measurements.

To create an iPhone test build without local Xcode, sign in to an Expo account and use the EAS `preview` profile in `eas.json`:

```sh
npx eas-cli login
npx eas-cli build:configure
npx eas-cli device:create
npx eas-cli build --platform ios --profile preview
```

An internal iOS build requires Apple signing credentials and the target iPhone registered for ad hoc distribution. EAS CLI prompts to configure credentials when needed.

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
