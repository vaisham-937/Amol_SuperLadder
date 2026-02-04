"""Test script to verify Dhan API fixes"""
import asyncio
from dhan_client import DhanClientWrapper

async def test_historical_data():
    """Test historical data fetching with fixed constants"""
    client = DhanClientWrapper()
    
    # Use your credentials
    client_id = "1101693020"
    access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzcwMDkyMjgzLCJpYXQiOjE3NzAwMDU4ODMsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAxNjkzMDIwIn0.hd5pAepKAI6KHqT42V_ox-XqRUlbWACoA89vs-hS3uRFwHrERERszBs2ghTnKn0RdYTF6gprVdQS9XKDlUf0wA"
    
    success, msg = client.connect(client_id, access_token)
    print(f"Connection: {success} - {msg}")
    
    if not success:
        return
    
    # Test with a few symbols
    test_symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'SBIN']
    
    for symbol in test_symbols:
        print(f"\nTesting {symbol}...")
        df = await client.get_historical_data_async(symbol, days=10)
        if df is not None and not df.empty:
            print(f"✅ {symbol}: Got {len(df)} rows of data")
            print(f"   Latest close: {df.iloc[-1]['close']}")
        else:
            print(f"❌ {symbol}: Failed to fetch data")

if __name__ == "__main__":
    asyncio.run(test_historical_data())
