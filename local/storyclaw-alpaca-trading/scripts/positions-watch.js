#!/usr/bin/env node
const { execFileSync } = require('child_process');
const path = require('path');

const trading = path.join(__dirname, 'trading.js');
function run(args) {
  return execFileSync('node', [trading, ...args], {
    env: { ...process.env, USER_ID: 'john' },
    encoding: 'utf8'
  });
}

function parsePositions(output) {
  const blocks = output.split(/\n(?=\s{2}[A-Z])/).map(s => s.trim()).filter(Boolean);
  const positions = [];
  for (const block of blocks) {
    const lines = block.split('\n').map(x => x.trim());
    const head = lines[0] || '';
    const m = head.match(/^([A-Z/]+):\s+([0-9.]+)/);
    if (!m) continue;
    const symbol = m[1].replace('/', '');
    const qty = Number(m[2]);
    const pnlLine = lines.find(l => l.startsWith('P&L:')) || '';
    const p = pnlLine.match(/P&L:\s+\$([0-9.-]+)\s+\(([0-9.-]+)%\)/);
    positions.push({
      symbol,
      qty,
      pnl: p ? Number(p[1]) : 0,
      pnlPct: p ? Number(p[2]) : 0,
    });
  }
  return positions;
}

function parseRsi(output) {
  const m = output.match(/RSI\([^)]*\):\s*([0-9.]+)/);
  return m ? Number(m[1]) : 50;
}

function runZScore(symbol) {
  try {
    const output = execFileSync('python3', [path.join(__dirname, 'zscore_strategy.py'), symbol], {
      env: { ...process.env, USER_ID: 'john' },
      encoding: 'utf8'
    });
    return JSON.parse(output);
  } catch (e) {
    return { error: e.message };
  }
}

try {
  const positions = parsePositions(run(['positions']));
  const alerts = [];
  for (const pos of positions) {
    const zResult = runZScore(pos.symbol);
    if (zResult.error) continue;

    const isExit = zResult.recommendation.startsWith("EXIT");
    const isStop = zResult.recommendation.includes("STOP");
    
    if (isExit || isStop) {
      alerts.push({
        symbol: pos.symbol,
        qty: pos.qty,
        pnlPct: pos.pnlPct,
        z_score: zResult.z_score,
        reason: zResult.reasoning
      });
    }
  }
  console.log(JSON.stringify(alerts, null, 2));
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
