#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const { getStatePath } = require("./config-loader");

const monitorConfig = JSON.parse(
  fs.readFileSync(path.join(__dirname, "..", "config.monitor.json"), "utf8"),
);

function requestText(commandArgs) {
  return execFileSync("node", [path.join(__dirname, "trading.js"), ...commandArgs], {
    env: { ...process.env, USER_ID: monitorConfig.userId },
    encoding: "utf8",
  });
}

function parseQuoteOutput(output) {
  const bid = Number((output.match(/Bid: \$([0-9.]+)/) || [])[1] || 0);
  const ask = Number((output.match(/Ask: \$([0-9.]+)/) || [])[1] || 0);
  const mid = Number((output.match(/Mid: \$([0-9.]+)/) || [])[1] || 0);
  const price = ask > 0 ? ask : bid > 0 ? bid : mid > 0 ? mid : 0;
  const spreadPct = bid > 0 && ask > 0 ? ((ask - bid) / ((ask + bid) / 2)) * 100 : null;
  return { bid, ask, mid, price, spreadPct };
}

function parseRsiOutput(output) {
  return Number((output.match(/RSI\([^)]*\):\s*([0-9.]+)/) || [])[1] || 50);
}

function parseBarsOutput(output) {
  const lines = output.split("\n").filter((line) => /^\s*\d{4}-\d{2}-\d{2}/.test(line));
  return lines.map((line) => {
    const m = line.match(/(\d{4}-\d{2}-\d{2}[T ]?[\d:]*Z?): O:([0-9.]+) H:([0-9.]+) L:([0-9.]+) C:([0-9.]+) V:([0-9.]+)/);
    if (!m) return null;
    return {
      date: m[1],
      o: Number(m[2]),
      h: Number(m[3]),
      l: Number(m[4]),
      c: Number(m[5]),
      v: Number(m[6]),
    };
  }).filter(Boolean);
}

function safeQuote(symbol) {
  try {
    return parseQuoteOutput(requestText(["quote", symbol]));
  } catch {
    return { bid: 0, ask: 0, mid: 0, price: 0, spreadPct: null };
  }
}

function safeRsi(symbol) {
  try {
    return parseRsiOutput(requestText(["rsi", symbol, "14"]));
  } catch {
    return 50;
  }
}

function safeBars(symbol) {
  try {
    return parseBarsOutput(requestText(["bars", symbol, "40"]));
  } catch {
    return [];
  }
}

function sma(values, period) {
  if (values.length < period) return null;
  const slice = values.slice(-period);
  return slice.reduce((a, b) => a + b, 0) / period;
}

function isMarketHoursET(date = new Date()) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    weekday: "short",
    hour: "numeric",
    minute: "numeric",
    hour12: false,
  }).formatToParts(date);
  const weekday = parts.find((p) => p.type === "weekday")?.value || "";
  const hour = Number(parts.find((p) => p.type === "hour")?.value || 0);
  const minute = Number(parts.find((p) => p.type === "minute")?.value || 0);
  const dayMap = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  const day = dayMap[weekday] ?? 0;
  if (day === 0 || day === 6) return false;
  const total = hour * 60 + minute;
  return total >= 570 && total <= 960;
}

function classifyConfidence(score, isCrypto, zScore = 0) {
  const type = isCrypto ? "crypto" : "stocks";
  const { high, medium, low } = monitorConfig.sizing[type];
  let level = "low";
  let amount = low;

  if (score >= monitorConfig.thresholds.highConfidence) {
    level = "high";
    amount = high;
  } else if (score >= monitorConfig.thresholds.mediumConfidence) {
    level = "medium";
    amount = medium;
  }

  // Dynamic scaling based on Z-Score intensity (Projected Profit)
  // If Z is very extreme (e.g. 3.0), we want to invest more than if it is just 2.0.
  const intensity = Math.max(0, Math.abs(zScore) - 1.5); // Start scaling after 1.5
  const dynamicAmount = amount + (intensity * 400); // Add $400 for every point of Z beyond 1.5
  
  const finalAmount = Math.min(2000, Math.round(dynamicAmount / 25) * 25); // Round to nearest 25 and cap at 2000
  
  return { level, amount: finalAmount };
}

