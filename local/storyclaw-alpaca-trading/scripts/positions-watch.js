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

async function main() {
  const positions = await getPositions();
  const alerts = [];

  for (const pos of positions) {
    const strategy = getStrategyRecommendation(pos.symbol);
    if (!strategy) continue;

    const isAlpha = strategy.mode === "ALPHA";
    const pnl = pos.pnlPct;
    
    let shouldSell = false;
    let reason = "";

    // 1. Hard Take Profits
    if (isAlpha && pnl >= 20.0) {
      shouldSell = true;
      reason = `ALPHA: Take-Profit target reached at ${pnl.toFixed(2)}%`;
    } else if (!isAlpha && pnl >= 6.0) {
      shouldSell = true;
      reason = `SHIELD: Take-Profit target reached at ${pnl.toFixed(2)}%`;
    }

    // 2. Trailing Stops (Simulated)
    // We don't have historical "peak" price here easily, so we use a simplified version:
    // If we were up > 5% and now dropped below 2% profit, exit.
    // Or just check if the strategy returns a SELL recommendation.
    if (strategy.action === "SELL") {
      shouldSell = true;
      reason = strategy.reasoning;
    }

    // 3. Hard Stop Losses
    if (isAlpha && pnl <= -3.0) {
      shouldSell = true;
      reason = `ALPHA: Hard Stop-Loss triggered at ${pnl.toFixed(2)}%`;
    } else if (!isAlpha && pnl <= -5.0) {
      shouldSell = true;
      reason = `SHIELD: Hard Stop-Loss triggered at ${pnl.toFixed(2)}%`;
    }

    if (shouldSell) {
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
