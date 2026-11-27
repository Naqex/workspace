"""Offline synthetic + local_cache verification tests for Wave 4 Same-Feed MT5 Parity (`W4-G03`).

All checks use `_check(...)` (ZERO bare `assert` statements) so 100% of assertions
remain enforced under `python -O -m pytest` (`[ARCH-02]`).

Offline CI tests (`-m "not local_cache"`):
  - Static safety: LF-only, 0 BOM, 0 bare `assert`s, 0 `MetaTrader5` imports,
    0 `order_send` refs, `creationflags` on every `subprocess.run`, `ORDER_SEND_CAPABLE=False`.
  - Holdout `< 2025-01-01` fail-closed guards & forbidden Exness/Program Files path locks.
  - FTMO broker-day D1 aggregation (`NY+7` US DST `>= 2020` vs EU DST `<= 2019`),
    round-trip DST encoding/decoding, and exact MQL5 `iATR(14)` (`SMA(TR, 14)`).
  - Exact immutable `naqex_red_news_utc.csv` loader, `EST03UTC` +/-3600s expansion,
    +/-135s hard ban, and `RC-3` post-blackout re-entry (`1s` after +/-10m blackout).
  - Synthetic 8-symbol `simulate_v103_same_feed_m1` end-to-end test proving `RC-3`
    post-news re-entry and `RC-6` `NEWS_PRE_FLATTEN` `gross_R` sync.
  - `RC-4` / `RC-7`: `InpSizingMode=1` `BARRIER_TAPER`, directional cluster caps,
    MQL5 half-away-from-zero tick rounding, and `10K` vs `100K` `0.01`-lot drift math.

Local-cache test (`@pytest.mark.local_cache`):
  - Validates `.runtime/offensive4/audits/w4_t0_parity98_receipt.json` and
    `.tmp/swarm_dropbox/w4-t0-parity98.json` (`W4-G03 >= 98%` Same-Feed parity,
    `RC-1..RC-7` ledger with `RC-5 = SKIPPED_IN_TESTER`, `10K` vs `100K` drift,
    strictly separated `Model=4` Real-Tick Q4-2024 microstructure drift, `MT5_PROCS == 0`).
"""

from __future__ import annotations

import ast
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from quant_factory.wave4 import ftmo_m1_exporter as exp
from quant_factory.wave4 import same_feed_mt5_parity as sfp


def _check(condition: bool, message: str) -> None:
    """Assertion helper immune to `python -O` bytecode stripping."""
    if not condition:
        raise AssertionError(message)


def _make_preset_cfg(
    *,
    initial_balance_usd: float = 10_000.0,
    sizing_mode: int = 0,
    base_phase_mult: float = 1.0,
    target_profit_pct: float = 0.0,
    kill_daily_dd_pct: float = 2.5,
    kill_static_dd_pct: float = 8.0,
    max_total_open_risk_pct: float = 2.0,
    max_idx_cluster_pct: float = 1.0,
) -> sfp.PresetConfig:
    return sfp.PresetConfig(
        preset_name="synthetic.set",
        contract_sku="SYNTHETIC_TEST",
        initial_balance_usd=initial_balance_usd,
        target_profit_pct=target_profit_pct,
        hard_daily_dd_pct=5.0,
        hard_static_dd_pct=10.0,
        daily_reset_mode=1,
        sizing_mode=sizing_mode,
        base_phase_mult=base_phase_mult,
        profit_lock_pct=0.0,
        profit_lock_mult=base_phase_mult,
        amber_dd_pct=3.5,
        amber_mult=0.65,
        red_dd_pct=6.0,
        red_mult=0.40,
        kill_daily_dd_pct=kill_daily_dd_pct,
        kill_static_dd_pct=kill_static_dd_pct,
        max_total_open_risk_pct=max_total_open_risk_pct,
        hard_total_open_ceiling_pct=3.0,
        max_symbol_risk_pct=1.5,
        max_usd_cluster_pct=2.0,
        max_jpy_cluster_pct=2.0,
        max_idx_cluster_pct=max_idx_cluster_pct,
        enable_spread_guard=True,
        max_usdjpy_spread_pts=25.0,
        max_gbpusd_spread_pts=35.0,
        max_eurjpy_spread_pts=25.0,
        max_index_spread_pts=350.0,
        default_max_spread_pts=35.0,
        rollover_start_utc=21,
        rollover_end_utc=0,
        early_close_min=10,
        tester_utc_offset_h=2,
        enable_red_news=True,
        news_pad_sec=600,
        news_hard_ban_sec=135,
        profit_lock_basis_mode=0,
        post_close_refresh_mode=1,
        leverage=100,
    )


