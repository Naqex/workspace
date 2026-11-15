"""V10 cached Development admission; binary M1 reuse, no new provider or validation."""
from pathlib import Path
import hashlib
import json
import subprocess
import numpy as np

from prop_campaign_source import ROOT, stamp, read, write_json
from quant_core.market_data_store import MarketDataStore, BAR
from prop_v5_data import QDM
from prop_v9_eurusd import ingest

JOB = ROOT / "enterprise-alpha-v10-20261115"
FIRST, END, SEED = stamp("2018-01-01"), stamp("2024-01-01"), stamp("2017-11-01")


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def prepare():
    JOB.mkdir(exist_ok=True)
    cache = ROOT / "gold-continuous-B2-20261113-v1/source-cache"
    store = MarketDataStore(cache)
    bars = store.bars(SEED, END)
    applied = []
    patches = read(ROOT / "prop-atlas-v2-20261114/gold-source-corrections.json")["patches"]
    for p in patches:
        if SEED <= p["at"] < END:
            i = int(bars["t"].searchsorted(p["at"]))
            if i == len(bars) or bars["t"][i] != p["at"]:
                raise ValueError("source_patch_missing")
            for field, value in zip(("bo", "bh", "bl", "bc"), p["corrected"]):
                bars[field][i] = value
            applied.append(p["at"])
    for field in ("o", "h", "l", "c"):
        bars["a" + field] = bars["b" + field] + 338
    gold_path = JOB / "XAUUSD-M1.bin"
    if gold_path.exists():
        raise ValueError("preserve_existing_V10_source")
    bars.tofile(gold_path)
    proofs = {"XAUUSD": dict(path=str(gold_path), binary_sha256=sha(gold_path),
        records=len(bars), canonical_manifest_sha256=sha(cache / "manifest.json"),
        raw_declared_sha256=store.raw_declared_sha256, patch_timestamps=applied,
        source="QDM_BID_M1_WITH_REGISTERED_CORRECTIONS", Ask_proxy=.338)}
    del bars, store
    folder = JOB / "eur-export"
    folder.mkdir()
    args = ["-data", "action=export", "symbols=EURUSD_TW", "timeframe=M1", "timezone=UTC",
            "datefrom=2017.11.01", "dateto=2023.12.31", "outputdir=" + folder.as_posix(),
            "format=Custom", "cIncludeHeader=true", "cHeader=DateTime,Open,High,Low,Close",
            "cFormat=[Date:yyyy.MM.dd HH:mm:ss],[Open],[High],[Low],[Close]"]
    with (folder / "export.log").open("w") as log:
        result = subprocess.run([str(QDM / "qdmcli.exe"), *args], cwd=QDM, stdout=log,
            stderr=subprocess.STDOUT, timeout=240, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    files = list(folder.glob("*.csv"))
    if result.returncode or len(files) != 1:
        raise ValueError("V10_EUR_cached_export_failed")
    bars = ingest(files[0], SEED, END)
    eur_path = JOB / "EURUSD-M1.bin"
    bars.tofile(eur_path)
    proofs["EURUSD"] = dict(path=str(eur_path), binary_sha256=sha(eur_path),
        records=len(bars), raw_path=str(files[0]), raw_sha256=sha(files[0]),
        source="QDM_CACHED_BID_M1", Ask_proxy=.0001)
    write_json(JOB / "source-admission.json", dict(assets=proofs, first=FIRST, seed=SEED, end=END,
        native_Ask=False, cached_only=True, validation_prices_opened=False,
        skipped_assets={a: "NO_ADMITTED_LOCAL_M1_H1_FULL_2018_2023_PLUS_COST_SPEC"
                        for a in ("US500", "USDJPY", "GBPUSD")}))
    print(dict(stage="V10_source_prepared", assets={k: v["records"] for k, v in proofs.items()}), flush=True)


def sources():
    proof = read(JOB / "source-admission.json")
    out = {}
    for asset, row in proof["assets"].items():
        if sha(row["path"]) != row["binary_sha256"]:
            raise ValueError("V10_source_binary_changed")
        out[asset] = np.memmap(row["path"], dtype=BAR, mode="r")
    return out


if __name__ == "__main__":
    prepare()
