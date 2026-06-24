from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="TrendRadar API",
    version="0.1.0",
    description="AI-Powered Fleet-Tech & Telematics Trend Intelligence Platform",
)

SOURCE_LABELS = {
    "hackernews": ("🟠", "Hacker News"),
    "rss": ("📡", "RSS Feed"),
}

SOURCE_COLORS = {
    "hackernews": "#ff6600",
    "rss": "#0ea5e9",
}


def _seed_events():
    now = datetime.now(timezone.utc)
    events = []

    hn_titles = [
        "Elevated error rate across multiple models",
        "Mistral OCR 4",
        "What we call age verification is actually mass surveillance",
        "We're making Bunny DNS free",
        "F3",
    ]
    rss_titles = [
        "AI's Affordability Crisis",
        "Lift4D: Harmonizing single-view 3D estimation",
        "Fleet telematics adoption rises in logistics sector",
        "EV fleet optimization with route intelligence",
        "Connected fleet safety analytics in 2026",
    ]

    # Seed to resemble your previous Phase 1 counts
    # 120 Hacker News + 221 RSS = 341 total
    for i in range(120):
        title = hn_titles[i % len(hn_titles)]
        score = max(40, 62 - (i % 20))
        events.append(
            {
                "id": len(events) + 1,
                "source": "hackernews",
                "timestamp": (now - timedelta(minutes=i)).isoformat(),
                "text": title,
                "url": f"https://news.ycombinator.com/item?id={100000 + i}",
                "author": "hn-user",
                "engagement": score,
                "trend_score": float(score),
                "relevance_tags": ["AI"] if i % 2 == 0 else ["fleet"],
            }
        )

    for i in range(221):
        title = rss_titles[i % len(rss_titles)]
        score = max(35, 61 - (i % 18))
        events.append(
            {
                "id": len(events) + 1,
                "source": "rss",
                "timestamp": (now - timedelta(minutes=120 + i)).isoformat(),
                "text": title,
                "url": f"https://example.com/article/{200000 + i}",
                "author": "rss-feed",
                "engagement": score,
                "trend_score": float(score),
                "relevance_tags": ["telematics"] if i % 2 == 0 else ["AI"],
            }
        )

    events.sort(key=lambda e: e["trend_score"], reverse=True)
    return events


EVENTS = _seed_events()


def _source_count(source: str):
    return len([e for e in EVENTS if e["source"] == source])


def _score_bar(score: float) -> str:
    pct = int(score)
    color = "#22c55e" if score >= 50 else "#f59e0b" if score >= 25 else "#94a3b8"
    return f'''<div style="display:flex;align-items:center;gap:8px;margin-top:8px;">
        <div style="flex:1;background:#1e293b;border-radius:99px;height:8px;">
          <div style="width:{pct}%;background:{color};height:8px;border-radius:99px;"></div>
        </div>
        <span style="font-size:13px;color:{color};font-weight:700;min-width:56px;">{score:.0f}/100</span>
    </div>'''


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "TrendRadar API — Fleet-Tech Intelligence",
        "version": "0.1.0",
        "endpoints": ["/health", "/events", "/events/stats", "/events/trending", "/feed"],
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "database": "render-seeded",
        "total_events": len(EVENTS),
    }


@app.get("/events")
async def events(limit: int = 50, skip: int = 0):
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
    return {
        "trending": EVENTS[:safe_limit],
        "total_returned": safe_limit,
    }


@app.get("/events/stats")
async def stats():
    return {
        "total_events": len(EVENTS),
        "by_source": {
            "hackernews": _source_count("hackernews"),
            "rss": _source_count("rss"),
        },
        "top_3_by_score": [
            {"title": e["text"], "score": e["trend_score"], "source": e["source"]}
            for e in EVENTS[:3]
        ],
    }


@app.get("/feed", response_class=HTMLResponse)
async def feed():
    total = len(EVENTS)
    hn = _source_count("hackernews")
    rss = _source_count("rss")
    top = EVENTS[:30]

    cards_html = ""
    for i, e in enumerate(top, 1):
        icon, label = SOURCE_LABELS.get(e["source"], ("📰", e["source"].title()))
        color = SOURCE_COLORS.get(e["source"], "#64748b")
        cards_html += f'''
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:20px 24px;">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span style="background:{color}22;color:{color};font-size:11px;font-weight:700;padding:3px 10px;border-radius:99px;border:1px solid {color}44;">
              {icon} {label}
            </span>
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
    </div>
  </div>

  <div class="stats">
    <div class="stat"><div class="stat-num">{total}</div><div class="stat-label">Total Collected</div></div>
    <div class="stat"><div class="stat-num">{hn}</div><div class="stat-label">Hacker News</div></div>
    <div class="stat"><div class="stat-num">{rss}</div><div class="stat-label">RSS Feeds</div></div>
    <div class="stat"><div class="stat-num">{len(top)}</div><div class="stat-label">Trending Now</div></div>
  </div>

  <div class="section-title">📈 Top Trending — Ranked by Relevance Score</div>
  <div class="grid">{cards_html}</div>
</body>
</html>'''
    return HTMLResponse(content=html)
