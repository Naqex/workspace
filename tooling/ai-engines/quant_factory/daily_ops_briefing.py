"""Naqex Quant Pod — 1-Command Deterministic Daily / Overnight Operations Briefing CLI.

Stdlib-only, read-only on workspace state (`ORDER_SEND_COUNT = 0`, zero API keys, zero network calls).
Inspects all live overnight telemetry & verified Wave-2 artifacts safely (gracefully marking missing
optional runtime files as `PENDING` instead of crashing), computes an honest Operational Health Score
(0-100) with explicit PASS / WARN / PENDING / FAIL breakdown, and emits BOTH a structured JSON receipt
and a concise Vietnamese Markdown operations briefing (zero bare `$` characters).

Usage:
  python -X utf8 tooling/ai-engines/quant_factory/daily_ops_briefing.py \\
    --capital-usd 50000 --usd-vnd 25500 \\
    --out-md .runtime/live-overnight/daily_ops_briefing.md \\
    --out-json .runtime/live-overnight/daily_ops_briefing.json
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]

ORDER_SEND_COUNT = 0
EXPECTED_HOLDOUT_LOCK_SHA256 = "f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486"
DEFAULT_CAPITAL_USD = 50_000.0
DEFAULT_USD_VND = 25_500.0
M2_MAKER_HURDLE_BPS = 6.15
HEARTBEAT_STALE_SEC = 600.0


def _safe_read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_jsonl_rows(path: Path, max_tail: int = 500) -> tuple[int, list[dict[str, Any]]]:
    if not path.is_file():
        return 0, []
    try:
        lines = [ln.strip() for ln in path.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    except OSError:
        return 0, []
    total = len(lines)
    rows: list[dict[str, Any]] = []
    for ln in lines[-max_tail:]:
        try:
            obj = json.loads(ln)
            if isinstance(obj, dict):
                rows.append(obj)
        except json.JSONDecodeError:
            continue
    return total, rows


def _parse_float(tok: str) -> float | None:
    m = re.search(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?", tok or "")
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def _check_holdout_lock(root: Path) -> dict[str, Any]:
    lock_path = root / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"
    reg_path = root / "planning/research/PORTFOLIO-REGISTRY.json"
    reg = _safe_read_json(reg_path)
    reg_rows = int(((reg or {}).get("holdout_lock") or {}).get("holdout_rows_analysed", 0)) if isinstance(reg, dict) else 0

    if not lock_path.is_file():
        return {
            "id": "holdout_lock",
            "label": "Sealed Holdout 2025+ Lock",
            "status": "PENDING",
            "score": 0,
            "max_score": 25,
            "detail": "NATIVE_FTMO_HOLDOUT_LOCK.json not present in root",
            "data": {"present": False, "sha256": None, "holdout_rows_analysed": reg_rows},
        }

    digest = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    ok = digest == EXPECTED_HOLDOUT_LOCK_SHA256
    return {
        "id": "holdout_lock",
        "label": "Sealed Holdout 2025+ Lock",
        "status": "PASS" if ok else "FAIL",
        "score": 25 if ok else 0,
        "max_score": 25,
        "detail": f"SHA256={digest[:16]}... ({'EXACT_MATCH' if ok else 'BREACH_MISMATCH'}) · holdout_rows_analysed={reg_rows}",
        "data": {
            "present": True,
            "sha256": digest,
            "expected_sha256": EXPECTED_HOLDOUT_LOCK_SHA256,
            "matches": ok,
            "holdout_rows_analysed": reg_rows,
        },
    }


def _check_crypto_shadow(root: Path) -> dict[str, Any]:
    ov = root / ".runtime/live-overnight"
    latest = _safe_read_json(ov / "crypto_shadow_latest.json")
    n_rows, rows = _read_jsonl_rows(ov / "crypto_shadow_log.jsonl")
    obj = latest if isinstance(latest, dict) else (rows[-1] if rows else None)

    if not isinstance(obj, dict):
        return {
            "id": "crypto_shadow",
            "label": "Live Crypto Spot/Perp Shadow (L2 TCA)",
            "status": "PENDING",
            "score": 0,
            "max_score": 15,
            "detail": "Awaiting .runtime/live-overnight/crypto_shadow_latest.json",
            "data": {"cycles": 0},
        }

    tca = obj.get("tca_summary_top15") or {}
    s2 = obj.get("sleeve2_f4_4h_ema") or {}
    s3a = obj.get("sleeve3a_carry_btc_eth") or {}
    basis = s3a.get("perp_live_basis") or {}
    depth = obj.get("orderbook_depth_top15") or {}

    cycles = max(n_rows, int(obj.get("cycle_num") or 0))
    os_cnt = int(obj.get("order_send_count", 0))
    med_slip_10k = tca.get("median_slip_10k_bps")
    budget_10k = float(tca.get("backtest_assumed_oneway_slip_bps") or 5.0)
    within_budget = tca.get("tca_within_budget_10k")
    if within_budget is None and med_slip_10k is not None:
        within_budget = float(med_slip_10k) <= budget_10k

    btc_fund = (basis.get("BTCUSDT") or {}).get("next_funding_ann_pct")
    eth_fund = (basis.get("ETHUSDT") or {}).get("next_funding_ann_pct")
    majors = {
        sym: {
            "mid": (depth.get(sym) or {}).get("mid"),
            "spread_bps": (depth.get(sym) or {}).get("spread_bps"),
            "slip_10k_bps": (depth.get(sym) or {}).get("slip_10k_bps"),
        }
        for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT")
        if isinstance(depth.get(sym), dict)
    }

    if os_cnt != 0:
        status, score = "FAIL", 0
    elif within_budget:
        status, score = "PASS", 15
    else:
        status, score = "WARN", 8

    slip_txt = f"{float(med_slip_10k):.3f} bps" if med_slip_10k is not None else "n/a"
    fund_txt = f"BTC {btc_fund:+.2f}% / ETH {eth_fund:+.2f}%" if (btc_fund is not None and eth_fund is not None) else "n/a"
    return {
        "id": "crypto_shadow",
        "label": "Live Crypto Spot/Perp Shadow (L2 TCA)",
        "status": status,
        "score": score,
        "max_score": 15,
        "detail": (
            f"Cycles={cycles} · 10k Slip={slip_txt} (<= {budget_10k:.1f} bps: {within_budget}) "
            f"· BTC Bull={bool(s2.get('btc_regime_bull'))} · Perp Fund={fund_txt}"
        ),
        "data": {
            "cycles": cycles,
            "timestamp_utc": obj.get("timestamp_utc"),
            "order_send_count": os_cnt,
            "median_spread_bps": tca.get("median_spread_bps"),
            "median_slip_10k_bps": med_slip_10k,
            "max_slip_10k_bps": tca.get("max_slip_10k_bps"),
            "budget_10k_bps": budget_10k,
            "within_budget_10k": within_budget,
            "btc_regime_bull": s2.get("btc_regime_bull"),
            "active_positions": s2.get("active_count"),
            "btc_funding_ann_pct": btc_fund,
            "eth_funding_ann_pct": eth_fund,
            "majors_l2": majors,
        },
    }


def _check_crypto_maker_probe(root: Path) -> dict[str, Any]:
    ov = root / ".runtime/live-overnight"
    latest = _safe_read_json(ov / "crypto_maker_shadow_latest.json")
    n_rows, rows = _read_jsonl_rows(ov / "crypto_maker_shadow.jsonl")
    obj = latest if isinstance(latest, dict) else (rows[-1] if rows else None)

    if not isinstance(obj, dict):
        return {
            "id": "crypto_maker_probe",
            "label": "Live Crypto Maker Probe (M2B Fill Gate)",
            "status": "PENDING",
            "score": 0,
            "max_score": 15,
            "detail": f"Awaiting crypto_maker_shadow_latest.json (M2 hurdle <= {M2_MAKER_HURDLE_BPS:.2f} bps)",
            "data": {"cycles": 0, "hurdle_bps": M2_MAKER_HURDLE_BPS},
        }

    cycles = max(n_rows, int(obj.get("cycle_num") or 1))
    # Support top-level, nested summary/windows, AND real `passive_limit_probe_active_basket` schemas
    summ = obj.get("summary") if isinstance(obj.get("summary"), dict) else {}
    probe_ab = obj.get("passive_limit_probe_active_basket") if isinstance(obj.get("passive_limit_probe_active_basket"), dict) else {}
    windows = obj.get("windows") if isinstance(obj.get("windows"), dict) else {}
    ab15 = probe_ab.get("15m") if isinstance(probe_ab.get("15m"), dict) else (probe_ab.get("5m") if isinstance(probe_ab.get("5m"), dict) else {})
    w15 = windows.get("15m") if isinstance(windows.get("15m"), dict) else (windows.get("60m") if isinstance(windows.get("60m"), dict) else {})

    def _pick(*keys: str) -> float | None:
        for src in (obj, ab15, summ, w15):
            for k in keys:
                val = src.get(k)
                if isinstance(val, (int, float)):
                    return float(val)
        return None

    fill_pct = _pick("fill_rate_pct", "touch_through_fill_rate_pct", "fill_rate_15m_pct", "avg_fill_rate_pct")
    if fill_pct is None:
        raw_fr = _pick("fill_rate")
        if raw_fr is not None:
            fill_pct = round(raw_fr * 100.0 if raw_fr <= 1.0 else raw_fr, 2)
    adv_bps = _pick("adverse_sel_bps", "adverse_selection_bps", "mean_adv_sel_5m_bps", "adverse_selection_5m_bps", "adverse_selection_15m_bps")
    eff_bps = _pick("effective_cost_bps", "eff_cost_bps", "all_in_maker_cost_bps", "effective_maker_cost_bps")
    os_cnt = int(obj.get("order_send_count", 0))

    if os_cnt != 0:
        status, score = "FAIL", 0
    elif eff_bps is not None and eff_bps <= M2_MAKER_HURDLE_BPS:
        status, score = "PASS", 15
    else:
        status, score = "WARN", 8

    f_txt = f"{fill_pct:.1f}%" if fill_pct is not None else "n/a"
    a_txt = f"{adv_bps:.2f} bps" if adv_bps is not None else "n/a"
    e_txt = f"{eff_bps:.2f} bps" if eff_bps is not None else "n/a"
    return {
        "id": "crypto_maker_probe",
        "label": "Live Crypto Maker Probe (M2B Fill Gate)",
        "status": status,
        "score": score,
        "max_score": 15,
        "detail": f"Cycles={cycles} · Fill={f_txt} · AdvSel={a_txt} · EffCost={e_txt} vs M2 Hurdle {M2_MAKER_HURDLE_BPS:.2f} bps",
        "data": {
            "cycles": cycles,
            "timestamp_utc": obj.get("timestamp_utc") or obj.get("generated_utc"),
            "order_send_count": os_cnt,
            "fill_rate_pct": fill_pct,
            "adverse_sel_bps": adv_bps,
            "effective_cost_bps": eff_bps,
            "hurdle_bps": M2_MAKER_HURDLE_BPS,
            "beats_m2_hurdle": (eff_bps is not None and eff_bps <= M2_MAKER_HURDLE_BPS),
        },
    }


def _check_mt5_demo_live(root: Path, now_utc: datetime) -> dict[str, Any]:
    ov = root / ".runtime/live-overnight"
    mql_files = root / ".runtime/ftmo-demo-portable-1515343166/MQL5/Files"

    spread_count, spread_rows = _read_jsonl_rows(ov / "mt5_live_spread_log.jsonl")
    hb_path = mql_files / "naqex_heartbeat.json"
    if not hb_path.is_file():
        alt_hb = ov / "naqex_heartbeat.json"
        if alt_hb.is_file():
            hb_path = alt_hb
    hb = _safe_read_json(hb_path)
    audit_path = mql_files / "naqex_exec_audit.csv"

    exec_rows = 0
    avg_spread_pts: float | None = None
    if audit_path.is_file():
        try:
            with audit_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
                rdr = list(csv.DictReader(f))
            exec_rows = len(rdr)
            sp_vals = [_parse_float(r.get("spread_pts", "")) for r in rdr]
            sp_clean = [v for v in sp_vals if v is not None]
            if sp_clean:
                avg_spread_pts = round(sum(sp_clean) / len(sp_clean), 2)
        except Exception:
            exec_rows = 0

    # Secondary account metadata from realtick_matrix_summary if live demo heartbeat is not running yet
    rt = _safe_read_json(root / ".runtime/mt5-realtick-results/realtick_matrix_summary.json")
    demo_acct = (rt.get("account") if isinstance(rt, dict) else None) if isinstance(rt, dict) else None

    if not isinstance(hb, dict) and not spread_rows and not isinstance(demo_acct, dict):
        return {
            "id": "mt5_demo_live",
            "label": "FTMO-Demo 1515343166 Live Telemetry",
            "status": "PENDING",
            "score": 0,
            "max_score": 15,
            "detail": "Awaiting naqex_heartbeat.json & mt5_live_spread_log.jsonl",
            "data": {"spread_rows": 0, "exec_audit_rows": exec_rows},
        }

    latest_sp = spread_rows[-1] if spread_rows else {}
    balance = (hb or {}).get("balance", latest_sp.get("balance", (demo_acct or {}).get("balance")))
    equity = (hb or {}).get("equity", latest_sp.get("equity", (demo_acct or {}).get("equity")))
    open_pos = int((hb or {}).get("open_positions", 0)) if isinstance(hb, dict) else None
    orphan_no_sl = int((hb or {}).get("orphan_no_sl", 0)) if isinstance(hb, dict) else 0
    kill_switch = bool((hb or {}).get("kill_switch", False)) if isinstance(hb, dict) else False

    hb_age_sec: float | None = None
    if isinstance(hb, dict) and hb.get("utc_ts") is not None:
        try:
            hb_age_sec = round(max(0.0, now_utc.timestamp() - float(hb["utc_ts"])), 1)
        except (ValueError, TypeError):
            hb_age_sec = None

    if orphan_no_sl > 0 or kill_switch:
        status, score = "FAIL", 0
    elif isinstance(hb, dict) and (hb_age_sec is None or hb_age_sec <= HEARTBEAT_STALE_SEC):
        status, score = "PASS", 15
    elif spread_rows:
        status, score = "WARN", 10
    else:
        status, score = "WARN", 7

    bal_txt = f"{float(balance):,.2f} USD" if balance is not None else "n/a"
    eq_txt = f"{float(equity):,.2f} USD" if equity is not None else "n/a"
    age_txt = f"{hb_age_sec:.0f}s" if hb_age_sec is not None else "no-hb"
    return {
        "id": "mt5_demo_live",
        "label": "FTMO-Demo 1515343166 Live Telemetry",
        "status": status,
        "score": score,
        "max_score": 15,
        "detail": (
            f"Bal={bal_txt} · Eq={eq_txt} · Open={open_pos if open_pos is not None else 'n/a'} "
            f"· OrphanNoSL={orphan_no_sl} · HbAge={age_txt} · SpreadRows={spread_count} · ExecAudit={exec_rows}"
        ),
        "data": {
            "balance_usd": balance,
            "equity_usd": equity,
            "open_positions": open_pos,
            "orphan_no_sl": orphan_no_sl,
            "kill_switch": kill_switch,
            "heartbeat_age_sec": hb_age_sec,
            "heartbeat_present": isinstance(hb, dict),
            "spread_rows": spread_count,
            "exec_audit_rows": exec_rows,
            "avg_audit_spread_pts": avg_spread_pts,
        },
    }


def _check_mt5_realtick(root: Path) -> dict[str, Any]:
    rt_path = root / ".runtime/mt5-realtick-results/realtick_matrix_summary.json"
    rt = _safe_read_json(rt_path)
    if not isinstance(rt, dict):
        return {
            "id": "mt5_realtick_reconcile",
            "label": "MT5 Model=4 Real-Tick Reconciliation",
            "status": "PENDING",
            "score": 0,
            "max_score": 15,
            "detail": "Awaiting .runtime/mt5-realtick-results/realtick_matrix_summary.json",
            "data": {"engines_run": 0},
        }

    rec_map = rt.get("reconciliation") if isinstance(rt.get("reconciliation"), dict) else {}
    engines_run = int(rt.get("engines_run") or len(rec_map))
    engines_ok = 0
    swap_zero_violated = False
    swap_zero_checked = 0
    drags: list[float] = []
    verdicts: dict[str, str] = {}

    for eid, rec in rec_map.items():
        if not isinstance(rec, dict):
            continue
        verdicts[eid] = str(rec.get("verdict", "UNKNOWN"))
        if rec.get("latency_drag_50_to_250ms_usd") is not None:
            drags.append(float(rec["latency_drag_50_to_250ms_usd"]))
        lc = rec.get("latency_curve") if isinstance(rec.get("latency_curve"), dict) else {}
        any_ok = False
        for lat_data in lc.values():
            if not isinstance(lat_data, dict):
                continue
            if lat_data.get("ok") is True:
                any_ok = True
            if lat_data.get("swap_zero_ok") is True:
                swap_zero_checked += 1
            elif lat_data.get("swap_zero_ok") is False:
                swap_zero_violated = True
        if any_ok:
            engines_ok += 1

    max_drag = round(max(drags, key=abs), 2) if drags else None
    if swap_zero_violated:
        status, score = "FAIL", 0
    elif engines_run >= 1 and engines_ok == engines_run and swap_zero_checked >= engines_run:
        status, score = "PASS", 15
    else:
        status, score = "WARN", 7

    drag_txt = f"{max_drag:+.2f} USD" if max_drag is not None else "n/a"
    return {
        "id": "mt5_realtick_reconcile",
        "label": "MT5 Model=4 Real-Tick Reconciliation",
        "status": status,
        "score": score,
        "max_score": 15,
        "detail": (
            f"Model={rt.get('model')} · Window={rt.get('window')} · Engines={engines_ok}/{engines_run} OK "
            f"· Swap==0 Checked={swap_zero_checked} (Viol={swap_zero_violated}) · MaxDrag50->250ms={drag_txt}"
        ),
        "data": {
            "model": rt.get("model"),
            "window": rt.get("window"),
            "latencies_ms": rt.get("latencies_ms", []),
            "engines_run": engines_run,
            "engines_ok": engines_ok,
            "swap_zero_checked": swap_zero_checked,
            "swap_zero_violated": swap_zero_violated,
            "max_latency_drag_50_to_250ms_usd": max_drag,
            "verdicts": verdicts,
        },
    }


def _check_pod_v2_risk_caps(root: Path, capital_usd: float, usd_vnd: float) -> dict[str, Any]:
    pod_md = root / "planning/research/QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md"
    if not pod_md.is_file():
        return {
            "id": "pod_v2_risk_caps",
            "label": "Quant Pod v2 CEX<=25% & Black-Swan Risk Guard",
            "status": "PENDING",
            "score": 0,
            "max_score": 15,
            "detail": "Awaiting QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md",
            "data": {"present": False},
        }

    txt = pod_md.read_text(encoding="utf-8", errors="replace")
    weights: dict[str, dict[str, float]] = {}
    shocks: dict[str, dict[str, float]] = {}
    sleeve_cols: list[str] = []

    for raw_ln in txt.splitlines():
        ln = raw_ln.strip()
        if not ln.startswith("|") or ln.startswith("|---"):
            continue
        cols = [c.strip() for c in ln.strip("|").split("|")]
        if cols[0] == "Allocator" and "Total CEX%" in cols:
            sleeve_cols = cols[1:]
            continue
        if cols[0] in ("NCO_CexCap25", "ERC_LW_CexCap25", "NCO_Capped35", "HRP"):
            if sleeve_cols and len(cols) == 1 + len(sleeve_cols) and cols[0] not in weights:
                weights[cols[0]] = {
                    col: (_parse_float(val) or 0.0)
                    for col, val in zip(sleeve_cols, cols[1:])
                }
            elif len(cols) >= 5 and cols[1].startswith("-"):
                shocks[cols[0]] = {
                    "cex50_instant_pct": abs(_parse_float(cols[1]) or 0.0),
                    "cex50_plus_p99d_pct": abs(_parse_float(cols[2]) or 0.0),
                    "corr085_p99_pct": abs(_parse_float(cols[3]) or 0.0),
                    "worst_case_pct": abs(_parse_float(cols[4]) or 0.0),
                }

    nco_w = weights.get("NCO_CexCap25")
    erc_w = weights.get("ERC_LW_CexCap25")
    nco_s = shocks.get("NCO_CexCap25")
    hrp_s = shocks.get("HRP")

    if not nco_w or not nco_s:
        return {
            "id": "pod_v2_risk_caps",
            "label": "Quant Pod v2 CEX<=25% & Black-Swan Risk Guard",
            "status": "WARN",
            "score": 7,
            "max_score": 15,
            "detail": "Pod v2 report found but NCO_CexCap25 rows incomplete",
            "data": {"present": True, "weights": weights, "shocks": shocks},
        }

    nco_cex_pct = float(nco_w.get("Total CEX%", 0.0))
    erc_cex_pct = float((erc_w or {}).get("Total CEX%", 0.0))
    cap_ok = nco_cex_pct <= 25.0 + 1e-6 and erc_cex_pct <= 25.0 + 1e-6

    wc_pct = nco_s["worst_case_pct"]
    wc_usd = round(capital_usd * wc_pct / 100.0, 2)
    wc_vnd_m = round((wc_usd * usd_vnd) / 1_000_000.0, 1)
    hrp_wc_pct = (hrp_s or {}).get("worst_case_pct", 41.58)
    hrp_wc_vnd_m = round((capital_usd * hrp_wc_pct / 100.0 * usd_vnd) / 1_000_000.0, 1)

    status = "PASS" if cap_ok else "FAIL"
    score = 15 if cap_ok else 0
    return {
        "id": "pod_v2_risk_caps",
        "label": "Quant Pod v2 CEX<=25% & Black-Swan Risk Guard",
        "status": status,
        "score": score,
        "max_score": 15,
        "detail": (
            f"NCO_CexCap25 TotalCEX={nco_cex_pct:.1f}% (<=25% OK={cap_ok}) · "
            f"-50% CEX Worst={wc_pct:.2f}% -> -{wc_usd:,.0f} USD (-{wc_vnd_m:.1f} tr VND @ {capital_usd:,.0f} USD) "
            f"vs HRP -{hrp_wc_pct:.2f}% (-{hrp_wc_vnd_m:.1f} tr VND)"
        ),
        "data": {
            "present": True,
            "capital_usd": round(capital_usd, 2),
            "usd_vnd": usd_vnd,
            "cap_enforced_le_25pct": cap_ok,
            "nco_cexcap25_weights_pct": nco_w,
            "erc_lw_cexcap25_weights_pct": erc_w,
            "nco_cexcap25_shocks_pct": nco_s,
            "nco_worst_loss_usd": wc_usd,
            "nco_worst_loss_vnd_m": wc_vnd_m,
            "hrp_worst_loss_vnd_m": hrp_wc_vnd_m,
        },
    }


def build_daily_ops_briefing(
    root: Path = ROOT,
    *,
    capital_usd: float = DEFAULT_CAPITAL_USD,
    usd_vnd: float = DEFAULT_USD_VND,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Assemble full deterministic Operational Health Briefing across all 6 domains."""
    ts_now = now_utc or datetime.now(timezone.utc)
    cap_u = max(1_000.0, float(capital_usd))
    fx = max(1_000.0, float(usd_vnd))

    checks = [
        _check_holdout_lock(root),
        _check_crypto_shadow(root),
        _check_crypto_maker_probe(root),
        _check_mt5_demo_live(root, ts_now),
        _check_mt5_realtick(root),
        _check_pod_v2_risk_caps(root, cap_u, fx),
    ]

    counts = {"PASS": 0, "WARN": 0, "PENDING": 0, "FAIL": 0}
    raw_score = 0
    max_score = 0
    for c in checks:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
        raw_score += int(c["score"])
        max_score += int(c["max_score"])

    # Hard fail-closed penalty: any FAIL caps health score at <= 40
    health_score = min(40, raw_score) if counts["FAIL"] > 0 else min(100, raw_score)
    if counts["FAIL"] > 0:
        overall_grade = "CRITICAL_FAIL_CLOSED"
    elif health_score >= 85:
        overall_grade = "GREEN_OPERATIONAL"
    elif health_score >= 55:
        overall_grade = "AMBER_PARTIAL_LIVE"
    else:
        overall_grade = "STANDBY_AWAITING_DAEMONS"

    return {
        "schema": "naqex-daily-ops-briefing-v1",
        "generated_utc": ts_now.isoformat(),
        "order_send_count": ORDER_SEND_COUNT,
        "capital_usd": round(cap_u, 2),
        "capital_vnd_m": round((cap_u * fx) / 1_000_000.0, 1),
        "usd_vnd": fx,
        "health_score": int(health_score),
        "max_score": int(max_score),
        "overall_grade": overall_grade,
        "status_counts": counts,
        "checks": checks,
    }


