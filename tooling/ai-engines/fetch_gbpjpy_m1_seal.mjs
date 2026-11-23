// Fetch GBPJPY M1 Bid & Ask (Development 2018-2024 ONLY; hard-locked < 2025-01-01T00:00:00Z)
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const dukascopy = require(path.resolve('D:/ANNAM/TradingWorkspace/.runtime/research-data/node_modules/dukascopy-node'));

const HOLDOUT_EXCLUSIVE_MS = Date.parse('2025-01-01T00:00:00Z');
const OUT_ROOT = path.resolve(process.argv[2] || 'E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/pass21-gbpjpy-m1-20261123');
const CACHE_DIR = path.join(OUT_ROOT, 'cache');
const RAW_DIR = path.join(OUT_ROOT, 'raw-json');
fs.mkdirSync(CACHE_DIR, { recursive: true });
fs.mkdirSync(RAW_DIR, { recursive: true });

async function fetchYearSide(year, priceType) {
  const from = new Date(`${year}-01-01T00:00:00Z`);
  const to = new Date(`${year + 1}-01-01T00:00:00Z`);
  if (+to > HOLDOUT_EXCLUSIVE_MS) {
    throw new Error(`Holdout guard tripped: ${to.toISOString()} > 2025-01-01T00:00:00Z`);
  }
  const outPath = path.join(RAW_DIR, `gbpjpy-m1-${priceType}-${year}.json`);
  if (fs.existsSync(outPath) && fs.statSync(outPath).size > 10000) {
    console.log(`CACHED_RAW ${year} ${priceType} (${fs.statSync(outPath).size} B)`);
    return;
  }
  const t0 = Date.now();
  const rows = await dukascopy.getHistoricalRates({
    instrument: 'gbpjpy',
    dates: { from, to },
    timeframe: 'm1',
    priceType,
    format: 'array',
    ignoreFlats: true,
    batchSize: 12,
    pauseBetweenBatchesMs: 80,
    retryCount: 3,
    pauseBetweenRetriesMs: 1500,
    useCache: true,
    cacheFolderPath: CACHE_DIR,
  });
  if (!rows.length) throw new Error(`Empty response for ${year} ${priceType}`);
  const lastMs = rows[rows.length - 1][0];
  if (lastMs >= HOLDOUT_EXCLUSIVE_MS) {
    throw new Error(`Holdout leak in response: ${lastMs}`);
  }
  fs.writeFileSync(outPath, JSON.stringify(rows));
  console.log(`FETCHED ${year} ${priceType.padEnd(3)}: ${rows.length} bars in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
}

async function main() {
  const tStart = Date.now();
  for (let year = 2018; year <= 2024; year++) {
    await fetchYearSide(year, 'bid');
    await fetchYearSide(year, 'ask');
  }
  console.log(`GBPJPY_FETCH_DONE in ${((Date.now() - tStart) / 1000).toFixed(1)}s`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
