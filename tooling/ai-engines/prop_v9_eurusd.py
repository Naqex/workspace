"""One pre-admitted conditional EURUSD S2 screen; cached M1 exports only."""
from pathlib import Path
import hashlib
import subprocess
from statistics import median
import numpy as np

from prop_campaign_source import ROOT, read, write_json, stamp
from prop_v5_data import QDM
from prop_v9 import generate, deadline, HOUR, DAY
from prop_v6_data import aggregate
from quant_core.market_data_store import BAR
from quant_core.ftmo_execution_and_calendar import gold_calendar

JOB = ROOT / "system-and-alpha-v9-20261115"
CARD = Path("planning/research/SYSTEM-AND-ALPHA-V9-EURUSD-ADMISSION-20261115.md")


def ingest(path, first, end):
    import pandas as pd
    f = pd.read_csv(path, dtype=str)
    if list(f.columns) != ["DateTime", "Open", "High", "Low", "Close"]:
        raise ValueError("EUR_export_schema")
    times = pd.to_datetime(f["DateTime"], format="%Y.%m.%d %H:%M:%S", utc=True).array.as_unit("ms").asi8
    if not len(times) or times[0] < first or times[-1] >= end or np.any(np.diff(times) <= 0):
        raise ValueError("EUR_export_time_fence")
    bars = np.zeros(len(times), dtype=BAR)
    bars["t"] = times
    for n, col in zip("ohlc", ("Open", "High", "Low", "Close")):
        values = pd.to_numeric(f[col]).to_numpy() * 100000
        if np.any(abs(values - np.rint(values)) > 1e-6):
            raise ValueError("EUR_price_grid")
        bars["b" + n] = np.rint(values).astype("int32")
        bars["a" + n] = bars["b" + n] + 10
    if np.any(bars["bl"] > np.minimum(bars["bo"], bars["bc"])) or np.any(
            bars["bh"] < np.maximum(bars["bo"], bars["bc"])):
        raise ValueError("EUR_export_OHLC")
    return bars


def measure(raw, bars, cal):
    out = []
    for r in raw:
        at = r["decision_msc"]
        i = int(bars["t"].searchsorted(at))
        if i == len(bars) or bars["t"][i] - at > 60000:
            out.append(dict(r, status="ENTRY_UNKNOWN"))
            continue
        buy = r["side"] == "BUY"
        p0 = int(bars["ao" if buy else "bo"][i])
        distance = (p0 - r["stop_units"] if buy else r["stop_units"] - p0)
        row = dict(r, entry_msc=int(bars["t"][i]), asset="EURUSD",
                   natural_sl_pips=distance / 10, friction_pips=1.9,
                   qualifies=distance > 0 and 19 / distance <= .15)
        end, why = deadline(row, cal)
        j = int(bars["t"].searchsorted(end))
        if j == len(bars) or bars["t"][j] - end > 60000 or distance <= 0:
            out.append(dict(row, status="ENDPOINT_OR_GEOMETRY_UNKNOWN"))
            continue
        px = int(bars["bo" if buy else "ao"][j])
        gross = (1 if buy else -1) * (px - p0)
        out.append(dict(row, status="OK", gross_USD_per_lot=gross,
                        net_USD_per_lot=gross - 9, net_pips=(gross - 9) / 10,
                        raw_markout_R=(gross - 9) / distance,
                        exit_msc=int(bars["t"][j]), reason=why))
    return out


def run():
    if (JOB / "eurusd-stage0.json").exists():
        raise ValueError("EUR_attempt_already_exists")
    write_json(JOB / "eurusd-registration.json", dict(
        card_sha256=hashlib.sha256(CARD.read_bytes()).hexdigest(),
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        conditional_Ask_proxy_pips=1, stress_commission_slippage_USD_lot=9))
    all_rows, proofs = [], []
    for seed, first, end in (("2018-11-01", "2019-01-01", "2021-01-01"),
                             ("2021-11-01", "2022-01-01", "2024-01-01")):
        folder = JOB / ("eur-" + first[:4])
        folder.mkdir()
        args = ["-data", "action=export", "symbols=EURUSD_TW", "timeframe=M1", "timezone=UTC",
                "datefrom=" + seed.replace("-", "."), "dateto=" + ("2020.12.31" if first.startswith("2019") else "2023.12.31"),
                "outputdir=" + folder.as_posix(), "format=Custom", "cIncludeHeader=true",
                "cHeader=DateTime,Open,High,Low,Close",
                "cFormat=[Date:yyyy.MM.dd HH:mm:ss],[Open],[High],[Low],[Close]"]
        with (folder / "export.log").open("w") as log:
            p = subprocess.run([str(QDM / "qdmcli.exe"), *args], cwd=QDM, stdout=log,
                stderr=subprocess.STDOUT, timeout=180, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        files = list(folder.glob("*.csv"))
        if p.returncode or len(files) != 1:
            raise ValueError("EUR_cached_export_failed")
        bars = ingest(files[0], stamp(seed), stamp(end))
        cal = gold_calendar(stamp(seed), stamp(end))
        raw = [r for r in generate(aggregate(bars), stamp(first), stamp(end), cal) if r["id"] == "S2.DAY"]
        rows = measure(raw, bars, cal)
        all_rows.extend(rows)
        with files[0].open("rb") as f:
            sha = hashlib.file_digest(f, "sha256").hexdigest()
        proofs.append(dict(file=str(files[0]), sha256=sha, records=len(bars), cached_only=True,
                           start=first, seed=seed, end=end, native_Ask=False))
        print(dict(stage="EUR_S2_cluster", first=first, signals=len(raw)), flush=True)
    annual, reasons = [], []
    for y in (2019, 2020, 2022, 2023):
        raw = [r for r in all_rows if r["day"].startswith(str(y))]
        valid = [r for r in raw if r["status"] == "OK"]
        accepted = [r for r in valid if r["qualifies"]]
        sl = median(r["natural_sl_pips"] for r in valid) if valid else None
        row = dict(year=y, raw=len(raw), observed=len(valid), admitted=len(accepted),
            median_SL_pips=sl, retention_pct=len(accepted) / len(raw) * 100 if raw else 0,
            mean_net_USD_lot=sum(r["net_USD_per_lot"] for r in valid) / len(valid) if valid else None,
            total_raw_markout_R=sum(r["raw_markout_R"] for r in valid))
        annual.append(row)
        for failed, label in ((len(valid) != len(raw), "ENDPOINT"), (len(accepted) < 40, "CADENCE"),
                              (row["retention_pct"] < 50, "RETENTION"),
                              (sl is None or 1.9 / sl > .15, "SCALE"),
                              (row["mean_net_USD_lot"] is None or row["mean_net_USD_lot"] <= 0, "ECONOMIC")):
            if failed:
                reasons.append(f"{y}:{label}")
    write_json(JOB / "eurusd-stage0.json", dict(annual=annual, raw=all_rows, source=proofs,
        eligible=not reasons, reasons=reasons, conditional=True, validation_opened=False))
    print(dict(stage="EUR_S2_complete", annual=annual, reasons=reasons), flush=True)


if __name__ == "__main__":
    run()
