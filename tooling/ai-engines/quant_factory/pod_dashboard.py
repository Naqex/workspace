"""Unified Naqex Quant Pod Command Center — Single-Command <2s Dashboard Generator (M5.2).

Outputs flat-first static HTML Control Room (`.runtime/pod_dashboard.html`) + Markdown snapshot
(`.runtime/pod_dashboard_snapshot.md`) in < 1.5s with zero external CDN/JS dependencies:
  - 4-Sleeve performance metrics & 7-allocator comparison (`ERC_Capped35` production target)
  - 4x4 synchronous correlation matrix
  - Capital Weight % vs Risk Budget Contribution % bars
  - Per-sleeve Live Alpha Decay traffic lights (CUSUM + Wald SPRT + Bootstrap Cone)
  - MT5 Heartbeat / Orchestrator status (`ops_monitor.inspect_heartbeat`)
  - Upcoming official Red-News calendar check (`naqex_red_news_utc.csv`, extended through 2027)
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import sys
import time

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

ROOT = Path(__file__).resolve().parents[3]
from quant_factory.live_decay_monitor import evaluate_live_decay
from quant_factory.ops_monitor import inspect_heartbeat
from quant_factory.portfolio_allocator import (
    ALLOCATORS,
    align_sleeves_business_days,
    compute_risk_contributions,
    compute_series_metrics,
    load_external_sleeve_json,
)
from quant_factory.report_gen import format_markdown_table

DEFAULT_RETURNS_DIR = ROOT / ".runtime/quant-pod-returns"
DEFAULT_HTML_OUT = ROOT / ".runtime/pod_dashboard.html"
DEFAULT_MD_OUT = ROOT / ".runtime/pod_dashboard_snapshot.md"
DEFAULT_RED_NEWS_CSV = ROOT / "tooling/ai-engines/exports/Files/naqex_red_news_utc.csv"
DEFAULT_HEARTBEAT_PATH = ROOT / ".runtime/naqex_heartbeat.json"
DERIVED_META_JSON = ROOT / ".runtime/hot-m1-cache/_derived/frozen_9e_tapes_v1.json"
LOCK_PATH = ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"
REGISTRY_PATH = ROOT / "planning/research/PORTFOLIO-REGISTRY.json"

CCY_TO_SYMBOLS = {
    "USD": "USDJPY, GBPUSD, EURUSD, US100.cash, XAUUSD",
    "EUR": "EURJPY, EURUSD",
    "GBP": "GBPUSD",
    "JPY": "USDJPY, EURJPY",
    "ALL": "ALL SYMBOLS",
}


def load_sleeve1_fast_dev_daily() -> tuple[dict[str, float], dict]:
    """Zero-Numba ultra-fast (<0.15s) Sleeve #1 daily loader from SHA-verified derived JSON tape index."""
    lock_sha = hashlib.sha256(LOCK_PATH.read_bytes()).hexdigest()
    reg = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    expected_lock = reg.get("holdout_lock", {}).get("lock_sha256", "")
    if expected_lock and lock_sha != expected_lock:
        raise ValueError(f"HOLDOUT_LOCK_SHA_MISMATCH: expected={expected_lock[:12]} got={lock_sha[:12]}")
    reg_sha = hashlib.sha256(json.dumps(reg.get("engines", []), sort_keys=True).encode("utf-8")).hexdigest()
    binding = hashlib.sha256(f"{lock_sha}|{reg_sha}|v1".encode()).hexdigest()

    base_risks = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    core7 = reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"]

    if DERIVED_META_JSON.exists():
        meta_raw = json.loads(DERIVED_META_JSON.read_text(encoding="utf-8"))
        if meta_raw.get("binding_sha256") == binding:
            ext_days = meta_raw["ext_days"]
            if max(ext_days) >= "2025-01-01":
                raise AssertionError(f"HOLDOUT_CONTAMINATION: {max(ext_days)}")
            daily = {dk: 0.0 for dk in ext_days}
            tapes_idx = meta_raw["tapes"]
            for eng in core7:
                risk_frac = base_risks[eng]
                for dk, row in tapes_idx[eng]["rows"].items():
                    if dk in daily:
                        daily[dk] += float(row["net_R"]) * risk_frac
            return daily, {
                "sleeve_id": "S1_PROP_FX_IDX",
                "strategy_name": "PORT_7E_P28_CORE_DEV",
                "holdout_lock_sha256": lock_sha,
            }

    # Cold-cache fallback
    from quant_factory.data_store import build_or_load_frozen_tapes
    d = build_or_load_frozen_tapes(force_rebuild=False)
    ext_days = d["ext_days"]
    daily = {dk: 0.0 for dk in ext_days}
    for eng in core7:
        risk_frac = base_risks[eng]
        for dk, (row, _st, _mk) in d["tapes"][eng].items():
            if dk in daily:
                daily[dk] += float(row["net_R"]) * risk_frac
    return daily, {
        "sleeve_id": "S1_PROP_FX_IDX",
        "strategy_name": "PORT_7E_P28_CORE_DEV",
        "holdout_lock_sha256": lock_sha,
    }


