"""Bit-exact pre-aligned M1 per-tier replay cache (strictly Dev `<= 2024`, zero linear scaling)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from quant_factory.capital_optimizer.constants import CORE7_IDS, TRADING_DAYS_PER_YEAR, StageArrays
from quant_factory.capital_optimizer.lot_sizing import assert_strict_pre_holdout_days, floor_lot_step


def _asset_currencies(asset: str) -> tuple[str, ...]:
    """Pure currency mapping matching `pass28_final_discovery_rednews_frontier.asset_currencies`."""
    if asset in ("US100", "US500", "XAUUSD"):
        return ("USD",)
    if asset == "GER40":
        return ("EUR",)
    if len(asset) == 6:
        return (asset[:3], asset[3:])
    return ("USD",)


def _margin_per_lot_usd(
    asset: str,
    entry_price: float,
    profile_mode: str = "Swing",
) -> tuple[float, float, float, float, float]:
    """Pure FTMO Demo bound margin/volume/commission specs (bit-identical to pass27, X13-safe)."""
    is_std = profile_mode == "Standard"
    if asset in ("US100", "US100.cash", "US500", "US500.cash"):
        mgn = entry_price * (0.02 if is_std else (1.0 / 15.0))
        return mgn, 0.01, 0.01, 1000.0, 0.0
    if asset == "XAUUSD":
        mgn = entry_price * 100.0 * (0.02 if is_std else 0.10)
        return mgn, 0.01, 0.01, 100.0, 5.20
    lev = 100.0 if is_std else 30.0
    if asset in ("USDJPY", "USDCAD", "USDCHF"):
        notional_usd = 100_000.0
    elif asset.startswith("EUR") and not asset.endswith("USD"):
        notional_usd = 100_000.0 * 1.15
    elif asset.startswith("GBP") and not asset.endswith("USD"):
        notional_usd = 100_000.0 * 1.35
    else:
        notional_usd = 100_000.0 * entry_price
    return notional_usd / lev, 0.01, 0.01, 50.0, 5.0


def _estimate_base_friction_usd_per_lot(row: dict[str, Any]) -> float:
    """Estimate per-lot round-trip friction USD (bit-identical to portfolio_v1_vs_v2_study, X13-safe)."""
    stop_cost = float(row.get("stop_risk_with_cost_usd") or 0.0)
    if stop_cost <= 0.0:
        return 0.0
    init_r = row.get("initial_risk_usd")
    if init_r is not None and float(init_r) > 0.0:
        diff = max(0.0, stop_cost - float(init_r))
        if diff > 0.0:
            return diff
    ep = row.get("entry_price")
    slp = row.get("sl_price") or row.get("stop")
    asset = str(row.get("asset") or "")
    if ep is not None and slp is not None and float(ep) > 0.0 and float(slp) > 0.0:
        dist = abs(float(ep) - float(slp))
        if asset in ("EURUSD", "GBPUSD", "AUDUSD"):
            raw_sl = dist * 100_000.0
        elif asset in ("USDJPY", "EURJPY", "GBPJPY"):
            usd_jpy = float(ep) if asset == "USDJPY" else 135.0
            raw_sl = dist * 100_000.0 / max(80.0, usd_jpy)
        elif asset in ("US100", "US500", "GER40"):
            raw_sl = dist * 1.0
        elif asset == "XAUUSD":
            raw_sl = dist * 100.0
        else:
            raw_sl = stop_cost * 0.96
        if 0.50 * stop_cost <= raw_sl < stop_cost:
            return max(stop_cost - raw_sl, 0.03 * stop_cost)
    return 0.035 * stop_cost


def _apply_cost_stress_to_tapes(
    tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]],
    cost_mult: float,
) -> dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]]:
    """Pure NumPy cost stress transform (bit-identical to portfolio_v1_vs_v2_study, X13-safe)."""
    if abs(cost_mult - 1.0) < 1e-9:
        return tapes
    delta_factor = float(cost_mult) - 1.0
    stressed: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]] = {}
    for eng, dm in tapes.items():
        new_dm: dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]] = {}
        for dk, (row, stamps, marks) in dm.items():
            base_fric = _estimate_base_friction_usd_per_lot(row)
            extra = delta_factor * base_fric
            new_row = {
                **row,
                "net_usd_per_lot": float(row["net_usd_per_lot"]) - extra,
                "stop_risk_with_cost_usd": float(row["stop_risk_with_cost_usd"]) + extra,
            }
            new_marks = np.asarray(marks, dtype=np.float64) - extra
            new_dm[dk] = (new_row, stamps, new_marks)
        stressed[eng] = new_dm
    return stressed


def _apply_red_news_guard_to_tape(
    tape: dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]],
    news_cal: dict[str, list[tuple[int, str]]],
    *,
    mode: str = "FLATTEN_5M",
    pad_sec: int = 300,
) -> tuple[dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]], dict[str, int]]:
    """Pure NumPy causal ±pad_sec red-news compliance guard (bit-identical to pass28, X13-safe)."""
    out: dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]] = {}
    stats = {
        "total_in": len(tape),
        "kept_untouched": 0,
        "blocked_entry": 0,
        "flattened_pre_news": 0,
        "skipped_day": 0,
    }
    for dk, (row, stamps, marks) in tape.items():
        asset = str(row.get("asset", "USDJPY"))
        ccys = set(_asset_currencies(asset))
        day_ev = [ts for ts, c in news_cal.get(dk, []) if c in ccys]
        if not day_ev:
            out[dk] = (row, stamps, marks)
            stats["kept_untouched"] += 1
            continue
        if mode == "SKIP_DAY":
            stats["skipped_day"] += 1
            continue
        t_ent = int(stamps[0])
        t_ext = int(row["exit"])
        if any(abs(t_ent - tn) <= pad_sec for tn in day_ev):
            stats["blocked_entry"] += 1
            continue
        cut_events = [tn - pad_sec for tn in day_ev if t_ent < (tn - pad_sec) < t_ext]
        if not cut_events:
            out[dk] = (row, stamps, marks)
            stats["kept_untouched"] += 1
            continue
        t_cut = min(cut_events)
        k = int(stamps.searchsorted(t_cut, side="right")) - 1
        if k < 0:
            stats["blocked_entry"] += 1
            continue
        new_stamps = stamps[: k + 1].copy()
        new_marks = marks[: k + 1].copy()
        term_pnl = float(new_marks[-1, 3])
        new_marks[-1, 3] = term_pnl
        new_row = {
            **row,
            "exit": int(new_stamps[-1]) + 60,
            "at_open": False,
            "reason": "NEWS_PRE_FLATTEN",
            "net_usd_per_lot": term_pnl,
            "net_R": float(term_pnl / row["stop_risk_with_cost_usd"]),
        }
        out[dk] = (new_row, new_stamps, new_marks)
        stats["flattened_pre_news"] += 1
    return out, stats


class ExactTierReplayCache:
    """Bit-exact pre-aligned M1 per-tier replay cache (pure Python/NumPy, X13-safe)."""

    def __init__(
        self,
        ext_days: list[str],
        raw_tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]],
        base_r: dict[str, float],
        red_news_cal: dict[str, list[tuple[int, str]]],
    ) -> None:
        self.holdout_rows_analysed = assert_strict_pre_holdout_days(ext_days)
        self.ext_days = sorted(ext_days)
        self.raw_tapes = raw_tapes
        self.base_r = dict(base_r)
        self.red_news_cal = red_news_cal
        self._stressed_tapes: dict[tuple[float, bool], dict[str, dict[str, Any]]] = {}
        self._prealigned_days: dict[tuple[float, bool], list[dict[str, Any]]] = {}
        self._replay_cache: dict[
            tuple[float, float, float, float, str, bool],
            tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray, np.ndarray],
        ] = {}

    def get_prepared_tapes(self, friction_mult: float, use_red_news: bool) -> dict[str, dict[str, Any]]:
        key = (round(float(friction_mult), 4), bool(use_red_news))
        if key in self._stressed_tapes:
            return self._stressed_tapes[key]

        base_key = (round(float(friction_mult), 4), False)
        if base_key not in self._stressed_tapes:
            stressed = _apply_cost_stress_to_tapes(self.raw_tapes, float(friction_mult))
            self._stressed_tapes[base_key] = stressed
        else:
            stressed = self._stressed_tapes[base_key]

        if not use_red_news:
            return stressed

        guarded: dict[str, dict[str, Any]] = {}
        for eng in CORE7_IDS:
            gt, _ = _apply_red_news_guard_to_tape(
                stressed[eng], self.red_news_cal, mode="FLATTEN_5M", pad_sec=300
            )
            guarded[eng] = gt
        self._stressed_tapes[key] = guarded
        return guarded

    def _get_prealigned_days(self, friction_mult: float, use_red_news: bool) -> list[dict[str, Any]]:
        """Pre-align 1-lot M1 mark matrices ONCE per `(friction_mult, use_red_news)`."""
        key = (round(float(friction_mult), 4), bool(use_red_news))
        if key in self._prealigned_days:
            return self._prealigned_days[key]

        tapes = self.get_prepared_tapes(friction_mult, use_red_news)
        pre_days: list[dict[str, Any]] = []
        for day_idx, dk in enumerate(self.ext_days):
            cands = [(eng, tapes[eng][dk]) for eng in CORE7_IDS if dk in tapes[eng]]
            if not cands:
                continue
            cands.sort(key=lambda kv: (kv[1][0]["entry"], kv[0]))
            k = len(cands)
            min_e = min(int(stamps[0]) for _, (_, stamps, _) in cands)
            max_x = max(int(stamps[-1]) for _, (_, stamps, _) in cands)
            n_tl = int((max_x - min_e) // 60) + 1
            marks_1lot = np.zeros((k, n_tl, 4), dtype=np.float64)

            meta_list: list[dict[str, Any]] = []
            for i, (eng, (row, stamps, marks)) in enumerate(cands):
                asset = row.get("asset") or (
                    "USDJPY" if "USDJPY" in eng else ("GBPUSD" if "GBPUSD" in eng else eng)
                )
                entry_ts = int(stamps[0])
                at_open = bool(row.get("at_open", False))
                release_ts = int(stamps[-1]) + (0 if at_open else 60)
                net_1lot = float(row["net_usd_per_lot"])
                stop_cost = float(row["stop_risk_with_cost_usd"])
                ep = float(row["entry_price"])
                mgn_std, vmin_s, vstep_s, vmax_s, comm_s = _margin_per_lot_usd(asset, ep, "Standard")
                mgn_swg, _vmin_w, _vstep_w, _vmax_w, comm_w = _margin_per_lot_usd(asset, ep, "Swing")

                offsets = (stamps - min_e) // 60
                start_o, end_o = int(offsets[0]), int(offsets[-1])
                marks_1lot[i, offsets, :] = marks
                if len(offsets) < (end_o - start_o + 1):
                    pos = np.arange(start_o, end_o + 1)
                    gaps = np.setdiff1d(pos, offsets, assume_unique=True)
                    past = offsets.searchsorted(gaps) - 1
                    marks_1lot[i, gaps, :] = marks[past, 3][:, None]
                if end_o + 1 < n_tl:
                    marks_1lot[i, end_o + 1 :, :] = net_1lot

                meta_list.append({
                    "eng": eng,
                    "asset": asset,
                    "base_r": self.base_r[eng],
                    "entry_ts": entry_ts,
                    "release_ts": release_ts,
                    "stop_cost": stop_cost,
                    "net_1lot": net_1lot,
                    "mgn_std": mgn_std,
                    "comm_std": comm_s,
                    "vmin": vmin_s,
                    "vstep": vstep_s,
                    "vmax": vmax_s,
                    "mgn_swg": mgn_swg,
                    "comm_swg": comm_w,
                    "stamps": stamps,
                    "marks": marks,
                })

            open_fl = np.zeros((k, k), dtype=np.float64)
            for j in range(k):
                st_j = meta_list[j]["entry_ts"]
                for i in range(j):
                    mi = meta_list[i]
                    if st_j >= mi["release_ts"]:
                        open_fl[i, j] = mi["net_1lot"]
                    else:
                        sc = mi["stamps"]
                        pos_i = int(sc.searchsorted(st_j))
                        if pos_i < len(sc) and int(sc[pos_i]) == st_j:
                            open_fl[i, j] = float(mi["marks"][pos_i, 0])
                        else:
                            open_fl[i, j] = float(mi["marks"][pos_i - 1, 3])

            pre_days.append({
                "day_idx": day_idx,
                "day": dk,
                "year": int(dk[:4]),
                "cands": meta_list,
                "marks_flat": np.ascontiguousarray(marks_1lot.reshape(k, n_tl * 4)),
                "open_fl": open_fl,
            })

        self._prealigned_days[key] = pre_days
        return pre_days

    def get_exact_tier_stage(
        self,
        *,
        capital_usd: float,
        mult: float,
        symcap_pct: float,
        profile_mode: str,
        use_red_news: bool,
        friction_mult: float,
    ) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        key = (
            round(float(capital_usd), 2),
            round(float(mult), 4),
            round(float(symcap_pct), 4),
            round(float(friction_mult), 4),
            str(profile_mode),
            bool(use_red_news),
        )
        if key in self._replay_cache:
            return self._replay_cache[key]

        pre_days = self._get_prealigned_days(friction_mult, use_red_news)
        n_days = len(self.ext_days)
        nets = np.zeros(n_days, dtype=np.float64)
        dds = np.zeros(n_days, dtype=np.float64)
        ups = np.zeros(n_days, dtype=np.float64)
        flg = np.zeros(n_days, dtype=np.int8)

        initial = float(capital_usd)
        balance = initial
        peak_eq = initial
        max_peak_dd = 0.0
        max_daily_dd = 0.0
        symcap = float(symcap_pct) / 100.0
        is_std = str(profile_mode) == "Standard"

        sized_cnt = 0
        min_lot_rej = 0
        margin_rej = 0
        symcap_skip = 0
        wins_sum = 0.0
        wins_cnt = 0
        loss_sum = 0.0
        loss_cnt = 0
        r_sum = 0.0
        r_cnt = 0
        cur_loss = 0
        max_loss = 0
        net_a = 0.0
        net_b = 0.0

        for pd_row in pre_days:
            cands = pd_row["cands"]
            k = len(cands)
            open_fl = pd_row["open_fl"]
            lots = np.zeros(k, dtype=np.float64)
            eff_risks = [0.0] * k
            margins = [0.0] * k
            any_sized = False

            for j in range(k):
                cj = cands[j]
                er = cj["base_r"] * float(mult)
                st_j = cj["entry_ts"]
                asset_j = cj["asset"]

                open_sym_r = 0.0
                for i in range(j):
                    if lots[i] > 0.0 and cands[i]["asset"] == asset_j and st_j < cands[i]["release_ts"]:
                        open_sym_r += eff_risks[i]
                rem = max(0.0, symcap - open_sym_r)
                if rem < er - 1e-12:
                    er = rem
                if er <= 1e-9:
                    symcap_skip += 1
                    continue

                budget = initial * er
                lot = floor_lot_step(
                    budget / cj["stop_cost"], step=cj["vstep"], vol_min=cj["vmin"], vol_max=cj["vmax"]
                )
                if lot < cj["vmin"]:
                    min_lot_rej += 1
                    continue

                mgn_1 = cj["mgn_std"] if is_std else cj["mgn_swg"]
                comm_1 = cj["comm_std"] if is_std else cj["comm_swg"]
                used_m = 0.0
                fl_sum = 0.0
                for i in range(j):
                    if lots[i] > 0.0:
                        if st_j < cands[i]["release_ts"]:
                            used_m += margins[i]
                        fl_sum += lots[i] * open_fl[i, j]
                avail = balance + fl_sum - used_m
                if lot * (mgn_1 + comm_1) > avail:
                    margin_rej += 1
                    continue

                lots[j] = lot
                eff_risks[j] = er
                margins[j] = lot * mgn_1
                any_sized = True
                sized_cnt += 1
                pnl_j = lot * cj["net_1lot"]
                if budget > 1e-9:
                    r_sum += pnl_j / budget
                    r_cnt += 1
                if pnl_j > 0.0:
                    wins_sum += pnl_j
                    wins_cnt += 1
                    cur_loss = 0
                elif pnl_j < 0.0:
                    loss_sum += -pnl_j
                    loss_cnt += 1
                    cur_loss += 1
                    if cur_loss > max_loss:
                        max_loss = cur_loss

            if not any_sized:
                continue

            comb = lots @ pd_row["marks_flat"]
            day_min_rel = float(comb.min())
            day_max_rel = float(comb.max())
            day_net = float(comb[-1])
            day_dd = max(0.0, -day_min_rel)
            day_up = max(0.0, day_max_rel)

            eq_pts = balance + comb
            if eq_pts.max() > peak_eq:
                run_peaks = np.maximum(peak_eq, np.maximum.accumulate(eq_pts))
                day_peak_dd = float(np.max(run_peaks - eq_pts))
                peak_eq = float(run_peaks[-1])
            else:
                day_peak_dd = float(peak_eq - eq_pts.min())
            if day_peak_dd > max_peak_dd:
                max_peak_dd = day_peak_dd
            if day_dd > max_daily_dd:
                max_daily_dd = day_dd

            d_i = pd_row["day_idx"]
            nets[d_i] = day_net
            dds[d_i] = day_dd
            ups[d_i] = day_up
            flg[d_i] = 1
            balance += day_net
            if pd_row["year"] <= 2020:
                net_a += day_net
            else:
                net_b += day_net

        yrs_span = max(1.0, float(len({d[:4] for d in self.ext_days})))
        ann_pct = 100.0 * ((balance - initial) / yrs_span) / initial
        peak_dd_pct = 100.0 * max_peak_dd / initial
        calmar = (ann_pct / peak_dd_pct) if peak_dd_pct > 1e-9 else 0.0
        daily_ret = nets / initial
        std_d = float(np.std(daily_ret, ddof=1)) if n_days > 1 else 0.0
        sharpe = (float(np.mean(daily_ret)) / std_d * math.sqrt(TRADING_DAYS_PER_YEAR)) if std_d > 1e-12 else 0.0
        pf = (wins_sum / loss_sum) if loss_sum > 1e-9 else 0.0
        wr = 100.0 * wins_cnt / max(1, wins_cnt + loss_cnt)
        rr = ((wins_sum / wins_cnt) / (loss_sum / loss_cnt)) if (wins_cnt > 0 and loss_cnt > 0) else 0.0
        ev_r = (r_sum / r_cnt) if r_cnt > 0 else 0.0
        tot_cand = sized_cnt + min_lot_rej + margin_rej

        bal_met = {
            "capital_usd": initial,
            "sized_trades": sized_cnt,
            "min_lot_rejected": min_lot_rej,
            "min_lot_reject_pct": round(100.0 * min_lot_rej / max(1, tot_cand), 3),
            "margin_rejected": margin_rej,
            "symcap_skipped": symcap_skip,
            "net_usd": round(balance - initial, 2),
            "ann_pct": round(ann_pct, 3),
            "ann_cluster_a_pct": round(100.0 * (net_a / 3.0) / initial, 3),
            "ann_cluster_b_pct": round(100.0 * (net_b / 4.0) / initial, 3),
            "peak_dd_pct": round(peak_dd_pct, 3),
            "max_daily_dd_pct": round(100.0 * max_daily_dd / initial, 3),
            "calmar": round(calmar, 3),
            "sharpe": round(sharpe, 3),
            "winrate_pct": round(wr, 2),
            "avg_rr": round(rr, 3),
            "ev_per_trade_r": round(ev_r, 4),
            "profit_factor": round(pf, 3),
            "max_loss_streak_trades": max_loss,
            "underwater_months": 0.0,
        }
        val = (bal_met, nets, dds, ups, flg)
        self._replay_cache[key] = val
        return val

    def build_stage_tuple(
        self,
        *,
        capital_usd: float,
        p1_mult: float,
        p1_lock_mult: float,
        p2_mult: float,
        p2_lock_mult: float,
        funded_mult: float,
        amber_mult: float,
        red_mult: float,
        p1_symcap: float,
        p2_symcap: float,
        fn_symcap: float,
        profile_mode: str,
        p1_news: bool,
        p2_news: bool,
        fn_news: bool,
        friction_mult: float,
        steps: int = 2,
    ) -> StageArrays:
        _, n_fn, d_fn, u_fn, f_fn = self.get_exact_tier_stage(
            capital_usd=capital_usd,
            mult=funded_mult,
            symcap_pct=fn_symcap,
            profile_mode=profile_mode,
            use_red_news=fn_news,
            friction_mult=friction_mult,
        )
        _, n_amb, d_amb, u_amb, f_amb = self.get_exact_tier_stage(
            capital_usd=capital_usd,
            mult=amber_mult,
            symcap_pct=fn_symcap,
            profile_mode=profile_mode,
            use_red_news=fn_news,
            friction_mult=friction_mult,
        )
        _, n_red, d_red, u_red, f_red = self.get_exact_tier_stage(
            capital_usd=capital_usd,
            mult=red_mult,
            symcap_pct=fn_symcap,
            profile_mode=profile_mode,
            use_red_news=fn_news,
            friction_mult=friction_mult,
        )
        if steps == 0:
            n_p1, d_p1, u_p1, f_p1 = n_fn, d_fn, u_fn, f_fn
            n_p1l, d_p1l, u_p1l, f_p1l = n_fn, d_fn, u_fn, f_fn
            n_p2, d_p2, u_p2, f_p2 = n_fn, d_fn, u_fn, f_fn
            n_p2l, d_p2l, u_p2l, f_p2l = n_fn, d_fn, u_fn, f_fn
        elif steps == 1:
            _, n_p1, d_p1, u_p1, f_p1 = self.get_exact_tier_stage(
                capital_usd=capital_usd,
                mult=p1_mult,
                symcap_pct=p1_symcap,
                profile_mode=profile_mode,
                use_red_news=p1_news,
                friction_mult=friction_mult,
            )
            _, n_p1l, d_p1l, u_p1l, f_p1l = self.get_exact_tier_stage(
                capital_usd=capital_usd,
                mult=p1_lock_mult,
                symcap_pct=p1_symcap,
                profile_mode=profile_mode,
                use_red_news=p1_news,
                friction_mult=friction_mult,
            )
            n_p2, d_p2, u_p2, f_p2 = n_fn, d_fn, u_fn, f_fn
            n_p2l, d_p2l, u_p2l, f_p2l = n_fn, d_fn, u_fn, f_fn
        else:
            _, n_p1, d_p1, u_p1, f_p1 = self.get_exact_tier_stage(
                capital_usd=capital_usd,
                mult=p1_mult,
                symcap_pct=p1_symcap,
                profile_mode=profile_mode,
                use_red_news=p1_news,
                friction_mult=friction_mult,
            )
            _, n_p1l, d_p1l, u_p1l, f_p1l = self.get_exact_tier_stage(
                capital_usd=capital_usd,
                mult=p1_lock_mult,
                symcap_pct=p1_symcap,
                profile_mode=profile_mode,
                use_red_news=p1_news,
                friction_mult=friction_mult,
            )
            _, n_p2, d_p2, u_p2, f_p2 = self.get_exact_tier_stage(
                capital_usd=capital_usd,
                mult=p2_mult,
                symcap_pct=p2_symcap,
                profile_mode=profile_mode,
                use_red_news=p2_news,
                friction_mult=friction_mult,
            )
            _, n_p2l, d_p2l, u_p2l, f_p2l = self.get_exact_tier_stage(
                capital_usd=capital_usd,
                mult=p2_lock_mult,
                symcap_pct=p2_symcap,
                profile_mode=profile_mode,
                use_red_news=p2_news,
                friction_mult=friction_mult,
            )
        return (
            n_p1, d_p1, u_p1, f_p1,
            n_p1l, d_p1l, u_p1l, f_p1l,
            n_p2, d_p2, u_p2, f_p2,
            n_p2l, d_p2l, u_p2l, f_p2l,
            n_fn, d_fn, u_fn, f_fn,
            n_amb, d_amb, u_amb, f_amb,
            n_red, d_red, u_red, f_red,
        )
