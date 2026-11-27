"""Two-Sided Boundary, Prague DST, R1/R2 Restart Hydration, Profile Resolution & EA Parity Tests.

Covers PLAN v3.1 / Astra R3 Notes #1, #2, #3 strictly offline (OrderSend = 0, Holdout 2025+ SEALED,
zero private_vault/ or .runtime/ dependency so Layer-1 GitHub Actions CI stays 100% green):
  1. Official `ftmo_standard_10k` contract schema + 3 new C10 DryRun presets + Astra R3 Note #2
     silent Swing fallback proof (`pass27_portfolio_m1_phase_audit.py:318`).
  2. Two-sided boundary tests (`+0.01`, `0.00`, `-0.01`, `gap-through`) for BOTH 5% Daily DD
     and 10% Static DD, contrasting FTMO official strict `<` vs conservative runner `<=`, with
     strictly separated `BOT_AUTO_KILL` vs `FIRM_HARD_BREACH` flags.
  3. Prague `00:00` reset across BOTH Spring (CET->CEST, 23h) and Fall (CEST->CET, 25h) DST
     transitions — verified against both `ZoneInfo("Europe/Prague")` and exact MQL5 math mirror.
  4. Phase transition guard: hitting +10% P1 / +5% P2 while an open position is active MUST NOT
     prematurely transition phase.
  5. Restart Hydration R1 (`HydrateTradedDaysFromHistory`) and R2 (`RestoreOrInitDayAnchorM` &
     `PersistAutoKillStateM`) deterministic offline fixtures, plus source verification that both
     branches are `SKIPPED_IN_TESTER` (labeled `PYTHON_LOGIC_VERIFIED_MQL_BRANCH_UNEXECUTED /
     UNTESTED_ON_LIVE_RESTART`).
  6. Astra R3 Note #3 source checks (`LogMasterShadowRow` early-return at L373, `OnTick` 1s
     throttle at L879) and sub-second floor-pierce-and-rebound observation lag fixture.
  7. Exact EA Step 2B lot sizing (`ACCOUNT_BALANCE * allowedRiskPct * 0.95`, `RoundVolumeDownToStep`,
     `OrderCalcMargin <= 85%` scale-down) vs Step 2A divergence verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sys
import unittest
from zoneinfo import ZoneInfo

AI_ENGINES = Path(__file__).resolve().parents[1]
EXPORTS_DIR = AI_ENGINES / "exports"
REPO_ROOT = AI_ENGINES.parents[1]

for _p in (AI_ENGINES, EXPORTS_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import mql5_parity_checker as parity  # noqa: E402
import pass27_portfolio_m1_phase_audit as p27  # noqa: E402
import verify_deployment_kit as kit  # noqa: E402

ORDER_SEND_COUNT = 0
HOLDOUT_ROWS_ANALYSED = 0
PRAGUE_TZ = ZoneInfo("Europe/Prague")


# =============================================================================
# 1. Exact Reference Evaluators (Boundaries, Prague DST, Phase Guard, Step 2B)
# =============================================================================

def evaluate_ftmo_dd_boundaries(
    *,
    initial_balance: float,
    day_anchor_balance: float,
    equity: float,
    daily_limit_pct: float = 5.0,
    static_limit_pct: float = 10.0,
    bot_kill_daily_pct: float = 3.5,
    bot_kill_static_pct: float = 8.0,
) -> dict[str, object]:
    """Evaluate DD boundaries separating BOT_AUTO_KILL from FIRM_HARD_BREACH, and
    contrasting FTMO official strict `<` floor breach vs conservative runner `<=`."""
    daily_floor = round(day_anchor_balance - initial_balance * (daily_limit_pct / 100.0), 8)
    static_floor = round(initial_balance * (1.0 - static_limit_pct / 100.0), 8)

    daily_dd_pct = max(0.0, ((day_anchor_balance - equity) / initial_balance) * 100.0)
    static_dd_pct = max(0.0, ((initial_balance - equity) / initial_balance) * 100.0)

    # FTMO official: strictly below floor (`equity < floor`)
    official_daily_breach = equity < daily_floor - 1e-12
    official_static_breach = equity < static_floor - 1e-12

    # Conservative Python runner (`single_ticket_runner.py:238-239`): `dd >= limit` / `equity <= floor`
    runner_daily_breach = equity <= daily_floor + 1e-12
    runner_static_breach = equity <= static_floor + 1e-12

    # Naqex_Master_Prop7E.mq5:795: `dailyDdPct >= InpKillDailyDdPct || staticDdPct >= InpKillStaticDdPct`
    bot_auto_kill_daily = daily_dd_pct >= bot_kill_daily_pct - 1e-12
    bot_auto_kill_static = static_dd_pct >= bot_kill_static_pct - 1e-12

    return {
        "daily_floor_usd": daily_floor,
        "static_floor_usd": static_floor,
        "daily_dd_pct": round(daily_dd_pct, 6),
        "static_dd_pct": round(static_dd_pct, 6),
        "BOT_AUTO_KILL": bool(bot_auto_kill_daily or bot_auto_kill_static),
        "BOT_AUTO_KILL_DAILY": bool(bot_auto_kill_daily),
        "BOT_AUTO_KILL_STATIC": bool(bot_auto_kill_static),
        "FIRM_HARD_BREACH_OFFICIAL_LT": bool(official_daily_breach or official_static_breach),
        "FIRM_HARD_BREACH_DAILY_OFFICIAL_LT": bool(official_daily_breach),
        "FIRM_HARD_BREACH_STATIC_OFFICIAL_LT": bool(official_static_breach),
        "FIRM_HARD_BREACH_RUNNER_LE": bool(runner_daily_breach or runner_static_breach),
        "FIRM_HARD_BREACH_DAILY_RUNNER_LE": bool(runner_daily_breach),
        "FIRM_HARD_BREACH_STATIC_RUNNER_LE": bool(runner_static_breach),
    }


def _last_sunday_of_month(year: int, month: int) -> int:
    # Exact mirror of Naqex_Master_Prop7E.mq5:106-111
    d31 = datetime(year, month, 31, tzinfo=timezone.utc)
    dow_sun0 = (d31.weekday() + 1) % 7  # Python Mon=0..Sun=6 -> MQL5 Sun=0..Sat=6
    return 31 - dow_sun0


def mql5_prague_utc_offset_hours(utc_dt: datetime) -> int:
    # Exact mirror of Naqex_Master_Prop7E.mq5:113-120
    if utc_dt.month < 3 or utc_dt.month > 10:
        return 1
    if 3 < utc_dt.month < 10:
        return 2
    ls = _last_sunday_of_month(utc_dt.year, utc_dt.month)
    if utc_dt.month == 3:
        return 2 if (utc_dt.day > ls or (utc_dt.day == ls and utc_dt.hour >= 1)) else 1
    return 2 if (utc_dt.day < ls or (utc_dt.day == ls and utc_dt.hour < 1)) else 1


def mql5_prague_midnight_utc_offset_hours(year: int, month: int, day: int) -> int:
    # Exact mirror of Naqex_Master_Prop7E.mq5:123-130 (V101-03)
    if month < 3 or month > 10:
        return 1
    if 3 < month < 10:
        return 2
    ls = _last_sunday_of_month(year, month)
    if month == 3:
        return 2 if day > ls else 1
    return 2 if day <= ls else 1


def mql5_prague_day_key_and_reset_start_utc(utc_ts: int) -> tuple[int, int]:
    # Exact mirror of Naqex_Master_Prop7E.mq5:132-166 (with srvMinusUtc = 0 -> UTC)
    utc_dt = datetime.fromtimestamp(utc_ts, timezone.utc)
    cur_off = mql5_prague_utc_offset_hours(utc_dt) * 3600
    prg_now = utc_ts + cur_off
    prg_dt = datetime.fromtimestamp(prg_now, timezone.utc)
    day_of_year = prg_dt.timetuple().tm_yday - 1  # MQL5 day_of_year is 0-based (Jan 1 = 0)
    day_key = prg_dt.year * 1000 + day_of_year
    mid_off = mql5_prague_midnight_utc_offset_hours(prg_dt.year, prg_dt.month, prg_dt.day) * 3600
    prg_mid_utc = (prg_now - (prg_now % 86400)) - mid_off
    return day_key, prg_mid_utc


def evaluate_phase_transition(
    *,
    stage: str,
    initial_balance: float,
    realized_balance: float,
    floating_equity: float,
    open_positions_count: int,
    trading_days: int,
    min_trading_days: int = 4,
    p1_target_pct: float = 10.0,
    p2_target_pct: float = 5.0,
) -> dict[str, object]:
    """Strict phase-transition check: NEVER transition while an open position is active."""
    if stage not in ("P1", "P2"):
        return {"transitioned": False, "next_stage": stage, "reason": "ALREADY_FUNDED_OR_TERMINAL"}
    target_pct = p1_target_pct if stage == "P1" else p2_target_pct
    target_usd = initial_balance * (1.0 + target_pct / 100.0)
    next_stage = "P2" if stage == "P1" else "FUNDED"

    if open_positions_count > 0:
        return {
            "transitioned": False,
            "next_stage": stage,
            "reason": "OPEN_POSITION_ACTIVE_HOLD",
            "floating_above_target": floating_equity >= target_usd - 1e-9,
        }
    if trading_days < min_trading_days:
        return {
            "transitioned": False,
            "next_stage": stage,
            "reason": "MIN_TRADING_DAYS_NOT_MET",
        }
    if realized_balance >= target_usd - 1e-9:
        return {
            "transitioned": True,
            "next_stage": next_stage,
            "reason": f"{stage}_TARGET_MET_FLAT",
        }
    return {"transitioned": False, "next_stage": stage, "reason": "TARGET_NOT_REACHED"}


def mql5_round_volume_down_to_step(raw_lots: float, vol_step: float, vol_min: float, vol_max: float) -> float:
    """Exact mirror of Naqex_PropGuard.mqh:233-253."""
    if raw_lots <= 0.0 or vol_step <= 0.0:
        return 0.0
    digits = 0
    scaled = vol_step
    while digits < 8 and abs(scaled - round(scaled)) > 1e-7:
        scaled *= 10.0
        digits += 1
    lots = round(math.floor((raw_lots + 1e-9) / vol_step) * vol_step, digits)
    if lots < vol_min:
        return 0.0
    return round(min(lots, vol_max), digits)


def ea_step2b_compute_lots(
    *,
    account_balance: float,
    allowed_risk_pct: float,
    sl_dist: float,
    tick_size: float,
    tick_value_loss: float,
    free_margin: float,
    margin_per_lot: float,
    vol_step: float = 0.01,
    vol_min: float = 0.01,
    vol_max: float = 50.0,
) -> dict[str, object]:
    """Exact mirror of Naqex_Master_Prop7E.mq5:640-668."""
    if account_balance <= 0.0 or tick_size <= 0.0 or tick_value_loss <= 0.0 or vol_step <= 0.0:
        return {"lots": 0.0, "status": "INVALID_SPECS", "margin_scaled": False}
    loss_per_lot = (sl_dist / tick_size) * tick_value_loss
    if loss_per_lot <= 0.0:
        return {"lots": 0.0, "status": "INVALID_SL", "margin_scaled": False}
    risk_money = account_balance * (allowed_risk_pct / 100.0) * 0.95
    lots = mql5_round_volume_down_to_step(risk_money / loss_per_lot, vol_step, vol_min, vol_max)
    if lots < vol_min:
        return {"lots": 0.0, "status": "SILENT_BELOW_VOLMIN", "margin_scaled": False}
    req_margin = lots * margin_per_lot
    if free_margin <= 0.0 or req_margin <= 0.0:
        return {"lots": 0.0, "status": "ORDER_BLOCKED_MARGIN", "margin_scaled": False}
    max_allow_m = free_margin * 0.85
    margin_scaled = False
    if req_margin > max_allow_m:
        margin_scaled = True
        lots = mql5_round_volume_down_to_step(lots * (max_allow_m / req_margin), vol_step, vol_min, vol_max)
        if lots < vol_min:
            return {"lots": 0.0, "status": "SILENT_MARGIN_SCALED_BELOW_VOLMIN", "margin_scaled": True}
    return {"lots": lots, "status": "ACCEPTED", "margin_scaled": margin_scaled, "risk_money": round(risk_money, 4)}


# =============================================================================
# 2. Deterministic Offline Mirrors of R1 & R2 Restart Hydration (Astra Note #1)
# =============================================================================

@dataclass
class MockDeal:
    magic: int
    entry: str  # "IN" or "OUT"
    dtype: str  # "BUY" or "SELL"
    deal_utc: int
    profit: float = 0.0
    swap: float = 0.0
    commission: float = 0.0


class OfflineHydrationModelR1:
    """Offline Python mirror of `Naqex_Signals_7E.mqh:320-402` (`HydrateTradedDaysFromHistory`).

    Status: PYTHON_LOGIC_VERIFIED_MQL_BRANCH_UNEXECUTED / UNTESTED_ON_LIVE_RESTART.
    """

    MAGIC_TO_IDX = {
        20261122: 0,  # E1 (UTC day)
        20261123: 1,  # E2 (D1 bar)
        20261125: 2,  # E3 (D1 bar)
        20261124: 3,  # E4 (NY day)
        20261126: 4,  # E5 (NY day)
        20261128: 5,  # E6 (D1 bar)
        20261129: 6,  # E7 (NY day)
        20261127: 7,  # S6 (UTC day)
    }
    NY_TZ = ZoneInfo("America/New_York")

    def __init__(self) -> None:
        self.traded_day: list[int] = [0] * 8
        self.hydrated: bool = False

    def _ny_day_key(self, utc_ts: int) -> int:
        ny_dt = datetime.fromtimestamp(utc_ts, timezone.utc).astimezone(self.NY_TZ)
        return int(datetime(ny_dt.year, ny_dt.month, ny_dt.day, tzinfo=timezone.utc).timestamp())

    def hydrate_from_history(
        self,
        now_utc: int,
        deals_48h: list[MockDeal],
        open_pos_magics: list[int],
        *,
        d1_bar_start_utc: int,
        history_select_ok: bool = True,
    ) -> bool:
        if now_utc <= 0 or not history_select_ok:
            self.hydrated = False
            return False
        cur_utc_day = now_utc - (now_utc % 86400)
        cur_ny_day = self._ny_day_key(now_utc)
        for d in deals_48h:
            if d.entry != "IN" or d.dtype not in ("BUY", "SELL"):
                continue
            idx = self.MAGIC_TO_IDX.get(d.magic, -1)
            if idx < 0:
                continue
            if idx in (0, 7):
                day_k = d.deal_utc - (d.deal_utc % 86400)
                if day_k > self.traded_day[idx]:
                    self.traded_day[idx] = day_k
            elif idx in (1, 2, 5):
                if d1_bar_start_utc > 0 and d.deal_utc >= d1_bar_start_utc:
                    self.traded_day[idx] = d1_bar_start_utc
            else:
                ny_k = self._ny_day_key(d.deal_utc)
                if ny_k > self.traded_day[idx]:
                    self.traded_day[idx] = ny_k
        for pm in open_pos_magics:
            idx = self.MAGIC_TO_IDX.get(pm, -1)
            if idx < 0:
                continue
            if idx in (0, 7):
                self.traded_day[idx] = cur_utc_day
            elif idx in (1, 2, 5):
                if d1_bar_start_utc > 0:
                    self.traded_day[idx] = d1_bar_start_utc
            else:
                self.traded_day[idx] = cur_ny_day
        self.hydrated = True
        return True

    def can_engine_trade(self, magic: int, session_day_key: int) -> bool:
        if not self.hydrated:
            return False
        idx = self.MAGIC_TO_IDX.get(magic, -1)
        if idx < 0:
            return False
        return self.traded_day[idx] != session_day_key


class OfflineAnchorAndAutoKillModelR2:
    """Offline Python mirror of `Naqex_Master_Prop7E.mq5:168-245` (`PersistAutoKillStateM` + `RestoreOrInitDayAnchorM`).

    Status: PYTHON_LOGIC_VERIFIED_MQL_BRANCH_UNEXECUTED / UNTESTED_ON_LIVE_RESTART.
    """

    def __init__(self, gv_store: dict[str, float]) -> None:
        self.gv = gv_store
        self.day_key: int = -1
        self.day_anchor_bal: float = 0.0
        self.day_anchor_eq: float = 0.0
        self.auto_kill_active: bool = False
        self.anchor_unrecovered: bool = False

    def persist_auto_kill(self, day_key: int, active: bool) -> None:
        if day_key <= 0:
            return
        self.gv["NQXG_ACCT_DAYKEY"] = float(day_key)
        self.gv["NQXG_ACCT_AUTOKILL"] = 1.0 if active else 0.0

    def restore_or_init_day_anchor(
        self,
        now_utc: int,
        bal: float,
        eq: float,
        deals_since_reset: list[MockDeal],
        *,
        history_select_ok: bool = True,
    ) -> None:
        today, reset_start_utc = mql5_prague_day_key_and_reset_start_utc(now_utc)
        is_new_day = today != self.day_key
        if (not is_new_day) and self.day_anchor_eq > 0.0 and (not self.anchor_unrecovered):
            return

        reconstructed_bal = bal
        self.anchor_unrecovered = False
        if now_utc >= reset_start_utc and history_select_ok:
            today_realized = sum(
                d.profit + d.swap + d.commission
                for d in deals_since_reset
                if d.dtype in ("BUY", "SELL") and d.deal_utc >= reset_start_utc
            )
            reconstructed_bal = bal - today_realized
            if reconstructed_bal <= 0.0:
                reconstructed_bal = bal
        elif now_utc - reset_start_utc > 600:
            self.anchor_unrecovered = True

        prev_day_key = self.day_key
        self.day_key = today
        self.day_anchor_bal = reconstructed_bal
        self.day_anchor_eq = reconstructed_bal  # InpDailyResetMode == 1 (FTMO Prague)

        if (
            prev_day_key == -1
            and "NQXG_ACCT_DAYKEY" in self.gv
            and int(self.gv["NQXG_ACCT_DAYKEY"]) == today
            and "NQXG_ACCT_AUTOKILL" in self.gv
        ):
            self.auto_kill_active = self.gv["NQXG_ACCT_AUTOKILL"] >= 1.0
        elif is_new_day:
            self.auto_kill_active = False
            self.persist_auto_kill(today, False)


# =============================================================================
# 3. Sub-Second Floor-Pierce-and-Rebound Fixture (Astra Note #3)
# =============================================================================

def simulate_subsecond_pierce_vs_ea_1s_throttle(
    ticks_ms_equity: list[tuple[int, float]],
    *,
    day_anchor_balance: float = 10000.0,
    initial_balance: float = 10000.0,
    firm_daily_limit_pct: float = 5.0,
    bot_kill_daily_pct: float = 3.5,
) -> dict[str, object]:
    """Compare raw tick-stream floor breach vs EA OnTick 1s-throttled (`Naqex_Master_Prop7E.mq5:879-887`) observation."""
    firm_floor = day_anchor_balance - initial_balance * (firm_daily_limit_pct / 100.0)
    bot_kill_floor = day_anchor_balance - initial_balance * (bot_kill_daily_pct / 100.0)

    raw_firm_breach_ms: int | None = None
    raw_bot_kill_cross_ms: int | None = None
    ea_last_sec: int | None = None
    ea_observed_firm_breach_ms: int | None = None
    ea_observed_bot_kill_ms: int | None = None
    ticks_processed_by_ea = 0

    for ts_ms, eq in ticks_ms_equity:
        if raw_firm_breach_ms is None and eq < firm_floor:
            raw_firm_breach_ms = ts_ms
        if raw_bot_kill_cross_ms is None and eq <= bot_kill_floor:
            raw_bot_kill_cross_ms = ts_ms

        sec = ts_ms // 1000
        if sec == ea_last_sec:
            continue  # Exact mirror of Naqex_Master_Prop7E.mq5:885 (`if(cur == s_lastTesterSec) return;`)
        ea_last_sec = sec
        ticks_processed_by_ea += 1
        if ea_observed_firm_breach_ms is None and eq < firm_floor:
            ea_observed_firm_breach_ms = ts_ms
        if ea_observed_bot_kill_ms is None and eq <= bot_kill_floor:
            ea_observed_bot_kill_ms = ts_ms

    return {
        "total_ticks": len(ticks_ms_equity),
        "ticks_processed_by_ea_1s_throttle": ticks_processed_by_ea,
        "raw_tick_stream_firm_breach_ms": raw_firm_breach_ms,
        "raw_tick_stream_bot_kill_cross_ms": raw_bot_kill_cross_ms,
        "ea_ontick_1s_observed_firm_breach_ms": ea_observed_firm_breach_ms,
        "ea_ontick_1s_observed_bot_kill_ms": ea_observed_bot_kill_ms,
        "intra_second_breach_missed_by_ea": (raw_firm_breach_ms is not None and ea_observed_firm_breach_ms is None),
    }


# =============================================================================
# 4. Comprehensive Test Suite
# =============================================================================

class StandardParityAndBoundaryTests(unittest.TestCase):
    def test_ftmo_standard_10k_contract_and_three_c10_presets(self) -> None:
        cfg = json.loads((AI_ENGINES / "configs/prop_contracts_v2.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["order_send_count"], 0)
        self.assertIn("ftmo_standard_10k", cfg["contracts"])
        c = cfg["contracts"]["ftmo_standard_10k"]
        self.assertEqual(c["profile_mode"], "Standard")
        self.assertEqual(c["leverage_fx"], 100)
        self.assertEqual(c["leverage_indices"], 50)
        self.assertEqual(c["leverage_metals"], 30)
        self.assertEqual(c["p1_target_pct"], 10.0)
        self.assertEqual(c["p2_target_pct"], 5.0)
        self.assertEqual(c["daily_dd_limit_pct"], 5.0)
        self.assertEqual(c["static_dd_limit_pct"], 10.0)
        self.assertEqual(c["official_floor_breach_operator"], "STRICT_LT")
        self.assertEqual(c["daily_reset_tz"], "Europe/Prague")
        self.assertTrue(c["news_policy_by_phase"]["p1"]["firm_news_allowed"])
        self.assertTrue(c["news_policy_by_phase"]["p2"]["firm_news_allowed"])
        self.assertFalse(c["news_policy_by_phase"]["funded"]["firm_news_allowed"])
        self.assertEqual(c["news_policy_by_phase"]["funded"]["firm_restricted_sec"], 120)
        self.assertEqual(c["news_policy_by_phase"]["funded"]["naqex_bot_guard_pad_sec"], 300)
        self.assertEqual(c["fee_pricing_tag"], "MODEL_ASSUMPTION")
        self.assertEqual(c["unpaid_bill_hold_tag"], "MODEL_ASSUMPTION")
        self.assertAlmostEqual(c["fee_eur"], 98.70, places=2)
        self.assertEqual(c["unpaid_bill_hold_calendar_days"], 14)

        # Verify all 3 C10 presets exist, are valid MQL5 inputs, DryRun=true, and zero OPSEC/bare $
        master_keys = (
            set(parity.parse_mq5_source(EXPORTS_DIR / "Naqex_Master_Prop7E.mq5")["inputs"])
            | set(parity.parse_mq5_source(EXPORTS_DIR / "Include/Naqex_PropGuard.mqh")["inputs"])
        )
        c10_expected = {
            "FTMO_Std10K_MasterProp7E_C10_P1_4x_L70.set": {
                "news": "true", "mult": 4.00, "tgt": 10.00, "pl_pct": 7.00, "pl_mult": 2.50,
                "k_day": 3.50, "k_st": 8.00, "caps": (1.75, 2.25, 2.00, 1.75, 3.00),
            },
            "FTMO_Std10K_MasterProp7E_C10_P2_35x.set": {
                "news": "true", "mult": 3.50, "tgt": 5.00, "pl_pct": 3.50, "pl_mult": 1.75,
                "k_day": 3.00, "k_st": 7.50, "caps": (1.75, 2.25, 2.00, 1.75, 3.00),
            },
            "FTMO_Std10K_MasterProp7E_C10_Funded_125x.set": {
                "news": "true", "mult": 1.25, "tgt": 0.00, "pl_pct": 0.00, "pl_mult": 1.25,
                "k_day": 2.50, "k_st": 7.50, "caps": (1.25, 1.75, 1.50, 1.25, 2.25),
            },
        }
        presets_dir = EXPORTS_DIR / "deployment_kit/presets"
        for fname, exp in c10_expected.items():
            p = presets_dir / fname
            self.assertTrue(p.is_file(), f"Missing C10 preset: {fname}")
            raw = p.read_text(encoding="utf-8")
            self.assertNotIn("$", raw)
            kv = kit.parse_set_file(p)
            self.assertEqual(set(kv) - master_keys, set(), f"Unknown keys in {fname}")
            self.assertEqual(kv["InpDryRunLogOnly"], "true")
            self.assertEqual(kv["InpGuardDryRunLogOnly"], "true")
            self.assertEqual(kv["InpGuardEnableRedNews"], exp["news"])
            self.assertAlmostEqual(float(kv["InpBasePhaseMult"]), exp["mult"], places=2)
            self.assertAlmostEqual(float(kv["InpTargetProfitPct"]), exp["tgt"], places=2)
            self.assertAlmostEqual(float(kv["InpProfitLockPct"]), exp["pl_pct"], places=2)
            self.assertAlmostEqual(float(kv["InpProfitLockMult"]), exp["pl_mult"], places=2)
            self.assertAlmostEqual(float(kv["InpKillDailyDdPct"]), exp["k_day"], places=2)
            self.assertAlmostEqual(float(kv["InpKillStaticDdPct"]), exp["k_st"], places=2)
            self.assertAlmostEqual(float(kv["InpGuardMaxDailyLossPct"]), exp["k_day"], places=2)
            sym_r, usd_c, jpy_c, idx_c, tot_r = exp["caps"]
            self.assertAlmostEqual(float(kv["InpMaxSymbolRiskPct"]), sym_r, places=2)
            self.assertAlmostEqual(float(kv["InpGuardMaxSymbolRiskPct"]), sym_r, places=2)
            self.assertAlmostEqual(float(kv["InpMaxUsdClusterPct"]), usd_c, places=2)
            self.assertAlmostEqual(float(kv["InpMaxJpyClusterPct"]), jpy_c, places=2)
            self.assertAlmostEqual(float(kv["InpMaxIdxClusterPct"]), idx_c, places=2)
            self.assertAlmostEqual(float(kv["InpMaxAccountOpenRiskPct"]), tot_r, places=2)

    def test_step2a_profile_switch_margin_and_silent_fallback_proof(self) -> None:
        # Astra R3 Note #2: passing "ftmo_standard_10k" directly to p27.margin_per_lot_usd silently falls back to Swing!
        for asset, px in (("USDJPY", 145.90), ("GBPUSD", 1.3125), ("EURJPY", 162.47), ("US100.cash", 19102.15)):
            m_swing = p27.margin_per_lot_usd(asset, px, "Swing")[0]
            m_std = p27.margin_per_lot_usd(asset, px, "Standard")[0]
            m_bad = p27.margin_per_lot_usd(asset, px, "ftmo_standard_10k")[0]
            self.assertAlmostEqual(m_bad, m_swing, places=6, msg=f"Silent fallback check failed for {asset}")
            self.assertAlmostEqual(m_swing / m_std, 100.0 / 30.0, places=4, msg=f"3.3333x margin ratio failed for {asset}")

    def test_two_sided_daily_dd_boundaries_and_bot_kill_separation(self) -> None:
        # Day anchor = 10,000.00 -> 5% daily floor = 9,500.00; bot auto-kill @ 3.5% = 9,650.00
        above = evaluate_ftmo_dd_boundaries(initial_balance=10000.0, day_anchor_balance=10000.0, equity=9500.01)
        exact = evaluate_ftmo_dd_boundaries(initial_balance=10000.0, day_anchor_balance=10000.0, equity=9500.00)
        below = evaluate_ftmo_dd_boundaries(initial_balance=10000.0, day_anchor_balance=10000.0, equity=9499.99)
        gap = evaluate_ftmo_dd_boundaries(initial_balance=10000.0, day_anchor_balance=10000.0, equity=9350.00)
        bot_only = evaluate_ftmo_dd_boundaries(initial_balance=10000.0, day_anchor_balance=10000.0, equity=9650.00)

        # +0.01 USD above floor -> NO_BREACH in both official & runner, BOT_AUTO_KILL already True (4.9999% >= 3.5%)
        self.assertFalse(above["FIRM_HARD_BREACH_DAILY_OFFICIAL_LT"])
        self.assertFalse(above["FIRM_HARD_BREACH_DAILY_RUNNER_LE"])
        self.assertTrue(above["BOT_AUTO_KILL_DAILY"])

        # Exact 0.00 USD at floor -> CONTRAST official strict `<` (NO_BREACH) vs runner `<=` (FIRM_HARD_BREACH)
        self.assertFalse(exact["FIRM_HARD_BREACH_DAILY_OFFICIAL_LT"])
        self.assertTrue(exact["FIRM_HARD_BREACH_DAILY_RUNNER_LE"])
        self.assertTrue(exact["BOT_AUTO_KILL_DAILY"])

        # -0.01 USD below floor & gap-through -> FIRM_HARD_BREACH in both
        self.assertTrue(below["FIRM_HARD_BREACH_DAILY_OFFICIAL_LT"])
        self.assertTrue(below["FIRM_HARD_BREACH_DAILY_RUNNER_LE"])
        self.assertTrue(gap["FIRM_HARD_BREACH_DAILY_OFFICIAL_LT"])
        self.assertTrue(gap["FIRM_HARD_BREACH_DAILY_RUNNER_LE"])

        # BOT_AUTO_KILL (3.5%) strictly separated from FIRM_HARD_BREACH (5.0%)
        self.assertTrue(bot_only["BOT_AUTO_KILL_DAILY"])
        self.assertFalse(bot_only["FIRM_HARD_BREACH_DAILY_OFFICIAL_LT"])
        self.assertFalse(bot_only["FIRM_HARD_BREACH_DAILY_RUNNER_LE"])

        # Shifted day anchor (profit carried over: day_anchor_balance = 10,400 -> floor = 9,900.00)
        shifted_exact = evaluate_ftmo_dd_boundaries(initial_balance=10000.0, day_anchor_balance=10400.0, equity=9900.00)
        shifted_below = evaluate_ftmo_dd_boundaries(initial_balance=10000.0, day_anchor_balance=10400.0, equity=9899.99)
        self.assertEqual(shifted_exact["daily_floor_usd"], 9900.00)
        self.assertFalse(shifted_exact["FIRM_HARD_BREACH_DAILY_OFFICIAL_LT"])
        self.assertTrue(shifted_exact["FIRM_HARD_BREACH_DAILY_RUNNER_LE"])
        self.assertTrue(shifted_below["FIRM_HARD_BREACH_DAILY_OFFICIAL_LT"])

    def test_two_sided_static_dd_boundaries_and_bot_kill_separation(self) -> None:
        # Day anchor = 9,300.00 (down -7% prior days), Static floor = 9,000.00; bot static kill @ 8.0% = 9,200.00
        bot_only = evaluate_ftmo_dd_boundaries(initial_balance=10000.0, day_anchor_balance=9300.0, equity=9200.00)
        above = evaluate_ftmo_dd_boundaries(initial_balance=10000.0, day_anchor_balance=9300.0, equity=9000.01)
        exact = evaluate_ftmo_dd_boundaries(initial_balance=10000.0, day_anchor_balance=9300.0, equity=9000.00)
        below = evaluate_ftmo_dd_boundaries(initial_balance=10000.0, day_anchor_balance=9300.0, equity=8999.99)
        gap = evaluate_ftmo_dd_boundaries(initial_balance=10000.0, day_anchor_balance=9300.0, equity=8800.00)

        self.assertTrue(bot_only["BOT_AUTO_KILL_STATIC"])
        self.assertFalse(bot_only["FIRM_HARD_BREACH_STATIC_OFFICIAL_LT"])
        self.assertFalse(bot_only["FIRM_HARD_BREACH_DAILY_OFFICIAL_LT"])

        self.assertFalse(above["FIRM_HARD_BREACH_STATIC_OFFICIAL_LT"])
        self.assertFalse(above["FIRM_HARD_BREACH_STATIC_RUNNER_LE"])

        # Exact 0.00 USD at static floor -> contrast strict `<` vs `<=`
        self.assertFalse(exact["FIRM_HARD_BREACH_STATIC_OFFICIAL_LT"])
        self.assertTrue(exact["FIRM_HARD_BREACH_STATIC_RUNNER_LE"])

        self.assertTrue(below["FIRM_HARD_BREACH_STATIC_OFFICIAL_LT"])
        self.assertTrue(below["FIRM_HARD_BREACH_STATIC_RUNNER_LE"])
        self.assertTrue(gap["FIRM_HARD_BREACH_STATIC_OFFICIAL_LT"])
        self.assertTrue(gap["FIRM_HARD_BREACH_STATIC_RUNNER_LE"])

    def test_prague_midnight_reset_spring_23h_and_fall_25h_dst(self) -> None:
        # Spring 2024 DST Sunday: 2024-03-31 (CET +1 -> CEST +2 at 01:00 UTC; 23h day!)
        sp_before = int(datetime(2024, 3, 30, 22, 59, 59, tzinfo=timezone.utc).timestamp())
        sp_start = int(datetime(2024, 3, 30, 23, 0, 0, tzinfo=timezone.utc).timestamp())
        sp_after_jump = int(datetime(2024, 3, 31, 1, 0, 0, tzinfo=timezone.utc).timestamp())
        sp_last_sec = int(datetime(2024, 3, 31, 21, 59, 59, tzinfo=timezone.utc).timestamp())
        sp_next_start = int(datetime(2024, 3, 31, 22, 0, 0, tzinfo=timezone.utc).timestamp())

        self.assertEqual(sp_next_start - sp_start, 23 * 3600)
        dk_bef, _ = mql5_prague_day_key_and_reset_start_utc(sp_before)
        dk_st, rs_st = mql5_prague_day_key_and_reset_start_utc(sp_start)
        dk_jmp, rs_jmp = mql5_prague_day_key_and_reset_start_utc(sp_after_jump)
        dk_end, rs_end = mql5_prague_day_key_and_reset_start_utc(sp_last_sec)
        dk_nxt, rs_nxt = mql5_prague_day_key_and_reset_start_utc(sp_next_start)

        self.assertNotEqual(dk_bef, dk_st)
        self.assertEqual(dk_st, dk_jmp)
        self.assertEqual(dk_st, dk_end)
        self.assertNotEqual(dk_end, dk_nxt)
        self.assertEqual(rs_st, sp_start)
        self.assertEqual(rs_jmp, sp_start)
        self.assertEqual(rs_end, sp_start)
        self.assertEqual(rs_nxt, sp_next_start)
        self.assertEqual(rs_nxt - rs_st, 23 * 3600)

        # Cross-verify against ZoneInfo("Europe/Prague")
        self.assertEqual(datetime.fromtimestamp(sp_before, timezone.utc).astimezone(PRAGUE_TZ).date().isoformat(), "2024-03-30")
        self.assertEqual(datetime.fromtimestamp(sp_start, timezone.utc).astimezone(PRAGUE_TZ).date().isoformat(), "2024-03-31")
        self.assertEqual(datetime.fromtimestamp(sp_last_sec, timezone.utc).astimezone(PRAGUE_TZ).date().isoformat(), "2024-03-31")
        self.assertEqual(datetime.fromtimestamp(sp_next_start, timezone.utc).astimezone(PRAGUE_TZ).date().isoformat(), "2024-04-01")

        # Fall 2024 DST Sunday: 2024-10-27 (CEST +2 -> CET +1 at 01:00 UTC; 25h day!)
        fl_before = int(datetime(2024, 10, 26, 21, 59, 59, tzinfo=timezone.utc).timestamp())
        fl_start = int(datetime(2024, 10, 26, 22, 0, 0, tzinfo=timezone.utc).timestamp())
        fl_after_jump = int(datetime(2024, 10, 27, 1, 0, 0, tzinfo=timezone.utc).timestamp())
        fl_last_sec = int(datetime(2024, 10, 27, 22, 59, 59, tzinfo=timezone.utc).timestamp())
        fl_next_start = int(datetime(2024, 10, 27, 23, 0, 0, tzinfo=timezone.utc).timestamp())

        self.assertEqual(fl_next_start - fl_start, 25 * 3600)
        fdk_bef, _ = mql5_prague_day_key_and_reset_start_utc(fl_before)
        fdk_st, frs_st = mql5_prague_day_key_and_reset_start_utc(fl_start)
        fdk_jmp, frs_jmp = mql5_prague_day_key_and_reset_start_utc(fl_after_jump)
        fdk_end, frs_end = mql5_prague_day_key_and_reset_start_utc(fl_last_sec)
        fdk_nxt, frs_nxt = mql5_prague_day_key_and_reset_start_utc(fl_next_start)

        self.assertNotEqual(fdk_bef, fdk_st)
        self.assertEqual(fdk_st, fdk_jmp)
        self.assertEqual(fdk_st, fdk_end)
        self.assertNotEqual(fdk_end, fdk_nxt)
        self.assertEqual(frs_st, fl_start)
        self.assertEqual(frs_jmp, fl_start)
        self.assertEqual(frs_end, fl_start)
        self.assertEqual(frs_nxt, fl_next_start)
        self.assertEqual(frs_nxt - frs_st, 25 * 3600)

        self.assertEqual(datetime.fromtimestamp(fl_before, timezone.utc).astimezone(PRAGUE_TZ).date().isoformat(), "2024-10-26")
        self.assertEqual(datetime.fromtimestamp(fl_start, timezone.utc).astimezone(PRAGUE_TZ).date().isoformat(), "2024-10-27")
        self.assertEqual(datetime.fromtimestamp(fl_last_sec, timezone.utc).astimezone(PRAGUE_TZ).date().isoformat(), "2024-10-27")
        self.assertEqual(datetime.fromtimestamp(fl_next_start, timezone.utc).astimezone(PRAGUE_TZ).date().isoformat(), "2024-10-28")

    def test_phase_transition_blocked_while_open_position_active(self) -> None:
        # P1 hits +10.25% floating equity while open_positions_count == 1 -> MUST NOT transition
        p1_open = evaluate_phase_transition(
            stage="P1", initial_balance=10000.0, realized_balance=10850.0,
            floating_equity=11025.0, open_positions_count=1, trading_days=6,
        )
        self.assertFalse(p1_open["transitioned"])
        self.assertEqual(p1_open["next_stage"], "P1")
        self.assertEqual(p1_open["reason"], "OPEN_POSITION_ACTIVE_HOLD")

        # Pullback before close -> realized 10,980 flat -> still P1
        p1_pullback = evaluate_phase_transition(
            stage="P1", initial_balance=10000.0, realized_balance=10980.0,
            floating_equity=10980.0, open_positions_count=0, trading_days=6,
        )
        self.assertFalse(p1_pullback["transitioned"])
        self.assertEqual(p1_pullback["next_stage"], "P1")

        # Flat at +10.05% with >=4 trading days -> transitions P1 -> P2
        p1_done = evaluate_phase_transition(
            stage="P1", initial_balance=10000.0, realized_balance=11005.0,
            floating_equity=11005.0, open_positions_count=0, trading_days=6,
        )
        self.assertTrue(p1_done["transitioned"])
        self.assertEqual(p1_done["next_stage"], "P2")

        # P2 hits +5.15% floating equity while open_positions_count == 1 -> MUST NOT transition
        p2_open = evaluate_phase_transition(
            stage="P2", initial_balance=10000.0, realized_balance=10420.0,
            floating_equity=10515.0, open_positions_count=1, trading_days=5,
        )
        self.assertFalse(p2_open["transitioned"])
        self.assertEqual(p2_open["next_stage"], "P2")
        self.assertEqual(p2_open["reason"], "OPEN_POSITION_ACTIVE_HOLD")

        # P2 flat at +5.02% with >=4 trading days -> transitions P2 -> FUNDED
        p2_done = evaluate_phase_transition(
            stage="P2", initial_balance=10000.0, realized_balance=10502.0,
            floating_equity=10502.0, open_positions_count=0, trading_days=5,
        )
        self.assertTrue(p2_done["transitioned"])
        self.assertEqual(p2_done["next_stage"], "FUNDED")

    def test_restart_hydration_r1_and_r2_offline_fixtures_and_tester_skip_proof(self) -> None:
        # 1. Source verification: BOTH R1 and R2 are explicitly SKIPPED_IN_TESTER!
        sig_src = (EXPORTS_DIR / "Include/Naqex_Signals_7E.mqh").read_text(encoding="utf-8")
        ea_src = (EXPORTS_DIR / "Naqex_Master_Prop7E.mq5").read_text(encoding="utf-8")
        self.assertRegex(sig_src, r"bool HydrateTradedDaysFromHistory[\s\S]{0,180}if\(MQLInfoInteger\(MQL_TESTER\)\)")
        self.assertRegex(ea_src, r"void PersistAutoKillStateM[\s\S]{0,120}if\(MQLInfoInteger\(MQL_TESTER\)")
        self.assertRegex(ea_src, r"void RestoreOrInitDayAnchorM[\s\S]{0,700}if\(!MQLInfoInteger\(MQL_TESTER\)\)")

        # 2. R1 Fixture: already-filled E1 deal earlier today -> restart blocks duplicate same-day trade
        t_fill = int(datetime(2024, 9, 3, 3, 15, 0, tzinfo=timezone.utc).timestamp())
        t_restart = int(datetime(2024, 9, 3, 5, 30, 0, tzinfo=timezone.utc).timestamp())
        utc_day = t_restart - (t_restart % 86400)
        d1_start = int(datetime(2024, 9, 2, 21, 0, 0, tzinfo=timezone.utc).timestamp())

        r1 = OfflineHydrationModelR1()
        # Fail-closed when HistorySelect fails
        self.assertFalse(r1.hydrate_from_history(t_restart, [], [], d1_bar_start_utc=d1_start, history_select_ok=False))
        self.assertFalse(r1.can_engine_trade(20261122, utc_day))
        self.assertFalse(r1.can_engine_trade(20261123, d1_start))

        # Succeeds when HistorySelect returns morning E1 fill -> blocks E1 duplicate, permits E2
        ok = r1.hydrate_from_history(
            t_restart,
            [MockDeal(magic=20261122, entry="IN", dtype="SELL", deal_utc=t_fill)],
            open_pos_magics=[],
            d1_bar_start_utc=d1_start,
            history_select_ok=True,
        )
        self.assertTrue(ok)
        self.assertFalse(r1.can_engine_trade(20261122, utc_day))  # E1 duplicate BLOCKED!
        self.assertTrue(r1.can_engine_trade(20261123, d1_start))  # E2 still allowed

        # 3. R2 Fixture: mid-day realized loss + auto-kill persisted -> restart reconstructs bal - todayRealized & stays locked
        gv_disk: dict[str, float] = {}
        t_midday = int(datetime(2024, 9, 3, 14, 0, 0, tzinfo=timezone.utc).timestamp())
        dk_today, _ = mql5_prague_day_key_and_reset_start_utc(t_midday)
        deals_today = [
            MockDeal(magic=20261122, entry="OUT", dtype="BUY", deal_utc=t_midday - 3600, profit=-355.0, swap=0.0, commission=-5.0),
        ]
        # Before restart: EA hits daily kill (>= 3.5%) and persists GV
        ea_before = OfflineAnchorAndAutoKillModelR2(gv_disk)
        ea_before.restore_or_init_day_anchor(t_midday - 7200, 10000.0, 10000.0, [])
        ea_before.auto_kill_active = True
        ea_before.persist_auto_kill(dk_today, True)

        # Mid-day restart: fresh RAM object reads bal=9640.00 + todayRealized=-360.00 + GV store
        ea_after = OfflineAnchorAndAutoKillModelR2(gv_disk)
        ea_after.restore_or_init_day_anchor(t_midday, 9640.0, 9640.0, deals_today)
        self.assertAlmostEqual(ea_after.day_anchor_bal, 10000.0, places=6)
        self.assertAlmostEqual(ea_after.day_anchor_eq, 10000.0, places=6)
        self.assertTrue(ea_after.auto_kill_active)  # MUST remain locked same Prague day!

        # Next Prague midnight (2024-09-04 00:00:00 CEST = 2024-09-03 22:00:00 UTC) -> unlocks cleanly!
        t_next_day = int(datetime(2024, 9, 3, 22, 0, 5, tzinfo=timezone.utc).timestamp())
        ea_after.restore_or_init_day_anchor(t_next_day, 9640.0, 9640.0, [])
        self.assertFalse(ea_after.auto_kill_active)
        self.assertAlmostEqual(ea_after.day_anchor_bal, 9640.0, places=6)
        self.assertEqual(gv_disk["NQXG_ACCT_AUTOKILL"], 0.0)

    def test_astra_r3_note3_tester_observability_and_subsecond_pierce_lag(self) -> None:
        ea_src = (EXPORTS_DIR / "Naqex_Master_Prop7E.mq5").read_text(encoding="utf-8")
        pg_src = (EXPORTS_DIR / "Include/Naqex_PropGuard.mqh").read_text(encoding="utf-8")

        # Confirm LogMasterShadowRow early-returns in MQL_TESTER and OnTick throttles to 1 tick/sec
        self.assertRegex(ea_src, r"void LogMasterShadowRow[\s\S]{0,250}if\(MQLInfoInteger\(MQL_TESTER\)\) return;")
        self.assertRegex(ea_src, r"void OnTick\(\)[\s\S]{0,250}s_lastTesterSec[\s\S]{0,120}if\(cur == s_lastTesterSec\) return;")
        self.assertRegex(pg_src, r"void LogExecAuditFor[\s\S]{0,450}if\(MQLInfoInteger\(MQL_TESTER\)\) return;")

        # Sub-second floor-pierce-and-rebound: pierces 9500 floor at .350ms, rebounds to 9520 by next second
        ticks = [
            (1725364801000, 9700.00),  # 12:00:01.000 -> EA processes this tick (safe)
            (1725364801250, 9620.00),  # 12:00:01.250 -> crosses bot kill (9650), SKIPPED by EA 1s throttle
            (1725364801350, 9498.50),  # 12:00:01.350 -> PIERCES FTMO 5% floor (9500), SKIPPED by EA 1s throttle!
            (1725364801800, 9530.00),  # 12:00:01.800 -> rebounds above floor, SKIPPED
            (1725364802000, 9520.00),  # 12:00:02.000 -> EA processes next second: sees bot kill, NEVER saw 5% pierce!
        ]
        res = simulate_subsecond_pierce_vs_ea_1s_throttle(ticks)
        self.assertEqual(res["raw_tick_stream_firm_breach_ms"], 1725364801350)
        self.assertEqual(res["raw_tick_stream_bot_kill_cross_ms"], 1725364801250)
        self.assertIsNone(res["ea_ontick_1s_observed_firm_breach_ms"])
        self.assertEqual(res["ea_ontick_1s_observed_bot_kill_ms"], 1725364802000)
        self.assertTrue(res["intra_second_breach_missed_by_ea"])

    def test_step2b_ea_sizing_and_85pct_margin_scaledown_vs_step2a(self) -> None:
        # Exact Deal #2 from MT5 2024-09-02 E1 USDJPY SELL @ 145.902, SL 146.550 (0.64% allowedRiskPct, bal=10000)
        sl_dist = 146.550 - 145.902
        tick_val = 100.0 / 145.902  # USDJPY tick value for tick_size=0.001, contract=100,000
        res = ea_step2b_compute_lots(
            account_balance=10000.0,
            allowed_risk_pct=0.64,
            sl_dist=sl_dist,
            tick_size=0.001,
            tick_value_loss=tick_val,
            free_margin=10000.0,
            margin_per_lot=1000.0,
        )
        self.assertEqual(res["status"], "ACCEPTED")
        self.assertAlmostEqual(res["lots"], 0.13, places=2)  # Exact match to MT5 deal #2 (0.13 lots)!
        self.assertFalse(res["margin_scaled"])

        # Margin scale-down <= 85% free margin (where Step 2A binary-rejects at >100% or allows up to 100%)
        tight = ea_step2b_compute_lots(
            account_balance=10000.0,
            allowed_risk_pct=1.75,
            sl_dist=0.50,
            tick_size=0.001,
            tick_value_loss=100.0 / 150.0,
            free_margin=400.0,  # 85% = 340 USD -> max 0.34 lots @ 1000 USD/lot
            margin_per_lot=1000.0,
        )
        self.assertEqual(tight["status"], "ACCEPTED")
        self.assertTrue(tight["margin_scaled"])
        self.assertAlmostEqual(tight["lots"], 0.34, places=2)


if __name__ == "__main__":
    unittest.main()
