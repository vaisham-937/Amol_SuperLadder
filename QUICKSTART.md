# Quick Start Guide - Dhan Ultra-Ladder Trading Application

## Application Overview

This is a production-ready, low-latency algorithmic trading application for the Dhan platform featuring:
- **WebSocket Live Data Streaming** - Real-time tick data with <10ms latency
- **Ladder Pyramiding Strategy** - Automatic position scaling on favorable moves
- **Bidirectional Trading** - Auto-flip between LONG and SHORT on SL hits
- **Performance Monitoring** - Track tick rates, latency, and system metrics
- **Emergency Controls** - Square-off all positions instantly

---

## Prerequisites

✅ Python 3.8 or higher  
✅ Dhan Trading Account  
✅ Dhan API Credentials (Client ID + Access Token)  
✅ Active internet connection

---

## Installation

All dependencies are already installed. If you need to reinstall:

```bash
pip install -r requirements.txt
```

---

## Starting the Application

### Option 1: Development Mode (Recommended for Testing)

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Option 2: Production Mode

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

Then open your browser to: **http://localhost:8000**

---

## Configuration Steps

### 1. Connect to Dhan API

1. Enter your **Dhan Client ID**
2. Enter your **Dhan Access Token**
3. Click **Connect API**
4. Wait for "Connected to Dhan API" confirmation

### 2. Configure Strategy Settings

**Trade Capital**: ₹100,000 (Start small for testing!)  
**Top N Gainers**: 5 (How many gainers to trade)  
**Top N Losers**: 5 (How many losers to trade)  
**Add Ons**: 5 (Maximum pyramid levels)  
**Add On % Rise**: 0.5% (Trigger for next add-on)  
**Initial Stop Loss**: 0.5%  
**Trailing SL**: 0.5% (From high watermark)  
**Target**: 2.0%  
**Stock Profit Target**: ₹5,000 (Per stock limit)  
**Stock Loss Limit**: ₹2,000 (Per stock limit)  
**Min Turnover**: 1.0 Cr (Minimum stock liquidity)

### 3. Start the Algorithm

1. Click **Start Algo**
2. The engine will:
   - Filter 200 stocks by volume SMA
   - Subscribe to WebSocket for live data
   - Identify top gainers/losers based on turnover
   - Auto-start ladders when criteria are met

---

## Dashboard Features

### 🔴 **Connection Status**
- **Green dot**: Connected to Dhan
- **Red dot**: Disconnected

### 📊 **Performance Metrics**
- **Tick Latency**: Average tick processing time (target: <10ms)
- **Order Latency**: Order execution time (target: <500ms)
- **Tick Rate**: Ticks processed per second
- **CPU & Memory**: System resource usage

### 🎯 **Active Positions Table**

| Column | Description |
|--------|-------------|
| Symbol | Stock symbol |
| Mode | LONG / SHORT / NONE |
| LTP | Last Traded Price |
| % Change | % change from previous close |
| P&L | Current profit/loss |
| Qty | Total quantity |
| Level | Current pyramid level |
| Avg Entry | Average entry price |
| TSL | Trailing stop-loss level |
| Target | Target price |
| Turnover | Current turnover in Crores |
| Status | IDLE / ACTIVE / CLOSED_* |
| Action | Close button for manual exit |

---

## Trading Strategy

### How It Works

1. **Stock Filtering**
   - Filters 200 high-value stocks by Volume SMA
   - Formula: `(Sum of Last 5 Days Volume) / 1875 > 2000`
   - Ensures sufficient liquidity

2. **Live Data Subscription**
   - Subscribes to filtered stocks via Dhan WebSocket
   - Calculates real-time % change and turnover

3. **Top Mover Selection**
   - Ranks stocks by % change
   - Selects top N gainers (LONG) and losers (SHORT)
   - Minimum turnover filter applied

4. **Ladder Initiation**
   - **LONG Ladder**: For top gainers
   - **SHORT Ladder**: For top losers
   - Initial position based on trade capital

5. **Pyramiding (Add-Ons)**
   - Adds same quantity on every 0.5% favorable move
   - Maximum 5 add-ons (6 total levels)
   - Average entry price tracked