def load_upcoming_red_news(
    csv_path: Path = DEFAULT_RED_NEWS_CSV,
    *,
    now_utc_ts: int | None = None,
    limit: int = 10,
) -> list[dict]:
    """Load next `limit` upcoming official red-news events from `naqex_red_news_utc.csv`."""
    now_ts = int(now_utc_ts if now_utc_ts is not None else time.time())
    if not csv_path.exists():
        return []
    upcoming = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            try:
                ts = int(r["utc_ts"])
            except (KeyError, ValueError):
                continue
            if ts >= now_ts - 300:
                ccy = str(r.get("ccy", "USD")).strip().upper()
                ev = str(r.get("event", "")).strip()
                dt_iso = datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                hrs = round((ts - now_ts) / 3600.0, 1)
                upcoming.append({
                    "utc_ts": ts,
                    "utc_iso": dt_iso,
                    "ccy": ccy,
                    "event": ev,
                    "hours_away": hrs,
                    "affected_symbols": CCY_TO_SYMBOLS.get(ccy, ccy),
                })
    upcoming.sort(key=lambda x: x["utc_ts"])
    return upcoming[:limit]


def build_dashboard_snapshot(
    *,
    returns_dir: Path = DEFAULT_RETURNS_DIR,
    heartbeat_path: Path = DEFAULT_HEARTBEAT_PATH,
    red_news_csv: Path = DEFAULT_RED_NEWS_CSV,
    now_utc_ts: int | None = None,
    seed: int = 20261124,
) -> dict:
    """Assemble full real-time Pod Command Center state in < 1.0s."""
    t0 = time.perf_counter()
    now_ts = int(now_utc_ts if now_utc_ts is not None else time.time())

    s1_map, s1_meta = load_sleeve1_fast_dev_daily()
    sleeve_maps = {"S1_PROP_FX_IDX": s1_map}
    sleeve_metas = {"S1_PROP_FX_IDX": s1_meta}

    for sid, fname in (
        ("S2_CRYPTO_SPOT", "sleeve2_crypto_spot.json"),
        ("S3A_FUND_CARRY", "sleeve3a_funding_carry.json"),
        ("S3B_MACRO_ETF", "sleeve3b_macro_etf.json"),
    ):
        p = returns_dir / fname
        if p.exists():
            rmap, rmeta = load_external_sleeve_json(p)
            sleeve_maps[sid] = rmap
            sleeve_metas[sid] = rmeta

    days, mat, names = align_sleeves_business_days(sleeve_maps, end_day="2024-12-31")
    train_mask = np.array([d <= "2022-12-31" for d in days])
    oos_mask = ~train_mask
    mat_tr = mat[train_mask]
    mat_oos = mat[oos_mask]

    sleeve_metrics = {nm: compute_series_metrics(mat[:, j], ann_days=252.0) for j, nm in enumerate(names)}
    corr = np.corrcoef(mat, rowvar=False) if len(names) > 1 else np.ones((1, 1))
    corr = np.nan_to_num(corr, nan=0.0)
    cov_full = np.cov(mat, rowvar=False) if len(names) > 1 else np.array([[float(np.var(mat[:, 0], ddof=1))]])

    alloc_summary = {}
    for mname, fn in ALLOCATORS.items():
        w_tr = fn(mat_tr) if len(names) > 1 else np.ones(1)
        w_full = fn(mat) if len(names) > 1 else np.ones(1)
        rc = compute_risk_contributions(cov_full, w_full)
        alloc_summary[mname] = {
            "weights_pct": {nm: round(100.0 * float(w_full[j]), 2) for j, nm in enumerate(names)},
            "risk_pct": {nm: round(100.0 * float(rc[j]), 2) for j, nm in enumerate(names)},
            "oos_metrics": compute_series_metrics(mat_oos @ w_tr, ann_days=252.0),
            "full_metrics": compute_series_metrics(mat @ w_tr, ann_days=252.0),
        }

    # CUSUM / Wald SPRT / Confidence Cone traffic lights (trailing 252d OOS vs earlier baseline)
    traffic_lights = {}
    for j, nm in enumerate(names):
        base_arr = mat_tr[:, j]
        fwd_arr = mat_oos[-252:, j] if len(mat_oos) >= 60 else mat_oos[:, j]
        dec = evaluate_live_decay(base_arr, fwd_arr, n_cone_draws=1000, seed=seed + j)
        v = dec["verdict"]
        light = "GREEN" if v.startswith("GREEN") else ("AMBER" if v.startswith("AMBER") else "RED")
        traffic_lights[nm] = {
            "light": light,
            "verdict": v,
            "cusum_sigma": dec["cusum"]["current_negative_sigma"],
            "sprt_state": dec["sprt"]["state"],
            "sprt_llr": dec["sprt"]["llr"],
            "cone_pct": dec["confidence_cone"]["observed_percentile"],
            "n_eval_days": dec["n_live"],
        }

    # Heartbeat status (graceful standby when MT5 has not been launched yet)
    if heartbeat_path.exists():
        hb = inspect_heartbeat(heartbeat_path, now_utc_ts=now_ts)
    else:
        hb = {
            "status": "STANDBY_DRYRUN",
            "age_seconds": None,
            "alerts": ["MT5 terminal not yet launched (OrderSend=0, DryRun standby)."],
            "payload": {"dry_run": True, "regime": "STANDBY", "risk_mult": 1.0, "open_positions": 0, "orphan_no_sl": 0},
        }

    upcoming_news = load_upcoming_red_news(red_news_csv, now_utc_ts=now_ts, limit=10)
    primary_policy = "ERC_Capped35" if "ERC_Capped35" in alloc_summary else "Equal_Weight"

    return {
        "schema": "naqex-pod-dashboard-v1",
        "generated_utc": datetime.fromtimestamp(now_ts, timezone.utc).isoformat(),
        "holdout_lock_sha256": s1_meta["holdout_lock_sha256"],
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "overlap_window": f"{days[0]}..{days[-1]} ({len(days)} biz days)",
        "primary_policy": primary_policy,
        "sleeve_names": names,
        "sleeve_metas": sleeve_metas,
        "sleeve_metrics": sleeve_metrics,
        "corr_matrix": [[round(float(corr[i, j]), 3) for j in range(len(names))] for i in range(len(names))],
        "allocators": alloc_summary,
        "traffic_lights": traffic_lights,
        "heartbeat": hb,
        "upcoming_red_news": upcoming_news,
        "gen_seconds": round(time.perf_counter() - t0, 4),
    }


