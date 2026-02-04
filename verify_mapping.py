import logging
import pandas as pd
from unittest.mock import MagicMock
from dhan_client import DhanClientWrapper

# Setup Logging
logging.basicConfig(level=logging.INFO)

def test_mapping_logic():
    print("Testing Security Mapping Logic...")

    client = DhanClientWrapper()
    
    # We will test the fetching method directly (requires internet)
    # The method is 'fetch_security_mapping'
    
    print("Fetching Master CSV (this may take a few seconds)...")
    client.fetch_security_mapping()
    
    if not client.symbol_map:
        print("FAIL: Map is empty. CSV fetch likely failed.")
        return
        
    print(f"Loaded {len(client.symbol_map)} symbols.")
    
    # Test a few known symbols
    test_symbols = ['MRF', 'RELIANCE', 'TCS']
    
    for sym in test_symbols:
        sid = client.get_security_id(sym)
        if sid:
            print(f"SUCCESS: {sym} -> {sid}")
        else:
            print(f"WARNING: {sym} not found in map (Attempting with -EQ check...)")
            # The logic tries -EQ automatically
            
    # Check what 'MRF' keys exist
    # print("Dictionary Sample:", list(client.symbol_map.keys())[:10])

if __name__ == "__main__":
    test_mapping_logic()
