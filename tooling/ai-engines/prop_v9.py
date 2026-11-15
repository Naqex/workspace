"""Finite V9 multi-regime Stage-0; no validation read for failed candidates."""
from collections import Counter, deque
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import hashlib
import json
from pathlib import Path
from statistics import median
import subprocess
import time
import numpy as np

from quant_core.market_data_store import MarketDataStore, QuoteStore, Checksums
from quant_core.ftmo_execution_and_calendar import GoldCosts, gold_calendar
from prop_campaign_source import ROOT, stamp, read, write_json, signals as original
from prop_v6_data import aggregate
from prop_v8_signals import contexts
from prop_atlas_scan import daily_context
from xau_h1_stage0_source import signal_features, HOUR, DAY

JOB = ROOT / "system-and-alpha-v9-20261115"
PROTOCOL = Path("planning/research/SYSTEM-AND-ALPHA-V9-PROTOCOL-20261115.md")
CACHE = ROOT / "gold-continuous-B2-20261113-v1/source-cache"
YEARS = (2019, 2020, 2022, 2023)
NAMES = ("S1.DAY", "S1.24H", "S2.DAY")


def structural_stop(feature, hm, buy):
    b = feature["bar"]
    bars = [hm.get(b[0] - k * HOUR) for k in range(4)]
    if any(r is None for r in bars):
        return None
    extreme = min(r[3] for r in bars) if buy else max(r[2] for r in bars)
    value = Decimal(extreme) + feature["atr_before"] * Decimal("-.1" if buy else ".1")
    return int(value.to_integral_value(rounding=ROUND_FLOOR if buy else ROUND_CEILING))


def generate(hours, first, end, calendar):
    """Closed H1 decisions and prior-only regime context; no future pivots."""
    history, _ = daily_context(hours)
    hm = {r[0]: r for r in hours if r[5] == 60}
    ctx = contexts(hours, hours[0][0])
    breakout = {r["decision_msc"]: r for r in original(hours, first=first, end=end)
                if r["recipe"] == "A"}
    seen, out = set(), []
    for f in signal_features(hours):
        at = f["at"]
        d = datetime.fromtimestamp(at / 1000, timezone.utc)
        day = at // DAY * DAY
        if not first <= at < end or not calendar.allowed(at) or f["atr_before"] is None:
            continue
        b = f["bar"]

        def add(name, buy, stop, regime):
            if stop is None or (name, day) in seen:
                return
            seen.add((name, day))
            out.append(dict(id=name, recipe=name, asset="XAUUSD", horizon=name.split(".")[-1],
                side="BUY" if buy else "SELL", decision_msc=at,
                stop_units=stop, day=d.date().isoformat(), regime=regime,
                role="CORE", regime_weight=1, d1_gate=True))

        if 8 <= d.hour <= 11 and day in history:
            upper, lower = history[day]
            buy = b[3] < lower < b[4] and b[4] > b[1]
            sell = b[2] > upper > b[4] and b[4] < b[1]
            if buy != sell:
                stop = structural_stop(f, hm, buy)
                for name in ("S1.DAY", "S1.24H"):
                    add(name, buy, stop, "PREVDAY_SWEEP")
        ratio = ctx.get(day, {}).get("ratio")
        if ratio is None:
            continue
        if ratio > 1.5 and at in breakout:
            r = breakout[at]
            add("S2.DAY", r["side"] == "BUY", r["stop_units"], "ASIA_EXPANSION")
        elif ratio <= 1.5 and 8 <= d.hour <= 15:
            asia = [hm.get(day + k * HOUR) for k in range(6)]
            if any(r is None for r in asia):
                continue
            upper, lower = max(r[2] for r in asia), min(r[3] for r in asia)
            buy = b[3] < lower < b[4] < upper and b[4] > b[1]
            sell = lower < b[4] < upper < b[2] and b[4] < b[1]
            if buy != sell:
                add("S2.DAY", buy, structural_stop(f, hm, buy), "ASIA_NORMAL_SWEEP")
    return out


