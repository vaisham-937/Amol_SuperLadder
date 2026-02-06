import logging
from unittest.mock import MagicMock

from config import StockStatus, StrategySettings
from dhan_client import DhanClientWrapper
from strategy_engine import LadderEngine

logging.basicConfig(level=logging.INFO)


def test_max_ladder_stocks_limits_new_starts():
    mock_dhan = MagicMock(spec=DhanClientWrapper)
    mock_dhan.is_connected = True

    engine = LadderEngine(mock_dhan)
    engine.running = True
    engine.update_settings(
        StrategySettings(
            max_ladder_stocks=20,
            top_n_gainers=10,
            top_n_losers=10,
            min_turnover_crores=1.0,
            trade_capital=5000.0,
        )
    )

    # Create 60 positive movers + 60 negative movers (all eligible by turnover/ltp)
    active = {}
    for i in range(60):
        sym = f"G{i:02d}"
        active[sym] = StockStatus(
            symbol=sym,
            mode="NONE",
            ltp=100.0,
            change_pct=5.0 - (i * 0.01),
            pnl=0.0,
            status="IDLE",
            entry_price=0.0,
            quantity=0,
            ladder_level=0,
            next_add_on=0.0,
            stop_loss=0.0,
            target=0.0,
            prev_close=95.0,
            turnover=2_00_00_000.0,  # 2 Cr
        )
    for i in range(60):
        sym = f"L{i:02d}"
        active[sym] = StockStatus(
            symbol=sym,
            mode="NONE",
            ltp=100.0,
            change_pct=-(5.0 - (i * 0.01)),
            pnl=0.0,
            status="IDLE",
            entry_price=0.0,
            quantity=0,
            ladder_level=0,
            next_add_on=0.0,
            stop_loss=0.0,
            target=0.0,
            prev_close=105.0,
            turnover=2_00_00_000.0,  # 2 Cr
        )

    engine.active_stocks = active

    def _start_long(stock: StockStatus):
        stock.mode = "LONG"
        stock.status = "ACTIVE"
        stock.quantity = 1

    def _start_short(stock: StockStatus):
        stock.mode = "SHORT"
        stock.status = "ACTIVE"
        stock.quantity = 1

    engine.start_long_ladder = MagicMock(side_effect=_start_long)
    engine.start_short_ladder = MagicMock(side_effect=_start_short)

    # Run selection multiple times; should only start up to 10 longs + 10 shorts total.
    for _ in range(5):
        engine.select_top_movers()

    assert engine.start_long_ladder.call_count == 10, "Should start only top 10 gainers"
    assert engine.start_short_ladder.call_count == 10, "Should start only top 10 losers"


def test_settings_enforce_sum_with_max_ladder_stocks():
    mock_dhan = MagicMock(spec=DhanClientWrapper)
    mock_dhan.is_connected = True
    engine = LadderEngine(mock_dhan)

    engine.update_settings(
        StrategySettings(
            max_ladder_stocks=5,
            top_n_gainers=3,
            top_n_losers=4,
        )
    )
    assert engine.settings.top_n_gainers == 3
    assert engine.settings.top_n_losers == 2, "Losers should be clamped so gainers+losers==max"


def test_session_max_blocks_new_symbols_even_if_capacity_frees_up():
    mock_dhan = MagicMock(spec=DhanClientWrapper)
    mock_dhan.is_connected = True

    engine = LadderEngine(mock_dhan)
    engine.running = True
    engine.update_settings(
        StrategySettings(
            max_ladder_stocks=5,
            top_n_gainers=3,
            top_n_losers=2,
            min_turnover_crores=1.0,
        )
    )

    # Simulate we've already started 5 unique symbols this session.
    engine.started_symbols = {"A", "B", "C", "D", "E"}

    engine.active_stocks = {
        "X1": StockStatus(
            symbol="X1",
            mode="NONE",
            ltp=100.0,
            change_pct=1.5,
            pnl=0.0,
            status="IDLE",
            entry_price=0.0,
            quantity=0,
            ladder_level=0,
            next_add_on=0.0,
            stop_loss=0.0,
            target=0.0,
            prev_close=98.0,
            turnover=2_00_00_000.0,
        )
    }

    engine.start_long_ladder = MagicMock()
    engine.start_short_ladder = MagicMock()
    engine.select_top_movers()
    assert engine.start_long_ladder.call_count == 0
    assert engine.start_short_ladder.call_count == 0


if __name__ == "__main__":
    test_max_ladder_stocks_limits_new_starts()
    test_settings_enforce_sum_with_max_ladder_stocks()
    test_session_max_blocks_new_symbols_even_if_capacity_frees_up()
    print("OK")
