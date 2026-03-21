# Design Context

> This file is the authoritative design source of truth for the Constitutional Governance project.
> All UI decisions must align with this document. Update it when the design direction changes.

## Users

**Primary:** Enterprise engineering teams deploying LLMs in high-stakes domains — customer support, financial advisory, HR automation, medical information, legal review.

**Context:** They are evaluating whether an AI governance tool is trustworthy enough to deploy in production. They see violations in their own LLM outputs, want to understand patterns, and need evidence for compliance reporting. They are sophisticated technical users who distrust hype and evaluate tools on merit.

**Job to be done:** Get observable, auditable evidence of what their AI said and whether it violated their standards. Prove to stakeholders that constitutional governance is rigorous, not theater.

## Brand Personality

**Trustworthy Guard** — A vigilant partner you can rely on. Calm confidence, steady, dependable. Not flashy or attention-seeking. The tool that catches what others miss, consistently, without drama.

**Voice:** Precise, clinical, evidence-first. No marketing language. No "AI-powered" buzzwords. Data speaks; we just make it legible.

**3-word personality:** Calm · Rigorous · Trustworthy

**Anti-personality:** Hype, urgency, startup energy, decorative AI aesthetics

## Aesthetic Direction

**Reference:** Stripe Dashboard — clean, minimal, confident. Subtle motion. Editorial typography hierarchy. Every element earns its place. Dark theme that feels premium rather than default.

**Anti-reference:** AI startup landing pages (no purple gradients, robot illustrations, "AI-powered" buzzwords). Generic enterprise dashboards (no blue sidebar, white cards, tab overload). Playful/consumer aesthetics.

**Theme:** Dark mode primary. Light/dark as a genuine toggle — not just an afterthought. The tool should feel at home in an engineer's terminal and a compliance officer's browser. The dark theme should feel like Stripe's dark mode: intentional, refined, not "dark for dark's sake."

**Color discipline:** Semantic color only carries meaning (severity, compliance score). Never decorative. Backgrounds stay neutral gray-blue. Accent (indigo) used sparingly for primary actions.

## Design Principles

1. **Evidence over aesthetics** — Every visual choice serves data legibility. If decoration doesn't help read the data, it doesn't belong.

2. **Trust is quiet** — The UI should never need to announce its seriousness through heavy borders, loud warnings, or aggressive colors. Calm confidence comes from whitespace, hierarchy, and consistency.

3. **Dense but breathable** — Information-dense like a Bloomberg terminal, but with the typographic discipline of Stripe. Small text is fine. Unreadable text is not.

4. **Monospace earns its place** — JetBrains Mono used for data (scores, timestamps, model names, IDs) and code quotes. Signals precision. Never decorative.

5. **Severity speaks** — Color carries semantic weight: red/orange/yellow/blue/gray for severity levels. Green/amber/red for score thresholds. Use these consistently everywhere. When a violation appears, the color should feel like an alert, not a design choice.

6. **Model-agnostic always** — No real model names or provider logos anywhere in the UI. The tool evaluates any model. Display fictional model names from config. Never imply endorsement of a specific provider.

7. **Motion is functional** — Shimmer skeletons during loading. Smooth scroll to results. Nothing that decorates or delays. If animation serves a cognitive purpose (e.g., drawing attention to a new result), it belongs. Otherwise it doesn't.

## Typography

- **Body:** Instrument Sans 400/500/600/700 — geometric, distinctive, excellent readability. Swap from Inter for personality without sacrificing professionalism.
- **Data/Mono:** JetBrains Mono 400/500 — restricted to genuine data: scores, timestamps, model names, IDs, code quotes. Never decorative.
- **Type scale:** 5-step modular scale using CSS custom properties:
  - `--text-xs` (11px) — uppercase labels with tracking
  - `--text-sm` (13px) — secondary metadata, table cells
  - `--text-base` (15px) — body text, inputs (above 14px minimum)
  - `--text-lg` (18px) — subheadings, model display
  - `--text-xl` (24px) — page heading
- **Weight hierarchy:** 400 body, 500 for interactive labels and secondary text, 600 for headings, 700 for data numbers. Strong contrast between levels — no muddiness.
- **Line-height:** 1.2 tight for headings, 1.4 for labels, 1.55 for body (increased for light-on-dark legibility).

## Layout Rhythm

- 4-column stat grid → full-width evaluate form → split audit log + constitution rules
- Sections separated by subtle borders, not heavy dividers or whitespace
- Cards have consistent 16px padding, 8px border-radius
- Form labels are uppercase tracking-wider at 11px — signals structure without visual weight

## Component Inventory

| Component | States | Notes |
|---|---|---|
| Stat card | Loading (skeleton), populated | Mono font for numbers (data-num class: 700 weight, tabular-nums). Color-coded compliance %. |
| Example chip | Default, hover, active | 13px body text, 500 weight. Category muted, label white. One action: click to evaluate. |
| Evaluate form | Empty, loading, result | Button transitions from indigo → gray while loading. Result panel fades in below. |
| Violation card | Compliant, violated, failed, skipped | Severity badge + explanation (body readable text) + quote (italic mono). |
| Audit log row | Normal, failed (dimmed) | Mono timestamps. Mono model names. Body text for status/score/violations. |
| Constitution rule | Enabled, disabled | ID in mono. Severity badge. Rule text in 13px body. |
| Error banner | Hidden, visible | Red-950 background. Appears at top of layout, not inline. |

## Tech Stack

- **Backend:** FastAPI + uvicorn + SQLite (WAL mode)
- **Frontend:** Single static HTML file. Tailwind CSS (CDN). Vanilla JS. No framework.
- **Fonts:** Google Fonts — Instrument Sans + JetBrains Mono
- **No icons library** — Use HTML entities (✓, ✗, ×) to avoid bundle overhead

## Files

- `service/static/index.html` — The only UI artifact. All design decisions live here.
- `service/app.py` — API config drives model names and provider display in the UI.
- `constitution/rules/` — Constitution rules power the "Constitution Rules" panel.
