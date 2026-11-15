"""Parity-first, alternating same-slice benchmark; no full-research speed claim."""
import hashlib
from pathlib import Path
from statistics import median
import time
import numpy as np
from prop_campaign_source import ROOT, stamp, write_json
from prop_v8_source import cache_bars
from quant_core.market_data_store import MarketDataStore


def run():
    folder = ROOT / "system-and-alpha-v9-20261115"
    first, end = stamp("2022-01-01"), stamp("2022-02-01")
    started = time.perf_counter()
    store = MarketDataStore(ROOT / "gold-continuous-B2-20261113-v1/source-cache")
    verify_seconds = time.perf_counter() - started
    before, _ = cache_bars(first, end)
    after = store.bars(first, end)
    if not np.array_equal(before, after):
        raise ValueError("benchmark_source_parity")
    samples = {"before": [], "after": []}
    for i in range(16):
        for mode in (("before", "after") if i % 2 == 0 else ("after", "before")):
            started = time.perf_counter()
            result = cache_bars(first, end)[0] if mode == "before" else store.bars(first, end)
            samples[mode].append(time.perf_counter() - started)
            if not np.array_equal(result, before):
                raise ValueError("benchmark_output_drift")
    receipt = dict(scope="warm seek of same 2022Jan M1 columns, one process, alternating",
                   rows=len(before), sample_count=16, samples=samples,
                   medians={k: median(v) for k, v in samples.items()},
                   startup_binary_validation_seconds=verify_seconds,
                   checksum_bytes=store.checksums.bytes_hashed,
                   source_sha256=hashlib.sha256(before.tobytes()).hexdigest(),
                   field_parity=True, cold_start_is_not_compared=True,
                   full_campaign_speedup_unmeasured=True)
    receipt["speedup"] = receipt["medians"]["before"] / receipt["medians"]["after"]
    write_json(folder / "core-benchmark.json", receipt)
    print(receipt["medians"], "speedup", receipt["speedup"], "startup", verify_seconds)


if __name__ == "__main__":
    run()
