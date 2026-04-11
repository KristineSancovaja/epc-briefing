#!/usr/bin/env python3
"""
EPC ISO 20022 Daily Briefing Agent
Run by GitHub Actions every weekday morning.
Writes docs/index.html which is served by GitHub Pages.
"""

import os
import json
import argparse
import re
from datetime import datetime
from pathlib import Path

import anthropic

DEFAULT_TOPIC  = "ISO 20022 payment standard EPC European Payments Council"
DEFAULT_OUTPUT = Path(__file__).parent / "docs" / "index.html"
HISTORY_FILE   = Path(__file__).parent / "docs" / "history.json"


def run_agent(topic: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    system = f"""You are a financial regulation intelligence agent monitoring the European
Payments Council (EPC) for ISO 20022 payment standard news.

Search europeanpaymentscouncil.eu and authoritative financial sources for the
most recent publications, rulebook updates, consultations, and news about: "{topic}".

Return ONLY a JSON object with no markdown, no preamble:
{{
  "topic": "the topic searched",
  "retrieved_at": "ISO 8601 datetime",
  "items": [
    {{
      "title": "full article or publication title",
      "date": "publication date (e.g. March 2025)",
      "tag": "one of: Rulebook | Consultation | News | Regulation | Technical | Event",
      "summary": "2-3 sentence plain-language summary",
      "url": "URL if found, else empty string"
    }}
  ],
  "agent_note": "brief note on sources and any limitations"
}}

Find 4-6 of the most recent relevant items from 2024-2026."""

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        system=system,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{
            "role": "user",
            "content": f"Search for the latest EPC and ISO 20022 news about: {topic}. Return JSON only."
        }],
    )

    raw = " ".join(b.text for b in response.content if b.type == "text")
    clean = re.sub(r"```json|```", "", raw).strip()
    s, e = clean.find("{"), clean.rfind("}")
    if s == -1 or e == -1:
        raise ValueError(f"No JSON in response: {raw[:300]}")
    return json.loads(clean[s:e+1])


def tag_css(tag: str) -> str:
    t = tag.lower()
    if "rulebook"   in t: return "background:#EBF7F0;color:#2D7A4F"
    if "consult"    in t: return "background:#FEF5E7;color:#8B5E14"
    if "tech"       in t: return "background:#F0EBF8;color:#5A3E8A"
    if "event"      in t: return "background:#FDECEA;color:#C0392B"
    if "regulation" in t: return "background:#EBF4FB;color:#1B6CA8"
    return "background:#F0EFEB;color:#5A5A54"


def render_html(result: dict, history: list) -> str:
    now     = datetime.now()
    items   = result.get("items", [])
    note    = result.get("agent_note", "")
    runs    = len(history)

    cards = ""
    for item in items:
        url = item.get("url") or "https://www.europeanpaymentscouncil.eu/news-insights/news"
        cards += f"""
        <article class="card">
          <div class="card-meta">
            <span class="tag" style="{tag_css(item.get('tag',''))}">{item.get('tag','News')}</span>
            <span class="date">{item.get('date','')}</span>
          </div>
          <h2 class="card-title">{item.get('title','')}</h2>
          <p class="card-summary">{item.get('summary','')}</p>
          <a class="card-link" href="{url}" target="_blank">Read on EPC &#8594;</a>
        </article>"""

    hist_rows = ""
    for h in history[:8]:
        hist_rows += f"""
        <div class="hist-row">
          <span class="hist-date">{h.get('date','')}</span>
          <span class="hist-n">{len(h.get('items',[]))} items</span>
        </div>"""
    if not hist_rows:
        hist_rows = '<p class="muted">No prior runs</p>'

    note_block = f'<div class="note-box">{note}</div>' if note else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EPC ISO 20022 Briefing {now.strftime('%d %b %Y')}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=Instrument+Sans:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Instrument Sans',sans-serif;background:#F4F2EE;color:#1A1A1A;min-height:100vh}}