def render_dashboard_markdown(snap: dict) -> str:
    """Render concise Markdown snapshot of the Unified Pod Command Center."""
    names = snap["sleeve_names"]
    pol = snap["primary_policy"]
    pol_d = snap["allocators"][pol]
    hb = snap["heartbeat"]
    next_ev = snap["upcoming_red_news"][0] if snap["upcoming_red_news"] else None

    lines = [
        "# Naqex Quant Pod — Command Center Snapshot",
        "",
        f"- **Generated UTC:** `{snap['generated_utc']}` (gen `{snap['gen_seconds']*1000:.0f} ms`)",
        f"- **Safety Seal:** Holdout `2025+` SEALED (`{snap['holdout_lock_sha256'][:12]}...`, `holdout_rows = 0`, `OrderSend = 0`)",
        f"- **Active Allocation Policy:** `{pol}` | Blind OOS (`2023–2024`): CAGR `{pol_d['oos_metrics']['cagr_pct']:+.2f}%`, Sharpe `{pol_d['oos_metrics']['sharpe']:.2f}`, MaxDD `{pol_d['oos_metrics']['max_dd_pct']:.2f}%`, Calmar `{pol_d['oos_metrics']['calmar']:.2f}`",
        f"- **MT5 Heartbeat:** `{hb['status']}` | **Next Red-News:** `{next_ev['utc_iso'] + ' ' + next_ev['ccy'] + ' ' + next_ev['event'] if next_ev else 'NONE'}`",
        "",
        "## 1. 4-Sleeve Metrics, Risk Budget & CUSUM/SPRT Traffic Lights",
        "",
    ]
    headers = ["Sleeve", "Strategy", "CAGR%", "Vol%", "Sharpe", "MaxDD%", "Cap Wt%", "Risk Wt%", "Traffic Light", "CUSUM σ", "SPRT State", "Cone Pct"]
    rows = []
    for nm in names:
        m = snap["sleeve_metrics"][nm]
        tl = snap["traffic_lights"][nm]
        rows.append([
            nm,
            snap["sleeve_metas"][nm]["strategy_name"],
            f"{m['cagr_pct']:+.2f}%",
            f"{m['ann_vol_pct']:.2f}%",
            f"{m['sharpe']:.2f}",
            f"{m['max_dd_pct']:.2f}%",
            f"{pol_d['weights_pct'][nm]:.1f}%",
            f"{pol_d['risk_pct'][nm]:.1f}%",
            tl["light"],
            f"{tl['cusum_sigma']:.2f}σ",
            tl["sprt_state"],
            f"{tl['cone_pct']:.1f}th",
        ])
    lines.append(format_markdown_table(headers, rows, right_align_cols={2, 3, 4, 5, 6, 7, 9, 11}))

    lines += ["", "## 2. 4×4 Synchronous Correlation Matrix", ""]
    c_headers = ["Sleeve"] + names
    c_rows = [[names[i]] + [f"{snap['corr_matrix'][i][j]:+.3f}" for j in range(len(names))] for i in range(len(names))]
    lines.append(format_markdown_table(c_headers, c_rows, right_align_cols=set(range(1, len(names) + 1))))

    lines += ["", "## 3. Upcoming Official Red-News Guard (2026–2027)", ""]
    n_headers = ["UTC Time", "Hours Away", "CCY", "Event (Provenance)", "Affected Naqex Symbols"]
    n_rows = [[e["utc_iso"], f"{e['hours_away']:+.1f}h", e["ccy"], e["event"], e["affected_symbols"]] for e in snap["upcoming_red_news"]]
    lines.append(format_markdown_table(n_headers, n_rows, right_align_cols={1}))
    lines.append("")
    return "\n".join(lines)


