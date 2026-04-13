#!/usr/bin/env python3
"""
EPC ISO 20022 Weekly Briefing Agent — Zalaris Branded
Runs every Monday at 09:00 UTC via GitHub Actions.
Writes docs/index.html served by GitHub Pages.
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
payment standard developments globally, with focus on the European Payments Council (EPC).

Search europeanpaymentscouncil.eu and authoritative financial/regulatory sources for
the most important developments this week related to: "{topic}".

Your task has TWO passes:
PASS 1 — Find the 3-5 most important ISO 20022 / EPC developments from the past 14 days.
PASS 2 — For EACH development, do a separate search to find its exact article URL.

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
      "source_url": "Full https:// URL. Use specific article page, not homepage. If not found use https://www.europeanpaymentscouncil.eu/news-insights/news"
    }}
  ],
  "nothing_new": false,
  "agent_note": "brief note on sources used"
}}

Rules:
- 3-5 bullets maximum, quality over quantity
- Each bullet must be a DISTINCT development
- importance=High: imminent deadline or major regulatory change
- importance=Medium: published update or consultation opened
- importance=Watch: upcoming item to monitor
- Every bullet MUST have a non-empty source_url"""

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        system=system,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{
            "role": "user",
            "content": "Search for ISO 20022 and EPC news from the past 14 days. For each item, search again to find its exact URL. Return JSON only."
        }],
    )

    raw = " ".join(b.text for b in response.content if b.type == "text")
    clean = re.sub(r"```json|```", "", raw).strip()
    s, e = clean.find("{"), clean.rfind("}")
    if s == -1 or e == -1:
        raise ValueError(f"No JSON in response: {raw[:300]}")

    result = json.loads(clean[s:e+1])

    # Guarantee every bullet has a URL
    fallbacks = {
        "epc":   "https://www.europeanpaymentscouncil.eu/news-insights/news",
        "swift": "https://www.swift.com/news-events/news",
        "ecb":   "https://www.ecb.europa.eu/press/pr/html/index.en.html",
        "bis":   "https://www.bis.org/list/speeches/index.htm",
    }
    default_url = "https://www.europeanpaymentscouncil.eu/news-insights/news"

    for b in result.get("bullets", []):
        url = (b.get("source_url") or "").strip()
        if not url:
            label = (b.get("source_label") or "").lower()
            b["source_url"] = next((v for k, v in fallbacks.items() if k in label), default_url)

    return result


def importance_cfg(imp: str):
    imp = (imp or "").strip().lower()
    if imp == "high":
        return ("#FDECEA", "#C0392B", "High")
    if imp == "watch":
        return ("#FFF8E7", "#EEA900", "Watch")
    return ("#E8F4FD", "#004F9E", "Medium")


def tag_cfg(tag: str):
    t = (tag or "").lower()
    if "rulebook"  in t: return ("#E8F5EE", "#1A7A4A")
    if "consult"   in t: return ("#FFF8E7", "#B07800")
    if "migrat"    in t: return ("#E8F4FD", "#004F9E")
    if "tech"      in t: return ("#F0EBF8", "#5A3E8A")
    if "event"     in t: return ("#FFF0EB", "#E9580C")
    return ("#F0F2F5", "#555E6E")


