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

function applyPerformanceModifiers(res, config) {
  if (!config.dynamic_modifiers) return res.suggestedSize;
  const mod = config.dynamic_modifiers[res.setup_type] || 1.0;
  
  // If mod is 0, the setup is disabled
  if (mod === 0) return 0;
  
  let finalSize = res.suggestedSize * mod;
  
  // Cap at limits
  const maxLimit = res.mode === "ALPHA" ? 2000 : 1500;
  return Math.min(finalSize, maxLimit);
}

function buildAlphaShieldAlert(res, isPyramid = false) {
  const adjustedSize = res.finalSize || applyPerformanceModifiers(res, monitorConfig);
  if (adjustedSize === 0) return null; // Setup disabled

  const prefix = isPyramid ? "🔥 **PYRAMID OPPORTUNITY**" : (res.mode === "ALPHA" ? "🚀 **ALPHA SIDE - Aggressive**" : "🛡️ **SHIELD SIDE - Conservative**");
  return [
    `${prefix}`,
    `Paper trade idea: ${res.symbol} (${res.action})`,
    `Reasoning: ${res.reasoning}`,
    `Setup: ${res.setup_type} | Performance Adj: ${((monitorConfig.dynamic_modifiers || {})[res.setup_type] || 1.0).toFixed(2)}x`,
    `Price: $${res.price.toFixed(2)} | RSI: ${res.rsi.toFixed(1)} | Vol: ${res.vol_ratio.toFixed(2)}x`,
    `Suggested Size: $${adjustedSize.toFixed(2)}`,
    `Target: ${res.takeProfit > 0 ? '$' + res.takeProfit.toFixed(2) : 'Dynamic'}`,
    `Protection: ${res.trailingStop > 0 ? res.trailingStop + '% Trailing Stop' : (res.stopLoss > 0 ? '$' + res.stopLoss.toFixed(2) + ' Hard Stop' : 'Standard')}`,
    `Action: alpaca ${res.action === "SHORT" ? "sell" : "buy-amount"} ${res.symbol} ${adjustedSize.toFixed(0)}`
  ].join("\n");
}

const { getCorrelation, checkSectorPerformance } = require("./utils_intelligence");

async function main() {
  const alphaSymbols = monitorConfig.strategy.alpha.symbols;
  const shieldSymbols = monitorConfig.strategy.shield.symbols;
  const symbols = [...alphaSymbols, ...shieldSymbols];
  
  const state = loadState();
  const currentPositions = await getPositionCount();
  const currentCount = currentPositions.count;
  const maxAllowed = monitorConfig.maxPositions || 20;

  // 1. Get Intel
  const intelPath = path.join(__dirname, "..", "state", "daily_intel.json");
  const intel = fs.existsSync(intelPath) ? JSON.parse(fs.readFileSync(intelPath, "utf8")) : { earnings: [], catalysts: {}, negative_news: {} };

  // 2. Get Sector Performance
  const sectorRanks = checkSectorPerformance(monitorConfig.sectors, monitorConfig.userId);
  const topSectors = sectorRanks.slice(0, 2).map(s => s[0]);
  const bottomSectors = sectorRanks.slice(-2).map(s => s[0]);

  // 3. Get Market Context (SPY Trend)
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
    if (currentCount >= maxAllowed && !currentPositions.symbols.includes(symbol)) continue;

    // Rule: Sector Priority
    const symbolSector = Object.keys(monitorConfig.sectors).find(k => monitorConfig.sectors[k].includes(symbol));
    if (alphaSymbols.includes(symbol)) {
      if (bottomSectors.includes(symbolSector)) continue; // Avoid bottom 2 for Alpha
    }

    const res = runAlphaShieldStrategy(symbol, marketContext);
    if (!res || res.error) continue;
    
    // Rule: Earnings/Catalyst
    if (res.action === "BUY") {
      if (intel.earnings.includes(symbol)) {
        // Alpha can only play AFTER earnings. Shield must exit BEFORE.
        if (res.mode === "ALPHA") {
           res.suggestedSize = Math.min(res.suggestedSize, 1000);
           res.stopLoss = res.price * 0.95;
           res.reasoning += " (Earnings Play - Restricted Size/Stop)";
        } else {
           continue; // Shield avoid earnings
        }
      }
      
      if (res.is_opening_bell && !intel.catalysts[symbol]) {
        continue; // Opening bell catalyst check
      }
    }

    if (res.action !== "HOLD") {
      allResults.push(res);
    }
  }

  const alerts = [];
  const handledSymbols = new Set(currentPositions.symbols);

  for (const res of allResults) {
    if (currentCount + alerts.length >= maxAllowed) {
      // Pyramiding check...
      continue;
    }

    if (!handledSymbols.has(res.symbol)) {
      // Rule: Correlation Check
      let sizeFactor = 1.0;
      for (const pos of currentPositions.symbols) {
         const corr = getCorrelation(res.symbol, pos, monitorConfig.userId);
         if (corr > 0.8) {
           sizeFactor = 0.5;
           res.reasoning += ` (Correlated with ${pos}, size reduced 50%)`;
           break;
         }
      }

      if (shouldAlert(state, res.symbol, res.price)) {
        const adjustedSize = applyPerformanceModifiers(res, monitorConfig) * sizeFactor;
        if (adjustedSize > 0) {
           res.finalSize = adjustedSize;
           alerts.push(buildAlphaShieldAlert(res));
           state.alerts[res.symbol] = { 
               ts: Date.now(), 
               price: res.price, 
               setup_type: res.setup_type,
               conditions: res.conditions,
               mode: res.mode,
               reasoning: res.reasoning
           };
           handledSymbols.add(res.symbol);
        }
      }
    }
  }

  // 2. Strategic Fill (If under minimum)
  const minRequired = monitorConfig.minPositions || 5;
  if (currentCount + alerts.length < minRequired) {
    const slotsToFill = minRequired - (currentCount + alerts.length);
    const candidates = [];
    for (const symbol of symbols) {
       if (handledSymbols.has(symbol)) continue;
       const res = runAlphaShieldStrategy(symbol, marketContext);
       if (!res || res.error) continue;
       candidates.push(res);
    }
    
    candidates.sort((a, b) => a.rsi - b.rsi);

    for (let i = 0; i < Math.min(slotsToFill, candidates.length); i++) {
      const res = candidates[i];
      if (currentCount + alerts.length >= maxAllowed) break;
      alerts.push(`⚠️ **STRATEGIC FILL** (Portfolio < ${minRequired})\n${buildAlphaShieldAlert(res)}`);
      state.alerts[res.symbol] = { 
          ts: Date.now(), 
          price: res.price,
          setup_type: "strategic_fill",
          conditions: res.conditions,
          mode: res.mode,
          reasoning: "Strategic portfolio fill to maintain minimum position count."
      };
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
