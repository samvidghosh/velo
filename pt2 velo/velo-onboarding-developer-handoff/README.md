# Velo onboarding · developer handoff

This package contains the approved visual reference and implementation brief for Velo’s onboarding sequence. Treat the design as locked: preserve its approved colors, type hierarchy, spacing, button placement, photos, and icon styling unless Nishitha explicitly requests a change.

## Start here

1. Read `Velo_Onboarding_Developer_Handoff.pdf` for the screen sequence, exact copy, interaction behavior, shared layout rules, and handoff checklist.
2. Open `velo-onboarding-preview.html` in a browser to view the nine approved screens together and try the selection, quiz, Back, Skip, and Continue states. Keep the `assets` folder beside the HTML file.
3. Use `SCREEN_SPEC.md` as the detailed, editable source of truth. `velo-onboarding-approved-2026-10-15.html` is the frozen visual baseline.

## Included files

- `Velo_Onboarding_Developer_Handoff.pdf` — shareable implementation brief.
- `velo-onboarding-preview.html` — approved interactive visual preview.
- `velo-onboarding-approved-2026-10-15.html` — frozen approved snapshot.
- `SCREEN_SPEC.md` — screen-by-screen content and design specification.
- `assets/` — the three local photos used by the preview.

## Screen order

1. Welcome / Let’s start
2. How will you use Velo? (Runner, Coach, Medical professional)
3. Choose your path (fitness/performance, learn form, reduce injury risk)
4. Lab-quality analysis
5. Game time / laboratory analysis cost quiz
6. Anytime, anywhere
7. Personalized analysis introduction
8. Runner identity
9. Running level (pace values in min/km)

The community-count screen is omitted. Pair account creation and login with the separate Velo authentication handoff.

## Product scope

V1 includes running-form video analysis and tailored corrective or strength exercises. Repeated assessments build a more useful picture of a runner’s movement and training context. Live in-ear coaching is planned for a later phase and must not be presented as a V1 feature.

## Design system

- Canvas reference: 393 × 852 pt. Use native safe-area constraints and Dynamic Type in the shipped iOS UI.
- Palette: deep blue-green glass surfaces with Voltage lime `#C4F52A` as the primary accent.
- Typography: Apple system sans-serif; preserve the hierarchy and weights in the screen spec.
- Actions: first screen has a single full-width “Let’s start” CTA. Later screens use same-height Back and Continue/Next controls in a shared centered footer; role and goal footers align to their glass panel edges.
- Touch areas: preserve at least 44 × 44 pt. Standard footer buttons are 52 pt high in the reference.
- Photos: supplied as local assets; preserve the image crops and dark legibility treatments shown in the preview.

## Image assets

- `assets/runner-gait-reference.png` — Welcome / “Understand how you move”.
- `assets/velo-lab-treadmill.png` — Lab-quality analysis.
- `assets/velo-anytime-road.png` — Anytime, anywhere.

Keep these filenames and the relative `assets/` directory next to the preview. Confirm production usage rights with the product owner before shipping.

## Preview behavior and implementation boundary

The HTML is a visual and interaction reference, not production application code. It demonstrates navigation, selection states, quiz feedback, and skip behavior. Implement these screens in the app’s existing iOS architecture and connect the production onboarding state and analytics as appropriate. Keep optional answers optional; do not fabricate a selection when a user skips. The quiz compares example Indian service prices and is educational context, not a promised universal price.