def deadline(row, calendar, horizon=None):
    at = row["entry_msc"]
    end, reason = calendar.deadline(at)
    horizon = horizon or row["horizon"]
    target = at // DAY * DAY + 20 * HOUR + HOUR // 2 if horizon == "DAY" else at + 24 * HOUR
    return (target, horizon) if target < end else (end, reason)


def markouts(raw, reader, calendar, cutoff):
    out = []
    for r in raw:
        entry = reader.endpoint(r["decision_msc"])
        row = dict(r, endpoints={})
        if entry is None:
            out.append(dict(row, status="ENTRY_UNKNOWN"))
            continue
        buy = r["side"] == "BUY"
        p0 = entry[2 if buy else 1]
        distance = (p0 - r["stop_units"] if buy else r["stop_units"] - p0) / 1000
        spread = (entry[2] - entry[1]) / 1000
        friction = spread + 2 * p0 / 1000 * .000007 + .4
        row.update(entry_msc=entry[0], entry_price_units=p0, natural_sl=distance,
                   entry_quote_index=entry[3], friction=friction,
                   friction_ratio=friction / distance if distance > 0 else None,
                   status="OK" if distance > 0 else "INVALID_STOP")
        if distance <= 0:
            out.append(row)
            continue
        for horizon in ("DAY", "24H"):
            end, why = deadline(row, calendar, horizon)
            finish = reader.endpoint(end) if end < cutoff else None
            if finish is None:
                row["endpoints"][horizon] = dict(status="ENDPOINT_UNKNOWN", deadline_msc=end)
                continue
            t = dict(row, exit_msc=finish[0], exit_price_units=finish[1 if buy else 2], reason=why)
            costs = {}
            for model in ("SYM_FLAT", "ASYM_ORDER"):
                money = GoldCosts(model).money(t, 100)
                costs[model] = dict(net_per_oz=money["net_usd"] / 100,
                    net_R=money["net_usd"] / (100 * distance),
                    gross_per_oz=money["gross_usd"] / 100, swap_per_oz=money["swap_usd"] / 100)
            row["endpoints"][horizon] = dict(status="OK", deadline_msc=end, exit_msc=finish[0],
                exit_price_units=t["exit_price_units"], costs=costs)
        out.append(row)
    return out


def summarize(rows):
    result = []
    for name in NAMES:
        for y in YEARS:
            raw = [r for r in rows if r["id"] == name and r["day"].startswith(str(y))]
            valid = [r for r in raw if r["status"] == "OK"]
            admitted = [r for r in valid if r["friction_ratio"] <= .15]
            primary = name.split(".")[-1]
            measurements = {}
            for horizon in ("DAY", "24H"):
                obs = [r for r in valid if r["endpoints"][horizon]["status"] == "OK"]
                measurements[horizon] = dict(observed=len(obs), **{
                    m: dict(mean_net_per_oz=float(np.mean([r["endpoints"][horizon]["costs"][m]["net_per_oz"] for r in obs])) if obs else None,
                            mean_gross_per_oz=float(np.mean([r["endpoints"][horizon]["costs"][m]["gross_per_oz"] for r in obs])) if obs else None,
                            net_R=sum(r["endpoints"][horizon]["costs"][m]["net_R"] for r in obs),
                            swap_per_oz=sum(r["endpoints"][horizon]["costs"][m]["swap_per_oz"] for r in obs))
                    for m in ("SYM_FLAT", "ASYM_ORDER")})
            result.append(dict(candidate=name, year=y, raw=len(raw), valid=len(valid),
                sides=dict(Counter(r["side"] for r in raw)), regimes=dict(Counter(r["regime"] for r in raw)),
                admitted=len(admitted), retention_pct=100 * len(admitted) / len(raw) if raw else 0,
                median_SL=median([r["natural_sl"] for r in valid]) if valid else None,
                median_friction=median([r["friction"] for r in valid]) if valid else None,
                scale_ratio=(median([r["friction"] for r in valid]) / median([r["natural_sl"] for r in valid])) if valid else None,
                primary=primary, markouts=measurements))
    return result