def _pill(label: str, kind: str) -> str:
    cls = {"GREEN": "pill-g", "OK": "pill-g", "AMBER": "pill-a", "WARNING": "pill-a", "STANDBY_DRYRUN": "pill-b"}.get(kind, "pill-r")
    return f'<span class="pill {cls}">{html.escape(label)}</span>'


def _corr_bg(val: float, is_diag: bool) -> str:
    if is_diag:
        return "#21262d"
    if val >= 0.40:
        return "rgba(248,81,73,0.28)"
    if val >= 0.20:
        return "rgba(210,153,34,0.24)"
    if val <= -0.10:
        return "rgba(46,160,67,0.24)"
    return "rgba(56,139,253,0.10)"


def render_dashboard_html(snap: dict) -> str:
    """Render flat-first, self-contained HTML Control Room (zero external CDN/JS)."""
    names = snap["sleeve_names"]
    pol = snap["primary_policy"]
    pol_d = snap["allocators"][pol]
    oos_m = pol_d["oos_metrics"]
    hb = snap["heartbeat"]
    hb_p = hb.get("payload") or {}
    greens = sum(1 for v in snap["traffic_lights"].values() if v["light"] == "GREEN")
    next_ev = snap["upcoming_red_news"][0] if snap["upcoming_red_news"] else None

    sleeve_rows_html = []
    for nm in names:
        m = snap["sleeve_metrics"][nm]
        tl = snap["traffic_lights"][nm]
        cap_w = pol_d["weights_pct"][nm]
        risk_w = pol_d["risk_pct"][nm]
        sleeve_rows_html.append(
            f"<tr>"
            f"<td><strong>{html.escape(nm)}</strong><div class='sub'>{html.escape(str(snap['sleeve_metas'][nm]['strategy_name']))}</div></td>"
            f"<td class='num'>{m['cagr_pct']:+.2f}%</td>"
            f"<td class='num'>{m['ann_vol_pct']:.2f}%</td>"
            f"<td class='num'>{m['sharpe']:.2f}</td>"
            f"<td class='num'>{m['max_dd_pct']:.2f}%</td>"
            f"<td class='num'>{m['calmar']:.2f}</td>"
            f"<td><div class='bar-wrap'><div class='bar-cap' style='width:{min(100.0, cap_w):.1f}%'></div><span>{cap_w:.1f}%</span></div>"
            f"<div class='bar-wrap'><div class='bar-risk' style='width:{min(100.0, risk_w):.1f}%'></div><span>{risk_w:.1f}%</span></div></td>"
            f"<td>{_pill(tl['light'], tl['light'])}<div class='sub'>CUSUM {tl['cusum_sigma']:.2f}&sigma; | Cone {tl['cone_pct']:.0f}th</div></td>"
            f"<td class='mono'>{html.escape(tl['sprt_state'])}<div class='sub'>LLR={tl['sprt_llr']:.2f}</div></td>"
            f"</tr>"
        )

    corr_head = "".join(f"<th class='num'>{html.escape(nm)}</th>" for nm in names)
    corr_rows = []
    for i, nm in enumerate(names):
        cells = []
        for j in range(len(names)):
            v = snap["corr_matrix"][i][j]
            cells.append(f"<td class='num mono' style='background:{_corr_bg(v, i == j)}'>{v:+.3f}</td>")
        corr_rows.append(f"<tr><td><strong>{html.escape(nm)}</strong></td>{''.join(cells)}</tr>")

    alloc_rows = []
    for aname, ad in snap["allocators"].items():
        om = ad["oos_metrics"]
        fm = ad["full_metrics"]
        mark = " *" if aname == pol else ""
        alloc_rows.append(
            f"<tr><td><strong>{html.escape(aname + mark)}</strong></td>"
            f"<td class='num'>{om['cagr_pct']:+.2f}%</td><td class='num'>{om['ann_vol_pct']:.2f}%</td>"
            f"<td class='num'>{om['sharpe']:.2f}</td><td class='num'>{om['max_dd_pct']:.2f}%</td><td class='num'>{om['calmar']:.2f}</td>"
            f"<td class='num'>{fm['cagr_pct']:+.2f}%</td><td class='num'>{fm['calmar']:.2f}</td></tr>"
        )

    news_rows = []
    for ev in snap["upcoming_red_news"]:
        news_rows.append(
            f"<tr><td class='mono'>{html.escape(ev['utc_iso'])}</td>"
            f"<td class='num mono'>{ev['hours_away']:+.1f}h</td>"
            f"<td><strong>{html.escape(ev['ccy'])}</strong></td>"
            f"<td class='mono'>{html.escape(ev['event'])}</td>"
            f"<td class='sub'>{html.escape(ev['affected_symbols'])}</td></tr>"
        )

    alerts_html = "".join(f"<li>{html.escape(a)}</li>" for a in hb.get("alerts", [])) or "<li>All guards healthy.</li>"
    next_ev_txt = f"{next_ev['ccy']} {next_ev['event']}" if next_ev else "NONE"
    next_ev_sub = f"{next_ev['utc_iso']} ({next_ev['hours_away']:+.1f}h)" if next_ev else "Calendar empty"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Naqex Quant Pod — Command Center</title>
