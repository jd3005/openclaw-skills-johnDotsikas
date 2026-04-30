#!/usr/bin/env python3
import json
import sys
import os
import subprocess
import math
import statistics

class AlphaShieldStrategy:
    def __init__(self, symbol, lookback=200):
        self.symbol = symbol
        self.lookback = lookback
        self.is_crypto = "USD" in symbol

    def get_market_data(self, timeframe="1Day", days=300):
        """Fetch historical bars using the existing trading.js utility."""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            trading_path = os.path.join(script_dir, "trading.js")
            
            cmd = ["node", trading_path, "bars", self.symbol, str(days), timeframe]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            lines = result.stdout.strip().split('\n')
            bars = []
            for line in lines:
                if 'C:' in line:
                    try:
                        # Extract O, H, L, C, V
                        parts = line.split(':')
                        # format: 2026-04-29T18:00:00Z: O:213.11 H:215.11 L:212.11 C:214.11 V:12345
                        # parts[1] has O, parts[2] has H, parts[3] has L, parts[4] has C, parts[5] has V
                        o = float(parts[2].split(' ')[0])
                        h = float(parts[3].split(' ')[0])
                        l = float(parts[4].split(' ')[0])
                        c = float(parts[5].split(' ')[0])
                        v = float(parts[6].split(' ')[0])
                        bars.append({'o': o, 'h': h, 'l': l, 'c': c, 'v': v})
                    except Exception as e:
                        continue
            return bars
        except Exception as e:
            return []

    def calculate_sma(self, prices, period):
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    def calculate_rsi(self, prices, period=14):
        if len(prices) < period + 1:
            return 50
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [abs(d) if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def analyze(self, market_context=None):
        # Default market context
        market_trend = market_context.get('trend', 'bull') if market_context else 'bull'
        vix = market_context.get('vix', 20) if market_context else 20
        
        # 1. Fetch data
        day_bars = self.get_market_data("1Day", 300)
        hour_bars = self.get_market_data("1Hour", 20)
        
        if len(day_bars) < 50:
            return {"error": "Insufficient historical data"}
            
        closes = [b['c'] for b in day_bars]
        highs = [b['h'] for b in day_bars]
        lows = [b['l'] for b in day_bars]
        volumes = [b['v'] for b in day_bars]
        
        current_price = closes[-1]
        prev_price = closes[-2]
        rsi = self.calculate_rsi(closes)
        sma50 = self.calculate_sma(closes, 50)
        sma200 = self.calculate_sma(closes, 200)
        avg_vol30 = self.calculate_sma(volumes, 30)
        current_vol = volumes[-1]
        
        # Check if ALPHA or SHIELD based on typical categorization
        # (This is a helper, but monitor.js will decide the mode)
        is_alpha_symbol = self.symbol in ["NVDA", "TSLA", "AMD", "META", "SOLUSD", "DOGEUSD"]
        
        # --- LIQUIDITY FILTER ---
        # 500k min volume (30-day avg), < 0.5% spread
        if avg_vol30 < 500000:
             return {"error": f"Insufficient liquidity: Avg Vol {avg_vol30:.0f} < 500k"}
        
        # Note: Spread check would need real-time quote data. 
        # For now, we assume monitor.js will handle the real-time spread check.

        # --- TIME-OF-DAY RULES ---
        now_est = datetime.now() - timedelta(hours=4) # Simple EST conversion
        hour = now_est.hour
        minute = now_est.minute
        time_mod = 1.0
        
        # 1. 9:30 - 9:40: Catalyst only (We'll flag this for monitor.js to check news)
        is_opening_bell = (hour == 9 and 30 <= minute <= 40)
        
        # 2. 11:00 - 1:00: Low-conviction (-30% size)
        if 11 <= hour < 13:
            time_mod = 0.70
            
        # 3. 3:30 - 4:00: Exit-only window
        is_exit_only = (hour == 15 and minute >= 30)
        
        res = {
            "symbol": self.symbol,
            "price": current_price,
            "rsi": rsi,
            "sma50": sma50,
            "sma200": sma200,
            "vol_ratio": current_vol / avg_vol30 if avg_vol30 else 1,
            "action": "HOLD",
            "mode": "ALPHA" if is_alpha_symbol else "SHIELD",
            "setup_type": "none",
            "reasoning": "",
            "suggestedSize": 0,
            "stopLoss": 0,
            "takeProfit": 0,
            "trailingStop": 0,
            "time_mod": time_mod,
            "is_opening_bell": is_opening_bell,
            "is_exit_only": is_exit_only,
            "conditions": {
                "rsi": rsi,
                "vol_ratio": current_vol / avg_vol30 if avg_vol30 else 1,
                "trend": market_trend,
                "vix": vix,
                "market_mode": market_trend
            }
        }

        # --- ALPHA LOGIC ---
        if res["mode"] == "ALPHA":
            # Rule: All ALPHA closed before market close (Eliminate overnight risk)
            # This is handled by monitor.js/positions-watch.js

            # 1. Aggressive Momentum / Breakout
            recent_max = max(highs[-21:-1])
            if rsi > 72 and res["vol_ratio"] >= 2.2 and current_price > recent_max:
                if is_exit_only:
                     res["reasoning"] = "ALPHA: Breakout detected, but in Exit-Only window. Skipping."
                else:
                    res["action"] = "BUY"
                    res["setup_type"] = "breakout"
                    res["reasoning"] = "ALPHA: High-Conviction Momentum Breakout (Extremely High Vol & RSI)."
                    res["suggestedSize"] = 2000 * time_mod
                    res["trailingStop"] = 3.0
                    res["takeProfit"] = current_price * 1.25
                
            # 2. Intraday Pullback Scalping
            elif (current_price - prev_price) / prev_price <= -0.05 and market_trend == 'bull':
                 if is_exit_only:
                     res["reasoning"] = "ALPHA: Pullback detected, but in Exit-Only window. Skipping."
                 else:
                    res["action"] = "BUY"
                    res["setup_type"] = "pullback"
                    res["reasoning"] = "ALPHA: Deep Intraday Pullback (Opportunistic Re-entry)."
                    res["suggestedSize"] = 2000 * time_mod
                    res["stopLoss"] = current_price * 0.96
                    res["takeProfit"] = current_price * 1.15

        # --- SHIELD LOGIC ---
        else:
            # 1. Stable Uptrend
            if sma50 and sma200 and current_price > sma50 and current_price > sma200:
                dist_to_50ma = (current_price - sma50) / sma50
                if 0 <= dist_to_50ma <= 0.015 and rsi < 65:
                    if is_exit_only:
                        res["reasoning"] = "SHIELD: Entry conditions met, but in Exit-Only window. Skipping."
                    else:
                        res["action"] = "BUY"
                        res["setup_type"] = "uptrend_accumulation"
                        res["reasoning"] = "SHIELD: Conservative Uptrend accumulation (Targeting 8% Swing)."
                        res["suggestedSize"] = 2000 * time_mod
                        res["trailingStop"] = 2.5
                        res["takeProfit"] = current_price * 1.08
                
            # 2. Blue Chip/ETF accumulation on 3-5% dip
            max_recent = max(highs[-30:])
            dip_pct = (max_recent - current_price) / max_recent
            if 0.03 <= dip_pct <= 0.06 and market_trend == 'bull':
                res["action"] = "BUY"
                res["setup_type"] = "strategic_dip"
                res["reasoning"] = f"SHIELD: Strategic accumulation on {dip_pct*100:.1f}% dip."
                res["suggestedSize"] = 2000
                res["trailingStop"] = 2.5
                res["takeProfit"] = current_price * 1.08

            # 3. Overbought Market Protection
            if rsi > 75 or vix > 25:
                res["action"] = "HOLD"
                res["reasoning"] = "SHIELD: Market Overbought or Volatile (RSI > 75 or VIX > 25). Neutral stance."
                res["suggestedSize"] = 0

        # Bear Market Modifier
        if market_trend == 'bear':
            if res["mode"] == "ALPHA":
                if res["action"] == "BUY":
                    res["suggestedSize"] *= 0.5 # Reduce size in bear market
                elif res["action"] == "SHORT":
                    res["suggestedSize"] = 2000 # Maximize shorts
            else:
                res["suggestedSize"] *= 0.5 # Reduce shield activity by 50%
                if res["action"] == "BUY":
                    res["reasoning"] += " (Size reduced 50% due to Bear Market trend)"

        return res

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Symbol required"}))
        sys.exit(1)
        
    symbol = sys.argv[1]
    context = {}
    if len(sys.argv) > 2:
        try:
            context = json.loads(sys.argv[2])
        except:
            pass
            
    strategy = AlphaShieldStrategy(symbol)
    result = strategy.analyze(context)
    print(json.dumps(result))
