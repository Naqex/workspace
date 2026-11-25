// One-Time Preregistered Holdout Fetcher (Protocol 521926f):
// Fetches Native M1 Bid & Ask for all 10 active portfolio assets for 2025-01-01 .. 2026-11-21 UTC.
// Writes ONLY to separate Holdout job root (NEVER touches .runtime/hot-m1-cache/ Development data!).
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const dukascopy = require(path.resolve('D:/ANNAM/TradingWorkspace/.runtime/research-data/node_modules/dukascopy-node'));

const OUT_ROOT = path.resolve(process.argv[2] || 'E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/holdout-2025-2026-m1-20261123');
const CACHE_DIR = path.join(OUT_ROOT, 'cache');
const RAW_DIR = path.join(OUT_ROOT, 'raw-json');
fs.mkdirSync(CACHE_DIR, { recursive: true });
fs.mkdirSync(RAW_DIR, { recursive: true });

const ASSETS = [
  { asset: 'USDJPY', inst: 'usdjpy', prefix: 'usdjpy' },
  { asset: 'GBPUSD', inst: 'gbpusd', prefix: 'gbpusd' },
  { asset: 'EURUSD', inst: 'eurusd', prefix: 'eurusd' },
  { asset: 'GBPJPY', inst: 'gbpjpy', prefix: 'gbpjpy' },
  { asset: 'AUDUSD', inst: 'audusd', prefix: 'audusd' },
  { asset: 'USDCAD', inst: 'usdcad', prefix: 'usdcad' },
  { asset: 'EURJPY', inst: 'eurjpy', prefix: 'eurjpy' },
  { asset: 'XAUUSD', inst: 'xauusd', prefix: 'xauusd' },
  { asset: 'US500',  inst: 'usa500idxusd', prefix: 'us500' },
  { asset: 'US100',  inst: 'usatechidxusd', prefix: 'us100' },
];

const WINDOWS = [
  { tag: '2025', from: '2025-01-01T00:00:00Z', to: '2026-01-01T00:00:00Z' },
  { tag: '2026', from: '2026-01-01T00:00:00Z', to: '2026-11-21T00:00:00Z' },
];

async function fetchOne(item, win, priceType) {
  const outPath = path.join(RAW_DIR, `${item.prefix}-m1-${priceType}-${win.tag}.json`);
  if (fs.existsSync(outPath) && fs.statSync(outPath).size > 5000) {
    console.log(`CACHED ${item.asset} ${win.tag} ${priceType}`);
    return;
  }
  const t0 = Date.now();
  const rows = await dukascopy.getHistoricalRates({
    instrument: item.inst,
    dates: { from: new Date(win.from), to: new Date(win.to) },
    timeframe: 'm1',
    priceType,
    format: 'array',
    ignoreFlats: true,
    batchSize: 12,
    pauseBetweenBatchesMs: 60,
    retryCount: 4,
    pauseBetweenRetriesMs: 1500,
    useCache: true,
    cacheFolderPath: CACHE_DIR,
  });
  fs.writeFileSync(outPath, JSON.stringify(rows));
  const lastIso = rows.length ? new Date(rows[rows.length - 1][0]).toISOString().slice(0, 16) : 'EMPTY';
  console.log(`FETCHED ${item.asset.padEnd(6)} ${win.tag} ${priceType.padEnd(3)}: ${String(rows.length).padStart(7)} bars (last=${lastIso}) in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
}

async function runPool(items, concurrency, fn) {
  let idx = 0;
  async function worker() {
    while (idx < items.length) {
      const cur = items[idx++];
      await fn(cur);
    }
  }
  await Promise.all(Array.from({ length: concurrency }, () => worker()));
}

async function main() {
  const tStart = Date.now();
  await runPool(ASSETS, 4, async (item) => {
    for (const win of WINDOWS) {
      await fetchOne(item, win, 'bid');
      await fetchOne(item, win, 'ask');
    }
  });
  console.log(`HOLDOUT_FETCH_ALL_10_DONE in ${((Date.now() - tStart) / 1000).toFixed(1)}s`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
