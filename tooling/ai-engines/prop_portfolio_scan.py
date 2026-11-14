"""Natural-SL realization of the frozen atlas; unknown paths stay visible."""
from collections import Counter
from datetime import datetime, timedelta, timezone
from statistics import median
from zoneinfo import ZoneInfo
import numpy as np

from prop_atlas_source import load_extra_fx
from prop_campaign_source import Prices
from prop_campaign_exits import funding_rate
from prop_portfolio_common import (
    JOB, ATLAS, MODELS, START, END, HOUR, DAY,
    read, write_json, digest, event,
)
from prop_portfolio_sources import BAR, MINUTE, NY, deadline, load_m1
from xau_h1_stage0_scan import funding_events

PRAGUE = ZoneInfo("Europe/Prague")
POINTS = (END - START) // MINUTE + 1


def gap_unknown(times, width):
    gaps = []
    for i in np.flatnonzero(np.diff(times) > max(15 * MINUTE, width)):
        start, end = int(times[i] + width), int(times[i + 1])
        local_start = datetime.fromtimestamp(start / 1000, timezone.utc).astimezone(NY)
        local_end = datetime.fromtimestamp(end / 1000, timezone.utc).astimezone(NY)
        clock = local_start.hour * 60 + local_start.minute
        normal = (
            end - start <= 2 * HOUR and
            local_start.date() == local_end.date() and
            16 * 60 + 15 <= clock <= 18 * 60
        )
        if not normal:
            gaps.append((start, end))
    return gaps


def quote(rows, at, width=MINUTE):
    i = int(rows["t"].searchsorted(at))
    if i == len(rows) or rows["t"][i] - at > 60000:
        return None
    return [int(rows["t"][i]), int(rows["bo"][i]), int(rows["ao"][i]), i]


