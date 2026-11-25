"""Self-Verifying MT5 Deployment Kit Builder & Verifier for Naqex 8-EA + Orchestrator Suite (M1.3).

Manages:
  1. Complete `.set` preset pack for ALL 10 operational profiles:
       - FTMO_FreeTrial_DryRun
       - FTMO_FreeTrial_Demo
       - FTMO_P1_Balanced_3to6m
       - FTMO_P1_Sprint_1to3m
       - FTMO_P2_Verify
       - FTMO_Funded_Swing_Safe
       - FTMO_Funded_Std_RedNews
       - The5ers_HighStakes_P1_Balanced
       - The5ers_HighStakes_P1_Sprint
       - The5ers_HighStakes_Funded
  2. Cryptographic SHA-256 manifest (`deployment_kit/manifest.sha256.json`) covering
     all `.mq5` sources, `Include/Naqex_PropGuard.mqh`, all 90 `.set` presets,
     `ops_watchdog/naqex_mt5_watchdog.ps1`, `ACTIVATION-CARD-LOCAL-MT5.md`, and
     compiled `.ex5` binaries under `.runtime/mt5-compiled-ex5/`.
  3. Strict fail-closed kit verifier (`verify_kit()`):
       - Runs MQL5 <-> Python parity audit
       - Verifies every `.set` key exists in its target `.mq5` / `Naqex_PropGuard.mqh`
       - Verifies magic number match, US100 spread threshold (`>= 350.0` pts), SYMCAP_100,
         Red-News enforcement, and ARM-LOCKED safety (`InpDryRunLogOnly=true` on all
         paid Challenge/Funded profiles and FreeTrial_DryRun)
       - Verifies all SHA-256 hashes and enforces `< 900 KB` anti-bloat limit

Strictly offline & fail-closed (OrderSend = 0, zero broker connections).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

EXPORTS_DIR = Path(__file__).resolve().parent
AI_ENGINES_DIR = EXPORTS_DIR.parent
REPO_ROOT = AI_ENGINES_DIR.parents[1]
KIT_DIR = EXPORTS_DIR / "deployment_kit"
PRESETS_DIR = KIT_DIR / "presets"
MANIFEST_PATH = KIT_DIR / "manifest.sha256.json"
DEFAULT_EX5_DIR = REPO_ROOT / ".runtime/mt5-compiled-ex5"
REGISTRY_PATH = REPO_ROOT / "planning/research/PORTFOLIO-REGISTRY.json"
ANTI_BLOAT_LIMIT_BYTES = 900 * 1024

if str(EXPORTS_DIR) not in sys.path:
    sys.path.insert(0, str(EXPORTS_DIR))

import mql5_parity_checker as parity  # noqa: E402

# Calibrated operational profiles synced to M2.2 10k-path Dual-P1 EV Frontier (`seed=20261124`, Dev 2018-2024).
# Respects `Naqex_PropGuard.mqh` `NQXG_GLOBAL_RISK_MULT` safe clamp `[0.20, 3.50]` by factoring
# effective multipliers > 3.50x into `ea_risk_scale` (applied to each EA's `InpRiskPercent`)
# times `base_phase_mult` (`Orchestrator InpBasePhaseMult <= 3.50`).
# Safety policy:
#   - FTMO_FreeTrial_DryRun: InpDryRunLogOnly=true, InpGuardDryRunLogOnly=true (Day 1-2 shadow log check)
#   - FTMO_FreeTrial_Demo:   InpDryRunLogOnly=false, InpGuardDryRunLogOnly=false (Day 3-14 FTMO Free Trial Demo fills)
#   - Paid Challenge/Funded: ARM-LOCKED (InpDryRunLogOnly=true, InpGuardDryRunLogOnly=true) until owner manually
#                            disarms on MT5 Inputs tab after Free Trial PASS & TCA GREEN sign-off!
OPERATIONAL_PROFILES: dict[str, dict[str, Any]] = {
    "FTMO_FreeTrial_DryRun": {
        "firm": "FTMO",
        "account_type": "FreeTrial_10k_Shadow",
        "capital_usd": 10000.0,
        "portfolio": "PORT_7E_CORE_PLUS_S6_SHADOW",
        "include_s6": True,
        "dry_run_preset": True,
        "arm_locked": True,
        "ea_risk_scale": 1.00,
        "base_phase_mult": 1.00,
        "effective_mult": 1.00,
        "calibration_tag": "M2_2_SEED20261124_SYNCED",
        "amber_dd_pct": 3.50,
        "amber_mult": 0.65,
        "red_dd_pct": 6.00,
        "red_mult": 0.40,
        "profit_lock_pct": 0.00,
        "profit_lock_mult": 1.00,
        "daily_reset_mode": 1,
        "kill_daily_dd_pct": 2.50,
        "kill_static_dd_pct": 7.50,
        "ea_daily_stop_pct": 2.50,
        "max_symbol_risk_pct": 1.00,
        "enable_red_news": True,
        "news_pad_sec": 300,
        "news_hard_ban_sec": 135,
        "notes": "Day 1-2 local PC Free Trial shadow dry-run. Logs signals & heartbeat with OrderSend=0 (Prague reset).",
    },
    "FTMO_FreeTrial_Demo": {
        "firm": "FTMO",
        "account_type": "FreeTrial_10k_Demo",
        "capital_usd": 10000.0,
        "portfolio": "PORT_7E_CORE_PLUS_S6",
        "include_s6": True,
        "dry_run_preset": False,
        "arm_locked": False,
        "ea_risk_scale": 1.00,
        "base_phase_mult": 1.00,
        "effective_mult": 1.00,
        "calibration_tag": "M2_2_SEED20261124_SYNCED",
        "amber_dd_pct": 3.50,
        "amber_mult": 0.65,
        "red_dd_pct": 6.00,
        "red_mult": 0.40,
        "profit_lock_pct": 0.00,
        "profit_lock_mult": 1.00,
        "daily_reset_mode": 1,
        "kill_daily_dd_pct": 2.50,
        "kill_static_dd_pct": 7.50,
        "ea_daily_stop_pct": 2.50,
        "max_symbol_risk_pct": 1.00,
        "enable_red_news": True,
        "news_pad_sec": 300,
        "news_hard_ban_sec": 135,
        "notes": "Day 3-14 FTMO Free Trial Demo paper execution (real demo fills + naqex_exec_audit.csv TCA check, Prague reset).",
    },
    "FTMO_P1_Balanced_3to6m": {
        "firm": "FTMO",
        "account_type": "Challenge_P1_10k_Balanced",
        "capital_usd": 10000.0,
        "portfolio": "PORT_7E_CORE_PLUS_S6",
        "include_s6": True,
        "dry_run_preset": True,
        "arm_locked": True,
        "ea_risk_scale": 1.50,
        "base_phase_mult": 2.67,
        "effective_mult": 4.00,
        "calibration_tag": "M2_2_SEED20261124_SYNCED",
        "amber_dd_pct": 7.50,
        "amber_mult": 1.00,
        "red_dd_pct": 9.00,
        "red_mult": 0.75,
        "profit_lock_pct": 5.00,
        "profit_lock_mult": 1.34,
        "daily_reset_mode": 1,
        "kill_daily_dd_pct": 4.20,
        "kill_static_dd_pct": 9.20,
        "ea_daily_stop_pct": 4.20,
        "max_symbol_risk_pct": 1.75,
        "enable_red_news": True,
        "news_pad_sec": 300,
        "news_hard_ban_sec": 135,
        "notes": "FTMO P1 Balanced (eff 4.00x = 1.50x EA * 2.67x Orch; SYMCAP 1.75%, ProfitLock >=+5% -> 2.01x, Prague reset). ARM-LOCKED.",
    },
    "FTMO_P1_Sprint_1to3m": {
        "firm": "FTMO",
        "account_type": "Challenge_P1_10k_Sprint",
        "capital_usd": 10000.0,
        "portfolio": "PORT_7E_CORE_PLUS_S6",
        "include_s6": True,
        "dry_run_preset": True,
        "arm_locked": True,
        "ea_risk_scale": 1.50,
        "base_phase_mult": 3.17,
        "effective_mult": 4.75,
        "calibration_tag": "M2_2_SEED20261124_SYNCED",
        "amber_dd_pct": 9.90,
        "amber_mult": 1.00,
        "red_dd_pct": 9.90,
        "red_mult": 1.00,
        "profit_lock_pct": 5.00,
        "profit_lock_mult": 1.34,
        "daily_reset_mode": 1,
        "kill_daily_dd_pct": 4.30,
        "kill_static_dd_pct": 9.50,
        "ea_daily_stop_pct": 4.30,
        "max_symbol_risk_pct": 2.00,
        "enable_red_news": True,
        "news_pad_sec": 300,
        "news_hard_ban_sec": 135,
        "notes": "FTMO P1 Sprint (eff 4.75x = 1.50x EA * 3.17x Orch; SYMCAP 2.00%, ProfitLock >=+5% -> 2.01x, Prague reset). ARM-LOCKED.",
    },
    "FTMO_P2_Verify": {
        "firm": "FTMO",
        "account_type": "Verification_P2_10k",
        "capital_usd": 10000.0,
        "portfolio": "PORT_7E_P28_CORE",
        "include_s6": False,
        "dry_run_preset": True,
        "arm_locked": True,
        "ea_risk_scale": 1.00,
        "base_phase_mult": 2.50,
        "effective_mult": 2.50,
        "calibration_tag": "M2_2_SEED20261124_SYNCED",
        "amber_dd_pct": 3.50,
        "amber_mult": 0.65,
        "red_dd_pct": 6.00,
        "red_mult": 0.40,
        "profit_lock_pct": 3.00,
        "profit_lock_mult": 1.50,
        "daily_reset_mode": 1,
        "kill_daily_dd_pct": 3.50,
        "kill_static_dd_pct": 7.50,
        "ea_daily_stop_pct": 3.50,
        "max_symbol_risk_pct": 1.50,
        "enable_red_news": True,
        "news_pad_sec": 300,
        "news_hard_ban_sec": 135,
        "notes": "FTMO Phase 2 Verification (eff 2.50x, 5% target, Core 7 EAs, SYMCAP 1.50%, ProfitLock >=+3% -> 1.50x, Prague reset). ARM-LOCKED.",
    },
    "FTMO_Funded_Swing_Safe": {
        "firm": "FTMO",
        "account_type": "Funded_Swing_10k",
        "capital_usd": 10000.0,
        "portfolio": "PORT_7E_P28_CORE",
        "include_s6": False,
        "dry_run_preset": True,
        "arm_locked": True,
        "ea_risk_scale": 1.00,
        "base_phase_mult": 1.00,
        "effective_mult": 1.00,
        "calibration_tag": "M2_2_SEED20261124_SYNCED",
        "amber_dd_pct": 3.50,
        "amber_mult": 0.65,
        "red_dd_pct": 6.00,
        "red_mult": 0.40,
        "profit_lock_pct": 0.00,
        "profit_lock_mult": 1.00,
        "daily_reset_mode": 1,
        "kill_daily_dd_pct": 2.50,
        "kill_static_dd_pct": 7.50,
        "ea_daily_stop_pct": 2.50,
        "max_symbol_risk_pct": 1.00,
        "enable_red_news": False,
        "news_pad_sec": 300,
        "news_hard_ban_sec": 135,
        "notes": "FTMO Funded Swing (1.00x, 1:30 FX, news allowed, Core 7 EAs, SYMCAP_100, Prague reset). ARM-LOCKED.",
    },
    "FTMO_Funded_Std_RedNews": {
        "firm": "FTMO",
        "account_type": "Funded_Standard_10k",
        "capital_usd": 10000.0,
        "portfolio": "PORT_7E_P28_CORE",
        "include_s6": False,
        "dry_run_preset": True,
        "arm_locked": True,
        "ea_risk_scale": 1.00,
        "base_phase_mult": 1.00,
        "effective_mult": 1.00,
        "calibration_tag": "M2_2_SEED20261124_SYNCED",
        "amber_dd_pct": 3.50,
        "amber_mult": 0.65,
        "red_dd_pct": 6.00,
        "red_mult": 0.40,
        "profit_lock_pct": 0.00,
        "profit_lock_mult": 1.00,
        "daily_reset_mode": 1,
        "kill_daily_dd_pct": 2.50,
        "kill_static_dd_pct": 7.50,
        "ea_daily_stop_pct": 2.50,
        "max_symbol_risk_pct": 1.00,
        "enable_red_news": True,
        "news_pad_sec": 300,
        "news_hard_ban_sec": 135,
        "notes": "FTMO Funded Standard (1.00x, 1:100 FX, safe -5m..-2m15s Red-News pre-flatten ON, Core 7 EAs, SYMCAP_100, Prague reset). ARM-LOCKED.",
    },
    "The5ers_HighStakes_P1_Balanced": {
        "firm": "The5ers",
        "account_type": "HighStakes_5k_P1_Balanced",
        "capital_usd": 5000.0,
        "portfolio": "PORT_7E_CORE_PLUS_S6",
        "include_s6": True,
        "dry_run_preset": True,
        "arm_locked": True,
        "ea_risk_scale": 1.50,
        "base_phase_mult": 2.67,
        "effective_mult": 4.00,
        "calibration_tag": "M2_2_SEED20261124_SYNCED",
        "amber_dd_pct": 7.50,
        "amber_mult": 1.00,
        "red_dd_pct": 9.00,
        "red_mult": 0.75,
        "profit_lock_pct": 4.00,
        "profit_lock_mult": 1.34,
        "daily_reset_mode": 0,
        "kill_daily_dd_pct": 4.20,
        "kill_static_dd_pct": 9.20,
        "ea_daily_stop_pct": 4.20,
        "max_symbol_risk_pct": 1.75,
        "enable_red_news": True,
        "news_pad_sec": 300,
        "news_hard_ban_sec": 135,
        "requires_ea_written_clearance": True,
        "notes": "The5ers HS 5k P1 Balanced (eff 4.00x; SYMCAP 1.75%, ProfitLock >=+4% [50% of 8% target] -> 2.01x, Server midnight reset, NAS100/SPX500 mapping; written EA clearance req). ARM-LOCKED.",
    },
    "The5ers_HighStakes_P1_Sprint": {
        "firm": "The5ers",
        "account_type": "HighStakes_5k_P1_Sprint",
        "capital_usd": 5000.0,
        "portfolio": "PORT_7E_CORE_PLUS_S6",
        "include_s6": True,
        "dry_run_preset": True,
        "arm_locked": True,
        "ea_risk_scale": 1.50,
        "base_phase_mult": 3.17,
        "effective_mult": 4.75,
        "calibration_tag": "M2_2_SEED20261124_SYNCED",
        "amber_dd_pct": 9.90,
        "amber_mult": 1.00,
        "red_dd_pct": 9.90,
        "red_mult": 1.00,
        "profit_lock_pct": 4.00,
        "profit_lock_mult": 1.34,
        "daily_reset_mode": 0,
        "kill_daily_dd_pct": 4.30,
        "kill_static_dd_pct": 9.50,
        "ea_daily_stop_pct": 4.30,
        "max_symbol_risk_pct": 2.00,
        "enable_red_news": True,
        "news_pad_sec": 300,
        "news_hard_ban_sec": 135,
        "requires_ea_written_clearance": True,
        "notes": "The5ers HS 5k P1 Sprint (eff 4.75x; SYMCAP 2.00%, ProfitLock >=+4% [50% of 8% target] -> 2.01x, Server midnight reset, NAS100/SPX500 mapping; written EA clearance req). ARM-LOCKED.",
    },
    "The5ers_HighStakes_Funded": {
        "firm": "The5ers",
        "account_type": "HighStakes_5k_Funded",
        "capital_usd": 5000.0,
        "portfolio": "PORT_7E_P28_CORE",
        "include_s6": False,
        "dry_run_preset": True,
        "arm_locked": True,
        "ea_risk_scale": 1.00,
        "base_phase_mult": 1.00,
        "effective_mult": 1.00,
        "calibration_tag": "M2_2_SEED20261124_SYNCED",
        "amber_dd_pct": 3.50,
        "amber_mult": 0.65,
        "red_dd_pct": 6.00,
        "red_mult": 0.40,
        "profit_lock_pct": 0.00,
        "profit_lock_mult": 1.00,
        "daily_reset_mode": 0,
        "kill_daily_dd_pct": 2.50,
        "kill_static_dd_pct": 7.50,
        "ea_daily_stop_pct": 2.50,
        "max_symbol_risk_pct": 1.00,
        "enable_red_news": True,
        "news_pad_sec": 300,
        "news_hard_ban_sec": 135,
        "requires_ea_written_clearance": True,
        "notes": "The5ers HS 5k Funded (1.00x, Core 7 EAs, SYMCAP_100, safe -5m..-2m15s Red-News ON, Server midnight reset, NAS100 mapping). ARM-LOCKED.",
    },
}

# Measured FTMO Demo spread caps in broker points (US100.cash normal spread = 195 pts -> cap 450 pts!)
SPREAD_CAP_BY_ENGINE: dict[str, float] = {
    "E1_USDJPY_TOKYO": 35.0,
    "E2_USDJPY_EXP80": 35.0,
    "E3_GBPUSD_VH": 35.0,
    "E4_US100_SESS40": 450.0,
    "E5_US100_RS1130": 450.0,
    "E6_EURJPY_VOLCOMP": 45.0,
    "E7_USDJPY_NY10ET": 35.0,
    "S6_FX_USD_BSK": 35.0,
}

# Recommended chart symbol to attach each EA on MT5 (default = FTMO)
CHART_ATTACH_BY_ENGINE: dict[str, dict[str, str]] = {
    "E1_USDJPY_TOKYO": {"symbol": "USDJPY", "timeframe": "M15"},
    "E2_USDJPY_EXP80": {"symbol": "USDJPY", "timeframe": "M15"},
    "E3_GBPUSD_VH": {"symbol": "GBPUSD", "timeframe": "M15"},
    "E4_US100_SESS40": {"symbol": "US100.cash", "timeframe": "M5"},
    "E5_US100_RS1130": {"symbol": "US100.cash", "timeframe": "M5"},
    "E6_EURJPY_VOLCOMP": {"symbol": "EURJPY", "timeframe": "M15"},
    "E7_USDJPY_NY10ET": {"symbol": "USDJPY", "timeframe": "M5"},
    "S6_FX_USD_BSK": {"symbol": "EURUSD", "timeframe": "M15"},
}

# Per-firm chart attachment mapping (FTMO uses US100.cash; The5ers uses NAS100)
CHART_ATTACH_BY_FIRM: dict[str, dict[str, dict[str, str]]] = {
    "FTMO": CHART_ATTACH_BY_ENGINE,
    "The5ers": {
        "E1_USDJPY_TOKYO": {"symbol": "USDJPY", "timeframe": "M15"},
        "E2_USDJPY_EXP80": {"symbol": "USDJPY", "timeframe": "M15"},
        "E3_GBPUSD_VH": {"symbol": "GBPUSD", "timeframe": "M15"},
        "E4_US100_SESS40": {"symbol": "NAS100", "timeframe": "M5"},
        "E5_US100_RS1130": {"symbol": "NAS100", "timeframe": "M5"},
        "E6_EURJPY_VOLCOMP": {"symbol": "EURJPY", "timeframe": "M15"},
        "E7_USDJPY_NY10ET": {"symbol": "USDJPY", "timeframe": "M5"},
        "S6_FX_USD_BSK": {"symbol": "EURUSD", "timeframe": "M15"},
    },
}

THE5ERS_BENCHMARK_VERIFICATION_NOTE = (
    "The5ers chart mapping uses NAS100 for E4/E5 and E7 InpEquitySymbol; verify exact S&P500 benchmark "
    "symbol (SPX500 vs US500) in E5 InpBenchmarkSymbol against The5ers Market Watch (G1 snapshot) before disarming."
)


def get_chart_attach_for_firm(firm: str) -> dict[str, dict[str, str]]:
    return CHART_ATTACH_BY_FIRM.get(firm, CHART_ATTACH_BY_ENGINE)


# Calibrated strict 4% daily / 8% static DD envelope for The5ers High Stakes 50K/60K/100K
# (empirically verified in Cycle-1 PROP-TIER-SCALING-AND-SYMCAP-AUDIT-20261124: slashes 1st-try
# Daily Breach from 34.7% -> 6.1%, EV/Fee 8.25x on 50K / 10.02x on 60K).
THE5ERS_4_8_CALIBRATED_P1: dict[str, Any] = {
    "ea_risk_scale": 1.00,
    "base_phase_mult": 2.75,
    "effective_mult": 2.75,
    "amber_dd_pct": 5.00,
    "amber_mult": 0.80,
    "red_dd_pct": 6.00,
    "red_mult": 0.50,
    "profit_lock_pct": 4.00,
    "profit_lock_mult": 1.50,
    "max_symbol_risk_pct": 1.15,
    "kill_daily_dd_pct": 2.80,
    "kill_static_dd_pct": 6.50,
    "ea_daily_stop_pct": 2.80,
    "calibration_tag": "CYCLE1_SYMCAP_4_8_CALIBRATED",
}


def build_scaled_tier_config(
    firm: str,
    capital_usd: float,
    phase: str = "P1_Balanced",
    dd_mode: str = "5_10",
    *,
    allow_unsafe_5_10_override: bool = False,
    enable_red_news: bool | None = None,
) -> dict[str, Any]:
    """Build a deterministic, ARM-LOCKED scaled tier config (FTMO 10K-100K, The5ers 5K-100K).

    Fail-closed guards:
      - Refuses `dd_mode="5_10"` on The5ers High Stakes >= 50,000 USD unless
        `allow_unsafe_5_10_override=True` (protects against deploying a 4.2% daily kill
        preset onto a strict 4.0% daily-limit account).
      - Refuses `enable_red_news=False` on The5ers (High Stakes enforces +/-2m news ban).
      - Always returns ARM-LOCKED (`dry_run_preset=True`, `arm_locked=True`, `order_send_count=0`).
    """
    cap = float(capital_usd)
    if cap <= 0.0:
        raise ValueError(f"capital_usd must be positive, got {capital_usd!r}")

    firm_raw = firm.strip()
    firm_low = firm_raw.lower().replace("-", "_").replace(" ", "_")
    if firm_low in ("ftmo", "ftmo_swing", "ftmo_std", "ftmo_standard"):
        firm_norm = "FTMO"
        is_ftmo_swing = firm_low == "ftmo_swing"
    elif firm_low in ("the5ers", "the5ers_highstakes", "the5ers_high_stakes", "5ers"):
        firm_norm = "The5ers"
        is_ftmo_swing = False
    else:
        raise ValueError(f"Unsupported firm {firm!r}; expected FTMO, FTMO_Swing, or The5ers.")

    dd_norm = dd_mode.strip().replace("/", "_")
    if dd_norm not in ("5_10", "4_8"):
        raise ValueError(f"Unsupported dd_mode {dd_mode!r}; expected '5_10' or '4_8'.")

    if firm_norm == "The5ers" and cap >= 50000.0 and dd_norm == "5_10" and not allow_unsafe_5_10_override:
        raise ValueError(
            f"SAFETY ABORT: The5ers High Stakes >= 50,000 USD ({cap:.0f} USD) enforces strict 4% daily / 8% static DD. "
            "Refusing dd_mode='5_10' (4.2% Kill Daily exceeds 4.0% prop limit!). "
            "Use dd_mode='4_8' (calibrated 2.75x->1.50x, SYMCAP 1.15%, Kill Daily 2.80%) "
            "or explicitly pass allow_unsafe_5_10_override=True."
        )

    phase_raw = phase.strip()
    phase_key = phase_raw.lower().replace("-", "_")
    if phase_key in ("p1_balanced", "p1_balanced_3to6m", "p1"):
        phase_norm = "P1_Balanced"
        base_profile = "FTMO_P1_Balanced_3to6m" if firm_norm == "FTMO" else "The5ers_HighStakes_P1_Balanced"
    elif phase_key in ("p1_sprint", "p1_sprint_1to3m"):
        phase_norm = "P1_Sprint"
        base_profile = "FTMO_P1_Sprint_1to3m" if firm_norm == "FTMO" else "The5ers_HighStakes_P1_Sprint"
    elif phase_key in ("p2_verify", "p2"):
        phase_norm = "P2_Verify"
        base_profile = "FTMO_P2_Verify"
    elif phase_key in ("funded", "funded_safe", "funded_swing", "funded_swing_safe"):
        phase_norm = "Funded_Swing_Safe" if firm_norm == "FTMO" else "Funded"
        base_profile = "FTMO_Funded_Swing_Safe" if firm_norm == "FTMO" else "The5ers_HighStakes_Funded"
    elif phase_key in ("funded_std", "funded_std_rednews"):
        phase_norm = "Funded_Std_RedNews" if firm_norm == "FTMO" else "Funded"
        base_profile = "FTMO_Funded_Std_RedNews" if firm_norm == "FTMO" else "The5ers_HighStakes_Funded"
    else:
        raise ValueError(
            f"Unsupported phase {phase!r}; expected P1_Balanced, P1_Sprint, P2_Verify, Funded, Funded_Swing_Safe, or Funded_Std_RedNews."
        )

    cfg: dict[str, Any] = dict(OPERATIONAL_PROFILES[base_profile])
    cfg["firm"] = firm_norm
    cfg["capital_usd"] = cap
    cfg["daily_reset_mode"] = 1 if firm_norm == "FTMO" else 0
    cfg["dry_run_preset"] = True
    cfg["arm_locked"] = True
    cfg["dd_mode"] = dd_norm
    cfg["daily_dd_limit_pct"] = 4.0 if dd_norm == "4_8" else 5.0
    cfg["static_dd_limit_pct"] = 8.0 if dd_norm == "4_8" else 10.0
    cfg["phase"] = phase_norm
    cfg["base_profile_template"] = base_profile

    if firm_norm == "The5ers":
        cfg["enable_red_news"] = True
        cfg["requires_ea_written_clearance"] = True

    if dd_norm == "4_8":
        if phase_norm in ("P1_Balanced", "P1_Sprint"):
            cfg.update(THE5ERS_4_8_CALIBRATED_P1)
            if phase_norm == "P1_Sprint":
                cfg["notes"] = (
                    f"{firm_norm} {cap/1000:.0f}K P1_Sprint capped to calibrated 4%/8% safe envelope "
                    "(2.75x->1.50x ProfitLock >=+5%, SYMCAP 1.15%, Kill Daily 2.80%). ARM-LOCKED."
                )
            else:
                cfg["notes"] = (
                    f"{firm_norm} {cap/1000:.0f}K P1_Balanced strict 4%/8% calibrated envelope "
                    "(2.75x->1.50x ProfitLock >=+5%, SYMCAP 1.15%, Kill Daily 2.80%, Kill Static 6.50%). ARM-LOCKED."
                )
        elif phase_norm == "P2_Verify":
            cfg.update(
                {
                    "ea_risk_scale": 1.00,
                    "base_phase_mult": 2.00,
                    "effective_mult": 2.00,
                    "amber_dd_pct": 3.50,
                    "amber_mult": 0.65,
                    "red_dd_pct": 5.50,
                    "red_mult": 0.40,
                    "profit_lock_pct": 3.00,
                    "profit_lock_mult": 1.25,
                    "max_symbol_risk_pct": 1.15,
                    "kill_daily_dd_pct": 2.80,
                    "kill_static_dd_pct": 6.50,
                    "ea_daily_stop_pct": 2.80,
                    "calibration_tag": "CYCLE1_SYMCAP_4_8_CALIBRATED",
                }
            )
        else:
            cfg.update(
                {
                    "ea_risk_scale": 1.00,
                    "base_phase_mult": 1.00,
                    "effective_mult": 1.00,
                    "profit_lock_pct": 0.00,
                    "profit_lock_mult": 1.00,
                    "max_symbol_risk_pct": 1.00,
                    "kill_daily_dd_pct": 2.50,
                    "kill_static_dd_pct": 6.50,
                    "ea_daily_stop_pct": 2.50,
                    "calibration_tag": "CYCLE1_SYMCAP_4_8_CALIBRATED",
                }
            )

    if enable_red_news is not None:
        if firm_norm == "The5ers" and not enable_red_news:
            raise ValueError("SAFETY ABORT: The5ers High Stakes enforces +/-2m news ban; enable_red_news cannot be False.")
        cfg["enable_red_news"] = bool(enable_red_news)
    elif is_ftmo_swing and phase_norm == "Funded_Swing_Safe":
        cfg["enable_red_news"] = False

    # Fail-closed safety invariants
    assert cfg["kill_daily_dd_pct"] < cfg["daily_dd_limit_pct"], "kill_daily_dd_pct must stay strictly below prop daily limit"
    assert cfg["kill_static_dd_pct"] < cfg["static_dd_limit_pct"], "kill_static_dd_pct must stay strictly below prop static limit"
    assert 0.20 <= float(cfg["base_phase_mult"]) <= 3.50, "base_phase_mult outside PropGuard clamp [0.20, 3.50]"
    assert cfg["dry_run_preset"] is True and cfg["arm_locked"] is True, "Scaled tier config must remain ARM-LOCKED"

    tier_label = f"{firm_norm}_{'Swing_' if is_ftmo_swing else ''}{int(cap // 1000)}K_{phase_norm}_{dd_norm}"
    cfg["tier_id"] = tier_label
    cfg["account_type"] = tier_label
    cfg["order_send_count"] = 0
    cfg["chart_attachments"] = get_chart_attach_for_firm(firm_norm)
    if firm_norm == "The5ers":
        cfg["broker_symbol_verification_note"] = THE5ERS_BENCHMARK_VERIFICATION_NOTE
    cfg["orchestrator_inputs"] = {
        "InpDryRunLogOnly": True,
        "InpGuardDryRunLogOnly": True,
        "InpInitialBalanceUSD": cap,
        "InpBasePhaseMult": float(cfg["base_phase_mult"]),
        "InpAmberDdPct": float(cfg["amber_dd_pct"]),
        "InpAmberMult": float(cfg["amber_mult"]),
        "InpRedDdPct": float(cfg["red_dd_pct"]),
        "InpRedMult": float(cfg["red_mult"]),
        "InpProfitLockPct": float(cfg["profit_lock_pct"]),
        "InpProfitLockMult": float(cfg["profit_lock_mult"]),
        "InpKillDailyDdPct": float(cfg["kill_daily_dd_pct"]),
        "InpKillStaticDdPct": float(cfg["kill_static_dd_pct"]),
        "InpDailyResetMode": int(cfg["daily_reset_mode"]),
        "InpAllowManualHaltFile": False,
        "InpGuardMaxDailyLossPct": float(cfg["ea_daily_stop_pct"]),
        "InpGuardMaxSymbolRiskPct": float(cfg["max_symbol_risk_pct"]),
        "InpGuardEnableRedNews": bool(cfg["enable_red_news"]),
        "InpGuardNewsPadSec": int(cfg["news_pad_sec"]),
        "InpGuardNewsHardBanSec": int(cfg["news_hard_ban_sec"]),
    }
    return cfg


def parse_preview_tier_spec(spec: str) -> dict[str, Any]:
    """Parse CLI `<firm>:<capital>:<phase>:<dd_mode>` spec into `build_scaled_tier_config()`."""
    parts = [p.strip() for p in spec.split(":")]
    if len(parts) < 2 or len(parts) > 4:
        raise ValueError(f"Expected <firm>:<capital>[:<phase>[:<dd_mode>]], got {spec!r}")
    firm = parts[0]
    cap_raw = parts[1].upper().replace(",", "")
    if cap_raw.endswith("K"):
        capital = float(cap_raw[:-1]) * 1000.0
    else:
        capital = float(cap_raw)
    phase = parts[2] if len(parts) >= 3 and parts[2] else "P1_Balanced"
    dd_mode = parts[3] if len(parts) >= 4 and parts[3] else "5_10"
    return build_scaled_tier_config(firm=firm, capital_usd=capital, phase=phase, dd_mode=dd_mode)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _format_set_val(val: Any) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)


def _render_set_file(header_lines: list[str], kv: dict[str, Any]) -> str:
    lines = [f"; {h}" for h in header_lines]
    for k, v in kv.items():
        lines.append(f"{k}={_format_set_val(v)}")
    return "\n".join(lines) + "\n"


def parse_set_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        # MT5 .set files may optionally use `value||start||step||stop||N`; keep primary value
        v_primary = v.split("||", 1)[0].strip()
        out[k.strip()] = v_primary
    return out


def build_presets_and_manifest(
    *,
    exports_dir: Path = EXPORTS_DIR,
    kit_dir: Path = KIT_DIR,
    ex5_dir: Path = DEFAULT_EX5_DIR,
    overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate all 10 profile `.set` preset directories and `manifest.sha256.json`."""
    presets_dir = kit_dir / "presets"
    presets_dir.mkdir(parents=True, exist_ok=True)

    mqh_parsed = parity.parse_mq5_source(exports_dir / "Include/Naqex_PropGuard.mqh")
    orch_parsed = parity.parse_mq5_source(exports_dir / "Naqex_AccountOrchestrator.mq5")
    ea_parsed_map = {
        eid: parity.parse_mq5_source(exports_dir / contract["file"])
        for eid, contract in parity.ENGINE_PARITY_CONTRACTS.items()
    }

    profiles_summary: dict[str, Any] = {}
    generated_set_files: list[Path] = []

    for pname, base_cfg in OPERATIONAL_PROFILES.items():
        cfg = {**base_cfg, **(overrides.get(pname, {}) if overrides else {})}
        pdir = presets_dir / pname
        pdir.mkdir(parents=True, exist_ok=True)

        dry = bool(cfg["dry_run_preset"])
        arm_note = (
            "ARM-LOCKED SAFETY: set InpDryRunLogOnly=false & InpGuardDryRunLogOnly=false ONLY after Free Trial PASS & TCA GREEN"
            if cfg["arm_locked"]
            else "FREE TRIAL DEMO ONLY: Demo paper execution enabled (never attach to paid account without re-audit)"
        )

        # 1. Naqex_AccountOrchestrator.set
        orch_kv: dict[str, Any] = {
            "InpDryRunLogOnly": dry,
            "InpInitialBalanceUSD": float(cfg["capital_usd"]),
            "InpBasePhaseMult": float(cfg["base_phase_mult"]),
            "InpAmberDdPct": float(cfg["amber_dd_pct"]),
            "InpAmberMult": float(cfg["amber_mult"]),
            "InpRedDdPct": float(cfg["red_dd_pct"]),
            "InpRedMult": float(cfg["red_mult"]),
            "InpProfitLockPct": float(cfg["profit_lock_pct"]),
            "InpProfitLockMult": float(cfg["profit_lock_mult"]),
            "InpKillDailyDdPct": float(cfg["kill_daily_dd_pct"]),
            "InpKillStaticDdPct": float(cfg["kill_static_dd_pct"]),
            "InpDailyResetMode": int(cfg["daily_reset_mode"]),
            "InpHeartbeatSec": 15,
            "InpHeartbeatFile": "naqex_heartbeat.json",
            "InpAllowManualHaltFile": False,
            "InpManualHaltFile": "naqex_manual_halt.flag",
            "InpMagicRangeMin": 20261120,
            "InpMagicRangeMax": 20261199,
            # PropGuard inputs inherited by Orchestrator
            "InpGuardDryRunLogOnly": dry,
            "InpGuardMaxDailyLossPct": float(cfg["ea_daily_stop_pct"]),
            "InpGuardMaxSymbolRiskPct": float(cfg["max_symbol_risk_pct"]),
            "InpGuardUseOrchestrator": True,
            "InpGuardMaxSpreadPoints": 35.0,
            "InpGuardRolloverStartUTC": 21,
            "InpGuardRolloverEndUTC": 0,
            "InpGuardEarlyCloseMin": 10,
            "InpGuardTesterUtcOffsetH": 2,
            "InpGuardEnableRedNews": bool(cfg["enable_red_news"]),
            "InpGuardRedNewsCsvFile": "naqex_red_news_utc.csv",
            "InpGuardNewsPadSec": int(cfg["news_pad_sec"]),
            "InpGuardNewsHardBanSec": int(cfg["news_hard_ban_sec"]),
            "InpGuardTcaAuditCsvFile": "naqex_exec_audit.csv",
            "InpGuardMagicRangeMin": 20261120,
            "InpGuardMagicRangeMax": 20261199,
        }
        # Assert every key exists in Orchestrator or PropGuard
        valid_orch_keys = set(orch_parsed["inputs"]) | set(mqh_parsed["inputs"])
        assert set(orch_kv).issubset(valid_orch_keys), f"Unknown orch keys: {set(orch_kv) - valid_orch_keys}"

        reset_desc = {0: "MT5_Server_Midnight", 1: "Europe_Prague_CET_CEST", 2: "UTC_Legacy"}.get(
            int(cfg["daily_reset_mode"]), str(cfg["daily_reset_mode"])
        )
        orch_set_path = pdir / "Naqex_AccountOrchestrator.set"
        orch_set_path.write_text(
            _render_set_file(
                [
                    f"Naqex MT5 Preset | Profile: {pname} | Target: Naqex_AccountOrchestrator.ex5",
                    f"Firm: {cfg['firm']} | AccountType: {cfg['account_type']} | CapitalUSD: {cfg['capital_usd']:.0f} | Reset: {reset_desc}",
                    arm_note,
                ],
                orch_kv,
            ),
            encoding="utf-8",
            newline="\n",
        )
        generated_set_files.append(orch_set_path)

        # 2. All 8 EA .set files
        firm_attach_map = get_chart_attach_for_firm(str(cfg["firm"]))
        active_eas: list[str] = []
        standby_eas: list[str] = []
        for eid, contract in parity.ENGINE_PARITY_CONTRACTS.items():
            ep = ea_parsed_map[eid]
            stem = Path(contract["file"]).stem
            is_s6_disabled = (eid == "S6_FX_USD_BSK") and (not bool(cfg["include_s6"]))
            ea_dry = True if is_s6_disabled else dry

            ea_kv: dict[str, Any] = {}
            for k, meta in ep["inputs"].items():
                ea_kv[k] = meta["value"]

            ea_kv["InpDryRunLogOnly"] = ea_dry
            ea_kv["InpMaxDailyLossPct"] = float(cfg["ea_daily_stop_pct"])
            if cfg["firm"] == "The5ers" and eid == "E5_US100_RS1130":
                ea_kv["InpBenchmarkSymbol"] = "SPX500"
            if cfg["firm"] == "The5ers" and eid == "E7_USDJPY_NY10ET":
                ea_kv["InpEquitySymbol"] = "NAS100"
            ea_scale = float(cfg.get("ea_risk_scale", 1.00))
            if is_s6_disabled:
                ea_kv["InpRiskPercent"] = 0.00
                standby_eas.append(eid)
            else:
                ea_kv["InpRiskPercent"] = round(float(ea_kv["InpRiskPercent"]) * ea_scale, 2)
                active_eas.append(eid)

            # Append PropGuard inputs for complete self-contained .set preset
            guard_kv: dict[str, Any] = {
                "InpGuardDryRunLogOnly": ea_dry,
                "InpGuardMaxDailyLossPct": float(cfg["ea_daily_stop_pct"]),
                "InpGuardMaxSymbolRiskPct": float(cfg["max_symbol_risk_pct"]),
                "InpGuardUseOrchestrator": True,
                "InpGuardMaxSpreadPoints": float(SPREAD_CAP_BY_ENGINE[eid]),
                "InpGuardRolloverStartUTC": 21,
                "InpGuardRolloverEndUTC": 0,
                "InpGuardEarlyCloseMin": 10,
                "InpGuardTesterUtcOffsetH": 2,
                "InpGuardEnableRedNews": bool(cfg["enable_red_news"]),
                "InpGuardRedNewsCsvFile": "naqex_red_news_utc.csv",
                "InpGuardNewsPadSec": int(cfg["news_pad_sec"]),
                "InpGuardNewsHardBanSec": int(cfg["news_hard_ban_sec"]),
                "InpGuardTcaAuditCsvFile": "naqex_exec_audit.csv",
                "InpGuardMagicRangeMin": 20261120,
                "InpGuardMagicRangeMax": 20261199,
            }
            full_kv = {**ea_kv, **guard_kv}
            valid_ea_keys = set(ep["inputs"]) | set(mqh_parsed["inputs"])
            assert set(full_kv).issubset(valid_ea_keys), f"Unknown EA keys for {eid}: {set(full_kv) - valid_ea_keys}"

            attach = firm_attach_map[eid]
            status_tag = "STANDBY_DISABLED_IN_CORE_ONLY_PROFILE" if is_s6_disabled else "ACTIVE"
            header_lines = [
                f"Naqex MT5 Preset | Profile: {pname} | Engine: {eid} ({status_tag})",
                f"Attach: {attach['symbol']} {attach['timeframe']} | Magic: {ea_kv['InpMagicNumber']} | MaxSpreadPts: {guard_kv['InpGuardMaxSpreadPoints']:.1f}",
            ]
            if cfg["firm"] == "The5ers" and eid == "E5_US100_RS1130":
                header_lines.append(
                    "Broker Symbol Check (The5ers G1): Attach to NAS100 M5 and verify exact S&P500 symbol (SPX500 vs US500) in InpBenchmarkSymbol against Market Watch before disarming"
                )
            elif cfg["firm"] == "The5ers" and eid == "E7_USDJPY_NY10ET":
                header_lines.append(
                    "Broker Symbol Check (The5ers G1): InpEquitySymbol set to NAS100; confirm exact NASDAQ symbol in The5ers Market Watch before disarming"
                )
            header_lines.append(arm_note)
            set_path = pdir / f"{stem}.set"
            set_path.write_text(
                _render_set_file(header_lines, full_kv),
                encoding="utf-8",
                newline="\n",
            )
            generated_set_files.append(set_path)

        meta_obj: dict[str, Any] = {
            "profile": pname,
            **cfg,
            "active_engines": active_eas,
            "standby_engines": standby_eas,
            "chart_attachments": firm_attach_map,
            "spread_caps_points": SPREAD_CAP_BY_ENGINE,
        }
        if cfg["firm"] == "The5ers":
            meta_obj["broker_symbol_verification_note"] = THE5ERS_BENCHMARK_VERIFICATION_NOTE
        meta_path = pdir / "profile_meta.json"
        meta_path.write_text(json.dumps(meta_obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        profiles_summary[pname] = {
            "firm": cfg["firm"],
            "capital_usd": cfg["capital_usd"],
            "ea_risk_scale": float(cfg.get("ea_risk_scale", 1.00)),
            "base_phase_mult": float(cfg["base_phase_mult"]),
            "effective_mult": float(cfg.get("effective_mult", cfg["base_phase_mult"])),
            "profit_lock_pct": float(cfg["profit_lock_pct"]),
            "profit_lock_mult": float(cfg["profit_lock_mult"]),
            "daily_reset_mode": int(cfg["daily_reset_mode"]),
            "dry_run_preset": dry,
            "arm_locked": cfg["arm_locked"],
            "enable_red_news": cfg["enable_red_news"],
            "news_hard_ban_sec": int(cfg["news_hard_ban_sec"]),
            "max_symbol_risk_pct": cfg["max_symbol_risk_pct"],
            "active_engine_count": len(active_eas),
            "calibration_tag": cfg.get("calibration_tag", "FROZEN_BASE"),
        }

    # 2b. Generate streamlined Round-3 single-spec Master_Prop7E presets (FTMO Swing 10K 3-phase + The5ers 5K shadow)
    master_v2_dir = kit_dir / "master_v2"
    master_v2_dir.mkdir(parents=True, exist_ok=True)
    master_presets_spec = {
        "FTMO_Swing_10K_Shadow_Demo_Master7E.set": {
            "InpDryRunLogOnly": "true",
            "InpShadowCompareMode": "true",
            "InpEnableS6Shadow": "true",
            "InpWritePrimaryHeartbeat": "false",
            "InpContractSku": "FTMO_SWING_10K_SHADOW_DEMO",
            "InpInitialBalanceUSD": "10000.00",
            "InpTargetProfitPct": "10.00",
            "InpHardDailyDdPct": "5.00",
            "InpHardStaticDdPct": "10.00",
            "InpDailyResetMode": "1",
            "InpSizingMode": "0",
            "InpBasePhaseMult": "1.00",
            "InpProfitLockPct": "0.00",
            "InpProfitLockMult": "1.00",
            "InpMaxSymbolRiskPct": "1.00",
            "InpMaxUsdClusterPct": "1.50",
            "InpMaxJpyClusterPct": "1.25",
            "InpMaxIdxClusterPct": "1.00",
            "InpMaxAccountOpenRiskPct": "2.00",
            "InpSymUS100": "US100.cash",
            "InpSymUS500": "US500.cash",
            "InpGuardDryRunLogOnly": "true",
            "InpGuardEnableRedNews": "true",
            "InpGuardNewsPadSec": "300",
            "InpGuardNewsHardBanSec": "135",
            "InpAllowManualHaltFile": "false",
        },
        "FTMO_Swing_10K_P1_Master7E.set": {
            "InpDryRunLogOnly": "true",
            "InpShadowCompareMode": "true",
            "InpEnableS6Shadow": "true",
            "InpWritePrimaryHeartbeat": "true",
            "InpContractSku": "FTMO_SWING_10K_P1",
            "InpInitialBalanceUSD": "10000.00",
            "InpTargetProfitPct": "10.00",
            "InpHardDailyDdPct": "5.00",
            "InpHardStaticDdPct": "10.00",
            "InpDailyResetMode": "1",
            "InpSizingMode": "1",
            "InpBasePhaseMult": "4.00",
            "InpProfitLockPct": "5.00",
            "InpProfitLockMult": "2.01",
            "InpMaxSymbolRiskPct": "1.75",
            "InpMaxUsdClusterPct": "2.25",
            "InpMaxJpyClusterPct": "2.00",
            "InpMaxIdxClusterPct": "1.75",
            "InpMaxAccountOpenRiskPct": "3.00",
            "InpSymUS100": "US100.cash",
            "InpSymUS500": "US500.cash",
            "InpGuardDryRunLogOnly": "true",
            "InpGuardEnableRedNews": "true",
            "InpGuardNewsPadSec": "300",
            "InpGuardNewsHardBanSec": "135",
            "InpAllowManualHaltFile": "false",
        },
        "FTMO_Swing_10K_P2_Master7E.set": {
            "InpDryRunLogOnly": "true",
            "InpShadowCompareMode": "true",
            "InpEnableS6Shadow": "true",
            "InpWritePrimaryHeartbeat": "true",
            "InpContractSku": "FTMO_SWING_10K_P2",
            "InpInitialBalanceUSD": "10000.00",
            "InpTargetProfitPct": "5.00",
            "InpHardDailyDdPct": "5.00",
            "InpHardStaticDdPct": "10.00",
            "InpDailyResetMode": "1",
            "InpSizingMode": "1",
            "InpBasePhaseMult": "2.00",
            "InpProfitLockPct": "3.00",
            "InpProfitLockMult": "1.00",
            "InpMaxSymbolRiskPct": "1.50",
            "InpMaxUsdClusterPct": "2.00",
            "InpMaxJpyClusterPct": "1.75",
            "InpMaxIdxClusterPct": "1.50",
            "InpMaxAccountOpenRiskPct": "2.50",
            "InpSymUS100": "US100.cash",
            "InpSymUS500": "US500.cash",
            "InpGuardDryRunLogOnly": "true",
            "InpGuardEnableRedNews": "true",
            "InpGuardNewsPadSec": "300",
            "InpGuardNewsHardBanSec": "135",
            "InpAllowManualHaltFile": "false",
        },
        "FTMO_Swing_10K_Funded_Master7E.set": {
            "InpDryRunLogOnly": "true",
            "InpShadowCompareMode": "true",
            "InpEnableS6Shadow": "true",
            "InpWritePrimaryHeartbeat": "true",
            "InpContractSku": "FTMO_SWING_10K_FUNDED",
            "InpInitialBalanceUSD": "10000.00",
            "InpTargetProfitPct": "0.00",
            "InpHardDailyDdPct": "5.00",
            "InpHardStaticDdPct": "10.00",
            "InpDailyResetMode": "1",
            "InpSizingMode": "1",
            "InpBasePhaseMult": "1.00",
            "InpProfitLockPct": "0.00",
            "InpProfitLockMult": "1.00",
            "InpMaxSymbolRiskPct": "1.00",
            "InpMaxUsdClusterPct": "1.50",
            "InpMaxJpyClusterPct": "1.25",
            "InpMaxIdxClusterPct": "1.00",
            "InpMaxAccountOpenRiskPct": "2.00",
            "InpSymUS100": "US100.cash",
            "InpSymUS500": "US500.cash",
            "InpGuardDryRunLogOnly": "true",
            "InpGuardEnableRedNews": "true",
            "InpGuardNewsPadSec": "300",
            "InpGuardNewsHardBanSec": "135",
            "InpAllowManualHaltFile": "false",
        },
        "The5ers_HS_5K_Shadow_Master7E.set": {
            "InpDryRunLogOnly": "true",
            "InpShadowCompareMode": "true",
            "InpEnableS6Shadow": "true",
            "InpWritePrimaryHeartbeat": "false",
            "InpContractSku": "THE5ERS_HS_5K_P1_SHADOW",
            "InpInitialBalanceUSD": "5000.00",
            "InpTargetProfitPct": "8.00",
            "InpHardDailyDdPct": "5.00",
            "InpHardStaticDdPct": "10.00",
            "InpDailyResetMode": "0",
            "InpSizingMode": "1",
            "InpBasePhaseMult": "4.00",
            "InpProfitLockPct": "4.00",
            "InpProfitLockMult": "2.01",
            "InpMaxSymbolRiskPct": "1.75",
            "InpMaxUsdClusterPct": "2.25",
            "InpMaxJpyClusterPct": "2.00",
            "InpMaxIdxClusterPct": "1.75",
            "InpMaxAccountOpenRiskPct": "3.00",
            "InpSymUS100": "NAS100",
            "InpSymUS500": "SPX500",
            "InpGuardDryRunLogOnly": "true",
            "InpGuardEnableRedNews": "true",
            "InpGuardNewsPadSec": "300",
            "InpGuardNewsHardBanSec": "135",
            "InpAllowManualHaltFile": "false",
        },
    }
    for fname, kv in master_presets_spec.items():
        lines = [f"; Naqex Round-3 Single-Authority Master_Prop7E Preset ({fname}) — FAIL-CLOSED DRYRUN=TRUE"]
        for k, v in kv.items():
            lines.append(f"{k}={v}")
        (master_v2_dir / fname).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    # 3. Build cryptographic SHA-256 manifest
    tracked_files: list[Path] = []
    tracked_files.extend(sorted(exports_dir.glob("*.mq5")))
    tracked_files.append(exports_dir / "Include/Naqex_PropGuard.mqh")
    tracked_files.append(exports_dir / "Include/Naqex_Signals_7E.mqh")
    tracked_files.append(exports_dir / "mql5_parity_checker.py")
    tracked_files.append(exports_dir / "verify_deployment_kit.py")
    for rel_kit in (
        "ACTIVATION-CARD-LOCAL-MT5.md",
        "ops_watchdog/naqex_mt5_watchdog.ps1",
        "vps_kit/sync_updated_ex5_when_flat.ps1",
    ):
        p = kit_dir / rel_kit
        if p.exists():
            tracked_files.append(p)
    tracked_files.extend(sorted(presets_dir.rglob("*.set")))
    tracked_files.extend(sorted(presets_dir.rglob("profile_meta.json")))
    tracked_files.extend(sorted(master_v2_dir.rglob("*.set")))

    tracked_entries: dict[str, dict[str, Any]] = {}
    for f in tracked_files:
        rel = f.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
        tracked_entries[rel] = {
            "sha256": sha256_file(f),
            "bytes": f.stat().st_size,
        }

    # Compiled .ex5 binaries (stored under gitignored .runtime/mt5-compiled-ex5/)
    ex5_entries: dict[str, dict[str, Any]] = {}
    if ex5_dir.exists():
        for ex5 in sorted(ex5_dir.glob("*.ex5")):
            rel = ex5.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
            ex5_entries[rel] = {
                "sha256": sha256_file(ex5),
                "bytes": ex5.stat().st_size,
            }

    # External Lane-B dependency (validated structurally, SHA recorded informatively)
    news_csv = exports_dir / "Files/naqex_red_news_utc.csv"
    news_info = parity.verify_red_news_csv(news_csv)

    manifest = {
        "schema": "naqex-mt5-deployment-kit-manifest-v1",
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "order_send_count": 0,
        "profile_count": len(OPERATIONAL_PROFILES),
        "profiles": profiles_summary,
        "tracked_files_count": len(tracked_entries),
        "tracked_files": tracked_entries,
        "compiled_ex5_count": len(ex5_entries),
        "compiled_ex5_dir": ".runtime/mt5-compiled-ex5",
        "compiled_ex5_files": ex5_entries,
        "external_dependencies": {
            "tooling/ai-engines/exports/Files/naqex_red_news_utc.csv": {
                "owner": "lane-b-risk-auditor",
                "rows_at_build": news_info.get("rows", 0),
                "snapshot_sha256": news_info.get("sha256"),
            }
        },
    }
    manifest_path = kit_dir / "manifest.sha256.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return manifest


def verify_kit(
    *,
    exports_dir: Path = EXPORTS_DIR,
    kit_dir: Path = KIT_DIR,
    ex5_dir: Path = DEFAULT_EX5_DIR,
    require_ex5: bool = False,
) -> dict[str, Any]:
    """Self-verify the complete MT5 deployment kit: parity, manifests, .set presets, safety & anti-bloat."""
    errors: list[str] = []

    # 1. Parity & safety check on all .mq5 + .mqh + red-news CSV + optional .ex5 logs
    parity_rep = parity.run_parity_audit(exports_dir=exports_dir, ex5_dir=ex5_dir, require_ex5=require_ex5)
    if not parity_rep["ok"]:
        errors.append("MQL5 <-> Python parity audit failed")
        errors.extend(parity_rep.get("global_errors", []))

    # 2. Manifest existence & SHA-256 verification
    manifest_path = kit_dir / "manifest.sha256.json"
    manifest: dict[str, Any] | None = None
    verified_tracked = 0
    verified_ex5 = 0
    if not manifest_path.exists():
        errors.append(f"Missing manifest: {manifest_path}")
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for rel, info in manifest.get("tracked_files", {}).items():
            fp = REPO_ROOT / rel
            if not fp.exists():
                errors.append(f"Manifest tracked file missing: {rel}")
                continue
            sz = fp.stat().st_size
            if sz > ANTI_BLOAT_LIMIT_BYTES:
                errors.append(f"Anti-bloat violation ({sz} > {ANTI_BLOAT_LIMIT_BYTES}): {rel}")
            actual_sha = sha256_file(fp)
            if actual_sha != info["sha256"]:
                errors.append(f"SHA-256 mismatch on {rel}: got {actual_sha[:12]} != manifest {info['sha256'][:12]}")
            else:
                verified_tracked += 1

        ex5_map = manifest.get("compiled_ex5_files", {})
        if require_ex5 and len(ex5_map) != 10:
            errors.append(f"Manifest expected 10 compiled .ex5 files (9 baseline + Master_Prop7E), found {len(ex5_map)}")
        for rel, info in ex5_map.items():
            fp = REPO_ROOT / rel
            if not fp.exists():
                if require_ex5:
                    errors.append(f"Manifest compiled .ex5 missing: {rel}")
                continue
            actual_sha = sha256_file(fp)
            if actual_sha != info["sha256"]:
                errors.append(f"Compiled .ex5 SHA-256 mismatch on {rel}")
            else:
                verified_ex5 += 1

    # 3. Validate all 10 profiles & all 90 .set files against parsed MQL5 inputs
    mqh_keys = set(parity.parse_mq5_source(exports_dir / "Include/Naqex_PropGuard.mqh")["inputs"])
    orch_keys = set(parity.parse_mq5_source(exports_dir / "Naqex_AccountOrchestrator.mq5")["inputs"]) | mqh_keys
    ea_keys_by_stem = {
        Path(c["file"]).stem: set(parity.parse_mq5_source(exports_dir / c["file"])["inputs"]) | mqh_keys
        for c in parity.ENGINE_PARITY_CONTRACTS.values()
    }
    stem_to_eid = {Path(c["file"]).stem: eid for eid, c in parity.ENGINE_PARITY_CONTRACTS.items()}

    presets_checked = 0
    presets_dir = kit_dir / "presets"
    for pname, cfg in OPERATIONAL_PROFILES.items():
        pdir = presets_dir / pname
        if not pdir.exists():
            errors.append(f"Missing profile directory: {pname}")
            continue

        # Check Orchestrator .set
        orch_set = pdir / "Naqex_AccountOrchestrator.set"
        if not orch_set.exists():
            errors.append(f"{pname}: missing Naqex_AccountOrchestrator.set")
        else:
            kv = parse_set_file(orch_set)
            unknown = set(kv) - orch_keys
            if unknown:
                errors.append(f"{pname}/Naqex_AccountOrchestrator.set has unknown keys: {sorted(unknown)}")
            expected_dry = "true" if cfg["dry_run_preset"] else "false"
            if kv.get("InpDryRunLogOnly") != expected_dry or kv.get("InpGuardDryRunLogOnly") != expected_dry:
                errors.append(f"{pname}/Naqex_AccountOrchestrator.set dry-run mismatch (expected {expected_dry})")
            if cfg["arm_locked"] and kv.get("InpDryRunLogOnly") != "true":
                errors.append(f"{pname}: ARM-LOCKED profile must keep InpDryRunLogOnly=true")
            if kv.get("InpAllowManualHaltFile") != "false":
                errors.append(f"{pname}/Naqex_AccountOrchestrator.set must keep InpAllowManualHaltFile=false")
            exp_reset = "1" if cfg["firm"] == "FTMO" else "0"
            if kv.get("InpDailyResetMode") != exp_reset:
                errors.append(
                    f"{pname}/Naqex_AccountOrchestrator.set InpDailyResetMode={kv.get('InpDailyResetMode')} != {exp_reset}"
                )
            pl_pct = float(kv.get("InpProfitLockPct", "-1"))
            pl_mult = float(kv.get("InpProfitLockMult", "-1"))
            if "_P1_" in pname:
                exp_pl_pct = 4.00 if cfg["firm"] == "The5ers" else 5.00
                if abs(pl_pct - exp_pl_pct) > 1e-6 or abs(pl_mult - 1.34) > 1e-6:
                    errors.append(f"{pname}: P1 ProfitLock mismatch (pct={pl_pct}, expected={exp_pl_pct}, mult={pl_mult})")
            elif "_P2_" in pname:
                if abs(pl_pct - 3.00) > 1e-6 or not (0.20 <= pl_mult <= 2.00):
                    errors.append(f"{pname}: P2 ProfitLock mismatch (pct={pl_pct}, mult={pl_mult})")
            elif any(tag in pname for tag in ("FreeTrial", "Funded")):
                if abs(pl_pct) > 1e-6:
                    errors.append(f"{pname}: FreeTrial/Funded must keep InpProfitLockPct=0.00 (got {pl_pct})")
            hb_sec = int(kv.get("InpGuardNewsHardBanSec", "0"))
            pad_sec = int(kv.get("InpGuardNewsPadSec", "0"))
            if hb_sec != 135 or hb_sec >= pad_sec:
                errors.append(
                    f"{pname}/Naqex_AccountOrchestrator.set invalid hard ban/pad ({hb_sec}/{pad_sec})"
                )
            orch_symcap = float(kv.get("InpGuardMaxSymbolRiskPct", "99"))
            if any(tag in pname for tag in ("FreeTrial", "Funded")) and orch_symcap > 1.00 + 1e-9:
                errors.append(f"{pname}/Naqex_AccountOrchestrator.set SYMCAP > 1.00 ({orch_symcap})")
            elif "_P2_" in pname and orch_symcap > 1.50 + 1e-9:
                errors.append(f"{pname}/Naqex_AccountOrchestrator.set P2 SYMCAP > 1.50 ({orch_symcap})")
            elif "_P1_" in pname and orch_symcap > 2.00 + 1e-9:
                errors.append(f"{pname}/Naqex_AccountOrchestrator.set P1 SYMCAP > 2.00 ({orch_symcap})")
            presets_checked += 1

        # Check profile_meta.json firm-specific chart attachment mapping
        meta_path = pdir / "profile_meta.json"
        if not meta_path.exists():
            errors.append(f"{pname}: missing profile_meta.json")
        else:
            meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
            att = meta_data.get("chart_attachments", {})
            exp_idx_sym = "NAS100" if cfg["firm"] == "The5ers" else "US100.cash"
            for idx_eid in ("E4_US100_SESS40", "E5_US100_RS1130"):
                got_sym = att.get(idx_eid, {}).get("symbol")
                if got_sym != exp_idx_sym:
                    errors.append(f"{pname}/profile_meta.json {idx_eid} symbol={got_sym!r} != {exp_idx_sym!r}")
            if cfg["firm"] == "The5ers" and not meta_data.get("broker_symbol_verification_note"):
                errors.append(f"{pname}/profile_meta.json missing broker_symbol_verification_note")

        # Check all 8 EA .set files
        for stem, valid_keys in ea_keys_by_stem.items():
            eid = stem_to_eid[stem]
            sp = pdir / f"{stem}.set"
            if not sp.exists():
                errors.append(f"{pname}: missing {stem}.set")
                continue
            kv = parse_set_file(sp)
            unknown = set(kv) - valid_keys
            if unknown:
                errors.append(f"{pname}/{stem}.set has unknown keys: {sorted(unknown)}")

            exp_magic = str(parity.ENGINE_PARITY_CONTRACTS[eid]["expected_inputs"]["InpMagicNumber"])
            if kv.get("InpMagicNumber") != exp_magic:
                errors.append(f"{pname}/{stem}.set magic={kv.get('InpMagicNumber')} != {exp_magic}")

            # US100.cash / NAS100 spread guard sanity (FTMO Demo measured spread = 195 pts)
            if eid in ("E4_US100_SESS40", "E5_US100_RS1130"):
                sp_cap = float(kv.get("InpGuardMaxSpreadPoints", "0"))
                if sp_cap < 350.0:
                    errors.append(f"{pname}/{stem}.set US100 InpGuardMaxSpreadPoints={sp_cap} < 350.0")

            # Red-news enforcement & safe pre-flatten hard ban window check
            exp_news = "true" if cfg["enable_red_news"] else "false"
            if kv.get("InpGuardEnableRedNews") != exp_news:
                errors.append(f"{pname}/{stem}.set InpGuardEnableRedNews={kv.get('InpGuardEnableRedNews')} != {exp_news}")
            ea_hb = int(kv.get("InpGuardNewsHardBanSec", "0"))
            ea_pad = int(kv.get("InpGuardNewsPadSec", "0"))
            if ea_hb != 135 or ea_hb >= ea_pad:
                errors.append(f"{pname}/{stem}.set invalid hard ban/pad ({ea_hb}/{ea_pad})")

            # Arm-lock safety check
            if cfg["arm_locked"]:
                if kv.get("InpDryRunLogOnly") != "true" or kv.get("InpGuardDryRunLogOnly") != "true":
                    errors.append(f"{pname}/{stem}.set violates ARM-LOCKED InpDryRunLogOnly=true")

            # Tightened SYMCAP invariants: FreeTrial/Funded <= 1.00, P2 <= 1.50, P1 <= 2.00
            symcap = float(kv.get("InpGuardMaxSymbolRiskPct", "99"))
            if any(tag in pname for tag in ("FreeTrial", "Funded")):
                if symcap > 1.00 + 1e-9:
                    errors.append(f"{pname}/{stem}.set SYMCAP_100 violated: {symcap} > 1.00")
            elif "_P2_" in pname:
                if symcap > 1.50 + 1e-9:
                    errors.append(f"{pname}/{stem}.set P2 SYMCAP violated: {symcap} > 1.50")
            elif "_P1_" in pname:
                if symcap > 2.00 + 1e-9:
                    errors.append(f"{pname}/{stem}.set P1 SYMCAP violated: {symcap} > 2.00")

            # Verify Orchestrator base_phase_mult stays inside Naqex_PropGuard.mqh [0.20, 3.50] clamp
            if not (0.20 <= float(cfg["base_phase_mult"]) <= 3.50):
                errors.append(f"{pname}: base_phase_mult={cfg['base_phase_mult']} outside PropGuard [0.20, 3.50]")

            presets_checked += 1

    # 4. Check Activation Card, Watchdog & Flat-Only Sync script existence & anti-bloat across exports/
    for req_file in (
        kit_dir / "ACTIVATION-CARD-LOCAL-MT5.md",
        kit_dir / "ops_watchdog/naqex_mt5_watchdog.ps1",
        kit_dir / "vps_kit/sync_updated_ex5_when_flat.ps1",
    ):
        if not req_file.exists():
            errors.append(f"Missing required kit artifact: {req_file.relative_to(REPO_ROOT)}")

    for f in exports_dir.rglob("*"):
        if f.is_file():
            if f.suffix.lower() == ".ex5":
                errors.append(f"Binary .ex5 must not live inside tracked exports/: {f.relative_to(REPO_ROOT)}")
            if f.stat().st_size > ANTI_BLOAT_LIMIT_BYTES:
                errors.append(f"Anti-bloat violation (>900 KB): {f.relative_to(REPO_ROOT)}")

    return {
        "schema": "naqex-deployment-kit-verify-v1",
        "ok": len(errors) == 0,
        "profiles_expected": len(OPERATIONAL_PROFILES),
        "presets_checked": presets_checked,
        "verified_tracked_files": verified_tracked,
        "verified_ex5_files": verified_ex5,
        "parity_ok": parity_rep["ok"],
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build or verify the Naqex MT5 Deployment Kit.")
    ap.add_argument("--build", action="store_true", help="Generate all 10 .set profiles and manifest.sha256.json.")
    ap.add_argument("--require-ex5", action="store_true", help="Require all 9 compiled .ex5 binaries & clean compile logs.")
    ap.add_argument("--json", action="store_true", help="Output JSON report.")
    ap.add_argument("--p1-balanced-mult", type=float, default=None, help="Optional override for P1 Balanced multiplier.")
    ap.add_argument("--p1-sprint-mult", type=float, default=None, help="Optional override for P1 Sprint multiplier.")
    ap.add_argument("--calibration-tag", type=str, default=None, help="Calibration provenance tag for P1 overrides.")
    ap.add_argument(
        "--preview-tier-json",
        type=str,
        default=None,
        help="Read-only JSON preview of a scaled tier config: <firm>:<capital>:<phase>:<dd_mode> (e.g. The5ers:50000:P1_Balanced:4_8).",
    )
    args = ap.parse_args(argv)

    if args.preview_tier_json:
        try:
            preview = parse_preview_tier_spec(args.preview_tier_json)
        except ValueError as exc:
            print(json.dumps({"ok": False, "order_send_count": 0, "error": str(exc)}, indent=2), file=sys.stderr)
            return 2
        print(json.dumps(preview, indent=2, ensure_ascii=False))
        return 0

    if args.build:
        overrides: dict[str, dict[str, Any]] = {}
        if args.p1_balanced_mult is not None:
            for k in ("FTMO_P1_Balanced_3to6m", "The5ers_HighStakes_P1_Balanced"):
                overrides[k] = {"base_phase_mult": float(args.p1_balanced_mult)}
                if args.calibration_tag:
                    overrides[k]["calibration_tag"] = args.calibration_tag
        if args.p1_sprint_mult is not None:
            for k in ("FTMO_P1_Sprint_1to3m", "The5ers_HighStakes_P1_Sprint"):
                overrides[k] = {"base_phase_mult": float(args.p1_sprint_mult)}
                if args.calibration_tag:
                    overrides[k]["calibration_tag"] = args.calibration_tag
        build_presets_and_manifest(overrides=overrides or None)

    rep = verify_kit(require_ex5=args.require_ex5)
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print(
            f"Deployment Kit Verify: {'PASS' if rep['ok'] else 'FAIL'} | "
            f"profiles={rep['profiles_expected']} presets={rep['presets_checked']} "
            f"tracked_sha={rep['verified_tracked_files']} ex5_sha={rep['verified_ex5_files']}"
        )
        for err in rep["errors"]:
            print(f"  ERR: {err}")
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
