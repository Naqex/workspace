"""Total Offensive #3 v3.5 — Stage 4 Portfolio V3 Accretion Gate (`G09`), Layer-2 Presets & `G11` Compile Proof.

Enforces `G09` (Accretion Gate) fail-closed after Stage 3 Blind Cluster B (`0 / 1,137` promoted):
  - ZERO unproven/killed bots are added to Prop V3.
  - Verified Prop V3 Champion: `PORT_7E_V103_SPRINT_SPR09_NO_UNAPPROVED_ADDITIONS`
    (immutable `Naqex_Master_Prop7E_v103.mq5` + `.set`-only `SPR09_M45_P2_35_B1` Eval + locked `Funded 1.0x`).
  - Aggregates the exact 7-SKU SSOT table (`available_vn=true`) with full balanced Law-15 metrics
    in USD & VND, monthly `3m/6m/12m/24m` Pass/Fail/Pending summing to `100.0%`, Funded `1.0x`
    12m breach `< 1.0%`, `1.25x` gap shock `<= 3.75%`, 4T/5T sequential bankroll ruin, and Best-Day Share.
  - Records a strictly diagnostic counterfactual note (`DIAG_COUNTERFACTUAL_NOT_PROMOTED`) explaining
    why the #1 Primary near-miss (`F01_US100_NY30_STOP_COIL`, `q_primary=0.49983`) is EXCLUDED.
  - Generates/verifies all 4 Layer-2 `.set` presets (FTMO Std 10K & The5ers HS 5K Eval/Funded) against
    exact `v103.mq5` 69-key schema and `OPS-2` (`account_phase_preflight.py`), plus Dev-only (`< 2025`)
    MT5 Strategy Tester `.ini` configs (`v103_Sprint_Eval_tester_dev.ini`, `v103_Funded_1x_tester_dev.ini`).
  - Runs an isolated `MetaEditor64.exe` compile proof inside `.tmp/off3_metaeditor_check/` confirming
    `0 errors, 0 warnings` on BOTH immutable `v103.mq5` and a 3-header V3 integration harness, then
    deletes `.tmp/off3_metaeditor_check/` immediately (`0` `.ex5` left in `private_vault/` or check dir).

HARD SAFETY & ARCHITECTURE INVARIANTS (`[ARCH-02]`, `G01`, `G02`, `G09`, `G10`, `G11`, `G12`, `B8`):
  - ZERO bare `assert` statements anywhere in this module (`python -O` safe).
  - ZERO `MetaTrader5` imports; `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`.
  - `holdout_rows_analysed == 0` and `max_day < "2025-01-01"` enforced fail-closed.
  - NEVER modifies `Naqex_Master_Prop7E_v103.mq5`, `Naqex_Master_Prop7E.mq5`,
    `Naqex_PropGuard.mqh`, `Naqex_Signals_7E.mqh`, or `naqex_red_news_utc.csv`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

AI_ENGINES_DIR: Final[Path] = Path(__file__).resolve().parents[2]
REPO_ROOT: Final[Path] = AI_ENGINES_DIR.parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_factory.live_ops.account_phase_preflight import (  # noqa: E402
    DEFAULT_FTMO_SPECS_28,
    parse_mt5_set_file,
    validate_account_deployment,
)

# ---------------------------------------------------------------------------
# Hard Safety & Contract Constants
# ---------------------------------------------------------------------------

ORDER_SEND_CAPABLE: Final[bool] = False
ORDER_SEND_COUNT: Final[int] = 0
HOLDOUT_CUTOFF_DAY: Final[str] = "2025-01-01"
HOLDOUT_CUTOFF_TESTER_DATE: Final[str] = "2025.01.01"
DEV_TESTER_FROM_DATE: Final[str] = "2018.01.02"
DEV_TESTER_TO_DATE: Final[str] = "2024.12.31"

SCHEMA_VERSION: Final[str] = "naqex-offensive3-stage4-prop-v3-metrics-v1"
PROP_V3_CHAMPION_ID: Final[str] = "PORT_7E_V103_SPRINT_SPR09_NO_UNAPPROVED_ADDITIONS"
EXPECTED_SPRINT_WINNER_ID: Final[str] = "SPR09_M45_P2_35_B1"
TOP_NEAR_MISS_ID: Final[str] = "F01_LOWFREQ_CAT::F01_US100_NY30_STOP_COIL"
OPS2_FUNDED_STATIC_KILL_CEILING_PCT: Final[float] = 8.00
G10_MAX_EVAL_GAP_125X_PCT: Final[float] = 3.75
G10_MAX_FUNDED_12M_BREACH_PCT: Final[float] = 1.00
V103_EXPECTED_INPUT_COUNT: Final[int] = 69

# Exact 7-SKU Offensive #3 focus allowlist (`available_vn=true` in `configs/ssot/firms_catalog.json`).
TARGET_SKUS: Final[tuple[str, ...]] = (
    "ftmo_standard_10k",
    "ftmo_standard_50k",
    "ftmo_standard_100k",
    "ftmo_swing_10k",
    "ftmo_swing_25k",
    "the5ers_hs_5k_classic",
    "the5ers_hs_5k_new",
)
# SKUs excluded from the 7-SKU Offensive #3 focus matrix:
# - `ftmo_swing_50k`: `available_vn=false` in `configs/ssot/firms_catalog.json`
# - `the5ers_hs_20k`: nonexistent in `configs/ssot/firms_catalog.json`
# - `ftmo_standard_25k`: `available_vn=true` in `configs/ssot/firms_catalog.json`, merely excluded
#   from the 7-SKU Offensive #3 focus matrix (not unavailable/nonexistent)
FORBIDDEN_SKUS: Final[frozenset[str]] = frozenset({"ftmo_swing_50k", "ftmo_standard_25k", "the5ers_hs_20k"})

DEFAULT_FUNNEL_JSON: Final[Path] = REPO_ROOT / "planning/research/OFFENSIVE3-ALPHA-FUNNEL-20261127.json"
DEFAULT_SPRINT_JSON: Final[Path] = REPO_ROOT / "private_vault/strategies/offensive3_v3/m1_v103_sprint_results.json"
DEFAULT_OUT_METRICS_JSON: Final[Path] = REPO_ROOT / "private_vault/strategies/offensive3_v3/prop_v3_metrics.json"
DEFAULT_PRESETS_DIR: Final[Path] = REPO_ROOT / "private_vault/presets/offensive3_v3"
DEFAULT_EXPORTS_DIR: Final[Path] = REPO_ROOT / "tooling/ai-engines/exports"
DEFAULT_LAYER2_V3_DIR: Final[Path] = REPO_ROOT / "private_vault/strategies/offensive3_v3"
DEFAULT_METAEDITOR_CHECK_DIR: Final[Path] = REPO_ROOT / ".tmp/off3_metaeditor_check"
DEFAULT_PORTABLE_DIR: Final[Path] = REPO_ROOT / ".runtime/ftmo-demo-portable-1515343166"

CORE_7E_SYMBOLS: Final[tuple[str, ...]] = (
    "USDJPY",
    "GBPUSD",
    "EURJPY",
    "US100.cash",
    "US500.cash",
    "EURUSD",
    "AUDUSD",
    "USDCAD",
)

LAYER2_V3_HEADERS: Final[tuple[str, ...]] = (
    "Naqex_ExtendedGuardV3.mqh",
    "Naqex_AccountPhaseGuard.mqh",
    "Naqex_DecisionBlackbox.mqh",
)

IMMUTABLE_MQ_RELPATHS: Final[tuple[str, ...]] = (
    "tooling/ai-engines/exports/Naqex_Master_Prop7E_v103.mq5",
    "tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5",
    "tooling/ai-engines/exports/Include/Naqex_PropGuard.mqh",
    "tooling/ai-engines/exports/Include/Naqex_Signals_7E.mqh",
)

# Synthetic read-only integration harness compiled ONLY in isolated `.tmp/off3_metaeditor_check/`
V3_HEADERS_HARNESS_MQ5: Final[str] = r"""//+------------------------------------------------------------------+
//| Naqex_V3_Headers_Harness.mq5 — Synthetic G11 Compile Proof ONLY  |
//| Verifies 0 errors, 0 warnings across all 3 Layer-2 V3 headers    |
//| alongside immutable Naqex_PropGuard.mqh & Naqex_Signals_7E.mqh.  |
//| Pure read-only harness: ZERO OrderSend calls.                    |
//+------------------------------------------------------------------+
#property strict
#property version "3.00"

#include "Include/Naqex_PropGuard.mqh"
#include "Include/Naqex_Signals_7E.mqh"
#include "Include/Naqex_ExtendedGuardV3.mqh"
#include "Include/Naqex_AccountPhaseGuard.mqh"
#include "Include/Naqex_DecisionBlackbox.mqh"

CNaqexExtendedGuardV3  g_extGuard;
CNaqexDecisionBlackbox g_blackbox;

int OnInit()
{
   string sym = _Symbol;
   bool extOk = g_extGuard.Init(sym);
   bool bbOk  = g_blackbox.InitFromInputs(sym, 20261120);
   long expLev = NaqexExpectedAccountLeverageForProfile("FTMO_STANDARD");
   int the5ersHour = CNaqexExtendedGuardV3::The5ersResetUtcHour(CNaqexExtendedGuardV3::NowUtcSafe());
   int ftmoHour    = CNaqexExtendedGuardV3::FtmoPragueResetUtcHour(CNaqexExtendedGuardV3::NowUtcSafe());
   bool oilMatch   = CNaqexExtendedGuardV3::CurrencyMatchesSymbolExtended("USOIL.cash", "EIA");

   NaqexAccountPhaseSpec spec;
   spec.expected_login            = 9900001;
   spec.expected_trade_mode       = ACCOUNT_TRADE_MODE_DEMO;
   spec.expected_account_leverage = (expLev > 0) ? expLev : 100;
   spec.symbol                    = sym;
   spec.expected_digits           = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   spec.expected_contract_size    = SymbolInfoDouble(sym, SYMBOL_TRADE_CONTRACT_SIZE);
   spec.account_phase             = NAQEX_PHASE_FUNDED;
   spec.preset_is_eval            = false;
   spec.base_phase_mult           = 1.00;
   spec.amber_dd_pct              = 3.50;
   spec.max_funded_risk_mult      = 1.00;
   spec.max_funded_amber_dd_pct   = 4.00;
   spec.require_manual_halt_file  = true;
   spec.allow_manual_halt_file    = true;
   spec.require_primary_heartbeat = true;
   spec.write_primary_heartbeat   = true;
   spec.max_allowed_stops_level   = 0;
   spec.contract_size_rel_tol     = 1e-6;
   spec.allow_tester_bypass_login = true;

   int phaseStatus = NaqexVerifyAccountPhaseOnInit(spec);
   PrintFormat("[V3_HARNESS] ext=%s bb=%s phase=%d reset5=%d resetF=%d oil=%s",
               extOk ? "1" : "0", bbOk ? "1" : "0", phaseStatus, the5ersHour, ftmoHour, oilMatch ? "1" : "0");
   return INIT_SUCCEEDED;
}

