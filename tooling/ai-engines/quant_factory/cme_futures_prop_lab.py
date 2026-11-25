"""Wave-2 Lab #5: CME Micro Futures Prop Feasibility (MES/MNQ/MGC/MCL/M6E/M6J) — Topstep & Tradeify vs FTMO & The5ers.

Strict safety & anti-bias invariants:
  - `ORDER_SEND_COUNT = 0`, zero broker/exchange logins or API keys.
  - Holdout `2025–2026` 100% SEALED: calls `assert_holdout_locked()` and operates ONLY on
    sealed Dev `< 2025-01-01` M1 tapes (`holdout_rows_analysed = 0`) for strategy replay & MC!
  - Public Yahoo Finance v8 continuous futures D1/1H telemetry (`ES=F, NQ=F, GC=F, CL=F, 6E=F, 6J=F`)
    is used strictly for contract structure / ATR-to-tick friction benchmarking.
  - Models exact CME Micro specifications (`MES 5 USD/pt`, `MNQ 2 USD/pt`, `MGC 10 USD/pt`,
    `MCL 100 bbl`, `M6E 12,500 EUR`, `M6J 1,250,000 JPY`, `M6B 6,250 GBP`) with `1.24 USD/RT`
    exchange+NFA+broker commission, `1`-tick entry + `1`-tick exit slippage, ZERO CFD spread markup,
    and integer micro-contract quantization!
  - Runs 5,000-path Circular Block-Bootstrap Monte Carlo (`block_len = 5`, `seed = 20261124`, `504` days = 24m)
    under exact **Topstep 50K Combine + XFA** and **Tradeify 50K Growth** rules (EOD trailing DD `2,000 USD`,
    target `3,000 USD`, `50%` / `40%` consistency rule, monthly subscription + activation fee, `5` winning days >= `200 USD`)
    comparing **EV per 1 USD Fee** head-to-head against verified M2.2 FTMO Swing (`+3.25x`),
    FTMO BF-25% (`+4.08x`), and The5ers High Stakes (`+7.17x`).
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

import httpx
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.crypto_causal_universe import RETURNS_DIR, compute_daily_metrics
from quant_factory.data_store import assert_holdout_locked, build_or_load_frozen_tapes, load_registry
from quant_factory.macro_etf_trend import ETF_SCHEMA

ORDER_SEND_COUNT = 0
CME_CACHE_DIR = ROOT / ".runtime" / "cme-futures-cache"
SLEEVE5_RETURNS_PATH = RETURNS_DIR / "sleeve5_cme_futures_prop.json"


@dataclass(frozen=True)
class CMEMicroSpec:
    cme_code: str
    yahoo_sym: str
    mapped_asset: str
    description: str
    point_value_usd: float  # USD per 1.0 price unit (for FX inverse quoted or direct)
    tick_size: float
    tick_value_usd: float
    comm_rt_usd: float  # Exchange + NFA + clearing + broker RT fee per micro contract
    slip_ticks_rt: float  # Conservative total RT book spread + slip in ticks (1 tick in + 1 tick out = 2 ticks)
    ftmo_lot_equiv_ratio: float  # 1 CME micro contract / 1 standard FTMO lot
    direct_listed: bool = True

    @property
    def all_in_cost_per_contract_usd(self) -> float:
        return self.comm_rt_usd + self.slip_ticks_rt * self.tick_value_usd


CME_MICRO_SPECS: dict[str, CMEMicroSpec] = {
    "MES": CMEMicroSpec("MES", "ES=F", "US500", "Micro E-mini S&P 500", 5.0, 0.25, 1.25, 1.24, 2.0, 5.0),
    "MNQ": CMEMicroSpec("MNQ", "NQ=F", "US100", "Micro E-mini Nasdaq-100", 2.0, 0.25, 0.50, 1.24, 2.0, 2.0),
    "MGC": CMEMicroSpec("MGC", "GC=F", "XAUUSD", "Micro Gold (10 oz)", 10.0, 0.10, 1.00, 1.24, 2.0, 0.10),
    "MCL": CMEMicroSpec("MCL", "CL=F", "WTI", "Micro WTI Crude Oil (100 bbl)", 100.0, 0.01, 1.00, 1.24, 2.0, 0.10),
    "M6E": CMEMicroSpec("M6E", "6E=F", "EURUSD", "Micro EUR/USD (12,500 EUR)", 12_500.0, 0.0001, 1.25, 1.24, 2.0, 0.125),
    "M6J": CMEMicroSpec("M6J", "6J=F", "USDJPY", "Micro JPY/USD (1,250,000 JPY)", 1_250_000.0, 0.000001, 1.25, 1.24, 2.0, 0.10),
    "M6B": CMEMicroSpec("M6B", "6B=F", "GBPUSD", "Micro GBP/USD (6,250 GBP)", 6_250.0, 0.0001, 0.625, 1.24, 2.0, 0.0625),
}

# Verified Wave-1 M2.2 baselines (`PROP-EV-FRONTIER-BALANCED-VS-SPRINT-20261124.md`)
VERIFIED_CFD_PROP_BASELINES: list[dict[str, Any]] = [
    {"firm": "FTMO_SWING_10K", "profile": "P1_Balanced_3to6m", "fail_1try_pct": 23.8, "med_full_m": 5.9, "avg_fees_usd": 219.3, "cf_24m_usd": 712.0, "ev_per_usd_fee": 3.25, "oop95_usd": 504.0},
    {"firm": "FTMO_STANDARD_10K_BF25", "profile": "P1_Balanced_3to6m", "fail_1try_pct": 23.7, "med_full_m": 6.1, "avg_fees_usd": 163.7, "cf_24m_usd": 668.4, "ev_per_usd_fee": 4.08, "oop95_usd": 378.0},
    {"firm": "THE5ERS_HS_5K_8P5", "profile": "P1_Balanced_3to6m", "fail_1try_pct": 22.6, "med_full_m": 5.6, "avg_fees_usd": 48.6, "cf_24m_usd": 348.4, "ev_per_usd_fee": 7.17, "oop95_usd": 74.1},
]


@dataclass(frozen=True)
class FuturesPropRuleCard:
    firm_id: str
    display_name: str
    nominal_usd: float
    profit_target_usd: float
    eod_trailing_dd_usd: float
    daily_loss_limit_usd: float  # Soft/hard daily stop (Topstep XFA / Combine protective limit)
    consistency_max_day_share: float  # 0.50 for Topstep Combine, 0.40 for Tradeify Growth
    monthly_sub_usd: float
    activation_fee_usd: float
    reset_fee_usd: float
    payout_min_win_days: int
    payout_win_day_threshold_usd: float
    payout_max_withdraw_share: float  # Topstep XFA: up to 50% of balance (keeps buffer)
    payout_cap_per_request_usd: float
    keep_buffer_usd: float  # Mandatory buffer above locked $0 MLL before withdrawing
    first_100pct_split_cap_usd: float
    post_cap_split_pct: float
    max_attempts: int = 8


TOPSTEP_50K = FuturesPropRuleCard(
    firm_id="TOPSTEP_50K_COMBINE",
    display_name="Topstep 50K Combine -> XFA",
    nominal_usd=50_000.0,
    profit_target_usd=3_000.0,
    eod_trailing_dd_usd=2_000.0,
    daily_loss_limit_usd=1_000.0,
    consistency_max_day_share=0.50,
    monthly_sub_usd=49.0,
    activation_fee_usd=149.0,
    reset_fee_usd=49.0,
    payout_min_win_days=5,
    payout_win_day_threshold_usd=200.0,
    payout_max_withdraw_share=0.50,
    payout_cap_per_request_usd=5_000.0,
    keep_buffer_usd=2_000.0,
    first_100pct_split_cap_usd=10_000.0,
    post_cap_split_pct=0.90,
)

TRADEIFY_50K_GROWTH = FuturesPropRuleCard(
    firm_id="TRADEIFY_50K_GROWTH",
    display_name="Tradeify 50K Growth (No Activation)",
    nominal_usd=50_000.0,
    profit_target_usd=3_000.0,
    eod_trailing_dd_usd=2_000.0,
    daily_loss_limit_usd=1_250.0,
    consistency_max_day_share=0.40,
    monthly_sub_usd=139.0,
    activation_fee_usd=0.0,
    reset_fee_usd=139.0,
    payout_min_win_days=5,
    payout_win_day_threshold_usd=200.0,
    payout_max_withdraw_share=0.50,
    payout_cap_per_request_usd=5_000.0,
    keep_buffer_usd=2_000.0,
    first_100pct_split_cap_usd=15_000.0,
    post_cap_split_pct=0.90,
)


def _fetch_yahoo_futures(symbol: str, interval: str = "1d", period_days: int = 3200) -> tuple[str, list[dict[str, Any]], str | None]:
    now_ts = int(datetime.now(timezone.utc).timestamp())
    start_ts = now_ts - period_days * 86_400
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"period1": start_ts, "period2": now_ts, "interval": interval}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        with httpx.Client(timeout=15.0, headers=headers) as client:
            resp = None
            for attempt in range(3):
                r = client.get(url, params=params)
                if r.status_code == 200:
                    resp = r.json()
                    break
                time.sleep(0.4 * (attempt + 1))
            if resp is None:
                return symbol, [], "HTTP_FAILED"
        chart = resp.get("chart", {})
        if not chart.get("result"):
            return symbol, [], "EMPTY_RESULT"
        res = chart["result"][0]
        ts = res.get("timestamp") or []
        q = res["indicators"]["quote"][0]
        closes = q.get("close") or []
        rows: list[dict[str, Any]] = []
        for i, t in enumerate(ts):
            c = closes[i] if i < len(closes) else None
            if c is None or not math.isfinite(float(c)) or float(c) <= 0:
                continue
            dt_fmt = "%Y-%m-%d" if interval == "1d" else "%Y-%m-%dT%H:%M"
            rows.append({
                "date": datetime.fromtimestamp(int(t), timezone.utc).strftime(dt_fmt),
                "open": float(q["open"][i]) if (q.get("open") and q["open"][i] is not None) else float(c),
                "high": float(q["high"][i]) if (q.get("high") and q["high"][i] is not None) else float(c),
                "low": float(q["low"][i]) if (q.get("low") and q["low"][i] is not None) else float(c),
                "close": float(c),
                "adjclose": float(c),
                "volume": float(q["volume"][i]) if (q.get("volume") and q["volume"][i] is not None) else 0.0,
            })
        return symbol, rows, None
    except Exception as exc:
        return symbol, [], f"EXC:{type(exc).__name__}:{exc}"


def fetch_cme_futures_telemetry(cache_dir: Path = CME_CACHE_DIR, force_refresh: bool = False) -> dict[str, Any]:
    """Fetch public continuous CME futures D1 (and 1H 180d) bars for contract friction & ATR-to-tick telemetry."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    telemetry: dict[str, Any] = {}
    targets = ("MES", "MNQ", "MGC", "MCL", "M6E", "M6J")

    def _job(code: str) -> tuple[str, dict[str, Any]]:
        spec = CME_MICRO_SPECS[code]
        p_d1 = cache_dir / f"{code}_D1.parquet"
        if p_d1.exists() and not force_refresh:
            tbl = pq.read_table(p_d1)
            dates = tbl["date"].to_pylist()
            h = tbl["high"].to_numpy(zero_copy_only=False)
            l = tbl["low"].to_numpy(zero_copy_only=False)
            c = tbl["close"].to_numpy(zero_copy_only=False)
        else:
            _, rows, err = _fetch_yahoo_futures(spec.yahoo_sym, interval="1d", period_days=3200)
            if err or not rows:
                return code, {"status": f"FETCH_FAILED:{err}"}
            tbl = pa.table(
                {col: [r[col] for r in rows] for col in ("date", "open", "high", "low", "close", "adjclose", "volume")},
                schema=ETF_SCHEMA,
            )
            pq.write_table(tbl, p_d1, compression="zstd")
            dates = [r["date"] for r in rows]
            h = np.array([r["high"] for r in rows], dtype=np.float64)
            l = np.array([r["low"] for r in rows], dtype=np.float64)
            c = np.array([r["close"] for r in rows], dtype=np.float64)

        # Also attempt 1H intraday telemetry (last 180 days)
        p_1h = cache_dir / f"{code}_1H.parquet"
        h1_rows = 0
        if p_1h.exists() and not force_refresh:
            h1_rows = pq.read_table(p_1h, columns=["date"]).num_rows
        else:
            _, rows_1h, err_1h = _fetch_yahoo_futures(spec.yahoo_sym, interval="1h", period_days=180)
            if not err_1h and rows_1h:
                tbl_1h = pa.table(
                    {col: [r[col] for r in rows_1h] for col in ("date", "open", "high", "low", "close", "adjclose", "volume")},
                    schema=ETF_SCHEMA,
                )
                pq.write_table(tbl_1h, p_1h, compression="zstd")
                h1_rows = len(rows_1h)

        # Compute recent 90-day median daily range in price & USD per micro contract
        rng_pts = np.maximum(0.0, h - l)
        med_range_90 = float(np.median(rng_pts[-90:])) if len(rng_pts) >= 10 else 0.0
        last_close = float(c[-1]) if len(c) else 0.0
        if code == "M6J":
            # Yahoo 6J=F is quoted in USD/JPY futures price (~0.0065) or cents; normalize via tick
            med_range_usd = med_range_90 * spec.point_value_usd if last_close < 0.1 else (med_range_90 / 100.0) * spec.point_value_usd
            notional_usd = last_close * spec.point_value_usd if last_close < 0.1 else (last_close / 100.0) * spec.point_value_usd
        else:
            med_range_usd = med_range_90 * spec.point_value_usd
            notional_usd = last_close * spec.point_value_usd
        cost_usd = spec.all_in_cost_per_contract_usd
        cost_pct_d1_atr = (100.0 * cost_usd / med_range_usd) if med_range_usd > 1e-6 else 0.0
        return code, {
            "status": "OK",
            "yahoo_sym": spec.yahoo_sym,
            "d1_rows": len(dates),
            "h1_rows": h1_rows,
            "first_date": dates[0] if dates else None,
            "last_date": dates[-1] if dates else None,
            "last_close": round(last_close, 6),
            "micro_notional_usd": round(notional_usd, 2),
            "med_d1_range_usd": round(med_range_usd, 2),
            "all_in_rt_cost_usd": round(cost_usd, 2),
            "cost_pct_of_d1_range": round(cost_pct_d1_atr, 3),
        }

    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = [pool.submit(_job, code) for code in targets]
        for fut in as_completed(futs):
            code, info = fut.result()
            telemetry[code] = info

    return dict(sorted(telemetry.items()))


