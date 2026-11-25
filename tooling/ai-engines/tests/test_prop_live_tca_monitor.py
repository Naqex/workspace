"""Unit tests for `quant_factory/prop_live_tca_monitor.py` (OrderSend=0, Holdout=0, OPSEC-safe)."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import numpy as np
import pytest

TESTS_DIR = Path(__file__).resolve().parent
AI_ENGINES_DIR = TESTS_DIR.parent
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_factory import prop_live_tca_monitor as tca_mon  # noqa: E402


FILLS_HEADER = (
    "utc_ts,utc_iso,session,account_login,server,trade_seq,position_id,order_id,deal_id,"
    "symbol,leg,side,position_side,exit_reason,volume,pre_bid,pre_ask,pre_spread_pts,"
    "pre_spread_bps,expected_price,fill_price,sl_price,adverse_slip_pts,adverse_slip_bps,"
    "latency_ms,commission_usd,commission_bps,swap_usd,pnl_usd,retcode,dry_run,comment"
)


def _make_fill_row(
    *,
    utc_ts: int,
    symbol: str,
    leg: str,
    side: str,
    trade_seq: int,
    pos_id: int,
    pre_spread_pts: float,
    pre_spread_bps: float,
    adv_slip_pts: float,
    adv_slip_bps: float,
    comm_bps: float = 0.25,
    latency_ms: float = 350.0,
    swap_usd: float = 0.0,
    retcode: int = 10009,
    dry_run: bool = False,
    login: int = 9876543210,
    comment: str = "CAL_PROBE",
) -> str:
    return (
        f"{utc_ts},2026-11-25T11:00:00+00:00,LONDON,{login},FTMO-Demo,{trade_seq},"
        f"{pos_id},{pos_id + 1},{pos_id + 2},{symbol},{leg},{side},{side},"
        f"{'TIME_EXIT' if leg == 'EXIT' else ''},0.01,100.0,100.01,{pre_spread_pts},"
        f"{pre_spread_bps},100.01,100.01,99.5,{adv_slip_pts},{adv_slip_bps},"
        f"{latency_ms},-0.03,{comm_bps},{swap_usd},0.05,{retcode},{dry_run},{comment}"
    )


def _write_clean_calibration_csv(path: Path) -> None:
    rows = [FILLS_HEADER]
    base_ts = 1795603200
    specs = [
        ("USDJPY", 4.0, 0.25, 0.30, 1.0, 0.06),
        ("GBPUSD", 4.0, 0.30, 0.23, 0.5, 0.04),
        ("EURJPY", 8.0, 0.45, 0.27, 1.0, 0.06),
        ("US100.cash", 195.0, 0.76, 0.0, 30.0, 0.12),
    ]
    seq = 1
    for rep in range(4):
        for sym, sp_pts, sp_bps, comm_bps, slip_pts, slip_bps in specs:
            pos_id = 592000000 + seq * 10
            rows.append(
                _make_fill_row(
                    utc_ts=base_ts + seq * 120,
                    symbol=sym,
                    leg="ENTRY",
                    side="BUY",
                    trade_seq=seq,
                    pos_id=pos_id,
                    pre_spread_pts=sp_pts,
                    pre_spread_bps=sp_bps,
                    adv_slip_pts=slip_pts,
                    adv_slip_bps=slip_bps,
                    comm_bps=comm_bps,
                )
            )
            rows.append(
                _make_fill_row(
                    utc_ts=base_ts + seq * 120 + 60,
                    symbol=sym,
                    leg="EXIT",
                    side="SELL",
                    trade_seq=seq,
                    pos_id=pos_id,
                    pre_spread_pts=sp_pts,
                    pre_spread_bps=sp_bps,
                    adv_slip_pts=slip_pts * 0.5,
                    adv_slip_bps=slip_bps * 0.5,
                    comm_bps=comm_bps,
                )
            )
            seq += 1
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_clean_healthy_pass_and_bootstrap_ci_coverage(tmp_path: Path) -> None:
    """Clean calibration stream yields GREEN_HEALTHY, OrderSend=0, Holdout=0, and valid 10k bootstrap CI."""
    csv_p = tmp_path / "ftmo_calibration_fills_9876543210.csv"
    _write_clean_calibration_csv(csv_p)

    rep = tca_mon.evaluate_live_tca(
        fills_csv_paths=[csv_p],
        use_hot_cache=False,
        n_bootstrap_draws=10_000,
        seed=20261125,
    )
    assert rep["readonly"] is True
    assert rep["order_send_capable"] is False
    assert rep["order_send_count"] == 0
    assert rep["holdout_rows_analysed"] == 0
    assert rep["verdict"] == "GREEN_HEALTHY"
    assert rep["cusum_overall"]["alert"] is False
    assert rep["tail_slip_outliers"] == []
    assert rep["inputs"]["live_fill_legs_analysed"] == 32

    ci = rep["portfolio"]["stratified_friction_multiplier_95ci"]
    assert ci["n_draws"] == 10_000
    assert ci["active_symbols"] == 4
    assert 0.0 < ci["ci_lo"] <= ci["median"] <= ci["ci_hi"] < 1.5
    assert ci["ci_lo"] <= ci["mean"] <= ci["ci_hi"]

    # Deterministic reproducibility check
    rep2 = tca_mon.evaluate_live_tca(
        fills_csv_paths=[csv_p],
        use_hot_cache=False,
        n_bootstrap_draws=10_000,
        seed=20261125,
    )
    assert rep2["portfolio"]["stratified_friction_multiplier_95ci"] == ci

    # Direct statistical coverage sanity on synthetic known-mean sample
    rng = np.random.default_rng(42)
    sample = rng.normal(loc=1.10, scale=0.15, size=60)
    boot = tca_mon.bootstrap_mean_ci(sample, n_draws=10_000, seed=20261125)
    assert boot["ci_lo"] < float(np.mean(sample)) < boot["ci_hi"]
    assert boot["ci_lo"] <= 1.15 and boot["ci_hi"] >= 1.05


def test_injected_slippage_regime_shift_triggers_pages_cusum(tmp_path: Path) -> None:
    """Sustained upward slippage shift triggers Page's CUSUM RED_CUSUM_DRIFT_ALERT with changepoint."""
    csv_p = tmp_path / "fills_regime_shift.csv"
    rows = [FILLS_HEADER]
    base_ts = 1795605000
    # 8 clean USDJPY fills (4 round-trips) with 0 slippage
    for i in range(1, 5):
        pos_id = 593000000 + i
        rows.append(
            _make_fill_row(
                utc_ts=base_ts + i * 100,
                symbol="USDJPY",
                leg="ENTRY",
                side="BUY",
                trade_seq=i,
                pos_id=pos_id,
                pre_spread_pts=4.0,
                pre_spread_bps=0.25,
                adv_slip_pts=0.0,
                adv_slip_bps=0.0,
                comm_bps=0.30,
            )
        )
        rows.append(
            _make_fill_row(
                utc_ts=base_ts + i * 100 + 30,
                symbol="USDJPY",
                leg="EXIT",
                side="SELL",
                trade_seq=i,
                pos_id=pos_id,
                pre_spread_pts=4.0,
                pre_spread_bps=0.25,
                adv_slip_pts=0.0,
                adv_slip_bps=0.0,
                comm_bps=0.30,
            )
        )
    # Regime shift starts at fill index 8: +8 pts (~0.55 bps, >3x one-way base) on 6 consecutive legs
    for i in range(5, 8):
        pos_id = 593000000 + i
        rows.append(
            _make_fill_row(
                utc_ts=base_ts + i * 100,
                symbol="USDJPY",
                leg="ENTRY",
                side="BUY",
                trade_seq=i,
                pos_id=pos_id,
                pre_spread_pts=5.0,
                pre_spread_bps=0.31,
                adv_slip_pts=8.5,
                adv_slip_bps=0.55,
                comm_bps=0.30,
            )
        )
        rows.append(
            _make_fill_row(
                utc_ts=base_ts + i * 100 + 30,
                symbol="USDJPY",
                leg="EXIT",
                side="SELL",
                trade_seq=i,
                pos_id=pos_id,
                pre_spread_pts=5.0,
                pre_spread_bps=0.31,
                adv_slip_pts=9.0,
                adv_slip_bps=0.58,
                comm_bps=0.30,
            )
        )
    csv_p.write_text("\n".join(rows) + "\n", encoding="utf-8")

    rep = tca_mon.evaluate_live_tca(
        fills_csv_paths=[csv_p],
        use_hot_cache=False,
        n_bootstrap_draws=2000,
        cusum_k=0.5,
        cusum_h=4.0,
    )
    assert rep["verdict"] == "RED_CUSUM_DRIFT_ALERT"
    assert rep["cusum_overall"]["alert"] is True
    assert rep["cusum_overall"]["active_breach"] is True
    assert rep["cusum_overall"]["max_stat"] >= 4.0
    assert rep["cusum_overall"]["estimated_changepoint_index"] == 8
    assert rep["cusum_overall"]["first_breach_index"] >= 9
    assert rep["per_symbol"]["USDJPY"]["cusum"]["alert"] is True
    assert rep["per_symbol"]["USDJPY"]["status"] == "RED_CUSUM_DRIFT"
    assert tca_mon.exit_code_for_report(rep) == 2