def gates(summaries):
    result = {}
    for name in NAMES:
        reasons = []
        for r in [s for s in summaries if s["candidate"] == name]:
            prefix = str(r["year"]) + ":"
            if r["admitted"] < (20 if name.startswith("S1") else 40):
                reasons.append(prefix + "CADENCE")
            if r["retention_pct"] < 50:
                reasons.append(prefix + "RETENTION")
            if r["scale_ratio"] is None or r["scale_ratio"] > .15:
                reasons.append(prefix + "NATURAL_SCALE")
            primary = r["markouts"][r["primary"]]
            if primary["observed"] != r["raw"]:
                reasons.append(prefix + "ENDPOINT")
            for model in ("SYM_FLAT", "ASYM_ORDER"):
                x = primary[model]
                if x["mean_net_per_oz"] is None or x["mean_net_per_oz"] <= 0:
                    reasons.append(prefix + model + ":NONPOSITIVE_RAW_MARKOUT")
                if x["mean_gross_per_oz"] is None or x["mean_gross_per_oz"] <= (r["median_friction"] or 0):
                    reasons.append(prefix + model + ":GROSS_BELOW_FRICTION")
        result[name] = dict(eligible=not reasons, reasons=reasons)
    return result


def run():
    JOB.mkdir(exist_ok=True)
    output = JOB / "development-stage0.json"
    if output.exists():
        raise ValueError("V9_existing_attempt_preserved")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    pins = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [PROTOCOL, Path(__file__), *Path(__file__).with_name("quant_core").glob("*.py")]}
    write_json(JOB / "research-registration.json", dict(commit=head, pins=pins,
        clean_OOS=False, dev_years=list(YEARS), frozen_before_outcomes=True))
    started = time.perf_counter()
    checksums = Checksums()
    store = MarketDataStore(CACHE, checksums)
    all_rows, source = [], []
    for start, end, warmup, manifest_path in (
        ("2019-01-01", "2021-01-01", "2018-11-01", ROOT / "prop-gold-v8-20261115/calendar-corrected/backward/OPEN_LOW_HIGH_CLOSE/manifest.json"),
        ("2022-01-01", "2024-01-01", "2021-11-01", ROOT / "prop-gold-v8-20261115/full/OPEN_LOW_HIGH_CLOSE/manifest.json"),
    ):
        first, cutoff, seed = stamp(start), stamp(end), stamp(warmup)
        bars = store.bars(seed, cutoff)
        patches = read(ROOT / "prop-atlas-v2-20261114/gold-source-corrections.json")["patches"]
        for p in patches:
            if seed <= p["at"] < cutoff:
                i = int(bars["t"].searchsorted(p["at"]))
                if i == len(bars) or bars["t"][i] != p["at"]:
                    raise ValueError("V9_source_patch_absent")
                for n, value in zip(("bo", "bh", "bl", "bc"), p["corrected"]):
                    bars[n][i] = value
        hours = aggregate(bars)
        calendar = gold_calendar(seed, cutoff)
        raw = generate(hours, first, cutoff, calendar)
        reader = QuoteStore(read(manifest_path), first, cutoff, checksums)
        marks = markouts(raw, reader, calendar, cutoff)
        all_rows.extend(marks)
        source.append(dict(start=start, end=end, seed=warmup, bars=len(bars), signals=len(raw),
                           quotes_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                           raw_declared_sha256=store.raw_declared_sha256,
                           binary_columns_verified=True, price_units=".001", prior_exposed=True))
        print(json.dumps(dict(stage="V9_Stage0_cluster", start=start, signals=len(raw))), flush=True)
    summaries = summarize(all_rows)
    decision = gates(summaries)
    write_json(output, dict(summaries=summaries, gates=decision, raw=all_rows, source=source,
                            seconds=time.perf_counter() - started,
                            bytes_hashed=checksums.bytes_hashed, pins=pins))
    write_json(JOB / "research-decision.json", dict(gates=decision,
        eligible=[k for k, v in decision.items() if v["eligible"]],
        validation_status="LOCKED_UNTIL_COMMITTED_ELIGIBLE_COMPOSITION",
        no2024_2026_prices_read=True, stage="STAGE0", source_conditional=True))
    print(json.dumps(dict(stage="V9_Stage0_complete", gates=decision)), flush=True)


if __name__ == "__main__":
    run()