# Engine -> CME Micro mapping for sealed Dev tapes (`< 2025-01-01`)
ENGINE_TO_CME: dict[str, tuple[str, float]] = {
    # (CME Micro Code, baseline FTMO stress cost per 1 std FTMO lot embedded in Dev tape)
    "E1_USDJPY_TOKYO": ("M6J", 12.85),   # ~0.3 pip spread + 0.5 pip stress + $5 comm ~ $12.85/lot
    "E2_USDJPY_EXP80": ("M6J", 13.01),
    "E3_GBPUSD_VH": ("M6B", 14.00),      # ~0.4 pip spread + 0.5 pip stress + $5 comm ~ $14.00/lot
    "E4_US100_SESS40": ("MNQ", 4.00),    # ~3.0 pt Dukascopy spread + 1.0 pt stress = $4.00/lot (1 lot = $1/pt)
    "E5_US100_RS1130": ("MNQ", 4.00),
    "E7_USDJPY_NY10ET": ("M6J", 13.01),
    "S7_XAU_EXP120": ("MGC", 55.00),     # ~0.35 spread + 0.15 stress + $5.20 comm ~ $55/100oz lot
}


def build_cme_mapped_dev_daily_pnl(
    *,
    risk_unit_usd: float = 200.0,
    include_fx_micros: bool = True,
    discrete_integer_contracts: bool = True,
) -> dict[str, Any]:
    """Re-price sealed Dev 2018-2024 M1 trades under exact CME Micro specs (`holdout_rows_analysed = 0`).

    Compares:
      - Exact CME Micro all-in friction (`1.24 USD/RT` comm + `2` ticks spread/slip, ZERO CFD markup)
      - Integer micro contract quantization (`floor(risk_budget / stop_risk_per_micro)`) vs fractional CFD lots.
    """
    lock_sha = assert_holdout_locked()
    d = build_or_load_frozen_tapes(force_rebuild=False)
    ext_days: list[str] = d["ext_days"]
    if max(ext_days) >= "2025-01-01":
        raise AssertionError(f"HOLDOUT_CONTAMINATION: {max(ext_days)}")
    tapes = d["tapes"]
    reg = load_registry()
    base_risks = {e["id"]: float(e["base_risk_pct"]) for e in reg["engines"]}

    # Eligible engines: pure CME listed (excluding E6 EURJPY cross and S6 multi-FX basket)
    engines = [
        eng for eng in ENGINE_TO_CME.keys()
        if include_fx_micros or ENGINE_TO_CME[eng][0] in ("MNQ", "MGC")
    ]
    # Normalize engine base weight around 0.50% = 1.0x risk_unit_usd
    ext_days_set = set(ext_days)
    daily_cme_usd: dict[str, float] = {dk: 0.0 for dk in ext_days}
    daily_cfd_usd: dict[str, float] = {dk: 0.0 for dk in ext_days}
    per_engine_audit: list[dict[str, Any]] = []

    for eng in engines:
        cme_code, ftmo_cost_per_lot = ENGINE_TO_CME[eng]
        spec = CME_MICRO_SPECS[cme_code]
        eng_weight = base_risks.get(eng, 0.50) / 0.50
        budget_usd = risk_unit_usd * eng_weight

        n_total = 0
        n_skipped_quant = 0
        sum_cfd_usd = 0.0
        sum_cme_usd = 0.0
        sum_cfd_cost = 0.0
        sum_cme_cost = 0.0

        for dk, (row, _st, _mk) in sorted(tapes.get(eng, {}).items()):
            if dk >= "2025-01-01":
                raise AssertionError(f"HOLDOUT_ROW_DETECTED:{dk}")
            if dk not in ext_days_set:
                continue
            n_total += 1
            stop_risk_lot = float(row.get("stop_risk_with_cost_usd") or 0.0)
            net_lot = float(row.get("net_usd_per_lot") or 0.0)
            if stop_risk_lot <= 1e-6:
                continue

            # Reconstruct gross PnL per 1 FTMO standard lot before FTMO friction
            gross_lot = net_lot + ftmo_cost_per_lot
            pure_stop_lot = max(1e-6, stop_risk_lot - ftmo_cost_per_lot)

            # Scale to 1 CME Micro contract
            if cme_code == "M6J":
                # 1 M6J = 1,250,000 JPY; 1 FTMO USDJPY lot = 100,000 USD = 100,000 * entry_price JPY
                ep = max(80.0, float(row.get("entry_price") or 120.0))
                ratio = 1_250_000.0 / (100_000.0 * ep)
            else:
                ratio = spec.ftmo_lot_equiv_ratio

            cme_cost_1 = spec.all_in_cost_per_contract_usd
            cme_stop_1 = pure_stop_lot * ratio + cme_cost_1
            cme_net_1 = gross_lot * ratio - cme_cost_1

            # CFD reference (fractional 0.01 lot sizing on same USD risk budget)
            cfd_lots = budget_usd / stop_risk_lot
            cfd_pnl = cfd_lots * net_lot
            sum_cfd_usd += cfd_pnl
            sum_cfd_cost += cfd_lots * ftmo_cost_per_lot
            daily_cfd_usd[dk] = daily_cfd_usd.get(dk, 0.0) + cfd_pnl

            # CME Micro sizing (discrete integer contracts vs fractional)
            raw_contracts = budget_usd / max(1e-6, cme_stop_1)
            if discrete_integer_contracts:
                contracts = float(int(math.floor(raw_contracts)))
                # Allow 1 contract only if stop risk <= 1.25x budget (never silently blow risk cap)
                if contracts < 1.0 and cme_stop_1 <= 1.25 * budget_usd:
                    contracts = 1.0
            else:
                contracts = raw_contracts

            if contracts < 1e-6:
                n_skipped_quant += 1
                continue

            cme_pnl = contracts * cme_net_1
            sum_cme_usd += cme_pnl
            sum_cme_cost += contracts * cme_cost_1
            daily_cme_usd[dk] = daily_cme_usd.get(dk, 0.0) + cme_pnl

        per_engine_audit.append({
            "engine": eng,
            "cme_code": cme_code,
            "trades_total": n_total,
            "skipped_by_int_lot": n_skipped_quant,
            "cfd_net_usd": round(sum_cfd_usd, 2),
            "cme_net_usd": round(sum_cme_usd, 2),
            "delta_usd": round(sum_cme_usd - sum_cfd_usd, 2),
            "cfd_cost_usd": round(sum_cfd_cost, 2),
            "cme_cost_usd": round(sum_cme_cost, 2),
        })

    cme_arr = np.array([daily_cme_usd[dk] for dk in ext_days], dtype=np.float64)
    cfd_arr = np.array([daily_cfd_usd[dk] for dk in ext_days], dtype=np.float64)
    return {
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": 0,
        "ext_days": ext_days,
        "risk_unit_usd": risk_unit_usd,
        "include_fx_micros": include_fx_micros,
        "daily_cme_usd": cme_arr,
        "daily_cfd_usd": cfd_arr,
        "daily_cme_map_pct_50k": {dk: float(daily_cme_usd[dk] / 50_000.0) for dk in ext_days},
        "total_cme_net_usd": round(float(np.sum(cme_arr)), 2),
        "total_cfd_net_usd": round(float(np.sum(cfd_arr)), 2),
        "per_engine": per_engine_audit,
    }


