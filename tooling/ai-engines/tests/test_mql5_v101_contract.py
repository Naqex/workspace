"""Pre-Compile MQL5 v1.01 Contract & Reference Math Test Harness (Offline Only, OrderSend = 0).

Covers:
  1. `V101-04`: Full 2026-2027 NYSE holiday & early-close calendar reference model
     (New Year, MLK, Presidents, Good Friday via Gregorian Easter, Memorial, Juneteenth,
      Independence Day, Labor, Thanksgiving, Black Friday early close, Christmas Eve/Day).
  2. `V101-03`: EU Europe/Prague DST exact Sunday midnight UTC offset verified across ALL 730 days
     of 2026-2027 against `zoneinfo.ZoneInfo("Europe/Prague")` (0-second error!).
  3. `V101-07`: `REL+HEADROOM` relative AMBER/RED multiplier + unconditional `dailyHeadroom < 2.0%` taper
     (`P1 4x AMBER=2.60x / RED=1.60x`, `Funded 1x AMBER=0.65x / RED=0.40x` unchanged!).
  4. `verify_v101_mq5_source_contract()`: auto-guarded so pytest passes cleanly while `v1.00` is frozen
     during Wave 1B, and flips automatically to strict `v1.01` enforcement as soon as `#property version "1.01"` lands!
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from zoneinfo import ZoneInfo

AI_ENGINES = Path(__file__).resolve().parents[1]
EXPORTS_DIR = AI_ENGINES / "exports"
PRAGUE_TZ = ZoneInfo("Europe/Prague")


# --- V101-04 Reference Model: Full NYSE Holiday & Early-Close Calendar (matches MQL5 algorithm) ---

def gregorian_easter_sunday(year: int) -> date:
    """Anonymous Gregorian algorithm (exact for MQL5 integer math porting)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _nth_weekday_of_month(year: int, month: int, weekday: int, nth: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + (nth - 1) * 7)


def _last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    last = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    offset = (last.weekday() - weekday) % 7
    return last - timedelta(days=offset)


def _observed_fixed(year: int, month: int, day: int) -> date:
    d = date(year, month, day)
    if d.weekday() == 5:  # Saturday -> Friday
        return d - timedelta(days=1)
    if d.weekday() == 6:  # Sunday -> Monday
        return d + timedelta(days=1)
    return d


def is_us_equity_holiday_or_early_close_ny(d: date) -> tuple[bool, str]:
    """Return (is_blocked, label) for NYSE full holidays & 13:00 ET early-close sessions."""
    y = d.year
    # Fixed holidays (observed)
    if d == _observed_fixed(y, 1, 1) or (d.month == 12 and d.day == 31 and date(y + 1, 1, 1).weekday() == 5):
        return True, "NEW_YEAR"
    if d == _nth_weekday_of_month(y, 1, 0, 3):  # 3rd Mon Jan
        return True, "MLK_DAY"
    if d == _nth_weekday_of_month(y, 2, 0, 3):  # 3rd Mon Feb
        return True, "PRESIDENTS_DAY"
    if d == gregorian_easter_sunday(y) - timedelta(days=2):
        return True, "GOOD_FRIDAY"
    if d == _last_weekday_of_month(y, 5, 0):  # Last Mon May
        return True, "MEMORIAL_DAY"
    if d == _observed_fixed(y, 6, 19):
        return True, "JUNETEENTH"
    july4_obs = _observed_fixed(y, 7, 4)
    if d == july4_obs:
        return True, "INDEPENDENCE_DAY"
    # NYSE early close on July 3 when July 4 is Tue..Fri (Mon=0..Fri=4)
    if date(y, 7, 4).weekday() in (1, 2, 3, 4) and d == date(y, 7, 3):
        return True, "JULY3_EARLY_CLOSE"
    if d == _nth_weekday_of_month(y, 9, 0, 1):  # 1st Mon Sep
        return True, "LABOR_DAY"
    thanksgiving = _nth_weekday_of_month(y, 11, 3, 4)  # 4th Thu Nov
    if d == thanksgiving:
        return True, "THANKSGIVING"
    if d == thanksgiving + timedelta(days=1):
        return True, "BLACK_FRIDAY_EARLY_CLOSE"
    xmas_obs = _observed_fixed(y, 12, 25)
    if d == xmas_obs:
        return True, "CHRISTMAS"
    # NYSE early close on Dec 24 when Dec 24 is a weekday and not already Christmas observed
    if d == date(y, 12, 24) and d.weekday() < 5:
        return True, "CHRISTMAS_EVE_EARLY_CLOSE"
    return False, ""


