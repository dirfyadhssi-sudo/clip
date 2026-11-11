# Palette's Journal - ClipSnap

## 2026-11-11 - Accessible segment time inputs and status regions
**Learning:** Single-page video trimming apps frequently use segmented numeric text/number inputs without standard `<label for>` bindings or accessible names, causing screen reader users to be unaware of unit meaning (hours, minutes, seconds). Adding explicit `aria-label` attributes to segmented time inputs and `aria-live="polite"` with `role="alert"`/`role="progressbar"` to dynamic feedback containers ensures real-time feedback and clear navigation without requiring visual design changes.
**Action:** When working on media clipping interfaces, ensure segmented timestamp inputs carry contextual aria-labels and status/error regions announce asynchronous download progress.