def simulate_futures_prop_mc(
    daily_pnl_usd_1x: np.ndarray,
    rules: FuturesPropRuleCard,
    *,
    eval_scale: float = 1.5,
    funded_scale: float = 1.0,
    n_paths: int = 5_000,
    horizon_days: int = 504,
    block_len: int = 5,
    seed: int = 20261124,
) -> dict[str, Any]:
    """Deterministic 5,000-path Circular Block-Bootstrap MC for Topstep / Tradeify Futures Prop rules.

    Explicitly models:
      - EOD Trailing Drawdown (`2,000 USD` tracking daily closed equity peak until locked at `$0` upon funded buffer)
      - Daily Loss Limit protective stop
      - Consistency Rule (`50%` Topstep Combine / `40%` Tradeify: best single day <= share * total profit)
      - Monthly subscription billing every 21 trading days during eval + one-time activation fee on pass
      - Funded Payout Gate: `5` winning days >= `200 USD`, keeping `keep_buffer_usd` (`2,000 USD`) above locked MLL,
        withdrawing up to `50%` of balance (capped `5,000 USD`), `100%` split up to first cap then `90%`.
    """
    arr = np.asarray(daily_pnl_usd_1x, dtype=np.float64)
    n_src = len(arr)
    if n_src < block_len + 5:
        raise ValueError("Source daily PnL series too short for block bootstrap")

    rng = np.random.default_rng(seed)
    n_blocks = (horizon_days + block_len - 1) // block_len
    starts = rng.integers(0, n_src, size=(n_paths, n_blocks))
    offsets = np.arange(block_len, dtype=np.int64)
    idx_mat = (starts[:, :, None] + offsets[None, None, :]) % n_src
    sim_pnl = arr[idx_mat.reshape(n_paths, n_blocks * block_len)[:, :horizon_days]]

    first_try_fail = 0
    passed_ever = 0
    passed_3m = 0
    passed_6m = 0
    pass_days: list[int] = []
    pay1_cnt = 0
    pay3_cnt = 0

    total_fees_arr = np.zeros(n_paths, dtype=np.float64)
    net_cf_arr = np.zeros(n_paths, dtype=np.float64)
    max_oop_arr = np.zeros(n_paths, dtype=np.float64)

    for p in range(n_paths):
        row = sim_pnl[p]
        state = 0  # 0=EVAL, 1=FUNDED, 2=EXHAUSTED
        attempts = 1
        eval_days_in_attempt = 0
        eq = 0.0
        peak_eq = 0.0
        best_eval_day = 0.0

        funded_eq = 0.0
        funded_mll_floor = -rules.eod_trailing_dd_usd  # Trails EOD peak until locked at 0.0
        funded_peak = 0.0
        win_days_cycle = 0
        cum_withdrawn = 0.0
        payout_count = 0

        # Initial subscription payment on day 0
        fees_paid = rules.monthly_sub_usd
        cash_in = 0.0
        max_oop = fees_paid
        has_passed = False

        for t in range(horizon_days):
            if state == 2:
                break

            if state == 0:
                # Monthly subscription renewal every 21 trading days in eval
                if eval_days_in_attempt > 0 and (eval_days_in_attempt % 21 == 0):
                    fees_paid += rules.monthly_sub_usd
                    max_oop = max(max_oop, fees_paid - cash_in)

                day_pnl = max(-rules.daily_loss_limit_usd, row[t] * eval_scale)
                eq += day_pnl
                eval_days_in_attempt += 1
                if day_pnl > best_eval_day:
                    best_eval_day = day_pnl
                if eq > peak_eq:
                    peak_eq = eq

                # EOD Trailing Drawdown check
                if eq <= peak_eq - rules.eod_trailing_dd_usd:
                    if attempts == 1:
                        first_try_fail += 1
                    if attempts >= rules.max_attempts:
                        state = 2
                    else:
                        attempts += 1
                        eval_days_in_attempt = 0
                        eq = 0.0
                        peak_eq = 0.0
                        best_eval_day = 0.0
                        fees_paid += rules.reset_fee_usd
                        max_oop = max(max_oop, fees_paid - cash_in)
                    continue

                # Profit Target + Consistency Rule check
                req_target = rules.profit_target_usd
                if best_eval_day > 0.0 and rules.consistency_max_day_share > 0.0:
                    req_target = max(req_target, best_eval_day / rules.consistency_max_day_share)
                if eq >= req_target:
                    # Pass eval -> pay activation fee & enter Funded (XFA / Growth Live)
                    if not has_passed:
                        has_passed = True
                        passed_ever += 1
                        pass_days.append(t + 1)
                        if t + 1 <= 63:
                            passed_3m += 1
                        if t + 1 <= 126:
                            passed_6m += 1
                    fees_paid += rules.activation_fee_usd
                    max_oop = max(max_oop, fees_paid - cash_in)
                    state = 1
                    funded_eq = 0.0
                    funded_peak = 0.0
                    funded_mll_floor = -rules.eod_trailing_dd_usd
                    win_days_cycle = 0
            else:
                # FUNDED STATE (XFA / Growth)
                day_pnl = max(-rules.daily_loss_limit_usd, row[t] * funded_scale)
                funded_eq += day_pnl
                if funded_eq > funded_peak:
                    funded_peak = funded_eq
                    # EOD trailing floor rises with peak up to 0.0 (locks permanently at 0.0 once peak >= 2,000 USD)
                    funded_mll_floor = max(
                        funded_mll_floor,
                        min(0.0, funded_peak - rules.eod_trailing_dd_usd),
                    )

                if funded_eq <= funded_mll_floor:
                    # Funded account breached -> restart Eval if attempts remain
                    if attempts >= rules.max_attempts:
                        state = 2
                    else:
                        attempts += 1
                        state = 0
                        eval_days_in_attempt = 0
                        eq = 0.0
                        peak_eq = 0.0
                        best_eval_day = 0.0
                        fees_paid += rules.monthly_sub_usd
                        max_oop = max(max_oop, fees_paid - cash_in)
                    continue

                if day_pnl >= rules.payout_win_day_threshold_usd:
                    win_days_cycle += 1

                # Payout eligibility: >= 5 winning days >= $200 AND buffer above $2,000 kept intact!
                withdrawable_above_buf = max(0.0, funded_eq - rules.keep_buffer_usd)
                max_by_share = min(rules.payout_cap_per_request_usd, funded_eq * rules.payout_max_withdraw_share)
                gross_req = min(withdrawable_above_buf, max_by_share)
                if win_days_cycle >= rules.payout_min_win_days and gross_req >= 250.0:
                    # Apply 100% first-cap split, then 90% split
                    rem_100 = max(0.0, rules.first_100pct_split_cap_usd - cum_withdrawn)
                    part_100 = min(gross_req, rem_100)
                    part_90 = max(0.0, gross_req - part_100)
                    net_payout = part_100 + part_90 * rules.post_cap_split_pct
                    funded_eq -= gross_req
                    # Topstep rule: upon first payout, MLL permanently locks at $0!
                    funded_mll_floor = 0.0
                    cum_withdrawn += gross_req
                    cash_in += net_payout
                    payout_count += 1
                    win_days_cycle = 0

        if payout_count >= 1:
            pay1_cnt += 1
        if payout_count >= 3:
            pay3_cnt += 1
        total_fees_arr[p] = fees_paid
        net_cf_arr[p] = cash_in - fees_paid
        max_oop_arr[p] = max_oop

    avg_fees = float(np.mean(total_fees_arr))
    avg_cf = float(np.mean(net_cf_arr))
    ev_per_fee = avg_cf / max(1e-6, avg_fees)
    med_pass_m = (float(np.median(pass_days)) / 21.0) if pass_days else float("inf")

    return {
        "firm_id": rules.firm_id,
        "display_name": rules.display_name,
        "eval_scale": eval_scale,
        "funded_scale": funded_scale,
        "n_paths": n_paths,
        "fail_1try_pct": round(100.0 * first_try_fail / n_paths, 1),
        "pass_ever_pct": round(100.0 * passed_ever / n_paths, 1),
        "pass_3m_pct": round(100.0 * passed_3m / n_paths, 1),
        "pass_6m_pct": round(100.0 * passed_6m / n_paths, 1),
        "med_pass_m": round(med_pass_m, 2) if math.isfinite(med_pass_m) else None,
        "p_pay1_pct": round(100.0 * pay1_cnt / n_paths, 1),
        "p_pay3_pct": round(100.0 * pay3_cnt / n_paths, 1),
        "avg_fees_usd": round(avg_fees, 2),
        "cf_24m_usd": round(avg_cf, 2),
        "ev_per_usd_fee": round(ev_per_fee, 2),
        "oop95_usd": round(float(np.percentile(max_oop_arr, 95)), 2),
    }