def test_static_safety_zero_bare_asserts_no_mt5_import_and_creationflags() -> None:
    """Verify LF, 0 BOM, 0 bare asserts (`[ARCH-02]`), 0 MetaTrader5 imports, and zero-popup subprocess calls."""
    src_path = Path(sfp.__file__).resolve()
    raw_bytes = src_path.read_bytes()
    _check(not raw_bytes.startswith(b"\xef\xbb\xbf"), "BOM detected in same_feed_mt5_parity.py")
    _check(b"\r\n" not in raw_bytes, "CRLF detected in same_feed_mt5_parity.py")

    tree = ast.parse(raw_bytes.decode("utf-8"), filename=str(src_path))
    bare_asserts = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    _check(not bare_asserts, f"Bare assert statement(s) forbidden under [ARCH-02]: lines {bare_asserts}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check(alias.name != "MetaTrader5", "MetaTrader5 import forbidden in same_feed_mt5_parity.py")
        elif isinstance(node, ast.ImportFrom):
            _check(node.module != "MetaTrader5", "MetaTrader5 from-import forbidden in same_feed_mt5_parity.py")
        elif isinstance(node, ast.Attribute):
            _check(node.attr != "order_send", "order_send forbidden in same_feed_mt5_parity.py")
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in ("run", "Popen")
        ):
            kw_names = {kw.arg for kw in node.keywords}
            _check(
                "creationflags" in kw_names,
                f"subprocess.{node.func.attr} at line {node.lineno} missing creationflags",
            )

    _check(sfp.ORDER_SEND_CAPABLE is False, "ORDER_SEND_CAPABLE must be False")
    _check(sfp.ORDER_SEND_COUNT == 0, "ORDER_SEND_COUNT must be 0")
    _check("MetaTrader5" not in sys.modules, "Importing same_feed_mt5_parity must NOT load MetaTrader5")


def test_holdout_and_mt5_safety_guards_fail_closed() -> None:
    """Reject post-2024 windows/bars, forbidden MT5 paths, and active MT5 processes under `python -O`."""
    with pytest.raises(exp.HoldoutViolationError):
        sfp.assert_dev_date_sealed("2025.01.01", "2024.01.02")
    with pytest.raises(exp.HoldoutViolationError):
        sfp.render_v103_tester_ini(
            set_filename="x.set", from_date="2024.01.02", to_date="2025.01.01", report_stem="r", deposit=10000
        )

    t_2025 = int(datetime(2025, 1, 1, 0, 0, tzinfo=UTC).timestamp())
    with pytest.raises(exp.HoldoutViolationError):
        sfp.build_broker_d1_from_m1(
            {
                "ts_utc": np.array([t_2025], dtype=np.int64),
                "open": np.array([150.0]),
                "high": np.array([150.1]),
                "low": np.array([149.9]),
                "close": np.array([150.0]),
            }
        )

    for bad_path in (
        r"C:\Program Files\MetaTrader 5",
        r"D:\x\D0E8209F77C8CF37AD8BF550E51FF075\terminal64.exe",
    ):
        with pytest.raises(exp.SafetyLockError):
            exp.assert_safe_portable_root(bad_path)

    with pytest.raises(exp.SafetyLockError):
        sfp.assert_zero_all_mt5_processes(lambda: ['"metatester64.exe","4321"'], context="unit")

    ini_txt = sfp.render_v103_tester_ini(
        set_filename="x.set", from_date="2024.01.02", to_date="2024.12.31", report_stem="r", deposit=100000
    )
    for tok in ("AllowLiveTrading=0", "Enabled=0", "KeepPrivate=1", "Model=1", "Deposit=100000", "ToDate=2024.12.31"):
        _check(tok in ini_txt, f"Missing required INI safety token {tok!r}")