def render_daily_ops_briefing_md(payload: dict[str, Any]) -> str:
    """Render concise Vietnamese Operations Briefing Markdown (strictly zero bare `$`)."""
    sc = payload["status_counts"]
    lines = [
        "---",
        "doc_type: ops-briefing",
        f"generated_utc: {payload['generated_utc']}",
        f"health_score: {payload['health_score']}",
        f"overall_grade: {payload['overall_grade']}",
        f"order_send_count: {payload['order_send_count']}",
        "---",
        "",
        "# Bản Tin Vận Hành Ngày — Naqex Quant Pod (`OrderSend = 0`)",
        "",
        f"- **Thời điểm UTC:** `{payload['generated_utc']}`",
        f"- **Điểm Sức Khỏe Vận Hành (Health Score):** **`{payload['health_score']} / {payload['max_score']}`** (`{payload['overall_grade']}`)",
        f"- **Phân bổ Trạng thái:** `PASS={sc['PASS']}` · `WARN={sc['WARN']}` · `PENDING={sc['PENDING']}` · `FAIL={sc['FAIL']}`",
        f"- **Quy mô vốn chiếu rủi ro:** `{payload['capital_usd']:,.0f} USD` (`{payload['capital_vnd_m']:,.1f} triệu VND` @ `{payload['usd_vnd']:,.0f} VND/USD`)",
        "",
        "## 1. Bảng Kiểm Tra 6 Trụ Cột Thực Chiến",
        "",
        "| Trụ cột | Trạng thái | Điểm | Chi tiết xác minh thực tế |",
        "| --- | :---: | :---: | --- |",
    ]

    for c in payload["checks"]:
        lines.append(f"| **{c['label']}** | `{c['status']}` | `{c['score']}/{c['max_score']}` | {c['detail']} |")

    pod_chk = next((c for c in payload["checks"] if c["id"] == "pod_v2_risk_caps"), None)
    if pod_chk and pod_chk["data"].get("present") and pod_chk["data"].get("nco_cexcap25_weights_pct"):
        w = pod_chk["data"]["nco_cexcap25_weights_pct"]
        lines += [
            "",
            "## 2. Phân Bổ Mục Tiêu Quant Pod v2 (`NCO_CexCap25` — Tái Cân Bằng `Monthly_1st`)",
            "",
            "| Sleeve | Tỷ trọng `NCO_CexCap25` | Quy đổi USD | Quy đổi triệu VND |",
            "| --- | ---: | ---: | ---: |",
        ]
        cap_u = float(payload["capital_usd"])
        fx = float(payload["usd_vnd"])
        for k, pct in w.items():
            if k == "Total CEX%":
                continue
            u = cap_u * float(pct) / 100.0
            vm = (u * fx) / 1_000_000.0
            lines.append(f"| `{k}` | `{pct:.1f}%` | `{u:,.0f} USD` | `{vm:,.1f} tr VND` |")
        lines.append(f"| **Tổng phơi nhiễm CEX (`S2 + S3A`)** | **`{w.get('Total CEX%', 0.0):.1f}% <= 25.0%`** | **`{cap_u * float(w.get('Total CEX%', 0.0)) / 100.0:,.0f} USD`** | **`{(cap_u * float(w.get('Total CEX%', 0.0)) / 100.0 * fx) / 1e6:,.1f} tr VND`** |")

    lines += [
        "",
        "## 3. Hành Động Ưu Tiên Kế Tiếp",
        "",
    ]
    actions = []
    for c in payload["checks"]:
        if c["status"] == "FAIL":
            actions.append(f"- **[KHẨN CẤP — FAIL] `{c['id']}`:** Kiểm tra ngay trước mọi quyết định giao dịch ({c['detail']}).")
        elif c["status"] == "PENDING":
            actions.append(f"- **[CHỜ KÍCH HOẠT — PENDING] `{c['id']}`:** {c['detail']}.")
        elif c["status"] == "WARN":
            actions.append(f"- **[THEO DÕI — WARN] `{c['id']}`:** {c['detail']}.")
    if not actions:
        actions.append("- Toàn bộ 6 trụ cột đều `PASS` (`100/100`): duy trì giám sát định kỳ và không can thiệp giữa lệnh.")
    lines.extend(actions)
    lines.append("")
    md_out = "\n".join(lines)
    # Hard safety guard against bare '$' slipping into prose
    assert "$" not in md_out, "Bare '$' detected in daily ops briefing Markdown!"
    return md_out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Naqex Quant Pod 1-Command Daily Ops Briefing CLI (OrderSend=0)")
    ap.add_argument("--root", type=Path, default=ROOT, help="Workspace root directory")
    ap.add_argument("--capital-usd", type=float, default=DEFAULT_CAPITAL_USD, help="Capital tier in USD for VND stress display")
    ap.add_argument("--usd-vnd", type=float, default=DEFAULT_USD_VND, help="USD/VND exchange rate")
    ap.add_argument("--out-md", type=Path, default=None, help="Optional path to write Vietnamese Markdown briefing")
    ap.add_argument("--out-json", type=Path, default=None, help="Optional path to write JSON receipt")
    args = ap.parse_args(argv)

    payload = build_daily_ops_briefing(
        root=args.root,
        capital_usd=args.capital_usd,
        usd_vnd=args.usd_vnd,
    )
    md = render_daily_ops_briefing_md(payload)

    if args.out_json is not None:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    if args.out_md is not None:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(md, encoding="utf-8", newline="\n")

    print(json.dumps({
        "schema": payload["schema"],
        "generated_utc": payload["generated_utc"],
        "health_score": payload["health_score"],
        "max_score": payload["max_score"],
        "overall_grade": payload["overall_grade"],
        "status_counts": payload["status_counts"],
        "out_md": str(args.out_md) if args.out_md else None,
        "out_json": str(args.out_json) if args.out_json else None,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
