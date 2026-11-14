"""Local source recovery audit and strictly timestamp-only holdout intake."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import csv
import io
import subprocess
import numpy as np
from prop_v5_common import JOB, V3, V4, ATLAS, read, write_json, event

QDM = Path("D:/ANNAM/TradingWorkspace/projects/mt5-tradingview-backtester/foundation_v2/.runtime/quantdatamanager")


def native(args):
    p = subprocess.run([str(QDM / "qdmcli.exe"), *args], cwd=QDM,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if p.returncode or "Exit app - ok" not in p.stdout:
        raise ValueError("QDM_metadata_export_failed")
    return p.stdout


def recovery():
    text = native(["-symbol", "action=list"])
    header = next(l for l in text.splitlines() if l.startswith("Symbol,") and "Timeframe" in l)
    symbols = list(csv.DictReader(io.StringIO(text[text.index(header):].split("Data listed.", 1)[0])))
    write_json(JOB / "qdm-inventory.json", symbols)
    old = read(ATLAS / "atlas-stage0.json")
    missing = [c for c in old["cells"] if any(y["priced"] < y["raw"] for y in c["annual"])]
    v3 = {c["cell"]["id"]: c for c in read(V3 / "natural-atlas.json")["cells"]}
    endpoint = read(V3 / "endpoint-recovery.json")
    rows = []
    for c in missing:
        name = c["cell"]["id"]
        now = v3[name]
        rows.append(dict(id=name, asset=c["cell"]["asset"], old_annual=c["annual"],
                         v3_funnel=now["funnel"], v3_complete=now["source_path_complete"],
                         status_counts=now["status_counts"],
                         stage0_pass=c["stage0_pass"],
                         recovery="V3_clock_repair_reused" if name.startswith("US500")
                         else "H1_only_partial_source_still_missing"))
    census = read(JOB / "file-census.json")
    raw = [r for r in census if Path(r["path"]).suffix.lower() in (".csv", ".bi5", ".bin", ".db")]
    gbp_symbols = [s for s in symbols if s.get("Instrument") == "GBPUSD"]
    write_json(JOB / "source-recovery.json", dict(
        original_incomplete=len(rows), cells=rows, endpoint_recovery=endpoint,
        raw_fx_candidates=raw, gbp_cached_symbols=gbp_symbols,
        gbp_status="NO_LOCAL_M1_TICK_SOURCE" if not gbp_symbols and not raw else "NEEDS_SOURCE_ADMISSION",
        third_selected=[], new_provider_downloads=0,
        scope="No new price/source facts available beyond V3 repairs; conditional H1 not promoted",
        v3_third_audit_sha256=None))
    event("source_recovery_complete", old_incomplete=len(rows), gbp_native=bool(gbp_symbols))


def timestamp_file(path):
    """Only a DateTime field is accepted; OHLC/Bid/Ask exports fail closed."""
    values = []
    with Path(path).open("r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        if header != ["DateTime"]:
            raise ValueError("holdout_export_has_non_timestamp_columns")
        for row in reader:
            if len(row) != 1:
                raise ValueError("holdout_price_column_forbidden")
            d = datetime.strptime(row[0], "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
            if not datetime(2025,1,1,tzinfo=timezone.utc) <= d < datetime(2026,11,1,tzinfo=timezone.utc):
                raise ValueError("blind_audit_time_fence")
            values.append(int(d.timestamp()) // 60)
    a = np.array(values, dtype="int64")
    if len(a) and np.any(np.diff(a) <= 0):
        raise ValueError("blind_timestamp_order")
    return a


def blind():
    inventory = read(JOB / "qdm-inventory.json")
    outputs = []
    for asset in ("XAUUSD", "EURUSD", "GBPUSD"):
        source = next((s for s in inventory if s.get("Instrument") == asset and s.get("Timeframe") == "M1"), None)
        if not source:
            outputs.append(dict(asset=asset, status="NO_CACHED_M1", stage1_price_qualified=False))
            continue
        target = JOB / f"blind-{asset}-timestamps"
        target.mkdir(exist_ok=False)
        native(["-data", "action=export", f"symbols={source['Symbol']}", "timeframe=M1",
                "timezone=UTC", "datefrom=2025.01.01", "dateto=2026.10.31",
                f"outputdir={target.as_posix()}", "format=Custom", "cIncludeHeader=true",
                "cHeader=DateTime", "cFormat=[Date:yyyy.MM.dd HH:mm:ss]"])
        files = list(target.glob("*.csv"))
        if len(files) != 1:
            raise ValueError("blind_export_file_count")
        times = timestamp_file(files[0])
        first = int(datetime(2025,1,1,tzinfo=timezone.utc).timestamp())//60
        last = int(datetime(2026,11,1,tzinfo=timezone.utc).timestamp())//60
        days = []
        for day in range(first//1440*1440, last, 1440):
            d = datetime.fromtimestamp(day*60,timezone.utc)
            a = times[(times >= day+7*60) & (times < day+21*60)]
            gaps = np.diff(np.r_[day+7*60-1, a, day+21*60])-1
            days.append(dict(day=d.date().isoformat(), weekday=d.weekday(),
                             main_session_minutes=len(a),
                             max_missing_minutes=int(max(gaps)) if len(gaps) else 840,
                             gaps_gt15=int(sum(gaps>15)),
                             main_session_timestamp_complete=bool(len(a) and max(gaps)<=15),
                             holiday_or_source_gap_unresolved=bool(d.weekday()<5 and (not len(a) or max(gaps)>15))))
        outputs.append(dict(
            asset=asset, source_metadata=source, status="TIMESTAMPS_ONLY",
            minutes=len(times), first=date_label(times[0]) if len(times) else None,
            last=date_label(times[-1]) if len(times) else None, days=days,
            weekdays_complete=sum(r["weekday"]<5 and r["main_session_timestamp_complete"] for r in days),
            weekdays_unknown=sum(r["holiday_or_source_gap_unresolved"] for r in days),
            timestamp_export=str(files[0]), stage1_price_qualified=False,
            reason="No Bid/Ask/order/spread checks; holidays and historical feed sessions unverified"))
        event("blind_timestamp_audit", asset=asset, minutes=len(times))
    write_json(JOB / "blind-holdout-audit.json", dict(
        assets=outputs, price_columns_parsed=0, indicator_calls=0, signal_calls=0,
        pnl_calls=0, provider_updates=0, pristine_oos_certified=False,
        exact_stage1_price_intervals_certified=[]))


def date_label(minute):
    return datetime.fromtimestamp(int(minute)*60, timezone.utc).isoformat()


if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("recovery","blind"))
    globals()[p.parse_args().stage]()
