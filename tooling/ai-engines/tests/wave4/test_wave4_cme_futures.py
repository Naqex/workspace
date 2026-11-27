"""Wave 4 (`W4-G15`) Tests: CME Futures `< 2025-01-01` Holdout Guard & 4-Firm Intraday Prop Feasibility.

Verifies (100% enforced even under `python -O` via `_check`):
  1. Strict `-O`-safe `< 2025-01-01` Holdout rejection across `cme_futures_prop_lab`
     (`load_cme_dev_d1_strict`, `fetch_cme_futures_telemetry`, `_fetch_yahoo_futures`,
     `validate_cme_dev_dates_strict`) and `cme_intraday_prop_feasibility` (`run_cme_4firm_monte_carlo`).
  2. Exact two-sided EOD Trailing DD vs Intraday Unrealized Trailing DD boundary checks
     (`+0.01 USD` safe, `0.00 USD` conservative breach, `-0.01 USD` breach, `gap-through`),
     floor lock-in (`$0` vs `+$100`), and `BOT_AUTO_KILL` vs `FIRM_SOFT_DLL_PAUSE` vs `FIRM_HARD_BREACH`.
  3. `15:10 CT` (`America/Chicago`) forced intraday flatten & Windows `tzdata`-free PEP-495 DST
     parity against `ZoneInfo("America/Chicago")` across March spring-forward & November fall-back (`fold=0/1`).
  4. Verified 4-firm catalog (`Topstep`, `MFFU`, `TakeProfitTrader`, `Tradeify`), `verified_utc` &
     `TERMS_VERIFIED_EXECUTION_UNMEASURED` tags, VN KYC feasibility matrix, and strict `G12` hygiene.
  5. Shared-path Monte Carlo invariants (`Pass + Fail + Pending == 100.0%` at 3m/6m/12m/24m,
     determinism, fast `n_paths=200` CI smoke, Tier-1 vs Tier-2 Law 15 grading separation,
     `GO_WAVE5_FUTURES` vs `SKIP` decision gates, and output confinement under `.runtime/offensive4/futures/`).
  6. Local-cache end-to-end verification against `.runtime/cme-futures-cache` (proving `<= 2024-12-31`
     filtering WITHOUT mutating Wave 2's `cme_prop_study_summary.json` or parquet files) and 10,000-path
     Sleeve #5 Dev simulation.
"""

from __future__ import annotations

import ast
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from quant_core.holdout_guard import HoldoutLockError
from quant_factory import cme_futures_prop_lab as lab5
from quant_factory.macro_etf_trend import ETF_SCHEMA
from quant_factory.wave4 import cme_intraday_prop_feasibility as w4_cme

ROOT = Path(__file__).resolve().parents[4]
WAVE2_SUMMARY_PATH = ROOT / ".runtime" / "cme-futures-cache" / "cme_prop_study_summary.json"
W4_MODULE_PATH = ROOT / "tooling" / "ai-engines" / "quant_factory" / "wave4" / "cme_intraday_prop_feasibility.py"
LAB5_MODULE_PATH = ROOT / "tooling" / "ai-engines" / "quant_factory" / "cme_futures_prop_lab.py"


def _check(condition: bool, message: str = "") -> None:
    """`-O`-safe check so every test verification executes even under `python -O`."""
    if not condition:
        raise AssertionError(message or "Verification check failed")


