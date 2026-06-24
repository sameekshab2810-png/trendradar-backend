from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="TrendRadar API",
    version="0.1.0",
    description="AI-Powered Fleet-Tech & Telematics Trend Intelligence Platform",
)

SAMPLE_EVENTS = [
    {
        "id": 1,
        "source": "hackernews",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "text": "Elevated error rate across multiple models",
        "url": "https://status.openai.com/incidents",
        "author": "hn-user",
        "engagement": 62,
        "trend_score": 62.0,
        "relevance_tags": ["AI", "models"],
    },
    {
        "id": 2,
        "source": "rss",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "text": "AI's Affordability Crisis",
        "url": "https://blog.dshr.org/2026/06/ais-affordability-crisis.html",
        "author": "rss-feed",
        "engagement": 61,
        "trend_score": 61.0,
        "relevance_tags": ["AI", "cost"],
    },
]


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "TrendRadar API — Fleet-Tech Intelligence",
        "version": "0.1.0",
        "endpoints": ["/health", "/events", "/events/stats", "/feed"],
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "database": "demo-mode",
        "total_events": len(SAMPLE_EVENTS),
    }


@app.get("/events")
async def events(limit: int = 10):
    data = SAMPLE_EVENTS[: max(1, min(limit, 50))]
    return {"events": data, "total": len(SAMPLE_EVENTS), "limit": limit}


@app.get("/events/stats")
async def stats():
    hn = len([e for e in SAMPLE_EVENTS if e["source"] == "hackernews"])
    rss = len([e for e in SAMPLE_EVENTS if e["source"] == "rss"])
    return {
        "total_events": len(SAMPLE_EVENTS),
        "by_source": {"hackernews": hn, "rss": rss},
        "top_3_by_score": [
            {"title": e["text"], "score": e["trend_score"], "source": e["source"]}
            for e in SAMPLE_EVENTS[:3]
        ],
    }


@app.get("/feed", response_class=HTMLResponse)
async def feed():
    cards = ""
    for i, e in enumerate(SAMPLE_EVENTS, 1):
        cards += f"""
        <div class='card'>
          <div class='meta'>#{i} • {e['source'].title()}</div>
          <h3>{e['text']}</h3>
          <p>Score: {e['trend_score']:.0f}/100</p>
          <a href='{e['url']}' target='_blank' rel='noopener'>Read Article →</a>
        </div>
        """

    return HTMLResponse(
        f"""<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>TrendRadar — Fleet-Tech Intelligence</title>
  <style>
    body {{ margin:0; background:#020817; color:#f1f5f9; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }}
    .wrap {{ max-width:1000px; margin:0 auto; padding:28px 16px; }}
    .head {{ border:1px solid #1e293b; background:#0b1220; border-radius:14px; padding:22px; }}
    h1 {{ margin:0; font-size:30px; }}
    h1 span {{ color:#3b82f6; }}
    .grid {{ margin-top:16px; display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px; }}
    .card {{ border:1px solid #1e293b; background:#0f172a; border-radius:12px; padding:14px; }}
    .meta {{ color:#94a3b8; font-size:12px; margin-bottom:6px; }}
    h3 {{ margin:0 0 8px 0; font-size:18px; }}
    a {{ color:#93c5fd; text-decoration:none; font-weight:600; }}
    a:hover {{ text-decoration:underline; }}
  </style>
</head>
<body>
  <div class='wrap'>
    <div class='head'>
      <h1>Trend<span>Radar</span> — Live Feed</h1>
      <p>Stable Render deployment endpoint.</p>
      <div class='grid'>{cards}</div>
    </div>
  </div>
</body>
</html>"""
    )
