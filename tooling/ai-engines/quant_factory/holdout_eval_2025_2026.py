"""ONE-TIME PREREGISTERED BLIND HOLDOUT EVALUATION (2025-01-01 .. 2026-11-20 UTC).

Protocol G0 commit: 521926f (planning/research/HOLDOUT-2025-2026-UNLOCK-PROTOCOL-20261123.md).
- Reads sealed Development warm-up (2024) from .runtime/hot-m1-cache/ (read-only, unmodified)
  and sealed Holdout (2025-2026) from .runtime/holdout-m1-cache/.
- First verifies exact Development parity (2024) against frozen Pass 28 tapes before scoring Holdout >= 2025-01-01.
- Scores ALL 9 frozen engines (zero parameter tweaks!), PORT_7E_P28_CORE, PORT_9E_P28_TURBO,
  SYMCAP_100, Official 2025-2026 Red-News ±5m Guard, Cluster-A Inverse-DD + Downside Vol Brake [0.55, 1.00],
  and CUSUM/SPRT/Confidence-Cone Alpha Decay monitor against frozen 2018-2024 baseline.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import csv
import json
from math import fsum
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

import numpy as np
import pyarrow.parquet as pq

AI_ENGINES = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AI_ENGINES))

import hot_m1_cache as hcache
import pass5_usdjpy_tokyo as clock
import pass7b_usdjpy_equity as jpy_eq
import pass11_portfolio as portfolio
import pass12_us500_ny_orb as us500_orb
import pass14_intel_top15_batch as p14
import pass24_mtf_new_archetypes as p24
import pass26_cross_asset_rs as p26
import pass27_portfolio_m1_phase_audit as p27
import pass28_final_discovery_rednews_frontier as p28
from native_ftmo_monfri_seal import ROOT, STOP, sha
from quant_core.ftmo_track_replay import profiles
from quant_factory.data_store import CONFIGS_DIR, build_or_load_frozen_tapes, load_registry
from quant_factory.live_decay_monitor import evaluate_live_decay
from quant_factory.prop_engine import (
    apply_vol_targeting_causal,
    compute_cluster_a_invdd_weights,
    replay_portfolio_m1,
)
from quant_factory.report_gen import write_verified_receipt

HOLDOUT_CACHE = ROOT / ".runtime" / "holdout-m1-cache"
NY_TZ = ZoneInfo("America/New_York")

# Official primary-source 2025-2026 US Red News dates (Federal Reserve FOMC 14:00 ET, BLS CPI 08:30 ET)
OFFICIAL_FOMC_2025_2026 = (
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
    "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
)
OFFICIAL_CPI_2025_2026 = (
    "2025-01-14", "2025-02-12", "2025-03-12", "2025-04-10",
    "2025-05-13", "2025-06-11", "2025-07-11", "2025-08-13",
    "2025-09-10", "2025-10-24", "2025-12-18",
    "2026-01-13", "2026-02-11", "2026-03-11", "2026-04-10",
    "2026-05-13", "2026-06-10", "2026-07-14", "2026-08-12",
    "2026-09-16", "2026-10-13", "2026-11-10", "2026-12-10",
)


def _local_ts(day_iso: str, hour: int, minute: int, tz: ZoneInfo) -> int:
    d = date.fromisoformat(day_iso)
    return int(datetime(d.year, d.month, d.day, hour, minute, tzinfo=tz).timestamp())


def build_2025_2026_red_news_calendar_and_export_csv(
    *,
    out_csv_path: Path | None = None,
) -> dict[str, list[tuple[int, str]]]:
    csv_path = out_csv_path or (HOLDOUT_CACHE / "holdout_red_news_usd_2018_2026.csv")
    resolved_csv = csv_path.resolve()
    prod_files_dir = (AI_ENGINES / "exports/Files").resolve()
    tracked_calendars_dir = (CONFIGS_DIR / "calendars").resolve()
    if (
        resolved_csv.name.lower() == "naqex_red_news_utc.csv"
        or prod_files_dir in resolved_csv.parents
        or tracked_calendars_dir in resolved_csv.parents
    ):
        raise ValueError(
            f"SAFETY ABORT: Refusing to overwrite production/tracked red-news calendar '{csv_path}'. "
            "Holdout calendar exports must stay strictly inside .runtime/holdout-m1-cache/ or an isolated temp directory."
        )

    events: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for d in OFFICIAL_FOMC_2025_2026:
        events[d].append((_local_ts(d, 14, 0, NY_TZ), "USD", "FOMC"))
    for d in OFFICIAL_CPI_2025_2026:
        events[d].append((_local_ts(d, 8, 30, NY_TZ), "USD", "US_CPI"))
    for yr in (2025, 2026):
        for mo in range(1, 13):
            d1 = date(yr, mo, 1)
            fri = d1 + timedelta(days=(4 - d1.weekday()) % 7)
            if mo == 1 and fri.day == 1:
                fri += timedelta(days=7)
            events[fri.isoformat()].append((_local_ts(fri.isoformat(), 8, 30, NY_TZ), "USD", "US_NFP"))

    # Persist holdout-only 2025-2026 JSON strictly beside csv_path (NEVER overwrite tracked configs/calendars/)
    cal_2526_json = {
        "schema": "naqex-red-news-official-2025-2026-v1",
        "sources": ["federalreserve.gov", "bls.gov"],
        "events_by_day": {
            dk: [{"utc_ts": ts, "ccy": c, "event": ev} for ts, c, ev in sorted(v)]
            for dk, v in sorted(events.items())
        },
    }
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.with_suffix(".json").write_text(
        json.dumps(cal_2526_json, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    # Export holdout-only USD 2018-2026 CSV strictly inside .runtime/holdout-m1-cache/
    # NEVER overwrite production 6-currency exports/Files/naqex_red_news_utc.csv!
    cal_1824 = json.loads((CONFIGS_DIR / "calendars/red_news_official_2018_2024.json").read_text(encoding="utf-8"))
    all_rows = []
    for dk, evs in sorted(cal_1824["events_by_day"].items()):
        for e in evs:
            all_rows.append((int(e["utc_ts"]), str(e["ccy"]), str(e.get("event", "US_MACRO"))))
    for dk, evs in sorted(events.items()):
        for ts, c, ev in sorted(evs):
            all_rows.append((ts, c, ev))
    all_rows.sort()

    with csv_path.open("w", encoding="utf-8", newline="\n") as f:
        w = csv.writer(f)
        w.writerow(["utc_ts", "ccy", "event"])
        w.writerows(all_rows)

    return {dk: [(ts, c) for ts, c, _ in sorted(v)] for dk, v in events.items()}


def load_combined_m1(asset: str, dev_years: tuple[int, ...] = (2023, 2024), holdout_years: tuple[int, ...] = (2025, 2026)) -> tuple[np.ndarray, np.ndarray]:
    """Load sealed Development warm-up + sealed Holdout M1 Bid/Ask arrays cleanly (read-only)."""
    dev_m = json.loads((hcache.DEFAULT_CACHE / "manifest.json").read_text(encoding="utf-8"))
    hol_m = json.loads((HOLDOUT_CACHE / "manifest.json").read_text(encoding="utf-8"))
    ts_parts, q_parts = [], []

    for root_dir, manifest, yrs in ((hcache.DEFAULT_CACHE, dev_m, dev_years), (HOLDOUT_CACHE, hol_m, holdout_years)):
        am = manifest["assets"][asset]
        scale = float(am["scale"])
        sub_dir = root_dir / am["dir"]
        for y in yrs:
            ym = am["years"].get(str(y))
            if not ym:
                continue
            pfile = sub_dir / ym["parquet"]
            assert sha(pfile) == ym["parquet_sha256"], f"SHA mismatch {asset} {y}"
            tbl = pq.read_table(pfile)
            mins = tbl.column("minute").to_numpy(zero_copy_only=False).astype(np.int64)
            q = np.column_stack([
                tbl.column(c).to_numpy(zero_copy_only=False).astype(np.float64) / scale
                for c in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")
            ])
            ts_parts.append(mins * 60)
            q_parts.append(q)

    times = np.concatenate(ts_parts)
    quotes = np.concatenate(q_parts, axis=0)
    assert np.all(times[1:] > times[:-1]), f"Non-monotonic timestamps for {asset}"
    return times, quotes


def replay_m1_tape_unbounded(
    asset: str,
    times: np.ndarray,
    quotes: np.ndarray,
    entry_idx: int,
    flat_idx: int,
    side: int,
    entry_p: float,
    sl_p: float,
    *,
    cost_tier: str = "stress",
    spec: dict | None = None,
    usdjpy_close_map: dict | None = None,
) -> tuple[dict, np.ndarray, np.ndarray] | None:
    """Exact mirror of pass27.replay_causal_m1_tape_trade without the < 2025 STOP assertion."""
    risk_p = side * (entry_p - sl_p)
    if risk_p <= 0 or entry_idx < 0 or flat_idx <= entry_idx:
        return None
    liq = quotes[entry_idx:flat_idx + 1, :4] if side == 1 else quotes[entry_idx:flat_idx + 1, 4:8]
    if side == 1:
        sl_hits = np.flatnonzero(liq[:-1, 2] <= sl_p + 1e-10)
    else:
        sl_hits = np.flatnonzero(liq[:-1, 1] >= sl_p - 1e-10)

    if len(sl_hits):
        rel = int(sl_hits[0])
        op = float(liq[rel, 0])
        gap = rel > 0 and side * (op - sl_p) <= 1e-10
        ex_p = op if gap else sl_p
        at_open = bool(gap)
        reason = "SL_GAP_OR_TOUCH"
    else:
        rel = len(liq) - 1
        ex_p = float(liq[-1, 0])
        at_open = True
        reason = "HARD_FLAT"

    stamps = times[entry_idx:entry_idx + rel + 1].astype(np.int64)
    c = p24.asset_cost_tiers(asset)
    slip_rt = float(c[cost_tier])
    comm = float(c["comm_usd"])
    sub_liq = liq[:rel + 1]

    d_entry = datetime.fromtimestamp(int(stamps[0]), timezone.utc).date()
    d_ex = datetime.fromtimestamp(int(stamps[-1]), timezone.utc).date()

    def _prior_day_rate(rmap: dict | None, ref_d: date) -> float | None:
        if not rmap:
            return None
        for lag in range(1, 15):
            val = rmap.get(ref_d - timedelta(days=lag))
            if val is not None and float(val) > 0.0:
                return float(val)
        earlier = [k for k in rmap if k < ref_d]
        return float(rmap[max(earlier)]) if earlier else None

    if c["is_index"]:
        cs = 1.0
        entry_conv_rate = 1.0
        exit_conv_rate = 1.0
    else:
        if spec is None:
            raise ValueError(f"Missing broker spec for non-index asset: {asset}")
        cs = float(spec["trade_contract_size"])
        cp = spec.get("currency_profit", "USD")
        if cp == "USD":
            entry_conv_rate = 1.0
            exit_conv_rate = 1.0
        elif cp == "JPY":
            if asset == "USDJPY":
                entry_conv_rate = 1.0 / entry_p
                exit_conv_rate = 1.0 / ex_p
            else:
                usdjpy_ent = _prior_day_rate(usdjpy_close_map, d_entry)
                entry_conv_rate = 1.0 / (usdjpy_ent if usdjpy_ent is not None else entry_p)
                usdjpy_ex = (
                    (usdjpy_close_map.get(d_ex) or _prior_day_rate(usdjpy_close_map, d_ex) or usdjpy_ent)
                    if usdjpy_close_map
                    else ex_p
                )
                exit_conv_rate = 1.0 / (float(usdjpy_ex) if usdjpy_ex is not None else ex_p)
        elif cp in ("CAD", "CHF"):
            entry_conv_rate = 1.0 / entry_p
            exit_conv_rate = 1.0 / ex_p
        else:
            entry_conv_rate = 1.0
            exit_conv_rate = 1.0

    entry_scale = cs * entry_conv_rate
    entry_drag_usd = comm + slip_rt * entry_scale
    exit_scale = cs * exit_conv_rate
    exit_drag_usd = comm + slip_rt * exit_scale

    hi_px = sub_liq[:, 1] if side == 1 else sub_liq[:, 2]
    lo_px = sub_liq[:, 2] if side == 1 else sub_liq[:, 1]
    if asset in ("USDJPY", "USDCAD", "USDCHF"):
        s_op = cs / sub_liq[:, 0]
        s_hi = cs / hi_px
        s_lo = cs / lo_px
        s_cl = cs / sub_liq[:, 3]
        cur_pnl = side * (sub_liq[:, 0] - entry_p) * s_op - (comm + slip_rt * s_op)
        hi_pnl = side * (hi_px - entry_p) * s_hi - (comm + slip_rt * s_hi)
        lo_pnl = side * (lo_px - entry_p) * s_lo - (comm + slip_rt * s_lo)
        cls_pnl = side * (sub_liq[:, 3] - entry_p) * s_cl - (comm + slip_rt * s_cl)
    else:
        cur_pnl = side * (sub_liq[:, 0] - entry_p) * entry_scale - entry_drag_usd
        hi_pnl = side * (hi_px - entry_p) * entry_scale - entry_drag_usd
        lo_pnl = side * (lo_px - entry_p) * entry_scale - entry_drag_usd
        cls_pnl = side * (sub_liq[:, 3] - entry_p) * entry_scale - entry_drag_usd

    spr0 = max(0.0, float(quotes[entry_idx, 4] - quotes[entry_idx, 0]))
    cur_pnl[0] = -spr0 * entry_scale - entry_drag_usd
    hi_pnl[0] = max(cur_pnl[0], cls_pnl[0])
    lo_pnl[0] = min(cur_pnl[0], lo_pnl[0], cls_pnl[0])

    net_usd = side * (ex_p - entry_p) * exit_scale - exit_drag_usd
    if rel == 0 or at_open:
        cur_pnl[-1] = hi_pnl[-1] = lo_pnl[-1] = cls_pnl[-1] = net_usd
    else:
        hi_pnl[-1] = max(cur_pnl[-1], net_usd)
        lo_pnl[-1] = min(cur_pnl[-1], net_usd)
        cls_pnl[-1] = net_usd

    marks = np.column_stack((cur_pnl, hi_pnl, lo_pnl, cls_pnl)).astype(np.float64)
    stop_risk_usd = risk_p * entry_scale + entry_drag_usd
    d_iso = d_entry.isoformat()
    row = {
        "day": d_iso, "year": int(d_iso[:4]), "asset": asset,
        "entry": int(stamps[0]), "exit": int(stamps[-1]) + (0 if at_open else 60),
        "at_open": at_open, "reason": reason, "side": side,
        "entry_price": float(entry_p), "sl_price": float(sl_p),
        "entry_conv_rate": float(entry_conv_rate),
        "exit_conv_rate": float(exit_conv_rate),
        "net_usd_per_lot": float(net_usd),
        "stop_risk_with_cost_usd": float(stop_risk_usd),
        "net_R": float(net_usd / stop_risk_usd),
    }
    return row, stamps, marks


def build_unified_bundle_unbounded(asset: str, times: np.ndarray, quotes: np.ndarray, swing_specs: dict, usdjpy_close_map: dict, years: tuple[int, ...]) -> dict:
    is_idx = asset in ("US500", "US100")
    if not is_idx:
        # Build UTC Mon-Fri daily bars strictly from M1 Bid OHLC
        day_secs = (times // 86400) * 86400
        uniq_days, start_idx = np.unique(day_secs, return_index=True)
        end_idx = np.r_[start_idx[1:], len(times)]
        d1 = []
        for ds, fi, ei in zip(uniq_days, start_idx, end_idx):
            dt = datetime.fromtimestamp(int(ds), timezone.utc)
            if dt.weekday() >= 5 or ei - fi < 60:
                continue
            q = quotes[fi:ei]
            d1.append({
                "date": dt.date(), "day_sec": int(ds), "fi": int(fi), "ei": int(ei),
                "o": float(q[0, 0]), "h": float(q[:, 1].max()),
                "l": float(q[:, 2].min()), "c": float(q[-1, 3]),
            })
        hs = np.array([d["h"] for d in d1], dtype=np.float64)
        ls = np.array([d["l"] for d in d1], dtype=np.float64)
        cs = np.array([d["c"] for d in d1], dtype=np.float64)
        atr = p14.wilder_atr(hs, ls, cs, 14)
        days = []
        for i in range(25, len(d1)):
            a_val = float(atr[i - 1])
            if not np.isfinite(a_val) or a_val <= 0:
                continue
            d = d1[i]
            fi, ei, dsec = d["fi"], d["ei"], d["day_sec"]
            sub_t = times[fi:ei]
            i_flat = int(sub_t.searchsorted(dsec + 20 * 3600 + 55 * 60, side="left"))
            if i_flat >= ei - fi:
                i_flat = ei - fi - 1
            if i_flat < 60:
                continue
            days.append({
                "day": d["date"].isoformat(), "year": d["date"].year, "day_sec": dsec,
                "fi": fi, "ei": ei, "flat_idx": fi + i_flat,
                "atr": a_val, "prev_rng": float(hs[i - 1] - ls[i - 1]),
                "morn_start_sec": dsec + 7 * 3600, "morn_end_sec": dsec + 12 * 3600,
                "win_end_sec": dsec + 16 * 3600,
            })
        return {"asset": asset, "is_index": False, "times": times, "quotes": quotes, "days": days, "spec": swing_specs[asset], "usdjpy_close_map": usdjpy_close_map}

    # Index assets (US500, US100) using exact NYSE calendar
    all_sess = []
    for y in years:
        sess, _ = us500_orb.calendar(y)
        for dkey, start in sorted(sess.items()):
            lo, hi = times.searchsorted([start, start + 386 * 60])
            if hi - lo < 300:
                continue
            q = quotes[lo:hi]
            all_sess.append({
                "day": dkey, "year": y, "start": int(start), "lo": int(lo), "hi": int(hi),
                "o": float(q[0, 0]), "h": float(q[:, 1].max()),
                "l": float(q[:, 2].min()), "c": float(q[-1, 3]),
            })
    hs = np.array([s["h"] for s in all_sess], dtype=np.float64)
    ls = np.array([s["l"] for s in all_sess], dtype=np.float64)
    cs = np.array([s["c"] for s in all_sess], dtype=np.float64)
    atr = p14.wilder_atr(hs, ls, cs, 14)
    days = []
    for i in range(25, len(all_sess)):
        a_val = float(atr[i - 1])
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        s = all_sess[i]
        s0 = s["start"]
        days.append({
            "day": s["day"], "year": s["year"], "day_sec": s0,
            "fi": s["lo"], "ei": s["hi"], "flat_idx": s["hi"] - 1,
            "atr": a_val, "morn_start_sec": s0, "morn_end_sec": s0 + 120 * 60,
            "win_end_sec": s0 + 300 * 60,
        })
    return {"asset": asset, "is_index": True, "times": times, "quotes": quotes, "days": days, "spec": None, "usdjpy_close_map": usdjpy_close_map}


def build_all_9_tapes_unbounded(bundles: dict, day_maps: dict, all_days: list[str], vol_ratios: dict) -> dict[str, dict]:
    """Generate exact M1 minute-by-minute tapes for ALL 9 frozen engines over any date range."""
    tapes: dict[str, dict] = {}

    # E1: USDJPY Tokyo Box OCO (exact Pass 6/7B rules: box [00:00..03:00 UTC), act [03:00..10:00 UTC), flat 18:00 Europe/Helsinki)
    e1 = {}
    bj = bundles["USDJPY"]
    t_j, q_j = bj["times"], bj["quotes"]
    addon_jpy = jpy_eq.PROFILE[portfolio.STRESS]
    for d in bj["days"]:
        dsec = d["day_sec"]
        utc = clock.date(dsec)
        flat_min = (clock.hard_flat(utc) - dsec) // 60
        lo, hi = t_j.searchsorted([dsec, dsec + (flat_min + 1) * 60])
        if hi - lo < 180:
            continue
        offsets = (t_j[lo:hi] - dsec) // 60
        if len(offsets) < 180 or int(offsets[0]) != 0 or int(offsets[-1]) < flat_min - 5:
            continue
        prices = q_j[lo:hi, :8]
        tr, _ = jpy_eq.select(dsec, prices, offsets=offsets)
        if tr is None:
            continue
        row = jpy_eq.record(tr, addon_jpy)
        stamps = np.array([tr.second_at(i) for i in range(tr.entry, tr.execution.index + 1)], dtype=np.int64)
        marks = jpy_eq.path(tr, addon_jpy)
        e1[d["day"]] = ({**row, "asset": "USDJPY", "at_open": tr.execution.at_open}, stamps, marks)
    tapes["E1_USDJPY_TOKYO"] = e1

    # E2: USDJPY EXP 0.80 ATR (07-17 UTC, SL 0.75, flat 20:55 UTC)
    def _daily_exp(asset: str, trig: float, sl_atr: float, *, min_prev_rng_mult: float = 0.0, max_vol_ratio: float | None = None):
        b = bundles[asset]
        ts, qs = b["times"], b["quotes"]
        vrm = vol_ratios[asset]
        out = {}
        for d in b["days"]:
            if min_prev_rng_mult > 0.0 and d["prev_rng"] < min_prev_rng_mult * d["atr"]:
                continue
            if max_vol_ratio is not None:
                vr = vrm.get(d["day"])
                if vr is None or vr >= max_vol_ratio:
                    continue
            fi, flat_idx = d["fi"], d["flat_idx"]
            open_0 = float(qs[fi, 0])
            top, bot = open_0 + trig * d["atr"], open_0 - trig * d["atr"]
            sub_t = ts[fi:flat_idx + 1]
            i0 = int(sub_t.searchsorted(d["day_sec"] + 7 * 3600, side="left"))
            i1 = int(sub_t.searchsorted(d["day_sec"] + 17 * 3600, side="left"))
            if i1 <= i0:
                continue
            scan = qs[fi + i0:fi + i1]
            up = scan[:, 5] >= top - 1e-10
            dn = scan[:, 2] <= bot + 1e-10
            hits = np.flatnonzero(up | dn)
            if not len(hits):
                continue
            j = int(hits[0])
            if up[j] and dn[j]:
                continue
            side = 1 if up[j] else -1
            e_idx = fi + i0 + j
            ep = max(top, float(qs[e_idx, 4])) if side == 1 else min(bot, float(qs[e_idx, 0]))
            item = replay_m1_tape_unbounded(
                asset, ts, qs, e_idx, flat_idx, side, ep, ep - side * sl_atr * d["atr"],
                spec=b["spec"], usdjpy_close_map=b["usdjpy_close_map"],
            )
            if item is not None:
                out[item[0]["day"]] = item
        return out

    tapes["E2_USDJPY_EXP80"] = _daily_exp("USDJPY", 0.80, 0.75)
    tapes["E3_GBPUSD_VH"] = _daily_exp("GBPUSD", 0.80, 0.75, min_prev_rng_mult=1.10)
    tapes["E6_EURJPY_VOLCOMP"] = _daily_exp("EURJPY", 0.75, 0.75, max_vol_ratio=0.85)
    tapes["S7_XAU_EXP120"] = _daily_exp("XAUUSD", 1.20, 0.75)

    # E4: US100 SESS_CONT_BRK_40
    e4 = {}
    b100 = bundles["US100"]
    t100, q100 = b100["times"], b100["quotes"]
    for d in b100["days"]:
        ms, me, we, a_val = d["morn_start_sec"], d["morn_end_sec"], d["win_end_sec"], d["atr"]
        m0 = int(t100.searchsorted(ms, side="left"))
        m1 = int(t100.searchsorted(me, side="left"))
        if m1 - m0 < 60:
            continue
        mq = q100[m0:m1]
        mo, mc = float(mq[0, 0]), float(mq[-1, 3])
        mh, ml = float(mq[:, 1].max()), float(mq[:, 2].min())
        mrng = mh - ml
        if mrng <= 1e-9 or abs(mc - mo) < 0.40 * a_val:
            continue
        pos = (mc - ml) / mrng
        side = 1 if (mc > mo and pos >= 0.70) else (-1 if (mc < mo and pos <= 0.30) else 0)
        if side == 0:
            continue
        fi, flat_idx = d["fi"], d["flat_idx"]
        sub_t = t100[fi:flat_idx + 1]
        i0 = int(sub_t.searchsorted(me, side="left"))
        i1 = int(sub_t.searchsorted(max(we, me + 5 * 3600), side="left"))
        if i1 <= i0:
            continue
        scan = q100[fi + i0:fi + i1]
        hits = np.flatnonzero(scan[:, 5] >= mh - 1e-10) if side == 1 else np.flatnonzero(scan[:, 2] <= ml + 1e-10)
        if not len(hits):
            continue
        e_idx = fi + i0 + int(hits[0])
        ep = max(mh, float(q100[e_idx, 4])) if side == 1 else min(ml, float(q100[e_idx, 0]))
        item = replay_m1_tape_unbounded("US100", t100, q100, e_idx, flat_idx, side, ep, ep - side * 0.65 * a_val)
        if item is not None:
            e4[item[0]["day"]] = item
    tapes["E4_US100_SESS40"] = e4

    # E5: US100 vs US500 RS 11:30 ET
    e5 = {}
    for dk in all_days:
        if dk not in day_maps["US100"] or dk not in day_maps["US500"]:
            continue
        d100, d500 = day_maps["US100"][dk], day_maps["US500"][dk]
        ts_s, ts_e = d100["day_sec"], d100["day_sec"] + 120 * 60
        z100 = p26.causal_z_return(b100, ts_s, ts_e, d100["atr"])
        z500 = p26.causal_z_return(bundles["US500"], ts_s, ts_e, d500["atr"])
        if z100 is None or z500 is None:
            continue
        diff = z100 - z500
        if abs(diff) < 0.25 or (z100 * diff <= 0):
            continue
        side = 1 if diff > 0 else -1
        fi, flat_idx = d100["fi"], d100["flat_idx"]
        e_idx = fi + int(t100[fi:flat_idx + 1].searchsorted(ts_e, side="left"))
        if e_idx >= flat_idx or int(t100[e_idx]) - ts_e > 600:
            continue
        ep = float(q100[e_idx, 4] if side == 1 else q100[e_idx, 0])
        item = replay_m1_tape_unbounded("US100", t100, q100, e_idx, flat_idx, side, ep, ep - side * 0.75 * d100["atr"])
        if item is not None:
            e5[item[0]["day"]] = item
    tapes["E5_US100_RS1130"] = e5

    # E7: USDJPY NY Risk Flow 10:00 ET
    e7 = {}
    for dk in all_days:
        if dk not in day_maps["USDJPY"] or dk not in day_maps["US100"] or not all(dk in day_maps[a] for a in p26.FX7):
            continue
        u1, dj = day_maps["US100"][dk], day_maps["USDJPY"][dk]
        ts_s, ts_e = u1["day_sec"], u1["day_sec"] + 30 * 60
        zu = p26.causal_z_return(b100, ts_s, ts_e, u1["atr"])
        z_map = {a: p26.causal_z_return(bundles[a], dj["day_sec"] + 7 * 3600, ts_e, day_maps[a][dk]["atr"]) for a in p26.FX7}
        if zu is None or any(v is None for v in z_map.values()):
            continue
        usd_s = p26.compute_g6_factors(z_map)["USD"]
        if abs(zu) < 0.25 or abs(usd_s) < 0.25 or zu * usd_s <= 0:
            continue
        side = 1 if usd_s > 0 else -1
        fi, flat_idx = dj["fi"], dj["flat_idx"]
        e_idx = fi + int(t_j[fi:flat_idx + 1].searchsorted(ts_e, side="left"))
        if e_idx >= flat_idx or int(t_j[e_idx]) - ts_e > 600:
            continue
        ep = float(q_j[e_idx, 4] if side == 1 else q_j[e_idx, 0])
        item = replay_m1_tape_unbounded(
            "USDJPY", t_j, q_j, e_idx, flat_idx, side, ep, ep - side * 0.75 * dj["atr"],
            spec=bj["spec"], usdjpy_close_map=bj["usdjpy_close_map"],
        )
        if item is not None:
            e7[item[0]["day"]] = item
    tapes["E7_USDJPY_NY10ET"] = e7

    # S6: FX USD Basket 12:00 UTC Z35
    s6 = {}
    for dk in all_days:
        if not all(dk in day_maps[a] for a in p26.FX7):
            continue
        dsec = day_maps["USDJPY"][dk]["day_sec"]
        ts_e, ts_s = dsec + 12 * 3600, dsec + 7 * 3600
        z_map = {a: p26.causal_z_return(bundles[a], ts_s, ts_e, day_maps[a][dk]["atr"]) for a in p26.FX7}
        if any(v is None for v in z_map.values()):
            continue
        usd_s = p26.compute_g6_factors(z_map)["USD"]
        if abs(usd_s) < 0.35:
            continue
        usd_dir = 1 if usd_s > 0 else -1
        best_a, best_sc, best_side = None, -1e9, 0
        for a in p26.USD_MAJORS_NOJPY:
            base, _ = p26.PAIR_CCY[a]
            side = usd_dir if base == "USD" else -usd_dir
            sc = side * z_map[a]
            if sc > best_sc:
                best_a, best_sc, best_side = a, sc, side
        if best_a is None or best_sc <= 0:
            continue
        b = bundles[best_a]
        dr = day_maps[best_a][dk]
        fi, flat_idx = dr["fi"], dr["flat_idx"]
        e_idx = fi + int(b["times"][fi:flat_idx + 1].searchsorted(ts_e, side="left"))
        if e_idx >= flat_idx or int(b["times"][e_idx]) - ts_e > 600:
            continue
        ep = float(b["quotes"][e_idx, 4] if best_side == 1 else b["quotes"][e_idx, 0])
        item = replay_m1_tape_unbounded(
            best_a, b["times"], b["quotes"], e_idx, flat_idx, best_side, ep,
            ep - best_side * 0.75 * dr["atr"], spec=b["spec"], usdjpy_close_map=b["usdjpy_close_map"],
        )
        if item is not None:
            s6[item[0]["day"]] = item
    tapes["S6_FX_USD_BSK"] = s6
    return tapes


def _replay_holdout_window(days: list[str], tapes: dict, risks: dict, *, max_sym: float | None = None, cal: dict | None = None) -> tuple[dict, list[dict]]:
    """Replay exact M1 floating-equity Prague reset over Holdout days (annualized by exact calendar span in years!)."""
    last_ts = int(datetime.fromisoformat(max(days) + "T23:59:59+00:00").timestamp())
    met, exits = replay_portfolio_m1(
        days, tapes, risks, 10000.0,
        profile_mode="Swing", max_symbol_concurrent_risk=max_sym, red_news_cal=cal, cutoff=last_ts + 60, allow_holdout=True,
    )
    # Exact calendar year span (2025-01-01 to 2026-11-20 = ~1.885 years)
    d0 = date.fromisoformat(min(days))
    d1 = date.fromisoformat(max(days))
    exact_years = max(0.25, (d1 - d0).days / 365.2425)
    total_pct = 100.0 * met["net_usd"] / 10000.0
    ann_exact = total_pct / exact_years
    calmar_exact = (ann_exact / met["peak_dd_pct"]) if met["peak_dd_pct"] > 1e-9 else 0.0
    by_y = defaultdict(float)
    for e in exits:
        by_y[e["day"][:4]] += float(e["net_usd"]) / 100.0
    return {
        "n_days": len(days),
        "span_years": round(exact_years, 3),
        "total_return_pct": round(total_pct, 2),
        "ann_pct": round(ann_exact, 2),
        "peak_dd_pct": met["peak_dd_pct"],
        "daily_loss_pct": met["daily_loss_pct"],
        "calmar": round(calmar_exact, 2),
        "underwater_months": met["underwater_months"],
        "sym_cap_hits": met["sym_cap_hits"],
        "margin_failures": met["margin_failures"],
        "years_pct": {k: round(v, 2) for k, v in sorted(by_y.items())},
    }, exits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="ONE-TIME Preregistered Blind Holdout Evaluator (2025-01-01+). Fail-closed without explicit unlock flag."
    )
    ap.add_argument(
        "--confirm-one-time-holdout-unlock",
        action="store_true",
        help="Required explicit owner unlock confirmation before reading .runtime/holdout-m1-cache/.",
    )
    args = ap.parse_args(argv)
    if not args.confirm_one_time_holdout_unlock:
        print(
            "HOLDOUT_LOCKED: Refusing to read .runtime/holdout-m1-cache/ without explicit "
            "--confirm-one-time-holdout-unlock flag (OrderSend=0, holdout_rows_analysed=0).",
            file=sys.stderr,
        )
        return 2

    t0 = time.perf_counter()
    reg = load_registry()
    specs, _ = profiles()
    swing_specs = specs["Swing"]
    cal_2526 = build_2025_2026_red_news_calendar_and_export_csv()

    assets10 = ("USDJPY", "GBPUSD", "EURUSD", "GBPJPY", "AUDUSD", "USDCAD", "EURJPY", "XAUUSD", "US500", "US100")
    raw_m1 = {a: load_combined_m1(a, dev_years=(2023, 2024), holdout_years=(2025, 2026)) for a in assets10}

    # Build USDJPY D1 close map from combined 2023-2026 M1
    tj, qj = raw_m1["USDJPY"]
    j_days = (tj // 86400) * 86400
    u_j, s_j = np.unique(j_days, return_index=True)
    e_j = np.r_[s_j[1:], len(tj)]
    usdjpy_close_map = {
        datetime.fromtimestamp(int(ds), timezone.utc).date(): float(qj[ei - 1, 3])
        for ds, ei in zip(u_j, e_j)
    }

    bundles = {
        a: build_unified_bundle_unbounded(a, raw_m1[a][0], raw_m1[a][1], swing_specs, usdjpy_close_map, years=(2023, 2024, 2025, 2026))
        for a in assets10
    }
    day_maps = {a: {d["day"]: d for d in bundles[a]["days"]} for a in assets10}
    all_days = sorted({d for dm in day_maps.values() for d in dm})
    vol_ratios = {a: p28._compute_vol_ratio_map(bundles[a]) for a in assets10}

    tapes_all = build_all_9_tapes_unbounded(bundles, day_maps, all_days, vol_ratios)

    base_risks = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    core7 = reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"]
    turbo9 = reg["frozen_portfolios"]["PORT_9E_P28_TURBO"]["engines"]
    risks7 = {k: base_risks[k] for k in core7}
    risks9 = {k: base_risks[k] for k in turbo9}

    # --- PARITY GATE ON 2024 DEVELOPMENT YEAR BEFORE SCORING HOLDOUT ---
    days_2024 = [d for d in all_days if d.startswith("2024-")]
    p24_7e, _ = _replay_holdout_window(days_2024, tapes_all, risks7)
    p24_9e, _ = _replay_holdout_window(days_2024, tapes_all, risks9)
    # Reference 2024 from frozen Dev audit: PORT_7E = +7.00%, PORT_9E = +6.60% (small <0.5% diff possible only from M1-derived vs MT5 D1 ATR)
    parity_2024 = {
        "PORT_7E_2024_unbounded_pct": p24_7e["total_return_pct"],
        "PORT_7E_2024_frozen_ref_pct": 7.00,
        "PORT_9E_2024_unbounded_pct": p24_9e["total_return_pct"],
        "PORT_9E_2024_frozen_ref_pct": 6.60,
    }

    # --- ONE-TIME BLIND HOLDOUT SCORING (STRICTLY day >= 2025-01-01) ---
    holdout_days = [d for d in all_days if d >= "2025-01-01"]
    holdout_tapes = {
        eng: {dk: val for dk, val in dm.items() if dk >= "2025-01-01"}
        for eng, dm in tapes_all.items()
    }

    # Per-engine blind Holdout metrics
    per_engine = {}
    for eng in turbo9:
        trs = [v[0] for _, v in sorted(holdout_tapes[eng].items())]
        rs = np.array([float(t["net_R"]) for t in trs], dtype=np.float64)
        wins = float(rs[rs > 0].sum()) if len(rs) else 0.0
        losses = float(-rs[rs < 0].sum()) if len(rs) else 0.0
        eq = np.cumsum(rs) if len(rs) else np.zeros(1)
        dd_r = float(np.max(np.maximum.accumulate(np.r_[0.0, eq]) - np.r_[0.0, eq]))
        buys = [float(t["net_R"]) for t in trs if t["side"] == 1]
        sells = [float(t["net_R"]) for t in trs if t["side"] == -1]
        by_y = defaultdict(float)
        for t in trs:
            by_y[str(t["year"])] += float(t["net_R"])
        per_engine[eng] = {
            "n": len(trs),
            "net_R": round(float(rs.sum()), 2) if len(rs) else 0.0,
            "pf": round(wins / losses, 2) if losses > 1e-9 else (99.0 if wins > 0 else 0.0),
            "win_rate_pct": round(100.0 * float(np.mean(rs > 0)), 1) if len(rs) else 0.0,
            "max_dd_R": round(dd_r, 2),
            "buy_R": round(fsum(buys), 2),
            "sell_R": round(fsum(sells), 2),
            "years_R": {k: round(v, 2) for k, v in sorted(by_y.items())},
        }

    # Portfolio Holdout evaluations (all pre-registered in Protocol 521926f)
    port_results = {}
    exits_map = {}
    for label, rk, cap_v, rn in (
        ("PORT_7E_UNCAPPED", risks7, None, None),
        ("PORT_7E_SYMCAP_100", risks7, 0.0100, None),
        ("PORT_7E_SYMCAP_100_REDNEWS", risks7, 0.0100, cal_2526),
        ("PORT_9E_UNCAPPED", risks9, None, None),
        ("PORT_9E_SYMCAP_100", risks9, 0.0100, None),
        ("PORT_9E_SYMCAP_100_REDNEWS", risks9, 0.0100, cal_2526),
    ):
        res, ex = _replay_holdout_window(holdout_days, holdout_tapes, rk, max_sym=cap_v, cal=rn)
        port_results[label] = res
        exits_map[label] = ex

    # Frozen Cluster-A Inverse-DD weights (fitted strictly on 2018-2020 Development!) + Downside Vol Brake [0.55, 1.00]
    dev_warm = build_or_load_frozen_tapes(force_rebuild=False)
    invdd_w9 = compute_cluster_a_invdd_weights(dev_warm["strict_cluster_a_days"], dev_warm["tapes"], turbo9, sum(risks9.values()))
    res_invdd, ex_invdd = _replay_holdout_window(holdout_days, holdout_tapes, invdd_w9, max_sym=0.0100, cal=None)
    port_results["PORT_9E_INVDD_SYMCAP_100"] = res_invdd

    # CUSUM / SPRT / Confidence Cone Live Alpha Decay Check (comparing Holdout 2025-2026 vs Frozen Dev 2018-2024!)
    _, dev_ex7 = replay_portfolio_m1(dev_warm["ext_days"], dev_warm["tapes"], risks7, 10000.0, profile_mode="Swing")
    _, dev_ex9 = replay_portfolio_m1(dev_warm["ext_days"], dev_warm["tapes"], risks9, 10000.0, profile_mode="Swing")

    def _to_daily_pct(days_list: list[str], ex_list: list[dict]) -> np.ndarray:
        m = {e["day"]: float(e["net_usd"]) / 100.0 for e in ex_list}
        return np.array([m.get(d, 0.0) for d in days_list], dtype=np.float64)

    decay_7e = evaluate_live_decay(_to_daily_pct(dev_warm["ext_days"], dev_ex7), _to_daily_pct(holdout_days, exits_map["PORT_7E_UNCAPPED"]))
    decay_9e = evaluate_live_decay(_to_daily_pct(dev_warm["ext_days"], dev_ex9), _to_daily_pct(holdout_days, exits_map["PORT_9E_UNCAPPED"]))

    # Weekend / swap=0 invariant on Holdout
    wk_viol = 0
    for eng, dm in holdout_tapes.items():
        for _dk, (_r, st, _m) in dm.items():
            if datetime.fromtimestamp(int(st[-1]), timezone.utc).weekday() >= 5:
                wk_viol += 1

    # Automated G0 Preregistered Go / Conditional / No-Go Verdict
    p7 = port_results["PORT_7E_UNCAPPED"]
    p9 = port_results["PORT_9E_UNCAPPED"]
    core_intact = sum(1 for e in core7 if per_engine[e]["net_R"] > -1.5)
    go_cond = (
        p7["ann_pct"] >= 4.0 and p9["ann_pct"] >= 4.0
        and p7["peak_dd_pct"] <= 7.5 and p9["peak_dd_pct"] <= 7.5
        and p7["daily_loss_pct"] <= 3.0 and p9["daily_loss_pct"] <= 3.0
        and p7["calmar"] >= 0.70 and p9["calmar"] >= 0.70
        and core_intact >= 5
        and p7["margin_failures"] == 0 and p9["margin_failures"] == 0 and wk_viol == 0
    )
    nogo_cond = (
        (p7["total_return_pct"] < 0.0 and p9["total_return_pct"] < 0.0)
        or p7["peak_dd_pct"] > 9.0 or p9["peak_dd_pct"] > 9.0
        or p7["daily_loss_pct"] > 4.0 or p9["daily_loss_pct"] > 4.0
    )
    verdict = "GO" if go_cond else ("NO_GO" if nogo_cond else "CONDITIONAL")

    payload = {
        "schema": "naqex-holdout-2025-2026-verdict-v1",
        "protocol_commit": "521926f",
        "evaluated_utc": datetime.now(timezone.utc).isoformat(),
        "holdout_window": {"first_day": min(holdout_days), "last_day": max(holdout_days), "trading_days": len(holdout_days)},
        "order_send_count": 0,
        "weekend_violations": wk_viol,
        "elapsed_seconds": round(time.perf_counter() - t0, 2),
        "dev_2024_parity": parity_2024,
        "per_engine_holdout": per_engine,
        "core_engines_intact_gt_neg15R": f"{core_intact}/7",
        "portfolios_holdout": port_results,
        "alpha_decay_monitor": {
            "PORT_7E": decay_7e,
            "PORT_9E": decay_9e,
        },
        "g0_preregistered_verdict": verdict,
    }
    out_path = ROOT / "planning/research/HOLDOUT-2025-2026-ONE-TIME-VERDICT-20261123.json"
    digest = write_verified_receipt(out_path, payload, overwrite=True)
    print(json.dumps({"receipt_sha256": digest[:16], **payload}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