<style>
  :root {{ --bg:#0d1117; --card:#161b22; --bd:#30363d; --tx:#e6edf3; --mut:#8b949e; --g:#2ea043; --a:#d29922; --r:#f85149; --b:#388bfd; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:20px; background:var(--bg); color:var(--tx); font:13px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
  header {{ display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; border-bottom:1px solid var(--bd); padding-bottom:12px; margin-bottom:16px; gap:8px; }}
  h1 {{ margin:0; font-size:18px; letter-spacing:0.2px; }}
  h2 {{ margin:0 0 10px; font-size:14px; color:#c9d1d9; text-transform:uppercase; letter-spacing:0.5px; }}
  .meta {{ color:var(--mut); font-size:12px; }}
  .grid-4 {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; margin-bottom:16px; }}
  .grid-2 {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(420px,1fr)); gap:12px; margin-bottom:16px; }}
  .card {{ background:var(--card); border:1px solid var(--bd); border-radius:4px; padding:14px; margin-bottom:14px; }}
  .kpi-val {{ font-size:22px; font-weight:600; margin:4px 0; }}
  .sub {{ color:var(--mut); font-size:11px; }}
  .mono {{ font-family:ui-monospace,SFMono-Regular,Consolas,monospace; }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; }}
  th, td {{ padding:7px 8px; border-bottom:1px solid var(--bd); text-align:left; vertical-align:middle; }}
  th {{ color:var(--mut); font-weight:600; font-size:11px; text-transform:uppercase; }}
  td.num, th.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .pill {{ display:inline-block; padding:2px 7px; border-radius:3px; font-size:11px; font-weight:600; }}
  .pill-g {{ background:rgba(46,160,67,0.2); color:#3fb950; border:1px solid rgba(46,160,67,0.5); }}
  .pill-a {{ background:rgba(210,153,34,0.2); color:#e3b341; border:1px solid rgba(210,153,34,0.5); }}
  .pill-r {{ background:rgba(248,81,73,0.2); color:#ff7b72; border:1px solid rgba(248,81,73,0.5); }}
  .pill-b {{ background:rgba(56,139,253,0.2); color:#79c0ff; border:1px solid rgba(56,139,253,0.5); }}
  .bar-wrap {{ display:flex; align-items:center; gap:6px; margin:2px 0; }}
  .bar-cap {{ height:7px; background:var(--b); border-radius:2px; min-width:2px; }}
  .bar-risk {{ height:7px; background:var(--a); border-radius:2px; min-width:2px; }}
  .legend {{ font-size:11px; color:var(--mut); margin-bottom:6px; }}
  ul {{ margin:6px 0 0 18px; padding:0; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>NAQEX QUANT POD — UNIFIED CONTROL ROOM</h1>
    <div class="meta">Generated: <span class="mono">{html.escape(snap['generated_utc'])}</span> | Gen Time: <span class="mono">{snap['gen_seconds']*1000:.0f} ms</span> | Window: <span class="mono">{html.escape(snap['overlap_window'])}</span></div>
  </div>
  <div>{_pill('HOLDOUT 2025+ SEALED | OrderSend=0', 'GREEN')} {_pill(f'LOCK {snap["holdout_lock_sha256"][:10]}', 'STANDBY_DRYRUN')}</div>
</header>

<section class="grid-4">
  <div class="card">
    <div class="sub">ACTIVE POLICY ({html.escape(pol)}) — OOS 2023-24</div>
    <div class="kpi-val">{oos_m['cagr_pct']:+.2f}% <span class="sub">CAGR</span></div>
    <div class="sub">Sharpe {oos_m['sharpe']:.2f} | Calmar {oos_m['calmar']:.2f} | MaxDD {oos_m['max_dd_pct']:.2f}%</div>
  </div>
  <div class="card">
    <div class="sub">ALPHA DECAY TRAFFIC LIGHTS (CUSUM+SPRT)</div>
    <div class="kpi-val">{greens}/{len(names)} GREEN</div>
    <div class="sub">Trailing 252d OOS vs Causal Train Baseline</div>
  </div>
  <div class="card">
    <div class="sub">MT5 ORCHESTRATOR HEARTBEAT</div>
    <div class="kpi-val">{_pill(hb['status'], hb['status'])}</div>
    <div class="sub">Regime={html.escape(str(hb_p.get('regime', 'N/A')))} | Mult={hb_p.get('risk_mult', 'N/A')}x | Orphan={hb_p.get('orphan_no_sl', 0)}</div>
  </div>
  <div class="card">
    <div class="sub">NEXT OFFICIAL RED-NEWS GUARD (±5m)</div>
    <div class="kpi-val" style="font-size:15px">{html.escape(next_ev_txt)}</div>
    <div class="sub mono">{html.escape(next_ev_sub)}</div>
  </div>
</section>

<section class="card">
  <h2>1. 4-Sleeve Performance, Capital vs Risk Budget &amp; Decay Lights</h2>
  <div class="legend"><span style="color:var(--b)">&#9632;</span> Capital Weight % ({html.escape(pol)}) &nbsp; <span style="color:var(--a)">&#9632;</span> Risk Budget Contribution %</div>
  <table>
    <thead><tr><th>Sleeve</th><th class="num">CAGR%</th><th class="num">Vol%</th><th class="num">Sharpe</th><th class="num">MaxDD%</th><th class="num">Calmar</th><th>Cap% / Risk%</th><th>CUSUM / Cone</th><th>Wald SPRT</th></tr></thead>
    <tbody>{''.join(sleeve_rows_html)}</tbody>
  </table>
</section>

<section class="grid-2">
  <div class="card">
    <h2>2. 4&times;4 Synchronous Correlation Matrix</h2>
    <table>
      <thead><tr><th>Sleeve</th>{corr_head}</tr></thead>
      <tbody>{''.join(corr_rows)}</tbody>
    </table>
  </div>
  <div class="card">
    <h2>3. Causal Allocator Benchmark (Blind OOS 2023-24)</h2>
    <table>
      <thead><tr><th>Method</th><th class="num">OOS CAGR</th><th class="num">OOS Vol</th><th class="num">OOS Sh</th><th class="num">OOS DD</th><th class="num">OOS Cal</th><th class="num">Full CAGR</th><th class="num">Full Cal</th></tr></thead>
      <tbody>{''.join(alloc_rows)}</tbody>
    </table>
  </div>
</section>

<section class="grid-2">
  <div class="card">
    <h2>4. MT5 Heartbeat &amp; Guard Telemetry</h2>
    <div class="sub">Age: <span class="mono">{hb['age_seconds']}s</span> | DryRun: <span class="mono">{hb_p.get('dry_run', True)}</span> | OpenPos: <span class="mono">{hb_p.get('open_positions', 0)}</span></div>
    <ul>{alerts_html}</ul>
  </div>
  <div class="card">
    <h2>5. Upcoming Official Red-News Calendar (2026–2027)</h2>
    <table>
      <thead><tr><th>UTC Time</th><th class="num">Away</th><th>CCY</th><th>Event</th><th>Affected Symbols</th></tr></thead>
      <tbody>{''.join(news_rows)}</tbody>
    </table>
  </div>
</section>
</body>
</html>
"""


def generate_pod_dashboard(
    *,
    html_out: Path = DEFAULT_HTML_OUT,
    md_out: Path = DEFAULT_MD_OUT,
    returns_dir: Path = DEFAULT_RETURNS_DIR,
    heartbeat_path: Path = DEFAULT_HEARTBEAT_PATH,
    red_news_csv: Path = DEFAULT_RED_NEWS_CSV,
    now_utc_ts: int | None = None,
) -> dict:
    """Single-command generator producing flat HTML Control Room + Markdown snapshot in < 2.0s."""
    t0 = time.perf_counter()
    snap = build_dashboard_snapshot(
        returns_dir=returns_dir,
        heartbeat_path=heartbeat_path,
        red_news_csv=red_news_csv,
        now_utc_ts=now_utc_ts,
    )
    html_text = render_dashboard_html(snap)
    md_text = render_dashboard_markdown(snap)
    html_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    html_out.write_text(html_text, encoding="utf-8", newline="\n")
    md_out.write_text(md_text, encoding="utf-8", newline="\n")
    total_sec = round(time.perf_counter() - t0, 4)
    snap["total_write_seconds"] = total_sec
    return snap


def main() -> int:
    parser = argparse.ArgumentParser(description="Naqex Quant Pod Unified Command Center (<2s)")
    parser.add_argument("--html", type=Path, default=DEFAULT_HTML_OUT)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD_OUT)
    args = parser.parse_args()
    snap = generate_pod_dashboard(html_out=args.html, md_out=args.md)
    print(json.dumps({
        "html_out": str(args.html),
        "html_bytes": args.html.stat().st_size,
        "md_out": str(args.md),
        "md_bytes": args.md.stat().st_size,
        "gen_seconds": snap["gen_seconds"],
        "total_write_seconds": snap["total_write_seconds"],
        "sleeves": snap["sleeve_names"],
        "traffic_lights": {k: v["light"] for k, v in snap["traffic_lights"].items()},
        "heartbeat_status": snap["heartbeat"]["status"],
        "upcoming_news_count": len(snap["upcoming_red_news"]),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
