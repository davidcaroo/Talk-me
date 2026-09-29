# Talk-me Landing Page Implementation Plan (Impeccable Craft & GitHub Pages)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a world-class, responsive, modern, light-themed minimalist landing page for **Talk-me (Voice Dictation)**, ready for zero-friction GitHub Pages deployment (`docs/` folder), featuring liquid glass styling, interactive voice dictation simulation, interactive feature bento grid, and direct Windows installer download.

**Architecture:** 
- **Delivery Model:** Static site inside `docs/` (`docs/index.html`, `docs/styles.css`, `docs/app.js`, `docs/assets/`) serving as the root for GitHub Pages (Source: Branch `main`, Folder `/docs`). Zero build tools required for deployment, pure HTML5/CSS3/ES6+ with CSS Custom Properties and Canvas API.
- **Design System & UX Craft (Impeccable):** Light theme, luminous visionOS liquid glass aesthetic, neo-grotesque typography (`Inter`), accessible contrast (WCAG AAA), ambient glow mesh gradients, interactive canvas waveform visualizer, simulated push-to-talk interactive playground, and responsive bento grid.
- **Interactive Simulator:** Live interactive widget demonstrating Talk-me: user clicks or holds spacebar to activate floating overlay with canvas waveform, transcribes sample phrases, and inlays text with auto-typing into a mockup chat/code editor.

**Tech Stack:** Semantic HTML5, CSS3 Modern Tokens (CSS Grid, Flexbox, Glassmorphism, CSS Custom Properties), Vanilla JavaScript (ES6 Modules, Canvas 2D API, IntersectionObserver, Web Audio synthetics), Lucide Icons (SVG inline), GitHub Pages.

**Spec:** Persuade Mode (Impeccable):
- Clear visual hierarchy: Header/Nav -> Hero with Live Simulator -> Metric Counters -> Feature Bento Grid -> How it Works (3 Steps) -> Comparison Matrix vs Cloud Tools -> Architecture / Privacy Proof -> FAQ Accordion -> Footer & Download CTA.
- Primary Call to Action: Download `VoiceDictation-Setup-1.0.0.exe` directly + GitHub Stars.

## Global Constraints

- 100% static, zero-build dependency (serves directly from GitHub Pages `/docs`).
- Light theme first: Porcelain white canvas (`#FBFBFD`), subtle lavender/cyan ambient glows, slate neutral typography (`#0F172A`, `#475569`), vibrant cobalt/indigo accents (`#2563EB`, `#3B82F6`).
- Mobile-first responsive design (320px to 4K displays).
- Accessible (ARIA landmarks, focus rings, keyboard accessible simulator, `prefers-reduced-motion` compliance).
- Fast: 100/100 Lighthouse performance target, zero heavy third-party tracking or bloated frameworks.

---

### Task 1: Design Tokens, Typography & Layout Architecture (`docs/styles.css`)

**Files:**
- Create: `docs/styles.css`
- Test: `tests/test_landing_page.py` (automated DOM/CSS structure verification)

**Interfaces:**
- Produces: CSS Custom Properties design system (`--bg-primary`, `--accent-primary`, `--glass-bg`, `--glass-border`, `--font-sans`, `--shadow-elevation`, etc.), reset, layout utilities, glassmorphism card classes.

- [ ] **Step 1: Write automated validation test in `tests/test_landing_page.py`**
Verify that `docs/styles.css` defines root variables for light theme, glassmorphism tokens, and responsive media queries.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_landing_page.py -v`

- [ ] **Step 3: Implement `docs/styles.css`**
Define complete light-theme token palette:
- Background: `#FBFBFD` with subtle radial mesh gradients.
- Typography: Inter with optical sizing and negative letter-spacing for headlines.
- Liquid glass tokens: `backdrop-filter: blur(24px)`, soft multi-layer shadow, translucent border.
- Bento grid and flex layout systems.
- Transitions and micro-interaction styles.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_landing_page.py -v`

- [ ] **Step 5: Commit**
`git add docs/styles.css tests/test_landing_page.py`
`git commit -m "feat(landing): establish modern light-theme design tokens and typography"`

---

### Task 2: Core Semantic HTML5 Structure & Brand Assets (`docs/index.html` & `docs/assets/`)

**Files:**
- Create: `docs/index.html`
- Create: `docs/assets/logo.svg`
- Modify: `tests/test_landing_page.py`

**Interfaces:**
- Consumes: `docs/styles.css`
- Produces: Semantic HTML5 structure (Header, Hero, Simulator Section, Bento Features, Workflow, Comparison, FAQ, Footer), meta tags for SEO/OpenGraph, accessible SVG icons.

- [ ] **Step 1: Write failing test in `tests/test_landing_page.py`**
Assert presence of semantic sections (`<header>`, `<main>`, `<section id="hero">`, `<section id="demo">`, `<section id="features">`, `<section id="comparison">`, `<section id="faq">`, `<footer>`) and brand logo.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_landing_page.py -v`

