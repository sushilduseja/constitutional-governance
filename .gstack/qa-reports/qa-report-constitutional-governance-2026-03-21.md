# QA Audit Report — Constitutional Governance Dashboard

**Date:** 2026-03-21
**Branch:** main (`91f9255`)
**Target:** `service/static/index.html` + `service/app.py`
**Severity:** Standard (all issues documented)
**Overall Health Score:** 58 / 100

---

## Anti-Patterns Verdict

**Does this look AI-generated?** No — this dashboard passes the AI slop test.

The interface has genuine discipline: no purple gradients, no gradient text on metrics, no glassmorphism, no robot-illustration vibes. The severity color system (red/amber/yellow/blue/gray) is used semantically and consistently. The example chip pattern with category + label is a functional UX choice, not decorative template filler. The dark theme doesn't lean on neon accents or glow effects to compensate for design decisions not being made.

**What does look generic:** Inter + JetBrains Mono as a font pairing signals "developer dashboard" rather than "designed dashboard." Inter is the single most overused font in production UIs — it reads as "I didn't think about typography." JetBrains Mono is fine for data, but Inter for body text in a tool that claims Stripe Dashboard as its reference is a gap between ambition and execution.

**One AI slop tell that slipped through:** The `placeholder-gray-600` on inputs at `text-sm` (12px) fails WCAG AA contrast (see Critical below). This is the most common accessibility failure pattern in AI-generated dark dashboards — muted placeholder text that looks "clean" but fails contrast.

---

## Executive Summary

| Severity | Count | Top Issues |
|---|---|---|
| Critical | 2 | Placeholder contrast failure, missing keyboard accessibility |
| High | 4 | Missing focus rings, touch targets too small, pure gray palette |
| Medium | 5 | No landmarks, placeholder-as-label, font pairing, skeleton animation |
| Low | 6 | Minor spacing inconsistencies, no reduced-motion, verbose HTML entities |

**Top 3 to fix first:**
1. **Placeholder contrast** — All `placeholder-gray-600` text fails WCAG AA at 12px. Fixing this costs one Tailwind class change.
2. **No focus indicators** — `outline: none` on all interactive elements with zero replacement. Keyboard users can't see where they are.
3. **All touch targets <44px** — Every button, chip, and icon button fails mobile accessibility.

**Score by category:**

| Category | Score | Notes |
|---|---|---|
| Console | 100 | No JS errors observed |
| Visual | 55 | Placeholder contrast + pure gray palette + generic font pairing |
| Functional | 70 | Missing focus, missing skip links, no landmarks |
| Accessibility | 35 | Critical contrast + focus + touch target failures |
| Performance | 80 | Clean — no layout thrashing, standard CDN caching |
| Theming | 60 | Pure gray tokens throughout, body is pure black, no brand tint |
| Responsive | 65 | Table overflow on mobile, logo may truncate, reasonable breakpoints |
| Links | 100 | No broken links |

---

## Critical Issues

### C-001: Placeholder text fails WCAG AA contrast at small font sizes

**Location:** `index.html:120, 127` — input fields
**Severity:** Critical — WCAG A violation, legally significant
**Category:** Accessibility

**What:** `placeholder-gray-600` (`#4B5563`) on `text-sm` (12px) input fields.

**WCAG Analysis:**
- Body text at <18px needs **4.5:1** (AA)
- `#4B5563` on `#111827` (gray-800 background) = approximately **2.6:1** — FAILS
- Even `placeholder-gray-400` would barely pass
- `placeholder-gray-500` on the same background = approximately **3.5:1** — FAILS AA

**Impact:** Placeholder text is used as secondary prompts ("Ask the monitored model anything...", "Additional context..."). Users with visual impairments cannot read these. Legal risk for enterprise deployments.

**Recommendation:** Increase placeholder opacity/value to `placeholder-gray-300` (`#D1D5DB`) or switch placeholder color to `#9CA3AF` on `text-xs` (10px) which meets 4.5:1. The "Stripe reference" aesthetic achieves muted placeholder text by using `--color-base-400` against a surface that's `#F6FAFC`, not gray-800. On dark backgrounds you need higher luminance values for placeholder text.

**Fix in practice:** Change `placeholder-gray-600` → `placeholder-gray-400` at minimum. Best: `placeholder-gray-500` + reduce placeholder font-size to 11px.

---