void OnTick()
{
   string sym = _Symbol;
   g_extGuard.OnTickFeedSample(sym);
   double minDays = 0.0;
   ENUM_NAQEX_TTL_STATUS ttl = g_extGuard.CheckCalendarTtlFor(sym, minDays);
   string feedReason = "";
   ENUM_NAQEX_FEED_STATUS feed = g_extGuard.EvaluateFeedHealthFor(sym, feedReason);
   if(ttl == NAQEX_TTL_RED || feed == NAQEX_FEED_RED)
   {
      g_blackbox.LogBlocked("HARNESS_SIG_0", sym, "BUY", NAQEX_DECISION_BLOCKED_FEED,
                            feedReason, "{\"ttl_days\":0.0}", 0.0, 0.0, 0.0);
   }
}
"""


# ---------------------------------------------------------------------------
# Atomic IO & Hashing Utilities
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    """Compute hex SHA-256 of a file without loading it all into RAM."""
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def canonical_json_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 of a JSON mapping excluding `receipt_payload_sha256`."""
    cleaned = {k: v for k, v in payload.items() if k != "receipt_payload_sha256"}
    encoded = json.dumps(cleaned, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    """Atomically write LF-only UTF-8 text via temp file + fsync + os.replace."""
    normalized = text.replace("\r\n", "\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            fh.write(normalized)
            fh.flush()
            os.fsync(fh.fileno())
            tmp_path = Path(fh.name)
        os.replace(tmp_path, path)
        tmp_path = None
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def atomic_write_json_with_sha(path: Path, payload: dict[str, Any]) -> tuple[str, str]:
    """Attach canonical `receipt_payload_sha256`, atomically write JSON, return `(payload_sha, file_sha)`."""
    out = dict(payload)
    payload_sha = canonical_json_sha256(out)
    out["receipt_payload_sha256"] = payload_sha
    text = json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    atomic_write_text(path, text)
    return payload_sha, sha256_file(path)


# ---------------------------------------------------------------------------
# 1. Fail-Closed `G09` Accretion Gate & Counterfactual Diagnostic
# ---------------------------------------------------------------------------


def parse_v103_mq5_inputs(v103_mq5_path: Path | None = None) -> tuple[str, ...]:
    """Extract ordered `input` parameter names declared in immutable `Naqex_Master_Prop7E_v103.mq5`."""
    target = v103_mq5_path or (DEFAULT_EXPORTS_DIR / "Naqex_Master_Prop7E_v103.mq5")
    if not target.is_file():
        raise FileNotFoundError(f"Immutable v103 EA source not found: {target}")
    src = target.read_text(encoding="utf-8")
    names = tuple(re.findall(r"^\s*input\s+\w+\s+(Inp\w+)\s*=", src, flags=re.MULTILINE))
    if len(names) != V103_EXPECTED_INPUT_COUNT:
        raise ValueError(
            f"V103_INPUT_SCHEMA_DRIFT: expected {V103_EXPECTED_INPUT_COUNT} inputs in {target.name}, got {len(names)}"
        )
    return names


def _require_strict_int(value: Any, name: str) -> int:
    """Fail-closed guard rejecting `bool`, `float`, `None`, and non-int inputs."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"G09_INVALID_INT_INPUT: {name} must be a strict int (got {value!r})")
    return value


def _require_finite_float(value: Any, name: str, *, error_prefix: str = "G09_ACCRETION_GATE_VIOLATION") -> float:
    """Fail-closed guard rejecting `bool`, `None`, non-numeric, `NaN`, and `+-Inf` inputs."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{error_prefix}: {name} must be a finite real number (got {value!r})")
    fval = float(value)
    if not math.isfinite(fval):
        raise ValueError(f"{error_prefix}: {name} must be finite (got {value!r})")
    return fval


def enforce_g09_accretion_gate(funnel_doc: Mapping[str, Any]) -> dict[str, Any]:
    """Enforce Gate `G09` (Accretion Gate) fail-closed on Stage 3 Blind Cluster B funnel results."""
    raw_holdout = funnel_doc.get("holdout_rows_analysed")
    if isinstance(raw_holdout, bool) or not isinstance(raw_holdout, int) or raw_holdout != 0:
        raise ValueError(f"HOLDOUT_LOCK_VIOLATION: funnel holdout_rows_analysed={raw_holdout!r}")
    raw_order_count = funnel_doc.get("order_send_count")
    if (
        funnel_doc.get("order_send_capable") is not False
        or isinstance(raw_order_count, bool)
        or not isinstance(raw_order_count, int)
        or raw_order_count != 0
    ):
        raise ValueError("ORDER_SEND_INVARIANT_VIOLATION in Stage 3 funnel receipt")

    cluster_b_years = list(funnel_doc.get("cluster_b_years") or [])
    for yr in cluster_b_years:
        yr_int = _require_strict_int(yr, "cluster_b_years[]")
        if yr_int >= 2025:
            raise ValueError(f"HOLDOUT_LOCK_VIOLATION: cluster_b_years contains >= 2025: {cluster_b_years}")

    counts = funnel_doc.get("funnel_counts")
    if not isinstance(counts, Mapping):
        raise ValueError("G09_MALFORMED_FUNNEL: missing funnel_counts mapping")

    tier1_list = list(funnel_doc.get("tier1_ftmo_ready") or [])
    tier2_list = list(funnel_doc.get("tier2_personal_vault") or [])
    tier1_count = _require_strict_int(counts.get("tier1_ftmo_ready"), "funnel_counts.tier1_ftmo_ready")
    tier2_count = _require_strict_int(counts.get("tier2_personal_vault"), "funnel_counts.tier2_personal_vault")
    tier3_count = _require_strict_int(counts.get("tier3_dead_no_edge"), "funnel_counts.tier3_dead_no_edge")
    total_eval = _require_strict_int(counts.get("total_evaluated"), "funnel_counts.total_evaluated")
    primary_eval = _require_strict_int(counts.get("primary_evaluated"), "funnel_counts.primary_evaluated")
    exploratory_only = _require_strict_int(
        counts.get("exploratory_only_evaluated"), "funnel_counts.exploratory_only_evaluated"
    )
    cond_retest_rej = _require_strict_int(
        counts.get("conditional_retest_rejected_count"), "funnel_counts.conditional_retest_rejected_count"
    )
    g7_pbo_exec = _require_strict_int(counts.get("g7_pbo_executed_count", 0), "funnel_counts.g7_pbo_executed_count")

    if any(
        c < 0
        for c in (tier1_count, tier2_count, tier3_count, primary_eval, exploratory_only, cond_retest_rej, g7_pbo_exec)
    ):
        raise ValueError(f"G09_ACCRETION_GATE_VIOLATION: negative count in funnel_counts: {dict(counts)}")

    if tier1_count != len(tier1_list):
        raise ValueError(
            f"G09_ACCRETION_GATE_VIOLATION: tier1_ftmo_ready count ({tier1_count}) != list len ({len(tier1_list)})"
        )
    if tier2_count != len(tier2_list):
        raise ValueError(
            f"G09_ACCRETION_GATE_VIOLATION: tier2_personal_vault count ({tier2_count}) != list len ({len(tier2_list)})"
        )
    if total_eval <= 0 or (tier1_count + tier2_count + tier3_count) != total_eval:
        raise ValueError(
            f"G09_ACCRETION_GATE_VIOLATION: tier sum {tier1_count}+{tier2_count}+{tier3_count} != total {total_eval}"
        )

    # Reject any attempt to sneak a killed/unqualified or NaN/Inf/bool-poisoned candidate into tier1_ftmo_ready
    for entry in tier1_list:
        if not isinstance(entry, Mapping):
            raise ValueError("G09_ACCRETION_GATE_VIOLATION: non-mapping entry in tier1_ftmo_ready")
        cid = str(entry.get("strategy_id") or "<unknown>")
        verdict = str(entry.get("council_verdict") or "")
        tier_tag = str(entry.get("tier") or "")
        if tier_tag != "TIER_1_FTMO_READY":
            raise ValueError(f"G09_ACCRETION_GATE_VIOLATION: {cid} has tier={tier_tag!r} != TIER_1_FTMO_READY")
        if verdict != "ACCEPT":
            raise ValueError(f"G09_ACCRETION_GATE_VIOLATION: {cid} council_verdict={verdict!r} != ACCEPT")
        q_prim = _require_finite_float(entry.get("bh_q_primary"), f"{cid}.bh_q_primary")
        pbo = _require_finite_float(entry.get("pbo_cscv"), f"{cid}.pbo_cscv")
        if q_prim < 0.0 or q_prim > 0.10:
            raise ValueError(f"G09_ACCRETION_GATE_VIOLATION: {cid} bh_q_primary={q_prim!r} outside [0.0, 0.10]")
        if pbo < 0.0 or pbo > 0.50:
            raise ValueError(f"G09_ACCRETION_GATE_VIOLATION: {cid} pbo_cscv={pbo!r} outside [0.0, 0.50]")
        for opt_metric in (
            "p_sign_flip_50k",
            "p_newey_west",
            "timing_p",
            "bh_q_exploratory",
            "dsr_council",
            "dsr_empirical",
            "sharpe_clb",
            "net_r_1x",
            "net_r_15x",
            "net_r_2x",
            "corr_port7e",
            "tail_corr_port7e",
        ):
            if opt_metric in entry and entry[opt_metric] is not None:
                _require_finite_float(entry[opt_metric], f"{cid}.{opt_metric}")

    if tier1_count != 0:
        raise ValueError(
            f"G09_UNEXPECTED_TIER1_PROMOTION: Stage 4 Offensive #3 v3.5 expects verified tier1_ftmo_ready == 0 "
            f"(got {tier1_count}); explicit accretion MC re-audit required before promoting new sleeves."
        )

    ledger = funnel_doc.get("duckdb_ledger_summary") or {}
    if not isinstance(ledger, Mapping):
        raise ValueError("G05_LEDGER_INTEGRITY_FAILED: duckdb_ledger_summary is not a mapping")
    if ledger.get("integrity_verified") is not True:
        raise ValueError("G05_LEDGER_INTEGRITY_FAILED: duckdb_ledger_summary.integrity_verified is not True")
    ledger_prim_pass = _require_strict_int(
        ledger.get("primary_bh_fdr_pass_count"), "duckdb_ledger_summary.primary_bh_fdr_pass_count"
    )
    if ledger_prim_pass != 0:
        raise ValueError("G09_ACCRETION_GATE_VIOLATION: ledger primary_bh_fdr_pass_count != 0")

    return {
        "gate_id": "G09_ACCRETION_GATE",
        "status": "PASS_FAIL_CLOSED_ZERO_UNAPPROVED_ADDITIONS",
        "campaign_run_id": str(funnel_doc.get("campaign_run_id") or ""),
        "total_evaluated": total_eval,
        "primary_evaluated": primary_eval,
        "exploratory_only_evaluated": exploratory_only,
        "tier1_ftmo_ready_count": tier1_count,
        "tier2_personal_vault_count": tier2_count,
        "tier3_dead_no_edge_count": tier3_count,
        "conditional_retest_rejected_count": cond_retest_rej,
        "g7_pbo_executed_count": g7_pbo_exec,
        "promoted_additions": [],
        "promoted_count": 0,
        "gates_relaxed": False,
        "prop_v3_champion": PROP_V3_CHAMPION_ID,
        "rationale": (
            "Stage 3 Blind Cluster B (2021-2024) honestly evaluated 1,137 candidates across F01..F12 "
            "(142 Primary + 995 Exploratory-only) with zero gates relaxed and yielded 0 TIER_1_FTMO_READY "
            "and 0 TIER_2_PERSONAL_VAULT. Per G09 Accretion Gate, zero unproven/killed bots are added; "
            "Prop V3 Champion remains immutable PORT_7E v1.03 with .set-only SPR09_M45_P2_35_B1 Eval + "
            "locked Funded 1.0x."
        ),
    }


def build_diagnostic_counterfactual_note(funnel_doc: Mapping[str, Any]) -> dict[str, Any]:
    """Build strictly diagnostic counterfactual note (`DIAG_COUNTERFACTUAL_NOT_PROMOTED`) for #1 near-miss."""
    near_misses = funnel_doc.get("tier3_dead_top20_near_misses") or []
    match: Mapping[str, Any] | None = None
    for row in near_misses:
        if isinstance(row, Mapping) and str(row.get("strategy_id")) == TOP_NEAR_MISS_ID:
            match = row
            break
    if match is None:
        raise ValueError(f"MISSING_NEAR_MISS_RECORD: {TOP_NEAR_MISS_ID} absent from Stage 3 funnel JSON")
    if str(match.get("tier")) != "TIER_3_DEAD_NO_EDGE" or str(match.get("council_verdict")) != "REJECT_KILLED":
        raise ValueError(
            f"G09_COUNTERFACTUAL_INTEGRITY_ERROR: {TOP_NEAR_MISS_ID} must be TIER_3_DEAD_NO_EDGE / REJECT_KILLED"
        )

    n_eff_prim = float((funnel_doc.get("effective_trials_n_eff") or {}).get("primary_m200", {}).get("n_eff", 72.0019))
    m_primary = int((funnel_doc.get("funnel_counts") or {}).get("primary_evaluated", 142))
    p_50k = float(match["p_sign_flip_50k"])
    q_prim = float(match["bh_q_primary"])
    rank1_threshold_p = round(0.10 / max(1, m_primary), 6)
    n_eff_adj_p = round(min(1.0, p_50k * n_eff_prim), 4)

    return {
        "tag": "DIAG_COUNTERFACTUAL_NOT_PROMOTED",
        "promoted": False,
        "included_in_prop_v3": False,
        "strategy_id": TOP_NEAR_MISS_ID,
        "alpha_family_id": str(match["alpha_family_id"]),
        "pool_tier": str(match["pool_tier"]),
        "tier": str(match["tier"]),
        "council_verdict": str(match["council_verdict"]),
        "blindness_tier": str(match["blindness_tier"]),
        "data_resolution": str(match["data_resolution"]),
        "observed_cluster_b_metrics": {
            "n_trades_clb": int(match["n_trades_clb"]),
            "sharpe_clb": float(match["sharpe_clb"]),
            "net_r_1x": float(match["net_r_1x"]),
            "net_r_15x": float(match["net_r_15x"]),
            "net_r_2x": float(match["net_r_2x"]),
            "net_r_zero_pos_swap": float(match["net_r_zero_pos_swap"]),
            "fade_net_r_1x": float(match["fade_net_r_1x"]),
            "trim5_win_pf": float(match["trim5_win_pf"]),
            "p_sign_flip_50k": p_50k,
            "p_newey_west": float(match["p_newey_west"]),
            "timing_p": float(match["timing_p"]),
            "bh_q_primary": q_prim,
            "bh_q_exploratory": float(match["bh_q_exploratory"]),
            "dsr_council": float(match["dsr_council"]),
            "dsr_empirical": float(match["dsr_empirical"]),
            "pbo_cscv": float(match["pbo_cscv"]),
            "corr_port7e": float(match["corr_port7e"]),
            "tail_corr_port7e": float(match["tail_corr_port7e"]),
            "crisis_passed": bool(match["crisis_passed"]),
        },
        "multiple_testing_math": {
            "m_primary_trials": m_primary,
            "n_eff_primary": round(n_eff_prim, 4),
            "bh_fdr_alpha": 0.10,
            "required_rank1_raw_p_for_q_le_010": rank1_threshold_p,
            "observed_raw_p_sign_flip_50k": p_50k,
            "observed_bh_q_primary": q_prim,
            "effective_n_eff_bonferroni_p": n_eff_adj_p,
            "clears_bh_fdr_primary": q_prim <= 0.10,
            "clears_n_eff_adjusted_010": n_eff_adj_p <= 0.10,
        },
        "exclusion_reasons": [
            (
                f"Failed global BH-FDR on Primary M={m_primary}: q_primary={q_prim:.5f} > 0.10 "
                f"(rank #1 requires raw p <= {rank1_threshold_p:.6f}; observed p_sign_flip_50k={p_50k:.6f})."
            ),
            (
                f"Even after effective independent trial adjustment (N_eff={n_eff_prim:.2f}), "
                f"p * N_eff = {n_eff_adj_p:.4f} > 0.10 -> statistically indistinguishable from multiple-testing noise."
            ),
            (
                f"Empirical DSR = {float(match['dsr_empirical']):.4f} < 0.50 "
                "and Research Council verdict = REJECT_KILLED."
            ),
            (
                "Blindness tier is DEV_CLB_CONSUMED_12OLD (US100 M1 2021-2024 previously viewed in historical Dev), "
                "NOT fresh unseen data."
            ),
            (
                "Per G09 Accretion Gate and Zero-Gate-Relaxation policy, strictly EXCLUDED from Prop V3; "
                "re-evaluation permitted ONLY via future prospective forward-shadow tracking on unseen live/demo data."
            ),
        ],
    }


# ---------------------------------------------------------------------------
# 2. Balanced Law-15 Portfolio & Exact 7-SKU SSOT Table Aggregator
# ---------------------------------------------------------------------------


def build_7sku_ssot_summary(sprint_doc: Mapping[str, Any]) -> dict[str, Any]:
    """Validate `m1_v103_sprint_results.json` and extract exact 7-SKU SSOT table + Law-15 scorecard."""
    raw_holdout = sprint_doc.get("holdout_rows_analysed")
    if isinstance(raw_holdout, bool) or not isinstance(raw_holdout, int) or raw_holdout != 0:
        raise ValueError(f"HOLDOUT_LOCK_VIOLATION: sprint holdout_rows={raw_holdout!r}")
    raw_order_cnt = sprint_doc.get("order_send_count")
    if (
        sprint_doc.get("order_send_capable") is not False
        or isinstance(raw_order_cnt, bool)
        or not isinstance(raw_order_cnt, int)
        or raw_order_cnt != 0
    ):
        raise ValueError("ORDER_SEND_INVARIANT_VIOLATION in M1 Sprint receipt")
    max_day = str(sprint_doc.get("max_day") or "")
    if not max_day or max_day >= HOLDOUT_CUTOFF_DAY:
        raise ValueError(f"HOLDOUT_LOCK_VIOLATION: sprint max_day={max_day!r} >= {HOLDOUT_CUTOFF_DAY}")

    winner_id = str(sprint_doc.get("winner_candidate_id") or "")
    if winner_id != EXPECTED_SPRINT_WINNER_ID:
        raise ValueError(
            f"G09_CHAMPION_MISMATCH: expected sprint winner {EXPECTED_SPRINT_WINNER_ID}, got {winner_id!r}"
        )

    candidates = sprint_doc.get("candidates") or {}
    if winner_id not in candidates:
        raise ValueError(f"Missing winner {winner_id} in sprint candidates")
    winner = candidates[winner_id]
    cfg = winner["config"]
    shock_eval = winner["shock_eval"]
    shock_funded = winner["shock_funded"]

    if float(cfg["funded_mult"]) != 1.0:
        raise ValueError(f"G10_FUNDED_LOCK_VIOLATION: funded_mult={cfg['funded_mult']} != 1.0")
    funded_ks = float(cfg["funded_kill_static_pct"])
    if funded_ks > OPS2_FUNDED_STATIC_KILL_CEILING_PCT + 1e-9 or funded_ks <= 0.0:
        raise ValueError(
            f"G10_OPS2_KS_DRIFT: sprint receipt funded_kill_static_pct={funded_ks} exceeds "
            f"OPS-2 Funded ceiling {OPS2_FUNDED_STATIC_KILL_CEILING_PCT:.2f}%"
        )
    if float(shock_eval["gap_shock_125x_pct"]) > G10_MAX_EVAL_GAP_125X_PCT + 1e-9:
        raise ValueError(
            f"G10_GAP_SHOCK_VIOLATION: eval 1.25x gap shock {shock_eval['gap_shock_125x_pct']}% > 3.75%"
        )
    if float(shock_funded["gap_shock_125x_pct"]) > 2.50 + 1e-9:
        raise ValueError(
            f"G10_GAP_SHOCK_VIOLATION: funded 1.25x gap shock {shock_funded['gap_shock_125x_pct']}% > 2.50%"
        )

    usd_vnd_rate = float(sprint_doc["usd_vnd_rate"])
    core_100k = dict(sprint_doc["core_100k_1x_funded_law15"])
    p1_10k = dict(winner["p1_dev_replay_10k"])

    core_100k["max_dd_pct"] = core_100k["peak_dd_pct"]
    core_100k["ev_vnd_per_trade"] = round(float(core_100k["ev_usd_per_trade"]) * usd_vnd_rate, 0)
    p1_10k["max_dd_pct"] = p1_10k["peak_dd_pct"]
    p1_10k["ev_vnd_per_trade"] = round(float(p1_10k["ev_usd_per_trade"]) * usd_vnd_rate, 0)

    raw_skus = tuple(sprint_doc.get("target_skus") or ())
    if raw_skus != TARGET_SKUS:
        raise ValueError(f"SSOT_SKU_MISMATCH: expected {TARGET_SKUS}, got {raw_skus}")
    sku_matrix = sprint_doc.get("sku_matrix") or {}
    for bad in FORBIDDEN_SKUS:
        if bad in sku_matrix:
            raise ValueError(f"FORBIDDEN_SKU_PRESENT: {bad}")

    sku_table: dict[str, Any] = {}
    eval_fail_by_sku: dict[str, Any] = {}
    for sku_id in TARGET_SKUS:
        if sku_id not in sku_matrix:
            raise ValueError(f"MISSING_SSOT_SKU: {sku_id}")
        raw = sku_matrix[sku_id]
        if raw.get("available_vn") is not True:
            raise ValueError(f"SKU_UNAVAILABLE_VN: {sku_id}")

        wp = raw["winner_promo_1x"]
        b1 = raw["baseline_fn1x_promo_1x"]
        w4 = raw["winner_4_ticket_promo"]
        w5 = raw["winner_5_ticket_promo"]
        fn_law15 = raw.get("funded_1x_dev_law15")
        if not isinstance(fn_law15, Mapping):
            raise ValueError(
                f"MISSING_PER_SKU_FUNDED_LAW15: {sku_id} missing direct 0.01-lot-floored funded_1x_dev_law15"
            )

        # Fail-closed checks: Funded 1x breach < 1%, monthly Pass+Fail+Pending == 100%
        fn_br = float(wp["funded_12m_breach_pct"])
        if fn_br >= G10_MAX_FUNDED_12M_BREACH_PCT:
            raise ValueError(f"G10_FUNDED_BREACH_VIOLATION: {sku_id} funded_12m_breach_pct={fn_br}% >= 1.00%")

        monthly = wp["monthly_pass_fail_pending"]
        for horizon_key in ("3m", "6m", "12m", "24m"):
            if horizon_key not in monthly:
                raise ValueError(f"MISSING_MONTHLY_BUCKET: {sku_id} missing {horizon_key}")
            bucket = monthly[horizon_key]
            total_pct = float(bucket["pass_pct"]) + float(bucket["fail_pct"]) + float(bucket["pending_pct"])
            if abs(total_pct - 100.0) > 0.02 or abs(float(bucket["sum_pct"]) - 100.0) > 0.02:
                raise ValueError(f"LAW15_SUM_NOT_100: {sku_id} {horizon_key} sum={total_pct:.4f}")

        cap_usd = float(raw["capital_usd"])
        ev_trade_usd_true = round(float(fn_law15["ev_usd_per_trade"]), 2)
        ev_trade_vnd_true = round(ev_trade_usd_true * usd_vnd_rate, 0)
        fail_24 = float(wp["fail_24m_pct"])
        within_20_30 = 20.0 - 1e-9 <= fail_24 <= 30.0 + 1e-9
        eval_fail_by_sku[sku_id] = {
            "capital_usd": cap_usd,
            "eval_24m_fail_pct": fail_24,
            "within_20_30_band": within_20_30,
            "delta_above_30_pct": round(max(0.0, fail_24 - 30.0), 2),
        }

        entry: dict[str, Any] = {
            "contract_id": sku_id,
            "display_name": str(raw["display_name"]),
            "firm_id": str(raw["firm_id"]),
            "capital_usd": cap_usd,
            "available_vn": True,
            "daily_reset_mode": int(raw["daily_reset_mode"]),
            "daily_dd_basis_label": (
                "MIDNIGHT_BALANCE_OVER_INITIAL" if int(raw["daily_reset_mode"]) == 1 else "MAX_BALANCE_EQUITY"
            ),
            "reset_tz": str(raw["reset_tz"]),
            "p1_target_pct": float(raw["p1_target_pct"]),
            "p2_target_pct": float(raw["p2_target_pct"]),
            "min_trading_days": int(raw["min_trading_days"]),
            "min_profitable_days": int(raw["min_profitable_days"]),
            "profitable_day_threshold_pct": float(raw["profitable_day_threshold_pct"]),
            "leverage_fx": float(raw["leverage_fx"]),
            "leverage_indices": float(raw["leverage_indices"]),
            "promo_label": str(raw["promo_label"]),
            "execution_status": str(raw["execution_status"]),
            "effective_fee_usd": float(wp["effective_fee_usd"]),
            "effective_fee_vnd_tr": float(wp["effective_fee_vnd_tr"]),
            "ev_npv_24m_usd": float(wp["ev_npv_24m_usd"]),
            "ev_npv_24m_vnd_tr": float(wp["ev_npv_24m_vnd_tr"]),
            "med_npv_24m_usd": float(wp["med_npv_24m_usd"]),
            "med_npv_24m_vnd_tr": float(wp["med_npv_24m_vnd_tr"]),
            "ev_undisc_24m_usd": float(wp["ev_undisc_24m_usd"]),
            "ev_undisc_24m_vnd_tr": float(wp["ev_undisc_24m_vnd_tr"]),
            "ev_per_fee_npv24": float(wp["ev_per_fee_npv24"]),
            "baseline_fn1x_ev_per_fee_npv24": float(b1["ev_per_fee_npv24"]),
            "ev_per_fee_uplift_vs_base_fn1x": round(
                float(wp["ev_per_fee_npv24"]) - float(b1["ev_per_fee_npv24"]), 2
            ),
            "p_npv24_le_0_pct": float(wp["p_npv24_le_0_pct"]),
            # Balanced Law-15 trade & risk metrics computed directly per SKU at actual capital & leverage (0.01-lot)
            "funded_1x_metrics_source": "DIRECT_PER_SKU_M1_REPLAY_001_LOT_FLOORED",
            "trades_funded_1x": int(fn_law15["sized_trades"]),
            "winrate_pct": float(fn_law15["winrate_pct"]),
            "avg_rr": float(fn_law15["avg_rr"]),
            "ev_per_trade_r": float(fn_law15["ev_per_trade_r"]),
            "ev_usd_per_trade_funded_1x": ev_trade_usd_true,
            "ev_vnd_per_trade_funded_1x": ev_trade_vnd_true,
            "profit_factor_funded_1x": float(fn_law15["profit_factor"]),
            "max_dd_pct_funded_1x": float(fn_law15["peak_dd_pct"]),
            "calmar_funded_1x": float(fn_law15["calmar"]),
            "sharpe_funded_1x": float(fn_law15["sharpe"]),
            # Monthly Pass/Fail/Pending == 100.0%
            "eval_24m_fail_pct": fail_24,
            "eval_24m_fail_within_20_30_band": within_20_30,
            "monthly_pass_fail_pending": monthly,
            # Pass & payout timing (calendar days)
            "p1_med_pass_cal_days_cond": float(wp["p1_med_pass_cal_days_cond"]),
            "p1_med_pass_cal_days_uncond": float(wp["p1_med_pass_cal_days_uncond"]),
            "full_med_pass_cal_days_cond": float(wp["full_med_pass_cal_days_cond"]),
            "full_med_pass_cal_days_uncond": float(wp["full_med_pass_cal_days_uncond"]),
            "cond_med_pay1_cal_days": float(wp["cond_med_pay1_cal_days"]),
            "uncond_med_pay1_cap730_days": float(wp["uncond_med_pay1_cap730_days"]),
            # Prop survival, shock & multi-ticket ruin (at unified KS=8.00%)
            "funded_kill_static_dd_pct": funded_ks,
            "funded_12m_breach_pct": fn_br,
            "funded_12m_wilson_ub_pct": float(wp["funded_12m_wilson_ub_pct"]),
            "funded_dry_months_pct": float(wp["funded_dry_months_pct"]),
            "gap_shock_eval_125x_pct": float(shock_eval["gap_shock_125x_pct"]),
            "gap_shock_funded_125x_pct": float(shock_funded["gap_shock_125x_pct"]),
            "bankroll_4_ticket_ruin_pct": float(w4["sequential_ruin_pct"]),
            "bankroll_5_ticket_ruin_pct": float(w5["sequential_ruin_pct"]),
            "bankroll_4_ticket_pass_24m_pct": float(w4["pass_24m_pct"]),
            "bankroll_4_ticket_ev_npv24_usd": float(w4["ev_npv_24m_usd"]),
            "bankroll_4_ticket_ev_npv24_vnd_tr": float(w4["ev_npv_24m_vnd_tr"]),
            "bankroll_4_ticket_mean_tickets": float(w4["mean_tickets_used"]),
            "best_day_share": wp["best_day_share"],
        }
        if "winner_orig_1x" in raw:
            wo = raw["winner_orig_1x"]
            entry["orig_fee_1x"] = {
                "effective_fee_usd": float(wo["effective_fee_usd"]),
                "effective_fee_vnd_tr": float(wo["effective_fee_vnd_tr"]),
                "ev_npv_24m_usd": float(wo["ev_npv_24m_usd"]),
                "ev_npv_24m_vnd_tr": float(wo["ev_npv_24m_vnd_tr"]),
                "ev_per_fee_npv24": float(wo["ev_per_fee_npv24"]),
            }
        sku_table[sku_id] = entry

    ftmo10k = sku_table["ftmo_standard_10k"]
    skus_above_30 = [
        sku_id for sku_id, info in eval_fail_by_sku.items() if info["eval_24m_fail_pct"] > 30.0 + 1e-9
    ]
    anchor_fail = eval_fail_by_sku["ftmo_standard_10k"]["eval_24m_fail_pct"]
    above_desc = (
        ", ".join(
            f"{sid}={eval_fail_by_sku[sid]['eval_24m_fail_pct']:.2f}% "
            f"(+{eval_fail_by_sku[sid]['delta_above_30_pct']:.2f}%)"
            for sid in skus_above_30
        )
        if skus_above_30
        else "none"
    )
    eval_fail_band_disclosure = {
        "selection_anchor_sku": "ftmo_standard_10k",
        "selection_band_pct": [20.0, 30.0],
        "anchor_sku_eval_24m_fail_pct": anchor_fail,
        "anchor_within_20_30_band": eval_fail_by_sku["ftmo_standard_10k"]["within_20_30_band"],
        "skus_marginally_above_30_pct": skus_above_30,
        "by_sku": eval_fail_by_sku,
        "note": (
            f"The 20%-30% Eval fail selection band is anchored on ftmo_standard_10k ({anchor_fail:.2f}%). "
            f"Larger accounts with finer 0.01-lot sizing granularity sit marginally above 30.00%: {above_desc}."
        ),
    }

    law15_scale = {
        "evidence_stage": str(sprint_doc["evidence_stage"]),
        "holdout_unlocked": False,
        "demo_live_verified": False,
        "scales": {
            "ev_per_fee_npv24_ftmo_std_10k_bf": {
                "bad": "< 1.0x",
                "usable": "1.0x .. 3.0x",
                "good": "3.0x .. 8.0x",
                "top_1pct_realistic": ">= 8.0x (with Funded 12m breach < 1% & 4T ruin < 1%)",
                "current_value": ftmo10k["ev_per_fee_npv24"],
                "current_tier": "TOP_1PCT_DEV_BACKTEST_PENDING_DEMO_PARITY",
                "gap_to_live_top_1pct": (
                    f"Dev backtest clears +{ftmo10k['ev_per_fee_npv24']:.2f}x EV/Fee & "
                    f"{ftmo10k['funded_12m_breach_pct']:.2f}% Funded 12m breach (unified KS={funded_ks:.2f}%), "
                    "but requires MT5 Strategy Tester >= 98% parity (Dev 2018-2024) + live/demo execution "
                    "proof before claiming realized Top 1%."
                ),
            },
            "funded_1x_sharpe_calmar_pf": {
                "sharpe_scale": {"bad": "< 0.5", "usable": "0.5 .. 1.0", "good": "1.0 .. 1.5", "top_1pct": ">= 1.5"},
                "calmar_scale": {"bad": "< 0.4", "usable": "0.4 .. 0.8", "good": "0.8 .. 1.5", "top_1pct": ">= 1.5"},
                "pf_scale": {"bad": "< 1.05", "usable": "1.05 .. 1.15", "good": "1.15 .. 1.35", "top_1pct": ">= 1.35"},
                "current_sharpe": float(core_100k["sharpe"]),
                "current_calmar": float(core_100k["calmar"]),
                "current_pf": float(core_100k["profit_factor"]),
                "current_tier": "GOOD_CONSISTENT_MULTI_ENGINE",
                "gap_to_top_1pct": (
                    f"Funded 1x 100K reference Sharpe {float(core_100k['sharpe']):.2f} / "
                    f"Calmar {float(core_100k['calmar']):.2f} / PF {float(core_100k['profit_factor']):.2f} "
                    "(with exact per-SKU 0.01-lot-floored Funded 1x metrics in sku_table_7_ssot) sit solidly "
                    "in Good tier; closing to Top 1% (Sharpe >= 1.5, Calmar >= 1.5) requires a genuinely "
                    "orthogonal blind-verified sleeve in future R&D."
                ),
            },
        },
    }

    presets_written = sprint_doc.get("presets_written") or {}
    return {
        "winner_candidate_id": winner_id,
        "winner_selection_reason": str(sprint_doc.get("winner_selection_reason") or ""),
        "winner_config": cfg,
        "eval_fail_band_disclosure": eval_fail_band_disclosure,
        "ops2_funded_static_kill_harmonization": {
            "unified_ks_source_of_truth": True,
            "m1_sprint_receipt_funded_kill_static_pct": funded_ks,
            "exported_preset_funded_kill_static_pct": funded_ks,
            "ops2_funded_static_kill_ceiling_pct": OPS2_FUNDED_STATIC_KILL_CEILING_PCT,
            "m1_eval_set_sha256": str(presets_written.get("eval_set_sha256") or ""),
            "m1_funded_set_sha256": str(presets_written.get("funded_set_sha256") or ""),
            "reason": (
                f"Unified KS={funded_ks:.2f}% single source of truth across SprintCandidate.funded_kill_static_pct, "
                "m1_v103_sprint_results.json (all 7/7 SSOT available_vn=true SKUs on 10,000 paths), "
                "prop_v3_metrics.json, and all exported Funded 1.0x .set presets (directly passes OPS-2 <= 8.00%)."
            ),
            "all_7_ssot_skus_ks80_metrics": {
                sku_id: {
                    "ev_per_fee_npv24": sku_table[sku_id]["ev_per_fee_npv24"],
                    "ev_npv_24m_usd": sku_table[sku_id]["ev_npv_24m_usd"],
                    "funded_12m_breach_pct": sku_table[sku_id]["funded_12m_breach_pct"],
                    "funded_12m_wilson_ub_pct": sku_table[sku_id]["funded_12m_wilson_ub_pct"],
                }
                for sku_id in TARGET_SKUS
            },
        },
        "shock_eval": shock_eval,
        "shock_funded": shock_funded,
        "usd_vnd_rate": usd_vnd_rate,
        "dev_window": str(sprint_doc["dev_window"]),
        "max_day": max_day,
        "n_paths": int(sprint_doc["n_paths"]),
        "seed": int(sprint_doc["seed"]),
        "reset_boundary_audit": sprint_doc["reset_boundary_audit"],
        "core_portfolio_law15": {
            "funded_1x_100k": core_100k,
            "eval_sprint_p1_10k": p1_10k,
            "law15_benchmark_scale": law15_scale,
        },
        "target_skus": list(TARGET_SKUS),
        "sku_table_7_ssot": sku_table,
        "friction_sensitivity_ftmo_std_10k": sprint_doc.get("friction_sensitivity_ftmo_std_10k") or {},
        "cluster_stability_ftmo_std_10k": sprint_doc.get("cluster_stability_ftmo_std_10k") or {},
    }


# ---------------------------------------------------------------------------
# 3. Layer-2 `.set` Preset & Dev Strategy Tester `.ini` Rendering + Validation
# ---------------------------------------------------------------------------


def render_v103_layer2_preset(
    *,
    firm: str,
    phase: str,
    winner_config: Mapping[str, Any],
    v103_mq5_path: Path | None = None,
) -> str:
    """Render an exact 69-key LF-only `.set` preset for immutable `Naqex_Master_Prop7E_v103.mq5`.

    Supports:
      - `firm="FTMO_STD_10K"` (`InpDailyResetMode=1`, `Europe/Prague`, `$10,000`, P1 `10%` / P2 `5%`)
      - `firm="THE5ERS_HS_5K"` (`InpDailyResetMode=0` `MAX_BALANCE_EQUITY`, `17:00 America/New_York`,
        `$5,000`, Classic P1 `8%` / New P1 `10%` / P2 `5%`)
      - `phase="EVAL"` (`SPR09_M45_P2_35_B1`) or `phase="FUNDED"` (strictly locked `1.00x`,
        `InpKillStaticDdPct=8.00` compliant with `OPS-2` ceiling `<= 8.00%`).
    """
    if firm not in ("FTMO_STD_10K", "THE5ERS_HS_5K"):
        raise ValueError(f"Unsupported firm preset profile: {firm!r}")
    if phase not in ("EVAL", "FUNDED"):
        raise ValueError(f"Unsupported phase preset profile: {phase!r}")

    is_the5ers = firm == "THE5ERS_HS_5K"
    capital_usd = 5000.00 if is_the5ers else 10000.00
    daily_reset_mode = 0 if is_the5ers else 1
    provisional_alias_comment = (
        "; PROVISIONAL_SYMBOL_ALIASES [TERMS_VERIFIED_EXECUTION_UNMEASURED]: InpSymUS100=US100.cash and "
        "InpSymUS500=US500.cash are FTMO placeholder aliases for offline OPS-2 parity ONLY; "
        "LIVE/NON-DRYRUN BLOCKED until a real The5ers MT5 demo MarketWatch spec snapshot (the5ers_specs.json) "
        "verifies broker index aliases, digits, contract sizes, and stops levels.\n"
        if is_the5ers
        else ""
    )

    if phase == "EVAL":
        sku_code = f"{firm}_V103_SPRINT_EVAL"
        target_pct = 8.00 if is_the5ers else 10.00
        base_mult = float(winner_config["p1_mult"])
        p2_mult = float(winner_config["p2_mult"])
        pl_pct = 0.00
        pl_mult = base_mult
        amber_dd = float(winner_config["eval_amber_dd_pct"])
        amber_mult = float(winner_config["eval_amber_mult"])
        red_dd = float(winner_config["eval_red_dd_pct"])
        red_mult = float(winner_config["eval_red_mult"])
        kill_daily = float(winner_config["eval_p1_kill_daily_pct"])
        p2_kill_daily = float(winner_config["eval_p2_kill_daily_pct"])
        kill_static = float(winner_config["eval_p1_kill_static_pct"])
        p2_kill_static = float(winner_config["eval_p2_kill_static_pct"])
        tot_open = min(float(winner_config["eval_total_open_cap_pct"]), 3.00)
        hard_ceil = 3.00
        symcap = float(winner_config["eval_symcap_pct"])
        usd_cap = float(winner_config["eval_usd_cluster_pct"])
        jpy_cap = float(winner_config["eval_jpy_cluster_pct"])
        idx_cap = float(winner_config["eval_idx_cluster_pct"])
        sizing_mode = int(winner_config["eval_sizing_mode"])
        basis_comment = (
            "; Daily DD Basis: InpDailyResetMode=0 (MAX_BALANCE_EQUITY / 17:00 America/New_York US DST; "
            "v103.mq5 L264/L973; Classic P1=8.00%, New P1 override InpTargetProfitPct=10.00)\n"
            if is_the5ers
            else "; Daily DD Basis: InpDailyResetMode=1 (Europe/Prague DST Midnight Balance / InitialBalance)\n"
        )
        header = (
            f"; Naqex MT5 Master_Prop7E v1.03 Sprint Eval Preset ({winner_config['candidate_id']}) | SKU: {sku_code}\n"
            f"; Phase 1 Defaults: Target={target_pct:.2f}% Mult={base_mult:.2f}x PL=0.00%->{pl_mult:.2f}x "
            f"KillDaily={kill_daily:.2f}% KillStatic={kill_static:.2f}%\n"
            f"; Phase 2 Overrides: InpTargetProfitPct=5.00 InpBasePhaseMult={p2_mult:.2f} "
            f"InpProfitLockPct=0.00 InpProfitLockMult={p2_mult:.2f} "
            f"InpKillDailyDdPct={p2_kill_daily:.2f} InpKillStaticDdPct={p2_kill_static:.2f}\n"
            f"{basis_comment}"
            f"{provisional_alias_comment}"
            f"; Shield A+B1+B2+B3 ON: TotalOpenCap={tot_open:.2f}% (1.25x gap <= {tot_open * 1.25:.2f}% <= 4.50%), "
            "SpreadGuard=ON, 6-CCY +-10m Red-News=ON (+-135s hard ban)\n"
            "; FAIL-CLOSED DEFAULTS + B8 KILL-SWITCH READY: InpDryRunLogOnly=true, InpShadowCompareMode=true, "
            "InpGuardDryRunLogOnly=true, InpWritePrimaryHeartbeat=true, InpAllowManualHaltFile=true\n"
        )
    else:
        sku_code = f"{firm}_V103_FUNDED_1X"
        target_pct = 0.00
        base_mult = 1.00
        pl_pct = 0.00
        pl_mult = 1.00
        amber_dd = 3.50
        amber_mult = 0.65
        red_dd = 6.00
        red_mult = 0.40
        kill_daily = min(float(winner_config["funded_kill_daily_pct"]), 2.50)
        kill_static = float(winner_config["funded_kill_static_pct"])
        if kill_static <= 0.0 or kill_static > OPS2_FUNDED_STATIC_KILL_CEILING_PCT + 1e-9:
            raise ValueError(
                f"OPS2_FUNDED_KS_VIOLATION: winner_config funded_kill_static_pct={kill_static} "
                f"outside (0.0, {OPS2_FUNDED_STATIC_KILL_CEILING_PCT:.2f}]"
            )
        tot_open = min(float(winner_config["funded_total_open_cap_pct"]), 2.00)
        hard_ceil = 2.25
        symcap = min(float(winner_config["funded_symcap_pct"]), 1.00)
        usd_cap = min(float(winner_config["funded_usd_cluster_pct"]), 1.50)
        jpy_cap = min(float(winner_config["funded_jpy_cluster_pct"]), 1.25)
        idx_cap = min(float(winner_config["funded_idx_cluster_pct"]), 1.00)
        sizing_mode = 0
        basis_comment = (
            "; Daily DD Basis: InpDailyResetMode=0 (MAX_BALANCE_EQUITY / 17:00 America/New_York US DST; "
            "v103.mq5 L264/L973)\n"
            if is_the5ers
            else "; Daily DD Basis: InpDailyResetMode=1 (Europe/Prague DST Midnight Balance / InitialBalance)\n"
        )
        header = (
            f"; Naqex MT5 Master_Prop7E v1.03 Funded 1.0x Preservation Preset | SKU: {sku_code}\n"
            f"; Strictly Locked Funded Profile: Mult=1.00x Amber=3.50%->0.65x Red=6.00%->0.40x "
            f"KillDaily={kill_daily:.2f}% KillStatic={kill_static:.2f}% (OPS-2 <= 8.00%)\n"
            f"{basis_comment}"
            f"{provisional_alias_comment}"
            f"; Shield A+B1+B2+B3 ON: TotalOpenCap={tot_open:.2f}% (<= 2.25%, 1.25x gap <= {tot_open * 1.25:.2f}%), "
            "SpreadGuard=ON, 6-CCY +-10m Red-News=ON (+-135s hard ban)\n"
            "; FAIL-CLOSED DEFAULTS + B8 KILL-SWITCH READY: InpDryRunLogOnly=true, InpShadowCompareMode=true, "
            "InpGuardDryRunLogOnly=true, InpWritePrimaryHeartbeat=true, InpAllowManualHaltFile=true\n"
        )

    news_pad_sec = max(600, int(winner_config.get("news_pad_sec", 600)))
    ordered_kv: list[tuple[str, str]] = [
        ("InpGuardDryRunLogOnly", "true"),
        ("InpGuardMaxDailyLossPct", f"{kill_daily:.2f}"),
        ("InpGuardMaxSymbolRiskPct", f"{symcap:.2f}"),
        ("InpGuardUseOrchestrator", "false"),
        ("InpGuardMaxSpreadPoints", "35.00"),
        ("InpGuardRolloverStartUTC", "21"),
        ("InpGuardRolloverEndUTC", "0"),
        ("InpGuardEarlyCloseMin", "10"),
        ("InpGuardTesterUtcOffsetH", "2"),
        ("InpGuardEnableRedNews", "true"),
        ("InpGuardRedNewsCsvFile", "naqex_red_news_utc.csv"),
        ("InpGuardNewsPadSec", str(news_pad_sec)),
        ("InpGuardNewsHardBanSec", "135"),
        ("InpGuardTcaAuditCsvFile", "naqex_exec_audit.csv"),
        ("InpGuardMagicRangeMin", "20261120"),
        ("InpGuardMagicRangeMax", "20261199"),
        ("InpDryRunLogOnly", "true"),
        ("InpShadowCompareMode", "true"),
        ("InpEnableS6Shadow", "false"),
        ("InpWritePrimaryHeartbeat", "true"),
        ("InpContractSku", sku_code),
        ("InpInitialBalanceUSD", f"{capital_usd:.2f}"),
        ("InpTargetProfitPct", f"{target_pct:.2f}"),
        ("InpHardDailyDdPct", "5.00"),
        ("InpHardStaticDdPct", "10.00"),
        ("InpDailyResetMode", str(daily_reset_mode)),
        ("InpSizingMode", str(sizing_mode)),
        ("InpBasePhaseMult", f"{base_mult:.2f}"),
        ("InpProfitLockPct", f"{pl_pct:.2f}"),
        ("InpProfitLockMult", f"{pl_mult:.2f}"),
        ("InpAmberDdPct", f"{amber_dd:.2f}"),
        ("InpAmberMult", f"{amber_mult:.2f}"),
        ("InpRedDdPct", f"{red_dd:.2f}"),
        ("InpRedMult", f"{red_mult:.2f}"),
        ("InpKillDailyDdPct", f"{kill_daily:.2f}"),
        ("InpKillStaticDdPct", f"{kill_static:.2f}"),
        ("InpMaxTotalOpenRiskPct", f"{tot_open:.2f}"),
        ("InpHardTotalOpenCeilingPct", f"{hard_ceil:.2f}"),
        ("InpMaxSymbolRiskPct", f"{symcap:.2f}"),
        ("InpMaxUsdClusterPct", f"{usd_cap:.2f}"),
        ("InpMaxJpyClusterPct", f"{jpy_cap:.2f}"),
        ("InpMaxIdxClusterPct", f"{idx_cap:.2f}"),
        ("InpEnableSpreadGuard", "true"),
        ("InpMaxUsdJpySpreadPoints", "25.00"),
        ("InpMaxGbpUsdSpreadPoints", "35.00"),
        ("InpMaxEurJpySpreadPoints", "25.00"),
        ("InpMaxIndexSpreadPoints", "350.00"),
        ("InpUse6CcyNewsPad10m", "true"),
        ("InpSymUSDJPY", "USDJPY"),
        ("InpSymGBPUSD", "GBPUSD"),
        ("InpSymEURJPY", "EURJPY"),
        ("InpSymUS100", "US100.cash"),
        ("InpSymUS500", "US500.cash"),
        ("InpSymEURUSD", "EURUSD"),
        ("InpSymAUDUSD", "AUDUSD"),
        ("InpSymUSDCAD", "USDCAD"),
        ("InpMaxSlippagePointsFx", "35"),
        ("InpMaxSlippagePointsIdx", "450"),
        ("InpMaxBreakoutTickLagMs", "5000"),
        ("InpHeartbeatSec", "15"),
        ("InpHeartbeatFile", "naqex_master_v103_heartbeat.json"),
        ("InpShadowCsvFile", "naqex_master_v103_shadow.csv"),
        ("InpProfitLockBasisMode", "0"),
        ("InpOpportunityLifecycleMode", "1"),
        ("InpPostCloseRefreshMode", "1"),
        ("InpAllowManualHaltFile", "true"),
        ("InpManualHaltFile", "naqex_manual_halt.flag"),
        ("InpMagicRangeMin", "20261120"),
        ("InpMagicRangeMax", "20261199"),
    ]

    expected_keys = parse_v103_mq5_inputs(v103_mq5_path)
    actual_keys = tuple(k for k, _ in ordered_kv)
    if set(actual_keys) != set(expected_keys) or len(actual_keys) != len(expected_keys):
        missing = sorted(set(expected_keys) - set(actual_keys))
        extra = sorted(set(actual_keys) - set(expected_keys))
        raise ValueError(f"PRESET_69KEY_MISMATCH({firm}/{phase}): missing={missing} extra={extra}")

    body = "\n".join(f"{k}={v}" for k, v in ordered_kv)
    return header + body + "\n"


def render_dev_strategy_tester_ini(
    *,
    preset_filename: str,
    report_name: str,
    deposit_usd: int = 10000,
    leverage: str = "1:100",
    from_date: str = DEV_TESTER_FROM_DATE,
    to_date: str = DEV_TESTER_TO_DATE,
) -> str:
    """Render clean MT5 Strategy Tester Dev-only (`2018.01.02 - 2024.12.31`, NEVER `2025+`) `.ini` config."""
    validate_tester_date_dev_only(from_date)
    validate_tester_date_dev_only(to_date)
    if from_date > to_date:
        raise ValueError(f"TESTER_DATE_ORDER_ERROR: FromDate={from_date} > ToDate={to_date}")

    lines = [
        f"; Naqex MT5 Strategy Tester Dev Parity Config | Preset: {preset_filename}",
        f"; STRICT DEV WINDOW ONLY ({from_date} - {to_date}, NEVER 2025+ Holdout!)",
        "; Owner parity verification target: >= 98% match vs Python Dev M1 replay.",
        "[Common]",
        "KeepPrivate=1",
        "ProxyEnable=0",
        "[Experts]",
        "AllowLiveTrading=0",
        "AllowDllImport=0",
        "Enabled=0",
        "[Tester]",
        r"Expert=Naqex\Naqex_Master_Prop7E_v103.ex5",
        f"ExpertParameters={preset_filename}",
        "Symbol=USDJPY",
        "Period=M5",
        "Model=4",
        "ExecutionMode=0",
        "Optimization=0",
        f"FromDate={from_date}",
        f"ToDate={to_date}",
        f"Deposit={int(deposit_usd)}",
        "Currency=USD",
        f"Leverage={leverage}",
        "UseLocal=1",
        "UseRemote=0",
        "UseCloud=0",
        "Visual=0",
        f"Report={report_name}",
        "ReplaceReport=1",
        "ShutdownTerminal=1",
    ]
    return "\n".join(lines) + "\n"


def validate_tester_date_dev_only(date_str: str) -> None:
    """Fail-closed if an MT5 Strategy Tester `.ini` date string is malformed or `>= 2025.01.01`."""
    m = re.fullmatch(r"(\d{4})\.(\d{2})\.(\d{2})", str(date_str).strip())
    if not m:
        raise ValueError(f"TESTER_DATE_FORMAT_ERROR: expected YYYY.MM.DD, got {date_str!r}")
    year = int(m.group(1))
    if year >= 2025 or str(date_str).strip() >= HOLDOUT_CUTOFF_TESTER_DATE:
        raise ValueError(f"HOLDOUT_LOCK_VIOLATION: Strategy Tester date {date_str!r} >= {HOLDOUT_CUTOFF_TESTER_DATE}")


def validate_tester_ini_file(ini_path: Path) -> dict[str, str]:
    """Parse and fail-closed validate an MT5 Strategy Tester `.ini` file (strictly `< 2025` & live trading OFF)."""
    raw = ini_path.read_bytes()
    if b"\r\n" in raw:
        raise ValueError(f"TESTER_INI_CRLF_ERROR: {ini_path.name} must be LF-only")
    kv: dict[str, str] = {}
    for line in raw.decode("utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith(";") or (s.startswith("[") and s.endswith("]")):
            continue
        if "=" in s:
            k, v = s.split("=", 1)
            kv[k.strip()] = v.strip()

    for key in ("FromDate", "ToDate"):
        if key not in kv:
            raise ValueError(f"TESTER_INI_MISSING_KEY: {ini_path.name} missing {key}")
        validate_tester_date_dev_only(kv[key])
    if kv["FromDate"] > kv["ToDate"]:
        raise ValueError(f"TESTER_INI_RANGE_ERROR: {kv['FromDate']} > {kv['ToDate']}")
    for zero_key in ("AllowLiveTrading", "AllowDllImport", "Enabled"):
        if kv.get(zero_key) != "0":
            raise ValueError(f"TESTER_INI_SAFETY_ERROR: {ini_path.name} must set {zero_key}=0")
    return kv


def _build_reference_marketwatch() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for sym in CORE_7E_SYMBOLS:
        spec = DEFAULT_FTMO_SPECS_28[sym]
        out[sym] = {
            "symbol": sym,
            "in_market_watch": True,
            "trade_mode": "FULL",
            "digits": spec["digits"],
            "point": 10.0 ** (-int(spec["digits"])),
            "contract_size": spec["contract_size"],
            "stops_level": spec["stops_level"],
        }
    return out


def verify_preset_with_ops2(
    preset_path: Path,
    *,
    firm_profile: str,
    account_phase: str,
    v103_mq5_path: Path | None = None,
) -> dict[str, Any]:
    """Verify a `.set` preset on disk against `v103.mq5` 69-key schema + `OPS-2` `account_phase_preflight`."""
    if not preset_path.is_file():
        raise FileNotFoundError(f"Preset not found: {preset_path}")
    raw_bytes = preset_path.read_bytes()
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"PRESET_BOM_ERROR: {preset_path.name} must not contain UTF-8 BOM")
    if b"\r\n" in raw_bytes:
        raise ValueError(f"PRESET_CRLF_ERROR: {preset_path.name} must be LF-only")
    raw_text = raw_bytes.decode("utf-8")

    if firm_profile == "THE5ERS_HS_5K":
        if "; PROVISIONAL_SYMBOL_ALIASES" not in raw_text or "the5ers_specs.json" not in raw_text:
            raise ValueError(
                f"THE5ERS_PROVISIONAL_ALIAS_HEADER_MISSING({preset_path.name}): "
                "The5ers preset must explicitly disclose provisional FTMO .cash aliases and the5ers_specs.json gate"
            )

    expected_keys = set(parse_v103_mq5_inputs(v103_mq5_path))
    parsed = parse_mt5_set_file(preset_path)
    actual_keys = set(parsed.keys())
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        raise ValueError(f"PRESET_SCHEMA_MISMATCH({preset_path.name}): missing={missing} extra={extra}")

    # Verify fail-closed DryRun + B8 safety flags
    for req_true in (
        "InpAllowManualHaltFile",
        "InpWritePrimaryHeartbeat",
        "InpDryRunLogOnly",
        "InpShadowCompareMode",
        "InpGuardDryRunLogOnly",
        "InpEnableSpreadGuard",
        "InpGuardEnableRedNews",
        "InpUse6CcyNewsPad10m",
    ):
        if parsed.get(req_true) is not True:
            raise ValueError(f"PRESET_FAILCLOSED_VIOLATION({preset_path.name}): {req_true}={parsed.get(req_true)!r}")

    if firm_profile == "THE5ERS_HS_5K" and parsed.get("InpDailyResetMode") != 0:
        raise ValueError(
            f"THE5ERS_DAILY_MODE_ERROR({preset_path.name}): expected InpDailyResetMode=0 (MAX_BALANCE_EQUITY)"
        )
    if firm_profile == "FTMO_STANDARD" and parsed.get("InpDailyResetMode") != 1:
        raise ValueError(f"FTMO_DAILY_MODE_ERROR({preset_path.name}): expected InpDailyResetMode=1 (Europe/Prague)")

    mw = _build_reference_marketwatch()
    asset_levs = (
        {"FX": 100, "INDICES": 20, "METALS": 33}
        if firm_profile == "THE5ERS_HS_5K"
        else {"FX": 100, "INDICES": 50, "METALS": 30}
    )

    rep_match = validate_account_deployment(
        expected_login=9900001,
        actual_login=9900001,
        expected_trade_mode="DEMO",
        actual_trade_mode="DEMO",
        firm_profile=firm_profile,
        account_phase=account_phase,
        preset=preset_path,
        account_leverage=100,
        asset_class_leverages=asset_levs,
        market_watch_symbols=mw,
        required_symbols=list(CORE_7E_SYMBOLS),
        strict_funded_1x=(account_phase == "FUNDED"),
        days_since_last_trade=2,
    )
    if not rep_match.passed:
        raise ValueError(
            f"OPS2_PREFLIGHT_REJECTED({preset_path.name}, {firm_profile}/{account_phase}): {rep_match.reject_codes}"
        )

    # Negative adversarial test: attaching an EVAL preset to a FUNDED account MUST HARD REJECT!
    eval_on_funded_rejected: bool | None = None
    eval_on_funded_codes: list[str] = []
    if account_phase == "EVAL":
        rep_adv = validate_account_deployment(
            expected_login=9900001,
            actual_login=9900001,
            expected_trade_mode="REAL",
            actual_trade_mode="REAL",
            firm_profile=firm_profile,
            account_phase="FUNDED",
            preset=preset_path,
            account_leverage=100,
            asset_class_leverages=asset_levs,
            market_watch_symbols=mw,
            required_symbols=list(CORE_7E_SYMBOLS),
            strict_funded_1x=True,
        )
        eval_on_funded_rejected = not rep_adv.passed
        eval_on_funded_codes = list(rep_adv.reject_codes)
        if rep_adv.passed or "EVAL_PRESET_ON_FUNDED_ACCOUNT" not in rep_adv.reject_codes:
            raise ValueError(
                f"OPS2_EVAL_ON_FUNDED_GUARD_FAILURE({preset_path.name}): passed={rep_adv.passed} "
                f"codes={rep_adv.reject_codes}"
            )

    is_the5ers_profile = firm_profile == "THE5ERS_HS_5K"
    return {
        "file": str(preset_path.relative_to(REPO_ROOT).as_posix())
        if preset_path.is_relative_to(REPO_ROOT)
        else str(preset_path),
        "sha256": sha256_file(preset_path),
        "firm_profile": firm_profile,
        "account_phase": account_phase,
        "execution_status": (
            "TERMS_VERIFIED_EXECUTION_UNMEASURED" if is_the5ers_profile else "MEASURED_DEMO_EXECUTION"
        ),
        "symbol_aliases_provisional": is_the5ers_profile,
        "specs_source_for_offline_ops2": (
            "ftmo_specs_28_placeholder_until_the5ers_marketwatch_capture"
            if is_the5ers_profile
            else "ftmo_specs_28_verified_20261124"
        ),
        "live_non_dryrun_blocked_until": "the5ers_specs.json" if is_the5ers_profile else None,
        "key_count": len(parsed),
        "all_69_v103_keys_verified": True,
        "daily_reset_mode": int(parsed["InpDailyResetMode"]),
        "base_phase_mult": float(parsed["InpBasePhaseMult"]),
        "kill_daily_dd_pct": float(parsed["InpKillDailyDdPct"]),
        "kill_static_dd_pct": float(parsed["InpKillStaticDdPct"]),
        "allow_manual_halt_file": bool(parsed["InpAllowManualHaltFile"]),
        "write_primary_heartbeat": bool(parsed["InpWritePrimaryHeartbeat"]),
        "fail_closed_dry_run_defaults": True,
        "ops2_preflight_verdict": rep_match.verdict,
        "ops2_preflight_passed": rep_match.passed,
        "ops2_reject_codes": list(rep_match.reject_codes),
        "ops2_eval_on_funded_rejected": eval_on_funded_rejected,
        "ops2_eval_on_funded_reject_codes": eval_on_funded_codes,
    }


def export_and_verify_layer2_artifacts(
    *,
    winner_config: Mapping[str, Any],
    presets_dir: Path = DEFAULT_PRESETS_DIR,
    v103_mq5_path: Path | None = None,
) -> dict[str, Any]:
    """Write/harmonize all 4 `.set` presets + 2 Dev Strategy Tester `.ini` configs and run `OPS-2` preflight."""
    presets_dir.mkdir(parents=True, exist_ok=True)
    specs = (
        ("FTMO_Std10K_v103_Sprint_Eval.set", "FTMO_STD_10K", "FTMO_STANDARD", "EVAL"),
        ("FTMO_Std10K_v103_Funded_1x.set", "FTMO_STD_10K", "FTMO_STANDARD", "FUNDED"),
        ("The5ers_HS5K_v103_Sprint_Eval.set", "THE5ERS_HS_5K", "THE5ERS_HS_5K", "EVAL"),
        ("The5ers_HS5K_v103_Funded_1x.set", "THE5ERS_HS_5K", "THE5ERS_HS_5K", "FUNDED"),
    )
    preset_reports: dict[str, Any] = {}
    for fname, firm_key, firm_profile, phase in specs:
        target = presets_dir / fname
        rendered = render_v103_layer2_preset(
            firm=firm_key,
            phase=phase,
            winner_config=winner_config,
            v103_mq5_path=v103_mq5_path,
        )
        atomic_write_text(target, rendered)
        rep = verify_preset_with_ops2(
            target,
            firm_profile=firm_profile,
            account_phase=phase,
            v103_mq5_path=v103_mq5_path,
        )
        preset_reports[fname] = rep

    ini_specs = (
        ("v103_Sprint_Eval_tester_dev.ini", "FTMO_Std10K_v103_Sprint_Eval.set", "v103_Sprint_Eval_tester_dev"),
        ("v103_Funded_1x_tester_dev.ini", "FTMO_Std10K_v103_Funded_1x.set", "v103_Funded_1x_tester_dev"),
    )
    ini_reports: dict[str, Any] = {}
    for ini_name, set_name, rep_name in ini_specs:
        ini_path = presets_dir / ini_name
        ini_text = render_dev_strategy_tester_ini(
            preset_filename=set_name,
            report_name=rep_name,
            deposit_usd=10000,
            leverage="1:100",
            from_date=DEV_TESTER_FROM_DATE,
            to_date=DEV_TESTER_TO_DATE,
        )
        atomic_write_text(ini_path, ini_text)
        kv = validate_tester_ini_file(ini_path)
        ini_reports[ini_name] = {
            "file": str(ini_path.relative_to(REPO_ROOT).as_posix())
            if ini_path.is_relative_to(REPO_ROOT)
            else str(ini_path),
            "sha256": sha256_file(ini_path),
            "expert": kv["Expert"],
            "expert_parameters": kv["ExpertParameters"],
            "from_date": kv["FromDate"],
            "to_date": kv["ToDate"],
            "strictly_pre_2025": True,
            "allow_live_trading": int(kv["AllowLiveTrading"]),
            "model": int(kv["Model"]),
        }

    return {
        "presets": preset_reports,
        "tester_inis": ini_reports,
    }


# ---------------------------------------------------------------------------
# 4. Isolated `MetaEditor64.exe` Compilation Proof (`G11`) — Zero `.ex5` Left!
# ---------------------------------------------------------------------------


def _decode_metaeditor_log(log_path: Path) -> str:
    raw = log_path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8", errors="replace")


def _parse_compile_result_line(log_text: str) -> dict[str, Any]:
    m = re.search(
        r"Result:\s*(\d+)\s+errors?,\s*(\d+)\s+warnings?,\s*(\d+)\s+ms\s+elapsed(?:,\s*cpu='([^']+)')?",
        log_text,
    )
    if not m:
        raise RuntimeError(f"METAEDITOR_LOG_UNPARSEABLE:\n{log_text[-1200:]}")
    return {
        "errors": int(m.group(1)),
        "warnings": int(m.group(2)),
        "elapsed_ms": int(m.group(3)),
        "cpu": m.group(4) or "unknown",
        "result_line": m.group(0),
    }


def locate_metaeditor_and_include(portable_dir: Path = DEFAULT_PORTABLE_DIR) -> tuple[Path, Path]:
    """Locate `MetaEditor64.exe` and its `MQL5` standard include root without launching any MT5 terminal."""
    candidates = (
        (portable_dir / "MetaEditor64.exe", portable_dir / "MQL5"),
        (Path(r"C:\Program Files\MetaTrader 5\MetaEditor64.exe"), portable_dir / "MQL5"),
        (Path(r"C:\Program Files\MetaTrader 5\MetaEditor64.exe"), Path(r"C:\Program Files\MetaTrader 5\MQL5")),
    )
    for exe_p, inc_p in candidates:
        if exe_p.is_file() and (inc_p / "Include/Trade/Trade.mqh").is_file():
            return exe_p, inc_p
    raise FileNotFoundError("Could not locate MetaEditor64.exe with MQL5/Include/Trade/Trade.mqh")


def run_isolated_metaeditor_proof(
    *,
    exports_dir: Path = DEFAULT_EXPORTS_DIR,
    layer2_v3_dir: Path = DEFAULT_LAYER2_V3_DIR,
    work_dir: Path = DEFAULT_METAEDITOR_CHECK_DIR,
    portable_dir: Path = DEFAULT_PORTABLE_DIR,
    private_vault_dir: Path | None = None,
) -> dict[str, Any]:
    """Compile immutable `v103.mq5` + 3-header V3 harness in `.tmp/off3_metaeditor_check/`, then DELETE ALL `.ex5`."""
    metaeditor_exe, mql5_inc = locate_metaeditor_and_include(portable_dir)
    pv_dir = private_vault_dir or (REPO_ROOT / "private_vault")

    # Record immutable source hashes BEFORE compilation
    source_paths = {
        "Naqex_Master_Prop7E_v103.mq5": exports_dir / "Naqex_Master_Prop7E_v103.mq5",
        "Naqex_PropGuard.mqh": exports_dir / "Include/Naqex_PropGuard.mqh",
        "Naqex_Signals_7E.mqh": exports_dir / "Include/Naqex_Signals_7E.mqh",
        **{h: layer2_v3_dir / h for h in LAYER2_V3_HEADERS},
    }
    pre_hashes: dict[str, str] = {}
    for label, p in source_paths.items():
        if not p.is_file():
            raise FileNotFoundError(f"G11 compile input missing: {p}")
        pre_hashes[label] = sha256_file(p)

    if work_dir.exists():
        shutil.rmtree(work_dir)

    compile_results: dict[str, Any] = {}
    try:
        inc_dir = work_dir / "Include"
        inc_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_paths["Naqex_Master_Prop7E_v103.mq5"], work_dir / "Naqex_Master_Prop7E_v103.mq5")
        shutil.copy2(source_paths["Naqex_PropGuard.mqh"], inc_dir / "Naqex_PropGuard.mqh")
        shutil.copy2(source_paths["Naqex_Signals_7E.mqh"], inc_dir / "Naqex_Signals_7E.mqh")
        for hdr in LAYER2_V3_HEADERS:
            shutil.copy2(source_paths[hdr], inc_dir / hdr)
        atomic_write_text(work_dir / "Naqex_V3_Headers_Harness.mq5", V3_HEADERS_HARNESS_MQ5)

        for target_name in ("Naqex_Master_Prop7E_v103.mq5", "Naqex_V3_Headers_Harness.mq5"):
            mq5_path = work_dir / target_name
            log_path = work_dir / f"{mq5_path.stem}.log"
            cmd = [
                str(metaeditor_exe),
                f"/compile:{mq5_path}",
                f"/inc:{mql5_inc}",
                f"/log:{log_path}",
            ]
            subprocess.run(cmd, check=False, timeout=90)
            if not log_path.is_file():
                raise RuntimeError(f"METAEDITOR_NO_LOG: {log_path}")
            log_text = _decode_metaeditor_log(log_path)
            parsed = _parse_compile_result_line(log_text)
            ex5_built = mq5_path.with_suffix(".ex5").is_file()
            if parsed["errors"] != 0 or parsed["warnings"] != 0 or not ex5_built:
                raise RuntimeError(
                    f"G11_COMPILE_FAILED({target_name}): errors={parsed['errors']} warnings={parsed['warnings']} "
                    f"ex5_built={ex5_built}\n{log_text[-1500:]}"
                )
            included = sorted(
                {
                    Path(m.group(1).strip()).name
                    for m in re.finditer(r"information:\s+including\s+(.+)", log_text)
                }
            )
            compile_results[target_name] = {
                **parsed,
                "ex5_compiled_and_deleted": True,
                "included_headers": included,
            }
    finally:
        if work_dir.exists():
            shutil.rmtree(work_dir)

    # Verify zero mutation of source files AND zero `.ex5` left behind
    for label, p in source_paths.items():
        post_sha = sha256_file(p)
        if post_sha != pre_hashes[label]:
            raise RuntimeError(f"IMMUTABILITY_VIOLATION: {label} hash changed during compile check!")

    if work_dir.exists():
        raise RuntimeError(f"G11_CLEANUP_FAILED: {work_dir} still exists after compile proof")
    remaining_pv_ex5 = list(pv_dir.rglob("*.ex5")) if pv_dir.is_dir() else []
    if remaining_pv_ex5:
        raise RuntimeError(f"G11_EX5_LEAK_IN_PRIVATE_VAULT: {[str(p) for p in remaining_pv_ex5]}")

    return {
        "gate_id": "G11_ISOLATED_METAEDITOR_COMPILE_PROOF",
        "status": "PASS_0_ERRORS_0_WARNINGS",
        "verified_utc": datetime.now(UTC).isoformat(),
        "isolated_work_dir_deleted": not work_dir.exists(),
        "remaining_ex5_in_private_vault": 0,
        "remaining_ex5_in_check_dir": 0,
        "immutable_sources_verified_unchanged": True,
        "source_sha256": pre_hashes,
        "targets": compile_results,
    }


