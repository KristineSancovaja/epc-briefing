#!/usr/bin/env python3
"""
EPC ISO 20022 Weekly Briefing Agent
Runs every Monday at 09:00 UTC via GitHub Actions.
Writes docs/index.html served by GitHub Pages.

Two-pass approach:
  Pass 1 - find key developments
  Pass 2 - find the exact URL for each development
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

    system = f"""You are a financial regulation intelligence agent monitoring ISO 20022
payment standard developments, with focus on the European Payments Council (EPC).

Your task has TWO passes:

PASS 1 — Search for the 3-5 most important ISO 20022 / EPC developments from the past 14 days.

PASS 2 — For EACH development found in Pass 1, perform a SEPARATE web search to find the
exact URL of the article, press release, or publication page. Search for the title + site name.
Use the most specific URL you can find — not a homepage.

Return ONLY a JSON object — no markdown, no preamble:
{{
  "topic": "ISO 20022 — Weekly Intelligence Briefing",
  "week": "Week of [Monday date]",
  "executive_summary": "One sentence: the single most important development this week.",
  "bullets": [
    {{
      "headline": "Short punchy headline, max 10 words",
      "detail": "One sentence explaining what happened and why it matters.",
      "tag": "one of: Rulebook | Consultation | Regulation | Technical | Migration | Event",
      "importance": "one of: High | Medium | Watch",
      "source_label": "Readable source name e.g. EPC, SWIFT, ECB, BIS, Reuters",
      "source_url": "REQUIRED — full https:// URL found in Pass 2. Never use a homepage. Use the deepest page URL available."
    }}
  ],
  "nothing_new": false,
  "agent_note": "note on sources"
}}

