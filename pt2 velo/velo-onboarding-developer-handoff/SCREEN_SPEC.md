# Velo onboarding: screen flow and UI specification

## Approved visual baseline — 15 October 2026

The current onboarding design is approved and should be treated as locked. Do not change its colors, typography, photo treatments, component dimensions, screen alignment, button layout, or icon styling in later edits unless Nishitha explicitly asks for a change. This includes the centered, consistent-weight non-binary icon on the runner-identity screen. Use `velo-onboarding-approved-2026-10-15.html` as the preserved visual snapshot; the working preview may continue only for explicitly requested new screens or changes.

This preview contains the welcome/intent screens and their next onboarding screens. The Ochy community-count screen is intentionally omitted. Live in-ear coaching remains a later phase; V1 is running-form analysis plus tailored strength/corrective exercises.

## Existing screens

### 1. Welcome / start

**Headline:** Understand how / you move.

**Body:** Velo turns your running video into a clear / picture of your form, then helps you build / strength with exercises made for you.

Use the supplied full-bleed running photo with a dark cinematic scrim. Keep the wordmark centered, copy left-aligned in the lower photo area, and the Voltage lime action above the home indicator.

### 2. How will you use Velo?

Choose one: Runner (for my own training), Coach (for the athletes I coach), or Medical professional (for clinical movement support). Continue is enabled after a selection.

### 3. Choose your path

Choose one: Improve fitness and performance; Learn about my running form; Reduce my injury risk. The chosen goal personalizes the first assessment and exercise plan.

## New screens

### 4. Lab-quality analysis

**Headline:** Velo brings lab-quality analysis to you.

**Body:** Ever wondered what a full analysis of your running form can reveal?

Use the user-supplied treadmill photo at `assets/velo-lab-treadmill.png`, with a deep blue-green scrim, centered Velo wordmark, slim progress indicator, and lime Next action.

### 5. Game time: lab-analysis cost

**Question:** How much do you think a running analysis in a laboratory costs?

Options: ₹2,500; ₹5,000; ₹15,000. The preview marks ₹15,000 correct for a comprehensive advanced biomechanical profile. When a runner chooses incorrectly, animate the selected answer in red and reveal ₹15,000 as the correct answer in the same screen; animate a restrained confetti burst for a correct answer. Pricing varies with the depth of testing: current Indian examples range from ₹2,500 for online video form analysis to ₹3,500 for in-studio running form analysis, ₹5,000 for an advanced gait test, and ₹15,000 for an advanced biomechanical profile that includes gait analysis. This is an educational comparison, not a single standard market price.