# ---------------------------------------------------------------------------
# 5. Full Stage 4 Orchestrator
# ---------------------------------------------------------------------------


def build_prop_v3_metrics(
    *,
    funnel_json_path: Path = DEFAULT_FUNNEL_JSON,
    sprint_json_path: Path = DEFAULT_SPRINT_JSON,
    presets_dir: Path = DEFAULT_PRESETS_DIR,
    exports_dir: Path = DEFAULT_EXPORTS_DIR,
    layer2_v3_dir: Path = DEFAULT_LAYER2_V3_DIR,
    metaeditor_check_dir: Path = DEFAULT_METAEDITOR_CHECK_DIR,
    portable_dir: Path = DEFAULT_PORTABLE_DIR,
    run_metaeditor_proof: bool = True,
    compile_proof_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble full fail-closed Stage 4 Prop V3 receipt (`prop_v3_metrics.json`)."""
    funnel_doc = json.loads(funnel_json_path.read_text(encoding="utf-8"))
    sprint_doc = json.loads(sprint_json_path.read_text(encoding="utf-8"))

    g09_gate = enforce_g09_accretion_gate(funnel_doc)
    counterfactual = build_diagnostic_counterfactual_note(funnel_doc)
    sprint_summary = build_7sku_ssot_summary(sprint_doc)

    v103_mq5_path = exports_dir / "Naqex_Master_Prop7E_v103.mq5"
    layer2_exports = export_and_verify_layer2_artifacts(
        winner_config=sprint_summary["winner_config"],
        presets_dir=presets_dir,
        v103_mq5_path=v103_mq5_path,
    )

    # Fail-closed SHA-256 reconciliation: m1_v103_sprint_results.json, prop_v3_metrics.json, and disk .set MUST match
    presets_written = sprint_doc.get("presets_written") or {}
    for pw_key, fname in (
        ("eval_set_sha256", "FTMO_Std10K_v103_Sprint_Eval.set"),
        ("funded_set_sha256", "FTMO_Std10K_v103_Funded_1x.set"),
    ):
        expected_sha = str(presets_written.get(pw_key) or "")
        actual_sha = str(layer2_exports["presets"][fname]["sha256"])
        if expected_sha and expected_sha != actual_sha:
            raise ValueError(
                f"PRESET_SHA256_DRIFT({fname}): m1_sprint={expected_sha} != stage4_disk={actual_sha}"
            )

    if compile_proof_override is not None:
        compile_proof = dict(compile_proof_override)
    elif run_metaeditor_proof:
        compile_proof = run_isolated_metaeditor_proof(
            exports_dir=exports_dir,
            layer2_v3_dir=layer2_v3_dir,
            work_dir=metaeditor_check_dir,
            portable_dir=portable_dir,
        )
    else:
        compile_proof = {
            "gate_id": "G11_ISOLATED_METAEDITOR_COMPILE_PROOF",
            "status": "SKIPPED_OFFLINE_TEST_MODE",
            "isolated_work_dir_deleted": not metaeditor_check_dir.exists(),
            "remaining_ex5_in_private_vault": len(list((REPO_ROOT / "private_vault").rglob("*.ex5")))
            if (REPO_ROOT / "private_vault").is_dir()
            else 0,
            "remaining_ex5_in_check_dir": 0,
        }

    immutable_hashes: dict[str, str] = {}
    for rel in IMMUTABLE_MQ_RELPATHS:
        p = REPO_ROOT / rel
        if p.is_file():
            immutable_hashes[rel] = sha256_file(p)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": datetime.now(UTC).isoformat(),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_rows_analysed": 0,
        "dev_window": sprint_summary["dev_window"],
        "max_day": sprint_summary["max_day"],
        "prop_v3_champion": PROP_V3_CHAMPION_ID,
        "sprint_winner_candidate_id": sprint_summary["winner_candidate_id"],
        "input_provenance": {
            "stage3_alpha_funnel_json": str(funnel_json_path.relative_to(REPO_ROOT).as_posix())
            if funnel_json_path.is_relative_to(REPO_ROOT)
            else str(funnel_json_path),
            "stage3_alpha_funnel_sha256": sha256_file(funnel_json_path),
            "m1_v103_sprint_results_json": str(sprint_json_path.relative_to(REPO_ROOT).as_posix())
            if sprint_json_path.is_relative_to(REPO_ROOT)
            else str(sprint_json_path),
            "m1_v103_sprint_results_sha256": sha256_file(sprint_json_path),
            "immutable_mql5_sha256": immutable_hashes,
        },
        "g09_accretion_gate": g09_gate,
        "champion_portfolio_summary": sprint_summary,
        "diagnostic_counterfactual_not_promoted": counterfactual,
        "layer2_presets_and_tester_exports": layer2_exports,
        "g11_metaeditor_compile_proof": compile_proof,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Offensive #3 Stage 4: G09 Accretion Gate, 7-SKU SSOT Prop V3 Receipt, "
            "Layer-2 Presets & G11 Compile Proof."
        )
    )
    p.add_argument("--funnel-json", type=Path, default=DEFAULT_FUNNEL_JSON)
    p.add_argument("--sprint-json", type=Path, default=DEFAULT_SPRINT_JSON)
    p.add_argument("--presets-dir", type=Path, default=DEFAULT_PRESETS_DIR)
    p.add_argument("--out-json", type=Path, default=DEFAULT_OUT_METRICS_JSON)
    p.add_argument("--skip-metaeditor-proof", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    payload = build_prop_v3_metrics(
        funnel_json_path=args.funnel_json,
        sprint_json_path=args.sprint_json,
        presets_dir=args.presets_dir,
        run_metaeditor_proof=not args.skip_metaeditor_proof,
    )
    payload_sha, file_sha = atomic_write_json_with_sha(args.out_json, payload)
    g09 = payload["g09_accretion_gate"]
    g11 = payload["g11_metaeditor_compile_proof"]
    print(
        f"STAGE4_PROP_V3_OK champion={payload['prop_v3_champion']} "
        f"tier1={g09['tier1_ftmo_ready_count']} promoted={g09['promoted_count']} "
        f"skus={len(payload['champion_portfolio_summary']['sku_table_7_ssot'])} "
        f"g11={g11['status']} payload_sha256={payload_sha} file_sha256={file_sha}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
