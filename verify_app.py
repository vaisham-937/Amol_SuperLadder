"""
Application Verification Script
Tests core functionality and performance of the Dhan trading application.
"""

import asyncio
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all required modules can be imported."""
    logger.info("Testing imports...")
    try:
        import fastapi
        import uvicorn
        import dhanhq
        import websockets
        import pandas as pd
        import numpy as np
        import aiohttp
        import ujson
        import psutil
        
        from config import StrategySettings, StockStatus, PerformanceSettings
        from dhan_client import DhanClientWrapper
        from strategy_engine import LadderEngine
        from order_manager import OrderManager
        from performance_monitor import perf_monitor
        from main import app
        
        logger.info("PASS: All imports successful")
        return True
    except ImportError as e:
        logger.error(f"FAIL: Import error: {e}")
        return False

def test_config():
    """Test configuration models."""
    logger.info("Testing configuration models...")
    try:
        from config import StrategySettings, StockStatus, PerformanceSettings
        
        # Test StrategySettings
        settings = StrategySettings(
            client_id="test123",
            access_token="token456",
            trade_capital=100000,
            no_of_add_ons=5
        )
        assert settings.client_id == "test123"
        assert settings.trade_capital == 100000
        
        # Test StockStatus
        stock = StockStatus(
            symbol="TCS",
            mode="LONG",
            ltp=3500.0,
            change_pct=2.5,
            pnl=500.0,
            status="ACTIVE",
            entry_price=3450.0,
            quantity=10,
            ladder_level=1,
            next_add_on=3550.0,
            stop_loss=3400.0,
            target=3600.0
        )
        assert stock.symbol == "TCS"
        assert stock.mode == "LONG"
        
        # Test PerformanceSettings
        perf_settings = PerformanceSettings()
        assert perf_settings.tick_batch_interval_ms == 100
        
        logger.info("PASS: Configuration models working correctly")
        return True
    except Exception as e:
        logger.error(f"FAIL: Config test failed: {e}")
        return False

def test_performance_monitor():
    """Test performance monitoring."""
    logger.info("Testing performance monitor...")
    try:
        from performance_monitor import PerformanceMonitor
        
        monitor = PerformanceMonitor(enabled=True)
        
        # Record some test latencies
        monitor.record_tick_latency(5.2)
        monitor.record_tick_latency(6.8)
        monitor.record_tick_latency(4.5)
        
        monitor.record_order_latency(250.0)
        monitor.record_order_latency(300.0)
        
        # Get stats
        tick_stats = monitor.get_tick_stats()
        assert tick_stats['total_ticks'] == 3
        assert tick_stats['min_latency_ms'] == 4.5
        assert tick_stats['max_latency_ms'] == 6.8
        
        order_stats = monitor.get_order_stats()
        assert order_stats['total_orders'] == 2
        
        system_stats = monitor.get_system_stats()
        assert 'cpu_percent' in system_stats
        assert 'memory_mb' in system_stats
        
        logger.info("PASS: Performance monitor working correctly")
        return True
    except Exception as e:
        logger.error(f"FAIL: Performance monitor test failed: {e}")
        return False

def test_order_manager():
    """Test order management."""
    logger.info("Testing order manager...")
    try:
        from order_manager import OrderManager, Order
        
        manager = OrderManager()
        
        # Create order
        order = manager.create_order(
            symbol="TCS",
            transaction_type="BUY",
            quantity=10,
            order_type="MARKET"
        )
        assert order is not None
        assert order.symbol == "TCS"
        assert order.quantity == 10
        
        # Update order status
        manager.update_order_status(
            order.order_id,
            status="EXECUTED",
            executed_price=3500.0,
            executed_quantity=10
        )
        
        # Get stock orders
        stock_orders = manager.get_stock_orders("TCS")
        assert len(stock_orders) == 1
        
        # Calculate average entry
        avg_entry = manager.calculate_average_entry("TCS", "BUY")
        assert avg_entry == 3500.0
        
        # Get summary
        summary = manager.get_summary()
        assert summary['total_orders'] == 1
        assert summary['executed'] == 1
        
        logger.info("PASS: Order manager working correctly")
        return True
    except Exception as e:
        logger.error(f"FAIL: Order manager test failed: {e}")
        return False

def test_dhan_client_structure():
    """Test Dhan client structure (without actual connection)."""
    logger.info("Testing Dhan client structure...")
    try:
        from dhan_client import DhanClientWrapper
        
        client = DhanClientWrapper()
        assert client.is_connected == False
        assert hasattr(client, 'symbol_map')
        assert hasattr(client, 'id_map')
        assert hasattr(client, 'get_security_id')
        assert hasattr(client, 'subscribe')
        assert hasattr(client, 'place_order')
        
        logger.info("PASS: Dhan client structure valid")
        return True
    except Exception as e:
        logger.error(f"FAIL: Dhan client test failed: {e}")
        return False

def test_strategy_engine_structure():
    """Test strategy engine structure."""
    logger.info("Testing strategy engine structure...")
    try:
        from dhan_client import DhanClientWrapper
        from strategy_engine import LadderEngine
        
        client = DhanClientWrapper()
        engine = LadderEngine(client)
        
        assert hasattr(engine, 'active_stocks')
        assert hasattr(engine, 'order_manager')
        assert hasattr(engine, 'settings')
        assert hasattr(engine, 'process_tick')
        assert hasattr(engine, 'start_long_ladder')
        assert hasattr(engine, 'start_short_ladder')
        assert hasattr(engine, 'calculate_pnl')
        
        logger.info("PASS: Strategy engine structure valid")
        return True
    except Exception as e:
        logger.error(f"FAIL: Strategy engine test failed: {e}")
        return False

def test_api_structure():
    """Test FastAPI app structure."""
    logger.info("Testing API structure...")
    try:
        from main import app
        
        # Check routes exist
        routes = [route.path for route in app.routes]
        assert "/" in routes
        assert "/api/login" in routes
        assert "/api/start" in routes
        assert "/api/stop" in routes
        assert "/api/status" in routes
        assert "/api/positions" in routes
        assert "/api/square-off-all" in routes
        assert "/api/square-off/{symbol}" in routes
        assert "/api/cache/warm/status" in routes
        assert "/api/close-position/{symbol}" in routes
        assert "/api/warmup" in routes
        assert "/api/metrics" in routes
        assert "/api/top-movers" in routes
        assert "/api/health" in routes
        assert "/ws" in routes
        
        logger.info("PASS: API structure valid")
        return True
    except Exception as e:
        logger.error(f"FAIL: API test failed: {e}")
        return False

def run_all_tests():
    """Run all verification tests."""
    logger.info("="*60)
    logger.info("Starting Application Verification")
    logger.info("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Performance Monitor", test_performance_monitor),
        ("Order Manager", test_order_manager),
        ("Dhan Client", test_dhan_client_structure),
        ("Strategy Engine", test_strategy_engine_structure),
        ("API Structure", test_api_structure),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n--- Running: {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("VERIFICATION SUMMARY")
    logger.info("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\nAll tests passed! Application is ready.")
        logger.info("\nNext Steps:")
        logger.info("1. Start the application: python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        logger.info("2. Open dashboard: http://localhost:8000")
        logger.info("3. Enter Dhan credentials and connect")
        logger.info("4. Configure strategy settings")
        logger.info("5. Start the algo with small capital for testing")
        return True
    else:
        logger.error("\nSome tests failed. Please fix issues before proceeding.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
