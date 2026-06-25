# rp_build — YouTube Visual Summarizer

Generates beautiful HTML slide presentations from YouTube videos using the **Kami** design system and **frontend-slides** animation framework, with content extraction inspired by **defuddle**.

## Overview

Give it a YouTube URL, and it produces a single self-contained HTML file with:

- **Kami design system** — warm parchment `#f5f4ed` background, ink-blue `#1B365D` accent, serif typography, metric cards, quotes, and tag components
- **frontend-slides format** — 1920×1080 fixed-stage layout with CSS entrance animations, keyboard/touch navigation, and progress bar
- **Dan Koe Comprehensive Summarizer** — structured sections: Overview, Core Thesis, Key Points, Contextual Framework, Detailed Breakdown, Nuanced Perspectives, Underlying Assumptions, Connections & Implications
- **YouTube transcript** — extracted via InnerTube API (same approach as defuddle), with speaker diarization and chapter markers

## Repos Integrated

| Repo | Role |
|------|------|
| [frontend-slides](https://github.com/zarazhangrui/frontend-slides) | HTML slide presentation structure and animations |
| [kami](https://github.com/tw93/kami) | Design system (colors, typography, spacing, components) |
| [defuddle](https://github.com/kepano/defuddle) | Content extraction methodology (InnerTube API, transcript parsing) |

## Requirements

- Python 3
- Only standard library modules (`json`, `urllib`, `xml.etree.ElementTree`)

## Usage

```bash
python3 summarize.py <youtube-url>
```

Example:

```bash
python3 summarize.py "https://www.youtube.com/watch?v=jNQXAC9IVRw"
```

This generates `summary_<video-title>.html` — open it in any browser.

### Navigation

| Input | Action |
|-------|--------|
| → / ↓ / Space | Next slide |
| ← / ↑ | Previous slide |
| Click nav arrows | Previous / Next |
| Touch swipe | Navigate slides |
| Print (Ctrl+P) | Print-friendly layout |

## Output

A single `.html` file with all CSS and JavaScript inline — zero dependencies, works offline.

## Credits

- [Dan Koe](https://x.com/thedankoe/status/1897996820716175735) — Comprehensive Content Summarizer prompt
- [Zara Zhang](https://github.com/zarazhangrui/frontend-slides) — Frontend Slides
- [Tw93](https://github.com/tw93/kami) — Kami design system
- [Kepano](https://github.com/kepano/defuddle) — Defuddle content extraction