def _make_synthetic_cme_cache(tmp_path: Path, *, include_post_2024: bool = True) -> Path:
    """Create a minimal synthetic CME D1 (+ optional 1H) parquet cache for offline CI tests."""
    cache_dir = tmp_path / "cme_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    dev_dates = [f"2024-12-{day:02d}" for day in range(1, 32)]
    post_dates = ["2025-01-02", "2025-01-03", "2026-11-23"] if include_post_2024 else []
    all_dates = dev_dates + post_dates

    for code in ("MES", "MNQ", "MGC", "MCL", "M6E", "M6J"):
        n = len(all_dates)
        base = 5000.0 if code == "MES" else (18000.0 if code == "MNQ" else 100.0)
        tbl = pa.table(
            {
                "date": all_dates,
                "open": [base + i * 0.5 for i in range(n)],
                "high": [base + i * 0.5 + 10.0 for i in range(n)],
                "low": [base + i * 0.5 - 10.0 for i in range(n)],
                "close": [base + i * 0.5 + 2.0 for i in range(n)],
                "adjclose": [base + i * 0.5 + 2.0 for i in range(n)],
                "volume": [1000.0] * n,
            },
            schema=ETF_SCHEMA,
        )
        pq.write_table(tbl, cache_dir / f"{code}_D1.parquet", compression="zstd")

        if include_post_2024:
            h1_tbl = pa.table(
                {
                    "date": ["2026-11-20T14:00", "2026-11-20T15:00", "2026-11-23T16:00"],
                    "open": [base, base + 1.0, base + 2.0],
                    "high": [base + 5.0, base + 6.0, base + 7.0],
                    "low": [base - 5.0, base - 4.0, base - 3.0],
                    "close": [base + 1.0, base + 2.0, base + 3.0],
                    "adjclose": [base + 1.0, base + 2.0, base + 3.0],
                    "volume": [200.0, 200.0, 200.0],
                },
                schema=ETF_SCHEMA,
            )
            pq.write_table(h1_tbl, cache_dir / f"{code}_1H.parquet", compression="zstd")
    return cache_dir