# --- V101-03 Reference Model: Exact EU Europe/Prague DST Midnight Offset ---

def last_sunday_of_month(year: int, month: int) -> int:
    last = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    # Python weekday: Mon=0..Sun=6 -> days since Sunday = (weekday + 1) % 7
    return last.day - ((last.weekday() + 1) % 7)


def prague_utc_offset_hours(utc_dt: datetime) -> int:
    """EU DST: CEST (+2) from last Sun Mar 01:00 UTC to last Sun Oct 01:00 UTC, else CET (+1)."""
    if utc_dt.month < 3 or utc_dt.month > 10:
        return 1
    if 3 < utc_dt.month < 10:
        return 2
    ls = last_sunday_of_month(utc_dt.year, utc_dt.month)
    if utc_dt.month == 3:
        return 2 if (utc_dt.day > ls or (utc_dt.day == ls and utc_dt.hour >= 1)) else 1
    return 2 if (utc_dt.day < ls or (utc_dt.day == ls and utc_dt.hour < 1)) else 1


def prague_midnight_utc_exact(now_utc: datetime) -> datetime:
    """Exact V101-03 Prague 00:00 local midnight converted to UTC using midnight's OWN DST offset!"""
    cur_off = prague_utc_offset_hours(now_utc)
    prg_now = now_utc + timedelta(hours=cur_off)
    # At 00:00 Prague local time on EU DST transition Sundays (last Sun Mar / Oct),
    # the clock switch has NOT occurred yet (switch happens at 02:00/03:00 Prague = 01:00 UTC)!
    # Therefore: on last Sun Mar 00:00 Prague -> CET (+1); on last Sun Oct 00:00 Prague -> CEST (+2)!
    y, m, d = prg_now.year, prg_now.month, prg_now.day
    if m < 3 or m > 10:
        mid_off = 1
    elif 3 < m < 10:
        mid_off = 2
    else:
        ls = last_sunday_of_month(y, m)
        if m == 3:
            mid_off = 2 if d > ls else 1  # On d == ls at 00:00 Prague, still CET (+1)!
        else:
            mid_off = 2 if d <= ls else 1  # On d == ls at 00:00 Prague, still CEST (+2)!
    prg_midnight_naive = datetime(y, m, d, 0, 0, 0, tzinfo=timezone.utc)
    return prg_midnight_naive - timedelta(hours=mid_off)


# --- V101-07 Reference Model: REL+HEADROOM Regime Multiplier ---

def compute_v101_risk_multiplier(
    *,
    base_mult: float,
    daily_dd_pct: float,
    static_dd_pct: float,
    profit_pct: float,
    kill_daily_dd_pct: float,
    kill_static_dd_pct: float = 8.0,
    amber_dd_pct: float = 3.50,
    amber_mult: float = 0.65,
    red_dd_pct: float = 6.00,
    red_mult: float = 0.40,
    profit_lock_pct: float = 5.00,
    profit_lock_mult: float = 2.01,
    target_profit_pct: float = 10.00,
    sizing_mode: int = 0,
) -> tuple[float, str]:
    """Exact V101-07 REL+HEADROOM formula: relative AMBER/RED scaling + unconditional dailyHeadroom < 2.0% taper."""
    mult = float(base_mult)
    regime = "NORMAL"
    if static_dd_pct >= red_dd_pct:
        mult = min(mult, base_mult * red_mult)
        regime = "RED_BRAKE"
    elif static_dd_pct >= amber_dd_pct:
        mult = min(mult, base_mult * amber_mult)
        regime = "AMBER_BRAKE"
    elif profit_lock_pct > 0.0 and profit_pct >= profit_lock_pct:
        mult = min(mult, profit_lock_mult)
        regime = "PROFIT_LOCK"

    # Unconditional dailyHeadroom < 2.0% taper (even when sizing_mode == 0!) -> 0.0% daily DD breaches!
    daily_headroom = max(0.0, kill_daily_dd_pct - daily_dd_pct)
    if daily_headroom < 2.0:
        daily_scale = max(0.25, daily_headroom / 2.0)
        mult = min(mult, base_mult * daily_scale)
        if regime == "NORMAL":
            regime = "DAILY_HEADROOM_TAPER"

    if sizing_mode == 1:
        static_headroom = max(0.0, kill_static_dd_pct - static_dd_pct)
        dd_scale = 1.0
        if static_headroom < 3.5:
            dd_scale = min(dd_scale, max(0.25, static_headroom / 3.5))
        if target_profit_pct > 0.0 and profit_pct > 0.0:
            rem = max(0.0, target_profit_pct - profit_pct)
            frac_rem = rem / target_profit_pct
            if frac_rem < 0.35:
                dd_scale = min(dd_scale, max(0.35, frac_rem / 0.35))
        mult = min(mult, base_mult * dd_scale)
        if dd_scale < 0.99 and regime == "NORMAL":
            regime = "BARRIER_TAPER"

    return round(max(0.0, mult), 4), regime


