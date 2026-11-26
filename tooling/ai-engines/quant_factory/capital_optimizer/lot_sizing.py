"""Strict Holdout guard, exact 0.01-lot rounding simulator, and replay-exit metrics."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from quant_factory.capital_optimizer.constants import (
    HOLDOUT_CUTOFF_DAY,
    HOLDOUT_MAX_YEAR,
    TRADING_DAYS_PER_YEAR,
)


def assert_strict_pre_holdout_days(days: list[str] | tuple[str, ...]) -> int:
    """Fail-closed if ANY day is `>= 2025-01-01` or year > 2024; returns `holdout_rows_analysed = 0`."""
    for d in days:
        ds = str(d)
        if ds >= HOLDOUT_CUTOFF_DAY or int(ds[:4]) > HOLDOUT_MAX_YEAR:
            raise ValueError(f"HOLDOUT_LOCK_VIOLATION: forbidden holdout date detected: {ds}")
    return 0


def floor_lot_step(
    raw_lots: float,
    *,
    step: float = 0.01,
    vol_min: float = 0.01,
    vol_max: float = 1000.0,
) -> float:
    """Exact broker `0.01`-lot floor rounding (`< vol_min` returns `0.0`, trade skipped)."""
    if raw_lots <= 0.0 or not math.isfinite(raw_lots):
        return 0.0
    capped = min(float(raw_lots), float(vol_max))
    steps = math.floor(capped / step + 1e-9)
    lot = round(steps * step, 8)
    if lot < vol_min - 1e-12:
        return 0.0
    return lot


def simulate_exact_lot_rounding_on_trade_list(
    trades: list[dict[str, Any]],
    *,
    capital_usd: float,
    risk_mult: float = 1.0,
    vol_step: float = 0.01,
    vol_min: float = 0.01,
    vol_max: float = 1000.0,
    years_span: float = 7.0,
) -> dict[str, Any]:
    """Exact per-trade `0.01`-lot rounding evaluator (works on real frozen tapes OR synthetic fixtures)."""
    holdout_rows = 0
    total_signals = 0
    sized_trades = 0
    min_lot_rejected = 0
    ideal_risk_sum = 0.0
    actual_risk_sum = 0.0

    pnls: list[float] = []
    r_vals: list[float] = []
    bal = float(capital_usd)
    peak = bal
    max_dd = 0.0
    cur_loss_streak = 0
    max_loss_streak = 0
    day_pnls: dict[str, float] = {}

    for tr in trades:
        dk = str(tr["day"])
        yr = int(tr.get("year", int(dk[:4])))
        if dk >= HOLDOUT_CUTOFF_DAY or yr > HOLDOUT_MAX_YEAR:
            raise ValueError(
                f"HOLDOUT_LOCK_VIOLATION: trade date {dk} / year {yr} exceeds sealed 2024 cutoff"
            )
        total_signals += 1
        base_risk_frac = float(tr["base_risk_frac"])
        stop_cost_1lot = float(tr["stop_risk_with_cost_usd"])
        net_1lot = float(tr["net_usd_per_lot"])
        if stop_cost_1lot <= 0.0:
            continue

        budget_usd = float(capital_usd) * base_risk_frac * float(risk_mult)
        raw_lots = budget_usd / stop_cost_1lot
        lot = floor_lot_step(raw_lots, step=vol_step, vol_min=vol_min, vol_max=vol_max)

        ideal_risk_sum += budget_usd
        if lot <= 0.0:
            min_lot_rejected += 1
            continue

        sized_trades += 1
        actual_risk_usd = lot * stop_cost_1lot
        actual_risk_sum += actual_risk_usd
        pnl = lot * net_1lot
        pnls.append(pnl)
        r_vals.append(pnl / max(1e-9, budget_usd))
        day_pnls[dk] = day_pnls.get(dk, 0.0) + pnl

        bal += pnl
        if bal > peak:
            peak = bal
        dd = peak - bal
        if dd > max_dd:
            max_dd = dd

        if pnl < 0.0:
            cur_loss_streak += 1
            if cur_loss_streak > max_loss_streak:
                max_loss_streak = cur_loss_streak
        elif pnl > 0.0:
            cur_loss_streak = 0

    wins = [p for p in pnls if p > 0.0]
    losses = [p for p in pnls if p < 0.0]
    gross_win = float(sum(wins))
    gross_loss = abs(float(sum(losses)))
    pf = (gross_win / gross_loss) if gross_loss > 1e-9 else (99.0 if gross_win > 0.0 else 0.0)
    winrate_pct = (100.0 * len(wins) / len(pnls)) if pnls else 0.0
    avg_win = (gross_win / len(wins)) if wins else 0.0
    avg_loss = (gross_loss / len(losses)) if losses else 0.0
    rr = (avg_win / avg_loss) if avg_loss > 1e-9 else 0.0
    ev_r = float(np.mean(r_vals)) if r_vals else 0.0

    total_net = float(sum(pnls))
    ann_pct = 100.0 * (total_net / max(1e-9, float(years_span))) / float(capital_usd)
    max_dd_pct = 100.0 * max_dd / float(capital_usd)
    calmar = (ann_pct / max_dd_pct) if max_dd_pct > 1e-9 else 0.0

    if len(day_pnls) >= 2:
        dp = np.asarray(list(day_pnls.values()), dtype=np.float64) / float(capital_usd)
        std_d = float(np.std(dp, ddof=1))
        sharpe = (float(np.mean(dp)) / std_d * math.sqrt(TRADING_DAYS_PER_YEAR)) if std_d > 1e-12 else 0.0
    else:
        sharpe = 0.0

    return {
        "capital_usd": float(capital_usd),
        "risk_mult": float(risk_mult),
        "holdout_rows_analysed": holdout_rows,
        "total_signals": total_signals,
        "sized_trades": sized_trades,
        "min_lot_rejected": min_lot_rejected,
        "min_lot_reject_pct": round(100.0 * min_lot_rejected / max(1, total_signals), 3),
        "mean_risk_utilization_pct": round(100.0 * actual_risk_sum / max(1e-9, ideal_risk_sum), 2),
        "total_net_usd": round(total_net, 2),
        "ann_return_pct": round(ann_pct, 3),
        "max_dd_pct": round(max_dd_pct, 3),
        "calmar": round(calmar, 3),
        "sharpe": round(sharpe, 3),
        "winrate_pct": round(winrate_pct, 2),
        "avg_rr": round(rr, 3),
        "ev_per_trade_r": round(ev_r, 4),
        "profit_factor": round(pf, 3),
        "max_loss_streak_trades": max_loss_streak,
    }


def exits_to_daily_arrays_with_upside(
    ext_days: list[str],
    exits: list[dict[str, Any]],
    initial: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Convert M1 replay exits into dense daily `(net_usd, intraday_dd_usd, intraday_upside_usd, traded_flag)`."""
    by_day = {e["day"]: e for e in exits}
    n = len(ext_days)
    nets = np.zeros(n, dtype=np.float64)
    dds = np.zeros(n, dtype=np.float64)
    ups = np.zeros(n, dtype=np.float64)
    flg = np.zeros(n, dtype=np.int8)
    prev_cash = float(initial)
    for i, dk in enumerate(ext_days):
        e = by_day.get(dk)
        if e is not None:
            nets[i] = float(e["net_usd"])
            dds[i] = max(0.0, prev_cash - float(e["day_equity_minimum"]))
            ups[i] = max(0.0, float(e.get("day_equity_maximum", prev_cash + max(0.0, nets[i]))) - prev_cash)
            flg[i] = 1
            prev_cash = float(e["cash"])
    return nets, dds, ups, flg


