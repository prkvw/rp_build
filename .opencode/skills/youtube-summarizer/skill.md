# YouTube Video Summarizer

## Trigger
When the user provides a YouTube URL and asks to summarize it, follow this workflow.

## Workflow

### 1. Extract Content
Run the summarizer script with the YouTube URL:
```bash
python3 summarize.py <youtube-url>
```
This fetches video metadata, chapters, and transcript via YouTube's InnerTube API.

### 2. Understand the Content
Read the generated HTML file to understand the video's structure:
- Title, author, duration, description
- Chapter markers and timestamps
- Full transcript with speaker diarization

### 3. Generate Comprehensive Summary
Use the Dan Koe Comprehensive Content Summarizer prompt to analyze the content:

**System Prompt:**
You are an Expert Content Summarizer with a talent for capturing both key facts and underlying context. Your summaries include essential information, meaningful context, philosophical underpinnings, and subtle nuances that others might overlook. You prioritize comprehensiveness over brevity, ensuring nothing important is missed, while still organizing information efficiently.

**Structure the summary across these sections:**
- **Core Thesis** — The central argument or main purpose (1-2 sentences)
- **Key Points** — Crucial facts, arguments, or conclusions (bulleted)
- **Contextual Framework** — Philosophical, theoretical, historical, or cultural context
- **Detailed Breakdown** — Section-by-section or chronological capture of all significant content
- **Nuanced Perspectives** — Competing viewpoints, counterarguments, or qualifiers
- **Underlying Assumptions** — Unstated premises, worldviews, or biases
- **Connections & Implications** — Broader connections and practical applications

### 4. Generate Visual HTML
Update the HTML file to populate each slide with the real summarized content:

- **Slide 1 (Title)**: Video title, author, duration — dark brand background with ink-blue gradient
- **Slide 2 (Overview)**: Metrics — author, duration, word count
- **Slide 3 (Core Thesis)**: Thesis statement in a card
- **Slide 4 (Key Points)**: Bulleted list with brand arrows
- **Slide 5 (Contextual Framework)**: Context paragraph
- **Slide 6 (Detailed Breakdown)**: Section analysis with timestamps
- **Slide 7 (Nuanced Perspectives)**: Quote-styled counterarguments
- **Slide 8 (Assumptions & Implications)**: Analysis

### 5. Design Rules
Use these design tokens from the Kami design system:
- Background: `#f5f4ed` (parchment) — never pure white
- Accent: `#1B365D` (ink-blue) — use sparingly, < 5% of surface
- Cards: `#faf9f5` (ivory) with `1px solid #e8e6dc` border, 8-12px radius
- Typography: serif (Charter, Georgia) — headings weight 500, body weight 400
- Line-height: titles 1.15, body 1.55
- Animations: fade-up entrance with staggered delays (0.1s increments)
- Shadows: ring (`0 0 0 1px var(--border)`) or whisper (`0 4px 24px rgba(0,0,0,0.05)`) only
- Tags: solid hex backgrounds (`#E4ECF5`, `#EEF2F7`), never rgba

Use the frontend-slides 1920x1080 fixed-stage format:
- `.deck-viewport` fills the window
- `.deck-stage` is 1920x1080, scaled via JS `Math.min(innerW/1920, innerH/1080)`
- Each `.slide` is `position: absolute; inset: 0` with `.active`/`.visible` class toggle
- Navigation: arrow keys, touch swipe, bottom nav bar with progress
- `.reveal` class on elements that should animate in with staggered delays

### 6. Output
Present the generated HTML file as the final result. The user can open it in a browser and navigate through slides with arrow keys.

## Files
- `summarize.py` — Python script that fetches YouTube data and generates the HTML shell
- `summary_*.html` — Generated output file
- `defuddle/` — Content extraction library (reference for InnerTube API approach)
- `kami/` — Design system reference (tokens, styles)
- `frontend-slides/` — Slide presentation format reference (template, animations)