# --- Guarded v1.01 MQL5 Source Contract Verifier ---

V101_REQUIRED_TOKENS: dict[str, tuple[str, ...]] = {
    "Naqex_Master_Prop7E.mq5": (
        "HydrateTradedDaysFromHistory",
        "CancelPendingOrdersByReason",
        "InpBasePhaseMult * InpAmberMult",
        "InpBasePhaseMult * InpRedMult",
        "DAILY_HEADROOM_TAPER",
        "SetDeviationInPoints",
        "InpMaxSlippagePointsFx",
        "InpMaxSlippagePointsIdx",
        "RoundVolumeDownToStep",
        "reqMargin <= 0.0",
        "AcctAutoKillKey",
        "PragueMidnightUtcOffsetHoursM",
        "DEAL_POSITION_ID",
        "ORDER_FILL_RECONCILED",
        "IsInsideRedNewsHardBanFor",
    ),
    "Include/Naqex_Signals_7E.mqh": (
        "HydrateTradedDaysFromHistory",
        "IsTradedDayHydrated",
        "WEEKEND_GAP_FAILSAFE_SWAP0",
        "IsUsEquityHolidayOrHalfDayNY",
        "CNaqexPropGuard::ServerNow()",
    ),
    "Include/Naqex_PropGuard.mqh": (
        "magicOverride",
        "TimeTradeServer",
        "ServerNow",
        "IsInsideRedNewsHardBanFor",
        "IsUsEquityHolidayOrHalfDayNY",
        "GregorianEasterSunday",
        "RoundVolumeDownToStep",
        "ConfigureDeviationPoints",
        "reqMargin <= 0.0",
    ),
}


def verify_v101_mq5_source_contract(exports_dir: Path = EXPORTS_DIR) -> dict:
    """Auto-guarded source contract: reports V100_FROZEN_PRE_APPLY on v1.00, enforces all 7 patches strictly on >= v1.01."""
    master_path = exports_dir / "Naqex_Master_Prop7E.mq5"
    raw_master = master_path.read_text(encoding="utf-8")
    m_ver = re.search(r'#property\s+version\s+"([^"]+)"', raw_master)
    version = m_ver.group(1) if m_ver else "0.00"

    missing: list[str] = []
    for rel_file, tokens in V101_REQUIRED_TOKENS.items():
        txt = (exports_dir / rel_file).read_text(encoding="utf-8")
        for tok in tokens:
            if tok not in txt:
                missing.append(f"{rel_file}: missing '{tok}'")

    is_v101_or_higher = tuple(int(x) for x in version.split(".")[:2]) >= (1, 1)
    if not is_v101_or_higher:
        return {
            "version": version,
            "enforced": False,
            "ok": True,
            "status": "V100_FROZEN_PRE_APPLY",
            "pending_v101_tokens": missing,
        }
    return {
        "version": version,
        "enforced": True,
        "ok": len(missing) == 0,
        "status": "V101_CONTRACT_PASS" if not missing else "V101_CONTRACT_FAIL",
        "missing_v101_tokens": missing,
    }


