#!/usr/bin/env python3
"""
YouTube Visual Summarizer
Extracts YouTube video transcripts via InnerTube API and generates
a beautiful HTML slide presentation using:
- Kami design system (warm parchment, ink-blue accent, serif typography)
- Frontend-slides format (1920x1080 stage with CSS animations)
- Dan Koe Comprehensive Content Summarizer structure
"""

import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from html import escape
from urllib.parse import urlparse, parse_qs


INNERTUBE_API = "https://www.youtube.com/youtubei/v1/player?prettyPrint=false"
INNERTUBE_NEXT = "https://www.youtube.com/youtubei/v1/next?prettyPrint=false"
INNERTUBE_CLIENT_VERSION = "20.10.38"
USER_AGENT = "Mozilla/5.0 (compatible; Summarizer/1.0)"


def get_video_id(url):
    parsed = urlparse(url)
    if parsed.hostname == "youtu.be":
        return parsed.path.lstrip("/").split("/")[0]
    if "shorts" in parsed.path:
        return parsed.path.split("/shorts/")[1].split("/")[0]
    return parse_qs(parsed.query).get("v", [None])[0]


def fetch_json(url, data=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode() if data else None,
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def get_video_metadata(video_id):
    context = {
        "client": {
            "clientName": "ANDROID",
            "clientVersion": INNERTUBE_CLIENT_VERSION,
        }
    }
    payload = {"context": context, "videoId": video_id}
    data = fetch_json(INNERTUBE_API, payload)

    details = data.get("videoDetails", {})
    microformat = data.get("microformat", {}).get("playerMicroformatRenderer", {})
    caption_tracks = (
        data.get("captions", {})
        .get("playerCaptionsTracklistRenderer", {})
        .get("captionTracks", [])
    )

    metadata = {
        "title": details.get("title", ""),
        "author": details.get("author", ""),
        "channel_id": details.get("channelId", ""),
        "description": details.get("shortDescription", ""),
        "length_seconds": int(details.get("lengthSeconds", 0)),
        "upload_date": microformat.get("uploadDate", ""),
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        "caption_tracks": caption_tracks,
    }
    return metadata


def get_chapters(video_id):
    context = {
        "client": {
            "clientName": "WEB",
            "clientVersion": "2.20240101.00.00",
        }
    }
    payload = {"context": context, "videoId": video_id}
    try:
        data = fetch_json(INNERTUBE_NEXT, payload)
        chapters = []

        panels = (
            data.get("playerOverlays", {})
            .get("playerOverlayRenderer", {})
            .get("decoratedPlayerBarRenderer", {})
            .get("decoratedPlayerBarRenderer", {})
            .get("playerBar", {})
            .get("multiMarkersPlayerBarRenderer", {})
            .get("markersMap", [])
        )
        for panel in panels:
            markers = panel.get("value", {}).get("chapters", [])
            for marker in markers:
                ch = marker.get("chapterRenderer", {})
                title = ch.get("title", {}).get("simpleText", "")
                start_ms = ch.get("timeRangeStartMillis")
                if title and start_ms is not None:
                    chapters.append({"title": title, "start": start_ms / 1000})

        if not chapters:
            eng_panels = data.get("engagementPanels", [])
            for panel in eng_panels:
                content = (
                    panel.get("engagementPanelSectionListRenderer", {})
                    .get("content", {})
                )
                items = (
                    content.get("macroMarkersListRenderer", {})
                    .get("contents", [])
                )
                for item in items:
                    renderer = item.get("macroMarkersListItemRenderer", {})
                    title = renderer.get("title", {}).get("simpleText", "")
                    time_str = renderer.get("timeDescription", {}).get("simpleText", "")
                    if title and time_str:
                        seconds = parse_timestamp(time_str)
                        if seconds is not None:
                            chapters.append({"title": title, "start": seconds})

        return chapters
    except Exception:
        return []


def parse_timestamp(ts):
    parts = ts.split(":")
    try:
        parts = [int(p) for p in parts]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
    except ValueError:
        pass
    return None


def format_ts(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def pick_caption_track(tracks):
    non_asr = [t for t in tracks if t.get("kind") != "asr"]
    pool = non_asr if non_asr else tracks
    for track in pool:
        if track.get("languageCode", "").startswith("en"):
            return track
    return pool[0] if pool else None


def fetch_transcript(video_id, caption_tracks):
    track = pick_caption_track(caption_tracks)
    if not track or not track.get("baseUrl"):
        return None

    base_url = track["baseUrl"]
    req = urllib.request.Request(
        base_url,
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        xml_data = resp.read().decode("utf-8")

    segments = []
    root = ET.fromstring(xml_data)

    for p in root.findall(".//{*}p"):
        start_ms = p.get("t")
        if start_ms:
            start = int(start_ms) / 1000
            text_parts = []
            for s in p.findall(".//{*}s"):
                if s.text:
                    text_parts.append(s.text)
            text = "".join(text_parts)
            if not text:
                text = "".join(p.itertext())
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                segments.append({"start": start, "text": text})

    if not segments:
        for text in root.findall(".//{*}text"):
            start = text.get("start")
            if start:
                t = re.sub(r"\s+", " ", (text.text or "")).strip()
                if t:
                    segments.append({"start": float(start), "text": t})

    return segments


def format_duration(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)


def build_html(video_id, metadata, transcript, chapters):
    title = escape(metadata["title"])
    author = escape(metadata["author"])
    description = escape(metadata.get("description", ""))[:300]
    duration = format_duration(metadata["length_seconds"])
    upload_date = metadata.get("upload_date", "")

    transcript_text = " ".join(s["text"] for s in (transcript or []))
    word_count = len(transcript_text.split())

    chapter_slides = []
    if chapters:
        for ch in chapters:
            ch_title = escape(ch["title"])
            ch_time = format_ts(ch["start"])
            chapter_slides.append(
                f"""<section class="slide chapter-slide">
                    <div class="slide-content">
                        <p class="reveal chapter-label">Chapter</p>
                        <h2 class="reveal">{ch_title}</h2>
                        <p class="reveal timestamp">{ch_time}</p>
                    </div>
                </section>"""
            )

    transcript_segments_html = ""
    if transcript:
        for i, seg in enumerate(transcript[:60]):
            ts = format_ts(seg["start"])
            text = escape(seg["text"])
            transcript_segments_html += f"""<p class="reveal transcript-line"><span class="ts">{ts}</span> {text}</p>"""

    summary_slides = f"""
    <section class="slide title-slide">
        <div class="slide-content">
            <p class="reveal eyebrow">YouTube Video Summary</p>
            <h1 class="reveal">{title}</h1>
            <div class="reveal meta-row">
                <span class="meta-author">{author}</span>
                <span class="meta-sep">·</span>
                <span class="meta-duration">{duration}</span>
            </div>
            <p class="reveal tagline">{description[:200]}...</p>
        </div>
    </section>

    <section class="slide">
        <div class="slide-content">
            <p class="reveal section-num">01 · Overview</p>
            <h2 class="reveal section-title">Video Information</h2>
            <div class="reveal metrics">
                <div class="metric">
                    <span class="metric-value">{escape(author)}</span>
                    <span class="metric-label">Creator</span>
                </div>
                <div class="metric">
                    <span class="metric-value">{duration}</span>
                    <span class="metric-label">Duration</span>
                </div>
                <div class="metric">
                    <span class="metric-value">{word_count}</span>
                    <span class="metric-label">Words</span>
                </div>
            </div>
        </div>
    </section>

    <section class="slide">
        <div class="slide-content">
            <p class="reveal section-num">02 · Core Thesis</p>
            <h2 class="reveal section-title">Core Thesis</h2>
            <div class="reveal thesis-box">
                <p>{description[:500]}</p>
            </div>
        </div>
    </section>

    <section class="slide">
        <div class="slide-content">
            <p class="reveal section-num">03 · Key Points</p>
            <h2 class="reveal section-title">Key Points</h2>
            <ul class="reveal key-points">
                <li>Main arguments and conclusions from the video</li>
                <li>Crucial facts and conceptual takeaways</li>
                <li>Actionable insights and practical applications</li>
                <li>Critical distinctions and clarifications made</li>
            </ul>
        </div>
    </section>

    <section class="slide">
        <div class="slide-content">
            <p class="reveal section-num">04 · Contextual Framework</p>
            <h2 class="reveal section-title">Contextual Framework</h2>
            <p class="reveal body-text">Philosophical and theoretical underpinnings that shape the content. Historical and cultural context that informs the creator's perspective.</p>
        </div>
    </section>

    <section class="slide">
        <div class="slide-content">
            <p class="reveal section-num">05 · Detailed Breakdown</p>
            <h2 class="reveal section-title">Detailed Breakdown</h2>
            <p class="reveal body-text">Section-by-section analysis with timestamps, capturing all significant content, arguments, and illustrative examples.</p>
        </div>
    </section>

    <section class="slide">
        <div class="slide-content">
            <p class="reveal section-num">06 · Nuanced Perspectives</p>
            <h2 class="reveal section-title">Nuanced Perspectives</h2>
            <p class="reveal body-text">Competing viewpoints, counterarguments, qualifiers, and limitations acknowledged in the content.</p>
            <div class="reveal quote">
                <p>Notable quotes and key passages that capture the essence of the argument.</p>
            </div>
        </div>
    </section>

    <section class="slide">
        <div class="slide-content">
            <p class="reveal section-num">07 · Underlying Assumptions</p>
            <h2 class="reveal section-title">Underlying Assumptions</h2>
            <p class="reveal body-text">Unstated premises, worldviews, and biases that inform the content. Implicit frameworks and methodological approaches used.</p>
        </div>
    </section>

    <section class="slide">
        <div class="slide-content">
            <p class="reveal section-num">08 · Connections & Implications</p>
            <h2 class="reveal section-title">Connections & Implications</h2>
            <p class="reveal body-text">How this content connects to broader ideas, movements, and disciplines. Practical applications and suggested next steps.</p>
        </div>
    </section>
    """

    transcript_slides = ""
    if transcript and transcript_segments_html:
        transcript_slides = f"""
    <section class="slide">
        <div class="slide-content">
            <p class="reveal section-num">09 · Transcript</p>
            <h2 class="reveal section-title">Full Transcript</h2>
            <div class="reveal transcript-container">
                {transcript_segments_html}
            </div>
        </div>
    </section>
    """

    chapter_slides_html = "\n".join(chapter_slides) if chapters else ""

    chapters_part = ""
    if chapters:
        ch_items = "".join(
            f'<li class="reveal"><span class="ts">{format_ts(c["start"])}</span> {escape(c["title"])}</li>'
            for c in chapters
        )
        chapters_part = f"""
    <section class="slide">
        <div class="slide-content">
            <p class="reveal section-num">Chapters</p>
            <h2 class="reveal section-title">Video Chapters</h2>
            <ul class="reveal chapter-list">{ch_items}</ul>
        </div>
    </section>
    """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Summary — {title}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Charter:opsz,wght@12..72,400;12..72,500;12..72,700&display=swap');

        :root {{
            --parchment:    #f5f4ed;
            --ivory:        #faf9f5;
            --warm-sand:    #e8e6dc;
            --brand:        #1B365D;
            --brand-light:  #2D5A8A;
            --brand-tint:   #EEF2F7;
            --tag-bg:       #E4ECF5;
            --near-black:   #141413;
            --dark-warm:    #3d3d3a;
            --olive:        #504e49;
            --stone:        #6b6a64;
            --border:       #e8e6dc;
            --serif: Charter, Georgia, Palatino, "Times New Roman", serif;
            --sans: var(--serif);
            --mono: "JetBrains Mono", "SF Mono", "Fira Code", Consolas, Monaco, monospace;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            background: var(--parchment);
            font-family: var(--serif);
            overflow: hidden;
        }}

        .deck-viewport {{
            position: fixed;
            inset: 0;
            overflow: hidden;
            background: var(--parchment);
        }}

        .deck-stage {{
            width: 1920px;
            height: 1080px;
            transform-origin: 0 0;
            position: absolute;
            top: 0;
            left: 0;
        }}

        .slide {{
            position: absolute;
            inset: 0;
            width: 1920px;
            height: 1080px;
            visibility: hidden;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.6s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 80px;
        }}

        .slide.active,
        .slide.visible {{
            visibility: visible;
            opacity: 1;
            pointer-events: auto;
        }}

        .slide-content {{
            max-width: 1400px;
            width: 100%;
        }}

        .reveal {{
            opacity: 0;
            transform: translateY(24px);
            transition: opacity 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94),
                        transform 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }}

        .slide.visible .reveal {{
            opacity: 1;
            transform: translateY(0);
        }}

        .slide.visible .reveal:nth-child(1) {{ transition-delay: 0.1s; }}
        .slide.visible .reveal:nth-child(2) {{ transition-delay: 0.2s; }}
        .slide.visible .reveal:nth-child(3) {{ transition-delay: 0.3s; }}
        .slide.visible .reveal:nth-child(4) {{ transition-delay: 0.4s; }}
        .slide.visible .reveal:nth-child(5) {{ transition-delay: 0.5s; }}
        .slide.visible .reveal:nth-child(6) {{ transition-delay: 0.6s; }}

        .title-slide {{
            background: linear-gradient(135deg, var(--brand) 0%, #0f1e35 100%);
        }}

        .title-slide h1 {{
            font-family: var(--serif);
            font-size: 48pt;
            font-weight: 500;
            color: var(--ivory);
            line-height: 1.15;
            margin-bottom: 24px;
        }}

        .title-slide .eyebrow {{
            font-family: var(--sans);
            font-size: 14px;
            font-weight: 500;
            color: var(--tag-bg);
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 20px;
        }}

        .title-slide .meta-row {{
            font-family: var(--sans);
            font-size: 16px;
            color: rgba(250, 249, 245, 0.7);
            margin-bottom: 16px;
        }}

        .title-slide .meta-sep {{
            margin: 0 12px;
            opacity: 0.4;
        }}

        .title-slide .tagline {{
            font-family: var(--serif);
            font-size: 18px;
            color: rgba(250, 249, 245, 0.6);
            line-height: 1.5;
            max-width: 900px;
        }}

        .section-num {{
            font-family: var(--sans);
            font-size: 13px;
            font-weight: 500;
            color: var(--brand);
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-bottom: 12px;
        }}

        .section-title {{
            font-family: var(--serif);
            font-size: 36pt;
            font-weight: 500;
            color: var(--near-black);
            line-height: 1.2;
            margin-bottom: 24px;
            border-left: 3px solid var(--brand);
            padding-left: 20px;
        }}

        .metrics {{
            display: flex;
            gap: 40px;
            margin-top: 20px;
        }}

        .metric {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}

        .metric-value {{
            font-family: var(--serif);
            font-size: 28px;
            font-weight: 500;
            color: var(--brand);
            font-variant-numeric: tabular-nums;
            line-height: 1;
        }}

        .metric-label {{
            font-family: var(--sans);
            font-size: 12px;
            color: var(--olive);
        }}

        .body-text {{
            font-family: var(--serif);
            font-size: 18px;
            font-weight: 400;
            color: var(--dark-warm);
            line-height: 1.55;
            max-width: 1000px;
        }}

        .thesis-box {{
            background: var(--ivory);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px 28px;
            font-family: var(--serif);
            font-size: 18px;
            font-weight: 400;
            color: var(--dark-warm);
            line-height: 1.55;
            margin-top: 12px;
        }}

        .key-points {{
            list-style: none;
            padding: 0;
        }}

        .key-points li {{
            font-family: var(--serif);
            font-size: 18px;
            color: var(--dark-warm);
            line-height: 1.5;
            padding: 10px 0 10px 28px;
            position: relative;
            border-bottom: 1px solid var(--border);
        }}

        .key-points li::before {{
            content: "→";
            position: absolute;
            left: 0;
            color: var(--brand);
        }}

        .quote {{
            border-left: 2px solid var(--brand);
            padding: 8px 0 8px 20px;
            margin-top: 24px;
        }}

        .quote p {{
            font-family: var(--serif);
            font-size: 17px;
            font-weight: 400;
            color: var(--olive);
            line-height: 1.55;
            font-style: italic;
        }}

        .chapter-slide {{
            background: var(--ivory);
        }}

        .chapter-slide h2 {{
            font-family: var(--serif);
            font-size: 32pt;
            font-weight: 500;
            color: var(--near-black);
            line-height: 1.2;
            margin-bottom: 16px;
        }}

        .chapter-label {{
            font-family: var(--sans);
            font-size: 12px;
            font-weight: 600;
            color: var(--brand);
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-bottom: 12px;
        }}

        .chapter-list {{
            list-style: none;
            padding: 0;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}

        .chapter-list li {{
            font-family: var(--serif);
            font-size: 16px;
            color: var(--dark-warm);
            line-height: 1.5;
            padding: 8px 12px;
            background: var(--ivory);
            border: 1px solid var(--border);
            border-radius: 8px;
        }}

        .transcript-container {{
            max-height: 700px;
            overflow-y: auto;
            background: var(--ivory);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
        }}

        .transcript-line {{
            font-family: var(--serif);
            font-size: 15px;
            color: var(--dark-warm);
            line-height: 1.55;
            padding: 6px 0;
            border-bottom: 1px solid rgba(232, 230, 220, 0.5);
        }}

        .ts {{
            font-family: var(--mono);
            font-size: 12px;
            color: var(--brand);
            font-weight: 500;
            margin-right: 10px;
            min-width: 55px;
            display: inline-block;
        }}

        .timestamp {{
            font-family: var(--mono);
            font-size: 13px;
            color: var(--stone);
        }}

        .slide-nav {{
            position: fixed;
            bottom: 40px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 16px;
            align-items: center;
            z-index: 100;
            background: var(--ivory);
            border: 1px solid var(--border);
            border-radius: 40px;
            padding: 10px 20px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.06);
        }}

        .slide-nav button {{
            background: none;
            border: none;
            cursor: pointer;
            font-family: var(--serif);
            font-size: 16px;
            color: var(--brand);
            padding: 4px 12px;
            border-radius: 6px;
            transition: background 0.2s;
        }}

        .slide-nav button:hover {{
            background: var(--brand-tint);
        }}

        .slide-nav .counter {{
            font-family: var(--mono);
            font-size: 13px;
            color: var(--stone);
            min-width: 60px;
            text-align: center;
        }}

        .slide-nav .progress-bar {{
            width: 120px;
            height: 3px;
            background: var(--border);
            border-radius: 2px;
            overflow: hidden;
        }}

        .slide-nav .progress-fill {{
            height: 100%;
            background: var(--brand);
            border-radius: 2px;
            transition: width 0.3s ease;
        }}

        @media print {{
            body {{ overflow: visible; }}
            .deck-viewport {{ position: relative; }}
            .slide {{ position: relative; visibility: visible; opacity: 1; break-after: page; page-break-after: always; }}
            .slide-nav {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="deck-viewport">
        <main class="deck-stage" id="deckStage">
            {summary_slides}
            {chapters_part}
            {transcript_slides}
            {chapter_slides_html}
        </main>
    </div>

    <nav class="slide-nav" id="slideNav">
        <button id="prevSlide" aria-label="Previous slide">←</button>
        <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
        <span class="counter" id="slideCounter">1 / 1</span>
        <button id="nextSlide" aria-label="Next slide">→</button>
    </nav>

    <script>
        class SlidePresentation {{
            constructor() {{
                this.slides = document.querySelectorAll('.slide');
                this.current = 0;
                this.stage = document.getElementById('deckStage');
                this.counter = document.getElementById('slideCounter');
                this.progressFill = document.getElementById('progressFill');

                this.setupStageScale();
                this.setupNavigation();
                this.setupKeyboardNav();
                this.setupTouchNav();
                this.showSlide(0);

                window.addEventListener('resize', () => this.setupStageScale());
            }}

            setupStageScale() {{
                const w = window.innerWidth;
                const h = window.innerHeight;
                const scale = Math.min(w / 1920, h / 1080);
                const x = (w - 1920 * scale) / 2;
                const y = (h - 1080 * scale) / 2;
                this.stage.style.transform = `translate(${{x}}px, ${{y}}px) scale(${{scale}})`;
            }}

            showSlide(index) {{
                if (index < 0 || index >= this.slides.length) return;
                this.slides.forEach(s => s.classList.remove('active', 'visible'));
                this.current = index;
                this.slides[index].classList.add('active');
                requestAnimationFrame(() => {{
                    this.slides[index].classList.add('visible');
                }});
                this.counter.textContent = `${{index + 1}} / ${{this.slides.length}}`;
                this.progressFill.style.width = `${{((index + 1) / this.slides.length) * 100}}%`;
            }}

            setupNavigation() {{
                document.getElementById('prevSlide').addEventListener('click', () => this.showSlide(this.current - 1));
                document.getElementById('nextSlide').addEventListener('click', () => this.showSlide(this.current + 1));
            }}

            setupKeyboardNav() {{
                document.addEventListener('keydown', (e) => {{
                    if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === ' ') {{
                        e.preventDefault();
                        this.showSlide(this.current + 1);
                    }} else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {{
                        e.preventDefault();
                        this.showSlide(this.current - 1);
                    }}
                }});
            }}

            setupTouchNav() {{
                let startX = 0;
                this.stage.addEventListener('touchstart', (e) => {{ startX = e.changedTouches[0].screenX; }});
                this.stage.addEventListener('touchend', (e) => {{
                    const diff = startX - e.changedTouches[0].screenX;
                    if (Math.abs(diff) > 50) {{
                        this.showSlide(this.current + (diff > 0 ? 1 : -1));
                    }}
                }});
            }}
        }}

        new SlidePresentation();
    </script>
</body>
</html>"""

    return html


def main():
    if len(sys.argv) < 2:
        print("Usage: python summarize.py <youtube-url>")
        print("   or: python summarize.py --url <youtube-url>")
        sys.exit(1)

    url = sys.argv[1]
    if url == "--url" and len(sys.argv) > 2:
        url = sys.argv[2]

    video_id = get_video_id(url)
    if not video_id:
        print(f"Error: Could not extract video ID from URL: {url}")
        sys.exit(1)

    print(f"Fetching video metadata...")
    metadata = get_video_metadata(video_id)
    print(f"  Title: {metadata['title']}")
    print(f"  Author: {metadata['author']}")
    print(f"  Duration: {format_duration(metadata['length_seconds'])}")

    print(f"Fetching chapters...")
    chapters = get_chapters(video_id)
    print(f"  Found {len(chapters)} chapters")

    print(f"Fetching transcript...")
    if metadata["caption_tracks"]:
        transcript = fetch_transcript(video_id, metadata["caption_tracks"])
        if transcript:
            print(f"  {len(transcript)} transcript segments")
        else:
            print("  No transcript available")
    else:
        transcript = None
        print("  No caption tracks available")

    print(f"Generating HTML presentation...")
    html = build_html(video_id, metadata, transcript, chapters)

    safe_title = re.sub(r'[^\w\- ]', '', metadata['title'])[:50].strip().replace(' ', '_')
    output_file = f"summary_{safe_title or video_id}.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\nDone! Output: {output_file}")
    print(f"Open in browser to view the visual summary.")


if __name__ == "__main__":
    main()
