#!/usr/bin/env python3
import json
import sys
import subprocess
import math
import statistics
from datetime import datetime

class ZScoreStrategy:
    def __init__(self, symbol, lookback=20, slippage=0.001):
        self.symbol = symbol
        self.lookback = lookback
        self.slippage = slippage

    def get_market_data(self):
        """Fetch historical bars using the existing trading.js utility."""
        try:
            # We call the existing trading.js bars command to get raw data
            cmd = ["node", "scripts/trading.js", "bars", self.symbol, str(self.lookback + 5)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            lines = result.stdout.strip().split('\n')
            prices = []
            
            # Parsing the format: 2026-04-29: O:213.11 H:215.11 L:212.11 C:214.11 V:12345
            for line in lines:
                if 'C:' in line:
                    try:
                        close_part = line.split('C:')[1].split(' ')[0]
                        prices.append(float(close_part))
                    except (IndexError, ValueError):
                        continue
            
            return prices
        except Exception as e:
            print(f"Error fetching data: {e}", file=sys.stderr)
            return []

    def calculate_z_score(self, prices):
        if len(prices) < self.lookback:
            return None, None, None

        recent_prices = prices[-self.lookback:]
        sma = statistics.mean(recent_prices)
        stdev = statistics.stdev(recent_prices)
        
        current_price = prices[-1]
        
        if stdev == 0:
            return 0, sma, stdev
            
        z_score = (current_price - sma) / stdev
        return z_score, sma, stdev

    def analyze(self):
        prices = self.get_market_data()
        if not prices:
            return {"error": "No data available"}

        current_price = prices[-1]
        z_score, sma, stdev = self.calculate_z_score(prices)
        
        if z_score is None:
            return {"error": "Insufficient data for lookback period"}

        recommendation = "HOLD"
        action = None
        reasoning = f"Z-Score is {z_score:.2f} (Price: {current_price:.2f}, SMA: {sma:.2f})"

        # Logic based on Z-Score thresholds
        if z_score < -3.0:
            recommendation = "EXIT_LONG_STOP"
            action = "SELL"
            reasoning += " | CRITICAL: Z-Score below -3.0. Trend breakout detected. Hard Stop-Loss triggered."
        elif z_score > 3.0:
            recommendation = "EXIT_SHORT_STOP"
            action = "BUY"
            reasoning += " | CRITICAL: Z-Score above +3.0. Trend breakout detected. Hard Stop-Loss triggered."
        elif z_score < -2.0:
            recommendation = "LONG_ENTRY"
            action = "BUY"
            reasoning += " | Mean Reversion: Z-Score below -2.0. Price is significantly undervalued relative to 20-period average."
        elif z_score > 2.0:
            recommendation = "SHORT_ENTRY"
            action = "SELL"
            reasoning += " | Mean Reversion: Z-Score above +2.0. Price is significantly overvalued relative to 20-period average."
        elif abs(z_score) < 0.2:
            recommendation = "EXIT_REVERSION"
            action = "EXIT"
            reasoning += " | Target Reached: Z-Score returned to ~0. Closing position for Take Profit."

        # Slippage simulation
        sim_price = current_price * (1 + self.slippage) if action == "BUY" else current_price * (1 - self.slippage)
        
        return {
            "symbol": self.symbol,
            "z_score": z_score,
            "sma": sma,
            "stdev": stdev,
            "price": current_price,
            "sim_price_with_slippage": sim_price,
            "recommendation": recommendation,
            "action": action,
            "reasoning": reasoning,
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Symbol required"}))
        sys.exit(1)
    
    symbol = sys.argv[1]
    strategy = ZScoreStrategy(symbol)
    print(json.dumps(strategy.analyze(), indent=2))
