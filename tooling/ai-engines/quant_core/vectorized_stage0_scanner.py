"""Array-based raw endpoint screen; conditional quotes, never a stop/account replay."""
from dataclasses import dataclass
from math import erfc, sqrt
from statistics import NormalDist
import numpy as np

HOUR, DAY = 3_600_000, 86_400_000
HORIZONS = ("DAY", "24H", "48H", "FRIDAY")


@dataclass(frozen=True)
class AssetCosts:
    asset: str
    scale: int
    contract: int
    extra_roundtrip: float
    swap_long: float
    swap_short: float
    notional_side: float = 0


def costs(asset, model):
    if model not in ("SYM", "ASYM"):
        raise ValueError("unknown_cost_view")
    if asset == "XAUUSD":
        return AssetCosts(asset, 1000, 100, .4, -.4 if model == "SYM" else -.45,
                          -.4 if model == "SYM" else -.05, .000007)
    if asset == "EURUSD":
        return AssetCosts(asset, 100000, 100000, .00009, -.0004, -.0004)
    raise ValueError("asset_cost_not_admitted")


def funding_multipliers(entry, exit_at):
    entry, exit_at = np.asarray(entry, dtype="int64"), np.asarray(exit_at, dtype="int64")
    if np.any(exit_at < entry):
        raise ValueError("negative_holding_period")
    if not len(entry):
        return np.zeros(0, dtype="int64")
    days = np.arange(entry.min() // DAY, exit_at.max() // DAY + 1)
    weekday = (days + 3) % 7
    events = days * DAY + 22 * HOUR
    weights = np.where(weekday < 5, np.where(weekday == 2, 3, 1), 0)
    cumulative = np.r_[0, np.cumsum(weights)]
    return cumulative[np.searchsorted(events, exit_at, side="right")] - cumulative[
        np.searchsorted(events, entry, side="right")]


def deadlines(entries, horizon, calendar):
    entries = np.asarray(entries, dtype="int64")
    flats = np.asarray(calendar.times, dtype="int64")
    index = np.searchsorted(flats, entries, side="right")
    if np.any(index == len(flats)):
        raise ValueError("future_calendar_break_missing")
    flat = flats[index]
    if horizon == "FRIDAY":
        return flat
    if horizon == "DAY":
        target = entries // DAY * DAY + 20 * HOUR + HOUR // 2
    elif horizon in ("24H", "48H"):
        target = entries + (24 if horizon == "24H" else 48) * HOUR
    else:
        raise ValueError("unknown_horizon")
    return np.minimum(target, flat)


def endpoint_indices(bars, targets, cutoff):
    times = bars["t"]
    indices = times.searchsorted(targets)
    safe = np.minimum(indices, len(times) - 1)
    ok = (targets < cutoff) & (indices < len(times)) & (times[safe] >= targets) & (times[safe] - targets <= 60000)
    return safe, ok


def economics(asset, side, entry_price_units, exit_price_units, entry, exit_at, model):
    spec = costs(asset, model)
    p0, px = np.asarray(entry_price_units) / spec.scale, np.asarray(exit_price_units) / spec.scale
    sign = np.where(side == 1, 1, -1)
    gross = sign * (px - p0)
    # Gold reference is 1 lot/100oz, with each commission leg rounded to cents.
    if asset == "XAUUSD":
        fees = sum(np.floor(p * spec.contract * spec.notional_side * 100 + .5 + 1e-9) / 100
                   for p in (p0, px)) / spec.contract
    else:
        fees = np.zeros(len(p0))
    mult = funding_multipliers(entry, exit_at)
    swap = np.where(side == 1, spec.swap_long, spec.swap_short) * mult
    friction = fees + spec.extra_roundtrip
    return dict(gross=gross, commission=fees, other=spec.extra_roundtrip,
                funding=swap, funding_multipliers=mult, net=gross - friction + swap)


def measure(asset, recipe, bars, calendar, first, cutoff):
    """One recipe's signal arrays × four horizons; no outcome selection."""
    decision = np.asarray(recipe["at"], dtype="int64")
    side, stops = np.asarray(recipe["side"]), np.asarray(recipe["stop"], dtype="int64")
    entries, entry_ok = endpoint_indices(bars, decision, cutoff)
    at = bars["t"][entries]
    p0 = np.where(side == 1, bars["ao"][entries], bars["bo"][entries])
    spec = costs(asset, "SYM")
    natural = np.where(side == 1, p0 - stops, stops - p0) / spec.scale
    spread = (bars["ao"][entries] - bars["bo"][entries]) / spec.scale
    friction = spread + spec.extra_roundtrip + 2 * p0 / spec.scale * spec.notional_side
    valid = entry_ok & (natural > 0) & (decision >= first) & (decision < cutoff)
    weekday = (at // DAY + 3) % 7
    # A Friday signal after hard-flat cannot be carried into the following week.
    valid &= (weekday < 5) & ~((weekday == 4) & (at % DAY >= 20 * HOUR + HOUR // 2))
    ratio = np.divide(friction, natural, out=np.full(len(natural), np.inf), where=natural > 0)
    years = (decision.astype("datetime64[ms]").astype("datetime64[Y]").astype(int) + 1970)
    result = []
    for horizon in HORIZONS:
        target = deadlines(at, horizon, calendar)
        exits, exit_ok = endpoint_indices(bars, target, cutoff)
        px = np.where(side == 1, bars["bo"][exits], bars["ao"][exits])
        end = bars["t"][exits]
        # DAY has no executable same-day endpoint for decisions after its close.
        ok = valid & exit_ok & (target >= at) & (end >= at)
        row = dict(asset=asset, recipe=recipe["id"], family=recipe["family"], horizon=horizon,
                   at=decision, entry_at=at, exit_at=end, deadline=target, side=side,
                   entry_price=p0, exit_price=px, stop=stops, natural=natural,
                   friction=friction, ratio=ratio, ok=ok, admitted=ok & (ratio <= .15),
                   years=years, model={})
        for model in ("SYM", "ASYM"):
            money = economics(asset, side, p0, px, at, np.maximum(end, at), model)
            money["net_R"] = np.divide(money["net"], natural, out=np.zeros(len(at)), where=natural > 0)
            row["model"][model] = money
        result.append(row)
    return result


def holm(pvalues, trials=None):
    p = np.asarray(pvalues, dtype=float)
    if np.any(~np.isfinite(p)) or np.any((p < 0) | (p > 1)):
        raise ValueError("invalid_pvalues")
    trials = len(p) if trials is None else trials
    if trials < len(p):
        raise ValueError("trial_count_below_observed")
    order = np.argsort(p)
    adjusted = np.minimum(1, np.maximum.accumulate(p[order] * (trials - np.arange(len(p)))))
    out = np.empty(len(p))
    out[order] = adjusted
    return out


def daily_statistics(values, trials):
    """Newey-West mean test + explicitly approximate deflated-Sharpe diagnostic."""
    x = np.asarray(values, dtype=float)
    if x.ndim != 2 or x.shape[1] < 10 or trials < x.shape[0]:
        raise ValueError("statistical_matrix_shape_or_trials")
    n = x.shape[1]
    mu = x.mean(axis=1)
    centered = x - mu[:, None]
    v0 = np.mean(centered ** 2, axis=1)
    long_var = v0.copy()
    for lag in range(1, 6):
        long_var += 2 * (1 - lag / 6) * np.sum(centered[:, lag:] * centered[:, :-lag], axis=1) / n
    long_var = np.maximum(long_var, v0 * 1e-6)
    se = np.sqrt(long_var / n)
    t = np.divide(mu, se, out=np.zeros_like(mu), where=se > 0)
    p = np.array([.5 * erfc(v / sqrt(2)) for v in t])
    std = np.sqrt(v0)
    sr = np.divide(mu, std, out=np.zeros_like(mu), where=std > 0)
    skew = np.divide(np.mean(centered ** 3, axis=1), std ** 3,
                     out=np.zeros_like(mu), where=std > 0)
    kurt = np.divide(np.mean(centered ** 4, axis=1), v0 ** 2,
                     out=np.full_like(mu, 3), where=v0 > 0)
    effective = np.clip(np.divide(n * v0, long_var, out=np.ones_like(mu), where=long_var > 0), 2, n)
    norm = NormalDist()
    euler = .5772156649015329
    max_sr = ((1 - euler) * norm.inv_cdf(1 - 1 / trials) +
              euler * norm.inv_cdf(1 - 1 / (trials * np.e))) / np.sqrt(effective - 1) if trials > 1 else np.zeros_like(mu)
    denom = np.sqrt(np.maximum(1e-12, 1 - skew * sr + (kurt - 1) * sr * sr / 4))
    z = (sr - max_sr) * np.sqrt(effective - 1) / denom
    dsr = np.array([.5 * erfc(-v / sqrt(2)) for v in z])
    return dict(t_stat=t, p_one_sided=p, p_holm=holm(p, trials), sharpe_daily=sr,
                DSR_proxy=dsr, effective_days=effective, n_days=n,
                HAC_lag=5, trials=trials, exact_DSR=False)


def summaries(measurements, first, end, trials):
    weekdays = np.arange(first // DAY, end // DAY)
    weekdays = weekdays[(weekdays + 3) % 7 < 5]
    daily = np.zeros((len(measurements), len(weekdays)))
    output = []
    for j, m in enumerate(measurements):
        annual = []
        for year in range(2018, 2024):
            raw = m["years"] == year
            ok, admitted = raw & m["ok"], raw & m["admitted"]
            row = dict(year=year, raw=int(raw.sum()), priced=int(ok.sum()), admitted=int(admitted.sum()),
                       cost12=int((ok & (m["ratio"] <= .12)).sum()),
                       retention=float(admitted.sum() / raw.sum()) if raw.sum() else 0,
                       median_SL=float(np.median(m["natural"][ok])) if ok.any() else None,
                       scale_ratio=float(np.median(m["friction"][ok]) / np.median(m["natural"][ok])) if ok.any() else None,
                       economics={})
            for model in ("SYM", "ASYM"):
                x = m["model"][model]
                row["economics"][model] = dict(raw_net_R=float(x["net_R"][ok].sum()),
                    admitted_net_R=float(x["net_R"][admitted].sum()),
                    mean_net_price_units=float(x["net"][ok].mean()) if ok.any() else None,
                    gross_price_units=float(x["gross"][ok].mean()) if ok.any() else None,
                    swap_price_units=float(x["funding"][ok].sum()),
                    per_lot_net=float(x["net"][ok].mean() * costs(m["asset"], model).contract) if ok.any() else None)
            annual.append(row)
        indices = weekdays.searchsorted(m["at"][m["ok"]] // DAY)
        np.add.at(daily[j], indices, m["model"]["SYM"]["net_R"][m["ok"]])
        output.append(dict(asset=m["asset"], recipe=m["recipe"], family=m["family"], horizon=m["horizon"],
                           annual=annual))
    statistics = daily_statistics(daily, trials)
    for j, row in enumerate(output):
        measurement = measurements[j]
        row["statistics"] = {k: (float(v[j]) if isinstance(v, np.ndarray) else v) for k, v in statistics.items()}
        reasons, clusters = [], []
        for years in ((2018, 2019, 2020), (2021, 2022, 2023)):
            a = [r for r in row["annual"] if r["year"] in years]
            raw, admitted = sum(r["raw"] for r in a), sum(r["admitted"] for r in a)
            c = dict(years=list(years), raw=raw, admitted=admitted,
                     retention=admitted / raw if raw else 0, net={})
            cohort = np.isin(measurement["years"], years) & measurement["ok"]
            c["scale_ratio"] = (float(np.median(measurement["friction"][cohort]) /
                                      np.median(measurement["natural"][cohort]))
                                if cohort.any() else None)
            if raw == 0 or c["retention"] < .6:
                reasons.append(f"{years[0]}:RETENTION")
            if admitted < 60:
                reasons.append(f"{years[0]}:CADENCE")
            if sum(r["priced"] for r in a) != raw:
                reasons.append(f"{years[0]}:ENDPOINT")
            if c["scale_ratio"] is None or c["scale_ratio"] > .15:
                reasons.append(f"{years[0]}:SCALE")
            for model in ("SYM", "ASYM"):
                totals = dict(raw=sum(r["economics"][model]["raw_net_R"] for r in a),
                              admitted=sum(r["economics"][model]["admitted_net_R"] for r in a))
                c["net"][model] = totals
                if min(totals.values()) <= 0:
                    reasons.append(f"{years[0]}:{model}:CLUSTER_ECONOMIC")
            clusters.append(c)
        for model in ("SYM", "ASYM"):
            positives = sum(r["economics"][model]["raw_net_R"] > 0 for r in row["annual"])
            if positives < 4:
                reasons.append(model + ":FEWER_THAN_4_POSITIVE_YEARS")
        row["economic_gate"] = not reasons
        if row["statistics"]["p_holm"] > .05:
            reasons.append("HOLM_MULTIPLE_TESTING")
        if row["statistics"]["DSR_proxy"] < .95:
            reasons.append("DEFLATED_SHARPE_PROXY")
        row.update(clusters=clusters, eligible=not reasons, reasons=reasons,
                   score=min(c["net"]["SYM"]["raw"] / 3 for c in clusters))
    return output, daily
