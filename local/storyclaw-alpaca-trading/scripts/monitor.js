#!/usr/bin/env node
/**
 * Alpha/Shield Strategy Monitor
 */

const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

// Load config
const { loadUserConfig, getStatePath } = require("./config-loader");
const { config: monitorConfig } = loadUserConfig();

function requestText(args) {
  try {
    return execFileSync("node", [path.join(__dirname, "trading.js"), ...args], {
      env: { ...process.env, USER_ID: monitorConfig.userId },
      encoding: "utf8",
    });
  } catch (e) {
    return "";
  }
}

function safeBars(symbol) {
  try {
    const output = requestText(["bars", symbol, "300"]);
    const lines = output.split("\n").filter((line) => /^\s*\d{4}-\d{2}-\d{2}/.test(line));
    return lines.map((line) => {
      const m = line.match(/(\d{4}-\d{2}-\d{2}[T ]?[\d:]*Z?): O:([0-9.]+) H:([0-9.]+) L:([0-9.]+) C:([0-9.]+) V:([0-9.]+)/);
      if (!m) return null;
      return { c: parseFloat(m[5]), v: parseFloat(m[6]) };
    }).filter(b => b !== null);
  } catch {
    return [];
  }
}

async function getPositionCount() {
  try {
    const output = requestText(["positions"]);
    if (output.includes("No positions")) return { count: 0, symbols: [], raw: [] };
    const symbols = [];
    const lines = output.split("\n");
    const raw = [];
    
    // Parse positions and P&L %
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (line.includes(":") && !line.includes("Value:") && !line.includes("P&L:")) {
            const sym = line.split(":")[0].trim();
            symbols.push(sym);
            
            // Look for P&L % in the next few lines
            const pnlLine = lines[i+2];
            if (pnlLine && pnlLine.includes("P&L:")) {
                const match = pnlLine.match(/\(([-0-9.]+)%\)/);
                if (match) {
                    raw.push({ symbol: sym, unrealized_plpc: parseFloat(match[1]) / 100 });
                }
            }
        }
    }
    return { count: symbols.length, symbols, raw };
  } catch (e) {
    return { count: 0, symbols: [], raw: [] };
  }
}

function loadState() {
  const statePath = getStatePath(monitorConfig.userId, "alpaca-monitor.json");
  if (!fs.existsSync(statePath)) return { alerts: {} };
  try {
    return JSON.parse(fs.readFileSync(statePath, "utf8"));
  } catch {
    return { alerts: {} };
  }
}

function saveState(state) {
  const statePath = getStatePath(monitorConfig.userId, "alpaca-monitor.json");
  fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
}

function shouldAlert(state, symbol, price) {
  const prev = state.alerts[symbol];
  if (!prev) return true;
  const elapsedMinutes = (Date.now() - prev.ts) / 60000;
  if (elapsedMinutes >= monitorConfig.cooldownMinutes) return true;
  return false;
}

function runAlphaShieldStrategy(symbol, context) {
  try {
    const output = execFileSync("python3", [
      path.join(__dirname, "alpha_shield_strategy.py"), 
      symbol, 
      JSON.stringify(context)
    ], {
      env: { ...process.env, USER_ID: monitorConfig.userId },
      encoding: "utf8",
    });
    return JSON.parse(output);
  } catch (e) {
    return { error: e.message };
  }
}

function buildAlphaShieldAlert(res, isPyramid = false) {
  const prefix = isPyramid ? "🔥 **PYRAMID OPPORTUNITY**" : (res.mode === "ALPHA" ? "🚀 **ALPHA SIDE - Aggressive**" : "🛡️ **SHIELD SIDE - Conservative**");
  return [
    `${prefix}`,
    `Paper trade idea: ${res.symbol} (${res.action})`,
    `Reasoning: ${res.reasoning}`,
    `Price: $${res.price.toFixed(2)} | RSI: ${res.rsi.toFixed(1)} | Vol: ${res.vol_ratio.toFixed(2)}x`,
    `Suggested Size: $${res.suggestedSize}`,
    `Target: ${res.takeProfit > 0 ? '$' + res.takeProfit.toFixed(2) : 'Dynamic'}`,
    `Protection: ${res.trailingStop > 0 ? res.trailingStop + '% Trailing Stop' : (res.stopLoss > 0 ? '$' + res.stopLoss.toFixed(2) + ' Hard Stop' : 'Standard')}`,
    `Action: alpaca ${res.action === "SHORT" ? "sell" : "buy-amount"} ${res.symbol} ${res.suggestedSize}`
  ].join("\n");
}

