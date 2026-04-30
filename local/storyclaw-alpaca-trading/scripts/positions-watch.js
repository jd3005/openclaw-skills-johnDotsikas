#!/usr/bin/env node
/**
 * Alpha/Shield Positions Watch
 * Monitors open positions and triggers sells based on dynamic trailing stops and targets.
 */

const { execFileSync } = require("child_process");
const path = require("path");
const { loadUserConfig } = require("./config-loader");
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

async function getPositions() {
  const output = requestText(["positions"]);
  if (output.includes("No positions")) return [];
  
  const positions = [];
  const lines = output.split("\n");
  let currentPos = null;

  for (const line of lines) {
    if (line.includes(":") && !line.includes("Value:") && !line.includes("P&L:")) {
      if (currentPos) positions.push(currentPos);
      const sym = line.split(":")[0].trim();
      const qty = line.split(":")[1].split(" ")[1].trim();
      currentPos = { symbol: sym, qty: qty };
    } else if (line.includes("P&L:")) {
      const matchPct = line.match(/\(([-0-9.]+)%\)/);
      const matchDollar = line.match(/\$([-0-9.,]+)/);
      if (matchPct && currentPos) {
        currentPos.pnlPct = parseFloat(matchPct[1]);
      }
      if (matchDollar && currentPos) {
        currentPos.pnlDollar = parseFloat(matchDollar[1].replace(/,/g, ''));
      }
    }
  }
  if (currentPos) positions.push(currentPos);
  return positions;
}

function getStrategyRecommendation(symbol) {
  try {
    const output = execFileSync("python3", [path.join(__dirname, "alpha_shield_strategy.py"), symbol], {
      env: { ...process.env, USER_ID: monitorConfig.userId },
      encoding: "utf8",
    });
    return JSON.parse(output);
  } catch {
    return null;
  }
}

function loadMonitorState() {
  const statePath = path.join(__dirname, "..", "state", `${monitorConfig.userId}.alpaca-monitor.json`);
  if (!fs.existsSync(statePath)) return { alerts: {} };
  try { return JSON.parse(fs.readFileSync(statePath, "utf8")); } catch { return { alerts: {} }; }
}

function logTrade(symbol, exitPrice, pnlPct, pnlDollar, reason) {
  const state = loadMonitorState();
  const entryInfo = state.alerts[symbol] || {};
  const trade = {
    symbol,
    mode: entryInfo.mode || "UNKNOWN",
    setup_type: entryInfo.setup_type || "manual_or_old",
    entry_price: entryInfo.price || 0,
    exit_price: exitPrice,
    pnl_pct: pnlPct,
    pnl_dollar: pnlDollar,
    entry_time: entryInfo.ts ? new Date(entryInfo.ts).toISOString() : "UNKNOWN",
    exit_time: new Date().toISOString(),
    conditions: entryInfo.conditions || {},
    reasoning: entryInfo.reasoning || "Standard exit rule triggered.",
    exit_reason: reason
  };
  const logPath = path.join(__dirname, "..", "state", "trades.jsonl");
  fs.appendFileSync(logPath, JSON.stringify(trade) + "\n");
}

async function main() {
  const positions = await getPositions();
  const alerts = [];

  for (const pos of positions) {
    const strategy = getStrategyRecommendation(pos.symbol);
    if (!strategy) continue;

    const isAlpha = strategy.mode === "ALPHA";
    const pnl = pos.pnlPct;
    const currentPrice = strategy.price;
    
    let shouldSell = false;
    let reason = "";

    if (isAlpha && pnl >= 25.0) {
      shouldSell = true;
      reason = `ALPHA: Take-Profit target reached at ${pnl.toFixed(2)}%`;
    } else if (!isAlpha && pnl >= 8.0) {
      shouldSell = true;
      reason = `SHIELD: Take-Profit target reached at ${pnl.toFixed(2)}%`;
    }

    if (strategy.action === "SELL") {
      shouldSell = true;
      reason = strategy.reasoning;
    }

    if (isAlpha && pnl <= -3.0) {
      shouldSell = true;
      reason = `ALPHA: Hard Stop-Loss triggered at ${pnl.toFixed(2)}%`;
    } else if (!isAlpha && pnl <= -5.0) {
      shouldSell = true;
      reason = `SHIELD: Hard Stop-Loss triggered at ${pnl.toFixed(2)}%`;
    }

    if (shouldSell) {
      logTrade(pos.symbol, currentPrice, pnl, pos.pnlDollar, reason);
      alerts.push({
        symbol: pos.symbol,
        qty: pos.qty,
        pnlPct: pnl,
        pnlDollar: pos.pnlDollar,
        reason: reason
      });
    }
  }

  console.log(JSON.stringify(alerts));
}

main();