def render_html(result: dict, history: list) -> str:
    now     = datetime.now()
    bullets = result.get("bullets", [])
    summary = result.get("executive_summary", "")
    week    = result.get("week", f"Week of {now.strftime('%d %b %Y')}")
    note    = result.get("agent_note", "")
    nothing = result.get("nothing_new", False)
    runs    = len(history)

    # Bullet cards
    bullet_html = ""
    if nothing or not bullets:
        bullet_html = '<div class="empty-state">No significant new developments this week. Check back next Monday.</div>'
    else:
        for i, b in enumerate(bullets):
            bg, color, label = importance_cfg(b.get("importance", "Medium"))
            tbg, tcolor      = tag_cfg(b.get("tag", ""))
            delay            = i * 0.08
            url              = (b.get("source_url") or default_url).strip()
            src_lbl          = (b.get("source_label") or "Read more").strip()

            bullet_html += f"""
      <div class="card" style="animation-delay:{delay:.2f}s">
        <div class="card-top">
          <div class="card-tags">
            <span class="pill" style="background:{bg};color:{color}">{label}</span>
            <span class="pill" style="background:{tbg};color:{tcolor}">{b.get('tag','News')}</span>
          </div>
          <span class="card-num">#{i+1}</span>
        </div>
        <div class="card-headline">{b.get('headline','')}</div>
        <div class="card-detail">{b.get('detail','')}</div>
        <div class="card-source">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M5 2H2a1 1 0 00-1 1v7a1 1 0 001 1h7a1 1 0 001-1V7M8 1h3m0 0v3m0-3L5 7"
              stroke="#18B2E8" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <a href="{url}" target="_blank" rel="noopener" class="source-link">{src_lbl} &rarr;</a>
        </div>
      </div>"""

    # History
    hist_html = ""
    for h in history[:6]:
        n = len(h.get('bullets', h.get('items', [])))
        hist_html += f'<div class="hist-row"><span>{h.get("date","")}</span><span class="hist-n">{n} items</span></div>'
    if not hist_html:
        hist_html = '<p class="muted">No prior runs</p>'

    default_url = "https://www.europeanpaymentscouncil.eu/news-insights/news"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zalaris · ISO 20022 Weekly Briefing · {now.strftime('%d %b %Y')}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&family=Open+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{{
  --z-deep-navy:#17245F;
  --z-navy:#1B3D82;
  --z-primary-blue:#004F9E;
  --z-sky-blue:#18B2E8;
  --z-orange:#E9580C;
  --z-gold:#EEA900;
  --z-light-gray:#E0E6ED;
  --z-body-text:#333333;
  --z-off-white:#F5F7FA;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Open Sans',sans-serif;background:var(--z-off-white);color:var(--z-body-text);min-height:100vh}}
/* ── Header ── */
.site-header{{background:var(--z-deep-navy);padding:0 2rem}}
.accent-bar{{height:4px;background:linear-gradient(90deg,var(--z-primary-blue),var(--z-sky-blue))}}
.hdr{{max-width:1040px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;height:60px}}
.logo{{display:flex;align-items:center;gap:12px}}
.logo-mark{{width:32px;height:32px;background:var(--z-sky-blue);border-radius:50%;display:flex;align-items:center;justify-content:center}}
.logo-mark svg{{width:18px;height:18px}}
.logo-name{{font-family:'Poppins',sans-serif;font-size:15px;font-weight:700;color:#fff;letter-spacing:.01em}}
.logo-name span{{color:var(--z-sky-blue)}}
.hdr-date{{font-size:11px;color:rgba(255,255,255,.4);font-family:'Open Sans',sans-serif}}
/* ── Hero ── */
.hero{{background:var(--z-deep-navy);padding:3rem 2rem 2.5rem;position:relative;overflow:hidden}}
.hero::after{{content:'';position:absolute;right:-80px;top:-80px;width:360px;height:360px;border-radius:50%;background:var(--z-navy);opacity:.4}}
.hero-inner{{max-width:1040px;margin:0 auto;position:relative;z-index:1}}
.hero-eyebrow{{font-family:'Poppins',sans-serif;font-size:10px;font-weight:600;letter-spacing:.14em;color:var(--z-sky-blue);text-transform:uppercase;margin-bottom:10px}}
.hero h1{{font-family:'Poppins',sans-serif;font-size:clamp(26px,4vw,44px);font-weight:800;color:#fff;line-height:1.15;margin-bottom:6px}}
.hero h1 span{{color:var(--z-sky-blue)}}
.week-label{{font-size:12px;color:rgba(255,255,255,.4);margin-bottom:1.5rem;font-family:'Open Sans',sans-serif}}
.summary-box{{background:rgba(255,255,255,.07);border-left:3px solid var(--z-orange);padding:14px 18px;font-size:14px;color:rgba(255,255,255,.85);line-height:1.65;max-width:620px;border-radius:0 4px 4px 0}}
.stats{{display:flex;gap:2.5rem;margin-top:1.75rem;flex-wrap:wrap}}
.stat-n{{font-family:'Poppins',sans-serif;font-size:28px;font-weight:800;color:var(--z-sky-blue);display:block;line-height:1}}
.stat-l{{font-size:11px;color:rgba(255,255,255,.35);margin-top:2px;display:block}}
/* ── Main layout ── */
.main{{max-width:1040px;margin:0 auto;padding:2rem;display:grid;grid-template-columns:1fr 260px;gap:2rem;align-items:start}}
@media(max-width:720px){{.main{{grid-template-columns:1fr}}}}
/* ── Section header ── */
.section-hdr{{display:flex;align-items:center;gap:10px;margin-bottom:1.25rem}}
.section-hdr h2{{font-family:'Poppins',sans-serif;font-size:18px;font-weight:700;color:var(--z-deep-navy)}}
.section-hdr-line{{flex:1;height:1px;background:var(--z-light-gray)}}
/* ── Cards ── */
.card{{background:#fff;border:1px solid var(--z-light-gray);border-radius:8px;padding:1.25rem 1.5rem;margin-bottom:.875rem;border-top:3px solid var(--z-primary-blue);animation:fadeUp .35s ease both;transition:box-shadow .15s}}
.card:hover{{box-shadow:0 4px 20px rgba(23,36,95,.08)}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
.card-top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}}
.card-tags{{display:flex;gap:6px;flex-wrap:wrap}}
.pill{{font-family:'Poppins',sans-serif;font-size:10px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;padding:3px 9px;border-radius:3px}}
.card-num{{font-family:'Poppins',sans-serif;font-size:22px;font-weight:800;color:var(--z-light-gray)}}
.card-headline{{font-family:'Poppins',sans-serif;font-size:15px;font-weight:700;color:var(--z-deep-navy);line-height:1.35;margin-bottom:8px}}
.card-detail{{font-size:13px;color:#555;line-height:1.7;margin-bottom:12px}}
.card-source{{display:flex;align-items:center;gap:7px;padding-top:10px;border-top:1px solid var(--z-light-gray)}}
.source-link{{font-family:'Poppins',sans-serif;font-size:12px;font-weight:600;color:var(--z-primary-blue);text-decoration:none}}
.source-link:hover{{color:var(--z-sky-blue);text-decoration:underline}}
.empty-state{{background:#fff;border:1px solid var(--z-light-gray);border-radius:8px;padding:2.5rem;text-align:center;color:#888;font-size:14px}}
/* ── Sidebar ── */
.sidebar-card{{background:#fff;border:1px solid var(--z-light-gray);border-radius:8px;padding:1.25rem;margin-bottom:1rem}}
.sidebar-card h3{{font-family:'Poppins',sans-serif;font-size:13px;font-weight:700;color:var(--z-deep-navy);margin-bottom:.875rem;padding-bottom:8px;border-bottom:1px solid var(--z-light-gray)}}
.hist-row{{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--z-light-gray);font-size:12px;font-family:'Open Sans',sans-serif}}
.hist-row:last-child{{border-bottom:none}}
.hist-n{{color:#aaa}}
.legend-row{{display:flex;align-items:center;gap:8px;margin-bottom:7px;font-size:12px}}
.muted{{font-size:13px;color:#aaa;padding:4px 0}}
/* ── Footer ── */
footer{{background:var(--z-deep-navy);padding:1.25rem 2rem;margin-top:3rem}}
.ftr{{max-width:1040px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem}}
.ftr-l{{font-size:11px;color:rgba(255,255,255,.25);font-family:'Open Sans',sans-serif}}
.ftr-r{{font-size:11px;color:rgba(255,255,255,.25);font-family:'Open Sans',sans-serif}}
.ftr-r span{{color:var(--z-sky-blue)}}
</style>
</head>
<body>

<div class="accent-bar"></div>
<header class="site-header">
  <div class="hdr">
    <div class="logo">
      <div class="logo-mark">
        <svg viewBox="0 0 18 18" fill="none">
          <path d="M2 14L9 4l7 10H2z" fill="#fff" opacity=".9"/>
        </svg>
      </div>
      <span class="logo-name">Zalaris <span>·</span> ISO 20022 Monitor</span>
    </div>
    <span class="hdr-date">{now.strftime('%A, %d %B %Y')}</span>
  </div>
</header>

<section class="hero">
  <div class="hero-inner">
    <p class="hero-eyebrow">European Payments Council · Weekly Intelligence</p>
    <h1>ISO 20022<br><span>Weekly Briefing</span></h1>
    <p class="week-label">{week}</p>
    {f'<div class="summary-box">{summary}</div>' if summary else ''}
    <div class="stats">
      <div><span class="stat-n">{len(bullets)}</span><span class="stat-l">developments</span></div>
      <div><span class="stat-n">{runs}</span><span class="stat-l">weeks tracked</span></div>
      <div><span class="stat-n">{now.strftime("%d %b")}</span><span class="stat-l">last updated</span></div>
    </div>
  </div>
</section>

<div class="main">
  <div>
    <div class="section-hdr">
      <h2>Key developments this week</h2>
      <div class="section-hdr-line"></div>
    </div>
    {bullet_html}
    {f'<p style="font-size:11px;color:#aaa;margin-top:8px;font-style:italic">{note}</p>' if note else ''}
  </div>

  <aside>
    <div class="sidebar-card">
      <h3>Priority legend</h3>
      <div class="legend-row"><span class="pill" style="background:#FDECEA;color:#C0392B">High</span> Act now / imminent</div>
      <div class="legend-row"><span class="pill" style="background:#E8F4FD;color:#004F9E">Medium</span> New publication</div>
      <div class="legend-row"><span class="pill" style="background:#FFF8E7;color:#EEA900">Watch</span> Upcoming item</div>
    </div>
    <div class="sidebar-card">
      <h3>Run history</h3>
      {hist_html}
    </div>
    <div class="sidebar-card">
      <h3>About</h3>
      <p style="font-size:12px;color:#666;line-height:1.65">Claude AI agent with live web search. Monitors ISO 20022 developments across EPC, SWIFT, ECB and national central banks. Runs every Monday at 10:00 CET.</p>
    </div>
  </aside>
</div>

<footer>
  <div class="ftr">
    <span class="ftr-l">Zalaris · ISO 20022 Weekly Intelligence · EPC Monitor</span>
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