def test_us100_tail_slip_outlier_and_symbol_alias_normalization(tmp_path: Path) -> None:
    """Aliases (`USDJPY.pro`, `GBPUSDm`, `EURJPY+`, `NAS100`) normalize cleanly & flag US100 tail spikes."""
    csv_p = tmp_path / "fills_aliases.csv"
    rows = [
        FILLS_HEADER,
        _make_fill_row(
            utc_ts=1795606000,
            symbol="USDJPY.pro",
            leg="ENTRY",
            side="BUY",
            trade_seq=1,
            pos_id=594000001,
            pre_spread_pts=3.0,
            pre_spread_bps=0.19,
            adv_slip_pts=0.0,
            adv_slip_bps=0.0,
            comm_bps=0.30,
        ),
        _make_fill_row(
            utc_ts=1795606060,
            symbol="USDJPY.pro",
            leg="EXIT",
            side="SELL",
            trade_seq=1,
            pos_id=594000001,
            pre_spread_pts=4.0,
            pre_spread_bps=0.25,
            adv_slip_pts=1.0,
            adv_slip_bps=0.06,
            comm_bps=0.30,
        ),
        _make_fill_row(
            utc_ts=1795606120,
            symbol="GBPUSDm",
            leg="ENTRY",
            side="BUY",
            trade_seq=2,
            pos_id=594000002,
            pre_spread_pts=4.0,
            pre_spread_bps=0.31,
            adv_slip_pts=0.0,
            adv_slip_bps=0.0,
            comm_bps=0.23,
        ),
        _make_fill_row(
            utc_ts=1795606180,
            symbol="GBPUSDm",
            leg="EXIT",
            side="SELL",
            trade_seq=2,
            pos_id=594000002,
            pre_spread_pts=4.0,
            pre_spread_bps=0.31,
            adv_slip_pts=0.0,
            adv_slip_bps=0.0,
            comm_bps=0.23,
        ),
        _make_fill_row(
            utc_ts=1795606240,
            symbol="EURJPY+",
            leg="ENTRY",
            side="SELL",
            trade_seq=3,
            pos_id=594000003,
            pre_spread_pts=8.0,
            pre_spread_bps=0.46,
            adv_slip_pts=2.0,
            adv_slip_bps=0.11,
            comm_bps=0.27,
        ),
        _make_fill_row(
            utc_ts=1795606300,
            symbol="EURJPY+",
            leg="EXIT",
            side="BUY",
            trade_seq=3,
            pos_id=594000003,
            pre_spread_pts=8.0,
            pre_spread_bps=0.46,
            adv_slip_pts=0.0,
            adv_slip_bps=0.0,
            comm_bps=0.27,
        ),
        # NAS100 alias -> US100.cash with single-fill +330 pts adverse slip (>150 pt V101-06 limit!)
        _make_fill_row(
            utc_ts=1795606360,
            symbol="NAS100",
            leg="ENTRY",
            side="SELL",
            trade_seq=4,
            pos_id=594000004,
            pre_spread_pts=195.0,
            pre_spread_bps=0.76,
            adv_slip_pts=-80.0,
            adv_slip_bps=-0.31,
            comm_bps=0.0,
        ),
        _make_fill_row(
            utc_ts=1795606420,
            symbol="USTEC.pro",
            leg="EXIT",
            side="BUY",
            trade_seq=4,
            pos_id=594000004,
            pre_spread_pts=195.0,
            pre_spread_bps=0.76,
            adv_slip_pts=330.0,
            adv_slip_bps=1.29,
            comm_bps=0.0,
        ),
    ]
    csv_p.write_text("\n".join(rows) + "\n", encoding="utf-8")

    assert tca_mon.normalize_tca_symbol("USDJPY.pro") == "USDJPY"
    assert tca_mon.normalize_tca_symbol("GBPUSDm") == "GBPUSD"
    assert tca_mon.normalize_tca_symbol("EURJPY+") == "EURJPY"
    assert tca_mon.normalize_tca_symbol("NAS100") == "US100.cash"
    assert tca_mon.normalize_tca_symbol("USTEC.pro") == "US100.cash"

    rep = tca_mon.evaluate_live_tca(
        fills_csv_paths=[csv_p],
        use_hot_cache=False,
        n_bootstrap_draws=2000,
    )
    assert rep["verdict"] == "AMBER_TAIL_SLIP_OUTLIER"
    assert rep["cusum_overall"]["alert"] is False
    assert rep["per_symbol"]["USDJPY"]["paired_roundtrips"] == 1
    assert rep["per_symbol"]["GBPUSD"]["paired_roundtrips"] == 1
    assert rep["per_symbol"]["EURJPY"]["paired_roundtrips"] == 1
    assert rep["per_symbol"]["US100.cash"]["paired_roundtrips"] == 1
    assert len(rep["tail_slip_outliers"]) == 1
    out0 = rep["tail_slip_outliers"][0]
    assert out0["symbol"] == "US100.cash"
    assert out0["adverse_slip_pts"] == 330.0
    assert out0["deviation_limit_pts"] == 150.0
    assert out0["severity"] == "CRITICAL_DEVIATION_BREACH"
    assert rep["per_symbol"]["US100.cash"]["recommended_deviation_pts_if_breached"] >= 380.0
    # Default exit code 0 for advisory AMBER, 2 when --strict-alerts
    assert tca_mon.exit_code_for_report(rep, strict_alerts=False) == 0
    assert tca_mon.exit_code_for_report(rep, strict_alerts=True) == 2