def test_broker_day_d1_aggregation_ny_plus_7_dst_and_mql5_sma_atr() -> None:
    """Verify `RC-1` broker-day D1 midnight (`NY+7` >= 2020, EU <= 2019) & exact MQL5 `SMA(TR, 14)`."""
    dst_cases = [
        ("2019-03-14T12:00:00Z", 2),  # EU still winter (+2)
        ("2019-10-30T12:00:00Z", 2),  # EU already winter (+2)
        ("2020-03-11T12:00:00Z", 3),  # US NY+7 already summer (+3)
        ("2020-10-28T12:00:00Z", 3),  # US NY+7 still summer (+3)
        ("2024-01-10T22:00:00Z", 2),  # Winter broker midnight = 22:00 UTC -> next server day 00:00
        ("2024-07-10T21:00:00Z", 3),  # Summer broker midnight = 21:00 UTC -> next server day 00:00
        ("2024-11-06T12:00:00Z", 2),  # US back to EST (+2)
    ]
    utc_arr = np.array([int(datetime.fromisoformat(s).timestamp()) for s, _ in dst_cases], dtype=np.int64)
    srv_arr = sfp.encode_utc_to_ftmo_server_times(utc_arr)
    for idx, (_iso, exp_off) in enumerate(dst_cases):
        got_off = int(srv_arr[idx] - utc_arr[idx]) // 3600
        _check(got_off == exp_off, f"DST offset mismatch for {dst_cases[idx]}: got +{got_off}h")
        _check(sfp.ftmo_server_offset_hours_from_utc(int(utc_arr[idx])) == exp_off, "Scalar DST offset mismatch")
    decoded = exp.decode_ftmo_server_times_to_utc(srv_arr)
    _check(bool(np.array_equal(decoded, utc_arr)), "encode/decode FTMO DST round-trip mismatch")

    ts_list: list[int] = []
    op_list: list[float] = []
    hi_list: list[float] = []
    lo_list: list[float] = []
    cl_list: list[float] = []
    base_srv_day = int(datetime(2024, 7, 1, 0, 0, tzinfo=UTC).timestamp())
    for d in range(16):
        bar0_utc = base_srv_day + d * 86400 - 3 * 3600
        bar1_utc = bar0_utc + 12 * 3600
        rng = 1.0 + 0.1 * d
        px = 150.0 + 0.05 * d
        ts_list.extend([bar0_utc, bar1_utc])
        op_list.extend([px, px + 0.1])
        hi_list.extend([px + rng, px + 0.2])
        lo_list.extend([px, px])
        cl_list.extend([px + 0.1, px + 0.05])

    d1 = sfp.build_broker_d1_from_m1(
        {
            "ts_utc": np.array(ts_list, dtype=np.int64),
            "open": np.array(op_list),
            "high": np.array(hi_list),
            "low": np.array(lo_list),
            "close": np.array(cl_list),
        },
        atr_period=14,
    )
    _check(len(d1["d1_day_key"]) == 16, f"Expected 16 broker D1 bars, got {len(d1['d1_day_key'])}")
    expected_prior_atr14 = float(np.mean(d1["tr"][:14]))
    _check(
        abs(float(d1["prior_atr14"][14]) - expected_prior_atr14) < 1e-12,
        f"Causal SMA(TR,14) mismatch: {d1['prior_atr14'][14]} != {expected_prior_atr14}",
    )
    _check(np.isnan(d1["prior_atr14"][13]), "prior_atr14 must remain NaN before 14 completed prior days")


