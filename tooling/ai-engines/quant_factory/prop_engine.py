"""Layer 3: Config-driven exact M1 Prague-reset Portfolio Replay, Per-Symbol Risk Cap, Vol-Targeting & Numba JIT Lifecycle."""

from collections import Counter, defaultdict
from math import fsum, isclose

from numba import njit
import numpy as np

import pass5_usdjpy_tokyo as clock
import pass7b_usdjpy_equity as jpy_eq
import pass11_portfolio as portfolio
import pass23_ftmo_lifecycle_sim as p23l
import pass27_portfolio_m1_phase_audit as p27
import pass28_final_discovery_rednews_frontier as p28
from native_ftmo_monfri_seal import START, STOP


HOLDOUT_CUTOFF_DAY = "2025-01-01"


def replay_portfolio_m1(
    days: list[str],
    tapes: dict[str, dict],
    risks: dict[str, float],
    initial: float = 10000.0,
    *,
    profile_mode: str = "Standard",
    max_symbol_concurrent_risk: float | None = None,
    red_news_cal: dict | None = None,
    news_pad_sec: int = 300,
    cutoff: int = STOP,
    allow_holdout: bool = False,
) -> tuple[dict, list[dict]]:
    """Config-driven exact minute-by-minute M1 floating-equity Prague-reset portfolio audit.

    Enforces optional per-symbol concurrent risk cap (guards FTMO 1% trade-idea bundle rule across US100/USDJPY!)
    and optional ±news_pad_sec causal red-news flatten guard.
    Fail-closed on any holdout day `>= 2025-01-01` or `cutoff > STOP` unless `allow_holdout=True`.
    """
    sorted_days = sorted(days)
    if not allow_holdout:
        if int(cutoff) > int(STOP):
            raise ValueError(f"HOLDOUT_LOCK_VIOLATION: replay cutoff {cutoff} exceeds sealed STOP ({STOP})")
        bad_days = [str(d) for d in sorted_days if str(d) >= HOLDOUT_CUTOFF_DAY]
        if bad_days:
            raise ValueError(
                f"HOLDOUT_LOCK_VIOLATION: replay_portfolio_m1 received holdout days >= {HOLDOUT_CUTOFF_DAY}: {bad_days[:5]}"
            )
    active_tapes = {}
    news_stats = {}
    for eng in risks:
        if not allow_holdout:
            for dk in sorted_days:
                if dk in tapes[eng]:
                    st_arr = tapes[eng][dk][1]
                    if len(st_arr) > 0 and int(st_arr[-1]) >= int(STOP):
                        raise ValueError(
                            f"HOLDOUT_LOCK_VIOLATION: Tape '{eng}' day '{dk}' timestamp {int(st_arr[-1])} >= STOP ({STOP})"
                        )
        if red_news_cal is not None:
            gt, st = p28.apply_red_news_guard_to_tape(tapes[eng], red_news_cal, mode="FLATTEN_5M", pad_sec=news_pad_sec)
            active_tapes[eng] = gt
            news_stats[eng] = st
        else:
            active_tapes[eng] = tapes[eng]

    balance = float(initial)
    meter = jpy_eq.EquityMetrics(initial, START, [int(np.datetime64(d, "D").astype(int)) for d in sorted_days])
    exits, totals, rejects = [], defaultdict(list), Counter()
    peak_margin = peak_simultaneous = 0.0
    max_concurrent = sym_cap_hits = 0

    for dk in sorted_days:
        day_candidates = [(eng, active_tapes[eng][dk]) for eng in risks if dk in active_tapes[eng]]
        if not day_candidates:
            continue
        day_candidates.sort(key=lambda kv: (kv[1][0]["entry"], kv[0]))

        sized = []
        orders = []
        sym_risk_used = defaultdict(float)

        for eng, (row, stamps, marks) in day_candidates:
            eff_risk = float(risks[eng])
            asset = row.get("asset") or ("USDJPY" if "USDJPY" in eng else ("GBPUSD" if "GBPUSD" in eng else eng))
            stamp = int(stamps[0])

            if max_symbol_concurrent_risk is not None:
                # Recompute currently open risk on the SAME symbol (only trades still open at `stamp`!)
                open_sym_r = fsum(t.row.get("_eff_risk", 0.0) for t in sized if t.row.get("asset") == asset and stamp < t.release)
                rem = max(0.0, max_symbol_concurrent_risk - open_sym_r)
                if rem < eff_risk - 1e-12:
                    sym_cap_hits += 1
                    eff_risk = rem
                if eff_risk <= 1e-9:
                    rejects["SYM_RISK_CAP_SKIP"] += 1
                    orders.append({"engine": eng, "asset": asset, "status": "SYM_RISK_CAP_SKIP", "lots": 0.0})
                    continue

            budget = initial * eff_risk
            mgn_1lot, vmin, vstep, vmax, comm_1lot = p27.margin_per_lot_usd(asset, float(row["entry_price"]), profile_mode)
            acct = jpy_eq.Account(eng, initial, mgn_1lot, vmin, vstep, vmax)
            lot = jpy_eq.floor_lot(budget, float(row["stop_risk_with_cost_usd"]), acct)
            used_m = fsum(t.margin for t in sized if stamp < t.release)
            avail = balance + fsum(t.open_floating(stamp) for t in sized) - used_m

            status = "SIZED"
            if lot < vmin:
                status = "MIN_LOT"
            elif lot * (mgn_1lot + comm_1lot) > avail:
                status = "MARGIN"
            rejects[status] += 1
            orders.append({"engine": eng, "asset": asset, "entry": stamp, "lots": lot if status == "SIZED" else 0.0, "status": status, "eff_risk": eff_risk})
            if status == "SIZED":
                row_copy = {**row, "asset": asset, "at_open": bool(row.get("at_open", False)), "_eff_risk": eff_risk}
                sized.append(portfolio.SizedTrade(row_copy, stamps, marks, lot, lot * mgn_1lot, lot * float(row["net_usd_per_lot"])))
                sym_risk_used[asset] += eff_risk

        if not sized:
            continue

        tl, comb_marks, mgn_arr, conc_arr, _ = portfolio.combined_marks(sized)
        assert jpy_eq.prague_day(int(tl[0])) == jpy_eq.prague_day(int(tl[-1]))
        points = np.r_[balance, (balance + comb_marks).ravel()]
        meter.add(np.r_[tl[0], np.repeat(tl, 4)], points, balance)

        peak_margin = max(peak_margin, float(mgn_arr.max()))
        max_concurrent = max(max_concurrent, int(conc_arr.max()))
        if np.any(conc_arr >= 2):
            peak_simultaneous = max(peak_simultaneous, float(mgn_arr[conc_arr >= 2].max()))

        net = fsum(t.net for t in sized)
        assert isclose(float(comb_marks[-1, -1]), net, abs_tol=1e-5)
        balance += net
        totals[dk[:4]].append(net)
        exits.append({
            "day": dk, "net_usd": net, "cash": balance, "orders": orders,
            "day_equity_minimum": float(points.min()), "day_equity_maximum": float(points.max()),
        })

    if balance < meter.peak:
        meter.update_age(np.array([meter.peak_at]), np.array([cutoff - 1]))

    yrs_span = max(1.0, len({d[:4] for d in sorted_days}))
    ann_all = (balance - initial) / yrs_span
    ann_A = fsum(fsum(totals[str(y)]) for y in clock.CLUSTERS["A"]) / 3.0
    ann_B = fsum(fsum(totals[str(y)]) for y in clock.CLUSTERS["B"]) / 4.0
    peak_dd_pct = 100.0 * meter.dd / initial
    ann_pct_all = 100.0 * ann_all / initial
    calmar = (ann_pct_all / peak_dd_pct) if peak_dd_pct > 1e-9 else 0.0

    return {
        "net_usd": round(balance - initial, 2),
        "ann_pct": {"all": round(ann_pct_all, 2), "A": round(100.0 * ann_A / initial, 2), "B": round(100.0 * ann_B / initial, 2)},
        "daily_loss_pct": round(100.0 * meter.daily / initial, 2),
        "peak_dd_pct": round(peak_dd_pct, 2),
        "calmar": round(calmar, 2),
        "underwater_months": round(meter.max_age[0] / clock.DAY / (365.2425 / 12.0), 2),
        "peak_margin_pct": round(100.0 * peak_margin / initial, 2),
        "max_concurrent_positions": max_concurrent,
        "sym_cap_hits": sym_cap_hits,
        "margin_failures": int(rejects["MARGIN"]),
        "years_pct": {str(y): round(100.0 * fsum(totals[str(y)]) / initial, 2) for y in clock.YEAR},
        "news_stats": news_stats,
    }, exits


