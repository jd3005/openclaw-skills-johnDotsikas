#!/usr/bin/env node
const fs = require('fs');
const { execFileSync } = require('child_process');
const path = require('path');
const { getStatePath } = require('./config-loader');

const reply = (process.argv.slice(2).join(' ') || '').trim().toLowerCase();
const buyStatePath = getStatePath('john', 'alpaca-discord-pending.json');
const sellStatePath = getStatePath('john', 'alpaca-discord-pending-sell.json');
const trading = path.join(__dirname, 'trading.js');

if (reply === 'place it') {
  if (!fs.existsSync(buyStatePath)) {
    console.log('NO_PENDING_BUY');
    process.exit(0);
  }
  const pending = JSON.parse(fs.readFileSync(buyStatePath, 'utf8'));
  const out = execFileSync('node', [trading, 'buy-amount', pending.symbol, String(pending.amount)], {
    env: { ...process.env, USER_ID: 'john' },
    encoding: 'utf8'
  });
  fs.unlinkSync(buyStatePath);
  console.log(out.trim());
  process.exit(0);
}

if (reply === 'sell it') {
  if (!fs.existsSync(sellStatePath)) {
    console.log('NO_PENDING_SELL');
    process.exit(0);
  }
  const pending = JSON.parse(fs.readFileSync(sellStatePath, 'utf8'));
  const out = execFileSync('node', [trading, 'sell-all', pending.symbol], {
    env: { ...process.env, USER_ID: 'john' },
    encoding: 'utf8'
  });
  fs.unlinkSync(sellStatePath);
  console.log(out.trim());
  process.exit(0);
}

if (reply === "don't place it" || reply === 'dont place it' || reply === 'skip this one' || reply === 'skip' || reply === "i'll do it manually" || reply === 'ill do it manually') {
  if (fs.existsSync(buyStatePath)) {
    const pending = JSON.parse(fs.readFileSync(buyStatePath, 'utf8'));
    fs.unlinkSync(buyStatePath);
    console.log(`SKIPPED ${pending.symbol}`);
    process.exit(0);
  }
  if (fs.existsSync(sellStatePath)) {
    const pending = JSON.parse(fs.readFileSync(sellStatePath, 'utf8'));
    fs.unlinkSync(sellStatePath);
    console.log(`SKIPPED ${pending.symbol}`);
    process.exit(0);
  }
  console.log('NO_PENDING_ALERT');
  process.exit(0);
}

console.log('UNRECOGNIZED_REPLY');