def test_red_news_csv_loader_and_post_blackout_reentry_rc2_rc3(tmp_path: Path) -> None:
    """Verify `RC-2` CSV loader (`EST03UTC`, currency matching) and `RC-3` 1s post-blackout re-entry."""
    nfp_ts = int(datetime(2024, 1, 5, 13, 30, 0, tzinfo=UTC).timestamp())
    boj_ts = int(datetime(2024, 1, 23, 3, 0, 0, tzinfo=UTC).timestamp())
    csv_path = tmp_path / "test_red_news.csv"
    csv_path.write_text(
        f"utc_ts,ccy,event\n{nfp_ts},USD,US_MACRO\n{boj_ts},JPY,BOJ_RATE_EST03UTC\n",
        encoding="utf-8",
        newline="\n",
    )
    events = sfp.load_mt5_red_news_csv(csv_path)
    _check(len(events) == 2, f"Expected 2 events, got {len(events)}")
    idx = sfp.RedNewsCalendarIndex(events, pad_sec=600, hard_ban_sec=135)

    _check(idx.is_inside_red_news_window("USDJPY", nfp_ts), "USDJPY must be blocked at NFP")
    _check(
        idx.is_inside_red_news_window("US100.cash", nfp_ts + 600),
        "US100.cash must be blocked at exact +600s boundary",
    )
    _check(
        not idx.is_inside_red_news_window("US100.cash", nfp_ts + 601),
        "RC-3: must unblock 1s after +/-10m blackout (+601s)",
    )
    _check(not idx.is_inside_red_news_window("EURJPY", nfp_ts), "EURJPY should NOT match USD event")

    _check(idx.is_in_pre_flatten_window("USDJPY", nfp_ts - 600), "Pre-flatten must trigger at exact -600s")
    _check(idx.is_in_pre_flatten_window("USDJPY", nfp_ts - 136), "Pre-flatten must trigger at -136s")
    _check(not idx.is_in_pre_flatten_window("USDJPY", nfp_ts - 135), "Pre-flatten must suppress inside +/-135s")
    _check(idx.is_inside_hard_ban("USDJPY", nfp_ts - 135), "Hard ban must be True at -135s")

    _check(idx.is_inside_red_news_window("EURJPY", boj_ts + 3599), "EST03UTC must expand to +/-3600s")
    _check(not idx.is_inside_red_news_window("EURJPY", boj_ts + 3601), "EST03UTC must clear at +3601s")

    empty_idx = sfp.RedNewsCalendarIndex([], pad_sec=600, hard_ban_sec=135)
    _check(empty_idx.is_inside_red_news_window("USDJPY", nfp_ts), "Empty calendar must fail-closed block")