def test_opsec_redaction_and_timestamp_preservation(tmp_path: Path) -> None:
    """Verify ZERO leaks of logins, tickets, IPv4/IPv6, URLs, secrets, or bare `$`, keeping HH:MM:SS."""
    dirty = (
        "time=2026-11-25T13:15:35+00:00 login=9876543210 ticket=592241541 "
        "ip4=198.51.100.42 ip6=2001:db8:85a3::8a2e:370:7334 "
        "url=https://broker.example.test/token password=SyntheticSecret99 "
        "cost=$12.50 file=ftmo_calibration_fills_9876543210.csv other=9876543211"
    )
    clean = tca_mon.sanitize_text(dirty)
    assert "13:15:35" in clean  # HH:MM:SS timestamp MUST survive IPv6 redaction!
    assert "9876543210" not in clean
    assert "9876543211" not in clean
    assert "592241541" not in clean
    assert "198.51.100.42" not in clean
    assert "2001:db8" not in clean
    assert "https://" not in clean
    assert "SyntheticSecret99" not in clean
    assert "$" not in clean
    assert "USD12.50" in clean

    # Verify full end-to-end JSON + Vietnamese rendering contains ZERO sensitive identifiers
    csv_p = tmp_path / "ftmo_calibration_fills_9876543210.csv"
    _write_clean_calibration_csv(csv_p)
    rep = tca_mon.evaluate_live_tca(fills_csv_paths=[csv_p], use_hot_cache=False, n_bootstrap_draws=1000)
    raw_json = json.dumps(rep, ensure_ascii=False)
    vi_text = tca_mon.render_tca_monitor_vi(rep)
    for blob in (raw_json, vi_text):
        assert "9876543210" not in blob
        assert "9876543211" not in blob
        assert "592000" not in blob
        assert "$" not in blob
        assert re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", blob) is None