def _make_dev_return_dict(
    n_days: int = 300,
    *,
    mean: float = 0.0012,
    std: float = 0.0045,
    seed: int = 17,
) -> dict[str, float]:
    """Build deterministic sealed Dev daily returns strictly `< 2025-01-01`."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(loc=mean, scale=std, size=n_days)
    days: list[str] = []
    cur = date(2024, 12, 31)
    while len(days) < n_days:
        if cur.weekday() < 5:
            days.append(cur.isoformat())
        cur -= timedelta(days=1)
    days.reverse()
    return {d: float(r) for d, r in zip(days, rets, strict=True)}


# ===========================================================================
# 1. Strict `-O`-Safe `< 2025-01-01` Holdout Guard Tests
# ===========================================================================


def test_cme_holdout_guard_rejects_post_2024_under_python_O(tmp_path: Path) -> None:
    """All Holdout guards MUST fail closed with `HoldoutLockError` (active under `python -O`)."""
    cache_dir = _make_synthetic_cme_cache(tmp_path, include_post_2024=True)

    # 1. Invalid cutoff_date rejected fail-closed
    for bad_cutoff in ("2025-01-01", "2026-11-23", "2025-06-15", None, True, "bad-date"):
        with pytest.raises(HoldoutLockError):
            lab5.load_cme_dev_d1_strict(cache_dir=cache_dir, cutoff_date=bad_cutoff)  # type: ignore[arg-type]
        with pytest.raises(HoldoutLockError):
            lab5.fetch_cme_futures_telemetry(
                cache_dir=cache_dir,
                cutoff_date=bad_cutoff,  # type: ignore[arg-type]
                strict_dev_cutoff=True,
            )

    # 2. Strict raw rejection mode blocks parquet containing >= 2025-01-01 rows
    with pytest.raises(HoldoutLockError):
        lab5.load_cme_dev_d1_strict(
            cache_dir=cache_dir,
            cutoff_date="2024-12-31",
            reject_post_cutoff_in_cache=True,
        )

    # 3. Default filtering mode strips >= 2025-01-01 strictly in memory WITHOUT modifying parquet on disk!
    before_bytes = (cache_dir / "MNQ_D1.parquet").read_bytes()
    dev_d1 = lab5.load_cme_dev_d1_strict(cache_dir=cache_dir, cutoff_date="2024-12-31")
    after_bytes = (cache_dir / "MNQ_D1.parquet").read_bytes()
    _check(before_bytes == after_bytes, "load_cme_dev_d1_strict must NEVER mutate cached parquet on disk")
    _check(dev_d1["holdout_rows_analysed"] == 0, "holdout_rows_analysed must be 0")
    _check(dev_d1["max_date"] == "2024-12-31", f"unexpected max_date: {dev_d1['max_date']}")
    _check(dev_d1["max_date"] < "2025-01-01", "max_date must be < 2025-01-01")
    for code in ("MES", "MNQ", "MGC", "MCL", "M6E", "M6J"):
        s = dev_d1["series"][code]
        _check(s["n_rows"] == 31, f"{code} expected 31 dev rows, got {s['n_rows']}")
        _check(s["excluded_post_cutoff_rows"] == 3, f"{code} expected 3 excluded rows")
        _check(s["last_date"] == "2024-12-31", f"{code} last_date mismatch")
        _check(max(s["dates"]) < "2025-01-01", f"{code} holdout leak")

    # 4. fetch_cme_futures_telemetry filters strictly < 2025-01-01 and drops post-2024 1H bars
    tel = lab5.fetch_cme_futures_telemetry(cache_dir=cache_dir, cutoff_date="2024-12-31", strict_dev_cutoff=True)
    for code, row in tel.items():
        _check(row["status"] == "OK", f"{code} failed")
        _check(row["holdout_rows_analysed"] == 0, f"{code} holdout_rows_analysed != 0")
        _check(row["last_date"] <= "2024-12-31", f"{code} last_date > 2024-12-31")
        _check(row["d1_rows"] == 31, f"{code} d1_rows mismatch")
        _check(row["excluded_post_cutoff_d1_rows"] == 3, f"{code} excluded mismatch")
        _check(row["h1_rows"] == 0, f"{code} post-2024 1H rows leaked")

    # 5. _fetch_yahoo_futures forbids post-2024 intraday fetches & post-2024 cutoffs BEFORE any network call
    with pytest.raises(HoldoutLockError):
        lab5._fetch_yahoo_futures("NQ=F", interval="1h", cutoff_date="2024-12-31", strict_dev_cutoff=True)
    with pytest.raises(HoldoutLockError):
        lab5._fetch_yahoo_futures("NQ=F", interval="1d", cutoff_date="2025-01-01", strict_dev_cutoff=True)

    # 6. run_cme_4firm_monte_carlo rejects any Holdout 2025+ date in input returns!
    contaminated = _make_dev_return_dict(n_days=60)
    contaminated["2025-01-02"] = 0.0025
    with pytest.raises(HoldoutLockError):
        w4_cme.run_cme_4firm_monte_carlo(contaminated, n_paths=100, seed=42)


# ===========================================================================
# 2. EOD Trailing DD vs Intraday Unrealized Trailing DD Boundary Tests
# ===========================================================================


def test_eod_vs_intraday_trailing_dd_two_sided_boundaries_and_gap_through() -> None:
    """Verify `±0.01 USD`, `0.00 USD`, `gap-through`, floor lock-in, and EOD vs Intraday divergence."""
    # --- A. Two-sided boundary around initial -$2,000.00 floor ---
    sm_safe = w4_cme.CMEPropDDStateMachine(mode=w4_cme.TrailingDDMode.EOD_TRAILING, max_dd_usd=2_000.0)
    ev_plus_cent = sm_safe.step_tick(-1_999.99, is_eod_close=False)
    _check(not ev_plus_cent.breached, "+0.01 USD above floor must NOT breach")
    _check(ev_plus_cent.breach_kind == w4_cme.BreachKind.NONE.value)
    _check(abs(ev_plus_cent.margin_to_floor_usd - 0.01) < 1e-6)

    sm_exact = w4_cme.CMEPropDDStateMachine(mode=w4_cme.TrailingDDMode.EOD_TRAILING, max_dd_usd=2_000.0)
    ev_exact = sm_exact.step_tick(-2_000.00, is_eod_close=False)
    _check(ev_exact.breached, "0.00 USD exact floor triggers conservative <= breach")
    _check(ev_exact.breach_kind == w4_cme.BreachKind.FIRM_HARD_BREACH.value)
    _check(ev_exact.margin_to_floor_usd == 0.0)
    _check(ev_exact.gap_through_usd == 0.0)

    sm_minus_cent = w4_cme.CMEPropDDStateMachine(mode=w4_cme.TrailingDDMode.EOD_TRAILING, max_dd_usd=2_000.0)
    ev_minus_cent = sm_minus_cent.step_tick(-2_000.01, is_eod_close=False)
    _check(ev_minus_cent.breached, "-0.01 USD below floor MUST breach")
    _check(ev_minus_cent.breach_kind == w4_cme.BreachKind.FIRM_HARD_BREACH.value)
    _check(abs(ev_minus_cent.gap_through_usd - 0.01) < 1e-6)

    sm_gap = w4_cme.CMEPropDDStateMachine(mode=w4_cme.TrailingDDMode.EOD_TRAILING, max_dd_usd=2_000.0)
    ev_gap = sm_gap.step_tick(-2_375.50, is_eod_close=False)
    _check(ev_gap.breached, "gap-through MUST breach")
    _check(ev_gap.breach_kind == w4_cme.BreachKind.FIRM_HARD_BREACH.value)
    _check(abs(ev_gap.gap_through_usd - 375.50) < 1e-6)

    # --- B. Head-to-head divergence: EOD Trailing SURVIVES intraday spike+reversal; TPT PRO Intraday BREACHES! ---
    eod_sm = w4_cme.CMEPropDDStateMachine(mode=w4_cme.TrailingDDMode.EOD_TRAILING, max_dd_usd=2_000.0)
    intra_sm = w4_cme.CMEPropDDStateMachine(
        mode=w4_cme.TrailingDDMode.INTRADAY_UNREALIZED_TRAILING,
        max_dd_usd=2_000.0,
    )
    ev_eod = eod_sm.step_session_bar(
        intraday_high_pnl_usd=1_800.0,
        intraday_low_pnl_usd=-400.0,
        eod_close_pnl_usd=-400.0,
    )
    ev_intra = intra_sm.step_session_bar(
        intraday_high_pnl_usd=1_800.0,
        intraday_low_pnl_usd=-400.0,
        eod_close_pnl_usd=-400.0,
    )
    _check(not ev_eod.breached and ev_eod.floor_usd == -2_000.0, "EOD trailing must survive intraday giveback")
    _check(ev_intra.breached and ev_intra.floor_usd == -200.0, "Intraday trailing must ratchet floor to -$200 & breach")
    _check(abs(ev_intra.gap_through_usd - 200.0) < 1e-6)

    # --- C. Two-sided ±0.01 check AFTER intraday ratchet on TPT PRO ---
    intra_edge = w4_cme.CMEPropDDStateMachine(
        mode=w4_cme.TrailingDDMode.INTRADAY_UNREALIZED_TRAILING,
        max_dd_usd=2_000.0,
    )
    intra_edge.step_tick(1_500.0)  # floor -> -500.0
    _check(intra_edge.floor_usd == -500.0)
    _check(not intra_edge.step_tick(-499.99).breached)
    _check(intra_edge.step_tick(-500.01).breached)

    # --- D. Floor Lock-In ($0 Topstep vs +$100 MFFU/Tradeify) ---
    topstep_sm = w4_cme.CMEPropDDStateMachine(
        mode=w4_cme.TrailingDDMode.EOD_TRAILING,
        max_dd_usd=2_000.0,
        lock_floor_pnl_usd=0.0,
    )
    topstep_sm.step_session_bar(intraday_high_pnl_usd=2_600.0, intraday_low_pnl_usd=0.0, eod_close_pnl_usd=2_500.0)
    _check(topstep_sm.floor_usd == 0.0 and topstep_sm.floor_locked is True)

    mffu_sm = w4_cme.CMEPropDDStateMachine(
        mode=w4_cme.TrailingDDMode.EOD_TRAILING,
        max_dd_usd=2_000.0,
        lock_floor_pnl_usd=100.0,
    )
    mffu_sm.step_session_bar(intraday_high_pnl_usd=2_500.0, intraday_low_pnl_usd=0.0, eod_close_pnl_usd=2_500.0)
    _check(mffu_sm.floor_usd == 100.0 and mffu_sm.floor_locked is True)

    # --- E. Separate BOT_AUTO_KILL vs FIRM_SOFT_DLL_PAUSE vs FIRM_HARD_BREACH ---
    sep_sm = w4_cme.CMEPropDDStateMachine(
        mode=w4_cme.TrailingDDMode.EOD_TRAILING,
        max_dd_usd=2_000.0,
        firm_daily_loss_limit_usd=1_000.0,
        daily_loss_is_hard_breach=False,
        bot_daily_kill_usd=600.0,
    )
    ev_bot = sep_sm.step_tick(-650.0)
    _check(not ev_bot.breached and ev_bot.breach_kind == w4_cme.BreachKind.BOT_AUTO_KILL.value)
    _check(sep_sm.bot_auto_kill_count == 1 and sep_sm.soft_dll_pause_count == 0 and sep_sm.hard_breach_count == 0)

    ev_dll = sep_sm.step_tick(-1_050.0)
    _check(not ev_dll.breached and ev_dll.breach_kind == w4_cme.BreachKind.FIRM_SOFT_DLL_PAUSE.value)
    _check(sep_sm.soft_dll_pause_count == 1)

    # --- F. Bug Pattern #3: reject bool, NaN, Inf fail-closed ---
    for bad_val in (True, False, float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError):
            sep_sm.step_tick(bad_val)  # type: ignore[arg-type]


# ===========================================================================
# 3. `15:10 CT` Forced Intraday Flatten & March / November DST Transitions
# ===========================================================================


def test_1510_ct_dst_transitions_and_tzdata_free_pep495_parity() -> None:
    """Verify exact March/November DST transitions & 0 mismatches vs `ZoneInfo('America/Chicago')`."""
    zi_chi = ZoneInfo("America/Chicago")
    fb_chi = w4_cme.resolve_chicago_tz(prefer_fallback=True)

    transition_windows = [
        datetime(2024, 3, 10, 6, 0, tzinfo=UTC),
        datetime(2024, 11, 3, 5, 0, tzinfo=UTC),
        datetime(2025, 3, 9, 6, 0, tzinfo=UTC),
        datetime(2025, 11, 2, 5, 0, tzinfo=UTC),
        datetime(2026, 3, 8, 6, 0, tzinfo=UTC),
        datetime(2026, 11, 1, 5, 0, tzinfo=UTC),
    ]
    folds_seen = set()
    for start_u in transition_windows:
        for mins in range(0, 300, 15):
            u = start_u + timedelta(minutes=mins)
            d_zi = u.astimezone(zi_chi)
            d_fb = u.astimezone(fb_chi)
            _check(d_zi.utcoffset() == d_fb.utcoffset(), f"Offset mismatch at {u}")
            _check(d_zi.dst() == d_fb.dst(), f"DST mismatch at {u}")
            _check(d_zi.tzname() == d_fb.tzname(), f"tzname mismatch at {u}")
            _check(d_zi.fold == d_fb.fold, f"PEP-495 fold mismatch at {u}")
            _check(d_zi.replace(tzinfo=None) == d_fb.replace(tzinfo=None))
            folds_seen.add(d_fb.fold)
    _check(folds_seen == {0, 1}, "Must exercise both fold=0 and fold=1 on November fall-back")

    ambig_0_zi = datetime(2024, 11, 3, 1, 30, fold=0, tzinfo=zi_chi).astimezone(UTC)
    ambig_0_fb = datetime(2024, 11, 3, 1, 30, fold=0, tzinfo=fb_chi).astimezone(UTC)
    ambig_1_zi = datetime(2024, 11, 3, 1, 30, fold=1, tzinfo=zi_chi).astimezone(UTC)
    ambig_1_fb = datetime(2024, 11, 3, 1, 30, fold=1, tzinfo=fb_chi).astimezone(UTC)
    _check(ambig_0_zi == ambig_0_fb == datetime(2024, 11, 3, 6, 30, tzinfo=UTC))
    _check(ambig_1_zi == ambig_1_fb == datetime(2024, 11, 3, 7, 30, tzinfo=UTC))

    for use_fb in (False, True):
        _check(
            w4_cme.get_1510_ct_utc_cutoff(date(2024, 3, 8), prefer_fallback_tz=use_fb)
            == datetime(2024, 3, 8, 21, 10, tzinfo=UTC)
        )
        _check(
            w4_cme.get_1510_ct_utc_cutoff(date(2024, 3, 11), prefer_fallback_tz=use_fb)
            == datetime(2024, 3, 11, 20, 10, tzinfo=UTC)
        )
        _check(
            w4_cme.get_1510_ct_utc_cutoff(date(2024, 11, 1), prefer_fallback_tz=use_fb)
            == datetime(2024, 11, 1, 20, 10, tzinfo=UTC)
        )
        _check(
            w4_cme.get_1510_ct_utc_cutoff(date(2024, 11, 4), prefer_fallback_tz=use_fb)
            == datetime(2024, 11, 4, 21, 10, tzinfo=UTC)
        )

        d_winter = w4_cme.evaluate_cme_1510_ct_flatten(
            datetime(2024, 3, 8, 20, 10, tzinfo=UTC),
            open_contracts=2,
            prefer_fallback_tz=use_fb,
        )
        d_summer = w4_cme.evaluate_cme_1510_ct_flatten(
            datetime(2024, 3, 11, 20, 10, tzinfo=UTC),
            open_contracts=2,
            prefer_fallback_tz=use_fb,
        )
        _check(d_winter.action == "ALLOW_TRADING" and d_winter.tz_abbr == "CST" and not d_winter.must_flatten_now)
        _check(
            d_summer.action == "FORCE_FLAT_VIOLATION_RISK"
            and d_summer.tz_abbr == "CDT"
            and d_summer.must_flatten_now
            and d_summer.breach_if_position_open
            and not d_summer.order_send_capable
        )

        d_buf = w4_cme.evaluate_cme_1510_ct_flatten(
            datetime(2024, 3, 11, 20, 9, 30, tzinfo=UTC),
            open_contracts=1,
            close_buffer_sec=60,
            prefer_fallback_tz=use_fb,
        )
        _check(
            d_buf.action == "PRE_CLOSE_FLATTEN_REQUIRED"
            and d_buf.must_flatten_now
            and not d_buf.breach_if_position_open
        )

        d_reopen = w4_cme.evaluate_cme_1510_ct_flatten(
            datetime(2024, 3, 10, 22, 0, tzinfo=UTC),
            open_contracts=0,
            prefer_fallback_tz=use_fb,
        )
        _check(d_reopen.action == "ALLOW_TRADING" and not d_reopen.in_blackout_window)

    with pytest.raises(ValueError):
        w4_cme.evaluate_cme_1510_ct_flatten(datetime(2024, 3, 11, 20, 10), open_contracts=1)

    stream = [
        datetime(2024, 3, 8, 20, 10, tzinfo=UTC),
        datetime(2024, 3, 8, 21, 9, 30, tzinfo=UTC),
        datetime(2024, 3, 11, 19, 30, tzinfo=UTC),
        datetime(2024, 3, 11, 20, 10, tzinfo=UTC),
    ]
    flat_res = w4_cme.apply_1510_ct_intraday_flatten_to_positions(stream, [2, 2, 2, 2], prefer_fallback_tz=True)
    _check(flat_res["effective_contracts"] == [2, 0, 2, 0])
    _check(flat_res["forced_flatten_count"] == 2)
    _check(flat_res["dst_days_count"] == 1 and flat_res["std_days_count"] == 1)


# ===========================================================================
# 4. 4-Firm Catalog, Provenance, VN KYC Matrix, G12 & `[ARCH-02]` Hygiene
# ===========================================================================


def test_4firm_catalog_vn_kyc_g12_and_zero_bare_asserts() -> None:
    """Verify all 4 firms, provenance stamps, VN KYC statuses, G12 compliance, and zero bare asserts."""
    firms_present = {spec.firm_id for spec in w4_cme.CME_4FIRM_CATALOG.values()}
    _check(firms_present == {"topstep", "mffu", "takeprofittrader", "tradeify"})

    for tid, spec in w4_cme.CME_4FIRM_CATALOG.items():
        _check(spec.verified_utc.endswith("Z"), f"{tid} missing UTC stamp")
        _check(spec.execution_status == "TERMS_VERIFIED_EXECUTION_UNMEASURED")
        _check("15:10" in spec.mandatory_flat_ct)

    tpt = w4_cme.CME_4FIRM_CATALOG["tpt_50k_pro"]
    _check(tpt.eval_dd_mode == w4_cme.TrailingDDMode.EOD_TRAILING.value)
    _check(tpt.funded_dd_mode == w4_cme.TrailingDDMode.INTRADAY_UNREALIZED_TRAILING.value)
    _check(tpt.payout_cadence_days == 1)

    kyc = w4_cme.build_vn_kyc_feasibility_matrix()
    by_firm = {row["firm_id"]: row for row in kyc}
    _check(set(by_firm.keys()) == {"topstep", "mffu", "takeprofittrader", "tradeify", "ftmo_incumbent"})
    _check(by_firm["topstep"]["vn_kyc_status"] == w4_cme.VNKycStatus.ALLOWED_XFA_ONLY.value)
    _check(by_firm["topstep"]["vn_kyc_eligible"] is True)
    _check(by_firm["topstep"]["vn_live_funded_eligible"] is False)
    for restricted in ("mffu", "takeprofittrader", "tradeify"):
        _check(by_firm[restricted]["vn_kyc_status"] == w4_cme.VNKycStatus.RESTRICTED_VN_PROHIBITED.value)
        _check(by_firm[restricted]["vn_kyc_eligible"] is False)

    w4_src = W4_MODULE_PATH.read_text(encoding="utf-8").lower()
    for banned_g12 in ("live chat", "live-chat", "contact support", "email support", "nhắn support"):
        _check(banned_g12 not in w4_src, f"G12 violation token {banned_g12!r} in {W4_MODULE_PATH.name}")

    for mod_path in (W4_MODULE_PATH, LAB5_MODULE_PATH):
        src = mod_path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(mod_path))
        bare_asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        _check(bare_asserts == [], f"Bare Python assert found in {mod_path.name} at lines {bare_asserts}")
        mt5_imports: list[int] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(a.name == "MetaTrader5" or a.name.startswith("MetaTrader5.") for a in node.names):
                    mt5_imports.append(node.lineno)
            elif isinstance(node, ast.ImportFrom):
                mod_name = node.module or ""
                if mod_name == "MetaTrader5" or mod_name.startswith("MetaTrader5."):
                    mt5_imports.append(node.lineno)
        _check(mt5_imports == [], f"MetaTrader5 import found in {mod_path.name} at lines {mt5_imports}")


# ===========================================================================
# 5. Fast Monte Carlo Smoke (`n_paths=200`), Law 13 `Pass+Fail+Pending==100%`
# ===========================================================================


def test_4firm_mc_smoke_pass_fail_pending_sum_and_decision_gates(tmp_path: Path) -> None:
    """Fast CI smoke (`n_paths=200`): determinism, Pass+Fail+Pending==100%, output confinement, GO vs SKIP."""
    _check(w4_cme.ORDER_SEND_CAPABLE is False and w4_cme.ORDER_SEND_COUNT == 0)

    dev_weak = _make_dev_return_dict(n_days=260, mean=0.00015, std=0.0055, seed=101)
    r1 = w4_cme.run_cme_4firm_monte_carlo(dev_weak, n_paths=200, seed=42)
    r2 = w4_cme.run_cme_4firm_monte_carlo(dev_weak, n_paths=200, seed=42)

    _check(r1["invariants"]["order_send_count"] == 0)
    _check(r1["invariants"]["holdout_rows_analysed"] == 0)
    _check(r1["cme_4firm_results"] == r2["cme_4firm_results"], "MC must be 100% deterministic for fixed seed")
    _check(r1["incumbent_ftmo_results"] == r2["incumbent_ftmo_results"])
    _check(r1["decision"] == "SKIP")

    # Verify Law 15 domain-tier isolation (Tier 1 CFD vs Tier 2 CME Futures)
    for row in r1["cme_4firm_results"].values():
        _check(row["domain_scorecard"]["domain_tier"] == "TIER_2_CME_FUTURES_INTRADAY")
    for row in r1["incumbent_ftmo_results"].values():
        _check(row["domain_scorecard"]["domain_tier"] == "TIER_1_CFD_PROP_SINGLE_BOT")

    all_rows = list(r1["cme_4firm_results"].values()) + list(r1["incumbent_ftmo_results"].values())
    _check(len(all_rows) == 10)
    for row in all_rows:
        for horizon in ("3m", "6m", "12m", "24m"):
            h = row["pass_fail_pending"][horizon]
            _check(0.0 <= h["pass_pct"] <= 100.0)
            _check(0.0 <= h["fail_pct"] <= 100.0)
            _check(0.0 <= h["pending_pct"] <= 100.0)
            _check(abs((h["pass_pct"] + h["fail_pct"] + h["pending_pct"]) - 100.0) <= 1e-3)
            _check(abs(h["sum_pct"] - 100.0) <= 1e-3)
        _check(0.0 <= row["prob_net_le_zero_pct"] <= 100.0)
        _check(0.0 <= row["p_payout_1_pct"] <= 100.0)
        _check(row["median_cal_days_to_payout1_unconditional"] <= 730.0)

    dev_strong = _make_dev_return_dict(n_days=260, mean=0.0022, std=0.0030, seed=202)
    r_strong = w4_cme.run_cme_4firm_monte_carlo(dev_strong, n_paths=200, seed=42)
    _check(r_strong["decision"] in {"GO_WAVE5_FUTURES", "SKIP"})
    _check(r_strong["cme_4firm_results"]["topstep_50k_combine"]["ev_per_usd_fee"] > 3.0)
    _check(r_strong["cme_4firm_results"]["topstep_50k_combine"]["median_net_24m_usd"] > 0.0)
    _check(r_strong["cme_4firm_results"]["topstep_50k_combine"]["median_net_24m_vnd"] > 0.0)

    with pytest.raises(ValueError):
        w4_cme.run_cme_4firm_monte_carlo(
            dev_weak,
            n_paths=100,
            seed=42,
            write_output_path=tmp_path / "illegal_outside.json",
        )


# ===========================================================================
# 6. Local-Cache Proof: Wave 2 Non-Mutation + 10,000-Path Sealed Dev MC
# ===========================================================================


@pytest.mark.local_cache
def test_local_cache_strict_dev_d1_and_10k_mc_preserves_wave2() -> None:
    """Verify real `.runtime/cme-futures-cache` loads strictly <= 2024-12-31 while Wave 2 summary stays untouched."""
    _check(WAVE2_SUMMARY_PATH.is_file(), "Wave 2 CME summary missing")
    wave2_before_bytes = WAVE2_SUMMARY_PATH.read_bytes()

    d1_strict = lab5.load_cme_dev_d1_strict(cache_dir=lab5.CME_CACHE_DIR, cutoff_date="2024-12-31")
    _check(d1_strict["holdout_rows_analysed"] == 0)
    _check(d1_strict["max_date"] <= "2024-12-31" and d1_strict["max_date"] < "2025-01-01")
    for code in ("MES", "MNQ", "MGC", "MCL", "M6E", "M6J"):
        _check(d1_strict["series"][code]["n_rows"] >= 1500)
        _check(d1_strict["series"][code]["last_date"] <= "2024-12-31")

    dev_returns = w4_cme.load_dev_cme_sleeve_returns()
    _check(max(dev_returns.keys()) < "2025-01-01")

    prod_json = w4_cme.DEFAULT_OUTPUT_JSON
    prod_before_bytes = prod_json.read_bytes() if prod_json.is_file() else None
    res = w4_cme.run_cme_4firm_monte_carlo(
        dev_returns,
        n_paths=10_000,
        seed=42,
        write_output_path=None,
    )
    if prod_before_bytes is not None:
        _check(
            prod_json.read_bytes() == prod_before_bytes,
            "Production wave4_cme_intraday_feasibility.json MUST NOT be mutated by pytest!",
        )
    _check(res["invariants"]["order_send_count"] == 0)
    _check(res["invariants"]["holdout_rows_analysed"] == 0)
    _check(res["simulation_config"]["n_paths"] == 10_000)
    _check(res["simulation_config"]["dev_input_max_date"] <= "2024-12-31")
    _check(res["decision"] in {"GO_WAVE5_FUTURES", "SKIP"})

    # Verify TPT PRO Intraday Unrealized Trailing DD has strictly higher 12m Funded blowup than Topstep 50K EOD
    ts50_blow = res["cme_4firm_results"]["topstep_50k_combine"]["funded_blowup_12m_pct"]
    tpt50_blow = res["cme_4firm_results"]["tpt_50k_pro"]["funded_blowup_12m_pct"]
    _check(
        ts50_blow is not None and tpt50_blow is not None and tpt50_blow > ts50_blow,
        f"Expected TPT PRO intraday trailing blowup ({tpt50_blow}%) > Topstep 50K EOD ({ts50_blow}%)",
    )

    wave2_after_bytes = WAVE2_SUMMARY_PATH.read_bytes()
    _check(wave2_before_bytes == wave2_after_bytes, "Wave 2 cme_prop_study_summary.json was mutated!")
    w2_json = json.loads(wave2_after_bytes.decode("utf-8"))
    for row in w2_json["yahoo_futures_telemetry"].values():
        _check(row["h1_rows"] >= 500)
