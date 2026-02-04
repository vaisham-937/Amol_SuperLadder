import logging
import json
import pandas as pd
from unittest.mock import MagicMock, patch
from strategy_engine import LadderEngine, STOCK_LIST
from config import StockStatus
from dhan_client import DhanClientWrapper

# Setup Logging
logging.basicConfig(level=logging.INFO)

def test_load_filtered_stocks():
    """Test loading pre-filtered stocks from JSON."""
    print("Testing Load Filtered Stocks from JSON...")
    
    # Mock Dhan Client
    mock_dhan = MagicMock(spec=DhanClientWrapper)
    mock_dhan.is_connected = True
    
    # Create test JSON file
    test_data = {
        'timestamp': '2026-02-03T07:00:00',
        'criteria': {
            'volume_sma_threshold': 2000,
            'volume_sma_divisor': 1875,
            'required_days': 5
        },
        'total_stocks_screened': 180,
        'stocks_accepted': 3,
        'candidates': {
            'MRF': 131500.50,
            'BOSCHLTD': 34250.75,
            'SHREECEM': 26800.00
        }
    }
    
    # Write test JSON
    with open('test_filtered_stocks.json', 'w') as f:
        json.dump(test_data, f, indent=2)
    
    # Initialize Engine
    engine = LadderEngine(mock_dhan)
    
    # Test loading
    candidates = engine.load_filtered_stocks('test_filtered_stocks.json')
    
    print(f"\nLoaded Candidates: {candidates}")
    
    # Assertions
    assert len(candidates) == 3, "Should load 3 candidates"
    assert 'MRF' in candidates, "MRF should be in candidates"
    assert candidates['MRF'] == 131500.50, "MRF prev_close should match"
    assert candidates['BOSCHLTD'] == 34250.75, "BOSCHLTD prev_close should match"
    
    # Cleanup
    import os
    os.remove('test_filtered_stocks.json')
    
    print("\nTest Passed: Load filtered stocks works correctly.")

if __name__ == "__main__":
    test_load_filtered_stocks()
