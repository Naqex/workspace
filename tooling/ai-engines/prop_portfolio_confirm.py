"""Confirm the M1-selected sleeve on existing paired ticks before validation."""
from datetime import datetime, timezone
import numpy as np

from prop_campaign_source import Prices
from prop_portfolio_accounts import (
    quantity_steps, entry_exit_fee, funding_step, trade_money, VALUE, SLIP,
)
from prop_portfolio_common import (
    JOB, MODELS, START, END, read, write_json, digest, event,
)
from prop_portfolio_scan import POINTS, native_bars, metrics, corr, gap_unknown
from prop_portfolio_sources import MINUTE
from xau_h1_stage0_scan import funding_events


def curves(trades, reader, model, risk):
    differences = [np.zeros(POINTS) for _ in range(3)]
    source_gaps = []
    net = []
    for trade in trades:
        ticks, _ = reader.path(trade["entry_msc"], trade["exit_msc"])
        gaps = gap_unknown(ticks["t"], 0, asset=trade["asset"])
        if gaps:
            source_gaps.append(dict(day=trade["day"], gaps=gaps))
        bars = native_bars(reader, trade["entry_msc"], trade["exit_msc"])
        if bars is None:
            raise ValueError("selected_native_path_unknown")
        q = quantity_steps(trade, risk)
        buy = trade["side"] == "BUY"
        price_views = [bars["bc"] if buy else bars["ac"],
                       bars["bl"] if buy else bars["ah"],
                       bars["bh"] if buy else bars["al"]]
        at = np.minimum(bars["t"] + MINUTE - 1, trade["exit_msc"])
        carry = np.zeros(len(at))
        for f in funding_events(trade["entry_msc"], trade["exit_msc"]):
            carry[at >= f["at"]] += q * funding_step(trade, model) * f["multiplier"]
        money = trade_money(trade, q, model, risk)
        final = money["net_usd"] / 150
        net.append(final)
        for difference, prices in zip(differences, price_views):
            values = (
                (1 if buy else -1) * q * VALUE[trade["asset"]] *
                (prices.astype("float64") - trade["entry_price_units"])
                - entry_exit_fee(trade, trade["entry_price_units"], q)
                - q * SLIP[trade["asset"]] + carry
            ) / 150000
            indices = np.minimum((at - START) // MINUTE, POINTS - 1)
            np.add.at(difference,
                      np.r_[indices, min(POINTS - 1, (trade["exit_msc"] - START) // MINUTE + 1)],
                      np.diff(np.r_[0., values, final]))
    result = [np.cumsum(d) for d in differences]
    if abs(result[0][-1] - sum(net)) > 1e-8:
        raise ValueError("native_curve_cost_bridge")
    return result, source_gaps


def confirm():
    preliminary = read(JOB / "satellite-decision.json")
    if preliminary["selected"] != ["EURUSD.SWEEP.ASIA.LONDON.DAY"]:
        raise ValueError("unexpected_preliminary_selection")
    name = preliminary["selected"][0]
    trades = read(JOB / "eur-satellite-dev-trades.json")
    funnel = read(JOB / "eur-satellite-dev-funnel.json")
    reader = Prices(read(JOB / "eur-native-dev-v1/manifest.json"))
    comparison = {}
    reasons = []
    for model in MODELS:
        full, gaps = curves(trades, reader, model, 150)
        small, _ = curves(trades, reader, model, 75)
        out = metrics(full)
        a, b = out["net_R"]["2022"], out["net_R"]["2023"]
        if a + b < 8 or not ((a >= 0 and b >= 0) or
                            (min(a, b) >= -1 and max(a, b) >= 10)):
            reasons.append(model + ":NATIVE_NET_GATE")
        with np.load(JOB / f"core-curve-{model}.npz") as stored:
            core = [stored[k] for k in ("close", "low", "high")]
        core_stat = metrics(core)
        joined = metrics([a + b for a, b in zip(core, small)])
        correlation = corr(out["daily"], core_stat["daily"])
        if correlation is None or correlation >= .25:
            reasons.append(model + ":NATIVE_CORRELATION")
        if (joined["total_net_R"] / joined["max_R_DD"] <=
                core_stat["total_net_R"] / core_stat["max_R_DD"]):
            reasons.append(model + ":NATIVE_MARGINAL_RATIO")
        if gaps:
            reasons.append(model + ":NATIVE_HELD_PATH_GAPS")
        comparison[model] = dict(
            sleeve=out, core=core_stat, portfolio_half_budget=joined,
            correlation=correlation, source_gaps=gaps,
        )
        np.savez_compressed(JOB / f"native-curve-{name}-{model}.npz",
                            close=full[0], low=full[1], high=full[2],
                            small_close=small[0], small_low=small[1], small_high=small[2])
    if any(s["reason"].endswith("UNKNOWN") for s in funnel["skipped"]):
        reasons.append("NATIVE_ENTRY_ENDPOINT_UNKNOWN")
    result = dict(
        selected=[] if reasons else [name], reasons=reasons,
        comparison=comparison, source="paired original QDM ticks",
        filled=len(trades), raw=funnel["raw"], skipped=funnel["skipped"],
        entry_sl_horizon_parameters_unchanged=True,
        manifest_sha256=digest(JOB / "eur-native-dev-v1/manifest.json"),
        cutoff=END, prices2024_2026_read=False,
        utc=datetime.now(timezone.utc).isoformat(),
    )
    write_json(JOB / "final-satellite-decision.json", result)
    event("native_satellite_confirmation", selected=result["selected"], reasons=reasons)


if __name__ == "__main__":
    confirm()
