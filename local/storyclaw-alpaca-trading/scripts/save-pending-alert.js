#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { getStatePath } = require('./config-loader');

const [,, symbol, amount, price, score] = process.argv;
if (!symbol || !amount) process.exit(1);

const statePath = getStatePath('john', 'alpaca-discord-pending.json');
const payload = {
  symbol,
  amount: Number(amount),
  price: Number(price || 0),
  score: Number(score || 0),
  createdAt: Date.now()
};
fs.writeFileSync(statePath, JSON.stringify(payload, null, 2));
console.log(statePath);
