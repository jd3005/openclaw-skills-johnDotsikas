#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const config = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'config.monitor.json'), 'utf8'));
const trading = path.join(__dirname, 'trading.js');
const userId = config.userId || 'john';

function request(args) {
  return execFileSync('node', [trading, ...args], {
    env: { ...process.env, USER_ID: userId },
    encoding: 'utf8',
  });
}

function parseQuote(output) {
  const bid = Number((output.match(/Bid: \$([0-9.]+)/) || [])[1] || 0);
  const ask = Number((output.match(/Ask: \$([0-9.]+)/) || [])[1] || 0);
  const mid = Number((output.match(/Mid: \$([0-9.]+)/) || [])[1] || 0);
  const price = ask > 0 ? ask : bid > 0 ? bid : mid;
  const spreadPct = bid > 0 && ask > 0 ? ((ask - bid) / ((ask + bid) / 2)) * 100 : null;
  return { price, spreadPct };
}

function parseRsi(output) {
  return Number((output.match(/RSI\([^)]*\):\s*([0-9.]+)/) || [])[1] || 50);
}

function parseBars(output) {
  return output.split('\n').map((line) => {
    const m = line.match(/(\d{4}-\d{2}-\d{2}): O:([0-9.]+) H:([0-9.]+) L:([0-9.]+) C:([0-9.]+) V:([0-9.]+)/);
    if (!m) return null;
    return { c: Number(m[5]) };
  }).filter(Boolean);
}

function sma(values, period) {
  if (values.length < period) return null;
  const slice = values.slice(-period);
  return slice.reduce((a, b) => a + b, 0) / period;
}

function score(symbol) {
  try {
    const quote = parseQuote(request(['quote', symbol]));
    const rsi = parseRsi(request(['rsi', symbol, '14']));
    const closes = parseBars(request(['bars', symbol, '30'])).map((b) => b.c).filter((n) => Number.isFinite(n) && n > 0);
    if (!quote.price || closes.length < 6) return null;

    const last = closes[closes.length - 1];
    const prev = closes[closes.length - 2] ?? last;
    const fiveDayAgo = closes[closes.length - 6] ?? last;
    const sma5 = sma(closes, 5);
    const sma20 = sma(closes, 20);
    const breakout = closes.length >= 20 ? Math.max(...closes.slice(-20, -1)) : null;
    const momentum5 = fiveDayAgo ? ((last - fiveDayAgo) / fiveDayAgo) * 100 : 0;

    let points = 0;
    const reasons = [];

    if (rsi <= 35) { points += 28; reasons.push(`RSI oversold at ${rsi.toFixed(2)}`); }
    else if (rsi <= 42) { points += 18; reasons.push(`RSI rebound zone at ${rsi.toFixed(2)}`); }
    else if (rsi >= 70) { points -= 12; reasons.push(`RSI overbought at ${rsi.toFixed(2)}`); }

    if (sma5 != null && sma20 != null) {
      if (last > sma5 && sma5 > sma20) { points += 22; reasons.push('Price above 5-day and 20-day trend stack'); }
      else if (last > sma20) { points += 10; reasons.push('Price holding above 20-day average'); }
      else { points -= 8; reasons.push('Price below 20-day average'); }
    } else if (sma5 != null) {
      if (last > sma5) { points += 8; reasons.push('Price above short-term average'); }
      else { points -= 4; reasons.push('Price below short-term average'); }
    }

    if (momentum5 > 3) { points += 18; reasons.push(`5-day momentum strong at ${momentum5.toFixed(2)}%`); }
    else if (momentum5 > 0.5) { points += 10; reasons.push(`5-day momentum positive at ${momentum5.toFixed(2)}%`); }
    else if (momentum5 < -3) { points -= 8; reasons.push(`5-day momentum weak at ${momentum5.toFixed(2)}%`); }

    if (quote.spreadPct != null) {
      if (quote.spreadPct <= 0.24) { points += 18; reasons.push(`Spread tight at ${quote.spreadPct.toFixed(2)}%`); }
      else if (quote.spreadPct <= 0.6) { points += 8; reasons.push(`Spread acceptable at ${quote.spreadPct.toFixed(2)}%`); }
      else { points -= 16; reasons.push(`Spread wide at ${quote.spreadPct.toFixed(2)}%`); }
    } else {
      reasons.push('Quote spread unavailable');
    }

    if (last > prev) { points += 8; reasons.push('Latest close stronger than prior close'); }
    if (breakout != null && last >= breakout * 0.995) { points += 16; reasons.push('Trading near 20-day breakout'); }
    if (['SPY','QQQ','AAPL','MSFT','NVDA'].includes(symbol)) { points += 10; reasons.push('Core watchlist symbol'); }

    return { symbol, score: points, price: quote.price, rsi, momentum5, spreadPct: quote.spreadPct, reasons };
  } catch (error) {
    return { symbol, error: error.message, score: -999 };
  }
}

const symbols = config.stockWatchlist || [];
const ranked = symbols.map(score).filter(Boolean).sort((a, b) => b.score - a.score);
console.log(JSON.stringify(ranked.slice(0, 5), null, 2));
