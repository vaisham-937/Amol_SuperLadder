from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel
import asyncio
import json
import logging
import sys

from config import StrategySettings
from dhan_client import DhanClientWrapper
from strategy_engine import LadderEngine
from performance_monitor import perf_monitor

# Logging Setup
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
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
            # Construct Status JSON
            status_data = {
                "active_stocks": [s.dict() for s in engine.active_stocks.values()],
                "global_pnl": engine.pnl_global,
                "is_running": engine.running,
                "dhan_connected": dhan.is_connected,
                "performance": perf_monitor.get_all_metrics() if perf_monitor.enabled else {}
            }
            await manager.broadcast(json.dumps(status_data))
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
        await asyncio.sleep(0.5)  # Update every 500ms

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_status())
    # Start performance logging
    if perf_monitor.enabled:
        asyncio.create_task(perf_monitor.periodic_logging(interval_seconds=60))

# Routes
@app.get("/")
async def get_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/login")
async def login_dhan(settings: StrategySettings):
    """Connect to Dhan API and update credentials."""
    success, msg = dhan.connect(settings.client_id, settings.access_token)
    if success:
        engine.update_settings(settings)
    return {"success": success, "message": msg}

@app.post("/api/settings")
async def update_settings(settings: StrategySettings):
    """Update strategy settings and auto-connect if credentials provided."""
    
    # If credentials are provided, connect to Dhan first
    if settings.client_id and settings.access_token:
        logger.info("Credentials detected in settings - auto-connecting to Dhan...")
        success, msg = dhan.connect(settings.client_id, settings.access_token)
        if not success:
            logger.error(f"Failed to connect to Dhan: {msg}")
            return {"status": "error", "message": f"Failed to connect to Dhan: {msg}"}
        logger.info("✅ Dhan connected successfully via Save Settings")
    
    # Update strategy settings
    engine.update_settings(settings)
    logger.info(f"Settings updated and applied")
    
    return {"status": "success", "message": "Settings saved and Dhan connected", "settings": settings.dict()}

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
    return {"status": "Stopped"}

@app.get("/api/status")
async def get_status():
    """Get current system status."""
    return {
        "dhan_connected": dhan.is_connected,
        "engine_running": engine.running,
        "active_positions": len([s for s in engine.active_stocks.values() if s.mode != "NONE"]),
        "total_stocks": len(engine.active_stocks),
        "global_pnl": engine.pnl_global
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