IMPORTANT: Every bullet MUST have a source_url. If you cannot find the exact article,
use the most relevant section page such as:
- https://www.europeanpaymentscouncil.eu/news-insights/news
- https://www.swift.com/news-events/news
- https://www.ecb.europa.eu/press/pr/html/index.en.html
Never leave source_url as an empty string."""

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        system=system,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{
            "role": "user",
            "content": (
                "Pass 1: Search for the most important ISO 20022 and EPC developments "
                "from the past 14 days. "
                "Pass 2: For each development, search again to find its exact article URL. "
                "Include a real https:// URL for every single bullet. "
                "Return JSON only."
            )
        }],
    )

    raw = " ".join(b.text for b in response.content if b.type == "text")
    clean = re.sub(r"```json|```", "", raw).strip()
    s, e = clean.find("{"), clean.rfind("}")
    if s == -1 or e == -1:
        raise ValueError(f"No JSON in response: {raw[:300]}")

    result = json.loads(clean[s:e+1])

    # Fallback: if any bullet still has empty source_url, assign a sensible default
    fallbacks = {
        "epc":        "https://www.europeanpaymentscouncil.eu/news-insights/news",
        "swift":      "https://www.swift.com/news-events/news",
        "ecb":        "https://www.ecb.europa.eu/press/pr/html/index.en.html",
        "bis":        "https://www.bis.org/list/speeches/index.htm",
    }
    default_url = "https://www.europeanpaymentscouncil.eu/news-insights/news"

    for b in result.get("bullets", []):
        url = (b.get("source_url") or "").strip()
        if not url or url == "":
            label = (b.get("source_label") or "").lower()
            b["source_url"] = next(
                (v for k, v in fallbacks.items() if k in label),
                default_url
            )

    return result


def importance_style(imp: str):
    imp = (imp or "").strip().lower()
    if imp == "high":
        return ("background:#FDECEA;color:#C0392B", "High", "#C0392B")
    if imp == "watch":
        return ("background:#FEF5E7;color:#8B5E14", "Watch", "#8B5E14")
    return ("background:#EBF7F0;color:#2D7A4F", "Medium", "#2D7A4F")


def tag_style(tag: str):
    t = (tag or "").lower()
    if "rulebook"  in t: return "background:#EBF7F0;color:#2D7A4F"
    if "consult"   in t: return "background:#FEF5E7;color:#8B5E14"
    if "migrat"    in t: return "background:#EBF4FB;color:#1B6CA8"
    if "tech"      in t: return "background:#F0EBF8;color:#5A3E8A"
    if "event"     in t: return "background:#FDECEA;color:#C0392B"
    return "background:#F0EFEB;color:#5A5A54"


def render_html(result: dict, history: list) -> str:
    now      = datetime.now()
    bullets  = result.get("bullets", [])
    summary  = result.get("executive_summary", "")
    week     = result.get("week", f"Week of {now.strftime('%d %b %Y')}")
    note     = result.get("agent_note", "")
    nothing  = result.get("nothing_new", False)
    runs     = len(history)

    bullet_html = ""
    if nothing or not bullets:
        bullet_html = """
        <div style="padding:2rem;text-align:center;color:#888;font-size:14px;background:#fff;border-radius:6px;border:1px solid rgba(11,31,58,.1)">
          No significant new developments this week. Check back next Monday.
        </div>"""
    else:
        for i, b in enumerate(bullets):
            imp_style, imp_label, imp_color = importance_style(b.get("importance", "Medium"))
            t_style    = tag_style(b.get("tag", ""))
            delay      = i * 0.08
            source_url = (b.get("source_url") or "").strip()
            source_lbl = (b.get("source_label") or "Read more").strip()

            source_block = f"""
          <div class="bullet-source">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style="flex-shrink:0;margin-top:1px">
              <path d="M5 2H2a1 1 0 00-1 1v7a1 1 0 001 1h7a1 1 0 001-1V7M8 1h3m0 0v3m0-3L5 7" stroke="#1B6CA8" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <a href="{source_url}" target="_blank" rel="noopener" class="source-link">{source_lbl} &rarr;</a>
          </div>"""

            bullet_html += f"""
        <div class="bullet-card" style="animation-delay:{delay:.2f}s">
          <div class="bullet-top">
            <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
              <span class="pill" style="{imp_style}">{imp_label}</span>
              <span class="pill" style="{t_style}">{b.get('tag','News')}</span>
            </div>
            <span class="bullet-num" style="color:{imp_color}">#{i+1}</span>
          </div>
          <div class="bullet-headline">{b.get('headline','')}</div>
          <div class="bullet-detail">{b.get('detail','')}</div>
          {source_block}
        </div>"""

    hist_html = ""
    for h in history[:6]:
        hist_html += f"""
        <div class="hist-row">
          <span class="hist-date">{h.get('date','')}</span>
          <span class="hist-n">{len(h.get('bullets', h.get('items', [])))} items</span>
        </div>"""
    if not hist_html:
        hist_html = '<p style="font-size:13px;color:#aaa;padding:4px 0">No prior runs</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ISO 20022 Weekly Briefing · {now.strftime('%d %b %Y')}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=Instrument+Sans:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Instrument Sans',sans-serif;background:#F4F2EE;color:#1A1A1A;min-height:100vh}}
header{{background:#0B1F3A;border-bottom:2px solid #E8A020;padding:0 2rem}}
.hdr{{max-width:960px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;height:52px}}
.badge{{background:#E8A020;color:#0B1F3A;font-family:'DM Mono',monospace;font-size:10px;font-weight:500;padding:3px 8px;border-radius:3px;letter-spacing:.05em}}
.hdr-name{{color:#fff;font-size:13px;font-weight:500;margin-left:10px}}
.hdr-date{{font-family:'DM Mono',monospace;font-size:10px;color:rgba(255,255,255,.35)}}
.hero{{background:#142D52;padding:2.5rem 2rem 2rem}}
.hero-inner{{max-width:960px;margin:0 auto}}
.eyebrow{{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.12em;color:#F5C05A;text-transform:uppercase;margin-bottom:8px}}
h1{{font-family:'DM Serif Display',serif;font-size:clamp(24px,3.5vw,40px);color:#fff;line-height:1.2;margin-bottom:6px}}
h1 em{{color:#F5C05A;font-style:italic}}
.week-label{{font-family:'DM Mono',monospace;font-size:11px;color:rgba(255,255,255,.4);margin-bottom:1.25rem}}
.summary-box{{background:rgba(255,255,255,.07);border-left:3px solid #E8A020;border-radius:0 4px 4px 0;padding:12px 16px;font-size:14px;color:rgba(255,255,255,.85);line-height:1.6;max-width:640px}}
.stats{{display:flex;gap:2rem;margin-top:1.5rem}}
.stat-n{{font-family:'DM Serif Display',serif;font-size:24px;color:#F5C05A;display:block}}
.stat-l{{font-size:10px;color:rgba(255,255,255,.3);letter-spacing:.05em}}
.main{{max-width:960px;margin:0 auto;padding:2rem;display:grid;grid-template-columns:1fr 240px;gap:2rem;align-items:start}}
@media(max-width:700px){{.main{{grid-template-columns:1fr}}}}
.section-title{{font-family:'DM Serif Display',serif;font-size:18px;color:#0B1F3A;margin-bottom:1rem}}
.bullet-card{{background:#fff;border:1px solid rgba(11,31,58,.1);border-radius:6px;padding:1.25rem;margin-bottom:.75rem;animation:fadeUp .35s ease both}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:translateY(0)}}}}
.bullet-top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}}
.pill{{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.05em;text-transform:uppercase;padding:3px 8px;border-radius:2px}}
.bullet-num{{font-family:'DM Serif Display',serif;font-size:20px;opacity:.3}}
.bullet-headline{{font-family:'DM Serif Display',serif;font-size:16px;color:#0B1F3A;line-height:1.3;margin-bottom:6px}}
.bullet-detail{{font-size:13px;color:#555;line-height:1.6;margin-bottom:10px}}
.bullet-source{{display:flex;align-items:flex-start;gap:6px;padding-top:10px;border-top:1px solid rgba(11,31,58,.07)}}
.source-link{{font-size:12px;color:#1B6CA8;text-decoration:none;font-weight:500}}
.source-link:hover{{text-decoration:underline}}
.sidebar-card{{background:#fff;border:1px solid rgba(11,31,58,.1);border-radius:6px;padding:1.25rem;margin-bottom:1rem}}
.sidebar-title{{font-family:'DM Serif Display',serif;font-size:14px;color:#0B1F3A;margin-bottom:.75rem;padding-bottom:8px;border-bottom:1px solid rgba(11,31,58,.08)}}
.hist-row{{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(11,31,58,.06);font-size:12px}}
.hist-row:last-child{{border-bottom:none}}
.hist-date{{font-family:'DM Mono',monospace;color:#555}}
.hist-n{{font-family:'DM Mono',monospace;color:#aaa}}
.legend-row{{display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:12px;color:#555}}
footer{{background:#0B1F3A;padding:1rem 2rem;margin-top:3rem}}
.ftr{{max-width:960px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem}}
.ftr-l{{font-family:'DM Mono',monospace;font-size:10px;color:rgba(255,255,255,.2)}}
.ftr-r{{font-size:10px;color:rgba(255,255,255,.2)}}
.ftr-r span{{color:#E8A020}}
</style>
</head>
<body>
<header>
  <div class="hdr">
    <div><span class="badge">ISO 20022</span><span class="hdr-name">EPC Weekly Intelligence</span></div>
    <span class="hdr-date">{now.strftime('%A, %d %B %Y')}</span>
  </div>
</header>
<section class="hero">
  <div class="hero-inner">
    <p class="eyebrow">European Payments Council · Weekly Monitor</p>
    <h1>ISO 20022<br><em>Weekly Briefing</em></h1>
    <p class="week-label">{week}</p>
    {f'<div class="summary-box">{summary}</div>' if summary else ''}
    <div class="stats">
      <div><span class="stat-n">{len(bullets)}</span><span class="stat-l">developments</span></div>
      <div><span class="stat-n">{runs}</span><span class="stat-l">weeks tracked</span></div>
    </div>
  </div>
</section>
<div class="main">
  <div>
    <div class="section-title">Key developments this week</div>
    {bullet_html}
    {f'<p style="font-size:11px;color:#aaa;margin-top:8px;font-style:italic">{note}</p>' if note else ''}
  </div>
  <aside>
    <div class="sidebar-card">
      <div class="sidebar-title">Priority legend</div>
      <div class="legend-row"><span class="pill" style="background:#FDECEA;color:#C0392B">High</span> Act now / imminent</div>
      <div class="legend-row"><span class="pill" style="background:#EBF7F0;color:#2D7A4F">Medium</span> New publication</div>
      <div class="legend-row"><span class="pill" style="background:#FEF5E7;color:#8B5E14">Watch</span> Upcoming item</div>
    </div>
    <div class="sidebar-card">
      <div class="sidebar-title">Run history</div>
      {hist_html}
    </div>
    <div class="sidebar-card">
      <div class="sidebar-title">About</div>
      <p style="font-size:12px;color:#666;line-height:1.6">Claude AI agent with live web search. Monitors ISO 20022 developments across EPC, SWIFT, ECB and national central banks. Runs every Monday at 10:00 CET.</p>
    </div>
  </aside>
</div>
<footer>
  <div class="ftr">
    <span class="ftr-l">ISO 20022 Weekly Intelligence · EPC Monitor</span>
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
        "date":    datetime.now().strftime("%d %b %Y"),
        "topic":   result.get("topic", ""),
        "bullets": result.get("bullets", []),
    }
    history.insert(0, entry)
    history = history[:52]
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2))
    return history


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic",  default=DEFAULT_TOPIC)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    print(f"[{datetime.now().isoformat()}] Running ISO 20022 weekly briefing agent...")
    result  = run_agent(args.topic)
    history = load_history()
    history = save_history(history, result)
    html    = render_html(result, history)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Done: {len(result.get('bullets',[]))} bullets · saved to {out}")


if __name__ == "__main__":
    main()
