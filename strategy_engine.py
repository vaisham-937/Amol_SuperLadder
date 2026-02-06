import asyncio
import json
import logging
import os
from config import StrategySettings, StockStatus
from dhan_client import DhanClientWrapper
from order_manager import OrderManager
from performance_monitor import perf_monitor
import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo
from redis_store import load_candidates

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

STOCK_LIST = ['MRF','PAGEIND','BOSCHLTD','3MINDIA','HONAUT','ABBOTINDIA','SHREECEM','JSWHL','POWERINDIA',
    'PTCIL','FORCEMOT','MARUTI','NEULANDLAB','LMW','TVSHLTD','MAHSCOOTER','ZFCVINDIA','DIXON',
    'PGHH','SOLARINDS','ULTRACEMCO','BAJAJHLDNG','MCX','DYNAMATECH','ASTRAZEN','APARINDS',
    'BAJAJ-AUTO','GILLETTE','WENDT','TASTYBITE','VOLTAMP','OFSS','NUVAMA','POLYCAB','EICHERMOT',
    'APOLLOHOSP','CRAFTSMAN','NSIL','AMBER','DIVISLAB','PERSISTENT','LTIM','ESABINDIA',
    'NAVINFLUOR','ICRA','LINDEINDIA','HEROMOTOCO','ATUL','BRITANNIA','VSTTILLERS','JKCEMENT',
    'ALKEM','PGHL','LUMAXIND','BLUEDART','ABB','CERA','PILANIINVS','FOSECOIND','VADILALIND',
    'TATAELXSI','KICL','PFIZER','INDIGO','SUNDARMFIN','ORISSAMINE','LTTS','SANOFICONR',
    'CUMMINSIND','CRISIL','ECLERX','FINEORG','BAYERCROP','HAL','TVSSRICHAK','KAYNES','SANOFI',
    'TRENT','LT','KEI','SHILCTECH','BASF','TITAN','KINGFA','DMART','MUTHOOTFIN','SCHAEFFLER',
    'TORNTPHARM','SMLMAH','AIAENG','CEATLTD','SWARAJENG','GRWRHITECH','M&M','ESCORTS',
    'TVSMOTOR','BANARISUG','AKZOINDIA','INGERRAND','VHL','FLUOROCHEM','PIIND','KIRLOSIND',
    'KMEW','RADICO','SUPREMEIND','TCS','NETWEB','THANGAMAYL','SIEMENS','SHRIPISTON',
    'PRIVISCL','TIMKEN','GVT&D','ETHOSLTD','SRF','TCPLPACK','WAAREEENER','ANANDRATHI','NDGL',
    'MPHASIS','ENRIN','LALPATHLAB','THERMAX','GODFRYPHLP','GRASIM','BBL','ASIANPAINT','BSE',
    'HDFCAMC','CARTRADE','AJANTPHARM','BHARATRAS','TIINDIA','ENDURANCE','PRUDENT','AIIL',
    'GLAXO','ANGELONE','DATAPATTNS','DOMS','MAZDOCK','RATNAMANI','SHAILY','INTERARCH','GRSE',
    'HONDAPOWER','BALKRISIND','MTARTECH','HYUNDAI','JUBLCPL','COROMANDEL','RPGLIFE','KDDL',
    'CENTUM','FIEMIND','SAFARI','ADANIENT','NBIFIN','HINDUNILVR','POWERMECH','INDIAMART',
    'V2RETAIL','STYLAMIND','ANUP','TIIL','MANKIND','KOTAKBANK','MASTEK','COLPAL','LUPIN','E2E',
    'BHARTIARTL','BAJAJFINSV','GODREJPROP','DALBHARAT','STYRENIX','SBILIFE','MPSLTD',
    'GALAXYSURF','GLENMARK','SUMMITSEC','CAPLIPOINT','ICICIGI','CHOLAHLDNG','POLICYBZR','TEGA',
    'METROPOLIS','LGBBROSLTD','POLYMED','AUTOAXLES','NH','BBTC','COFORGE','GRAVITA','SKFINDIA',
    'CIGNITITEC','TATACOMM','JBCHEPHARM','BLUESTARCO','SUNPHARMA','GRPLTD','ACC','PHOENIXLTD',
    'APLAPOLLO','CHOLAFIN','MFSL','GKWLIMITED','SANSERA','BEML','AFFLE','BHARTIHEXA','GLAND',
    'ABREL','HCLTECH','ZOTA','SJS','ACUTAAS','PRESTIGE','OBEROIRLTY','TBOTEK','UBL','IKS',
    'MAPMYINDIA','BETA','KIRLOSBROS','VEEDOL','ONESOURCE','IFBIND','AZAD','HESTERBIO','TEAMLEASE',
    'COCHINSHIP','INDOTECH','THEJO','INFY','ALKYLAMINE','VINATIORGA','PGIL','GRINDWELL','TECHM',
    'YASHO','ERIS','LGEINDIA','AAVAS','BIRLANU','RELIANCE','CPPLUS','CARERATING','EIMCOELECO',
    'DEEPAKNTR','JINDALPHOT','CDSL','ADANIPORTS','PIRAMALFIN','CIPLA','SOLEX','HIRECT','ARMANFIN',
    'LUMAXTECH','PIDILITIND','IPCALAB','MIDWESTLTD','PIXTRANS','NPST','SOBHA','UNITDSPR',
    'EMCURE','TATVA','DPABHUSHAN','WELINV','JCHAC','BHARATFORG','RRKABEL','VENKEYS','NILKAMAL',
    'JLHL','VINDHYATEL','ASTRAL','EPIGRAL','BDL','HAVELLS','IMFA','ZENTEC','RAINBOW','NAUKRI',
    'VOLTAS','CONCORDBIO','ICICIBANK','RANEHOLDIN','MANORAMA','WOCKPHARMA','NGLFINE','ACCELYA',
    'ANURAS','PAYTM','POCL','TORNTPOWER','CREDITACC','LLOYDSME','TRAVELFOOD','AXISBANK','DRREDDY',
    'AMBIKCO','SUNCLAY','PUNJABCHEM','IFBAGRO','VENUSPIPES','UNOMINDA','WABAG','DCMSHRIRAM',
    'NESCO','NESTLEIND','KPITTECH','DEEPAKFERT','INDIGOPNTS','SASKEN','DODLA','SPECTRUM','OLECTRA',
    'DHANUKA','AUROPHARMA','APOLSINHOT','HOMEFIRST','KPIL','CYIENT','METROBRAND','DHUNINV',
    'GULFOILLUB','GODREJCP','MALLCOM','MEDANTA','AURIONPRO','TATACONSUM','UTIAMC','KIRLOSENG',
    '360ONE','INOXINDIA','RAYMONDLSL','JSWSTEEL','MGL','SIGNATURE','BALAMINES','LUXIND','GESHIP',
    'TECHNOE','NIBE','GOODLUCK','JPOLYINVST','LODHA','NEOGEN','DIAMONDYD','JUBLPHARMA','MAXHEALTH',
    'ADOR','GMMPFAUDLR','HAPPYFORGE','BIRLACORPN','INDIAGLYCO','SANDESH','TTKHLTCARE','CHEVIOT',
    'RAMCOCEM','KAJARIACER','PVRINOX','KFINTECH','TCI','RACLGEAR','KIRLPNU','ADANIGREEN','IMPAL',
    'EIDPARRY','DREDGECORP','INTELLECT','JINDALSTEL','SEAMECLTD','KERNEX','GRINFRA','CCL',
    'EXPLEOSOL','HATSUN','BAJFINANCE','GODREJIND','MACPOWER','LAURUSLABS','ADANIENSOL','WEALTH',
    'HDFCBANK','GROBTEA','GMBREW','SUDARSCHEM','ENTERO','ASAHIINDIA','RPEL','AJMERA','VIJAYA',
    'DSSL','KPRMILL','AUBANK','KSCL','GABRIEL','XPROINDIA','SBIN','GLOBUSSPR','BATAINDIA','ASALCBR',
    'AHLUCONT','JYOTICNC','SHARDAMOTR','WAAREERTL','MAITHANALL','UNIMECH','PNBHOUSING','SUNDRMFAST',
    'ELDEHSG','ACE','ARE&M','ZYDUSLIFE','EXCELINDUS','CARYSIL','CHENNPETRO','WHIRLPOOL','ATLANTAELE',
    'NUCLEUS','PREMIERENE','SHARDACROP','CANFINHOME','CLEAN','ASTRAMICRO','NATCOPHARM','KAUSHALYA',
   ]
