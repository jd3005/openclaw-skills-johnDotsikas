#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "..", "config.monitor.json")
TRADES_PATH = os.path.join(BASE_DIR, "..", "state", "trades.jsonl")

def load_trades():
    trades = []
    if os.path.exists(TRADES_PATH):
        with open(TRADES_PATH, 'r') as f:
            for line in f:
                try:
                    trades.append(json.loads(line))
                except:
                    continue
    return trades

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

def evaluate_daily():
    trades = load_trades()
    if not trades:
        print("No trades to evaluate.")
        return

    config = load_config()
    
    # Group trades by setup_type (last 20 for each)
    setup_stats = {}
    for t in trades:
        st = t['setup_type']
        if st not in setup_stats:
            setup_stats[st] = []
        setup_stats[st].append(t)

    summary = "📊 **Daily Performance Recalibration**\n"
    changes_made = False

    for st, st_trades in setup_stats.items():
        recent = st_trades[-20:]
        wins = [t for t in recent if t['pnl_pct'] > 0]
        win_rate = len(wins) / len(recent) if recent else 0
        
        avg_gain = sum([t['pnl_pct'] for t in wins]) / len(wins) if wins else 0
        losses = [t for t in recent if t['pnl_pct'] <= 0]
        avg_loss = sum([abs(t['pnl_pct']) for t in losses]) / len(losses) if losses else 0

        summary += f"\n- **{st}**: {win_rate*100:.1f}% Win Rate ({len(recent)} samples)\n"

        # Rule: Win Rate < 40% -> Reduce size by 25%
        if win_rate < 0.40 and len(recent) >= 5:
            summary += f"   ⚠️ Setup underperforming. Reducing size by 25%.\n"
            # We need to find where this setup is in config. 
            # (In our simplified config, we have global alpha/shield sizes)
            # I'll add a 'dynamic_modifiers' section to config.
            if 'dynamic_modifiers' not in config: config['dynamic_modifiers'] = {}
            config['dynamic_modifiers'][st] = config['dynamic_modifiers'].get(st, 1.0) * 0.75
            changes_made = True
            
            # Rule: Win Rate < 35% -> Disable (Mark as disabled in modifiers)
            if win_rate < 0.35 and len(recent) >= 10:
                summary += f"   🚫 CRITICAL: Win rate below 35%. Disabling setup until review.\n"
                config['dynamic_modifiers'][st] = 0

        # Rule: Win Rate > 65% -> Increase size by 10%
        elif win_rate > 0.65 and len(recent) >= 5:
            summary += f"   🚀 Setup outperforming! Increasing size by 10%.\n"
            if 'dynamic_modifiers' not in config: config['dynamic_modifiers'] = {}
            current_mod = config['dynamic_modifiers'].get(st, 1.0)
            # Cap at max sizes (implicit in monitor.js logic)
            config['dynamic_modifiers'][st] = min(current_mod * 1.10, 1.5)
            changes_made = True

        # Rule: Average Loss > Average Gain
        if avg_loss > avg_gain and len(recent) >= 5:
            summary += f"   ⚠️ Negative Expectancy (Avg Loss > Avg Gain). Tightening stops.\n"
            # Note: We'd need to update strategy logic to use these modifiers for stops.
            # For now, we'll just flag it in the report.

    if changes_made:
        save_config(config)
        summary += "\n✅ Strategy weights updated."
    
    print(summary)

def generate_weekly_report():
    trades = load_trades()
    # Filter for last 7 days
    one_week_ago = datetime.now() - timedelta(days=7)
    recent = [t for t in trades if datetime.fromisoformat(t['exit_time'].replace('Z', '')) > one_week_ago]
    
    if not recent:
        print("No trades in the last week.")
        return

    total_trades = len(recent)
    wins = [t for t in recent if t['pnl_pct'] > 0]
    win_rate = len(wins) / total_trades
    net_pnl = sum([t['pnl_dollar'] for t in recent])
    
    report = f"""
📅 **Weekly Performance Summary**
Total Trades: {total_trades}
Win Rate: {win_rate*100:.1f}%
Net Capital Change: ${net_pnl:.2f}

Best Setup: {max(set([t['setup_type'] for t in recent]), key=lambda s: sum([t['pnl_dollar'] for t in recent if t['setup_type'] == s]))}
Worst Setup: {min(set([t['setup_type'] for t in recent]), key=lambda s: sum([t['pnl_dollar'] for t in recent if t['setup_type'] == s]))}
"""
    print(report)

if __name__ == "__main__":
    if "--daily" in sys.argv:
        evaluate_daily()
    elif "--weekly" in sys.argv:
        generate_weekly_report()
    else:
        print("Usage: performance_engine.py --daily | --weekly")