def test_partial_lines_missing_files_and_exec_audit_ingestion(tmp_path: Path) -> None:
    """Concurrent-append truncated CSV/JSONL rows & missing files are handled gracefully."""
    # 1. Missing files -> NO_DATA without crashing
    rep_empty = tca_mon.evaluate_live_tca(
        fills_csv_paths=[tmp_path / "does_not_exist.csv"],
        spread_jsonl_path=tmp_path / "no_spread.jsonl",
        audit_csv_paths=[tmp_path / "no_audit.csv"],
        use_hot_cache=False,
    )
    assert rep_empty["verdict"] == "NO_DATA"
    assert len(rep_empty["inputs"]["missing_files"]) == 2
    assert tca_mon.exit_code_for_report(rep_empty) == 0

    # 2. Truncated trailing lines + dry_run + reject + exec_audit CSV
    csv_p = tmp_path / "fills_partial.csv"
    csv_p.write_text(
        "\n".join([
            FILLS_HEADER,
            _make_fill_row(
                utc_ts=1795607000, symbol="USDJPY", leg="ENTRY", side="BUY",
                trade_seq=1, pos_id=595000001, pre_spread_pts=4.0, pre_spread_bps=0.25,
                adv_slip_pts=0.0, adv_slip_bps=0.0, dry_run=True,
            ),
            _make_fill_row(
                utc_ts=1795607020, symbol="USDJPY", leg="ENTRY_REJECT", side="BUY",
                trade_seq=2, pos_id=595000002, pre_spread_pts=4.0, pre_spread_bps=0.25,
                adv_slip_pts=0.0, adv_slip_bps=0.0, retcode=10004,
            ),
            # Mid-write truncated trailing CSV line
            "1795607050,2026-11-25T11:10:50+00:00,LONDON,9876543210,FTMO-Demo,3",
        ]) + "\n",
        encoding="utf-8",
    )

    spread_p = tmp_path / "mt5_live_spread_log.jsonl"
    valid_sp = json.dumps({
        "captured_utc_ts": 1795607100,
        "session": "LONDON",
        "account": {"login": 9876543210},
        "quotes": {
            "USDJPY": {"available": True, "bid": 159.200, "ask": 159.204, "spread_pts": 4.0, "point": 0.001},
            "NAS100": {"available": True, "bid": 25500.0, "ask": 25501.95, "spread_pts": 195.0, "point": 0.01},
        },
    })
    spread_p.write_text(valid_sp + "\n{\"captured_utc_ts\": 1795607105, \"quotes\": {\"USD", encoding="utf-8")

    audit_p = tmp_path / "naqex_exec_audit_test.csv"
    audit_p.write_text(
        "\n".join([
            "utc_ts,magic,symbol,side,event_type,signal_price,fill_price,sl_price,lots,spread_pts,latency_ms,retcode,comment,swap_usd",
            "1795607200,20261122,USDJPY.pro,BUY,ORDER_FILL,159.200,159.201,159.050,0.01,4.0,210.0,10009,pos=888001,0.0",
            "1795607500,20261122,USDJPY.pro,SELL,POSITION_CLOSE,159.250,159.249,159.050,0.01,4.0,190.0,10009,tk=888002|pos=888001,0.0",
            "1795607600,20261122,USDJPY.pro,BUY,ORDER_FILL,159.25",  # truncated line
        ]) + "\n",
        encoding="utf-8",
    )

    rep = tca_mon.evaluate_live_tca(
        fills_csv_paths=[csv_p],
        spread_jsonl_path=spread_p,
        audit_csv_paths=[audit_p],
        use_hot_cache=False,
        n_bootstrap_draws=1000,
    )
    assert rep["inputs"]["dryrun_rows_ignored"] == 1
    assert rep["inputs"]["rejected_orders"] == 1
    assert rep["inputs"]["malformed_or_partial_rows_skipped"] == 2
    assert rep["inputs"]["spread_log_rows_parsed"] == 1
    assert rep["inputs"]["spread_log_partial_lines_skipped"] == 1
    assert rep["inputs"]["live_fill_legs_analysed"] == 2
    assert rep["per_symbol"]["USDJPY"]["live_spread_samples"] == 1
    assert rep["per_symbol"]["US100.cash"]["live_spread_samples"] == 1
    assert rep["verdict"] == "GREEN_HEALTHY"


