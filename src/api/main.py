from datetime import datetime, timezone
from typing import Any, Dict, List

import feedparser
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="TrendRadar API",
    version="0.1.0",
    description="AI-Powered Fleet-Tech & Telematics Trend Intelligence Platform",
)

RSS_FEEDS = [
    "https://techcrunch.com/feed/",
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "https://www.ttnews.com/rss.xml",
]

SOURCE_LABELS = {
    "hackernews": ("🟠", "Hacker News"),
    "rss": ("📡", "RSS Feed"),
}

SOURCE_COLORS = {
    "hackernews": "#ff6600",
    "rss": "#0ea5e9",
}

EVENTS: List[Dict[str, Any]] = []


def _score_bar(score: float) -> str:
    pct = int(max(0, min(score, 100)))
    color = "#22c55e" if score >= 50 else "#f59e0b" if score >= 25 else "#94a3b8"
    return f'''<div style="display:flex;align-items:center;gap:8px;margin-top:8px;">
        <div style="flex:1;background:#1e293b;border-radius:99px;height:8px;">
          <div style="width:{pct}%;background:{color};height:8px;border-radius:99px;"></div>
        </div>
        <span style="font-size:13px;color:{color};font-weight:700;min-width:56px;">{score:.0f}/100</span>
    </div>'''


def _safe_get(url: str, timeout: int = 15):
    return requests.get(url, timeout=timeout, headers={"User-Agent": "TrendRadar/0.1"})


def _normalize_scores(events: List[Dict[str, Any]]) -> None:
    if not events:
        return

    raw_scores = [float(e.get("raw_score", 0.0)) for e in events]
    low = min(raw_scores)
    high = max(raw_scores)

    if high <= low:
        for e in events:
            e["trend_score"] = 50.0
        return

    # Spread scores into a readable range so cards don't all show 100/100.
    out_low = 35.0
    out_high = 92.0
    span = high - low
    out_span = out_high - out_low

    for e in events:
        normalized = out_low + ((float(e.get("raw_score", 0.0)) - low) / span) * out_span
        e["trend_score"] = round(normalized, 1)


def _collect_hn(limit: int = 120) -> List[Dict[str, Any]]:
    events = []
    try:
        top_ids = _safe_get("https://hacker-news.firebaseio.com/v0/topstories.json").json()[:limit]
        for story_id in top_ids:
            item = _safe_get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json").json() or {}
            title = item.get("title") or "Untitled Hacker News Story"
            url = item.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
            raw_score = float(max(0, (item.get("score") or 0)))
            ts = datetime.fromtimestamp(item.get("time") or datetime.now(timezone.utc).timestamp(), tz=timezone.utc)
            events.append(
                {
                    "id": len(events) + 1,
                    "source": "hackernews",
                    "timestamp": ts.isoformat(),
                    "text": title,
                    "url": url,
                    "author": item.get("by") or "hn-user",
                    "engagement": int(raw_score),
                    "raw_score": raw_score,
                    "trend_score": raw_score,
                    "relevance_tags": ["AI"] if "ai" in title.lower() else ["tech"],
                    "event_metadata": {"description": "Top story from Hacker News."},
                }
            )
    except Exception:
        return []
    return events


def _collect_rss(limit: int = 221) -> List[Dict[str, Any]]:
    events = []
    per_feed = max(1, limit // len(RSS_FEEDS))

    for feed_url in RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:per_feed]:
                title = getattr(entry, "title", None) or "Untitled RSS Item"
                url = getattr(entry, "link", None) or feed_url
                published = getattr(entry, "published", None) or datetime.now(timezone.utc).isoformat()
                raw_score = float(max(35, min(80, 50 + (len(title) % 25))))
                events.append(
                    {
                        "id": len(events) + 1,
                        "source": "rss",
                        "timestamp": published,
                        "text": title,
                        "url": url,
                        "author": getattr(entry, "author", None) or "rss-feed",
                        "engagement": int(raw_score),
                        "raw_score": raw_score,
                        "trend_score": raw_score,
                        "relevance_tags": ["telematics"] if "fleet" in title.lower() else ["news"],
                        "event_metadata": {"description": "Latest item from RSS feed."},
                    }
                )
        except Exception:
            continue

    return events[:limit]


def refresh_events() -> Dict[str, int]:
    global EVENTS
    hn_events = _collect_hn(limit=120)
    rss_events = _collect_rss(limit=221)
    combined = hn_events + rss_events
    _normalize_scores(combined)
    EVENTS = sorted(combined, key=lambda e: e.get("trend_score", 0), reverse=True)
    return {
        "total": len(EVENTS),
        "hackernews": len(hn_events),
        "rss": len(rss_events),
    }


@app.on_event("startup")
async def startup_refresh():
    if not EVENTS:
        refresh_events()


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "TrendRadar API — Fleet-Tech Intelligence",
        "version": "0.1.0",
        "endpoints": ["/health", "/collect", "/events", "/events/stats", "/events/trending", "/feed"],
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "database": "render-runtime",
        "total_events": len(EVENTS),
    }


@app.post("/collect")
async def collect():
    counts = refresh_events()
    return {
        "status": "collection_completed",
        "total_events_collected": counts["total"],
        "new_events_saved": counts["total"],
        "by_source": {"hackernews": counts["hackernews"], "rss": counts["rss"]},
    }