def test_synthetic_end_to_end_post_news_reentry_and_preflatten_gross_r() -> None:
    """End-to-end synthetic 8-symbol `simulate_v103_same_feed_m1` proving `RC-3` re-entry & `RC-6` gross_R."""
    weekdays = [date(2024, 1, d) for d in range(1, 24) if date(2024, 1, d).weekday() < 5]
    ts_srv_list: list[int] = []
    uj_o: list[float] = []
    uj_h: list[float] = []
    uj_l: list[float] = []
    uj_c: list[float] = []
    uj_sp: list[int] = []

    event_early_utc = int(datetime(2024, 1, 22, 8, 30, 0, tzinfo=UTC).timestamp())
    event_nfp_utc = int(datetime(2024, 1, 22, 13, 30, 0, tzinfo=UTC).timestamp())

    for d in weekdays:
        d0_srv = int(datetime(d.year, d.month, d.day, 0, 0, tzinfo=UTC).timestamp())
        if d < date(2024, 1, 22):
            for m_off, (o, h, lo, c) in ((0, (145.0, 146.0, 145.0, 145.5)), (600, (145.5, 145.8, 145.2, 145.0))):
                ts_srv_list.append(d0_srv + m_off * 60)
                uj_o.append(o)
                uj_h.append(h)
                uj_l.append(lo)
                uj_c.append(c)
                uj_sp.append(4)
        elif d == date(2024, 1, 22):
            jan22_bars = [
                (2 * 60, 145.00, 145.20, 145.00, 145.10, 4),
                (5 * 60 + 10, 145.15, 145.25, 145.15, 145.24, 4),
                (10 * 60 + 20, 145.50, 145.52, 145.48, 145.50, 4),
                (15 * 60 + 30, 146.00, 146.15, 145.95, 146.10, 4),
                (15 * 60 + 40, 146.10, 146.18, 146.08, 146.12, 4),
                (22 * 60 + 55, 146.40, 146.42, 146.38, 146.40, 4),
            ]
            for m_off, o, h, lo, c, sp_v in jan22_bars:
                ts_srv_list.append(d0_srv + m_off * 60)
                uj_o.append(o)
                uj_h.append(h)
                uj_l.append(lo)
                uj_c.append(c)
                uj_sp.append(sp_v)

    ts_srv_arr = np.array(ts_srv_list, dtype=np.int64)
    ts_utc_arr = exp.decode_ftmo_server_times_to_utc(ts_srv_arr)

    bundle: dict[str, dict[str, Any]] = {}
    for sym in exp.PORT_7E_SYMBOLS:
        if sym == "USDJPY":
            o_a, h_a, l_a, c_a, sp_a = map(np.array, (uj_o, uj_h, uj_l, uj_c, uj_sp))
        else:
            if sym in ("GBPUSD", "EURUSD", "AUDUSD", "USDCAD"):
                base = 1.25
            elif sym == "EURJPY":
                base = 160.0
            else:
                base = 17000.0
            n = len(ts_srv_arr)
            o_a = np.full(n, base, dtype=np.float64)
            h_a = np.full(n, base + 0.0001, dtype=np.float64)
            l_a = np.full(n, base - 0.0001, dtype=np.float64)
            c_a = np.full(n, base, dtype=np.float64)
            sp_a = np.full(n, 4, dtype=np.int32)
        item = {
            "symbol": sym,
            "ts_utc": ts_utc_arr,
            "ts_server_raw": ts_srv_arr,
            "open": o_a.astype(np.float64),
            "high": h_a.astype(np.float64),
            "low": l_a.astype(np.float64),
            "close": c_a.astype(np.float64),
            "spread_pts": sp_a.astype(np.int32),
            "holdout_rows_analysed": 0,
        }
        item["d1"] = sfp.build_broker_d1_from_m1(item, atr_period=14)
        bundle[sym] = item

    cfg = _make_preset_cfg(initial_balance_usd=100_000.0)
    news_ev = [
        {"utc_ts": event_early_utc, "ccy": "USD", "label": "US_MACRO", "is_est03utc": False},
        {"utc_ts": event_nfp_utc, "ccy": "USD", "label": "US_MACRO", "is_est03utc": False},
    ]
    sim = sfp.simulate_v103_same_feed_m1(bundle, cfg, news_ev, from_date="2024.01.22", to_date="2024.01.23")
    pos = sim["positions"]
    _check(len(pos) == 2, f"Expected 2 synthetic trades (E1 pre-flattened + E2 re-entry), got {len(pos)}")

    e1 = next(p for p in pos if p["engine_id"] == "E1_USDJPY_TOKYO")
    e2 = next(p for p in pos if p["engine_id"] == "E2_USDJPY_EXP80")
    _check(e1["exit_reason"] == "NEWS_PRE_FLATTEN_6CCY", f"Expected NEWS_PRE_FLATTEN_6CCY, got {e1['exit_reason']}")
    expected_e1_r = (e1["exit_price"] - e1["entry_price"]) / e1["sl_dist"]
    _check(
        abs(e1["gross_R"] - expected_e1_r) < 1e-4,
        f"RC-6 gross_R not synced on NEWS_PRE_FLATTEN: {e1['gross_R']} != {expected_e1_r}",
    )
    _check(
        e2["entry_utc_ts"] == event_nfp_utc + 620,
        f"RC-3 post-blackout re-entry should fire at +620s, got diff={e2['entry_utc_ts'] - event_nfp_utc}s",
    )