def compute_exits_balanced_metrics(
    ext_days: list[str],
    exits: list[dict[str, Any]],
    replay_met: dict[str, Any],
    initial: float,
    tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]],
) -> dict[str, Any]:
    """Extract full balanced Law-15 portfolio statistics from exact M1 replay exits."""
    sized = 0
    min_lot_rej = 0
    margin_rej = 0
    symcap_rej = 0
    trade_pnls: list[float] = []
    trade_rs: list[float] = []
    cur_loss = 0
    max_loss = 0

    for ex in exits:
        dk = ex["day"]
        for o in ex.get("orders", []):
            st = o.get("status")
            if st == "SIZED":
                sized += 1
                eng = o["engine"]
                lots = float(o["lots"])
                eff_risk = float(o.get("eff_risk", 0.0))
                row = tapes[eng][dk][0]
                pnl = lots * float(row["net_usd_per_lot"])
                budget = initial * eff_risk
                trade_pnls.append(pnl)
                if budget > 1e-9:
                    trade_rs.append(pnl / budget)
                if pnl < 0.0:
                    cur_loss += 1
                    if cur_loss > max_loss:
                        max_loss = cur_loss
                elif pnl > 0.0:
                    cur_loss = 0
            elif st == "MIN_LOT":
                min_lot_rej += 1
            elif st == "MARGIN":
                margin_rej += 1
            elif st == "SYM_RISK_CAP_SKIP":
                symcap_rej += 1

    nets, _, _, _ = exits_to_daily_arrays_with_upside(ext_days, exits, initial)
    daily_ret = nets / max(1.0, float(initial))
    std_d = float(np.std(daily_ret, ddof=1)) if len(daily_ret) > 1 else 0.0
    sharpe = (float(np.mean(daily_ret)) / std_d * math.sqrt(TRADING_DAYS_PER_YEAR)) if std_d > 1e-12 else 0.0

    wins = [p for p in trade_pnls if p > 0.0]
    losses = [p for p in trade_pnls if p < 0.0]
    gwin = float(sum(wins))
    gloss = abs(float(sum(losses)))
    pf = (gwin / gloss) if gloss > 1e-9 else 0.0
    winrate = (100.0 * len(wins) / len(trade_pnls)) if trade_pnls else 0.0
    avg_w = (gwin / len(wins)) if wins else 0.0
    avg_l = (gloss / len(losses)) if losses else 0.0
    rr = (avg_w / avg_l) if avg_l > 1e-9 else 0.0
    ev_r = float(np.mean(trade_rs)) if trade_rs else 0.0
    tot_cand = sized + min_lot_rej + margin_rej

    return {
        "capital_usd": float(initial),
        "sized_trades": sized,
        "min_lot_rejected": min_lot_rej,
        "min_lot_reject_pct": round(100.0 * min_lot_rej / max(1, tot_cand), 3),
        "margin_rejected": margin_rej,
        "symcap_skipped": symcap_rej,
        "net_usd": round(float(replay_met["net_usd"]), 2),
        "ann_pct": round(float(replay_met["ann_pct"]["all"]), 3),
        "ann_cluster_a_pct": round(float(replay_met["ann_pct"]["A"]), 3),
        "ann_cluster_b_pct": round(float(replay_met["ann_pct"]["B"]), 3),
        "peak_dd_pct": round(float(replay_met["peak_dd_pct"]), 3),
        "max_daily_dd_pct": round(float(replay_met["daily_loss_pct"]), 3),
        "calmar": round(float(replay_met["calmar"]), 3),
        "sharpe": round(sharpe, 3),
        "winrate_pct": round(winrate, 2),
        "avg_rr": round(rr, 3),
        "ev_per_trade_r": round(ev_r, 4),
        "profit_factor": round(pf, 3),
        "max_loss_streak_trades": max_loss,
        "underwater_months": round(float(replay_met["underwater_months"]), 2),
    }
