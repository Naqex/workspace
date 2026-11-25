"""Registered Development-only cross-market markout, with no simulated stops."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo

import numpy as np

from prop_v26_common import ROOT, V19, FIRST, DEV_END, read, sha
from prop_v15_evidence import bars_for
from prop_v16_paths import CausalFlatSchedule
from prop_v6_data import aggregate
from prop_v21_common import compressed, save
from quant_core.ftmo_execution_and_calendar import gold_calendar
from quant_core.job_workspace import JobWorkspace
from quant_core.native_hourly_source import IndexedUs500Store, PairedHourlyStore
from quant_core.prop_lifecycle_and_parity import bindings
from quant_core.vectorized_stage0_scanner import DAY, HOUR, economics, endpoint_indices
import prop_v21_common as evidence

PROTOCOL = Path("planning/research/PROP-N1-PROTOCOL-20261118.md")
WORKSPACE = Path(__file__).resolve().parents[2]
BASE = ROOT / "prop-n1-stage0-20261118"
DEVELOPMENT_YEARS = range(2018, 2024)


def verify_commit(path):
    committed = subprocess.check_output(["git", "show", "HEAD:" + Path(path).resolve().relative_to(WORKSPACE).as_posix()])
    if committed.replace(b"\r\n", b"\n") != Path(path).read_bytes().replace(b"\r\n", b"\n"):
        raise ValueError("N1_INPUT_NOT_COMMITTED")


def exact_hour(bars, end):
    left, right = bars["t"].searchsorted([end - HOUR, end])
    part = bars[left:right]
    if len(part) != 60 or not np.array_equal(part["t"], np.arange(end - HOUR, end, 60000)):
        return None
    return part


def gold_events(index, gold, schedule):
    days = range(FIRST // DAY, DEV_END // DAY)
    ny = ZoneInfo("America/New_York")
    result = []
    coverage = defaultdict(lambda: dict(scheduled=0, complete=0))
    for day in days:
        date = datetime.fromtimestamp(day * 86400, timezone.utc)
        at = int(datetime(date.year, date.month, date.day, 10, 30, tzinfo=ny).timestamp() * 1000)
        if date.weekday() > 4 or schedule.off_kind(at, "XAUUSD") or schedule.off_kind(at, "US500"):
            continue
        stats = coverage[date.year]
        stats["scheduled"] += 1
        equity, target = exact_hour(index, at), exact_hour(gold, at)
        if equity is None or target is None:
            continue
        stats["complete"] += 1
        opening, close = int(equity[0]["bo"]), int(equity[-1]["bc"])
        if 400 * (opening - close) >= opening:
            result.append((at, 1, int(target["bl"].min()) - 1))
    return result, coverage


def peer_signal(gbp, aud, eur):
    """Integer comparisons of returns preserve the registered boundary exactly."""
    for side in (1, -1):
        g, a, e = (side * (closing - opening) for opening, closing in (gbp, aud, eur))
        if (1000 * g >= gbp[0] and 1000 * a >= aud[0] and e >= 0
                and 2 * e * gbp[0] <= g * eur[0] and 2 * e * aud[0] <= a * eur[0]):
            return side
    return 0


def eur_events(gbp, aud, eur, schedule):
    hours = {row[0] + HOUR: row for row in aggregate(eur) if row[5] == 60}
    peers = [{int(row["t"]) + HOUR: (int(row["bo"]), int(row["bc"])) for row in bars}
             for bars in (gbp, aud)]
    coverage = defaultdict(lambda: dict(scheduled=0, complete=0))
    result = []
    for day in range(FIRST // DAY, DEV_END // DAY):
        if (day + 3) % 7 >= 5:
            continue
        year = datetime.fromtimestamp(day * 86400, timezone.utc).year
        stats = coverage[year]
        used = False
        for hour in range(8, 17):
            at = day * DAY + hour * HOUR
            if schedule.off_kind(at, "EURUSD"):
                continue
            stats["scheduled"] += 1
            if at not in hours or any(at not in peer for peer in peers):
                continue
            minute = exact_hour(eur, at)
            if minute is None:
                continue
            stats["complete"] += 1
            if used:
                continue
            row = hours[at]
            side = peer_signal(peers[0][at], peers[1][at], (row[1], row[4]))
            if side:
                stop = int(minute["bl"].min()) - 1 if side == 1 else int(minute["ah"].max()) + 1
                result.append((at, side, stop))
                used = True
    return result, coverage


def intervals(values, timestamps):
    if len(values) < 2:
        return None
    _, codes = np.unique(timestamps // (7 * DAY), return_inverse=True)
    count = np.bincount(codes)
    total = np.bincount(codes, weights=values)
    if len(count) < 2:
        return None
    take = np.random.default_rng(261118).integers(len(count), size=(2000, len(count)))
    means = total[take].sum(axis=1) / count[take].sum(axis=1)
    return np.quantile(means, [.025, .975]).tolist()


def screen(asset, events, bars, hours, schedule, base_days):
    decision, side, stop = np.asarray(events, dtype=np.int64).reshape(-1, 3).T
    entry_index, valid = endpoint_indices(bars, decision, DEV_END)
    entry_time = bars["t"][entry_index]
    target = entry_time + hours * HOUR
    exit_index, known = endpoint_indices(bars, target, DEV_END)
    exit_time = bars["t"][exit_index]
    valid &= known & (exit_time >= entry_time) & (exit_time < DEV_END)
    valid &= np.asarray([not schedule.off_kind(int(a), asset)
                         and not schedule.off_kind(int(b), asset)
                         and b <= schedule.cutoff(int(a), asset) for a, b in zip(entry_time, exit_time)], dtype=bool)
    entry = np.where(side == 1, bars["ao"][entry_index], bars["bo"][entry_index])
    exit_ = np.where(side == 1, bars["bo"][exit_index], bars["ao"][exit_index])
    cost = economics(asset, side, entry, exit_, entry_time, np.maximum(entry_time, exit_time), "SYM")
    scale = 1000 if asset == "XAUUSD" else 100000
    spread = bars["ao"][entry_index] - bars["bo"][entry_index]
    friction = spread / scale + cost["commission"] + cost["other"]
    natural = side * (entry - stop) / scale
    usable = valid & (natural > 0)
    # Integer comparison: price and stop in native units, XAU costs in
    # 1/10000 USD/oz after commission cent rounding per lot.
    multiple = 10 if asset == "XAUUSD" else 1
    fee = np.rint((cost["commission"] + cost["other"]) * scale * multiple).astype(np.int64)
    pass_cost = usable & (100 * (spread * multiple + fee) <= 12 * side * (entry - stop) * multiple)
    years = decision.astype("datetime64[ms]").astype("datetime64[Y]").astype(int) + 1970
    months = decision.astype("datetime64[ms]").astype("datetime64[M]").astype(int)
    annual = []
    for year in DEVELOPMENT_YEARS:
        raw = years == year
        priced = raw & valid
        geometry = raw & usable
        n = int(raw.sum())
        net = cost["net"][priced]
        f = friction[priced]
        median_ratio = float(np.median(friction[geometry]) / np.median(natural[geometry])) if geometry.any() else None
        annual.append(dict(year=year, raw=n, days=len(set(decision[raw] // DAY)),
            empty_months=12-len(set(months[raw])), priced=int(priced.sum()),
            coverage=float(priced.sum()/n) if n else None, invalid_stop=int((priced & ~usable).sum()),
            median_natural=float(np.median(natural[geometry])) if geometry.any() else None,
            median_scale=median_ratio, retention=float((pass_cost & raw).sum()/n) if n else None,
            mean_net=float(net.mean()) if len(net) else None, mean_friction=float(f.mean()) if len(f) else None,
            net_quantiles=np.quantile(net,[.1,.5,.9]).tolist() if len(net) else None,
            mean_net_week_bootstrap_95=intervals(net,decision[priced]),
            days_without_baseline=len(set(decision[raw] // DAY) - base_days)))
    rows = [dict(decision=int(t), side=int(s), stop=int(z), entry_at=int(entry_time[i]) if valid[i] else None,
                 exit_at=int(exit_time[i]) if valid[i] else None,
                 net=float(cost["net"][i]) if valid[i] else None, pass_cost=bool(pass_cost[i]))
            for i,(t,s,z) in enumerate(events)]
    return annual, rows


def classify(annual):
    reasons = defaultdict(list)
    for row in annual:
        year = row["year"]
        if row["raw"] < 40:
            reasons["CADENCE_OR_SAMPLE_SHORTFALL"].append(f"{year}:LT40_RAW")
        if row["raw"] and row["coverage"] < .99:
            reasons["DATA_PATH_INCOMPLETE"].append(f"{year}:LT99PCT_PRICED")
        if row["priced"] and (row["mean_net"] <= 0 or row["mean_net"] < row["mean_friction"]):
            reasons["ECONOMIC_FAIL"].append(f"{year}:MARKOUT")
        if row["priced"] and (row["median_scale"] is None or row["median_scale"] > .12 or row["retention"] < .50):
            reasons["ECONOMIC_FAIL"].append(f"{year}:FRICTION_SCALE")
    return dict(reasons)


def main():
    verify_commit(PROTOCOL)
    verify_commit(__file__)
    runtime = JobWorkspace(BASE / "screen", WORKSPACE)
    root = runtime.activate()
    try:
        with bindings(evidence, JOB=root):
            sources = ROOT / "ensemble-and-storage-v11-20261115/source-admission-v11.json"
            dev = ROOT / "evidence-and-lifecycle-v14-20261115/source-dev-admission.json"
            baseline = V19 / "Dev-OLHC-PRIMARY-trades.json"
            pins = dict(admission=sha(sources), dev=sha(dev), baseline=sha(baseline))
            save("registration.json", dict(protocol_sha256=sha(PROTOCOL), code_sha256=sha(__file__),
                 head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                 first=FIRST, cutoff_exclusive=DEV_END, primary_hours=4, diagnostic_hours=2,
                 input_pins=pins))
            admission = read(sources)
            gold, eur = (bars_for(asset, True) for asset in ("XAUUSD", "EURUSD"))
            index = IndexedUs500Store(admission["minute_indices"]["US500"], FIRST, DEV_END).bars()
            peers = []
            for asset in ("GBPUSD", "AUDUSD"):
                source = dict(admission["hourly_indices"][asset])
                source["books"] = [book for book in source["books"] if book["last"] < DEV_END]
                peers.append(PairedHourlyStore(source, FIRST, DEV_END).bars())
            schedule = CausalFlatSchedule(gold_calendar(FIRST, DEV_END).events.values())
            base_days = {r["entry_msc"] // DAY for r in read(baseline)}
            results = []
            series = [
                ("N1-GOLD-EQUITY", "XAUUSD", gold, gold_events(index, gold, schedule)),
                ("N1-EUR-PEERS", "EURUSD", eur, eur_events(*peers, eur, schedule)),
            ]
            for identity, asset, bars, (events, coverage) in series:
                scopes = {}
                for hours in (4,2):
                    annual, rows = screen(asset, events, bars, hours, schedule, base_days)
                    compressed(f"{identity}-{hours}h", rows)
                    scopes[str(hours)] = annual
                reasons = classify(scopes["4"])
                results.append(dict(id=identity, asset=asset, input_coverage=coverage,
                                    horizons=scopes, reasons=reasons, stage0_passed=not reasons))
            summary = dict(trials=results, input_pins=pins, registration=sha(root / "registration.json"))
            save("screen-results.json", summary)
            print([(r["id"], r["stage0_passed"], [a["raw"] for a in r["horizons"]["4"]]) for r in results],flush=True)
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