class Mql5V101ContractTests(unittest.TestCase):
    def test_v101_04_nyse_2026_2027_holidays_and_early_closes(self):
        expected_blocked = {
            # 2026
            date(2026, 1, 1): "NEW_YEAR",
            date(2026, 1, 19): "MLK_DAY",
            date(2026, 2, 16): "PRESIDENTS_DAY",
            date(2026, 4, 3): "GOOD_FRIDAY",
            date(2026, 5, 25): "MEMORIAL_DAY",
            date(2026, 6, 19): "JUNETEENTH",
            date(2026, 7, 3): "INDEPENDENCE_DAY",
            date(2026, 9, 7): "LABOR_DAY",
            date(2026, 11, 26): "THANKSGIVING",
            date(2026, 11, 27): "BLACK_FRIDAY_EARLY_CLOSE",
            date(2026, 12, 24): "CHRISTMAS_EVE_EARLY_CLOSE",
            date(2026, 12, 25): "CHRISTMAS",
            # 2027
            date(2027, 1, 1): "NEW_YEAR",
            date(2027, 1, 18): "MLK_DAY",
            date(2027, 2, 15): "PRESIDENTS_DAY",
            date(2027, 3, 26): "GOOD_FRIDAY",
            date(2027, 5, 31): "MEMORIAL_DAY",
            date(2027, 6, 18): "JUNETEENTH",
            date(2027, 7, 5): "INDEPENDENCE_DAY",
            date(2027, 9, 6): "LABOR_DAY",
            date(2027, 11, 25): "THANKSGIVING",
            date(2027, 11, 26): "BLACK_FRIDAY_EARLY_CLOSE",
            date(2027, 12, 24): "CHRISTMAS",
        }
        for dt_d, exp_lbl in expected_blocked.items():
            blocked, lbl = is_us_equity_holiday_or_early_close_ny(dt_d)
            self.assertTrue(blocked, f"Expected NYSE block on {dt_d} ({exp_lbl})")
            self.assertEqual(lbl, exp_lbl, f"Label mismatch on {dt_d}: got {lbl} != {exp_lbl}")

        for normal_day in (date(2026, 11, 25), date(2026, 11, 30), date(2026, 7, 6), date(2027, 4, 1), date(2027, 11, 24)):
            blocked, lbl = is_us_equity_holiday_or_early_close_ny(normal_day)
            self.assertFalse(blocked, f"Normal trading day {normal_day} falsely blocked as {lbl}")

    def test_v101_03_prague_dst_midnight_exact_across_all_730_days_of_2026_2027(self):
        # Verify BOTH transition Sundays explicitly and every single day of 2026-2027 at 06:00 UTC against ZoneInfo!
        cur = datetime(2026, 1, 1, 6, 0, 0, tzinfo=timezone.utc)
        for _ in range(730):
            got_utc = prague_midnight_utc_exact(cur)
            prg_local = cur.astimezone(PRAGUE_TZ)
            exp_prg_mid = datetime(prg_local.year, prg_local.month, prg_local.day, 0, 0, 0, tzinfo=PRAGUE_TZ)
            exp_utc = exp_prg_mid.astimezone(timezone.utc)
            self.assertEqual(got_utc, exp_utc, f"Prague midnight mismatch on {cur.isoformat()}")
            cur += timedelta(days=1)

        # Explicit check on 2026 Spring Forward (29 Mar) and Fall Back (25 Oct) at 06:00 UTC
        self.assertEqual(prague_midnight_utc_exact(datetime(2026, 3, 29, 6, 0, tzinfo=timezone.utc)), datetime(2026, 3, 28, 23, 0, tzinfo=timezone.utc))
        self.assertEqual(prague_midnight_utc_exact(datetime(2026, 10, 25, 6, 0, tzinfo=timezone.utc)), datetime(2026, 10, 24, 22, 0, tzinfo=timezone.utc))

    def test_v101_07_rel_plus_headroom_multiplier_math(self):
        # P1 4.00x: AMBER -> 2.60x, RED -> 1.60x, PROFIT_LOCK -> 2.01x
        m_norm, r_norm = compute_v101_risk_multiplier(base_mult=4.0, daily_dd_pct=0.5, static_dd_pct=1.0, profit_pct=0.0, kill_daily_dd_pct=3.5)
        self.assertEqual((m_norm, r_norm), (4.0, "NORMAL"))

        m_amb, r_amb = compute_v101_risk_multiplier(base_mult=4.0, daily_dd_pct=0.5, static_dd_pct=4.0, profit_pct=0.0, kill_daily_dd_pct=3.5)
        self.assertEqual((m_amb, r_amb), (2.6, "AMBER_BRAKE"))

        m_red, r_red = compute_v101_risk_multiplier(base_mult=4.0, daily_dd_pct=0.5, static_dd_pct=6.5, profit_pct=0.0, kill_daily_dd_pct=3.5)
        self.assertEqual((m_red, r_red), (1.6, "RED_BRAKE"))

        m_pl, r_pl = compute_v101_risk_multiplier(base_mult=4.0, daily_dd_pct=0.2, static_dd_pct=0.0, profit_pct=5.5, kill_daily_dd_pct=3.5)
        self.assertEqual((m_pl, r_pl), (2.01, "PROFIT_LOCK"))

        # Funded 1.00x: AMBER -> 0.65x, RED -> 0.40x (100% unchanged vs v1.00!)
        m_f_amb, _ = compute_v101_risk_multiplier(base_mult=1.0, daily_dd_pct=0.2, static_dd_pct=4.0, profit_pct=0.0, kill_daily_dd_pct=2.5, profit_lock_pct=0.0)
        m_f_red, _ = compute_v101_risk_multiplier(base_mult=1.0, daily_dd_pct=0.2, static_dd_pct=6.5, profit_pct=0.0, kill_daily_dd_pct=2.5, profit_lock_pct=0.0)
        self.assertEqual(m_f_amb, 0.65)
        self.assertEqual(m_f_red, 0.40)

        # Unconditional dailyHeadroom < 2.0% taper even when sizing_mode=0!
        # kill_daily=3.5%, daily_dd=2.5% -> headroom=1.0% -> scale=0.50 -> 4.0 * 0.50 = 2.00x
        m_tap, r_tap = compute_v101_risk_multiplier(base_mult=4.0, daily_dd_pct=2.5, static_dd_pct=2.5, profit_pct=0.0, kill_daily_dd_pct=3.5, sizing_mode=0)
        self.assertEqual((m_tap, r_tap), (2.0, "DAILY_HEADROOM_TAPER"))
        # Tight headroom 0.1% -> floor scale 0.25 -> 1.00x
        m_flr, _ = compute_v101_risk_multiplier(base_mult=4.0, daily_dd_pct=3.4, static_dd_pct=4.0, profit_pct=0.0, kill_daily_dd_pct=3.5, sizing_mode=0)
        self.assertEqual(m_flr, 1.0)

    def test_v101_source_contract_guarded_on_frozen_v100_and_strict_on_v101(self):
        # 1. Real exports dir is now v1.01 -> MUST strictly enforce & PASS all 7 patch contracts!
        res = verify_v101_mq5_source_contract(EXPORTS_DIR)
        self.assertTrue(res["ok"], f"v1.01 source contract failed: {res}")
        self.assertEqual(res["version"], "1.01")
        self.assertTrue(res["enforced"])
        self.assertEqual(res["status"], "V101_CONTRACT_PASS")
        self.assertEqual(res["missing_v101_tokens"], [])

        # 2. Verify fail-closed defaults & live-calibrated US100 deviation buffer (>= 430 pts from live #330!)
        master_raw = (EXPORTS_DIR / "Naqex_Master_Prop7E.mq5").read_text(encoding="utf-8")
        guard_raw = (EXPORTS_DIR / "Include/Naqex_PropGuard.mqh").read_text(encoding="utf-8")
        self.assertRegex(master_raw, r"input\s+bool\s+InpDryRunLogOnly\s*=\s*true\s*;")
        self.assertRegex(master_raw, r"input\s+bool\s+InpShadowCompareMode\s*=\s*true\s*;")
        self.assertRegex(guard_raw, r"input\s+bool\s+InpGuardDryRunLogOnly\s*=\s*true\s*;")
        m_idx_dev = re.search(r"input\s+int\s+InpMaxSlippagePointsIdx\s*=\s*(\d+)\s*;", master_raw)
        self.assertIsNotNone(m_idx_dev)
        self.assertGreaterEqual(int(m_idx_dev.group(1)), 430)

        # 3. Negative contract check: stripping required v1.01 tokens on a v1.01 copy MUST FAIL strictly!
        with tempfile.TemporaryDirectory() as td:
            tmp_exp = Path(td) / "exports"
            shutil.copytree(EXPORTS_DIR / "Include", tmp_exp / "Include")
            shutil.copy2(EXPORTS_DIR / "Naqex_Master_Prop7E.mq5", tmp_exp / "Naqex_Master_Prop7E.mq5")

            mp = tmp_exp / "Naqex_Master_Prop7E.mq5"
            stripped = mp.read_text(encoding="utf-8")
            for tok in (
                "HydrateTradedDaysFromHistory",
                "CancelPendingOrdersByReason",
                "InpBasePhaseMult * InpAmberMult",
                "InpBasePhaseMult * InpRedMult",
                "SetDeviationInPoints",
                "AcctAutoKillKey",
            ):
                stripped = stripped.replace(tok, "REMOVED_FOR_TEST")
            mp.write_text(stripped, encoding="utf-8")
            bad = verify_v101_mq5_source_contract(tmp_exp)
            self.assertTrue(bad["enforced"])
            self.assertFalse(bad["ok"])
            self.assertEqual(bad["status"], "V101_CONTRACT_FAIL")
            self.assertGreaterEqual(len(bad["missing_v101_tokens"]), 6)


if __name__ == "__main__":
    unittest.main()