def test_barrier_taper_and_10k_vs_100k_lot_rounding_drift_rc4_rc7() -> None:
    """Verify `RC-4`/`RC-7`: `BARRIER_TAPER`, MQL5 half-away-from-zero tick rounding, and `10K` vs `100K` drift."""
    cfg_sprint = _make_preset_cfg(
        initial_balance_usd=10_000.0,
        sizing_mode=1,
        base_phase_mult=4.50,
        target_profit_pct=10.0,
        kill_daily_dd_pct=4.25,
        kill_static_dd_pct=9.50,
        max_total_open_risk_pct=3.0,
        max_idx_cluster_pct=2.25,
    )
    m_normal, reg_normal = sfp.compute_phase_risk_multiplier(cfg_sprint, 0.0, 0.0, 6.0, 6.0)
    _check(abs(m_normal - 4.50) < 1e-9 and reg_normal == "NORMAL", f"Expected NORMAL 4.50, got {m_normal}/{reg_normal}")

    m_taper, reg_taper = sfp.compute_phase_risk_multiplier(cfg_sprint, 0.0, 0.0, 8.25, 8.25)
    _check(
        abs(m_taper - 2.25) < 1e-9 and reg_taper == "BARRIER_TAPER",
        f"Expected BARRIER_TAPER 2.25, got {m_taper}/{reg_taper}",
    )

    _check(sfp.normalize_price_to_tick(141.0975, 0.001, 3) == 141.098, "mql_round 141.0975 must round UP to 141.098")
    _check(
        sfp.normalize_price_to_tick(144.93450000000001, 0.001, 3) == 144.935,
        "mql_round 144.9345 must round UP to 144.935",
    )

    cmp = sfp.compare_10k_vs_100k_lot_rounding_drift(
        risk_pct=0.16, loss_per_lot_usd=500.0, balance_perturbation_frac=0.005
    )
    _check(cmp["10K"]["rounded_lots"] == 0.03, f"Expected 0.03 lots on 10K, got {cmp['10K']}")
    _check(cmp["100K"]["rounded_lots"] == 0.30, f"Expected 0.30 lots on 100K, got {cmp['100K']}")
    _check(
        not cmp["10K"]["one_step_within_2pct_gate"],
        "Single 0.01-lot step at 10K (0.03 lots = 33.3%) exceeds 2% gate",
    )
    _check(
        cmp["100K"]["one_step_001_rel_drift"] < cmp["10K"]["one_step_001_rel_drift"] / 5.0,
        "100K quantization drift must be ~10x smaller",
    )

    cmp_e2 = sfp.compare_10k_vs_100k_lot_rounding_drift(risk_pct=0.59, loss_per_lot_usd=400.0)
    _check(cmp_e2["100K"]["one_step_within_2pct_gate"], f"100K E2 one-step drift should be <= 2%: {cmp_e2['100K']}")
    _check(not cmp_e2["10K"]["one_step_within_2pct_gate"], f"10K E2 one-step drift should exceed 2%: {cmp_e2['10K']}")


