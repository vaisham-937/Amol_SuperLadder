"""
Premarket Filtration Script
============================
Run this script before market hours to filter stocks by volume SMA criteria.
The filtered candidates are saved to 'filtered_stocks.json' for the strategy engine to use.

Usage:
    python premarket_filter.py
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional
from dhan_client import DhanClientWrapper
from strategy_engine import STOCK_LIST

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Filtration criteria
VOLUME_SMA_THRESHOLD = 2000
VOLUME_SMA_DIVISOR = 1875
REQUIRED_DAYS = 5


class PremarketFilter:
    """Handles premarket stock filtration based on volume SMA."""
    
    def __init__(self, dhan_client: DhanClientWrapper):
        self.dhan_client = dhan_client
        
    async def filter_single_stock(self, symbol: str) -> Optional[Tuple[str, float]]:
        """
        Filter a single stock based on volume SMA criteria.
        
        Args:
            symbol: Stock symbol to filter
            
        Returns:
            Tuple of (symbol, prev_close) if accepted, None if rejected
        """
        try:
            # Fetch historical data
            df = await self.dhan_client.get_historical_data_async(symbol, days=15)
            
            if df is None or df.empty or len(df) < REQUIRED_DAYS:
                logger.debug(f"REJECTED {symbol}: Insufficient data")
                return None
                
            # Get last 5 days
            last_5_days = df.tail(REQUIRED_DAYS)
            
            if 'volume' not in last_5_days.columns:
                logger.debug(f"REJECTED {symbol}: No volume data")
                return None
                
            # Calculate volume SMA
            total_volume_5d = last_5_days['volume'].sum()
            volume_sma = total_volume_5d / VOLUME_SMA_DIVISOR
            
            # Apply filter
            if volume_sma > VOLUME_SMA_THRESHOLD:
                prev_close = float(df.iloc[-1]['close'])
                logger.info(f"✓ ACCEPTED {symbol}: VolSMA={volume_sma:.2f}, PrevClose={prev_close:.2f}")
                return (symbol, prev_close)
            else:
                logger.debug(f"REJECTED {symbol}: VolSMA={volume_sma:.2f} (threshold: {VOLUME_SMA_THRESHOLD})")
                return None
                
        except Exception as e:
            logger.error(f"ERROR filtering {symbol}: {e}")
            return None
    
    async def filter_all_stocks(self, delay_between_stocks=1.2) -> Dict[str, float]:
        """
        Filter all stocks in STOCK_LIST using sequential processing with rate limiting.
        
        Args:
            delay_between_stocks: Delay in seconds between each stock (default: 1.2s)
        
        Returns:
            Dictionary mapping accepted symbols to their previous close prices
        """
        logger.info(f"Starting Volume SMA Filtration on {len(STOCK_LIST)} stocks...")
        logger.info(f"Criteria: Volume SMA > {VOLUME_SMA_THRESHOLD}")
        logger.info(f"Rate Limit: {delay_between_stocks}s delay between stocks")
        logger.info("=" * 70)
        
        accepted_stocks = {}
        total_stocks = len(STOCK_LIST)
        
        # Process stocks sequentially with rate limiting
        for idx, symbol in enumerate(STOCK_LIST, 1):
            # Progress indicator
            progress = (idx / total_stocks) * 100
            logger.info(f"[{idx}/{total_stocks}] ({progress:.1f}%) Processing {symbol}...")
            
            # Filter the stock
            result = await self.filter_single_stock(symbol)
            
            # Collect if accepted
            if result and isinstance(result, tuple):
                sym, prev_close = result
                accepted_stocks[sym] = prev_close
            
            # Rate limiting delay (except for last stock)
            if idx < total_stocks:
                await asyncio.sleep(delay_between_stocks)
        
        logger.info("=" * 70)
        logger.info(f"Filtration Complete: {len(accepted_stocks)} / {len(STOCK_LIST)} stocks accepted")
        return accepted_stocks
    
    def save_to_json(self, candidates: Dict[str, float], filepath: str = 'filtered_stocks.json'):
        """
        Save filtered candidates to JSON file.
        
        Args:
            candidates: Dictionary of symbol -> prev_close
            filepath: Path to save JSON file
        """
        data = {
            'timestamp': datetime.now().isoformat(),
            'criteria': {
                'volume_sma_threshold': VOLUME_SMA_THRESHOLD,
                'volume_sma_divisor': VOLUME_SMA_DIVISOR,
                'required_days': REQUIRED_DAYS
            },
            'total_stocks_screened': len(STOCK_LIST),
            'stocks_accepted': len(candidates),
            'candidates': candidates
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {len(candidates)} candidates to {filepath}")


async def main():
    """Main execution function."""
    logger.info("=" * 70)
    logger.info("PREMARKET STOCK FILTRATION - Volume SMA Filter")
    logger.info("=" * 70)
    
    # Load credentials
    import os
    from getpass import getpass
    
    # Try to load from environment variables first
    client_id = os.getenv('DHAN_CLIENT_ID')
    access_token = os.getenv('DHAN_ACCESS_TOKEN')
    
    # If not in environment, prompt user
    if not client_id or not access_token:
        logger.info("\nDhan API Credentials Required")
        logger.info("You can set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN environment variables")
        logger.info("or enter them now:\n")
        
        if not client_id:
            client_id = input("Enter Dhan Client ID: ").strip()
        if not access_token:
            access_token = getpass("Enter Dhan Access Token: ").strip()
    
    if not client_id or not access_token:
        logger.error("Credentials are required. Exiting.")
        return
    
    # Initialize Dhan client
    logger.info("Initializing Dhan client...")
    dhan_client = DhanClientWrapper()
    
    success, message = dhan_client.connect(client_id, access_token)
    if not success:
        logger.error(f"Failed to connect to Dhan API: {message}")
        logger.error("Please check your credentials and try again.")
        return
    
    logger.info("Dhan client connected successfully")
    
    # Run filtration
    filter_engine = PremarketFilter(dhan_client)
    candidates = await filter_engine.filter_all_stocks()
    
    # Save results
    filter_engine.save_to_json(candidates)
    
    # Print summary
    logger.info("=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total stocks screened: {len(STOCK_LIST)}")
    logger.info(f"Stocks accepted: {len(candidates)}")
    logger.info(f"Acceptance rate: {len(candidates)/len(STOCK_LIST)*100:.1f}%")
    
    if candidates:
        logger.info("\nAccepted Stocks:")
        for symbol, prev_close in sorted(candidates.items()):
            logger.info(f"  {symbol}: ₹{prev_close:.2f}")
    
    logger.info("=" * 70)
    logger.info("Filtration complete! You can now start the strategy engine.")


if __name__ == "__main__":
    asyncio.run(main())
