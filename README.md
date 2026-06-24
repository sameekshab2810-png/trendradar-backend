# TrendRadar Backend

Deploy-ready FastAPI backend for stable Render URL.

## Endpoints
- `/feed` - Web dashboard
- `/docs` - Swagger docs
- `/health` - Health check
- `/events` - Events list
- `/events/stats` - Event stats

## Render
- Build: `pip install -r requirements.txt`
- Start: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