Sources: [Run Mechanics pricing](https://runmechanics.in/) and [DY Patil Sports & High Performance Centre pricing](https://dypatilshpc.com/pricing/).

### 6. Anytime, anywhere

**Headline:** Anytime, anywhere.

**Body:** Whether on a treadmill, track, or road, check your form with Velo.

Use the user-supplied road-running photo at `assets/velo-anytime-road.png`, with a cinematic scrim and progress/navigation pattern.

### 7. Personalized analysis

**Headline:** Velo personalizes your analysis by scanning your running form.

**Prompt:** Tell us more about you.

Use the dark deep-green gradient, centered copy, and a lime Let’s go action. Avoid promising data storage behavior in this screen.

### 8. Runner identity

**Question:** How would you identify yourself?

Options: Man; Woman; Non-binary; Prefer not to say. Use four equal-height mutually exclusive rows. Keep a fixed 36 × 36 pt icon cell in every row, center each icon inside it, and reserve the same cell in the text-only “Prefer not to say” row. Leave a clear gap between the two-line question and helper line.

### 9. Running level

**Question:** How would you rate your level in running?

- Beginner — You’ve just started running.
- Intermediate — Your pace is about 4:58–7:09 min/km (converted from 8–11:30 min/mile).
- Advanced — You can run 10 km at about 4:58–6:13 min/km (converted from 8–10 min/mile).
- Elite — You run 10 km or more at 3:56 min/km or faster (converted from 6:20 min/mile or faster).

Use four equal-height rows with the same 36 × 36 pt icon frame. The icon should be a consistent circular pace/proficiency meter with quarter, half, three-quarter, and full lime arcs. These are direct conversions from the reference copy; the pace ranges overlap, so product should revisit the level definitions before using them as a training prescription.

## Shared design and implementation notes

- Reference canvas: 393 × 852 pt. Adapt to device bounds and anchor native content to actual safe areas.
- The welcome screen has one centered “Let’s start” action and no Back button.
- On every later screen, group Back and Next/Continue together in a centered bottom footer. Use matching 52 pt height (48 pt only in the compact-height preview), capsule shape, and 16 pt labels; keep Back narrower with a quiet glass outline and make Next/Continue wider with the Voltage fill. Keep the full group within the bottom safe area.
- Offer Skip on optional intent, goal, and quiz steps. Skipping advances without inventing a selection. “Prefer not to say” remains a direct choice for identity. Show selection and quiz feedback immediately, and let people revisit earlier steps with Back.
- Use Apple system sans-serif, sentence case, left-aligned screen copy, restrained liquid-glass panels, deep blue/green reflections, and Voltage lime `#C4F52A` as the bright accent. Align the welcome CTA to 20 pt screen insets. Align paired footer controls to the same horizontal content grid as their surrounding surface: 14 pt inset to the glass panel edges on role/goal screens, 20 pt inset on other screens. Keep copy edges, card edges, and navigation edges on these shared grids; center single-line helper text and option icons in their own frames. Use a consistent hierarchy: screen headlines 32–36 pt / semibold, question headings 25–27 pt / semibold, body copy 16 pt / regular, option titles 15–16 pt / semibold, helper labels at least 11 pt, and control labels 16 pt / semibold. Buttons are 52 pt high (48 pt in the compact preview) and exceed Apple’s 44 pt minimum touch-target guidance. Use Dynamic Type and system text styles in the native implementation.
- Welcome screen uses the original supplied photo. Lab and anytime screens use the newer user-supplied photographs with dark legibility scrims. Quiz, profile, and level screens use a near-black base with a restrained deep-green gradient and no photo.
- Maintain 44 pt minimum touch targets, visible selection state, keyboard focus, reduced-motion support, and Dynamic Type-safe native implementation.
- Keep the quiz in the “Game time!” format as the Ochy reference. Cost choices are INR; running paces are min/km. Correct/incorrect feedback remains on the quiz screen.


## Nielsen Norman Group heuristic application

This is a design review against the ten heuristics, not a substitute for testing with runners.

1. **Visibility of system status:** Keep the progress indicator visible and expose its step value to assistive technology; selection and quiz feedback appear in place.
2. **Match with the real world:** Use familiar running language, INR pricing, kilometres, and plain action labels.
3. **User control and freedom:** Keep Back discoverable on every screen; provide Skip on optional intent, goal, and quiz steps; preserve “Prefer not to say”; allow earlier answers to be changed.
4. **Consistency and standards:** Use the same centered bottom navigation row, equal-height capsule buttons, selection states, and touch targets throughout. The first welcome screen is the intentional single-action exception.
5. **Error prevention:** Use one-choice radio groups for single-choice questions and confirmation states for quiz answers; avoid treating optional answers as required data.
6. **Recognition rather than recall:** Keep answer choices and contextual helper text visible beside each question.
7. **Flexibility and efficiency:** Let people skip optional learning/personalization steps or go back to change responses.
8. **Aesthetic and minimalist design:** Use one clear lime primary button; keep Back and Skip visually quiet.
9. **Error recognition and recovery:** Show incorrect quiz feedback in red, then reveal the correct answer on that screen; selection can be changed.
10. **Help and documentation:** Explain why profile answers matter in context and clarify that identity answers may be skipped or withheld.
