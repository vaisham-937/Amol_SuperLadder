from pydantic import BaseModel
from typing import Optional, List

class StrategySettings(BaseModel):
    # Credentials
    client_id: str = ""
    access_token: str = ""
    
    # Ladder Settings
    no_of_add_ons: int = 5
    add_on_percentage: float = 0.5  # % rise/fall to add more
    initial_stop_loss_pct: float = 0.5
    trailing_stop_loss_pct: float = 0.5
    target_percentage: float = 2.0
    
    # Selection Settings
    max_ladder_stocks: int = 20
    top_n_gainers: int = 10
    top_n_losers: int = 10
    min_turnover_crores: float = 1.0
    
    # Risk Management
    trade_capital: float = 1000.0
    profit_target_per_stock: float = 5000.0
    loss_limit_per_stock: float = 2000.0
    
    # State
    is_active: bool = False

class TradeSignal(BaseModel):
    symbol: str
    signal_type: str  # LONG, SHORT
    price: float
    timestamp: str

class StockStatus(BaseModel):
    symbol: str
    mode: str # LONG, SHORT, NONE (Closed)
    ltp: float
    change_pct: float
    pnl: float
    status: str # ACTIVE, CLOSED_PROFIT, CLOSED_LOSS, STOPPED, IDLE
    entry_price: float
    quantity: int
    ladder_level: int
    next_add_on: float
    stop_loss: float
    target: float
    prev_close: float = 0.0
    turnover: float = 0.0
    high_watermark: float = 0.0  # For trailing SL tracking
    order_ids: List[str] = []  # Track all orders for this position
    avg_entry_price: float = 0.0  # Average entry price for accurate P&L

class PerformanceSettings(BaseModel):
    """Performance and optimization settings."""
    tick_batch_interval_ms: int = 100
    max_concurrent_orders: int = 2
    enable_performance_logging: bool = True
    websocket_reconnect_delay_seconds: int = 5
    order_retry_max_attempts: int = 3


