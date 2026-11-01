# Velo · Authentication UI developer handoff

This folder contains the current visual preview and implementation reference for the five account-entry screens.

## Start here

1. Read `Velo_Auth_Developer_Handoff.pdf` for the flow, screen behavior, design tokens, and iOS layout requirements.
2. Open `velo-voltage-preview.html` in a browser to inspect the five screens together. The preview loads `assets/velo-runner-night.jpg` locally, so keep the `assets` folder beside the HTML file.
3. Use the included JPEG as the temporary photographic asset. Its source and license are recorded in the PDF and below.

## Files

- `Velo_Auth_Developer_Handoff.pdf` — shareable build specification.
- `velo-voltage-preview.html` — five-screen visual reference.
- `assets/velo-runner-night.jpg` — selected real running photo.
- `assets/PHOTO_SOURCE.txt` — photographer, source page, and license.

## Design decisions

- Brand: Velo, lowercase wordmark.
- Palette: Voltage — `#10140A`, `#354719`, `#C4F52A`, `#EDFF9A`.
- Typography: native Apple system sans-serif; use Dynamic Type in the shipped app.
- Photo: full-bleed, softly motion-blurred running image with dark scrim and restrained cool graphite/forest tint.
- Actions: lime primary CTA with dark text; translucent outlined secondary; recognizable Apple and Google sign-in buttons.
- iOS dimensions: safe-area-aware; every interactive target at least 44 × 44 pt. Preview reference canvas is 393 × 852 pt.

## V1 product context

V1 is centered on running gait analysis and personalized corrective or strength exercises. Repeat assessments build an ongoing picture of the runner’s movement and history. Live in-ear coaching is planned for a later phase and should not be presented as a V1 feature.

## Integration items to connect

The screens are ready to implement visually. Connect the app’s existing authentication service, Apple and Google OAuth configuration, password policy, password recovery route, and final Privacy Policy / Terms URLs. The sample email and first name are placeholders.

## Photo source

The original running-at-night photo from the Unsplash collection is included locally. Its original preview did not retain contributor metadata. See `assets/PHOTO_SOURCE.txt`.