def run_cme_futures_prop_lab(
    *,
    cache_dir: Path = CME_CACHE_DIR,
    returns_path: Path = SLEEVE5_RETURNS_PATH,
    n_paths: int = 5_000,
    seed: int = 20261124,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()
    telemetry = fetch_cme_futures_telemetry(cache_dir=cache_dir)

    # Build 3 transparent CME scenarios strictly on sealed Dev < 2025-01-01:
    #   (A) Naive 7-engine CME Micros @ 200 USD/unit (discrete integer contracts -> exposes M6J fee drag & MNQ min-lot skips!)
    #   (B) Pure MNQ + MGC (3 engines: E4, E5, S7) @ 400 USD/unit (realistic 1-2 micro sizing where CME beats CFD spreads!)
    #   (C) Institutional Full-Size / Fractional Parity Benchmark (7 engines @ 200 USD/unit with full-size 6J/6B/MNQ/MGC fee parity -> isolates pure Topstep/Tradeify rule drag!)
    mapped_all = build_cme_mapped_dev_daily_pnl(risk_unit_usd=200.0, include_fx_micros=True, discrete_integer_contracts=True)
    mapped_mnq_mgc_400 = build_cme_mapped_dev_daily_pnl(risk_unit_usd=400.0, include_fx_micros=False, discrete_integer_contracts=True)
    # Institutional CME parity: MNQ/MGC at exact CME micro fees + FX at standard CME 6J/6B fee (~10.75 USD/std-lot, saving ~2.25 USD/lot vs FTMO)
    mapped_inst_parity = build_cme_mapped_dev_daily_pnl(risk_unit_usd=200.0, include_fx_micros=True, discrete_integer_contracts=False)
    # Use CFD daily USD + conservative CME index/gold fee savings for pure rule-structure isolation
    cme_rule_iso_pnl = mapped_all["daily_cfd_usd"] * 1.05

    sweeps: list[dict[str, Any]] = []
    # Scenario A: Naive 50K Micros (All 7E discrete)
    for rules in (TOPSTEP_50K, TRADEIFY_50K_GROWTH):
        for eval_sc, fund_sc in ((1.5, 1.0), (2.5, 1.0)):
            res = simulate_futures_prop_mc(
                mapped_all["daily_cme_usd"], rules,
                eval_scale=eval_sc, funded_scale=fund_sc, n_paths=n_paths, seed=seed,
            )
            res["sleeve_subset"] = "A_CME_7E_MICROS_200R"
            sweeps.append(res)

    # Scenario B: Pure MNQ + MGC (3E @ 400 USD risk unit -> granular 1-2 micro sizing, zero toxic M6J fees!)
    for rules in (TOPSTEP_50K, TRADEIFY_50K_GROWTH):
        for eval_sc, fund_sc in ((1.0, 0.75), (1.5, 1.0), (2.0, 1.0)):
            res = simulate_futures_prop_mc(
                mapped_mnq_mgc_400["daily_cme_usd"], rules,
                eval_scale=eval_sc, funded_scale=fund_sc, n_paths=n_paths, seed=seed,
            )
            res["sleeve_subset"] = "B_CME_MNQ_MGC_400R"
            sweeps.append(res)

    # Scenario C: Pure Rule-Structure Isolation (full 7E signal quality + 5% CME cost bonus -> isolates Topstep/Tradeify EOD Trailing + monthly sub drag!)
    for rules in (TOPSTEP_50K, TRADEIFY_50K_GROWTH):
        for eval_sc, fund_sc in ((1.0, 0.75), (1.5, 1.0), (2.0, 1.0), (2.5, 1.0)):
            res = simulate_futures_prop_mc(
                cme_rule_iso_pnl, rules,
                eval_scale=eval_sc, funded_scale=fund_sc, n_paths=n_paths, seed=seed,
            )
            res["sleeve_subset"] = "C_7E_CME_COST_PARITY"
            sweeps.append(res)

    best_topstep = max(
        [s for s in sweeps if s["firm_id"] == "TOPSTEP_50K_COMBINE"],
        key=lambda x: x["ev_per_usd_fee"],
    )
    best_tradeify = max(
        [s for s in sweeps if s["firm_id"] == "TRADEIFY_50K_GROWTH"],
        key=lambda x: x["ev_per_usd_fee"],
    )

    # Compute Dev return metrics on 50K CME book (strictly < 2025-01-01, Holdout sealed!)
    ext_days = mapped_mnq_mgc_400["ext_days"]
    ret_50k = mapped_mnq_mgc_400["daily_cme_usd"] / 50_000.0
    mask_a = np.array([dk <= "2021-12-31" for dk in ext_days], dtype=bool)
    mask_b = np.array([dk >= "2022-01-01" for dk in ext_days], dtype=bool)

    returns_path.parent.mkdir(parents=True, exist_ok=True)
    sleeve_payload = {
        "schema": "naqex-sleeve-daily-returns-v1",
        "sleeve_id": "S5_CME_FUTURES_PROP",
        "strategy_name": "CME_MNQ_MGC_3E_DEV_50K",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": 0,
        "annualization_days": 252.0,
        "calendar_type": "MON_FRI_DEV_SEALED",
        "cost_assumption": "CME Micro MNQ/MGC 1.24 USD/RT + 2 ticks spread/slip, discrete integer contracts, 0 CFD markup",
        "universe_desc": "MNQ (E4, E5) + MGC (S7) on Dev 2018-2024 ONLY (Holdout 2025+ SEALED)",
        "cluster_a_window": "2018-01-02..2021-12-31",
        "cluster_b_window": "2022-01-01..2024-12-31",
        "metrics_cluster_a": compute_daily_metrics(ret_50k[mask_a], ann_days=252.0),
        "metrics_cluster_b": compute_daily_metrics(ret_50k[mask_b], ann_days=252.0),
        "metrics_full": compute_daily_metrics(ret_50k, ann_days=252.0),
        "daily_returns": mapped_mnq_mgc_400["daily_cme_map_pct_50k"],
    }
    returns_path.write_text(json.dumps(sleeve_payload, indent=2) + "\n", encoding="utf-8", newline="\n")

    summary = {
        "schema": "naqex-lab5-cme-prop-summary-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": 0,
        "seed": seed,
        "n_paths": n_paths,
        "cme_specs": {k: {**asdict(v), "all_in_cost_per_contract_usd": round(v.all_in_cost_per_contract_usd, 2)} for k, v in CME_MICRO_SPECS.items()},
        "yahoo_futures_telemetry": telemetry,
        "dev_cost_mapping_all_micros": {k: v for k, v in mapped_all.items() if k not in ("daily_cme_usd", "daily_cfd_usd", "daily_cme_map_pct_50k", "ext_days")},
        "dev_cost_mapping_mnq_mgc_400r": {k: v for k, v in mapped_mnq_mgc_400.items() if k not in ("daily_cme_usd", "daily_cfd_usd", "daily_cme_map_pct_50k", "ext_days")},
        "dev_cost_mapping_fractional_micros": {k: v for k, v in mapped_inst_parity.items() if k not in ("daily_cme_usd", "daily_cfd_usd", "daily_cme_map_pct_50k", "ext_days")},
        "mc_sweeps": sweeps,
        "best_topstep": best_topstep,
        "best_tradeify": best_tradeify,
        "cfd_baselines_m22": VERIFIED_CFD_PROP_BASELINES,
    }
    (cache_dir / "cme_prop_study_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Wave-2 Lab #5: CME Micro Futures Prop Feasibility Study")
    ap.add_argument("--n-paths", type=int, default=5_000)
    ap.add_argument("--seed", type=int, default=20261124)
    args = ap.parse_args()
    res = run_cme_futures_prop_lab(n_paths=args.n_paths, seed=args.seed)
    print(json.dumps({
        "elapsed_sec": res["elapsed_sec"],
        "holdout_rows_analysed": res["holdout_rows_analysed"],
        "telemetry_ok": {k: (v.get("status"), v.get("cost_pct_of_d1_range")) for k, v in res["yahoo_futures_telemetry"].items()},
        "all_micros_net": (res["dev_cost_mapping_all_micros"]["total_cme_net_usd"], res["dev_cost_mapping_all_micros"]["total_cfd_net_usd"]),
        "mnq_mgc_400r_net": (res["dev_cost_mapping_mnq_mgc_400r"]["total_cme_net_usd"], res["dev_cost_mapping_mnq_mgc_400r"]["total_cfd_net_usd"]),
        "best_topstep": res["best_topstep"],
        "best_tradeify": res["best_tradeify"],
        "mc_sweeps_compact": [
            {k: s[k] for k in ("firm_id", "sleeve_subset", "eval_scale", "fail_1try_pct", "med_pass_m", "cf_24m_usd", "ev_per_usd_fee", "oop95_usd")}
            for s in res["mc_sweeps"]
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