### C-002: All interactive elements remove focus indicator without replacement

**Location:** `index.html:44` — `textarea:focus, input:focus { outline: none; }`
**Location:** All `<button>` elements — no focus ring defined
**Severity:** Critical — WCAG 2.1 Success Criterion 2.4.7 (Focus Visible)
**Category:** Accessibility

**What:** Every interactive element has `outline: none` with no `:focus-visible` replacement. Keyboard users (Tab navigation, screen readers, motor impairments) cannot see which element has focus.

**Impact:** Complete accessibility failure for keyboard-only users. Screen reader users who also navigate by keyboard are entirely blocked.

**Recommendation:** Add `:focus-visible` ring using the indigo accent color:

```css
:focus-visible {
  outline: 2px solid #6366f1; /* indigo-500 */
  outline-offset: 2px;
}
```

This should apply to all buttons, inputs, and interactive elements. The Stripe Dashboard approach uses a subtle 1px indigo ring — not heavy, but always visible.

---

## High-Severity Issues

### H-001: All touch targets are below 44x44px minimum

**Location:** `index.html:60` — refresh button (~36px wide)
**Location:** `index.html:132` — evaluate button (~64px wide, but ~36px tall)
**Location:** `index.html:372` — example chips (~32px wide, ~28px tall)
**Location:** `index.html:397` — close button (~40px wide, ~24px tall)
**Location:** `index.html:502` — submit button
**Severity:** High — WCAG 2.1 Success Criterion 2.5.5 (Target Size)
**Category:** Accessibility / Responsive

**What:** Every interactive element is smaller than the 44x44px minimum for touch targets. The example chips (12px font, 1px padding = ~28px touch target) are particularly problematic.

**Impact:** Mobile users frequently mis-tap. This is the most common mobile usability failure in enterprise dashboards.

**Recommendation:** Increase padding on all buttons to create 44px+ touch targets. For example chips, use `px-3 py-2` instead of `px-2 py-1`. For the close button, use `px-3 py-2` or add a pseudo-element for tap area expansion.

---

### H-002: Pure gray palette — no brand tint

**Location:** `index.html:28-39` — inline CSS + all Tailwind `gray-*` classes throughout
**Severity:** High — Design quality issue
**Category:** Theming / Brand

**What:** All neutral colors use Tailwind's pure gray scale (zero chroma/hue). The body background is pure `#0a0e14` (approaching pure black). The DESIGN.md principle states: "Add a subtle hint of your brand hue to all neutrals — even a chroma of 0.005-0.01 is enough to feel natural."

