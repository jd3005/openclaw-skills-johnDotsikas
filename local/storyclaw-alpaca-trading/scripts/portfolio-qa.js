#!/usr/bin/env node
const { execFileSync } = require('child_process');
const path = require('path');

const prompt = (process.argv.slice(2).join(' ') || '').trim().toLowerCase();
const trading = path.join(__dirname, 'trading.js');

function run(args) {
  return execFileSync('node', [trading, ...args], {
    env: { ...process.env, USER_ID: 'john' },
    encoding: 'utf8'
  });
}

function parseAccount(output) {
  const cash = Number((output.match(/Cash: \$([0-9.,]+)/) || [])[1]?.replace(/,/g, '') || 0);
  const portfolio = Number((output.match(/Portfolio Value: \$([0-9.,]+)/) || [])[1]?.replace(/,/g, '') || 0);
  const buyingPower = Number((output.match(/Buying Power: \$([0-9.,]+)/) || [])[1]?.replace(/,/g, '') || 0);
  return { cash, portfolio, buyingPower };
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
    const valueLine = lines.find(l => l.startsWith('Value:')) || '';
    const pnlLine = lines.find(l => l.startsWith('P&L:')) || '';
    const value = Number((valueLine.match(/Value:\s+\$([0-9.,-]+)/) || [])[1]?.replace(/,/g, '') || 0);
    const pnlPct = Number((pnlLine.match(/\(([0-9.-]+)%\)/) || [])[1] || 0);
    positions.push({ symbol, qty, value, pnlPct });
  }
  return positions;
}

try {
  if (prompt.includes('cash')) {
    const acct = parseAccount(run(['account']));
    console.log(`Cash: $${acct.cash.toFixed(2)} | Buying power: $${acct.buyingPower.toFixed(2)} | Portfolio value: $${acct.portfolio.toFixed(2)}`);
    process.exit(0);
  }

  if (prompt.includes('invested in') || prompt.includes('have in')) {
    const m = prompt.match(/(?:invested in|have in)\s+([a-z0-9/]+)/i);
    const symbol = m ? m[1].toUpperCase().replace('/', '') : '';
    const positions = parsePositions(run(['positions']));
    const pos = positions.find(p => p.symbol === symbol);
    if (!pos) {
      console.log(`No current position in ${symbol}.`);
      process.exit(0);
    }
    console.log(`${symbol}: value $${pos.value.toFixed(2)}, qty ${pos.qty}, P&L ${pos.pnlPct.toFixed(2)}%`);
    process.exit(0);
  }

  if (prompt.includes('portfolio') || prompt.includes('positions') || prompt.includes('invested')) {
    const positions = parsePositions(run(['positions']));
    if (!positions.length) {
      console.log('No open positions.');
      process.exit(0);
    }
    const summary = positions.map(p => `${p.symbol}: $${p.value.toFixed(2)} (${p.pnlPct.toFixed(2)}%)`).join(' | ');
    console.log(summary);
    process.exit(0);
  }

  console.log('UNRECOGNIZED_PORTFOLIO_QUESTION');
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