class LadderEngine:
    def __init__(self, dhan_client: DhanClientWrapper):
        self.dhan_client = dhan_client
        self.order_manager = OrderManager(dhan_client)
        self.settings = StrategySettings()
        self.active_stocks: Dict[str, StockStatus] = {}
        self.started_symbols = set()
        self.running = False
        self.pnl_global = 0.0
        
        # Cache for performance
        self.filtered_stocks_cache = None
        self.cache_timestamp = None
        
        # Pre-calculate multipliers
        self._update_multipliers()

    def _update_multipliers(self):
        """Pre-calculate percentage multipliers for performance."""
        self.add_on_mult = self.settings.add_on_percentage / 100
        self.init_sl_mult = self.settings.initial_stop_loss_pct / 100
        self.tsl_mult = self.settings.trailing_stop_loss_pct / 100
        self.target_mult = self.settings.target_percentage / 100

    def update_settings(self, new_settings: StrategySettings):
        new_settings = self._normalize_settings(new_settings)
        self.settings = new_settings
        self._update_multipliers()
        # Avoid logging sensitive tokens
        safe_settings = self.settings.model_dump()
        if safe_settings.get("access_token"):
            safe_settings["access_token"] = "***"
        logger.info(f"Settings Updated: {safe_settings}")

    def _normalize_settings(self, settings: StrategySettings) -> StrategySettings:
        """Clamp/adjust settings to avoid invalid combinations from UI."""
        try:
            max_ladders = int(settings.max_ladder_stocks or 0)
        except Exception:
            max_ladders = 0

        try:
            top_gainers = int(settings.top_n_gainers or 0)
        except Exception:
            top_gainers = 0

        try:
            top_losers = int(settings.top_n_losers or 0)
        except Exception:
            top_losers = 0

        max_ladders = max(1, max_ladders)
        top_gainers = max(0, top_gainers)
        top_losers = max(0, top_losers)

        # Rule: top_gainers + top_losers must not exceed max_ladders (when max_ladders > 0)
        if max_ladders > 0 and (top_gainers + top_losers) > max_ladders:
            # Prefer keeping gainers as-is and reduce losers first.
            top_losers = max(0, max_ladders - top_gainers)
            if top_losers == 0 and top_gainers > max_ladders:
                top_gainers = max_ladders

        return settings.model_copy(
            update={
                "max_ladder_stocks": max_ladders,
                "top_n_gainers": top_gainers,
                "top_n_losers": top_losers,
            }
        )

    def is_market_hours(self) -> bool:
        """Check if current time is within market hours."""
        now = datetime.now(IST).time()
        market_open = dt_time(9, 15)
        market_close = dt_time(15, 30)  # Market closes at 3:30 PM
        return market_open <= now <= market_close

    async def start_strategy(self):
        if not self.dhan_client.is_connected:
            logger.error("Cannot start: Dhan client not connected")
            return

        # If market is closed, don't start WebSocket feed; dashboard will use REST top-movers.
        if not self.is_market_hours():
            logger.info("Market closed - not starting WebSocket feed (use Top Movers API fallback)")
            self.running = False
            return

        self.running = True
        # Reset per-run state (so max ladder stocks applies per session)
        self.started_symbols.clear()
        logger.info("Strategy Engine Started")
        
        # Load pre-filtered stocks from JSON
        candidates_map = self.load_filtered_stocks()
        if not candidates_map:
            logger.error("No filtered stocks available. Run premarket_filter.py first!")
            self.running = False
            return
            
        candidates = list(candidates_map.keys())
        logger.info(f"Loaded {len(candidates)} pre-filtered candidates from filtered_stocks.json")
        
        # Subscribe to WebSocket
        self.dhan_client.subscribe(candidates, self.process_tick)
        
        # Initialize stocks in tracking dict
        for symbol in candidates:
            self.active_stocks[symbol] = StockStatus(
                symbol=symbol,
                mode="NONE",
                ltp=0.0,
                change_pct=0.0,
                pnl=0.0,
                status="IDLE",
                entry_price=0.0,
                quantity=0,
                ladder_level=0,
                next_add_on=0.0,
                stop_loss=0.0,
                target=0.0,
                prev_close=candidates_map[symbol],
                high_watermark=0.0
            )

        # Main loop
        while self.running:
            await asyncio.sleep(1)
            self.calculate_pnl()
            
            # Auto square-off at 3:20 PM
            if not self.is_market_hours() and self.running:
                logger.info("Market closed - Auto square-off triggered")
                await self.square_off_all()
                # Stop feed to avoid reconnect storms after market close
                self.dhan_client.stop_feed()
                self.running = False

    def process_tick(self, symbol: str, ltp: float, volume: float = 0.0):
        """Process incoming tick data with performance tracking."""
        import time
        start_time = time.time()
        
        if not self.running or symbol not in self.active_stocks:
            return

        stock = self.active_stocks[symbol]
        
        if stock.status == "STOPPED" or stock.status.startswith("CLOSED"):
            return

        # Update LTP and turnover
        stock.ltp = ltp
        if volume > 0:
            stock.turnover = volume * ltp
            
        # Calculate % Change
        if stock.prev_close > 0:
            stock.change_pct = ((ltp - stock.prev_close) / stock.prev_close) * 100
        
        # Update high watermark for trailing SL
        if stock.mode != "NONE":
            if stock.mode == "LONG" and ltp > stock.high_watermark:
                stock.high_watermark = ltp
            elif stock.mode == "SHORT" and (stock.high_watermark == 0 or ltp < stock.high_watermark):
                stock.high_watermark = ltp
        
        # Calculate P&L using average entry price
        if stock.mode != "NONE" and stock.quantity > 0:
            avg_price = self.order_manager.calculate_average_entry(symbol, "BUY" if stock.mode == "LONG" else "SELL")
            if avg_price > 0:
                stock.avg_entry_price = avg_price
                if stock.mode == "LONG":
                    stock.pnl = (ltp - avg_price) * stock.quantity
                else:
                    stock.pnl = (avg_price - ltp) * stock.quantity

        # Trading Logic
        if stock.mode == "LONG":
            self._process_long_position(stock)
        elif stock.mode == "SHORT":
            self._process_short_position(stock)
        
        # Global P&L Limits
        if abs(stock.pnl) > self.settings.profit_target_per_stock:
            self.close_position(stock, "Max Profit/Loss Reached")
            stock.status = "CLOSED_GlobalLimit"
        
        # Record performance
        latency_ms = (time.time() - start_time) * 1000
        perf_monitor.record_tick_latency(latency_ms)

    def _process_long_position(self, stock: StockStatus):
        """Process LONG position logic."""
        # 1. Check Target
        if stock.ltp >= stock.target:
            self.close_position(stock, "Target Hit")
            stock.status = "CLOSED_PROFIT"
            return

        # 2. Check Stop Loss / TSL
        if stock.ltp <= stock.stop_loss:
            self.close_position(stock, "SL Hit")
            # BIDIRECTIONAL: Flip to Short
            self.start_short_ladder(stock)
            return

        # 3. Add-on Logic (Pyramiding)
        if stock.ladder_level < self.settings.no_of_add_ons:
            if stock.ltp >= stock.next_add_on:
                self.execute_add_on(stock, "LONG")
        
        # 4. Update Trailing SL using high watermark
        if stock.high_watermark > 0:
            dynamic_sl = stock.high_watermark * (1 - self.tsl_mult)
            if dynamic_sl > stock.stop_loss:
                stock.stop_loss = dynamic_sl

    def _process_short_position(self, stock: StockStatus):
        """Process SHORT position logic."""
        # 1. Check Target
        if stock.ltp <= stock.target:
            self.close_position(stock, "Target Hit")
            stock.status = "CLOSED_PROFIT"
            return

        # 2. Check SL
        if stock.ltp >= stock.stop_loss:
            self.close_position(stock, "SL Hit")
            # BIDIRECTIONAL: Flip to Long
            self.start_long_ladder(stock)
            return

        # 3. Add-on Logic
        if stock.ladder_level < self.settings.no_of_add_ons:
            if stock.ltp <= stock.next_add_on:
                self.execute_add_on(stock, "SHORT")
        
        # 4. TSL
        if stock.high_watermark > 0:
            dynamic_sl = stock.high_watermark * (1 + self.tsl_mult)
            if dynamic_sl < stock.stop_loss or stock.stop_loss == 0:
                stock.stop_loss = dynamic_sl

    def execute_add_on(self, stock: StockStatus, mode: str):
        """Execute add-on order with tracking."""
        import time
        start_time = time.time()
        
        # Calculate quantity
        qty = max(1, int(self.settings.trade_capital / stock.entry_price)) if stock.entry_price > 0 else 1
        
        logger.info(f"Executing ADD-ON for {stock.symbol} ({mode}) Qty: {qty}")
        
        transaction_type = "BUY" if mode == "LONG" else "SELL"
        
        # Create order in order manager
        order = self.order_manager.create_order(
            symbol=stock.symbol,
            transaction_type=transaction_type,
            quantity=qty,
            order_type="MARKET"
        )
        
        # Place order
        response = self.dhan_client.place_order(
            symbol=stock.symbol,
            exchange_segment="NSE_EQ",
            transaction_type=transaction_type,
            quantity=qty,
            order_type="MARKET",
            product_type="INTRADAY"
        )
        
        if response and response.get('status') != 'failure':
            # Update order status
            order_id = response.get('orderId', order.order_id)
            self.order_manager.replace_order_id(order.order_id, str(order_id))
            self.order_manager.update_order_status(
                str(order_id),
                "EXECUTED",
                executed_price=stock.ltp,
                executed_quantity=qty
            )
            
            stock.quantity += qty
            stock.ladder_level += 1
            stock.order_ids.append(str(order_id))
            
            if mode == "LONG":
                stock.next_add_on = stock.ltp * (1 + self.add_on_mult)
            else:
                stock.next_add_on = stock.ltp * (1 - self.add_on_mult)
            
            logger.info(f"Pyramiding {stock.symbol}: Level {stock.ladder_level}, New Qty: {stock.quantity}")
        
        latency_ms = (time.time() - start_time) * 1000
        perf_monitor.record_order_latency(latency_ms)

    def close_position(self, stock: StockStatus, reason: str):
        """Close position with order tracking."""
        logger.info(f"Closing {stock.symbol}: {reason}")
        
        if stock.quantity > 0:
            transaction_type = "SELL" if stock.mode == "LONG" else "BUY"
            
            order = self.order_manager.create_order(
                symbol=stock.symbol,
                transaction_type=transaction_type,
                quantity=stock.quantity,
                order_type="MARKET"
            )
            
            response = self.dhan_client.place_order(
                symbol=stock.symbol,
                exchange_segment="NSE_EQ",
                transaction_type=transaction_type,
                quantity=stock.quantity,
                order_type="MARKET",
                product_type="INTRADAY"
            )
            
            if response:
                order_id = response.get('orderId', order.order_id)
                self.order_manager.replace_order_id(order.order_id, str(order_id))
                self.order_manager.update_order_status(
                    str(order_id),
                    "EXECUTED",
                    executed_price=stock.ltp,
                    executed_quantity=stock.quantity
                )
            
        stock.quantity = 0
        stock.mode = "NONE"

    def start_long_ladder(self, stock: StockStatus):
        """Start LONG ladder with order tracking."""
        if stock.symbol not in self.started_symbols and len(self.started_symbols) >= self.settings.max_ladder_stocks:
            logger.info(
                f"SKIP LONG {stock.symbol}: max ladder stocks reached "
                f"({len(self.started_symbols)}/{self.settings.max_ladder_stocks})"
            )
            return

        logger.info(f"Starting LONG Ladder for {stock.symbol}")
        
        qty = max(1, int(self.settings.trade_capital / stock.ltp)) if stock.ltp > 0 else 1
        
        order = self.order_manager.create_order(
            symbol=stock.symbol,
            transaction_type="BUY",
            quantity=qty,
            order_type="MARKET"
        )
        
        resp = self.dhan_client.place_order(
            symbol=stock.symbol,
            exchange_segment="NSE_EQ",
            transaction_type="BUY",
            quantity=qty,
            order_type="MARKET",
            product_type="INTRADAY"
        )
        
        if resp and resp.get('status') == 'failure':
            logger.error(f"Failed to start LONG ladder for {stock.symbol}: {resp}")
            return

        self.started_symbols.add(stock.symbol)

        # Update order status
        if resp:
            order_id = resp.get('orderId', order.order_id)
            self.order_manager.replace_order_id(order.order_id, str(order_id))
            self.order_manager.update_order_status(
                str(order_id),
                "EXECUTED",
                executed_price=stock.ltp,
                executed_quantity=qty
            )
            stock.order_ids.append(str(order_id))

        stock.mode = "LONG"
        stock.status = "ACTIVE"
        stock.ladder_level = 1
        stock.entry_price = stock.ltp
        stock.avg_entry_price = stock.ltp
        stock.quantity = qty
        stock.high_watermark = stock.ltp
        
        stock.stop_loss = stock.ltp * (1 - self.init_sl_mult)
        stock.target = stock.ltp * (1 + self.target_mult)
        stock.next_add_on = stock.ltp * (1 + self.add_on_mult)

    def start_short_ladder(self, stock: StockStatus):
        """Start SHORT ladder with order tracking."""
        if stock.symbol not in self.started_symbols and len(self.started_symbols) >= self.settings.max_ladder_stocks:
            logger.info(
                f"SKIP SHORT {stock.symbol}: max ladder stocks reached "
                f"({len(self.started_symbols)}/{self.settings.max_ladder_stocks})"
            )
            return

        logger.info(f"Starting SHORT Ladder for {stock.symbol}")
        
        qty = max(1, int(self.settings.trade_capital / stock.ltp)) if stock.ltp > 0 else 1
        
        order = self.order_manager.create_order(
            symbol=stock.symbol,
            transaction_type="SELL",
            quantity=qty,
            order_type="MARKET"
        )
        
        resp = self.dhan_client.place_order(
            symbol=stock.symbol,
            exchange_segment="NSE_EQ",
            transaction_type="SELL",
            quantity=qty,
            order_type="MARKET",
            product_type="INTRADAY"
        )
        
        if resp and resp.get('status') == 'failure':
            logger.error(f"Failed to start SHORT ladder for {stock.symbol}: {resp}")
            return

        self.started_symbols.add(stock.symbol)

        if resp:
            order_id = resp.get('orderId', order.order_id)
            self.order_manager.replace_order_id(order.order_id, str(order_id))
            self.order_manager.update_order_status(
                str(order_id),
                "EXECUTED",
                executed_price=stock.ltp,
                executed_quantity=qty
            )
            stock.order_ids.append(str(order_id))

        stock.mode = "SHORT"
        stock.status = "ACTIVE"
        stock.ladder_level = 1
        stock.entry_price = stock.ltp
        stock.avg_entry_price = stock.ltp
        stock.quantity = qty
        stock.high_watermark = stock.ltp
        
        stock.stop_loss = stock.ltp * (1 + self.init_sl_mult)
        stock.target = stock.ltp * (1 - self.target_mult)
        stock.next_add_on = stock.ltp * (1 - self.add_on_mult)

    def calculate_pnl(self):
        """Calculate total P&L using NumPy for performance."""
        pnl_values = [s.pnl for s in self.active_stocks.values()]
        self.pnl_global = np.sum(pnl_values) if pnl_values else 0.0
        
        # Periodic ranking
        self.select_top_movers()

    def select_top_movers(self):
        """Rank stocks and activate ladders for top movers."""
        min_turnover = self.settings.min_turnover_crores * 10000000

        logger.info(
            f"Selecting movers: min_turnover={self.settings.min_turnover_crores:.2f} Cr "
            f"({min_turnover:.0f})"
        )
        
        active_longs = 0
        active_shorts = 0
        for s in self.active_stocks.values():
            if s.quantity <= 0:
                continue
            if s.mode == "LONG":
                active_longs += 1
            elif s.mode == "SHORT":
                active_shorts += 1

        active_total = active_longs + active_shorts
        max_ladders = max(1, int(self.settings.max_ladder_stocks or 0))

        if len(self.started_symbols) >= max_ladders:
            logger.info(
                f"Max ladder stocks reached for session ({len(self.started_symbols)}/{max_ladders}) "
                f"- not starting new symbols"
            )
            return

        if active_total >= max_ladders:
            logger.info(
                f"Max ladder stocks reached ({active_total}/{max_ladders}) - not starting new ladders"
            )
            return

        # Only start as many as needed to reach configured targets.
        need_longs = max(0, int(self.settings.top_n_gainers or 0) - active_longs)
        need_shorts = max(0, int(self.settings.top_n_losers or 0) - active_shorts)

        remaining_capacity = max(0, max_ladders - active_total)
        if (need_longs + need_shorts) > remaining_capacity:
            # Keep longs priority, then shorts, under remaining capacity.
            need_longs = min(need_longs, remaining_capacity)
            need_shorts = min(need_shorts, max(0, remaining_capacity - need_longs))

        if need_longs <= 0 and need_shorts <= 0:
            logger.info(
                f"No new ladders needed (active_longs={active_longs}/{self.settings.top_n_gainers}, "
                f"active_shorts={active_shorts}/{self.settings.top_n_losers}, "
                f"max={max_ladders})"
            )
            return

        idle_stocks = []
        for s in self.active_stocks.values():
            if s.status != "IDLE":
                continue
            if s.ltp <= 0:
                logger.debug(f"FILTERED {s.symbol}: LTP<=0 (ltp={s.ltp})")
                continue
            if s.turnover < min_turnover:
                logger.debug(
                    f"FILTERED {s.symbol}: Turnover below threshold "
                    f"(turnover={s.turnover:.0f}, min={min_turnover:.0f})"
                )
                continue
            idle_stocks.append(s)
        
        if not idle_stocks:
            logger.info("No eligible idle stocks after turnover/LTP filters")
            return
            
        long_candidates = [s for s in idle_stocks if s.change_pct > 0]
        short_candidates = [s for s in idle_stocks if s.change_pct < 0]

        # Sort by % Change
        long_candidates.sort(key=lambda x: x.change_pct, reverse=True)
        short_candidates.sort(key=lambda x: x.change_pct)  # Most negative first

        top_gainers = long_candidates[:need_longs] if need_longs > 0 else []
        top_losers = short_candidates[:need_shorts] if need_shorts > 0 else []

        if top_gainers:
            logger.info(
                "Top Gainers (selected): " + ", ".join(
                    f"{s.symbol}({s.change_pct:.2f}%, turnover={s.turnover/10000000:.2f}Cr)"
                    for s in top_gainers
                )
            )
        if top_losers:
            logger.info(
                "Top Losers (selected): " + ", ".join(
                    f"{s.symbol}({s.change_pct:.2f}%, turnover={s.turnover/10000000:.2f}Cr)"
                    for s in top_losers
                )
            )

        for stock in top_gainers:
            logger.info(f"Activating LONG: {stock.symbol} ({stock.change_pct:.2f}%)")
            self.start_long_ladder(stock)

        for stock in top_losers:
            logger.info(f"Activating SHORT: {stock.symbol} ({stock.change_pct:.2f}%)")
            self.start_short_ladder(stock)

    def load_filtered_stocks(self, filepath: str = 'filtered_stocks.json') -> Dict[str, float]:
        """
        Load pre-filtered stocks from JSON file generated by premarket_filter.py.
        
        Args:
            filepath: Path to the filtered stocks JSON file
            
        Returns:
            Dictionary mapping symbols to their previous close prices
        """
        # Try Redis first (same-day cache)
        cached = load_candidates()
        if cached and cached.get("candidates"):
            candidates = cached.get("candidates", {})
            timestamp = cached.get("timestamp", "unknown")
            logger.info(f"Loaded {len(candidates)} filtered stocks from Redis")
            logger.info(f"Filter timestamp: {timestamp}")
            return candidates

        if not os.path.exists(filepath):
            logger.error(f"Filtered stocks file not found: {filepath}")
            logger.error("Please run 'python premarket_filter.py' before starting the strategy engine")
            return {}
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            candidates = data.get('candidates', {})
            timestamp = data.get('timestamp', 'unknown')
            
            logger.info(f"Loaded {len(candidates)} filtered stocks from {filepath}")
            logger.info(f"Filter timestamp: {timestamp}")
            
            return candidates
            
        except Exception as e:
            logger.error(f"Error loading filtered stocks: {e}")
            return {}


    async def square_off_all(self):
        """Emergency square-off all positions."""
        logger.warning("SQUARE OFF ALL triggered")
        
        for stock in self.active_stocks.values():
            if stock.mode != "NONE" and stock.quantity > 0:
                self.close_position(stock, "Emergency Square-off")
                stock.status = "CLOSED_EMERGENCY"
        
        logger.info("All positions squared off")