header{{background:#0B1F3A;border-bottom:2px solid #E8A020;padding:0 2rem}}
.hdr{{max-width:1100px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;height:56px}}
.badge{{background:#E8A020;color:#0B1F3A;font-family:'DM Mono',monospace;font-size:11px;font-weight:500;padding:3px 8px;border-radius:3px}}
.hdr-name{{color:#fff;font-size:14px;font-weight:500;margin-left:10px}}
.hdr-date{{font-family:'DM Mono',monospace;font-size:11px;color:rgba(255,255,255,.4)}}
.hero{{background:#142D52;padding:3rem 2rem 2rem}}
.hero-inner{{max-width:1100px;margin:0 auto}}
.hero-eyebrow{{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.12em;color:#F5C05A;text-transform:uppercase;margin-bottom:10px}}
h1{{font-family:'DM Serif Display',serif;font-size:clamp(26px,4vw,46px);color:#fff;line-height:1.15;margin-bottom:8px}}
h1 em{{color:#F5C05A;font-style:italic}}
.hero-sub{{font-size:14px;color:rgba(255,255,255,.5);margin-bottom:1.5rem;max-width:500px;line-height:1.6}}
.stats{{display:flex;gap:2rem}}
.stat-n{{font-family:'DM Serif Display',serif;font-size:26px;color:#F5C05A;display:block}}
.stat-l{{font-size:11px;color:rgba(255,255,255,.35);letter-spacing:.05em}}
.main{{max-width:1100px;margin:0 auto;padding:2rem;display:grid;grid-template-columns:1fr 280px;gap:2rem;align-items:start}}
@media(max-width:780px){{.main{{grid-template-columns:1fr}}}}
.feed-hdr{{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:1rem}}
.feed-title{{font-family:'DM Serif Display',serif;font-size:20px;color:#0B1F3A}}
.feed-count{{font-family:'DM Mono',monospace;font-size:11px;color:#888}}
.card{{background:#fff;border:1px solid rgba(11,31,58,.1);border-radius:6px;padding:1.25rem;margin-bottom:1rem}}
.card-meta{{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}}
.tag{{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.06em;text-transform:uppercase;padding:3px 8px;border-radius:2px}}
.date{{font-family:'DM Mono',monospace;font-size:11px;color:#888}}
.card-title{{font-family:'DM Serif Display',serif;font-size:17px;color:#0B1F3A;line-height:1.3;margin-bottom:8px}}
.card-summary{{font-size:13px;color:#555;line-height:1.7;margin-bottom:10px}}
.card-link{{font-size:12px;color:#1B6CA8;text-decoration:none;font-weight:500}}
.sidebar-card{{background:#fff;border:1px solid rgba(11,31,58,.1);border-radius:6px;padding:1.25rem;margin-bottom:1rem}}
.sidebar-title{{font-family:'DM Serif Display',serif;font-size:15px;color:#0B1F3A;margin-bottom:.75rem;padding-bottom:8px;border-bottom:1px solid rgba(11,31,58,.08)}}
.hist-row{{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid rgba(11,31,58,.06);font-size:12px}}
.hist-row:last-child{{border-bottom:none}}
.hist-date{{font-family:'DM Mono',monospace;color:#555}}
.hist-n{{font-family:'DM Mono',monospace;color:#aaa}}
.note-box{{font-size:12px;color:#888;line-height:1.6;font-style:italic;background:#F4F2EE;border-radius:4px;padding:10px;margin-top:8px}}
.muted{{font-size:13px;color:#aaa;padding:4px 0}}
footer{{background:#0B1F3A;padding:1.25rem 2rem;margin-top:4rem}}
.ftr{{max-width:1100px;margin:0 auto;display:flex;justify-content:space-between;align-items:center}}
.ftr-l{{font-family:'DM Mono',monospace;font-size:11px;color:rgba(255,255,255,.25)}}
.ftr-r{{font-size:11px;color:rgba(255,255,255,.2)}}
.ftr-r span{{color:#E8A020}}
</style>
</head>
<body>
<header>
  <div class="hdr">
    <div><span class="badge">ISO 20022</span><span class="hdr-name">EPC Intelligence Briefing</span></div>
    <span class="hdr-date">{now.strftime('%A, %d %B %Y')}</span>
  </div>
</header>
<section class="hero">
  <div class="hero-inner">
    <p class="hero-eyebrow">European Payments Council - Daily Monitor</p>
    <h1>Payment Standards<br><em>Intelligence Feed</em></h1>
    <p class="hero-sub">AI-powered daily digest of EPC publications, rulebooks, and consultations on ISO 20022.</p>
    <div class="stats">
      <div><span class="stat-n">{len(items)}</span><span class="stat-l">items today</span></div>
      <div><span class="stat-n">{runs}</span><span class="stat-l">total runs</span></div>
      <div><span class="stat-n">{now.strftime('%d %b')}</span><span class="stat-l">generated</span></div>
    </div>
  </div>
</section>
<div class="main">
  <div>
    <div class="feed-hdr">
      <h2 class="feed-title">Latest updates</h2>
      <span class="feed-count">{len(items)} item{'s' if len(items)!=1 else ''}</span>
    </div>
    {cards}
  </div>
  <aside>
    <div class="sidebar-card">
      <div class="sidebar-title">Run history</div>
      {hist_rows}
    </div>
    {"<div class='sidebar-card'><div class='sidebar-title'>Agent note</div>" + note_block + "</div>" if note else ""}
    <div class="sidebar-card">
      <div class="sidebar-title">About</div>
      <p style="font-size:13px;color:#666;line-height:1.6">Automated by Claude AI with live web search. Monitors <strong>europeanpaymentscouncil.eu</strong> for ISO 20022 updates. Runs weekdays at 07:00 UTC via GitHub Actions.</p>
    </div>
  </aside>
</div>
<footer>
  <div class="ftr">
    <span class="ftr-l">EPC ISO 20022 Daily Intelligence Briefing</span>
    <span class="ftr-r">Powered by <span>Claude AI</span></span>
  </div>
</footer>
</body>
</html>"""


def load_history() -> list:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            pass
    return []


def save_history(history: list, result: dict) -> list:
    entry = {
        "date":  datetime.now().strftime("%d %b %Y %H:%M"),
        "topic": result.get("topic", ""),
        "items": result.get("items", []),
    }
    history.insert(0, entry)
    history = history[:60]
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2))
    return history


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic",  default=DEFAULT_TOPIC)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    print(f"[{datetime.now().isoformat()}] Running EPC ISO 20022 agent...")
    result  = run_agent(args.topic)
    history = load_history()
    history = save_history(history, result)
    html    = render_html(result, history)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Done: {len(result.get('items',[]))} items saved to {out}")


if __name__ == "__main__":
    main()