6. **Exit Logic**
   - **Target Hit**: Exit at +2% profit
   - **Trailing SL**: Exit if price falls 0.5% from highest
   - **Bidirectional**: On SL hit, flip to opposite direction
   - **Global Limits**: Exit if per-stock P&L exceeds limits

7. **Market Hours**
   - Auto square-off at 3:20 PM IST
   - No new trades outside market hours

---

## Emergency Controls

### 🔴 SQUARE OFF ALL Button
- **Instantly closes all positions**
- Use in case of market volatility or system issues
- Confirmation dialog prevents accidental clicks

### Individual Position Close
- Click "Close" button in Actions column
- Exits specific position at market price

### STOP Button
- Stops the strategy engine
- Positions remain open (manual close required)

---

## Performance Targets

| Metric | Target | Purpose |
|--------|--------|---------|
| Tick Latency | <10ms | Fast price updates |
| Order Latency | <500ms | Quick execution |
| Tick Rate | >100/s | Handle multiple stocks |
| CPU Usage | <30% | Efficient processing |
| Memory | <500MB | Low resource usage |

---

## Safety Checklist

Before going live with real money:

- [ ] Test with ₹10,000 capital first
- [ ] Monitor first 3 trades manually
- [ ] Verify P&L calculations match expectations
- [ ] Test STOP and SQUARE OFF buttons
- [ ] Ensure stable internet connection
- [ ] Set appropriate position limits
- [ ] Understand the bidirectional trading risk
- [ ] Have manual square-off ready in Dhan app

---

## Troubleshooting

### Issue: "Dhan not connected"
**Solution**: Check credentials, ensure valid access token

### Issue: "No valid symbols to subscribe"
**Solution**: Stock filtering might have rejected all stocks. Check logs for details.

### Issue: WebSocket keeps disconnecting
**Solution**: Check internet stability. Auto-reconnect should handle temporary issues.

### Issue: Orders not executing
**Solution**: Check Dhan account balance, margin availability, and order logs.

### Issue: High latency (>50ms)
**Solution**: Close other applications, check CPU usage, ensure no background downloads.

---

## API Endpoints

For advanced integration:

- `GET /` - Dashboard
- `POST /api/login` - Connect to Dhan
- `POST /api/start` - Start engine
- `POST /api/stop` - Stop engine
- `GET /api/status` - System status
- `GET /api/positions` - Current positions
- `POST /api/square-off-all` - Emergency exit
- `POST /api/close-position/{symbol}` - Close specific position
- `GET /api/metrics` - Performance metrics
- `GET /api/health` - Health check
- `WS /ws` - WebSocket for live updates

---

## Support & Logs

### View Logs
Logs are displayed in the dashboard's "Logs" section.

For detailed logs, check the terminal where the application is running.

### Log Levels
- **INFO**: Normal operations
- **WARNING**: Issues that don't stop execution
- **ERROR**: Critical failures

---

## Tips for Success

1. **Start Small**: Test with ₹10,000-25,000 capital
2. **Monitor Initially**: Watch first few trades closely
3. **Adjust Settings**: Fine-tune based on market conditions
4. **Use Limits**: Set appropriate per-stock profit/loss limits
5. **Watch Volatility**: Be cautious during high volatility
6. **Internet**: Ensure stable connection throughout
7. **Backup Plan**: Keep Dhan app open for manual intervention

---

## Performance Optimization

The application is optimized for low-latency trading:

✅ **ujson** for faster JSON parsing  
✅ **NumPy** for vectorized calculations  
✅ **LRU caching** for security ID lookups  
✅ **Async operations** for parallel processing  
✅ **WebSocket batching** to reduce overhead  
✅ **Document fragments** for efficient UI updates  

---

## Legal Disclaimer

⚠️ **IMPORTANT**: This is a trading bot that executes real market orders with real money.

- Use at your own risk
- Past performance does not guarantee future results
- Always test with small capital first
- Monitor the system actively during trading
- Have emergency controls ready
- Understand the risks of algorithmic trading

The developers are not responsible for any financial losses incurred from using this software.

---

## Next Steps

1. ✅ Installation complete
2. ✅ Application verified
3. 🔄 Start the application
4. 🔄 Configure and connect
5. 🔄 Test with small capital
6. 🔄 Monitor and optimize
7. 🎯 Scale up gradually

**Happy Trading! 🚀**