async function main() {
  const alphaSymbols = monitorConfig.strategy.alpha.symbols;
  const shieldSymbols = monitorConfig.strategy.shield.symbols;
  const symbols = [...alphaSymbols, ...shieldSymbols];
  
  const state = loadState();
  const currentPositions = await getPositionCount();
  const currentCount = currentPositions.count;
  const maxAllowed = monitorConfig.maxPositions || 3;

  // 1. Get Market Context (SPY Trend)
  const spyBars = safeBars("SPY");
  const spyCloses = spyBars.map(b => b.c);
  const spySma200 = spyCloses.length >= 200 ? spyCloses.slice(-200).reduce((a,b) => a+b, 0) / 200 : 0;
  const spyCurrent = spyCloses[spyCloses.length - 1];
  const marketContext = {
    trend: (spyCurrent > spySma200 && spySma200 > 0) ? "bull" : "bear",
    vix: 20
  };

  const allResults = [];
  for (const symbol of symbols) {
    // If we already have 3 positions, we only scan symbols we already own (for pyramiding)
    if (currentCount >= maxAllowed && !currentPositions.symbols.includes(symbol)) continue;

    const res = runAlphaShieldStrategy(symbol, marketContext);
    if (!res || res.error) continue;
    
    if (res.action !== "HOLD") {
      allResults.push(res);
    }
  }

  const alerts = [];
  const handledSymbols = new Set(currentPositions.symbols);

  for (const res of allResults) {
    if (currentCount + alerts.length >= maxAllowed) {
      // Check for Pyramiding (ALPHA winner up 10%)
      const pos = currentPositions.raw.find(p => p.symbol === res.symbol);
      if (pos && res.mode === "ALPHA" && pos.unrealized_plpc >= 0.10) {
         if (res.vol_ratio >= 1.5 && shouldAlert(state, res.symbol + "-PYR", res.price)) {
            alerts.push(buildAlphaShieldAlert(res, true));
            state.alerts[res.symbol + "-PYR"] = { ts: Date.now(), score: res.price };
         }
      }
      continue;
    }

    if (!handledSymbols.has(res.symbol)) {
      if (shouldAlert(state, res.symbol, res.price)) {
        alerts.push(buildAlphaShieldAlert(res));
        state.alerts[res.symbol] = { ts: Date.now(), score: res.price };
        handledSymbols.add(res.symbol);
      }
    }
  }

  // 2. Strategic Fill (If under minimum)
  const minRequired = monitorConfig.minPositions || 5;
  if (currentCount + alerts.length < minRequired) {
    const slotsToFill = minRequired - (currentCount + alerts.length);
    // Sort all available symbols by "undervaluation" (Z-Score or RSI)
    // We'll use the AlphaShieldStrategy output to find the best of the remaining bunch
    const candidates = [];
    for (const symbol of symbols) {
       if (handledSymbols.has(symbol)) continue;
       const res = runAlphaShieldStrategy(symbol, marketContext);
       if (!res || res.error) continue;
       // We prefer lower RSI for fill
       candidates.push(res);
    }
    
    candidates.sort((a, b) => a.rsi - b.rsi);

    for (let i = 0; i < Math.min(slotsToFill, candidates.length); i++) {
      const res = candidates[i];
      if (currentCount + alerts.length >= maxAllowed) break;
      alerts.push(`⚠️ **STRATEGIC FILL** (Portfolio < ${minRequired})\n${buildAlphaShieldAlert(res)}`);
      state.alerts[res.symbol] = { ts: Date.now(), score: res.price };
      handledSymbols.add(res.symbol);
    }
  }

  if (alerts.length > 0) {
    console.log(alerts.join("\n\n---\n\n"));
    saveState(state);
  } else {
    console.log("No trade ideas right now.");
  }
}

main();