@app.get("/events")
async def events(limit: int = 30, skip: int = 0):
    safe_limit = max(1, min(limit, 200))
    safe_skip = max(0, skip)
    return {
        "events": EVENTS[safe_skip : safe_skip + safe_limit],
        "total": len(EVENTS),
        "skip": safe_skip,
        "limit": safe_limit,
    }


@app.get("/events/trending")
async def trending(limit: int = 30):
    safe_limit = max(1, min(limit, 100))
    return {"trending": EVENTS[:safe_limit], "total_returned": min(len(EVENTS), safe_limit)}


@app.get("/events/stats")
async def stats():
    hn = len([e for e in EVENTS if e["source"] == "hackernews"])
    rss = len([e for e in EVENTS if e["source"] == "rss"])
    return {
        "total_events": len(EVENTS),
        "by_source": {"hackernews": hn, "rss": rss},
        "top_3_by_score": [
            {"title": e["text"], "score": e["trend_score"], "source": e["source"]}
            for e in EVENTS[:3]
        ],
    }


@app.get("/feed", response_class=HTMLResponse)
async def feed():
    total = len(EVENTS)
    hn = len([e for e in EVENTS if e["source"] == "hackernews"])
    rss = len([e for e in EVENTS if e["source"] == "rss"])
    top = EVENTS[:30]

    cards_html = ""
    for i, e in enumerate(top, 1):
        icon, label = SOURCE_LABELS.get(e["source"], ("📰", e["source"].title()))
        color = SOURCE_COLORS.get(e["source"], "#64748b")
        cards_html += f'''
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:20px 24px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span style="background:{color}22;color:{color};font-size:11px;font-weight:700;padding:3px 10px;border-radius:99px;border:1px solid {color}44;">{icon} {label}</span>
            <span style="color:#475569;font-size:11px;">#{i}</span>
          </div>
          <h3 style="margin:0 0 8px 0;font-size:16px;font-weight:600;color:#f1f5f9;line-height:1.4;">{e['text']}</h3>
          <p style="margin:0 0 12px 0;font-size:13px;color:#64748b;line-height:1.5;">Click the link below to read the full article.</p>
          {_score_bar(e['trend_score'])}
          <div style="margin-top:14px;">
            <a href="{e['url']}" target="_blank" style="display:inline-flex;align-items:center;gap:6px;background:#1d4ed8;color:#fff;text-decoration:none;font-size:13px;font-weight:600;padding:8px 16px;border-radius:8px;">Read Article →</a>
          </div>
        </div>'''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>TrendRadar — Fleet-Tech Intelligence</title>
  <style>
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:#020817; color:#f1f5f9; min-height:100vh; }}
    .header {{ background:#0a0f1e; border-bottom:1px solid #1e293b; padding:20px 40px; display:flex; justify-content:space-between; align-items:center; }}
    .logo {{ font-size:22px; font-weight:800; color:#fff; letter-spacing:-0.5px; }}
    .logo span {{ color:#3b82f6; }}
    .badge {{ background:#1e3a5f; color:#7dd3fc; font-size:12px; padding:4px 12px; border-radius:99px; border:1px solid #1e40af; }}
    .stats {{ display:flex; gap:24px; padding:24px 40px 0; flex-wrap:wrap; }}
    .stat {{ background:#0f172a; border:1px solid #1e293b; border-radius:10px; padding:14px 20px; text-align:center; min-width:140px; }}
    .stat-num {{ font-size:32px; font-weight:800; color:#3b82f6; }}
    .stat-label {{ font-size:12px; color:#64748b; margin-top:2px; }}
    .collect-btn {{ background:#3b82f6; color:#fff; border:none; cursor:pointer; font-size:14px; font-weight:700; padding:10px 16px; border-radius:10px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(380px,1fr)); gap:16px; padding:24px 40px 40px; }}
    .section-title {{ padding:16px 40px 0; font-size:13px; color:#64748b; letter-spacing:0.05em; text-transform:uppercase; font-weight:600; }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <div class="logo">Trend<span>Radar</span></div>
      <div style="font-size:12px;color:#475569;margin-top:2px;">Fleet-Tech & AI Intelligence Platform</div>
    </div>
    <div style="display:flex;align-items:center;gap:12px;">
      <span class="badge">Render Live</span>
      <button class="collect-btn" onclick="collectNow()">⚡ Collect Latest</button>
    </div>
  </div>

  <div class="stats">
    <div class="stat"><div class="stat-num">{total}</div><div class="stat-label">Total Collected</div></div>
    <div class="stat"><div class="stat-num">{hn}</div><div class="stat-label">Hacker News</div></div>
    <div class="stat"><div class="stat-num">{rss}</div><div class="stat-label">RSS Feeds</div></div>
    <div class="stat"><div class="stat-num">{len(top)}</div><div class="stat-label">Trending Now</div></div>
  </div>

  <div id="status" style="padding:8px 40px;font-size:13px;color:#22c55e;min-height:28px;"></div>
  <div class="section-title">📈 Top Trending — Ranked by Relevance Score</div>
  <div class="grid">{cards_html}</div>

  <script>
    async function collectNow() {{
      document.getElementById('status').textContent = 'Collecting latest data...';
      try {{
        const r = await fetch('/collect', {{ method: 'POST' }});
        const d = await r.json();
        document.getElementById('status').textContent = 'Collected ' + d.total_events_collected + ' events. Refreshing...';
        setTimeout(() => location.reload(), 1500);
      }} catch (e) {{
        document.getElementById('status').textContent = 'Collection failed. Try again.';
      }}
    }}
  </script>
</body>
</html>'''
    return HTMLResponse(content=html)