function scoreSetup(symbol, rsi, quote, bars, isCrypto) {
  if (!quote.price || bars.length < 6) return null;

  let score = 0;
  const reasons = [];
  const closes = bars.map((b) => b.c).filter((v) => Number.isFinite(v) && v > 0);
  if (closes.length < 6) return null;
  const sma5 = sma(closes, 5);
  const sma20 = sma(closes, 20);
  const last = closes[closes.length - 1];
  const prev = closes[closes.length - 2] ?? last;
  const fiveDayAgo = closes[closes.length - 6] ?? last;
  const momentum5 = fiveDayAgo ? ((last - fiveDayAgo) / fiveDayAgo) * 100 : 0;

  if (!isCrypto && !isMarketHoursET()) {
    score -= 8;
    reasons.push("US stock market is currently closed, so execution quality may be worse");
  }

  if (rsi <= monitorConfig.thresholds.rsiOversold) {
    score += 28;
    reasons.push(`RSI is oversold at ${rsi.toFixed(2)}`);
  } else if (rsi <= monitorConfig.thresholds.rsiRebound) {
    score += 18;
    reasons.push(`RSI is in rebound territory at ${rsi.toFixed(2)}`);
  } else if (rsi >= monitorConfig.thresholds.rsiOverbought) {
    score -= 12;
    reasons.push(`RSI is overbought at ${rsi.toFixed(2)}`);
  }

  if (sma5 && sma20) {
    if (last > sma5 && sma5 > sma20) {
      score += 22;
      reasons.push("Price is above the 5-day average and the 5-day is above the 20-day");
    } else if (last > sma20) {
      score += 10;
      reasons.push("Price is holding above the 20-day average");
    } else {
      score -= 8;
      reasons.push("Price is below the 20-day average");
    }
  }

  if (momentum5 > 3) {
    score += 18;
    reasons.push(`5-day momentum is strong at ${momentum5.toFixed(2)}%`);
  } else if (momentum5 > 0.5) {
    score += 10;
    reasons.push(`5-day momentum is positive at ${momentum5.toFixed(2)}%`);
  } else if (momentum5 < -3) {
    score -= 8;
    reasons.push(`5-day momentum is weak at ${momentum5.toFixed(2)}%`);
  }

  if (quote.spreadPct != null) {
    const maxSpread = isCrypto ? monitorConfig.thresholds.maxSpreadPctCrypto : monitorConfig.thresholds.maxSpreadPctStocks;
    if (quote.spreadPct <= maxSpread * 0.4) {
      score += 18;
      reasons.push(`Spread is tight at ${quote.spreadPct.toFixed(2)}%`);
    } else if (quote.spreadPct <= maxSpread) {
      score += 8;
      reasons.push(`Spread is acceptable at ${quote.spreadPct.toFixed(2)}%`);
    } else {
      score -= 16;
      reasons.push(`Spread is too wide at ${quote.spreadPct.toFixed(2)}%`);
    }
  } else {
    score -= 12;
    reasons.push("Quote is incomplete, so pricing confidence is lower");
  }

  if (last > prev) {
    score += 8;
    reasons.push("Latest close is stronger than the prior close");
  }

  if (isCrypto) {
    score += 4;
    reasons.push("Crypto is available 24/7");
  } else {
    score += 8;
    reasons.push("Large-cap stock with strong liquidity profile");
  }

  if (["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "BTCUSD", "ETHUSD"].includes(symbol)) {
    score += 10;
    reasons.push("Core watchlist symbol with strong market attention");
  }

  const tradeStyle = score >= monitorConfig.thresholds.highConfidence ? "higher-conviction swing" : score >= monitorConfig.thresholds.mediumConfidence ? "standard swing" : "speculative watch";
  return { symbol, score, price: quote.price, reasons, tradeStyle };
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

function shouldAlert(state, symbol, score) {
  const prev = state.alerts[symbol];
  if (!prev) return true;
  const elapsedMinutes = (Date.now() - prev.ts) / 60000;
  if (elapsedMinutes >= monitorConfig.cooldownMinutes) return true;
  return Math.abs(score - prev.score) >= 6;
}



function runZScoreStrategy(symbol) {
  try {
    const output = execFileSync("python3", [path.join(__dirname, "zscore_strategy.py"), symbol], {
      env: { ...process.env, USER_ID: monitorConfig.userId },
      encoding: "utf8",
    });
    return JSON.parse(output);
  } catch (e) {
    return { error: e.message };
  }
}

function buildAlert(setup, confidence, zResult) {
  const projectedGainPct = confidence.level === "high" ? 8 : confidence.level === "medium" ? 5 : 3;
  const projectedTarget = setup.price * (1 + projectedGainPct / 100);
  const riskNote = confidence.level === "high" ? "Still a paper trade, but this is one of the stronger setups on the board." : confidence.level === "medium" ? "Reasonable setup, but not something I would call a lock." : "More speculative, so I would keep sizing smaller.";
  
  return [
    `Paper trade idea: ${setup.symbol}`,
    `Strategy: Z-Score Mean Reversion (Expert Mode)`,
    `Z-Score: ${zResult.z_score.toFixed(2)}`,
    `Confidence: ${confidence.level} (${setup.score.toFixed(0)})`,
    `Suggested size: $${confidence.amount}`,
    `Entry idea: around $${setup.price.toFixed(2)}`,
    `Trade style: ${setup.tradeStyle}`,
    `Analysis: ${zResult.reasoning}`,
    `Why I like it: ${setup.reasons.join("; ")}`,
    `Projected upside: roughly ${projectedGainPct}% if reversion occurs, around $${projectedTarget.toFixed(2)}`,
    `Slippage sim: est. price with 0.1% slippage is $${zResult.sim_price_with_slippage.toFixed(2)}`,
    `Risk note: ${riskNote}`,
    `You can place it yourself, or tell me: alpaca buy-amount ${setup.symbol} ${confidence.amount}`,
  ].join("\n");
}

function getPositionCount() {
  try {
    const output = execFileSync("node", [path.join(__dirname, "trading.js"), "positions"], {
      env: { ...process.env, USER_ID: monitorConfig.userId },
      encoding: "utf8",
    });
    const matches = output.match(/^[A-Z/]+:/gm);
    return matches ? matches.length : 0;
  } catch {
    return 0;
  }
}

function main() {
  const state = loadState();
  const symbols = [...monitorConfig.stockWatchlist, ...monitorConfig.cryptoWatchlist];
  const allResults = [];
  const currentCount = getPositionCount();
  const minRequired = monitorConfig.minPositions || 0;

  for (const symbol of symbols) {
    const isCrypto = monitorConfig.cryptoWatchlist.includes(symbol);
    const quote = safeQuote(symbol);
    const rsi = safeRsi(symbol);
    const bars = safeBars(symbol);
    const setup = scoreSetup(symbol, rsi, quote, bars, isCrypto);
    
    if (!setup) continue;

    const zResult = runZScoreStrategy(symbol);
    if (zResult.error || zResult.z_score === undefined) continue;

    if (zResult.action === "BUY") setup.score += 20;
    if (zResult.action === "SELL") setup.score -= 20;

    allResults.push({ setup, zResult, isCrypto });
  }

  // 1. First, pick high-quality alerts (Z < -2.0)
  const alerts = [];
  const handledSymbols = new Set(currentPositions.symbols); // Don't alert/buy if already owned

  for (const res of allResults) {
    if (res.setup.score >= monitorConfig.thresholds.minAlertScore || res.zResult.action === "BUY") {
      if (!handledSymbols.has(res.setup.symbol) && shouldAlert(state, res.setup.symbol, res.setup.score)) {
        const confidence = classifyConfidence(res.setup.score, res.isCrypto, res.zResult.z_score);
        alerts.push(buildAlert(res.setup, confidence, res.zResult));
        state.alerts[res.setup.symbol] = { ts: Date.now(), score: res.setup.score };
        handledSymbols.add(res.setup.symbol);
      }
    }
  }

  // 2. If under the minimum, force-pick the best remaining "relatively undervalued" stocks
  if (currentCount + alerts.length < minRequired) {
    const slotsToFill = minRequired - (currentCount + alerts.length);
    const candidates = allResults
      .filter(r => !handledSymbols.has(r.setup.symbol))
      .filter(r => r.zResult.z_score < 0.8) // Don't force-buy if it's already overvalued
      .sort((a, b) => a.zResult.z_score - b.zResult.z_score); // Lowest Z-score first

    for (let i = 0; i < Math.min(slotsToFill, candidates.length); i++) {
      const res = candidates[i];
      const confidence = classifyConfidence(res.setup.score, res.isCrypto, res.zResult.z_score);
      const alert = buildAlert(res.setup, confidence, res.zResult);
      alerts.push(`⚠️ **FORCED ENTRY** (Portfolio < ${minRequired})\n${alert}`);
      state.alerts[res.setup.symbol] = { ts: Date.now(), score: res.setup.score };
    }
  }

  saveState(state);

  if (alerts.length === 0) {
    console.log("No trade ideas right now.");
    return;
  }

  console.log(alerts.join("\n\n---\n\n"));
}

main();
