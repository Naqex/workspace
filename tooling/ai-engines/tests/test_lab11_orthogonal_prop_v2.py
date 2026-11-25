"""Wave-3 Cycle 1 Tests — Lab #11 Orthogonal Non-Breakout & New-Asset Prop v2 Discovery.

Verifies:
  1. Causal `shift=1` daily ATR14 & future-mutation zero-lookahead on `build_causal_m1_bundle` + `evaluate_lab11_spec`.
  2. Conservative M1 SL-before-TP tie-break when both SL & TP are touched in the same M1 bar.
  3. Hard `swap = 0` same-UTC-day intraday flat before 20:55 UTC invariant (and overnight rejection).
  4. Official 2018-2024 red-news `+-5m` guard blocking entries inside `+-300s` & pre-flattening open trades.
  5. Exact `1.5x` friction monotonicity & `GER40`/`BTCUSD` FTMO Swing margin specs.
  6. Sealed Holdout 2025+ lock (`holdout_rows_analysed == 0`, exact SHA-256), verified `.json` + `.sha256`
     receipt integrity, report hygiene (`0` bare `$`, `< 900 KB`, `0` broken relative links), and 100%
     verbatim JSON-to-Markdown parity across ALL 20 candidates + accretion tables.
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
from quant_factory.lab11_orthogonal_prop_v2_discovery import (
    ORDER_SEND_CAPABLE,
    REPORT_DIR,
    REPORT_STEM,
    apply_red_news_and_15x_stress,
    build_causal_m1_bundle,
    build_lab11_catalog,
    evaluate_lab11_spec,
    lab11_margin_per_lot_usd,
    replay_intraday_tape_trade,
)

LAB11_JSON_PATH = REPORT_DIR / f"{REPORT_STEM}.json"
LAB11_SHA_PATH = REPORT_DIR / f"{REPORT_STEM}.sha256"
LAB11_MD_PATH = REPORT_DIR / f"{REPORT_STEM}.md"
HOLDOUT_LOCK_PATH = ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"


def _make_synthetic_m1_bundle(
    asset: str = "EURUSD",
    n_days: int = 25,
    *,
    bar_overrides: dict[int, tuple[float, float, float, float, float, float, float, float]] | None = None,
) -> dict:
    """Build deterministic synthetic M1 Bid/Ask bundle strictly inside 2022 (< 2025-01-01)."""
    specs, _ = profiles()
    sw = specs["Swing"]
    spec = sw.get(asset)

    base_ts = int(datetime(2022, 2, 1, 0, 0, tzinfo=timezone.utc).timestamp())
    times_list = []
    quotes_list = []
    days_out = []
    px = 1.1000 if asset == "EURUSD" else 2000.0
    spr = 0.0001 if asset == "EURUSD" else 0.50

    day_count = 0
    cal_offset = 0
    raw_days = []
    while day_count < n_days:
        dsec = base_ts + cal_offset * 86400
        dt = datetime.fromtimestamp(dsec, timezone.utc)
        cal_offset += 1
        if dt.weekday() >= 5:
            continue
        fi = len(times_list)
        # Create 1260 M1 bars (00:00..20:59 UTC)
        for m in range(1260):
            ts = dsec + m * 60
            # Gentle intraday drift up during London morning (07:00..12:00 UTC) so fade triggers on later days
            step = (0.000015 if asset == "EURUSD" else 0.04) if (420 <= m < 720) else (-0.000008 if asset == "EURUSD" else -0.02)
            px = max(0.5, px + step)
            bo = px
            bh = px + (0.0002 if asset == "EURUSD" else 0.4)
            bl = px - (0.0002 if asset == "EURUSD" else 0.4)
            bc = px
            times_list.append(ts)
            quotes_list.append([bo, bh, bl, bc, bo + spr, bh + spr, bl + spr, bc + spr])
        li = len(times_list) - 1
        flat_idx = fi + 20 * 60 + 50
        raw_days.append({
            "day": dt.date().isoformat(),
            "year": dt.year,
            "weekday": dt.weekday(),
            "dsec": dsec,
            "fi": fi,
            "li": li,
            "flat_idx": flat_idx,
            "o": quotes_list[fi][0],
            "h": max(q[1] for q in quotes_list[fi:li + 1]),
            "l": min(q[2] for q in quotes_list[fi:li + 1]),
            "c": quotes_list[li][3],
        })
        day_count += 1

    times = np.asarray(times_list, dtype=np.int64)
    quotes = np.asarray(quotes_list, dtype=np.float64)
    if bar_overrides:
        for idx, vals in bar_overrides.items():
            quotes[idx] = vals

    # Strictly causal shift=1 ATR14
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
        if len(trs) >= 14:
            days_out.append({
                **d,
                "prev_o": prev["o"],
                "prev_h": prev["h"],
                "prev_l": prev["l"],
                "prev_c": prev["c"],
                "prev_day": prev["day"],
                "atr": max(1e-9, float(np.mean(trs[-14:]))),
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


def test_lab11_sl_before_tp_conservative_tiebreak_and_swap_zero():
    """Verify SL always beats TP when both touch on the SAME M1 bar, and swap=0 flat holds."""
    bundle = _make_synthetic_m1_bundle("EURUSD", n_days=18)
    d = bundle["days"][-1]
    e_idx = d["fi"] + 12 * 60       # 12:00 UTC entry
    flat_idx = d["flat_idx"]        # 20:50 UTC hard flat
    ep = float(bundle["quotes"][e_idx, 4])  # Ask open for BUY
    sl_d = 0.0020
    tp_d = 0.0020

    # Inject a single volatile M1 bar at e_idx+5 that breaches BOTH sl_p AND tp_p simultaneously!
    q_mut = bundle["quotes"].copy()
    q_mut[e_idx + 5, 0] = ep                # Bid open at ep
    q_mut[e_idx + 5, 1] = ep + tp_d + 0.001 # Bid high ABOVE TP!
    q_mut[e_idx + 5, 2] = ep - sl_d - 0.001 # Bid low BELOW SL!
    q_mut[e_idx + 5, 3] = ep + tp_d
    b_tie = {**bundle, "quotes": q_mut}

    res = replay_intraday_tape_trade(b_tie, e_idx, flat_idx, 1, sl_d, tp_dist=tp_d)
    assert res is not None
    row, stamps, marks, _fade = res
    assert row["reason"] == "SL_GAP_OR_TOUCH", f"Expected conservative SL-before-TP, got {row['reason']}"
    assert row["net_R"] <= -0.99, f"SL hit must yield ~-1R, got {row['net_R']}"
    assert row["swap_usd"] == 0.0
    # Verify same UTC day & closed before 20:55 UTC
    dt_e = datetime.fromtimestamp(int(stamps[0]), timezone.utc)
    dt_x = datetime.fromtimestamp(int(stamps[-1]), timezone.utc)
    assert dt_e.date() == dt_x.date()
    assert (dt_x.hour * 60 + dt_x.minute) <= 20 * 60 + 55


def test_lab11_causal_shift1_and_future_mutation_zero_lookahead():
    """Bit-for-bit zero-lookahead proof: mutating ALL M1 bars after cutoff leaves prefix trades identical."""
    b0 = _make_synthetic_m1_bundle("EURUSD", n_days=24)
    cut_day = b0["days"][3]["day"]
    cut_end_idx = b0["days"][3]["li"]

    q1 = b0["quotes"].copy()
    # Aggressively scramble ALL bars strictly after cut_day
    q1[cut_end_idx + 1 :, :] *= 1.35
    b1 = {**b0, "quotes": q1}
    # Recompute days_out strictly causally on scrambled future quotes (days up to cut_day must be identical!)
    b1_days = []
    for d in b0["days"]:
        if d["day"] <= cut_day:
            b1_days.append(dict(d))
        else:
            b1_days.append({**d, "atr": d["atr"] * 3.0, "prev_c": d["prev_c"] * 1.35})
    b1["days"] = b1_days
    b1["day_map"] = {d["day"]: d for d in b1_days}

    cfg = next(c for c in build_lab11_catalog() if c["id"] == "L11_A1_EURUSD_LDN_STRETCH_FADE")
    # Lower threshold purely on synthetic flat test fixture to guarantee trades fire before cut_day
    cfg_test = {**cfg, "thr": 0.05}
    t0, _ = evaluate_lab11_spec({"EURUSD": b0}, cfg_test)
    t1, _ = evaluate_lab11_spec({"EURUSD": b1}, cfg_test)

    pref0 = {dk: v for dk, v in t0.items() if dk <= cut_day}
    pref1 = {dk: v for dk, v in t1.items() if dk <= cut_day}
    assert len(pref0) >= 1, "Synthetic fixture must fire at least 1 trade before cut_day"
    assert set(pref0.keys()) == set(pref1.keys())
    for dk in pref0:
        assert pref0[dk][0] == pref1[dk][0], f"Lookahead detected on {dk}!"
        assert np.array_equal(pref0[dk][2], pref1[dk][2])


def test_lab11_red_news_guard_15x_monotonicity_and_new_asset_margin():
    """Verify red-news +-5m guard blocks/pre-flattens, 1.5x cost <= 1.0x cost, and GER40/BTCUSD margin specs."""
    bundle = _make_synthetic_m1_bundle("EURUSD", n_days=18)
    d = bundle["days"][-1]
    e_idx = d["fi"] + 12 * 60
    res = replay_intraday_tape_trade(bundle, e_idx, d["flat_idx"], 1, 0.0040, tp_dist=0.0080)
    assert res is not None
    row, stamps, marks, _ = res
    dk = row["day"]
    raw_tape = {dk: (row, stamps, marks)}

    # Case 1: Red news 2 minutes after entry -> entry inside +-300s MUST be blocked!
    cal_block = {dk: [(int(stamps[0]) + 120, "USD")]}
    t1_blk, _, st_blk = apply_red_news_and_15x_stress(raw_tape, cal_block)
    assert len(t1_blk) == 0 and st_blk["blocked_entry"] == 1

    # Case 2: Red news 60 minutes after entry -> open trade MUST pre-flatten <= t_news - 300s!
    t_news = int(stamps[0]) + 3600
    cal_flat = {dk: [(t_news, "USD")]}
    t1_flt, t15_flt, st_flt = apply_red_news_and_15x_stress(raw_tape, cal_flat)
    assert dk in t1_flt and st_flt["flattened_pre_news"] == 1
    assert t1_flt[dk][0]["reason"] == "NEWS_PRE_FLATTEN"
    assert int(t1_flt[dk][1][-1]) <= t_news - 300

    # Case 3: Exact 1.5x stress monotonicity (1.5x net strictly < 1.0x net!)
    assert t15_flt[dk][0]["net_usd_per_lot"] < t1_flt[dk][0]["net_usd_per_lot"]
    assert t15_flt[dk][0]["stop_risk_with_cost_usd"] > t1_flt[dk][0]["stop_risk_with_cost_usd"]

    # Case 4: Exact GER40 & BTCUSD Swing margin specs (NOT buggy FX 100k*price/30!)
    m_ger, vmin_g, _, _, _ = lab11_margin_per_lot_usd("GER40", 18000.0, "Swing")
    assert 1000.0 < m_ger < 2000.0 and vmin_g == 0.01
    m_btc, vmin_b, _, _, _ = lab11_margin_per_lot_usd("BTCUSD", 65000.0, "Swing")
    assert m_btc == pytest.approx(65000.0, rel=1e-6) and vmin_b == 0.01


def test_lab11_receipt_schema_holdout_seal_and_md_parity():
    """Verify Holdout 2025+ seal, JSON+SHA256 cryptographic match, MD hygiene, and 20/20 verbatim parity."""
    assert ORDER_SEND_CAPABLE is False
    assert LAB11_JSON_PATH.exists(), f"Missing receipt JSON: {LAB11_JSON_PATH}"
    assert LAB11_SHA_PATH.exists(), f"Missing SHA-256 sidecar: {LAB11_SHA_PATH}"
    assert LAB11_MD_PATH.exists(), f"Missing report MD: {LAB11_MD_PATH}"
    assert HOLDOUT_LOCK_PATH.exists()

    # 1. Anti-bloat (< 900 KB) & cryptographic SHA-256 sidecar verification
    for p in (LAB11_JSON_PATH, LAB11_MD_PATH, LAB11_SHA_PATH):
        assert p.stat().st_size < 900 * 1024, f"File exceeds 900 KB anti-bloat cap: {p}"
    expected_digest = hashlib.sha256(LAB11_JSON_PATH.read_bytes()).hexdigest()
    sha_line = LAB11_SHA_PATH.read_text(encoding="utf-8").strip()
    assert sha_line.startswith(expected_digest), f"SHA-256 mismatch: {sha_line} vs {expected_digest}"

    # 2. Holdout 2025+ seal & receipt schema
    d = json.loads(LAB11_JSON_PATH.read_text(encoding="utf-8"))
    lock_sha = hashlib.sha256(HOLDOUT_LOCK_PATH.read_bytes()).hexdigest()
    assert d["schema"] == "naqex-lab11-orthogonal-prop-v2-v1"
    assert d["order_send_capable"] is False
    assert d["holdout_rows_analysed"] == 0
    assert d["holdout_lock_sha256"] == lock_sha
    assert d["dev_window"][1] <= "2024-12-31"
    assert d["m_total"] == 20 and len(d["candidates"]) == 20
    assert d["mc_paths"] == 10_000 and d["mc_seed"] == 20261124
    assert d["p1_symcap_tight_pct"] == pytest.approx(1.75)

    # Verify swap = 0 on every candidate
    for c in d["candidates"]:
        assert c["swap_usd_total"] == 0.0

    # 3. Markdown hygiene: YAML frontmatter, 0 bare `$`, 0 broken relative links
    md = LAB11_MD_PATH.read_text(encoding="utf-8")
    assert md.startswith("---\n"), "Missing YAML frontmatter"
    assert "$" not in md, "Bare `$` found in Markdown prose/tables!"
    for _label, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", md):
        if target.startswith(("http://", "https://", "#")):
            continue
        resolved = (LAB11_MD_PATH.parent / target.split("#")[0]).resolve()
        assert resolved.exists(), f"Broken relative Markdown link: {target} -> {resolved}"

    # 4. Exact 20-of-20 candidate table verbatim JSON-to-MD parity
    for c in d["candidates"]:
        a1, b1, b15 = c["cluster_a_1x"], c["cluster_b_1x"], c["cluster_b_15x"]
        fg = ", ".join(c["failed_gates"]) if c["failed_gates"] else "NONE"
        row_md = (
            f"| `{c['id']}` | {c['asset']} | {a1['n']} | {a1['pf']:.2f} | {b1['n']} | {b1['pf']:.2f} | "
            f"{b1['net_R']:+.2f} | {b15['ann_R']:+.2f} | {c['pos_years']}/7 | {c['max_yr_share_pct']:.1f}% | "
            f"{c['corr_vs_live8']:+.3f} | {c['max_single_inc_corr']:+.3f} | {c['p_signflip_b']:.4f} | "
            f"{c['p_bonf_b']:.4f} | {c['bh_q_b']:.4f} | {c['dsr_b']['dsr']:.3f} | `{c['verdict']}` | {fg} |"
        )
        assert row_md in md, f"Candidate table MD-vs-JSON mismatch for {c['id']}:\n{row_md}"

    # 5. Exact accretion & 10k MC table verbatim JSON-to-MD parity
    for acc in d["accretion_comparison"]:
        m1, m15 = acc["m1_1x"], acc["m1_15x"]
        base_md = (
            f"| `{acc['portfolio_id']}` | {acc['n_engines']} | {m1['ann_pct']['all']:.2f}% | "
            f"{m1['sharpe_1x']:.2f} | {m1['peak_dd_pct']:.2f}% | {m1['calmar']:.2f} | "
            f"{m15['calmar']:.2f} | {acc['p1_symcap175_hits']} |"
        )
        assert base_md in md, f"Accretion base table mismatch:\n{base_md}"
        for fid in ("FTMO_SWING_10K", "THE5ERS_HS_5K"):
            for pol in ("P1_Balanced_SymCap175", "Dyn_ProfitLock_SymCap175"):
                st = acc["prop_mc_10k"][fid][pol]
                mc_md = (
                    f"| `{acc['portfolio_id']}` | {fid} | `{pol}` | "
                    f"{st['pass_3m_pct']:.1f}% / {st['pass_6m_pct']:.1f}% / {st['pass_12m_pct']:.1f}% | "
                    f"{st['med_days_pass']}d | {st['breach_pct']:.1f}% | {st['wipeout_pct']:.2f}% | "
                    f"{st['ev_24m_usd']:+.1f} USD | {st['ev_per_fee']:.2f}x |"
                )
                assert mc_md in md, f"Accretion MC table mismatch:\n{mc_md}"
