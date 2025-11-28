from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="GoblinStack AI")

# Mount static files and templates
# app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("goblinstack_dashboard.html", {"request": request})

@app.get("/markets", response_class=HTMLResponse)
async def markets(request: Request):
    return templates.TemplateResponse("goblinstack_markets.html", {"request": request})

@app.get("/predictions", response_class=HTMLResponse)
async def predictions(request: Request):
    return templates.TemplateResponse("goblinstack_predictions.html", {"request": request})

@app.get("/alerts", response_class=HTMLResponse)
async def alerts(request: Request):
    return templates.TemplateResponse("goblinstack_alerts.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    return templates.TemplateResponse("goblinstack_settings.html", {"request": request})

# API Endpoints
@app.get("/api/market-data")
async def get_market_data():
    return {
        "items": [
            {"name": "Eternal Crystal", "price": 850, "change": -15.2, "volume": 1250},
            {"name": "Elethium Ore", "price": 425, "change": 8.5, "volume": 3400},
            {"name": "Shadowghast Ingot", "price": 1200, "change": -2.1, "volume": 890}
        ]
    }

@app.get("/api/predictions")
async def get_predictions():
    return {
        "predictions": [
            {"item": "Eternal Crystal", "current": 850, "predicted": 1200, "confidence": 87, "timeframe": "3 days"},
            {"item": "Heavy Callous Hide", "current": 65, "predicted": 95, "confidence": 76, "timeframe": "2 days"}
        ]
    }

@app.get("/api/alerts")
async def get_alerts():
    return {
        "alerts": [
            {"type": "success", "title": "Target Hit", "message": "Umbral Aether dropped below 500g", "time": "2m ago"},
            {"type": "warning", "title": "Spike Warning", "message": "Enchant prices rising +15%", "time": "15m ago"},
            {"type": "danger", "title": "Crash Alert", "message": "Herb market oversaturated", "time": "1h ago"}
        ]
    }

if __name__ == "__main__":
    print("🚀 Starting GoblinStack AI on http://127.0.0.1:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