def test_holdout_contamination_guard_and_swap_violation_fail_closed(tmp_path: Path) -> None:
    """Holdout rows > 0 raises RuntimeError; non-zero swap triggers RED_FRICTION_BREACH."""
    bad_base = json.loads(json.dumps(tca_mon.STATIC_DEV_M1_BASELINES_PRE2025))
    bad_base["holdout_rows_analysed"] = 1
    with pytest.raises(RuntimeError, match="HOLDOUT_CONTAMINATION_DETECTED"):
        tca_mon.evaluate_live_tca(dev_baselines=bad_base)

    csv_p = tmp_path / "fills_swap.csv"
    csv_p.write_text(
        "\n".join([
            FILLS_HEADER,
            _make_fill_row(
                utc_ts=1795608000, symbol="GBPUSD", leg="ENTRY", side="BUY",
                trade_seq=1, pos_id=596000001, pre_spread_pts=4.0, pre_spread_bps=0.31,
                adv_slip_pts=0.0, adv_slip_bps=0.0, swap_usd=0.0,
            ),
            _make_fill_row(
                utc_ts=1795608200, symbol="GBPUSD", leg="EXIT", side="SELL",
                trade_seq=1, pos_id=596000001, pre_spread_pts=4.0, pre_spread_bps=0.31,
                adv_slip_pts=0.0, adv_slip_bps=0.0, swap_usd=-0.42,
            ),
        ]) + "\n",
        encoding="utf-8",
    )
    rep = tca_mon.evaluate_live_tca(fills_csv_paths=[csv_p], use_hot_cache=False, n_bootstrap_draws=1000)
    assert rep["inputs"]["swap_violations"] == 1
    assert rep["verdict"] == "RED_FRICTION_BREACH"
    assert tca_mon.exit_code_for_report(rep) == 2


def test_cli_offline_fixture_json_and_vietnamese_output(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI `--offline-fixture` runs cleanly in both `--json` and plain-Vietnamese summary modes."""
    rc_json = tca_mon.main(["--offline-fixture", "--json", "--bootstrap-draws", "1000"])
    assert rc_json == 0
    out_json = capsys.readouterr().out
    parsed = json.loads(out_json)
    assert parsed["schema"] == tca_mon.SCHEMA_VERSION
    assert parsed["order_send_count"] == 0
    assert parsed["holdout_rows_analysed"] == 0
    assert parsed["verdict"] == "GREEN_HEALTHY"
    assert "$" not in out_json

    rc_vi = tca_mon.main(["--offline-fixture", "--bootstrap-draws", "1000"])
    assert rc_vi == 0
    out_vi = capsys.readouterr().out
    assert "GIAM SAT CHI PHI KHOP LENH" in out_vi
    assert "OrderSend=0" in out_vi
    assert "Holdout 2025+=0 dong" in out_vi
    assert "$" not in out_vi
