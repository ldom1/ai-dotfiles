---
name: website-to-hyperframes-core
description: Reusable workflow for generating promotional HyperFrames videos from a brand profile + source HTML/URL. Works across projects (epidemie-des-mots, clawvis, etc.).
user-invocable: true
---

# website-to-hyperframes-core

Turn a website or HTML document into a short promotional video using HyperFrames. Designed for multi-project reuse — brand identity is loaded from a project-local profile.

## Prerequisites

Project must have `npx skills add heygen-com/hyperframes` installed and the following skills available:
- `/website-to-hyperframes` — URL capture → HyperFrames composition
- `/hyperframes` — composition authoring rules
- `/gsap` — animation patterns

## Workflow

### Step 1 — Load brand profile

Read the project's brand profile at `promotion/video/<project-name>.json`. It defines:

```json
{
  "name": "App name",
  "tagline": "Short tagline",
  "palette": { "primary": "#hex", "accent": "#hex", "bg": "#hex", "text": "#hex" },
  "typography": { "heading": "Font name", "body": "Font name" },
  "tone": "minimal | bold | playful | editorial",
  "cta": "Call-to-action text",
  "duration": 15
}
```

If the profile doesn't exist, create it before proceeding.

### Step 2 — Capture source

If given a URL: invoke `/website-to-hyperframes` to capture the page and generate a base composition.

If given raw HTML/design: extract key visual elements (hero, colors, typography) manually and build the composition from scratch using `/hyperframes`.

### Step 3 — Build composition

Output directory: `promotion/video/hyperframes/<project-name>-promo/`

Required files:
- `index.html` — root timeline, ~`duration`s, poster frame at 0s
- `hyperframes.json` — project config (`npx hyperframes init` then fill metadata)
- `meta.json` — `{ "id": "<slug>", "name": "<App> Promo" }`
- `assets/` — logo SVG, any supporting media

Apply brand profile: palette → CSS variables, typography → Google Fonts import, tone → animation style, cta → final scene.

### Step 4 — Lint

Always run after writing any `.html` file:

```bash
npx hyperframes lint
```

Fix all errors. Warnings are informational.

### Step 5 — Preview

```bash
npx hyperframes preview
```

Confirm timing, transitions, and CTA visibility in the browser before considering done.

## Composition structure (15s template)

| Time     | Scene                        |
|----------|------------------------------|
| 0–3s     | Logo/wordmark intro          |
| 3–10s    | Core value prop (2–3 beats)  |
| 10–13s   | Social proof or key feature  |
| 13–15s   | CTA + logo lockup            |

## Extending for a new project

1. Create `promotion/video/<new-project>.json` in the app's project repo
2. Run this skill pointing at that profile
3. Output lands in `promotion/video/hyperframes/<new-project>-promo/`
