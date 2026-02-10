import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

from config import StockStatus, StrategySettings
from dhan_client import DhanClientWrapper
from strategy_engine import LadderEngine


def test_open_gap_filters_for_entry():
    mock_dhan = MagicMock(spec=DhanClientWrapper)
    mock_dhan.is_connected = True
    engine = LadderEngine(mock_dhan)
    engine.running = True

    engine.update_settings(
        StrategySettings(
            max_ladder_stocks=5,
            top_n_gainers=1,
            top_n_losers=1,
            min_turnover_crores=1.0,
            max_open_gap_pct_long=3.0,
            min_open_gap_pct_short=-3.0,
            cycles_per_stock=3,
        )
    )

    # Eligible by turnover, but gainer is filtered out due to large positive gap (>3%)
    g1 = StockStatus(
        symbol="GAP_LONG_BAD",
        mode="NONE",
        ltp=103.5,
        change_pct=4.0,
        pnl=0.0,
        status="IDLE",
        entry_price=0.0,
        quantity=0,
        ladder_level=0,
        next_add_on=0.0,
        stop_loss=0.0,
        target=0.0,
        prev_close=100.0,
        turnover=2_00_00_000.0,  # 2 Cr
        day_open=105.0,
        open_gap_pct=5.0,
    )

    # Eligible by turnover, but loser is filtered out due to too negative gap (< -3%)
    l1 = StockStatus(
        symbol="GAP_SHORT_BAD",
        mode="NONE",
        ltp=96.0,
        change_pct=-4.0,
        pnl=0.0,
        status="IDLE",
        entry_price=0.0,
        quantity=0,
        ladder_level=0,
        next_add_on=0.0,
        stop_loss=0.0,
        target=0.0,
        prev_close=100.0,
        turnover=2_00_00_000.0,
        day_open=95.0,
        open_gap_pct=-5.0,
    )

    # Controls: these should be selected
    g2 = StockStatus(
        symbol="GAP_LONG_OK",
        mode="NONE",
        ltp=102.0,
        change_pct=3.0,
        pnl=0.0,
        status="IDLE",
        entry_price=0.0,
        quantity=0,
        ladder_level=0,
        next_add_on=0.0,
        stop_loss=0.0,
        target=0.0,
        prev_close=100.0,
        turnover=2_00_00_000.0,
        day_open=102.5,
        open_gap_pct=2.5,
    )
    l2 = StockStatus(
        symbol="GAP_SHORT_OK",
        mode="NONE",
        ltp=98.0,
        change_pct=-2.0,
        pnl=0.0,
        status="IDLE",
        entry_price=0.0,
        quantity=0,
        ladder_level=0,
        next_add_on=0.0,
        stop_loss=0.0,
        target=0.0,
        prev_close=100.0,
        turnover=2_00_00_000.0,
        day_open=98.5,
        open_gap_pct=-1.5,
    )

    engine.active_stocks = {
        g1.symbol: g1,
        l1.symbol: l1,
        g2.symbol: g2,
        l2.symbol: l2,
    }

    engine.start_long_ladder = MagicMock()
    engine.start_short_ladder = MagicMock()

    engine.select_top_movers()

    long_syms = [args[0].symbol for args, _ in engine.start_long_ladder.call_args_list]
    short_syms = [args[0].symbol for args, _ in engine.start_short_ladder.call_args_list]

    assert "GAP_LONG_OK" in long_syms
    assert "GAP_LONG_BAD" not in long_syms
    assert "GAP_SHORT_OK" in short_syms
    assert "GAP_SHORT_BAD" not in short_syms


def test_three_cycle_alternation_calls_flip_then_close():
    mock_dhan = MagicMock(spec=DhanClientWrapper)
    mock_dhan.is_connected = True
    engine = LadderEngine(mock_dhan)
    engine.running = True

    stock = StockStatus(
        symbol="TST",
        mode="LONG",
        ltp=100.0,
        change_pct=1.0,
        pnl=0.0,
        status="ACTIVE",
        entry_price=100.0,
        quantity=10,
        ladder_level=1,
        next_add_on=0.0,
        stop_loss=0.0,
        target=0.0,
        prev_close=99.0,
        turnover=2_00_00_000.0,
        cycle_total=3,
        cycle_index=0,
        cycle_start_mode="LONG",
    )

    engine._close_and_flip = MagicMock()
    engine.close_position = MagicMock()

    engine._finish_ladder_cycle(stock, reason="Target Hit")
    engine._close_and_flip.assert_called_once()
    engine.close_position.assert_not_called()

    # Simulate 2nd cycle completion
    stock.mode = "SHORT"
    stock.cycle_index = 1
    engine._close_and_flip.reset_mock()
    engine.close_position.reset_mock()
    engine._finish_ladder_cycle(stock, reason="Target Hit")
    engine._close_and_flip.assert_called_once()
    engine.close_position.assert_not_called()

    # 3rd cycle completion should close (no flip)
    stock.mode = "LONG"
    stock.cycle_index = 2
    engine._close_and_flip.reset_mock()
    engine.close_position.reset_mock()
    engine._finish_ladder_cycle(stock, reason="Target Hit")
    engine._close_and_flip.assert_not_called()
    engine.close_position.assert_called_once()


async def test_global_profit_exit_triggers_square_off_and_halts():
    mock_dhan = MagicMock(spec=DhanClientWrapper)
    mock_dhan.is_connected = True
    mock_dhan.subscribe = MagicMock()
    mock_dhan.stop_feed = MagicMock()

    engine = LadderEngine(mock_dhan)
    engine.is_market_hours = MagicMock(return_value=True)
    engine.load_filtered_stocks = MagicMock(return_value={"TST": 100.0})

    engine.update_settings(
        StrategySettings(
            global_profit_exit=8000.0,
            global_loss_exit=8000.0,
            trade_capital=1000.0,
        )
    )

    # Create a position with pnl over threshold after engine initializes tracking.
    async_square_off = AsyncMock()
    engine.square_off_all = async_square_off

    task = asyncio.create_task(engine.start_strategy())
    try:
        deadline = time.time() + 5.0
        while time.time() < deadline:
            if "TST" in engine.active_stocks:
                engine.active_stocks["TST"].pnl = 9000.0
            await asyncio.sleep(0.2)
            if engine.trading_halted:
                break

        assert engine.trading_halted is True
        async_square_off.assert_awaited()
    finally:
        engine.running = False
        try:
            await asyncio.wait_for(task, timeout=3.0)
        except Exception:
            pass


def main():
    test_open_gap_filters_for_entry()
    test_three_cycle_alternation_calls_flip_then_close()
    asyncio.run(test_global_profit_exit_triggers_square_off_and_halts())
    print("OK")


if __name__ == "__main__":
    main()

