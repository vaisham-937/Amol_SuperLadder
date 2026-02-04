import logging
import pandas as pd
from datetime import datetime, timedelta
from dhanhq import dhanhq
from dhanhq import marketfeed
import time
import requests
import io
import threading
import asyncio
from functools import lru_cache
from collections import deque
import ujson
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

try:
    import ujson as json
except ImportError:
    import json

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for API calls."""
    
    def __init__(self, max_requests_per_second=1.0, max_connections=5):
        """
        Initialize rate limiter.
        
        Args:
            max_requests_per_second: Maximum API requests per second (default: 1)
            max_connections: Maximum concurrent connections (default: 5)
        """
        self.max_requests_per_second = max_requests_per_second
        self.max_connections = max_connections
        self.tokens = max_requests_per_second
        self.last_update = time.time()
        self.lock = threading.Lock()
        self.active_connections = 0
        self.connection_lock = threading.Lock()
        
        logger.info(f"RateLimiter initialized: {max_requests_per_second} req/sec, {max_connections} max connections")
    
    def acquire(self, retry_on_limit=True, max_retries=3):
        """
        Acquire a token to make an API request.
        Blocks until a token is available.
        
        Args:
            retry_on_limit: Whether to retry on rate limit
            max_retries: Maximum number of retries
        
        Returns:
            True if token acquired, False if max retries exceeded
        """
        retries = 0
        
        while retries < max_retries:
            with self.lock:
                # Refill tokens based on time elapsed
                now = time.time()
                elapsed = now - self.last_update
                self.tokens = min(
                    self.max_requests_per_second,
                    self.tokens + elapsed * self.max_requests_per_second
                )
                self.last_update = now
                
                # Check if we have a token available
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return True
                
                # Calculate wait time
                wait_time = (1.0 - self.tokens) / self.max_requests_per_second
            
            # If not retrying, return False
            if not retry_on_limit:
                return False
            
            # Wait and retry
            logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s (attempt {retries + 1}/{max_retries})")
            time.sleep(wait_time)
            retries += 1
        
        logger.warning(f"Max retries ({max_retries}) exceeded for rate limiter")
        return False
    
    def acquire_connection(self):
        """Acquire a connection slot. Blocks until available."""
        while True:
            with self.connection_lock:
                if self.active_connections < self.max_connections:
                    self.active_connections += 1
                    return
            time.sleep(0.1)
    
    def release_connection(self):
        """Release a connection slot."""
        with self.connection_lock:
            self.active_connections = max(0, self.active_connections - 1)

class DhanClientWrapper:
    def __init__(self, max_requests_per_second=1.0, max_connections=5):
        """
        Initialize Dhan client wrapper with rate limiting.
        
        Args:
            max_requests_per_second: Max API requests per second (default: 1.0)
            max_connections: Max concurrent connections (default: 5)
        """
        self.dhan: dhanhq = None
        self.client_id = None
        self.access_token = None
        self.is_connected = False
        self.symbol_map = {}
        self.id_map = {}
        self.feed = None
        self.ws_thread = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5
        
        # Rate limiting
        self.rate_limiter = RateLimiter(
            max_requests_per_second=max_requests_per_second,
            max_connections=max_connections
        )
        
        # Performance optimizations
        self.tick_batch = []
        self.tick_batch_lock = threading.Lock()
        self.last_batch_process = time.time()
        self.batch_interval = 0.1  # 100ms batching

    def connect(self, client_id, access_token):
        """Connects to Dhan API."""
        try:
            self.dhan = dhanhq(client_id, access_token)
            self.client_id = client_id
            self.access_token = access_token
            
            # Verify connection by fetching something simple
            self.dhan.get_fund_limits() 
            self.is_connected = True
            logger.info("Connected to Dhan API Successfully")
            
            # Fetch Security Master
            self.fetch_security_mapping()
            
            # Build reverse mapping for fast lookups
            self._build_reverse_mapping()
            
            return True, "Connected"
        except Exception as e:
            self.is_connected = False
            logger.error(f"Failed to connect to Dhan: {e}")
            return False, str(e)

    def fetch_security_mapping(self):
        """Fetches Dhan Scrip Master to map symbols to Security IDs."""
        try:
            url = "https://images.dhan.co/api-data/api-scrip-master.csv"
            logger.info("Fetching Security Master CSV...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            
            df = pd.read_csv(io.StringIO(r.text))
            
            # Filter for NSE Equity
            equity_df = df[
                (df['SEM_EXM_EXCH_ID'] == 'NSE') & 
                (df['SEM_INSTRUMENT_NAME'] == 'EQUITY')
            ]
            
            if equity_df.empty:
                logger.warning("No NSE Equity records found, trying broad filter")
                equity_df = df
            
            # Create symbol mapping
            self.symbol_map = dict(zip(
                equity_df['SEM_TRADING_SYMBOL'], 
                equity_df['SEM_SMST_SECURITY_ID']
            ))
            
            logger.info(f"Loaded {len(self.symbol_map)} security mappings")
            
        except Exception as e:
            logger.error(f"Failed to fetch Security Master: {e}")

    def _build_reverse_mapping(self):
        """Build reverse mapping for O(1) lookups."""
        # Keep IDs as integers in reverse mapping
        self.id_map = {int(v): k for k, v in self.symbol_map.items()}
        logger.info(f"Built reverse mapping with {len(self.id_map)} entries")

    @lru_cache(maxsize=1000)
    def get_security_id(self, symbol):
        """Returns Security ID for a symbol as an integer (cached)."""
        # Try direct match
        if symbol in self.symbol_map:
            return int(self.symbol_map[symbol])
            
        # Try appending '-EQ'
        if f"{symbol}-EQ" in self.symbol_map:
             return int(self.symbol_map[f"{symbol}-EQ"])
             
        return None

    def subscribe(self, symbols, callback):
        """Subscribes to real-time feed for the list of symbols."""
        if not self.is_connected:
            logger.error("Cannot subscribe: Not connected")
            return
        
        # CRITICAL: Validate credentials before attempting WebSocket connection
        if not self.client_id or not self.access_token:
            logger.error(f"Cannot subscribe: Missing credentials (client_id={bool(self.client_id)}, access_token={bool(self.access_token)})")
            return
        
        logger.info(f"WebSocket will use: client_id={self.client_id[:10]}..., access_token={'*' * len(self.access_token) if self.access_token else 'NONE'}")

        try:
            logger.info(f"Subscribing to {len(symbols)} symbols...")
            
            # Map symbols to IDs (as integers, then convert to string for websocket subscription)
            sub_list = []
            for s in symbols:
                sid = self.get_security_id(s)  # Returns int
                if sid:
                    sub_list.append(str(sid))  # Convert to string for WebSocket
                else:
                    logger.warning(f"Could not map {s} for subscription")

            if not sub_list:
                logger.warning("No valid symbols to subscribe")
                return

            # Prepare instruments list
            # NSE = 1, BSE = 2 (Dhan API constants)
            exch_code = 1  # NSE
            instruments = [(exch_code, sid) for sid in sub_list]
            
            logger.info(f"Starting DhanFeed for {len(instruments)} instruments")
            
            # Initialize Feed
            self.feed = marketfeed.DhanFeed(
                self.client_id, 
                self.access_token, 
                instruments
            )
            
            # Store callback for reconnection
            self._callback = callback
            
            # Set callbacks
            self.feed.on_connect = self._on_ws_connect
            self.feed.on_message = lambda tick: self._on_tick(tick, callback)
            self.feed.on_error = self._on_ws_error
            self.feed.on_close = self._on_ws_close
            
            # CRITICAL FIX: Use asyncio.run() to properly handle event loop
            # This creates a fresh event loop in the thread and runs it to completion
            def run_feed_in_thread():
                """Run DhanFeed in separate thread using asyncio.run()."""
                import asyncio
                
                # Try to import nest_asyncio if available (helps with nested loops)
                try:
                    import nest_asyncio
                    nest_asyncio.apply()
                    logger.info("Applied nest_asyncio for better compatibility")
                except ImportError:
                    logger.warning("nest_asyncio not available, continuing without it")
                except Exception as e:
                    logger.warning(f"Could not apply nest_asyncio: {e}")
                
                # Create new loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Connect and run the WebSocket
                    loop.run_until_complete(self.feed.connect())
                    logger.info("Dhan WebSocket Connected Successfully")
                    # Keep the connection alive
                    loop.run_forever()
                except Exception as e:
                    logger.error(f"WebSocket error in thread: {e}", exc_info=True)
                finally:
                    loop.close()
            
            self.ws_thread = threading.Thread(target=run_feed_in_thread, daemon=True)
            self.ws_thread.start()
            
            logger.info("WebSocket Thread Started")
            
        except Exception as e:
            logger.error(f"Subscription failed: {e}")

    def _on_ws_connect(self, instance):
        logger.info("Dhan WebSocket Connected")
        self.reconnect_attempts = 0

    def _on_ws_error(self, instance, error):
        logger.error(f"Dhan WebSocket Error: {error}")

    def _on_ws_close(self, instance):
        logger.warning("Dhan WebSocket Closed")
        self._handle_reconnect()

    def _handle_reconnect(self):
        """Handle WebSocket reconnection with exponential backoff."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return
            
        self.reconnect_attempts += 1
        delay = self.reconnect_delay * (2 ** (self.reconnect_attempts - 1))
        delay = min(delay, 60)  # Cap at 60 seconds
        
        logger.info(f"Attempting reconnection in {delay}s (attempt {self.reconnect_attempts})")
        time.sleep(delay)
        
        try:
            if hasattr(self, '_callback') and hasattr(self, '_instruments'):
                self.subscribe(self._instruments, self._callback)
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")

    def _on_tick(self, tick_data, callback):
        """Process tick data with batching for performance."""
        start_time = time.time()
        
        try:
            # Check for LTP
            if 'LTP' in tick_data and 'security_id' in tick_data:
                sid = int(tick_data['security_id'])
                ltp = float(tick_data['LTP'])
                
                # Extract Volume
                volume = 0.0
                if 'volume' in tick_data:
                    volume = float(tick_data['volume'])
                elif 'total_volume' in tick_data:
                    volume = float(tick_data['total_volume'])
                
                # Get symbol from reverse mapping
                symbol = self.id_map.get(sid)
                if symbol:
                    try:
                        # Call callback directly for low latency
                        callback(symbol, ltp, volume)
                        
                        # Record performance
                        latency_ms = (time.time() - start_time) * 1000
                        if latency_ms > 10:  # Log only if > 10ms
                            logger.debug(f"Tick processing took {latency_ms:.2f}ms")
                            
                    except TypeError:
                        # Fallback for old signature
                        callback(symbol, ltp)
                    
        except Exception as e:
            logger.error(f"Tick processing error: {e}")

    async def get_historical_data_async(self, symbol, exchange_segment="NSE_EQ", days=15):
        """Async version of historical data fetching."""
        # For now, call sync version in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.get_historical_data, 
            symbol, 
            exchange_segment, 
            days
        )

    def get_historical_data(self, symbol, exchange_segment="NSE_EQ", days=15):
        """Fetches historical data for the last N days with rate limiting."""
        if not self.is_connected:
            return None

        try:
            # Acquire rate limit token
            if not self.rate_limiter.acquire():
                logger.error(f"Rate limit exceeded for {symbol}, skipping")
                return None
            
            # Acquire connection slot
            self.rate_limiter.acquire_connection()
            
            try:
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=days)
                
                security_id = self.get_security_id(symbol)
                if not security_id:
                    logger.error(f"Security ID not found for {symbol}")
                    return None
                
                # DEBUG: Log what we're about to send
                logger.debug(f"Fetching history for {symbol}: security_id={security_id} (type={type(security_id).__name__})")
                
                # According to Dhan SDK documentation:
                # exchange_segment should be string: "NSE_EQ", "BSE_EQ", etc.
                # NOT integer
                response = self.dhan.historical_daily_data(
                    security_id=str(security_id),  # SDK expects string
                    exchange_segment=exchange_segment,  # Use string like "NSE_EQ"
                    instrument_type="EQUITY",
                    from_date=start_date.strftime("%Y-%m-%d"),
                    to_date=end_date.strftime("%Y-%m-%d")
                )
                
                if response.get('status') == 'success':
                    data = response.get('data')
                    df = pd.DataFrame(data)
                    return df
                else:
                    logger.error(f"Failed to fetch history for {symbol}: {response}")
                    return None
                    
            finally:
                # Always release connection
                self.rate_limiter.release_connection()
                
        except Exception as e:
            logger.error(f"Exception fetching history for {symbol}: {e}")
            return None

    def place_order(self, symbol, transaction_type, quantity, 
                   exchange_segment="NSE_EQ", product_type="INTRADAY", 
                   order_type="MARKET"):
        """Places a market order with timing."""
        if not self.is_connected:
            return None
        
        start_time = time.time()
        
        try:
            security_id = self.get_security_id(symbol)
            if not security_id:
                logger.error(f"Cannot place order: Security ID not found for {symbol}")
                return None

            # According to Dhan SDK:
            # security_id: string
            # exchange_segment: string like "NSE_EQ", "BSE_EQ"
            # transaction_type: string "BUY" or "SELL"  
            # order_type: string "MARKET" or "LIMIT"
            # product_type: string "INTRADAY" or "CNC"
            # quantity: integer
            # price: float (0 for market orders)
            
            response = self.dhan.place_order(
                security_id=str(security_id),
                exchange_segment=exchange_segment,  # Use "NSE_EQ" directly
                transaction_type=transaction_type,   # Use "BUY"/"SELL" directly
                quantity=int(quantity),
                order_type=order_type,               # Use "MARKET"/"LIMIT" directly  
                product_type=product_type,           # Use "INTRADAY"/"CNC" directly
                price=0.0 if order_type == "MARKET" else 0.0
            )
            
            latency_ms = (time.time() - start_time) * 1000
            logger.info(f"Order Placed in {latency_ms:.2f}ms: {symbol} {transaction_type} {quantity} -> {response}")
            
            return response
            
        except Exception as e:
            logger.error(f"Order Placement Failed: {e}")
            return None

    def get_positions(self):
        """Fetch current positions from Dhan."""
        if not self.is_connected:
            return []
        
        try:
            response = self.dhan.get_positions()
            if response.get('status') == 'success':
                return response.get('data', [])
            return []
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            return []

    def square_off_position(self, symbol, quantity, transaction_type):
        """Square off a position."""
        opposite_type = "SELL" if transaction_type == "BUY" else "BUY"
        return self.place_order(
            symbol=symbol,
            transaction_type=opposite_type,
            quantity=quantity,
            order_type="MARKET",
            product_type="INTRADAY"
        )
