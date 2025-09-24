from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, date
import os, time
import feedparser, httpx

app = FastAPI(title="Trading Data API", version="1.0.0")

# CORS aperto (serve quando il GPT chiama il tuo server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- GAMMA LEVELS ---
@app.get("/gamma/levels")
def gamma_levels(symbol: str = "NQ", date_ref: str = str(date.today())):
    return [
        {"label": "1D_min", "level": 16120, "strength": 0.7, "kind": "1D_min", "source": "Mock"},
        {"label": "Gamma Wall", "level": 16350, "strength": 0.9, "kind": "GammaWall", "source": "Mock"},
        {"label": "HVL", "level": 16500, "strength": 0.5, "kind": "HVL", "source": "Mock"}
    ]

# --- GAMMA STATE / ENVIRONMENT ---
@app.get("/gamma/state")
def gamma_state(symbol: str = "NQ", date_ref: str = str(date.today())):
    return {
        "regime": "positive",
        "flip_level": 16280,
        "commentary": f"Gamma positiva su {symbol}, sopra flip tende a mean-revert.",
        "opex": "2025-09-20"
    }

# --- NEWS: FinancialJuice via RSS ---
FJ_RSS_URL = os.getenv("FJ_RSS_URL", "").strip()
FINNHUB_TOKEN = os.getenv("FINNHUB_TOKEN", "").strip()
TE_API_KEY = os.getenv("TE_API_KEY", "").strip()
_NEWS_CACHE = {"ts": 0, "data": []}
_CACHE_TTL = 60  # secondi di cache per non martellare il feed

def _map_importance(raw_text: str):
    if not raw_text:
        return "medium"
    v = raw_text.lower()
    if "high" in v or "red" in v or "3" in v:
        return "high"
    if "low" in v or "yellow" in v or "1" in v:
        return "low"
    return "medium"

@app.get("/calendar/news")
async def calendar_news(min_importance: str = "medium", limit: int = 20):
    # cache povera ma utile
    now = time.time()
    if now - _NEWS_CACHE["ts"] < _CACHE_TTL and _NEWS_CACHE["data"]:
        return _NEWS_CACHE["data"]

    if not FJ_RSS_URL:
        return []

    # 1) prova diretta col parser
    feed = feedparser.parse(FJ_RSS_URL)
    entries = getattr(feed, "entries", []) or []

    # 2) fallback con User-Agent se il feed fa lo schizzinoso
    if not entries:
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "Mozilla/5.0"}) as client:
            r = await client.get(FJ_RSS_URL)
            r.raise_for_status()
            entries = getattr(feedparser.parse(r.text), "entries", []) or []

    out = []
    for e in entries:
        ts = getattr(e, "published", None) or getattr(e, "updated", None)
        title = getattr(e, "title", None)
        tags = getattr(e, "tags", None) or []
        tag_text = " ".join([getattr(t, "term", "") for t in tags]) if tags else getattr(e, "summary", "")
        imp = _map_importance(tag_text)
        if ts and title:
            out.append({"ts": ts, "importance": imp, "title": title, "source": "FinancialJuice"})

      # filtra per importanza e limita risultati
    rank = {"low": 0, "medium": 1, "high": 2}
    thr = rank.get((min_importance or "medium").lower(), 1)
    out = [x for x in out if rank.get((x.get("importance") or "medium").lower(), 1) >= thr]
    out = out[:max(1, min(100, int(limit)))]

    _NEWS_CACHE["ts"] = now
    _NEWS_CACHE["data"] = out
    return out

# --- OPEX ---
@app.get("/calendar/opex")
def opex(symbol: str = "NQ"):
    return [
        {"date": "2025-09-20", "kind": "monthly", "notes": "Monthly OPEX"},
        {"date": "2025-09-27", "kind": "weekly", "notes": "Weekly OPEX"}
    ]

# --- ECON CALENDAR via TradingEconomics ---
def _map_te_importance(x):
    try:
        n = int(x)  # TE: 0=low, 1=medium, 2=high
    except:
        return "medium"
    return {0: "low", 1: "medium", 2: "high"}.get(n, "medium")

@app.get("/calendar/events")
async def econ_events(
    date: str,                      # YYYY-MM-DD
    min_importance: str = "medium", # low | medium | high
    limit: int = 50,
    country: str = ""               # es. "United States", "Euro Area"
):
    if not TE_API_KEY:
        return []

    params = {
        "c": TE_API_KEY,
        "f": "json",
        "initDate": date,
        "endDate": date,
    }
    if country:
        params["country"] = country  # TE usa nomi completi

    async with httpx.AsyncClient(timeout=12) as client:
        r = await client.get("https://api.tradingeconomics.com/calendar", params=params)
        r.raise_for_status()
        items = r.json()

    rank = {"low": 0, "medium": 1, "high": 2}
    thr = rank.get((min_importance or "medium").lower(), 1)

    out = []
    for it in items if isinstance(items, list) else []:
        d = (it.get("Date") or "")[:10]  # "2025-09-23T08:45:00" -> "2025-09-23"
        if d != date:
            continue
        imp = _map_te_importance(it.get("Importance"))
        if rank.get(imp, 1) < thr:
            continue
        out.append({
            "date": d,
            "time_utc": it.get("Date"),
            "title": it.get("Event"),
            "country": it.get("Country"),
            "importance": imp,
            "forecast": it.get("Forecast"),
            "previous": it.get("Previous"),
            "source": "TradingEconomics"
        })

    return out[:max(1, min(200, int(limit)))]

# --- PING ---
@app.get("/utils/ping")
def ping():
    return {"status": "ok"}