- [ ] **Step 3: Implement `docs/assets/logo.svg` and `docs/index.html`**
- Create vector brand logo `docs/assets/logo.svg` combining the soundwave and microphone in visionOS minimal style.
- Build semantic structure with compelling copywriting explaining Talk-me:
  - Hero: *"Tu voz, convertida en texto en milisegundos. 100% Privado y Local en tu PC."*
  - CTAs: *"Descargar para Windows (v1.0.0)"* + *"Ver en GitHub"*.
  - Bento grid cards: Privacidad absoluta (Offline Whisper), Latencia cero (RAM Warmup), Inyección en cualquier app (Cursor, VS Code, Word, WhatsApp), Detección inteligente de silencios (VAD).
  - Comparison table: Talk-me vs Dictado Windows vs Wispr Flow vs Dragon.
  - Interactive FAQ with `<details><summary>`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_landing_page.py -v`

- [ ] **Step 5: Commit**
`git add docs/index.html docs/assets/logo.svg tests/test_landing_page.py`
`git commit -m "feat(landing): create semantic structure, brand logo and high-impact copy"`

---

### Task 3: Interactive Voice Dictation Simulator & Canvas Waveform (`docs/app.js`)

**Files:**
- Create: `docs/app.js`
- Modify: `tests/test_landing_page.py`

**Interfaces:**
- Consumes: DOM elements in `docs/index.html`
- Produces: Interactive simulation engine (interactive spacebar hold / button click, real-time waveform canvas animation, typing cursor effect in target mockup window, sound effects toggle).

- [ ] **Step 1: Write failing test in `tests/test_landing_page.py`**
Verify `docs/app.js` exists and exports/initializes simulator, waveform rendering, and FAQ accordion interactions.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_landing_page.py -v`

- [ ] **Step 3: Implement `docs/app.js`**
- Smooth canvas visualizer simulating dynamic audio amplitudes.
- Push-to-talk interactive simulator:
  - User clicks or presses spacebar.
  - Floating visionOS capsule appears with live wave motion and "Escuchando...".
  - Releases: capsule shows "Transcribiendo..." (0.2s) -> "Texto insertado".
  - Target chat/editor mockup receives animated typewriter text insertion.
- Bento cards 3D tilt on mouse hover (subtle perspective effect).
- Scroll reveal animations with IntersectionObserver.
- Release version downloader auto-link to latest release asset.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_landing_page.py -v`

- [ ] **Step 5: Commit**
`git add docs/app.js tests/test_landing_page.py`
`git commit -m "feat(landing): add interactive dictation simulator and canvas visualizer"`

---

### Task 4: Visual Polish, Micro-interactions, Responsive Audit & Craft Pass

**Files:**
- Modify: `docs/styles.css`
- Modify: `docs/index.html`
- Modify: `docs/app.js`
- Test: `tests/test_landing_page.py`

**Interfaces:**
- Impeccable review pass: Eliminate any visual awkwardness, verify mobile viewports (375px, 768px, 1024px, 1440px), ensure WCAG AAA contrast, add smooth glass hover states, ambient blur glows.

- [ ] **Step 1: Write test for responsive breakpoints and accessibility tokens**
Verify mobile breakpoint queries and accessibility attributes (`aria-expanded`, `role="region"`, `alt` tags).

- [ ] **Step 2: Run test to verify it fails or needs additions**
Run: `pytest tests/test_landing_page.py -v`

- [ ] **Step 3: Implement polish pass**
- Refine button micro-interactions (magnetic feel, subtle active press scale 0.98).
- Liquid glass reflection highlights on card borders.
- Floating badges: *"Whisper AI Local"*, *"Open Source"*, *"0ms Cloud Latency"*.
- Mobile navigation drawer or clean compact sticky header.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_landing_page.py -v`

- [ ] **Step 5: Commit**
`git add docs/styles.css docs/index.html docs/app.js tests/test_landing_page.py`
`git commit -m "style(landing): polish micro-interactions, liquid glass effects and mobile responsiveness"`

---

### Task 5: GitHub Pages Configuration & Deployment Workflow

**Files:**
- Create: `.github/workflows/deploy-pages.yml` (optional GitHub Action for automated Pages deployment)
- Modify: `README.md` (add Landing Page link & badge)
- Test: `tests/test_landing_page.py`

**Interfaces:**
- Consumes: `docs/`
- Produces: Live URL on `https://davidcaroo.github.io/Talk-me/`

- [ ] **Step 1: Write test to verify GitHub Pages entrypoint validity**
Verify `docs/index.html` has valid relative paths and OpenGraph tags for `https://davidcaroo.github.io/Talk-me/`.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_landing_page.py -v`

- [ ] **Step 3: Implement `.github/workflows/deploy-pages.yml` and update `README.md`**
Configure native GitHub Pages deployment action with artifact upload or branch documentation. Add live landing page link in `README.md`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_landing_page.py -v`

- [ ] **Step 5: Commit**
`git add .github/workflows/deploy-pages.yml README.md tests/test_landing_page.py`
`git commit -m "ci(pages): configure automated GitHub Pages deployment for landing page"`
