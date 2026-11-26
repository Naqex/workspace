"""Registered satellite gates and fixed half-budget marginal contribution."""
from collections import Counter
import numpy as np

from prop_campaign_exits import costs
from prop_campaign_source import Prices
from xau_h1_execution import commission
from xau_h1_stage0_scan import funding_events
from prop_campaign_exits import funding_rate
from prop_portfolio_common import (
    JOB, ATLAS, V1, MODELS, START, END, read, write_json, digest, event,
)
from prop_portfolio_sources import MINUTE
from prop_portfolio_scan import POINTS, native_bars, metrics


def core_curves(model):
    native = Prices(read(V1 / "gold-dev-manifest-v2.json"))
    deltas = [np.zeros(POINTS) for _ in range(3)]
    trades = read(V1 / f"paths-{model}-A0.json")
    for t in trades:
        bars = native_bars(native, t["entry_msc"], t["exit_msc"])
        if bars is None:
            raise ValueError("core_source_path_unknown")
        q = int(150000 // abs(t["entry_price_units"] - t["stop_units"]))
        buy = t["side"] == "BUY"
        prices = [bars["bc"] if buy else bars["ac"],
                  bars["bl"] if buy else bars["ah"],
                  bars["bh"] if buy else bars["al"]]
        at = np.minimum(bars["t"] + MINUTE - 1, t["exit_msc"])
        carry = np.zeros(len(at))
        for f in funding_events(t["entry_msc"], t["exit_msc"]):
            carry[at >= f["at"]] += q * funding_rate(t["side"], model) * f["multiplier"]
        final = costs(t, model)["net_usd"] / 150
        for target, price in zip(deltas, prices):
            values = (
                (1 if buy else -1) * q *
                (price.astype("float64") - t["entry_price_units"]) / 1000
                - commission(t["entry_price_units"], q) - .20 * q + carry
            ) / 150
            ix = np.minimum((at - START) // MINUTE, POINTS - 1)
            np.add.at(target, np.r_[ix, min(POINTS - 1, (t["exit_msc"] - START) // MINUTE + 1)],
                      np.diff(np.r_[0., values, final]))
    curves = [np.cumsum(x) for x in deltas]
    path = JOB / f"core-curve-{model}.npz"
    np.savez_compressed(path, close=curves[0], low=curves[1], high=curves[2])
    return curves


def satellite_reasons(cell):
    reasons = []
    if not cell["source_path_complete"]:
        reasons.append("SOURCE_PATH_INCOMPLETE_OR_CONDITIONAL")
    for year, f in cell["funnel"].items():
        if f["friction_pass_rate"] < .6:
            reasons.append(year + ":FRICTION_RETENTION_LT60")
        if f["scale_ratio"] is None or f["scale_ratio"] > .15:
            reasons.append(year + ":MEDIAN_FRICTION_SL_GT15")
    for model, out in cell["models"].items():
        a, b = out["net_R"]["2022"], out["net_R"]["2023"]
        if a + b < 8:
            reasons.append(model + ":TOTAL_NET_R_LT8")
        if not ((a >= 0 and b >= 0) or
                (min(a, b) >= -1 and max(a, b) >= 10)):
            reasons.append(model + ":YEAR_STABILITY")
        correlation = out["correlation"]["pooled"]
        if correlation is None or correlation >= .25:
            reasons.append(model + ":CORRELATION_NOT_LT25")
    if cell["cell"]["asset"] == "US500" and cell["cell"]["horizon"] != "DAY":
        reasons.append("TARGET_DIVIDEND_CARRY_UNVERIFIED")
    return reasons


def select():
    cells = read(JOB / "natural-atlas.json")["cells"]
    core = {m: core_curves(m) for m in MODELS}
    original = {m: metrics(v) for m, v in core.items()}
    candidates = []
    for c in cells:
        c["satellite_reasons"] = satellite_reasons(c)
        if not c["satellite_reasons"]:
            candidates.append(c)
    selected = []
    trials = []
    current = core
    for slot in range(2):
        options = []
        for candidate in candidates:
            name = candidate["cell"]["id"]
            if any(name.rsplit(".", 1)[0] == s.rsplit(".", 1)[0] for s in selected):
                continue
            details = {}
            portfolio = {}
            gains = []
            for model in MODELS:
                with np.load(JOB / f"curve-{name}-{model}.npz") as stored:
                    small = [stored[k] for k in ("small_close", "small_low", "small_high")]
                portfolio[model] = [a + b for a, b in zip(current[model], small)]
                before, after = metrics(current[model]), metrics(portfolio[model])
                ratio0 = before["total_net_R"] / before["max_R_DD"]
                ratio1 = after["total_net_R"] / after["max_R_DD"]
                gains.append(ratio1 / ratio0)
                details[model] = dict(before=before, after=after, ratio_gain=ratio1 / ratio0)
            eligible = all(g > 1 for g in gains)
            trials.append(dict(slot=slot + 1, cell=name, eligible=eligible, models=details))
            if eligible:
                options.append((min(gains),
                                max(metrics(v)["max_R_DD"] for v in portfolio.values()),
                                name, portfolio))
        if not options:
            break
        options.sort(key=lambda row: (-row[0], row[1], row[2]))
        _, _, name, current = options[0]
        selected.append(name)
        candidates = [c for c in candidates if c["cell"]["id"] != name]
    rank = sorted(cells, key=lambda c: (
        -min(v["total_net_R"] for v in c["models"].values()),
        max(v["max_R_DD"] for v in c["models"].values()), c["cell"]["id"]))
    result = dict(
        selected=selected, cells=cells,
        top10=[c["cell"]["id"] for c in rank[:10]],
        top10_source_complete=[c["cell"]["id"] for c in rank if c["source_path_complete"]][:10],
        marginal_trials=trials, core_screen=original,
        only2022_2023=True, prices2024_2026_read=False,
        complete_paths=sum(c["source_path_complete"] for c in cells),
    )
    write_json(JOB / "satellite-decision.json", result)
    event("satellite_selection", selected=selected, marginal_trials=len(trials))


if __name__ == "__main__":
    select()