**Impact:** The palette feels like "default Tailwind dark theme" rather than a designed system. Pure gray at extreme lightness values (#0a0e14 is ~2% black, nearly pure black) lacks the sophistication of a tinted neutral. The Stripe reference uses cool-tinted grays toward blue — `#0A0E14` has no warmth, making the entire dashboard feel cold and mechanical.

**Recommendation:** Tint the gray palette toward a subtle hue (blue for professional/tech, or warm gray). Example: `body { background-color: oklch(6% 0.01 250); }` adds a barely perceptible blue cast that makes the dark background feel intentional rather than defaulted-to. The stat cards, input fields, and table rows should all use this tinted surface color.

---

### H-003: Missing semantic HTML landmarks

**Location:** `index.html:49-203` — entire `<body>` content
**Severity:** High — Accessibility / Structure
**Category:** Accessibility

**What:** The page has no `<header>`, `<main>`, `<footer>`, or `<nav>` landmarks. All content is a flat div hierarchy inside `<body>`. No `<section>` or `<article>` for major content regions.

**Impact:** Screen reader users rely on landmarks to navigate. Without them, the entire dashboard is one undifferentiated block. This makes the app effectively unusable with a screen reader.

**Recommendation:** Wrap major sections in semantic landmarks:
```html
<header><!-- header content --></header>
<main>
  <!-- stats, evaluate form, example results -->
</main>
<footer><!-- optional footer --></footer>
```

---

### H-004: No skip link for keyboard navigation

**Location:** `index.html` — missing entirely
**Severity:** High — WCAG 2.1 Success Criterion 2.4.1 (Bypass Blocks)
**Category:** Accessibility

**What:** No "Skip to main content" link exists. Keyboard users must tab through all navigation elements (header, form, every example chip) to reach the audit log.

**Impact:** Tedious keyboard navigation. WCAG violation.

**Recommendation:** Add as the first element in `<body>`:
```html
<a href="#main-content" class="sr-only focus:not-sr-only ...">Skip to main content</a>
```
With CSS that shows it only on focus.

---

## Medium-Severity Issues

### M-001: Placeholder text used as label proxy on optional context field

**Location:** `index.html:126-127` — context input
**Severity:** Medium — WCAG violation (placeholder as label pattern)
**Category:** Accessibility

**What:** The context field uses `placeholder="Additional context or conversation history..."` without a visible `<label>`. This is the textbook "placeholder as label" anti-pattern. The input does have a `<label>` element, but the placeholder text is more descriptive than the label ("Context (optional)").

**Impact:** When users start typing, the placeholder disappears and only "Context (optional)" remains — less informative. Also fails if the label font-size has poor contrast (gray-600 label vs gray-500 text).

**Recommendation:** Keep the label but make it more descriptive: `"System context or conversation history"`. Remove the `(optional)` suffix — all labels are implicitly optional unless marked required.

---

### M-002: Skeleton animation lacks reduced-motion support

**Location:** `index.html:34-43` — shimmer animation
**Severity:** Medium — Accessibility
**Category:** Performance / Accessibility

**What:** The skeleton shimmer animation runs continuously with no `prefers-reduced-motion` media query. The `@keyframes shimmer` and `.skeleton` class have no motion guard.

**Impact:** Vestibular disorders affect ~35% of adults over 40. Continuous motion causes discomfort.

**Recommendation:** Add:
```css
@media (prefers-reduced-motion: reduce) {
  .skeleton {
    animation: none;
    background: #1f2937; /* static mid-tone */
  }
}
```

---

### M-003: Inter is the single most overused font in production UIs

**Location:** `index.html:10` — Google Fonts import
**Severity:** Medium — Brand differentiation
**Category:** Visual / Brand

**What:** Inter is loaded as the primary font. The Stripe Dashboard reference uses a custom or semi-custom type system. Inter on a dark dashboard reads as "default Tailwind" rather than "designed for this product."

**Impact:** Undermines the "Trustworthy Guard" brand personality. The reference aesthetic ("Stripe Dashboard clean minimal confident") requires typographic choices that feel intentional, not inherited.

**Recommendation (Deferred):** Per the design context, this is a brand-level decision. If the ambition is truly Stripe-level polish, swap Inter for something with more personality: **Instrument Sans** (clean but distinctive), **Outfit** (geometric, modern), or **DM Sans** (friendly-professional). This is a Medium because the current typography is functional — it's a differentiation gap, not a failure.

---

### M-004: Example result panels use `visible` class toggling with no animation

**Location:** `index.html:420-421, 425-427` — `classList.add/remove('visible')`
**Severity:** Medium — UX / Motion
**Category:** UX

**What:** Clicking an example chip toggles `display: none` → `display: block` instantly with no transition. Panels also use `scrollIntoView({ behavior: 'smooth' })` — but the panel itself has no entrance animation.

**Impact:** Abrupt appearance feels jarring, especially on a dashboard that otherwise uses subtle shimmer skeletons (indicating loading awareness). Inconsistent with the "Trustworthy Guard" calm confidence personality.

**Recommendation:** Add a subtle fade-in for example result panels:
```css
.example-result {
  animation: fadeIn 200ms ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
```

---

### M-005: Loading button state sets text but not aria-live

**Location:** `index.html:514-516` — button disabled + text change
**Severity:** Medium — Accessibility
**Category:** Accessibility

**What:** When the evaluate button is clicked, its text changes to "Calling LLM..." but there's no `aria-live` region or `aria-busy` announcement for screen reader users.

**Impact:** Screen reader users don't know the action is in progress. They may re-submit or assume the form is broken.

**Recommendation:** Add `aria-live="polite"` to the result div, or add `aria-busy="true"` to the form during evaluation. The shimmer skeletons already provide visual loading feedback for sighted users.

---

## Low-Severity Issues

### L-001: `border-radius: 3px` on scrollbar conflicts with 8px on cards

**Location:** `index.html:32` — `border-radius: 3px` on scrollbar thumb
**Severity:** Low — Visual consistency
**Category:** Visual

**What:** Cards use `rounded-lg` (8px), but the scrollbar thumb uses 3px. Inconsistent rounding language.

**Impact:** Trivial visual inconsistency. Not noticeable to most users.

**Recommendation:** Change to `border-radius: 8px` or `border-radius: 9999px` (pill) for the scrollbar.

---

### L-002: No zoom prevention on pinch gestures

**Location:** `index.html:5` — viewport meta
**Severity:** Low — Performance
**Category:** Responsive

**What:** No `maximum-scale=1` on viewport meta. While zooming is generally good for accessibility, dashboard UIs often break at non-100% zoom due to fixed-width elements.

**Impact:** Dashboard is dense — zooming may cause layout breakage on some pages. Low risk since the app is data-focused.

**Recommendation:** Add `maximum-scale=1` to viewport meta, but consider the accessibility trade-off. Alternatively, ensure all fixed-width elements use fluid equivalents.

---

### L-003: `<title>` is generic "AI Governance"

**Location:** `index.html:6` — `<title>AI Governance</title>`
**Severity:** Low — Content / UX
**Category:** Content

**What:** Browser tab shows "AI Governance" — not descriptive. Users with multiple tabs can't distinguish this app from others.

**Impact:** Minor usability issue. Users may lose track of the tab.

**Recommendation:** "Constitutional Governance — Monitoring Dashboard" or "AI Governance | Compliance Monitor".

---

### L-004: `&#10003;` and `&#10007;` HTML entities are accessible but verbose

**Location:** `index.html:351-352` — status badges
**Severity:** Low — Code quality
**Category:** Performance

**What:** Unicode HTML entities (`&#10003;` = ✓, `&#10007;` = ✗) are used instead of inline SVGs or text characters. These render fine but are harder to style with CSS.

**Impact:** The DESIGN.md states "no icons library — use HTML entities" which this follows. However, the entities themselves can't be directly styled (color, weight) without CSS content tricks.

**Recommendation:** Keep as-is per design guidelines. If icon styling is needed, use `<svg>` inline. Current approach is acceptable.

---

### L-005: Shimmer skeleton background uses hard-coded hex colors

**Location:** `index.html:39` — `background: linear-gradient(90deg, #1f2937 25%, #374151 50%, #1f2937 75%)`
**Severity:** Low — Theming
**Category:** Theming

**What:** The shimmer uses Tailwind hex values directly rather than CSS custom properties, making dark/light theme adaptation harder.

**Impact:** If light mode is added later, the skeleton will need manual recoloring.

**Recommendation:** Extract to CSS custom properties:
```css
:root {
  --skeleton-from: var(--color-surface-2);
  --skeleton-via: var(--color-surface-3);
}
```

---

### L-006: Table overflow on mobile uses `max-height` with scrollbar

**Location:** `index.html:165` — `style="max-height: 420px;"` + `overflow-auto`
**Severity:** Low — Responsive
**Category:** Responsive

**What:** The audit log table scrolls internally with a scrollbar appearing on overflow. On narrow viewports, the sticky header may misalign with scrolling body columns.

**Impact:** Minor on mobile. Table headers may not perfectly align with body columns during horizontal scroll.

**Recommendation:** Add `display: block` + `overflow-x: auto` pattern for mobile table transformation, using `data-label` attributes on cells to create a card-based mobile view.

---

## Positive Findings

- **Severity color system is exemplary** — red/amber/yellow/blue/gray used exclusively for semantic meaning (severity levels, score thresholds). This is exactly right. The violations section with severity badges + explanations + quoted text is the best-designed component in the dashboard.
- **No decorative motion** — No bounce easing, no elastic animations, no animation that serves no purpose. The shimmer skeletons and smooth scroll are the only motion — both functional.
- **No icon library dependency** — HTML entities for check/cross are pragmatic and lightweight. No SVG sprites, no CDN icon library overhead.
- **Data density is appropriate** — The audit log, constitution rules panel, and stats row all have the right information density. This is a professional tool, not a marketing page.
- **No broken API calls** — All four parallel fetches (`config`, `stats`, `constitution`, `audit-log`) use proper error handling with a single error banner.
- **No layout thrashing** — No reading/writing layout properties in loops. DOM updates are batched into single `innerHTML` assignments.
- **Shimmer skeletons are well-implemented** — Using `background-size: 200%` with a smooth linear gradient, correct `border-radius`, and `animation` shorthand. Best skeleton implementation in the codebase.
- **Error boundary is clean** — Failed evaluations render with distinct badge + dimmed row opacity. Failed API calls show a red error banner. No silent failures.

---

## Recommendations by Priority

### Immediate (Critical — fix today)

1. **C-001: Fix placeholder contrast** — Change `placeholder-gray-600` to `placeholder-gray-400` (minimum) on all input fields. One-class change.
2. **C-002: Add focus rings** — Add `:focus-visible` CSS for all buttons, inputs, and interactive elements. Three lines of CSS.

### Short-term (High — this sprint)

3. **H-1: Enlarge touch targets** — Increase padding on all buttons to 44px+. Priority on example chips and close buttons.
4. **H-2: Tint the gray palette** — Replace `body { background-color: #0a0e14 }` with `oklch(6% 0.01 250)`. Add subtle hue to card backgrounds. This single change elevates the entire visual quality.
5. **H-3: Add semantic landmarks** — Wrap in `<header>`, `<main>`, `<footer>`.
6. **H-4: Add skip link** — One `<a>` tag + CSS.

### Medium-term (this sprint / next)

7. **M-1: Improve label text** on context field — descriptive labels > placeholder hints.
8. **M-2: Add reduced-motion** for skeleton shimmer.
9. **M-4: Animate example panel entrance** — 200ms fade-in.
10. **M-5: Add aria-live for loading state**.

### Long-term (nice-to-have)

11. **L-3: Improve page title** to "Constitutional Governance — Dashboard" or similar.
12. **L-5: Extract skeleton colors to CSS custom properties**.
13. **L-6: Mobile table transformation** — card-based mobile view for audit log.

---

## Suggested Commands for Fixes

| Issue(s) | Command | Why |
|---|---|---|
| **C-001** (placeholder contrast) | `/normalize` | Aligns placeholder colors with design tokens, fixes contrast across all form inputs |
| **C-002** (focus rings) | `/harden` | Adds `:focus-visible` rings, focus management for keyboard navigation |
| **H-1** (touch targets) | `/adapt` | Enlarges touch targets to 44px+ across mobile experience |
| **H-2** (gray palette) | `/colorize` | Adds subtle brand hue tint to the gray palette, elevates dark theme quality |
| **H-3 + H-4** (landmarks, skip link) | `/harden` | Adds semantic HTML landmarks and skip navigation for accessibility |
| **M-1** (label text) | `/clarify` | Improves label copy and input helper text across the form |
| **M-2** (reduced motion) | `/animate` | Adds `prefers-reduced-motion` support for skeleton and panel animations |
| **M-4** (panel animation) | `/animate` | Adds fade-in entrance for example result panels |
| **M-5** (aria-live) | `/harden` | Adds aria-live regions for async state announcements |
| **L-1** (scrollbar radius) | `/polish` | Fixes scrollbar border-radius to match card rounding |
| **L-6** (mobile table) | `/adapt` | Transforms audit log table to card layout on mobile |
| **All theming** | `/normalize` | Consolidates all inline colors and Tailwind arbitrary values into CSS custom properties |

**Recommended primary commands:**
- `/harden` — Addresses C-002, H-3, H-4, M-5 (accessibility, landmarks, focus, aria-live)
- `/normalize` — Addresses C-001, L-5 (contrast, color tokens, palette foundation)
- `/adapt` — Addresses H-1, L-6 (touch targets, mobile table)
- `/colorize` — Addresses H-2 (brand-tinted gray palette)

---

## Patterns & Systemic Issues

1. **Inline CSS in `<style>` block**: All custom CSS lives in a single `<style>` block at the top of the HTML. As the dashboard grows, this will become unmaintainable. Extract to a separate `styles.css` file.
2. **No CSS custom properties**: All colors are either Tailwind arbitrary values (`#0a0e14`) or Tailwind classes. No CSS variables means no theming API, no easy dark/light toggle. The entire inline CSS block needs to be rewritten to use custom properties.
3. **Tailwind arbitrary values scattered throughout**: `text-[11px]`, `text-[10px]`, `text-[9px]` — these are fine for a single file but indicate no typographic scale system. A fluid `text-xs/10px` system would be more maintainable.
4. **Pure black background on body**: `#0a0e14` is ~97% black. Pure black (`#000`) is a design smell. Even a 6% gray with a subtle hue tint would be more refined.

---

*Report generated by systematic QA audit across accessibility, performance, theming, responsive, and anti-pattern dimensions.*
