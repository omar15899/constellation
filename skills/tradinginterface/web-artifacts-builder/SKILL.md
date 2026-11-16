---
name: web-artifacts-builder
description: "Build complex claude.ai artifacts using the React+TypeScript+Vite+Tailwind+shadcn/ui build pipeline (init-artifact.sh + bundle-artifact.sh → single bundled HTML). Use when the artifact needs state management, routing, or 40+ shadcn/ui components. Not for simple HTML/JSX (use frontend-design) or static art (use canvas-design)."
license: Complete terms in LICENSE.txt
---

# Web Artifacts Builder

To build powerful frontend claude.ai artifacts, follow these steps:
1. Initialize the frontend repo using `scripts/init-artifact.sh`
2. Develop your artifact by editing the generated code
3. Bundle all code into a single HTML file using `scripts/bundle-artifact.sh`
4. Display artifact to user
5. (Optional) Test the artifact

**Stack**: React 18 + TypeScript + Vite + Parcel (bundling) + Tailwind CSS + shadcn/ui

## Design & Style Guidelines

VERY IMPORTANT: To avoid what is often referred to as "AI slop", avoid using excessive centered layouts, purple gradients, uniform rounded corners, and Inter font.

## Quick Start

### Step 1: Initialize Project

Run the initialization script to create a new React project:
```bash
bash scripts/init-artifact.sh <project-name>
cd <project-name>
```

This creates a fully configured project with:
- ✅ React + TypeScript (via Vite)
- ✅ Tailwind CSS 3.4.1 with shadcn/ui theming system
- ✅ Path aliases (`@/`) configured
- ✅ 40+ shadcn/ui components pre-installed
- ✅ All Radix UI dependencies included
- ✅ Parcel configured for bundling (via .parcelrc)
- ✅ Node 18+ compatibility (auto-detects and pins Vite version)

### Step 2: Develop Your Artifact

Edit the generated files. See **Common Development Tasks** below for guidance.

### Step 3: Bundle to Single HTML File

```bash
bash scripts/bundle-artifact.sh
```

Creates `bundle.html` — a self-contained artifact with all JavaScript, CSS, and dependencies inlined.

**What the script does**:
- Installs bundling dependencies (parcel, @parcel/config-default, parcel-resolver-tspaths, html-inline)
- Creates `.parcelrc` config with path alias support
- Builds with Parcel (no source maps)
- Inlines all assets into single HTML using html-inline

### Step 4: Share Artifact

Share the bundled HTML file in conversation so the user can view it as an artifact.

### Step 5: Testing (Optional)

Use available tools (Playwright, Puppeteer) if requested or if issues arise. Avoid testing upfront — it adds latency.

## Reference

- **shadcn/ui components**: https://ui.shadcn.com/docs/components
