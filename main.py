from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel
import asyncio
import json
import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from config import StrategySettings
from credentials_store import load_credentials, save_credentials
from dhan_client import DhanClientWrapper
from strategy_engine import LadderEngine
from performance_monitor import perf_monitor
from strategy_engine import STOCK_LIST

# Logging Setup (IST timestamps)
IST = ZoneInfo("Asia/Kolkata")

class ISTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, IST)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat(sep=" ", timespec="milliseconds")

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(ISTFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = [handler]
logger = logging.getLogger("Main")

app = FastAPI(title="Dhan Ladder Algo")

# Mount Static & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global Instances
dhan = DhanClientWrapper()
engine = LadderEngine(dhan)

# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"WebSocket send error: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# Background Task for Push Updates
async def broadcast_status():
    while True:
        try:
            positions = [s.dict() for s in engine.active_stocks.values() if s.mode != "NONE"]
            # Construct Status JSON (keep payload small for smooth UI)
            status_data = {
                "positions": positions,
                "active_positions": len(positions),
                "total_stocks": len(engine.active_stocks),
                "global_pnl": engine.pnl_global,
                "is_running": engine.running,
                "dhan_connected": dhan.is_connected,
                "market_open": engine.is_market_hours(),
                "performance": perf_monitor.get_all_metrics() if perf_monitor.enabled else {}
            }
            await manager.broadcast(json.dumps(status_data))
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
        await asyncio.sleep(0.5)  # 2 updates/sec keeps UI smooth

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_status())
    # Start performance logging
    if perf_monitor.enabled:
        asyncio.create_task(perf_monitor.periodic_logging(interval_seconds=60))
    # Auto-connect if saved credentials exist (do not block app startup)
    async def _auto_connect_saved():
        saved_client_id, saved_access_token = load_credentials()
        if not (saved_client_id and saved_access_token) or dhan.is_connected:
            return

        logger.info("Found saved Dhan credentials - auto-connecting in background...")
        try:
            success, msg = await asyncio.to_thread(
                dhan.connect, saved_client_id, saved_access_token, False
            )
        except Exception as e:
            logger.error(f"Auto-connect crashed: {e}", exc_info=True)
            return

        if success:
            merged = engine.settings.model_copy(
                update={"client_id": saved_client_id, "access_token": saved_access_token}
            )
            engine.update_settings(merged)
            logger.info("✅ Auto-connected to Dhan using saved credentials")
        else:
            logger.error(f"Auto-connect failed: {msg}")

    asyncio.create_task(_auto_connect_saved())

# Routes
@app.get("/")
async def get_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/login")
async def login_dhan(settings: StrategySettings):
    """Connect to Dhan API and update credentials."""
    # Skip slow security-master prefetch; it will be fetched lazily on subscribe/top-movers.
    success, msg = dhan.connect(settings.client_id, settings.access_token, False)
    if success:
        engine.update_settings(settings)
        save_credentials(settings.client_id, settings.access_token)
    return {"success": success, "message": msg}

@app.post("/api/settings")
async def update_settings(settings: StrategySettings):
    """Update strategy settings (does not connect to Dhan)."""

    # Preserve credentials if UI doesn't send them (avoid clobbering on refresh).
    merged = settings
    if not merged.client_id:
        merged = merged.model_copy(update={"client_id": engine.settings.client_id})
    if not merged.access_token:
        merged = merged.model_copy(update={"access_token": engine.settings.access_token})

    engine.update_settings(merged)
    logger.info(f"Settings updated and applied")
    
    msg = "Settings saved"
    if dhan.is_connected:
        msg = "Settings saved and Dhan connected"
    return {"status": "success", "message": msg, "settings": settings.dict()}

@app.post("/api/start")
async def start_engine():
    """Start the trading engine."""
    try:
        if not dhan.is_connected:
            logger.error("Cannot start engine: Dhan not connected")
            return {"status": "error", "message": "Dhan not connected. Please login first."}

        if engine.running:
            logger.warning("Engine already running")
            return {"status": "already_running", "message": "Engine is already running"}

        if not engine.is_market_hours():
            return {"status": "error", "message": "Market closed (IST). Engine will not start WebSocket feed."}

        # Ensure we have candidates, otherwise the engine will start and immediately stop.
        candidates_map = engine.load_filtered_stocks()
        if not candidates_map:
            return {
                "status": "error",
                "message": "No filtered stocks available. Run premarket_filter.py first.",
            }

        logger.info("Starting strategy engine...")
        asyncio.create_task(engine.start_strategy())
        return {"status": "success", "message": "Engine started successfully"}

    except Exception as e:
        logger.error(f"Failed to start engine: {e}", exc_info=True)
        return {"status": "error", "message": f"Failed to start: {str(e)}"}

@app.post("/api/stop")
async def stop_engine():
    """Stop the trading engine."""
    engine.running = False
    dhan.stop_feed()
    return {"status": "Stopped"}

@app.get("/api/status")
async def get_status():
    """Get current system status."""
    return {
        "dhan_connected": dhan.is_connected,
        "engine_running": engine.running,
        "active_positions": len([s for s in engine.active_stocks.values() if s.mode != "NONE"]),
        "total_stocks": len(engine.active_stocks),
        "global_pnl": engine.pnl_global,
        "market_open": engine.is_market_hours()
    }

@app.get("/api/positions")
async def get_positions():
    """Get current positions from Dhan."""
    if not dhan.is_connected:
        return {"status": "error", "message": "Not connected"}
    
    positions = dhan.get_positions()
    return {"status": "success", "positions": positions}

@app.post("/api/square-off-all")
async def emergency_square_off():
    """Emergency square-off all positions."""
    if not dhan.is_connected:
        return {"status": "error", "message": "Not connected"}
    
    try:
        await engine.square_off_all()
        return {"status": "success", "message": "All positions squared off"}
    except Exception as e:
        logger.error(f"Square-off failed: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/close-position/{symbol}")
async def close_single_position(symbol: str):
    """Close a specific position."""
    if symbol not in engine.active_stocks:
        return {"status": "error", "message": "Stock not found"}
    
    stock = engine.active_stocks[symbol]
    if stock.mode == "NONE":
        return {"status": "error", "message": "No active position"}
    
    try:
        engine.close_position(stock, "Manual Close")
        stock.status = "CLOSED_MANUAL"
        return {"status": "success", "message": f"{symbol} position closed"}
    except Exception as e:
        logger.error(f"Failed to close {symbol}: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/metrics")
async def get_metrics():
    """Get performance metrics."""
    return {
        "status": "success",
        "metrics": perf_monitor.get_all_metrics(),
        "order_summary": engine.order_manager.get_summary()
    }

@app.get("/api/top-movers")
async def get_top_movers():
    """Fetch top gainers/losers via REST for closed market or fallback."""
    if not dhan.is_connected:
        return {"status": "error", "message": "Not connected"}

    # Prefer filtered candidates if available
    candidates_map = engine.load_filtered_stocks()
    symbols = list(candidates_map.keys()) if candidates_map else STOCK_LIST

    result = dhan.get_top_movers(
        symbols,
        top_n_gainers=engine.settings.top_n_gainers,
        top_n_losers=engine.settings.top_n_losers,
        exchange_segment="NSE_EQ",
    )
    return {
        "status": "success",
        "gainers": result.get("gainers", []),
        "losers": result.get("losers", []),
        "errors": result.get("errors", []),
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "dhan_connected": dhan.is_connected,
        "engine_running": engine.running
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
