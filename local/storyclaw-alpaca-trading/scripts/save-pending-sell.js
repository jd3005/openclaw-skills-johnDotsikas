#!/usr/bin/env node
const fs = require('fs');
const { getStatePath } = require('./config-loader');

const [,, symbol, qty] = process.argv;
if (!symbol || !qty) process.exit(1);
const statePath = getStatePath('john', 'alpaca-discord-pending-sell.json');
fs.writeFileSync(statePath, JSON.stringify({ symbol, qty: Number(qty), createdAt: Date.now() }, null, 2));
console.log(statePath);