def net_values(asset, side, entry_price, prices, at, entry_at, model):
    sign = 1 if side == "BUY" else -1
    scale = 1000 if asset in ("XAUUSD", "US500") else 100000
    p0 = entry_price / scale
    px = prices.astype("float64") / scale
    gross = sign * (px - p0)
    if asset == "XAUUSD":
        fees = (p0 + px) * 0.000007
        slip = 0.4
        rate = funding_rate(side, model)
    elif asset == "US500":
        fees = 1
        slip = 1.5
        carry = -2 * (at // DAY - entry_at // DAY)
        return gross - fees - slip + carry
    else:
        fees = 0.00005
        slip = 0.00004
        rate = -0.0004
    carry = np.zeros(len(at))
    for funding in funding_events(entry_at, int(at[-1])):
        carry[at >= funding["at"]] += rate * funding["multiplier"]
    return gross - fees - slip + carry


def raw_geometry(row, entry):
    asset = row["asset"]
    scale = 1000 if asset in ("XAUUSD", "US500") else 100000
    buy = row["side"] == "BUY"
    p0 = entry[2] if buy else entry[1]
    distance = (p0 - row["stop_units"] if buy else row["stop_units"] - p0) / scale
    friction = (entry[2] - entry[1]) / scale
    friction += (
        2 * p0 / scale * 0.000007 + 0.4 if asset == "XAUUSD"
        else 2.5 if asset == "US500" else 0.00009
    )
    valid = distance > 0 and (
        entry[1] > row["stop_units"] if buy else entry[2] < row["stop_units"]
    )
    return p0, distance, friction, valid and friction / distance <= 0.15


def native_bars(native, entry, end):
    chunks = []
    for hour in range(entry // HOUR * HOUR, end // HOUR * HOUR + HOUR, HOUR):
        if hour not in native.files:
            return None
        ticks = native.hour(hour)
        ticks = ticks[(ticks["t"] >= entry) & (ticks["t"] <= end)]
        if not len(ticks):
            continue
        starts = np.r_[0, np.flatnonzero(np.diff(ticks["t"] // MINUTE)) + 1]
        ends = np.r_[starts[1:] - 1, len(ticks) - 1]
        bars = np.empty(len(starts), dtype=BAR)
        bars["t"] = ticks["t"][starts] // MINUTE * MINUTE
        for side in ("b", "a"):
            values = ticks[side]
            bars[side + "o"] = values[starts]
            bars[side + "h"] = np.maximum.reduceat(values, starts)
            bars[side + "l"] = np.minimum.reduceat(values, starts)
            bars[side + "c"] = values[ends]
        chunks.append(bars)
    return np.concatenate(chunks) if chunks else None


def realize(row, rows, native=None, width=MINUTE):
    asset = row["asset"]
    entry = row.get("entry_quote") or quote(rows, row["decision_msc"], width)
    if entry is None:
        return dict(status="ENTRY_UNKNOWN", raw=row), None
    p0, distance, friction, passes = raw_geometry(row, entry)
    geometry = dict(natural_sl=distance, friction=friction, pass15=passes)
    if not passes:
        return dict(status="FRICTION_REJECT", raw=row, **geometry), None
    end, why = deadline(row, entry[0])
    if end >= END:
        return dict(status="ENDPOINT_SCOPE_UNKNOWN", raw=row, **geometry), None
    finish = quote(rows, end, width)
    if finish is None and asset in ("GBPUSD", "AUDUSD"):
        if row.get("exit_quote") and row.get("deadline_msc") == end:
            finish = row["exit_quote"]
    if finish is None:
        return dict(status="ENDPOINT_UNKNOWN", raw=row, **geometry), None
    exact_path = width == MINUTE
    lo = int(rows["t"].searchsorted(entry[0] // width * width))
    hi = int(rows["t"].searchsorted(end))
    path = rows[lo:hi].copy()
    if not len(path):
        return dict(status="EMPTY_PATH", raw=row, **geometry), None
    if asset == "XAUUSD":
        observed = native_bars(native, entry[0], finish[0]) if row["side"] == "SELL" else None
        if observed is not None:
            path = observed[observed["t"] < end]
        elif row["side"] == "SELL":
            # A labeled conservative screen, never an admitted SELL ask path.
            spread = max(entry[2] - entry[1], 1)
            for name in ("o", "h", "l", "c"):
                path["a" + name] = path["b" + name] + spread
            exact_path = False
        else:
            # Replace entry's partial minute with observed post-entry ticks.
            ticks = native.hour(entry[0] // HOUR * HOUR)
            ticks = ticks[(ticks["t"] >= entry[0]) &
                          (ticks["t"] < (entry[0] // MINUTE + 1) * MINUTE)]
            if not len(ticks):
                return dict(status="ENTRY_MINUTE_UNKNOWN", raw=row, **geometry), None
            for field, value in zip(("bo", "bh", "bl", "bc"),
                                    (ticks["b"][0], ticks["b"].max(),
                                     ticks["b"].min(), ticks["b"][-1])):
                path[field][0] = value
    buy = row["side"] == "BUY"
    adverse = path["bl"] if buy else path["ah"]
    crossed = np.flatnonzero(adverse <= row["stop_units"] if buy
                            else adverse >= row["stop_units"])
    reason = why
    exit_at = finish[0]
    exit_px = finish[1] if buy else finish[2]
    if len(crossed):
        i = int(crossed[0])
        path = path[:i + 1]
        op = int(path["bo"][-1] if buy else path["ao"][-1])
        exit_px = min(op, row["stop_units"]) if buy else max(op, row["stop_units"])
        exit_at = min(end - 1, int(path["t"][-1]) + width - 1)
        reason = "SL_M1" if width == MINUTE else "SL_H1_CONDITIONAL"
    elif exit_px <= row["stop_units"] if buy else exit_px >= row["stop_units"]:
        reason = "SL_GAP_ENDPOINT"
    unknown_gaps = gap_unknown(np.r_[path["t"], exit_at], width)
    if unknown_gaps:
        exact_path = False
    if width != MINUTE and end % HOUR:
        exact_path = False
    scale = 1000 if asset in ("XAUUSD", "US500") else 100000
    unit = 1 if asset in ("XAUUSD", "US500") else 1000
    q = int(150 / (distance * unit))
    if q < 1:
        return dict(status="LOT_MIN", raw=row, **geometry), None
    record = dict(
        cell=row["id"], asset=asset, side=row["side"], day=row["day"],
        entry_msc=entry[0], entry_price_units=p0, stop_units=row["stop_units"],
        deadline_msc=end, exit_msc=exit_at, exit_price_units=exit_px, reason=reason,
        unit=unit, quantity=q, natural_sl=distance, friction=friction,
        pass15=passes, source_path_complete=exact_path,
        unknown_gaps=unknown_gaps, width=width, scale=scale,
    )
    return dict(status="FILLED", **record), path


def add_curve(deltas, record, path, model, risk=150):
    asset = record["asset"]
    buy = record["side"] == "BUY"
    q = int(risk / (record["natural_sl"] * record["unit"])) * record["unit"]
    if q == 0:
        return 0
    stamps = np.minimum(path["t"] + record["width"] - 1, record["exit_msc"])
    prices = [
        path["bc"] if buy else path["ac"],
        path["bl"] if buy else path["ah"],
        path["bh"] if buy else path["al"],
    ]
    final = float(net_values(
        asset, record["side"], record["entry_price_units"],
        np.array([record["exit_price_units"]]), np.array([record["exit_msc"]]),
        record["entry_msc"], model,
    )[0] * q / 150)
    for target, values in zip(deltas, prices):
        values = values.copy()
        if record["reason"].startswith("SL"):
            if target is deltas[0] or target is deltas[1]:
                values[-1] = record["exit_price_units"]
        liquidation = net_values(
            asset, record["side"], record["entry_price_units"], values,
            stamps, record["entry_msc"], model,
        ) * q / 150
        indices = np.minimum((stamps - START) // MINUTE, POINTS - 1)
        changes = np.diff(np.r_[0., liquidation, final])
        indices = np.r_[indices, min(
            POINTS - 1, (record["exit_msc"] - START) // MINUTE + 1)]
        np.add.at(target, indices, changes)
    return final


def daily_series(curve):
    result = {}
    day = datetime(2022, 1, 1, tzinfo=PRAGUE)
    prior = 0.
    while day < datetime(2024, 1, 2, tzinfo=PRAGUE):
        at = int(day.timestamp() * 1000)
        ix = (at - START) // MINUTE - 1
        if 0 <= ix < len(curve):
            value = float(curve[ix])
            label = (day.date() - timedelta(days=1))
            if label.weekday() < 5 and label.year in (2022, 2023):
                result[label.isoformat()] = value - prior
            prior = value
        day += timedelta(days=1)
    return result


def metrics(curves):
    close, low, high = curves
    yearly = {}
    previous = 0.
    for year, start, end in ((2022, START, START + 365 * DAY), (2023, START + 365 * DAY, END)):
        lo, hi = (start - START) // MINUTE, (end - START) // MINUTE
        terminal = float(close[min(hi, len(close) - 1)])
        yearly[str(year)] = terminal - previous
        previous = terminal
    dd = float(np.max(np.maximum.accumulate(high) - low))
    return dict(net_R=yearly, total_net_R=float(close[-1]), max_R_DD=dd,
                close_only_DD=float(np.max(np.maximum.accumulate(close) - close)),
                daily=daily_series(close))


def corr(one, two, year=None):
    keys = sorted(set(one) | set(two))
    if year is not None:
        keys = [k for k in keys if k.startswith(str(year))]
    a = [one.get(k, 0.) for k in keys]
    b = [two.get(k, 0.) for k in keys]
    if not keys or np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def core_daily(account):
    points = account["daily_equity_marks"] + [[END, account["balance_usd"] * 1000]]
    out = {}
    old = 50000000
    for at, equity in points:
        label = datetime.fromtimestamp(at / 1000, timezone.utc).astimezone(PRAGUE).date() - timedelta(days=1)
        if label.weekday() < 5 and label.year in (2022, 2023):
            out[label.isoformat()] = (equity - old) / 150000
        old = equity
    return out


def run():
    atlas = read(ATLAS / "atlas-stage0.json")
    data = {asset: load_m1(asset) for asset in ("XAUUSD", "EURUSD", "US500")}
    for asset in ("GBPUSD", "AUDUSD"):
        _, reader, _ = load_extra_fx(asset)
        rows = np.empty(len(reader.rows), dtype=BAR)
        for i, (at, pair) in enumerate(sorted(reader.rows.items())):
            rows[i] = (at, *pair[0], *pair[1])
        data[asset] = rows
    native = Prices(read(ATLAS / "gold-atlas-manifest.json"))
    regime = read(JOB / "regime-comparison.json")
    benchmarks = {m: core_daily(regime[m][2]) for m in MODELS}
    summaries = []
    for cell in atlas["cells"]:
        recipe = cell["cell"]
        asset = recipe["asset"]
        raw = read(ATLAS / f"stage0-{recipe['id']}.json")["rows"]
        counts = Counter()
        records = []
        deltas = {m: [np.zeros(POINTS) for _ in range(3)] for m in MODELS}
        small = {m: [np.zeros(POINTS) for _ in range(3)] for m in MODELS}
        complete = True
        for row in raw:
            record, path = realize(row, data[asset], native,
                                   HOUR if asset in ("GBPUSD", "AUDUSD") else MINUTE)
            counts[record["status"]] += 1
            record["raw_day"] = row["day"]
            records.append(record)
            if record["status"] != "FILLED":
                if record["status"] != "FRICTION_REJECT":
                    complete = False
                continue
            complete = complete and record["source_path_complete"]
            record["net_R"] = {}
            for model in MODELS:
                record["net_R"][model] = add_curve(deltas[model], record, path, model)
                add_curve(small[model], record, path, model, risk=75)
        measured = {}
        for model in MODELS:
            curves = [np.cumsum(x) for x in deltas[model]]
            out = metrics(curves)
            out["correlation"] = dict(
                pooled=corr(out["daily"], benchmarks[model]),
                per_year={str(y): corr(out["daily"], benchmarks[model], y) for y in (2022, 2023)},
            )
            measured[model] = out
            curve_path = JOB / f"curve-{recipe['id']}-{model}.npz"
            np.savez_compressed(curve_path, close=curves[0], low=curves[1], high=curves[2],
                                small_close=np.cumsum(small[model][0]),
                                small_low=np.cumsum(small[model][1]),
                                small_high=np.cumsum(small[model][2]))
        funnel = {}
        for year in (2022, 2023):
            rs = [r for r in records if r["raw_day"].startswith(str(year))]
            known = [r for r in rs if "natural_sl" in r]
            passing = sum(r.get("pass15", False) for r in rs)
            funnel[str(year)] = dict(
                raw=len(rs), filled=sum(r["status"] == "FILLED" for r in rs),
                friction_pass_rate=passing / len(rs) if rs else 0,
                natural_sl_median=median(r["natural_sl"] for r in known) if known else None,
                scale_ratio=(median(r["friction"] for r in known) /
                             median(r["natural_sl"] for r in known)) if known else None,
            )
        summary = dict(
            cell=recipe, funnel=funnel, status_counts=dict(counts),
            source_path_complete=complete, models=measured,
            prices2024_2026_read=False,
        )
        write_json(JOB / f"natural-{recipe['id']}.json", dict(summary=summary, records=records))
        summaries.append(summary)
        event("natural_SL_cell", cell=recipe["id"], complete=complete,
              net_R={m: round(v["total_net_R"], 4) for m, v in measured.items()})
    write_json(JOB / "natural-atlas.json", dict(cells=summaries, trials=len(summaries),
                                               prices2024_2026_read=False))


if __name__ == "__main__":
    run()
