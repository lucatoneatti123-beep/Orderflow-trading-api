from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, date

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

# --- NEWS ---
@app.get("/calendar/news")
def news():
    return [
        {"ts": "2025-09-19T12:30:00Z", "importance": "high", "title": "US CPI m/m", "source": "Mock"},
        {"ts": "2025-09-19T18:00:00Z", "importance": "medium", "title": "FOMC Member Speech", "source": "Mock"}
    ]

# --- OPEX ---
@app.get("/calendar/opex")
def opex(symbol: str = "NQ"):
    return [
        {"date": "2025-09-20", "kind": "monthly", "notes": "Monthly OPEX"},
        {"date": "2025-09-27", "kind": "weekly", "notes": "Weekly OPEX"}
    ]

# --- PING ---
@app.get("/utils/ping")
def ping():
    return {"status": "ok"}