@pytest.mark.local_cache
def test_local_cache_wave4_parity98_receipt_and_invariants() -> None:
    """Verify real Wave 4 Same-Feed MT5 Parity receipt (`W4-G03 >= 98%`, `RC-1..RC-7`, `MT5_PROCS == 0`)."""
    audit_path = sfp.DEFAULT_AUDIT_RECEIPT
    dropbox_path = sfp.DEFAULT_DROPBOX_RECEIPT
    _check(audit_path.is_file(), f"Missing parity receipt: {audit_path}")
    _check(dropbox_path.is_file(), f"Missing dropbox receipt: {dropbox_path}")
    _check(audit_path.read_bytes() == dropbox_path.read_bytes(), "Audit & dropbox receipts must be byte-identical")

    raw_bytes = audit_path.read_bytes()
    _check(not raw_bytes.startswith(b"\xef\xbb\xbf"), "BOM detected in receipt JSON")
    _check(b"\r\n" not in raw_bytes, "CRLF detected in receipt JSON")

    rec = json.loads(raw_bytes.decode("utf-8"))
    _check(rec.get("schema") == sfp.SCHEMA_RECEIPT, f"Unexpected receipt schema: {rec.get('schema')}")

    inv = rec["safety_invariants"]
    _check(inv["order_send_capable"] is False, "order_send_capable must be False")
    _check(inv["order_send_count"] == 0, "order_send_count must be 0")
    _check(inv["spend_vnd"] == 0, "spend_vnd must be 0")
    _check(inv["holdout_2025_plus_sealed"] is True, "holdout_2025_plus_sealed must be True")
    _check(inv["holdout_rows_analysed"] == 0, "holdout_rows_analysed must be 0")
    _check(inv["max_to_date"] <= "2024.12.31", f"max_to_date breached: {inv['max_to_date']}")
    _check(inv["mt5_processes_after"] == 0, f"MT5 processes not zero: {inv['mt5_processes_after']}")
    _check(inv["immutables_untouched"] is True, "Immutables must be untouched")
    _check(inv["private_vault_ex5_count"] == 0, "private_vault must have 0 .ex5 files")
    _check(inv["tracked_exports_ex5_count"] == 0, "tracked exports must have 0 .ex5 files")

    rc_ledger = rec["rc_closure_ledger"]
    for rc_id in ("RC-1", "RC-2", "RC-3", "RC-4", "RC-5", "RC-6", "RC-7"):
        _check(rc_id in rc_ledger, f"Missing {rc_id} in rc_closure_ledger")
    _check(
        rc_ledger["RC-5"]["status"] == "SKIPPED_IN_TESTER",
        f"RC-5 must be SKIPPED_IN_TESTER, got {rc_ledger['RC-5']}",
    )

    news_meta = rec["red_news_calendar"]
    _check(news_meta["total_events"] == 492, f"Expected 492 total red-news events, got {news_meta['total_events']}")
    _check(
        news_meta["dev_2018_2024_usd_events"] == 224,
        f"Expected 224 Dev USD events, got {news_meta['dev_2018_2024_usd_events']}",
    )

    m1_runs = rec["model1_same_feed_runs"]
    for req_run in (
        "Funded_1x_10K_2024_M1",
        "Sprint_Eval_10K_2024_M1",
        "Funded_1x_100K_2024_M1",
        "Sprint_Eval_100K_2024_M1",
        "Funded_1x_100K_2022_2024_M1",
    ):
        _check(req_run in m1_runs, f"Missing required Model=1 run {req_run}")
        gate_m = m1_runs[req_run]["reconciliation"]["strict_ops6_gate_60s"]["metrics"]
        _check(
            float(gate_m["trade_match_rate"]) >= 0.98,
            f"W4-G03 FAILED on {req_run}: trade_match_rate={gate_m['trade_match_rate']} < 0.98",
        )
        _check(int(gate_m["ghost_trades"]) == 0, f"Ghost trades detected on {req_run}: {gate_m['ghost_trades']}")
        _check(
            gate_m["gross_r_drift"] is not None and float(gate_m["gross_r_drift"]) <= 0.05,
            f"gross_r_drift > 0.05 on {req_run}: {gate_m['gross_r_drift']}",
        )

    m4_sep = rec["model4_realtick_microstructure_drift_separate"]
    _check(m4_sep["strictly_separated_from_model1"] is True, "Model=4 must be strictly separated from Model=1")
    _check("Funded_1x_10K_2024Q4_M4" in m4_sep["runs"], "Missing Funded_1x_10K_2024Q4_M4 in Model=4 report")
    _check("Sprint_Eval_10K_2024Q4_M4" in m4_sep["runs"], "Missing Sprint_Eval_10K_2024Q4_M4 in Model=4 report")