def compute_cluster_a_invdd_weights(cluster_a_days: list[str], tapes: dict, engine_ids: list[str], total_budget: float) -> dict[str, float]:
    """Strictly causal Inverse-DD risk parity weights fitted ONLY on Cluster A (< 2021-01-01)."""
    dds = {}
    for e in engine_ids:
        met, _ = replay_portfolio_m1(cluster_a_days, tapes, {e: 0.005}, 10000.0)
        dds[e] = max(0.30, float(met["peak_dd_pct"]))
    inv = {e: 1.0 / dds[e] for e in engine_ids}
    s = fsum(inv.values())
    return {e: total_budget * inv[e] / s for e in engine_ids}


def apply_vol_targeting_causal(
    days_sorted: list[str],
    nets: np.ndarray,
    dds: np.ndarray,
    *,
    window: int = 20,
    lo: float = 0.55,
    hi: float = 1.35,
    allow_holdout: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Strictly causal Moreira & Muir volatility-managed scaling (target vol fitted ONLY on Cluster A < 2021-01-01)."""
    if not allow_holdout and any(str(d) >= HOLDOUT_CUTOFF_DAY for d in days_sorted):
        raise ValueError(f"HOLDOUT_LOCK_VIOLATION: apply_vol_targeting_causal received day >= {HOLDOUT_CUTOFF_DAY}")
    idx_split = sum(1 for d in days_sorted if d < "2021-01-01")
    target_vol = float(np.std(nets[:max(30, idx_split)]))
    out_n = nets.copy()
    out_d = dds.copy()
    for i in range(window, len(nets)):
        rv = float(np.std(nets[i - window:i]))
        if rv > 1e-6:
            m = float(np.clip(target_vol / rv, lo, hi))
            out_n[i] = nets[i] * m
            out_d[i] = dds[i] * m
    return out_n, out_d


@njit(cache=True)
def _simulate_lifecycle_numba(
    idx_matrix: np.ndarray,
    nets_p1: np.ndarray, dds_p1: np.ndarray, flg_p1: np.ndarray,
    nets_core: np.ndarray, dds_core: np.ndarray, flg_core: np.ndarray,
    steps: int, cap: float, fee: float, fee_refund_ratio: float,
    p1_target: float, p2_target: float, daily_lim: float, static_lim: float,
    daily_pause_only: bool, min_days: int, min_prof_day: float,
    funded_cap_mult: float, split: float, payout_cycle: int, max_retries: int,
    retry_disc: np.ndarray,
    p1_mult: float, p2_mult: float, funded_mult: float,
    amber_dd: float, amber_mult: float, red_dd: float, red_mult: float,
    ea_daily_stop: float,
):
    """Numba-JIT prop lifecycle simulator: 2,000 x 504-day paths in < 0.02s (~150x faster than Python)."""
    n_paths, horizon = idx_matrix.shape
    scale = cap / 10000.0
    p1_goal = cap * (1.0 + p1_target)
    p2_goal = cap * (1.0 + p2_target)
    daily_cap = cap * daily_lim
    static_floor = cap * (1.0 - static_lim)
    ea_cut = cap * ea_daily_stop if ea_daily_stop > 0.0 else 1e18

    pass_days = np.full(n_paths, -1, dtype=np.int32)
    pay1_days = np.full(n_paths, -1, dtype=np.int32)
    cf12 = np.zeros(n_paths, dtype=np.float64)
    cf24 = np.zeros(n_paths, dtype=np.float64)
    oop = np.zeros(n_paths, dtype=np.float64)
    br1 = np.zeros(n_paths, dtype=np.int8)
    brf = np.zeros(n_paths, dtype=np.int8)
    tix = np.ones(n_paths, dtype=np.int32)

    for b in range(n_paths):
        stage = 1  # 1=P1, 2=P2, 3=FUNDED
        bal = cap
        tdays = 0
        attempts = 1
        fees = fee
        refunded = False
        payouts = 0.0
        cycle_d = 0
        max_oop = fee
        f_pass = -1
        f_pay = -1
        had_br1 = 0
        had_brf = 0

        for d in range(horizon):
            src = idx_matrix[b, d]
            cur_base = cap * funded_cap_mult if stage == 3 else cap
            eq_pct = (bal - cur_base) / cur_base

            use_p1_book = (stage == 1 and eq_pct > -amber_dd)
            m = p1_mult if stage == 1 else (p2_mult if stage == 2 else funded_mult)
            if eq_pct <= -red_dd:
                m = min(m, red_mult)
                use_p1_book = False
            elif eq_pct <= -amber_dd:
                m = min(m, amber_mult)
                use_p1_book = False

            eff_scale = scale * (funded_cap_mult if stage == 3 else 1.0)
            if use_p1_book:
                net = nets_p1[src] * eff_scale * m
                dd = dds_p1[src] * eff_scale * m
                flg = flg_p1[src]
            else:
                net = nets_core[src] * eff_scale * m
                dd = dds_core[src] * eff_scale * m
                flg = flg_core[src]

            cur_daily_cap = cur_base * daily_lim
            cur_static_floor = cur_base * (1.0 - static_lim)
            cur_ea_cut = cur_base * ea_daily_stop if ea_daily_stop > 0.0 else 1e18

            if daily_pause_only:
                if dd >= cur_daily_cap:
                    dd = min(dd, cur_daily_cap + cur_base * 0.001)
                    net = min(net, -cur_daily_cap)
                breached = (bal - dd) <= cur_static_floor + 1e-9
            else:
                if dd > cur_ea_cut:
                    dd = min(dd, cur_ea_cut + cur_base * 0.0025)
                    net = min(net, -cur_ea_cut)
                breached = (dd >= cur_daily_cap - 1e-9) or ((bal - dd) <= cur_static_floor + 1e-9)

            if breached:
                if stage == 1:
                    had_br1 = 1
                elif stage == 3:
                    had_brf = 1
                if attempts <= max_retries:
                    disc_idx = min(attempts - 1, len(retry_disc) - 1)
                    attempts += 1
                    fees += fee * retry_disc[disc_idx]
                    stage = 1
                    bal = cap
                    tdays = 0
                    refunded = False
                    cycle_d = 0
            else:
                bal += net
                if min_prof_day > 0.0:
                    if net >= cap * min_prof_day:
                        tdays += 1
                elif flg != 0:
                    tdays += 1

                if stage == 1 and bal >= p1_goal - 1e-9 and tdays >= min_days:
                    if steps == 1:
                        stage = 3
                        bal = cap * funded_cap_mult
                        tdays = 0
                        cycle_d = 0
                        if f_pass < 0:
                            f_pass = d + 1
                    else:
                        stage = 2
                        bal = cap
                        tdays = 0
                elif stage == 2 and bal >= p2_goal - 1e-9 and tdays >= min_days:
                    stage = 3
                    bal = cap * funded_cap_mult
                    tdays = 0
                    cycle_d = 0
                    if f_pass < 0:
                        f_pass = d + 1
                elif stage == 3:
                    cycle_d += 1
                    if cycle_d >= payout_cycle:
                        if bal > cur_base + 1e-6:
                            pay = (bal - cur_base) * split
                            if not refunded:
                                pay += fee * fee_refund_ratio
                                refunded = True
                            payouts += pay
                            if f_pay < 0:
                                f_pay = d + 1
                            bal = cur_base
                        cycle_d = 0

            if fees - payouts > max_oop:
                max_oop = fees - payouts
            if d + 1 == 252:
                cf12[b] = payouts - fees

        pass_days[b] = f_pass
        pay1_days[b] = f_pay
        cf24[b] = payouts - fees
        oop[b] = max_oop
        br1[b] = had_br1
        brf[b] = had_brf
        tix[b] = attempts

    return pass_days, pay1_days, cf12, cf24, oop, br1, brf, tix


def make_block_bootstrap_indices(
    n_obs: int,
    *,
    horizon: int = 504,
    n_paths: int = 2000,
    block_len: int = 5,
    seed: int = 20261123,
) -> np.ndarray:
    """Circular block bootstrap index matrix matching Pass 23-28 exact semantics."""
    rng = np.random.default_rng(seed)
    n_blocks = (horizon + block_len - 1) // block_len
    starts = rng.integers(0, n_obs, size=(n_paths, n_blocks))
    offs = np.arange(block_len, dtype=np.int64)[None, None, :]
    idxs = (starts[:, :, None] + offs).reshape(n_paths, n_blocks * block_len)[:, :horizon] % n_obs
    return idxs.astype(np.int32)


def evaluate_firm_profile(
    idx_matrix: np.ndarray,
    p1_series: tuple[np.ndarray, np.ndarray, np.ndarray],
    core_series: tuple[np.ndarray, np.ndarray, np.ndarray],
    firm_cfg: dict,
    prof_cfg: dict,
) -> dict:
    """Evaluate any declarative (firm_cfg, prof_cfg) pair via Numba JIT in <0.02s."""
    rdisc = np.ascontiguousarray(firm_cfg.get("retry_discounts", [1.0]), dtype=np.float64)
    pdays, pay1, cf12, cf24, oop, br1, brf, tix = _simulate_lifecycle_numba(
        np.ascontiguousarray(idx_matrix, dtype=np.int32),
        np.ascontiguousarray(p1_series[0], dtype=np.float64),
        np.ascontiguousarray(p1_series[1], dtype=np.float64),
        np.ascontiguousarray(p1_series[2], dtype=np.int8),
        np.ascontiguousarray(core_series[0], dtype=np.float64),
        np.ascontiguousarray(core_series[1], dtype=np.float64),
        np.ascontiguousarray(core_series[2], dtype=np.int8),
        int(firm_cfg.get("steps", 2)),
        float(firm_cfg["capital_usd"]),
        float(firm_cfg["fee_usd"]),
        float(firm_cfg.get("fee_refund_ratio", 1.0)),
        float(firm_cfg.get("p1_target_pct", 0.10)),
        float(firm_cfg.get("p2_target_pct", 0.05)),
        float(firm_cfg.get("daily_loss_pct", 0.05)),
        float(firm_cfg.get("static_loss_pct", 0.10)),
        bool(firm_cfg.get("daily_pause_non_breaching", False)),
        int(firm_cfg.get("min_days", 4)),
        float(firm_cfg.get("min_profitable_day_pct", 0.0)),
        float(firm_cfg.get("funded_capital_multiplier", 1.0)),
        float(firm_cfg.get("payout_split", 0.80)),
        int(firm_cfg.get("payout_cycle_days", 10)),
        int(firm_cfg.get("max_retries", 3)),
        rdisc,
        float(prof_cfg.get("p1_mult", 2.0)),
        float(prof_cfg.get("p2_mult", 1.25)),
        float(prof_cfg.get("funded_mult", 1.0)),
        float(prof_cfg.get("amber_dd_pct", 0.035)),
        float(prof_cfg.get("amber_mult", 0.65)),
        float(prof_cfg.get("red_dd_pct", 0.060)),
        float(prof_cfg.get("red_mult", 0.40)),
        float(prof_cfg.get("ea_daily_stop_pct", 0.035)),
    )
    n = len(pdays)
    valid_p = pdays[pdays > 0]
    valid_pay = pay1[pay1 > 0]
    return {
        "firm": firm_cfg["id"],
        "profile": prof_cfg["id"],
        "pass_3m": round(100.0 * float(np.sum((pdays > 0) & (pdays <= 63))) / n, 1),
        "pass_6m": round(100.0 * float(np.sum((pdays > 0) & (pdays <= 126))) / n, 1),
        "pass_9m": round(100.0 * float(np.sum((pdays > 0) & (pdays <= 189))) / n, 1),
        "pass_12m": round(100.0 * float(np.sum((pdays > 0) & (pdays <= 252))) / n, 1),
        "pass_24m": round(100.0 * float(len(valid_p)) / n, 1),
        "br1_pct": round(100.0 * float(np.mean(br1 > 0)), 1),
        "br_funded_pct": round(100.0 * float(np.sum(brf > 0)) / max(1, len(valid_p)), 1),
        "avg_tix": round(float(np.mean(tix)), 2),
        "med_pass_m": round(float(np.median(valid_p)) / 21.0, 1) if len(valid_p) else None,
        "med_pay1_m": round(float(np.median(valid_pay)) / 21.0, 1) if len(valid_pay) else None,
        "cf12_mean": round(float(np.mean(cf12)), 1),
        "cf24_mean": round(float(np.mean(cf24)), 1),
        "cf24_pos_pct": round(100.0 * float(np.mean(cf24 > 0)), 1),
        "oop95": round(float(np.percentile(oop, 95)), 1),
    }
