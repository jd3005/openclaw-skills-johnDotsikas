const { execFileSync } = require("child_process");
const path = require("path");

/**
 * Intelligent Utilities for Enhanced Directives
 */

function getCorrelation(symbol1, symbol2, userId) {
  try {
    const script = `
import json
import numpy as np
import subprocess
import os

def get_closes(sym):
    trading_path = os.path.join("${__dirname}", "trading.js")
    res = subprocess.run(["node", trading_path, "bars", sym, "30"], capture_output=True, text=True)
    lines = res.stdout.strip().split('\\n')
    closes = []
    for l in lines:
        if 'C:' in l:
            closes.append(float(l.split('C:')[1].split(' ')[0]))
    return closes

c1 = get_closes("${symbol1}")
c2 = get_closes("${symbol2}")
min_len = min(len(c1), len(c2))
if min_len < 10: print(0)
else:
    corr = np.corrcoef(c1[-min_len:], c2[-min_len:])[0,1]
    print(corr)
`;
    const output = execFileSync("python3", ["-c", script], { env: { ...process.env, USER_ID: userId }, encoding: "utf8" });
    return parseFloat(output.trim()) || 0;
  } catch {
    return 0;
  }
}

function checkSectorPerformance(sectors, userId) {
    const script = `
import os
import subprocess

def get_change(sym):
    trading_path = os.path.join("${__dirname}", "trading.js")
    res = subprocess.run(["node", trading_path, "bars", sym, "20"], capture_output=True, text=True)
    lines = res.stdout.strip().split('\\n')
    closes = []
    for l in lines:
        if 'C:' in l: closes.append(float(l.split('C:')[1].split(' ')[0]))
    if len(closes) < 20: return 0
    return (closes[-1] - closes[0]) / closes[0]

sector_data = ${JSON.stringify(sectors)}
results = {}
for name, syms in sector_data.items():
    changes = [get_change(s) for s in syms[:3]] # Check top 3 in each sector
    results[name] = sum(changes) / len(changes) if changes else 0

sorted_sectors = sorted(results.items(), key=lambda x: x[1], reverse=True)
import json
print(json.dumps(sorted_sectors))
`;
    try {
        const output = execFileSync("python3", ["-c", script], { env: { ...process.env, USER_ID: userId }, encoding: "utf8" });
        return JSON.parse(output.trim());
    } catch {
        return [];
    }
}

module.exports = { getCorrelation, checkSectorPerformance };
