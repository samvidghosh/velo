# Velo account entry · Screen specification

## Flow

`Welcome → Choose sign-up or log in`

Returning runner: `Log in → Home`

New runner: `Sign up · email → Sign up · email entered → Finish signing up`

Apple and Google authentication are available on the login and email sign-up screens. A successful provider sign-in follows the same account completion and onboarding path as email sign-up.

## Screen 1 · Welcome

**Purpose:** introduce Velo’s movement-understanding promise and offer the two account paths.

**Copy:** “Know your stride. Build stronger miles.” Supporting line: “Understand how you move. Get a gait analysis and strength work shaped around you.”

**Actions:** `Sign up` (primary) and `Log in` (secondary).

**Layout:** full-bleed motion-softened runner photo; lower photo area receives a deep scrim. Place lowercase Velo mark near the top safe area. Left-align the headline and support text; anchor two large actions above the bottom safe area.

## Screen 2 · Returning runner login

**Purpose:** let an existing runner return to their saved assessments and movement history.

**Elements:** heading “Welcome back”; email and password fields; `Forgot password?`; primary `Log in`; divider; `Continue with Apple`; `Continue with Google`; `New to Velo? Create account`.

**Behavior:** use email and secure password entry; support password managers and the system keyboard. Forgot password starts recovery. Login errors appear next to the relevant field or in a clear inline message. Provider sign-in starts the matching native authorization flow.

## Screen 3 · Sign up · email empty

**Purpose:** collect the email address for a new account.

**Elements:** heading “Sign up”; short account-creation description; labeled email field; disabled `Continue` until the address is valid; legal consent with separate Privacy Policy and Terms links; Apple and Google options; existing-account login link.

**Behavior:** validate the email address before enabling Continue. Keep terms readable and links independently tappable.

## Screen 4 · Sign up · email entered

This is the same layout as Screen 3 with a valid address populated and the `Continue` button enabled. Continue proceeds to Screen 5 and carries the email address forward.

## Screen 5 · Finish signing up

**Purpose:** complete email-based account creation.

**Elements:** first-name, password, and repeat-password fields; primary `Create account` action.

**Behavior:** preserve the email from Screen 4. Password fields are secure inputs. Validate the configured password policy and matching values; show inline feedback. On success, continue into Velo’s running onboarding flow.

## Shared layout and Apple dimensions

- Use the device’s actual safe areas for status bar, Dynamic Island, and home indicator. The 393 × 852 pt preview is a reference canvas, not a fixed layout.
- Minimum interactive hit region: 44 × 44 pt. Main buttons are shown at 48–50 pt high; fields at 52 pt.
- Use SF system text and Dynamic Type. Body copy is 15–16 pt in the mockup; legal copy is 12 pt. Never clip enlarged text; forms scroll and bottom actions remain reachable.
- Maintain legible contrast over photography using the dark scrim. Check contrast in light and dark appearance.
- Use keyboard-safe scrolling, correct email/password content types, secure text entry, and visible focus states.

## Design tokens

| Token | Value | Use |
|---|---|---|
| Graphite olive | `#10140A` | Primary canvas |
| Deep moss | `#354719` | Secondary depth |
| Voltage lime | `#C4F52A` | Primary actions / key emphasis |
| Pale lime | `#EDFF9A` | Highlight / subtle mark |
| Text | `#F7F5F0` | Primary copy |
| Font | Apple system sans-serif | All interface text |

## V1 boundary and product context

V1 delivers running gait analysis and personalized corrective or strength exercises. Repeated assessments and training history build a persistent understanding of each runner. Live in-ear coaching is a later phase; do not claim it is available in V1.

## Build dependencies

Connect the product’s authentication backend, Apple and Google OAuth configuration, password and recovery rules, and final policy URLs. Replace `runner@example.com` and `Runner` with actual user data. Confirm the desired post-auth onboarding route and error copy with the product owner before release.
