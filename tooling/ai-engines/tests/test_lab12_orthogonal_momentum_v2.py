"""Wave-3 Cycle 2 Tests — Lab #12 Orthogonal Structural Momentum & Vol-Expansion Discovery.

Verifies:
  1. Realistic stop-breakout fill mechanics (`max(top, AskOpen)` / `min(bot, BidOpen)`) & ambiguous dual-touch skip.
  2. Conservative SL-before-TP M1 tie-break & hard `swap = 0` same-UTC-day flat before 20:55 UTC.
  3. Causal `shift=1` vol_ratio (ATR5/ATR20) & bit-for-bit future-mutation zero-lookahead on stop-breakout & cross-asset specs.
  4. Official red-news `+-5m` filter, `1.5x` friction monotonicity, and calibrated FTMO Swing 25K (`270 USD` fee) config.
  5. Sealed Holdout 2025+ lock (`holdout_rows_analysed == 0`, exact SHA-256), verified `.json` + `.sha256`
     receipt integrity, report hygiene (`0` bare `$`, `< 900 KB`, `0` broken links), and 100% verbatim
     JSON-to-Markdown parity across ALL 16 candidates + accretion tables (including FTMO 25K!).
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np
import pytest

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_core.ftmo_track_replay import profiles
from quant_factory.lab11_orthogonal_prop_v2_discovery import apply_red_news_and_15x_stress
from quant_factory.lab12_orthogonal_momentum_v2_discovery import (
    ORDER_SEND_CAPABLE,
    REPORT_DIR,
    REPORT_STEM,
    _build_lab12_firms,
    _scan_stop_breakout,
    build_lab12_catalog,
    evaluate_lab12_spec,
    replay_lab12_trade,
)

LAB12_JSON_PATH = REPORT_DIR / f"{REPORT_STEM}.json"
LAB12_SHA_PATH = REPORT_DIR / f"{REPORT_STEM}.sha256"
LAB12_MD_PATH = REPORT_DIR / f"{REPORT_STEM}.md"
HOLDOUT_LOCK_PATH = ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"


def _make_synthetic_bundle_v2(asset: str = "XAUUSD", n_days: int = 28) -> dict:
    """Build deterministic synthetic M1 Bid/Ask bundle strictly inside 2022 (< 2025-01-01) with shift=1 vol_ratio."""
    specs, _ = profiles()
    sw = specs["Swing"]
    spec_key = asset if asset in sw else ("US500.cash" if asset == "US500" else None)
    spec = sw.get(spec_key) if spec_key else None

    base_ts = int(datetime(2022, 3, 1, 0, 0, tzinfo=timezone.utc).timestamp())
    times_list = []
    quotes_list = []
    raw_days = []
    px = 1900.0 if asset == "XAUUSD" else (1.1000 if asset == "EURUSD" else 4200.0)
    spr = 0.40 if asset == "XAUUSD" else (0.0001 if asset == "EURUSD" else 0.50)
    tick = 0.03 if asset == "XAUUSD" else (0.00001 if asset == "EURUSD" else 0.08)

    day_count = 0
    cal_offset = 0
    while day_count < n_days:
        dsec = base_ts + cal_offset * 86400
        dt = datetime.fromtimestamp(dsec, timezone.utc)
        cal_offset += 1
        if dt.weekday() >= 5:
            continue
        fi = len(times_list)
        # Quiet Asian box (00:00..07:00 UTC), then directional breakout during London/NY (07:00..16:00 UTC)
        for m in range(1260):
            ts = dsec + m * 60
            if 420 <= m < 720:
                px += tick
            elif m >= 720:
                px += tick * 0.2
            bo = px
            bh = px + tick * 2.0
            bl = px - tick * 2.0
            bc = px
            times_list.append(ts)
            quotes_list.append([bo, bh, bl, bc, bo + spr, bh + spr, bl + spr, bc + spr])
        li = len(times_list) - 1
        raw_days.append({
            "day": dt.date().isoformat(),
            "year": dt.year,
            "weekday": dt.weekday(),
            "dsec": dsec,
            "fi": fi,
            "li": li,
            "flat_idx": fi + 20 * 60 + 50,
            "o": quotes_list[fi][0],
            "h": max(q[1] for q in quotes_list[fi:li + 1]),
            "l": min(q[2] for q in quotes_list[fi:li + 1]),
            "c": quotes_list[li][3],
        })
        day_count += 1

    times = np.asarray(times_list, dtype=np.int64)
    quotes = np.asarray(quotes_list, dtype=np.float64)

    days_out = []
    trs = []
    for i, d in enumerate(raw_days):
        if i == 0:
            trs.append(max(1e-9, d["h"] - d["l"]))
            continue
        prev = raw_days[i - 1]
        prev2_c = raw_days[i - 2]["c"] if i >= 2 else prev["o"]
        tr_prev = max(prev["h"] - prev["l"], abs(prev["h"] - prev2_c), abs(prev["l"] - prev2_c))
        if i >= 2:
            trs.append(max(1e-9, tr_prev))
        if len(trs) >= 20:
            atr14 = float(np.mean(trs[-14:]))
            atr5 = float(np.mean(trs[-5:]))
            atr20 = float(np.mean(trs[-20:]))
            days_out.append({
                **d,
                "prev_o": prev["o"],
                "prev_h": prev["h"],
                "prev_l": prev["l"],
                "prev_c": prev["c"],
                "prev_rng": max(1e-9, prev["h"] - prev["l"]),
                "prev_day": prev["day"],
                "atr": max(1e-9, atr14),
                "vol_ratio": atr5 / max(1e-9, atr20),
            })

    return {
        "asset": asset,
        "times": times,
        "quotes": quotes,
        "spec": spec,
        "usdjpy_close_map": {},
        "days": days_out,
        "day_map": {d["day"]: d for d in days_out},
        "meta": {},
    }


def test_lab12_stop_breakout_fill_gap_ambiguous_skip_and_swap_zero():
    """Verify stop-order gap fill `max(top, AskOpen)`, dual-touch bar skip, SL-before-TP, and swap=0."""
    b = _make_synthetic_bundle_v2("XAUUSD", n_days=25)
    d = b["days"][-1]
    ts_s = d["dsec"] + 7 * 3600
    ts_e = d["dsec"] + 14 * 3600
    ts_f = d["dsec"] + 20 * 3600 + 50 * 60

    # Case 1: Gap open above `top` -> BUY stop MUST fill at worse AskOpen (`max(top, AskOpen)`), NOT idealized `top`!
    q_gap = b["quotes"].copy()
    trigger_idx = d["fi"] + 7 * 3600 // 60 + 10
    top = float(q_gap[trigger_idx - 1, 5]) + 2.0
    bot = float(q_gap[trigger_idx - 1, 2]) - 50.0
    gap_ask_open = top + 1.50
    q_gap[trigger_idx, 4] = gap_ask_open
    q_gap[trigger_idx, 5] = gap_ask_open + 1.0
    q_gap[trigger_idx, 0] = gap_ask_open - 0.40
    q_gap[trigger_idx, 2] = gap_ask_open - 0.50
    b_gap = {**b, "quotes": q_gap}

    res = _scan_stop_breakout(b_gap, d, ts_s, ts_e, ts_f, top, bot, sl_dist=15.0)
    assert res is not None
    row, stamps, _marks, _fade = res
    assert row["side"] == 1
    assert row["entry_price"] == pytest.approx(gap_ask_open, abs=1e-6), "Must fill at worse AskOpen on gap!"
    assert row["swap_usd"] == 0.0
    dt_e = datetime.fromtimestamp(int(stamps[0]), timezone.utc)
    dt_x = datetime.fromtimestamp(int(stamps[-1]), timezone.utc)
    assert dt_e.date() == dt_x.date() and (dt_x.hour * 60 + dt_x.minute) <= 20 * 60 + 55

    # Case 2: Ambiguous single M1 bar touching BOTH `top` AND `bot` -> MUST skip trade conservatively!
    q_amb = b["quotes"].copy()
    q_amb[trigger_idx, 5] = top + 5.0
    q_amb[trigger_idx, 2] = bot - 5.0
    b_amb = {**b, "quotes": q_amb}
    assert _scan_stop_breakout(b_amb, d, ts_s, ts_e, ts_f, top, bot, sl_dist=15.0) is None

    # Case 3: Conservative SL-before-TP tie-break on same M1 bar
    e_idx = d["fi"] + 8 * 60
    ep = float(b["quotes"][e_idx, 4])
    q_tie = b["quotes"].copy()
    q_tie[e_idx + 3, 1] = ep + 20.0  # Bid high > TP
    q_tie[e_idx + 3, 2] = ep - 20.0  # Bid low < SL
    b_tie = {**b, "quotes": q_tie}
    res_tie = replay_lab12_trade(b_tie, e_idx, d["flat_idx"], 1, 10.0, tp_dist=10.0)
    assert res_tie is not None and res_tie[0]["reason"] == "SL_GAP_OR_TOUCH"


def test_lab12_causal_shift1_and_future_mutation_zero_lookahead():
    """Bit-for-bit zero-lookahead proof across stop-breakout and cross-asset confluence specs."""
    bx0 = _make_synthetic_bundle_v2("XAUUSD", n_days=28)
    be0 = _make_synthetic_bundle_v2("EURUSD", n_days=28)
    cut_day = bx0["days"][2]["day"]
    cut_end_x = bx0["days"][2]["li"]
    cut_end_e = be0["days"][2]["li"]

    qx1 = bx0["quotes"].copy()
    qe1 = be0["quotes"].copy()
    qx1[cut_end_x + 1 :, :] *= 1.40
    qe1[cut_end_e + 1 :, :] *= 0.70

    bx1 = {**bx0, "quotes": qx1, "days": [dict(d) if d["day"] <= cut_day else {**d, "atr": d["atr"] * 2.5} for d in bx0["days"]]}
    bx1["day_map"] = {d["day"]: d for d in bx1["days"]}
    be1 = {**be0, "quotes": qe1, "days": [dict(d) if d["day"] <= cut_day else {**d, "atr": d["atr"] * 2.5} for d in be0["days"]]}
    be1["day_map"] = {d["day"]: d for d in be1["days"]}

    cat = {c["id"]: c for c in build_lab12_catalog()}
    for cid in ("L12_B1_XAU_ASIA_BOX_LDN_BRK", "L12_D3_XAU_USD_SAFEHAVEN_NY"):
        cfg = {**cat[cid]}
        if "thr" in cfg:
            cfg["thr"] = 0.01
        if "max_box_atr" in cfg:
            cfg["max_box_atr"] = 5.0
        t0, _ = evaluate_lab12_spec({"XAUUSD": bx0, "EURUSD": be0}, cfg)
        t1, _ = evaluate_lab12_spec({"XAUUSD": bx1, "EURUSD": be1}, cfg)
        p0 = {dk: v for dk, v in t0.items() if dk <= cut_day}
        p1 = {dk: v for dk, v in t1.items() if dk <= cut_day}
        assert len(p0) >= 1, f"{cid} should trigger at least 1 trade on synthetic prefix"
        assert set(p0.keys()) == set(p1.keys())
        for dk in p0:
            assert p0[dk][0] == p1[dk][0], f"Lookahead detected in {cid} on {dk}!"
            assert np.array_equal(p0[dk][2], p1[dk][2])


def test_lab12_firms_red_news_and_15x_monotonicity():
    """Verify FTMO Swing 25K calibrated fee (270 USD), red-news +-5m pre-flatten, and 1.5x stress monotonicity."""
    firms = {f["id"]: f for f in _build_lab12_firms()}
    assert set(firms.keys()) == {"FTMO_SWING_10K", "FTMO_SWING_25K", "THE5ERS_HS_5K"}
    assert firms["FTMO_SWING_25K"]["capital_usd"] == 25000.0
    assert firms["FTMO_SWING_25K"]["fee_usd"] == 270.0

    b = _make_synthetic_bundle_v2("XAUUSD", n_days=25)
    d = b["days"][-1]
    res = replay_lab12_trade(b, d["fi"] + 8 * 60, d["flat_idx"], 1, 15.0)
    assert res is not None
    row, stamps, marks, _ = res
    dk = row["day"]
    t_news = int(stamps[0]) + 1800
    t1, t15, st = apply_red_news_and_15x_stress({dk: (row, stamps, marks)}, {dk: [(t_news, "USD")]})
    assert st["flattened_pre_news"] == 1
    assert t1[dk][0]["reason"] == "NEWS_PRE_FLATTEN"
    assert int(t1[dk][1][-1]) <= t_news - 300
    assert t15[dk][0]["net_usd_per_lot"] < t1[dk][0]["net_usd_per_lot"]


def test_lab12_receipt_schema_holdout_seal_and_md_parity():
    """Verify Holdout 2025+ seal, JSON+SHA256 cryptographic match, MD hygiene, and 16/16 + 12/12 verbatim parity."""
    assert ORDER_SEND_CAPABLE is False
    assert LAB12_JSON_PATH.exists(), f"Missing receipt JSON: {LAB12_JSON_PATH}"
    assert LAB12_SHA_PATH.exists(), f"Missing SHA-256 sidecar: {LAB12_SHA_PATH}"
    assert LAB12_MD_PATH.exists(), f"Missing report MD: {LAB12_MD_PATH}"
    assert HOLDOUT_LOCK_PATH.exists()

    for p in (LAB12_JSON_PATH, LAB12_MD_PATH, LAB12_SHA_PATH):
        assert p.stat().st_size < 900 * 1024, f"File exceeds 900 KB anti-bloat cap: {p}"
    expected_digest = hashlib.sha256(LAB12_JSON_PATH.read_bytes()).hexdigest()
    assert LAB12_SHA_PATH.read_text(encoding="utf-8").strip().startswith(expected_digest)

    d = json.loads(LAB12_JSON_PATH.read_text(encoding="utf-8"))
    lock_sha = hashlib.sha256(HOLDOUT_LOCK_PATH.read_bytes()).hexdigest()
    assert d["schema"] == "naqex-lab12-orthogonal-momentum-v2-v1"
    assert d["order_send_capable"] is False
    assert d["holdout_rows_analysed"] == 0
    assert d["holdout_lock_sha256"] == lock_sha
    assert d["dev_window"][1] <= "2024-12-31"
    assert d["m_total"] == 16 and len(d["candidates"]) == 16
    assert d["cumulative_lab11_plus_lab12_tested"] == 36
    assert d["mc_paths"] == 10_000 and d["mc_seed"] == 20261124

    for c in d["candidates"]:
        assert c["swap_usd_total"] == 0.0

    md = LAB12_MD_PATH.read_text(encoding="utf-8")
    assert md.startswith("---\n"), "Missing YAML frontmatter"
    assert "$" not in md, "Bare `$` found in Markdown prose/tables!"
    for _label, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", md):
        if target.startswith(("http://", "https://", "#")):
            continue
        resolved = (LAB12_MD_PATH.parent / target.split("#")[0]).resolve()
        assert resolved.exists(), f"Broken relative Markdown link: {target} -> {resolved}"

    # Exact 16-of-16 candidate table verbatim JSON-to-MD parity
    for c in d["candidates"]:
        a1, b1, b15 = c["cluster_a_1x"], c["cluster_b_1x"], c["cluster_b_15x"]
        fg = ", ".join(c["failed_gates"]) if c["failed_gates"] else "NONE"
        row_md = (
            f"| `{c['id']}` | {c['asset']} | {a1['n']} | {a1['pf']:.2f} | {b1['n']} | {b1['pf']:.2f} | "
            f"{b1['net_R']:+.2f} | {b15['ann_R']:+.2f} | {c['pos_years']}/7 | {c['max_yr_share_pct']:.1f}% | "
            f"{c['corr_vs_live8']:+.3f} | {c['max_single_inc_corr']:+.3f} | {c['p_signflip_b']:.4f} | "
            f"{c['p_bonf_b']:.4f} | {c['bh_q_b']:.4f} | {c['dsr_b']['dsr']:.3f} | `{c['verdict']}` | {fg} |"
        )
        assert row_md in md, f"Candidate table mismatch for {c['id']}:\n{row_md}"

    # Exact accretion & 10k MC parity across FTMO 10K, FTMO 25K, The5ers 5K
    for acc in d["accretion_comparison"]:
        m1, m15 = acc["m1_1x"], acc["m1_15x"]
        base_md = (
            f"| `{acc['portfolio_id']}` | {acc['n_engines']} | {m1['ann_pct']['all']:.2f}% | "
            f"{m1['sharpe_1x']:.2f} | {m1['peak_dd_pct']:.2f}% | {m1['calmar']:.2f} | "
            f"{m15['calmar']:.2f} | {acc['p1_symcap175_hits']} |"
        )
        assert base_md in md, f"Accretion base table mismatch:\n{base_md}"
        for fid in ("FTMO_SWING_10K", "FTMO_SWING_25K", "THE5ERS_HS_5K"):
            for pol in ("P1_Balanced_SymCap175", "Dyn_ProfitLock_SymCap175"):
                st = acc["prop_mc_10k"][fid][pol]
                mc_md = (
                    f"| `{acc['portfolio_id']}` | {fid} | `{pol}` | "
                    f"{st['pass_3m_pct']:.1f}% / {st['pass_6m_pct']:.1f}% / {st['pass_12m_pct']:.1f}% | "
                    f"{st['med_days_pass']}d | {st['breach_pct']:.1f}% | {st['wipeout_pct']:.2f}% | "
                    f"{st['ev_24m_usd']:+.1f} USD | {st['ev_per_fee']:.2f}x |"
                )
                assert mc_md in md, f"Accretion MC table mismatch:\n{mc_md}"
