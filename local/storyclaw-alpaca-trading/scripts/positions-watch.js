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

try {
  const positions = parsePositions(run(['positions']));
  const alerts = [];
  for (const pos of positions) {
    const rsi = parseRsi(run(['rsi', pos.symbol, '14']));
    if (rsi >= 70 || pos.pnlPct >= 8) {
      alerts.push({
        symbol: pos.symbol,
        qty: pos.qty,
        pnlPct: pos.pnlPct,
        rsi,
        reason: rsi >= 70 ? `RSI is overbought at ${rsi.toFixed(2)}` : `Open gain is ${pos.pnlPct.toFixed(2)}%`
      });
    }
  }
  console.log(JSON.stringify(alerts, null, 2));
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
