import logging
from unittest.mock import MagicMock
from strategy_engine import LadderEngine
# Mocking config and StockStatus by creating dummy instances if needed, 
# or letting engine init them.
# We need to mock settings.

# Setup Logging
logging.basicConfig(level=logging.INFO)

def test_turnover_filter():
    print("Testing Turnover Filter Logic...")
    
    match_found = False
    
    # Mock Dhan Client
    from dhan_client import DhanClientWrapper
    mock_dhan = MagicMock(spec=DhanClientWrapper)
    mock_dhan.is_connected = True
    
    engine = LadderEngine(mock_dhan)
    engine.running = True
    
    # Setup 2 Stocks in 'active_stocks' (simulating after filter & sub)
    # Stock A: High Turnover (> 1Cr) -> Should be picked
    # Stock B: Low Turnover (< 1Cr) -> Should be ignored
    
    from config import StockStatus
    
    # 1.5 Cr Turnover
    s1 = StockStatus(
        symbol="HIGH_VAL", mode="NONE", ltp=100, change_pct=1.0, pnl=0, status="IDLE",
        entry_price=0, quantity=0, ladder_level=0, next_add_on=0, stop_loss=0, target=0, prev_close=99,
        turnover=15000000.0 
    )
    
    # 0.5 Cr Turnover
    s2 = StockStatus(
        symbol="LOW_VAL", mode="NONE", ltp=100, change_pct=2.0, pnl=0, status="IDLE",
        entry_price=0, quantity=0, ladder_level=0, next_add_on=0, stop_loss=0, target=0, prev_close=98,
        turnover=5000000.0 
    )
    
    engine.active_stocks = {"HIGH_VAL": s1, "LOW_VAL": s2}
    
    # Mock start_long_ladder to verify call
    engine.start_long_ladder = MagicMock()
    
    # Run Selection
    print("Running selection...")
    engine.select_top_movers()
    
    # Verify s1 is picked (High Turnover) despite s2 having higher % change (2% vs 1%)
    # Wait, both are filtered by Turnover first.
    # s2 should be rejected. s1 accepted.
    
    # Check calls
    called_args = [args[0].symbol for args, _ in engine.start_long_ladder.call_args_list]
    print("Activated Stocks:", called_args)
    
    assert "HIGH_VAL" in called_args, "High Turnover stock should be activated"
    assert "LOW_VAL" not in called_args, "Low Turnover stock should be rejected"
    
    print("Test Passed: Turnover filter works.")

if __name__ == "__main__":
    test_turnover_filter()
