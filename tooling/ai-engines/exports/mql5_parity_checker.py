"""Automated MQL5 <-> Python Parity & Safety Checker for the Naqex 8-EA + Orchestrator Production Suite.

Cross-checks all 8 exported white-box `.mq5` EAs, `Naqex_AccountOrchestrator.mq5`, and
`Include/Naqex_PropGuard.mqh` against:
  1. `planning/research/PORTFOLIO-REGISTRY.json` (magic numbers, assets, base risk %, params)
  2. Frozen Python research engines (`pass5`, `pass17`, `pass22`, `pass26`, `pass27`, `pass28`)
  3. Fail-closed Prop safety invariants (`InpDryRunLogOnly = true`, `audit_open_source_mq5` == 0 red flags,
     `SYMCAP_100`, red-news CSV wiring, causal prior-day D1 shift=1 ATR/range, no lookahead)
  4. Optional compiled `.ex5` + MetaEditor64 compile logs under `.runtime/mt5-compiled-ex5/`

Strictly read-only (zero broker/MT5 execution, zero OrderSend).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import inspect
import json
from pathlib import Path
import re
import sys
from typing import Any

EXPORTS_DIR = Path(__file__).resolve().parent
AI_ENGINES_DIR = EXPORTS_DIR.parent
REPO_ROOT = AI_ENGINES_DIR.parents[1]
REGISTRY_PATH = REPO_ROOT / "planning/research/PORTFOLIO-REGISTRY.json"
DEFAULT_EX5_DIR = REPO_ROOT / ".runtime/mt5-compiled-ex5"

if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

import mq5_whitebox_exporter as mq5_exp  # noqa: E402

INPUT_RE = re.compile(
    r"^\s*(?:input|sinput)\s+([A-Za-z0-9_]+)\s+([A-Za-z0-9_]+)\s*=\s*([^;]+);",
    re.M,
)
INCLUDE_RE = re.compile(r'^\s*#include\s+[<"]([^>"]+)[>"]', re.M)

# Exact per-engine parity contract anchored to frozen Python scripts and PORTFOLIO-REGISTRY.json.
ENGINE_PARITY_CONTRACTS: dict[str, dict[str, Any]] = {
    "E1_USDJPY_TOKYO": {
        "file": "Naqex_WB_TOKYO_BOX_USDJPY.mq5",
        "symbol_tokens": ["USDJPY"],
        "requires_d1_atr": False,
        "expected_inputs": {
            "InpDryRunLogOnly": True,
            "InpMagicNumber": 20261122,
            "InpBoxStartHourUTC": 0,
            "InpBoxEndHourUTC": 3,
            "InpActEndHourUTC": 10,
            "InpFlatHourHelsinki": 18,
            "InpMaxDailyLossPct": 2.50,
        },
        "risk_tolerance": 0.01,
        "required_code_tokens": [
            "HelsinkiUtcOffsetHours",
            "LastSundayOfMonth",
            "g_boxTop",
            "g_boxBottom",
            "g_guard.Init(trade, _Symbol, InpMagicNumber, InpMaxDailyLossPct)",
            "g_guard.IsInsideRedNewsWindow()",
            "g_guard.IsDailyLossBreached()",
            "g_guard.IsNearBrokerSessionClose()",
            "g_guard.IsSpreadAndSessionSafe()",
            "g_guard.ComputeSafeLots(",
            "g_guard.ExecuteChecked(",
            "g_guard.AlreadyTradedToday(",
            "g_guard.MarkTradedToday(",
        ],
        "python_module": "pass5_usdjpy_tokyo",
        "python_symbol": "hard_flat",
    },
    "E2_USDJPY_EXP80": {
        "file": "Naqex_WB_EXP080_USDJPY.mq5",
        "symbol_tokens": ["USDJPY"],
        "requires_d1_atr": True,
        "expected_inputs": {
            "InpDryRunLogOnly": True,
            "InpMagicNumber": 20261123,
            "InpTrigAtrMult": 0.80,
            "InpSlAtrMult": 0.75,
            "InpAtrPeriodD1": 14,
            "InpEntryStartHourUTC": 7,
            "InpEntryEndHourUTC": 17,
            "InpFlatHourUTC": 20,
            "InpFlatMinUTC": 55,
            "InpMaxDailyLossPct": 2.50,
        },
        "risk_tolerance": 0.01,
        "required_code_tokens": [
            "iATR(_Symbol, PERIOD_D1, InpAtrPeriodD1)",
            "CopyBuffer(g_atrHandle, 0, 1, 1, atrBuf)",
            "iOpen(_Symbol, PERIOD_D1, 0)",
            "g_guard.Init(trade, _Symbol, InpMagicNumber, InpMaxDailyLossPct)",
            "g_guard.IsInsideRedNewsWindow()",
            "g_guard.IsDailyLossBreached()",
            "g_guard.IsNearBrokerSessionClose()",
            "g_guard.IsSpreadAndSessionSafe()",
            "g_guard.ComputeSafeLots(",
            "g_guard.ExecuteChecked(",
        ],
        "python_module": "pass17_usdjpy_forensic_cross",
        "python_symbol": "build_usdjpy_exp_tape",
        "python_defaults": {"trig_atr": 0.80, "sl_atr": 0.75},
    },
    "E3_GBPUSD_VH": {
        "file": "Naqex_WB_EXP080_VOLHIGH_GBPUSD.mq5",
        "symbol_tokens": ["GBPUSD"],
        "requires_d1_atr": True,
        "expected_inputs": {
            "InpDryRunLogOnly": True,
            "InpMagicNumber": 20261125,
            "InpTrigAtrMult": 0.80,
            "InpSlAtrMult": 0.75,
            "InpMinPrevRangeAtr": 1.10,
            "InpAtrPeriodD1": 14,
            "InpEntryStartHourUTC": 7,
            "InpEntryEndHourUTC": 17,
            "InpFlatHourUTC": 20,
            "InpFlatMinUTC": 55,
            "InpMaxDailyLossPct": 2.50,
        },
        "risk_tolerance": 0.01,
        "required_code_tokens": [
            "iATR(_Symbol, PERIOD_D1, InpAtrPeriodD1)",
            "CopyBuffer(g_atrHandle, 0, 1, 1, atrBuf)",
            "iHigh(_Symbol, PERIOD_D1, 1) - iLow(_Symbol, PERIOD_D1, 1)",
            "g_guard.Init(trade, _Symbol, InpMagicNumber, InpMaxDailyLossPct)",
            "g_guard.IsInsideRedNewsWindow()",
            "g_guard.IsDailyLossBreached()",
            "g_guard.IsNearBrokerSessionClose()",
            "g_guard.IsSpreadAndSessionSafe()",
            "g_guard.ComputeSafeLots(",
            "g_guard.ExecuteChecked(",
        ],
        "python_module": "pass22_gbpusd_volhigh_3engine",
        "python_symbol": "build_gbpusd_volhigh_tape",
        "python_defaults": {"trig_atr": 0.80, "sl_atr": 0.75, "vol_mult": 1.10},
    },
    "E4_US100_SESS40": {
        "file": "Naqex_WB_SESS_CONT_BRK40_US100.mq5",
        "symbol_tokens": ["US100.cash"],
        "requires_d1_atr": True,
        "expected_inputs": {
            "InpDryRunLogOnly": True,
            "InpMagicNumber": 20261124,
            "InpMinMorningMoveAtr": 0.40,
            "InpCloseOuterPct": 0.70,
            "InpSlAtrMult": 0.65,
            "InpAtrPeriodD1": 14,
            "InpMaxDailyLossPct": 2.50,
        },
        "risk_tolerance": 0.01,
        "required_code_tokens": [
            "NewYorkUtcOffsetHours",
            "NthSundayOfMonth",
            "nyMins >= 9 * 60 + 30 && nyMins < 11 * 60 + 30",
            "nyMins >= 15 * 60 + 55",
            "CopyBuffer(g_atrHandle, 0, 1, 1, atrBuf)",
            "g_guard.Init(trade, _Symbol, InpMagicNumber, InpMaxDailyLossPct)",
            "g_guard.IsInsideRedNewsWindow()",
            "g_guard.IsDailyLossBreached()",
            "g_guard.IsNearBrokerSessionClose()",
            "g_guard.IsSpreadAndSessionSafe()",
            "g_guard.ComputeSafeLots(",
            "g_guard.ExecuteChecked(",
        ],
        "python_module": "pass27_portfolio_m1_phase_audit",
        "python_symbol": "build_us100_e4_tape",
    },
    "E5_US100_RS1130": {
        "file": "Naqex_WB_IDX_RS_US100_LEAD_1130.mq5",
        "symbol_tokens": ["US100", "US500.cash"],
        "requires_d1_atr": True,
        "expected_inputs": {
            "InpDryRunLogOnly": True,
            "InpBenchmarkSymbol": "US500.cash",
            "InpMagicNumber": 20261126,
            "InpMinRsDiffAtr": 0.25,
            "InpSlAtrMult": 0.75,
            "InpAtrPeriodD1": 14,
            "InpMaxDailyLossPct": 2.50,
        },
        "risk_tolerance": 0.01,
        "required_code_tokens": [
            "NewYorkUtcOffsetHours",
            "nyMins >= 9 * 60 + 30 && nyMins < 9 * 60 + 35",
            "nyMins < 11 * 60 + 30 || nyMins >= 11 * 60 + 40",
            "nyMins >= 15 * 60 + 55",
            "iClose(_Symbol, PERIOD_M1, 1)",
            "iClose(InpBenchmarkSymbol, PERIOD_M1, 1)",
            "CopyBuffer(g_atrMainHandle, 0, 1, 1, atrMain)",
            "CopyBuffer(g_atrBenchHandle, 0, 1, 1, atrBench)",
            "g_guard.Init(trade, _Symbol, InpMagicNumber, InpMaxDailyLossPct)",
            "g_guard.IsInsideRedNewsWindow()",
            "g_guard.IsDailyLossBreached()",
            "g_guard.IsSpreadAndSessionSafe()",
            "g_guard.ComputeSafeLots(",
            "g_guard.ExecuteChecked(",
        ],
        "python_module": "pass27_portfolio_m1_phase_audit",
        "python_symbol": "build_us100_e5_tape",
    },
    "E6_EURJPY_VOLCOMP": {
        "file": "Naqex_WB_VOLCOMP_EXP75_EURJPY.mq5",
        "symbol_tokens": ["EURJPY"],
        "requires_d1_atr": True,
        "expected_inputs": {
            "InpDryRunLogOnly": True,
            "InpMagicNumber": 20261128,
            "InpMaxVolRatio5_20": 0.85,
            "InpTrigAtrMult": 0.75,
            "InpSlAtrMult": 0.75,
            "InpAtrPeriodD1": 14,
            "InpEntryStartHourUTC": 7,
            "InpEntryEndHourUTC": 17,
            "InpFlatHourUTC": 20,
            "InpFlatMinUTC": 55,
            "InpMaxDailyLossPct": 2.50,
        },
        "risk_tolerance": 0.01,
        "required_code_tokens": [
            "IsVolCompressedCausal()",
            "for(int s = 1; s <= 20; s++)",
            "CopyBuffer(g_atrHandle, 0, 1, 1, atrBuf)",
            "g_guard.Init(trade, _Symbol, InpMagicNumber, InpMaxDailyLossPct)",
            "g_guard.IsInsideRedNewsWindow()",
            "g_guard.IsDailyLossBreached()",
            "g_guard.IsNearBrokerSessionClose()",
            "g_guard.IsSpreadAndSessionSafe()",
            "g_guard.ComputeSafeLots(",
            "g_guard.ExecuteChecked(",
        ],
        "python_module": "pass28_final_discovery_rednews_frontier",
        "python_symbol": "build_volcomp_m1_tape",
        "python_defaults": {"thr": 0.75, "sl_atr": 0.75},
    },
    "E7_USDJPY_NY10ET": {
        "file": "Naqex_WB_NY_RISK_FLOW_10ET_USDJPY.mq5",
        "symbol_tokens": ["USDJPY", "US100.cash"],
        "requires_d1_atr": True,
        "expected_inputs": {
            "InpDryRunLogOnly": True,
            "InpEquitySymbol": "US100.cash",
            "InpMagicNumber": 20261129,
            "InpMinEquityMoveAtr": 0.25,
            "InpMinUsdBasketZ": 0.25,
            "InpSlAtrMult": 0.75,
            "InpAtrPeriodD1": 14,
            "InpFlatHourUTC": 20,
            "InpFlatMinUTC": 55,
            "InpMaxDailyLossPct": 2.50,
        },
        "risk_tolerance": 0.01,
        "required_code_tokens": [
            '{"USDJPY", "USDCAD", "EURUSD", "GBPUSD", "AUDUSD"}',
            "{1, 1, -1, -1, -1}",
            "NewYorkUtcOffsetHours",
            "nyMins < 10 * 60 || nyMins >= 10 * 60 + 10",
            "CopyBuffer(g_eqAtrHandle, 0, 1, 1, eqAtr)",
            "g_guard.Init(trade, _Symbol, InpMagicNumber, InpMaxDailyLossPct)",
            "g_guard.IsInsideRedNewsWindow()",
            "g_guard.IsDailyLossBreached()",
            "g_guard.IsSpreadAndSessionSafe()",
            "g_guard.ComputeSafeLots(",
            "g_guard.ExecuteChecked(",
        ],
        "python_module": "pass28_final_discovery_rednews_frontier",
        "python_symbol": "build_usdjpy_ny_risk_10et_m1_tape",
        "python_defaults": {"thr": 0.25, "sl_atr": 0.75},
    },
    "S6_FX_USD_BSK": {
        "file": "Naqex_WB_FX_USD_BASKET_12U_Z35.mq5",
        "symbol_tokens": ["GBPUSD", "EURUSD", "AUDUSD", "USDCAD", "USDJPY"],
        "requires_d1_atr": True,
        "expected_inputs": {
            "InpDryRunLogOnly": True,
            "InpMagicNumber": 20261127,
            "InpMinUsdBasketZ": 0.35,
            "InpSlAtrMult": 0.75,
            "InpEntryHourUTC": 12,
            "InpLookbackHours": 5,
            "InpFlatHourUTC": 20,
            "InpFlatMinUTC": 55,
            "InpAtrPeriodD1": 14,
            "InpMaxDailyLossPct": 2.50,
        },
        "risk_tolerance": 0.01,
        "required_code_tokens": [
            '{"USDJPY", "USDCAD", "EURUSD", "GBPUSD", "AUDUSD"}',
            "{1, 1, -1, -1, -1}",
            '{"GBPUSD", "EURUSD", "AUDUSD", "USDCAD"}',
            "CopyBuffer(atrHandle, 0, 1, 1, atrBuf)",
            "iClose(sym, PERIOD_M1, 1)",
            "g_guard.Init(trade, _Symbol, InpMagicNumber, InpMaxDailyLossPct)",
            "g_guard.IsInsideRedNewsWindowFor(sym)",
            "g_guard.IsSpreadAndSessionSafeFor(sym)",
            "g_guard.IsDailyLossBreached()",
            "g_guard.ComputeSafeLotsFor(",
            "g_guard.ExecuteCheckedFor(",
        ],
        "python_module": "pass27_portfolio_m1_phase_audit",
        "python_symbol": "build_fx_usd_basket_s6_tape",
    },
}


def strip_mql_comments(src: str) -> str:
    no_block = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"//[^\n]*", "", no_block)


def parse_mql_literal(raw: str, mql_type: str) -> Any:
    val = raw.strip()
    t = mql_type.strip().lower()
    if t == "bool":
        if val == "true":
            return True
        if val == "false":
            return False
        return val
    if t in ("int", "long", "uint", "ulong", "short", "ushort", "char", "uchar"):
        return int(val)
    if t in ("double", "float"):
        return float(val)
    if t == "string":
        if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
            return val[1:-1]
        return val
    return val


def parse_mq5_source(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    code = strip_mql_comments(raw)
    inputs: dict[str, dict[str, Any]] = {}
    for m in INPUT_RE.finditer(code):
        mtype, name, default_raw = m.group(1), m.group(2), m.group(3).strip()
        inputs[name] = {
            "type": mtype,
            "raw": default_raw,
            "value": parse_mql_literal(default_raw, mtype),
        }
    includes = INCLUDE_RE.findall(code)
    audit = mq5_exp.audit_open_source_mq5(raw, filename=path.name)
    return {
        "path": str(path),
        "filename": path.name,
        "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "raw": raw,
        "code": code,
        "inputs": inputs,
        "includes": includes,
        "audit": audit,
    }


def _check_python_reference(module_name: str, symbol_name: str, expected_defaults: dict[str, Any] | None = None) -> list[str]:
    errs: list[str] = []
    try:
        mod = __import__(module_name)
    except Exception as exc:
        return [f"Failed to import frozen Python module {module_name}: {exc}"]
    fn = getattr(mod, symbol_name, None)
    if fn is None:
        return [f"Missing Python symbol {module_name}.{symbol_name}"]
    if expected_defaults:
        sig = inspect.signature(fn)
        for k, exp_v in expected_defaults.items():
            if k not in sig.parameters:
                errs.append(f"{module_name}.{symbol_name} missing parameter '{k}'")
            else:
                got_v = sig.parameters[k].default
                if isinstance(exp_v, float):
                    if not isinstance(got_v, (int, float)) or abs(float(got_v) - exp_v) > 1e-9:
                        errs.append(f"{module_name}.{symbol_name} param '{k}' default={got_v} != {exp_v}")
                elif got_v != exp_v:
                    errs.append(f"{module_name}.{symbol_name} param '{k}' default={got_v} != {exp_v}")
    return errs


def verify_red_news_csv(csv_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    rows = 0
    min_ts: int | None = None
    max_ts: int | None = None
    ccys: set[str] = set()
    if not csv_path.exists():
        return {"ok": False, "rows": 0, "errors": [f"Missing red-news CSV: {csv_path}"]}
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header or header[:3] != ["utc_ts", "ccy", "event"]:
            errors.append(f"Invalid red-news CSV header: {header}")
            return {"ok": False, "rows": 0, "errors": errors}
        for lineno, row in enumerate(reader, start=2):
            if not row or not row[0].strip():
                continue
            try:
                ts = int(row[0].strip())
            except ValueError:
                errors.append(f"Row {lineno}: invalid utc_ts '{row[0]}'")
                continue
            if ts < 1_400_000_000 or ts > 2_500_000_000:
                errors.append(f"Row {lineno}: utc_ts out of plausible range ({ts})")
            ccy = row[1].strip() if len(row) > 1 else ""
            if not ccy or len(ccy) > 6:
                errors.append(f"Row {lineno}: invalid ccy '{ccy}'")
            ccys.add(ccy)
            rows += 1
            min_ts = ts if min_ts is None else min(min_ts, ts)
            max_ts = ts if max_ts is None else max(max_ts, ts)
    if rows < 200:
        errors.append(f"Red-news CSV has too few rows ({rows} < 200)")
    return {
        "ok": len(errors) == 0,
        "rows": rows,
        "min_ts": min_ts,
        "max_ts": max_ts,
        "currencies": sorted(ccys),
        "sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "errors": errors,
    }


def verify_compile_logs(ex5_dir: Path, expected_stems: list[str]) -> dict[str, Any]:
    log_dir = ex5_dir / "logs"
    results: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    if not ex5_dir.exists():
        return {"ok": False, "present": False, "files": results, "errors": [f"EX5 dir missing: {ex5_dir}"]}
    for stem in expected_stems:
        ex5_path = ex5_dir / f"{stem}.ex5"
        log_path = log_dir / f"{stem}.log"
        item: dict[str, Any] = {
            "ex5_exists": ex5_path.exists(),
            "ex5_bytes": ex5_path.stat().st_size if ex5_path.exists() else 0,
            "ex5_sha256": hashlib.sha256(ex5_path.read_bytes()).hexdigest() if ex5_path.exists() else None,
            "log_exists": log_path.exists(),
            "errors": None,
            "warnings": None,
        }
        if not ex5_path.exists() or item["ex5_bytes"] <= 0:
            errors.append(f"Missing or empty compiled binary: {ex5_path.name}")
        if not log_path.exists():
            errors.append(f"Missing MetaEditor64 compile log: {log_path.name}")
        else:
            raw_bytes = log_path.read_bytes()
            if raw_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
                text = raw_bytes.decode("utf-16")
            else:
                text = raw_bytes.decode("utf-8", errors="replace")
            m = re.search(r"Result:\s*(\d+)\s+errors?,\s*(\d+)\s+warnings?", text, re.I)
            if not m:
                errors.append(f"Could not parse Result line in {log_path.name}")
            else:
                n_err, n_warn = int(m.group(1)), int(m.group(2))
                item["errors"] = n_err
                item["warnings"] = n_warn
                if n_err != 0 or n_warn != 0:
                    errors.append(f"{stem}: compile log reported {n_err} errors, {n_warn} warnings")
        results[stem] = item
    return {"ok": len(errors) == 0, "present": True, "files": results, "errors": errors}


def run_parity_audit(
    *,
    exports_dir: Path = EXPORTS_DIR,
    registry_path: Path = REGISTRY_PATH,
    ex5_dir: Path | None = DEFAULT_EX5_DIR,
    require_ex5: bool = False,
) -> dict[str, Any]:
    """Run complete MQL5 <-> Registry <-> Python parity & safety audit."""
    reg = json.loads(registry_path.read_text(encoding="utf-8"))
    global_errors: list[str] = []

    # 1. Audit Naqex_PropGuard.mqh
    mqh_path = exports_dir / "Include/Naqex_PropGuard.mqh"
    mqh_errors: list[str] = []
    if not mqh_path.exists():
        mqh_errors.append(f"Missing {mqh_path}")
        mqh_parsed = None
    else:
        mqh_parsed = parse_mq5_source(mqh_path)
        if mqh_parsed["audit"]["red_flags"]:
            mqh_errors.append(f"PropGuard red flags: {mqh_parsed['audit']['red_flags']}")
        expected_guard_inputs = {
            "InpGuardDryRunLogOnly": True,
            "InpGuardMaxDailyLossPct": 2.50,
            "InpGuardMaxSymbolRiskPct": 1.00,  # SYMCAP_100
            "InpGuardUseOrchestrator": True,
            "InpGuardEnableRedNews": True,
            "InpGuardRedNewsCsvFile": "naqex_red_news_utc.csv",
            "InpGuardNewsPadSec": 300,
            "InpGuardMagicRangeMin": 20261120,
            "InpGuardMagicRangeMax": 20261199,
        }
        for k, exp_v in expected_guard_inputs.items():
            got = mqh_parsed["inputs"].get(k, {}).get("value")
            if isinstance(exp_v, float):
                if not isinstance(got, (int, float)) or abs(float(got) - exp_v) > 1e-9:
                    mqh_errors.append(f"PropGuard {k}={got!r} != {exp_v!r}")
            elif got != exp_v:
                mqh_errors.append(f"PropGuard {k}={got!r} != {exp_v!r}")
        for tok in (
            "SYMBOL_TRADE_TICK_VALUE_LOSS",
            "ConfigureFillingMode",
            "SymbolInfoSessionTrade",
            "GetOpenSymbolRiskPctFor",
            "IsInsideRedNewsWindowFor",
            "IsSpreadAndSessionSafeFor",
            "NQXG_GLOBAL_KILLSWITCH",
            "NQXG_GLOBAL_RISK_MULT",
            "TRADE_RETCODE_DONE",
            "LogExecAuditFor",
            "MQL_TESTER",
        ):
            if tok not in mqh_parsed["code"]:
                mqh_errors.append(f"PropGuard missing required token: {tok}")

    # 2. Audit Naqex_AccountOrchestrator.mq5
    orch_path = exports_dir / "Naqex_AccountOrchestrator.mq5"
    orch_errors: list[str] = []
    if not orch_path.exists():
        orch_errors.append(f"Missing {orch_path}")
        orch_parsed = None
    else:
        orch_parsed = parse_mq5_source(orch_path)
        if orch_parsed["audit"]["red_flags"]:
            orch_errors.append(f"Orchestrator red flags: {orch_parsed['audit']['red_flags']}")
        if "Include/Naqex_PropGuard.mqh" not in orch_parsed["includes"]:
            orch_errors.append("Orchestrator missing #include Include/Naqex_PropGuard.mqh")
        expected_orch = {
            "InpDryRunLogOnly": True,
            "InpMagicRangeMin": 20261120,
            "InpMagicRangeMax": 20261199,
            "InpHeartbeatFile": "naqex_heartbeat.json",
        }
        for k, exp_v in expected_orch.items():
            got = orch_parsed["inputs"].get(k, {}).get("value")
            if got != exp_v:
                orch_errors.append(f"Orchestrator {k}={got!r} != {exp_v!r}")
        for tok in (
            "NQXG_GLOBAL_KILLSWITCH",
            "NQXG_GLOBAL_RISK_MULT",
            "ConfigureFillingMode",
            "orphan_no_sl",
        ):
            if tok not in orch_parsed["code"]:
                orch_errors.append(f"Orchestrator missing token: {tok}")

    # 3. Audit all 8 Registry-exported EAs
    reg_engines = {e["id"]: e for e in reg["engines"]}
    exported_reg_ids = [e["id"] for e in reg["engines"] if e.get("mq5_export")]
    if set(exported_reg_ids) != set(ENGINE_PARITY_CONTRACTS.keys()):
        global_errors.append(
            f"Exported engine set mismatch: registry={sorted(exported_reg_ids)} vs contracts={sorted(ENGINE_PARITY_CONTRACTS.keys())}"
        )

    magic_min = (
        int(orch_parsed["inputs"]["InpMagicRangeMin"]["value"])
        if orch_parsed and "InpMagicRangeMin" in orch_parsed["inputs"]
        else 20261120
    )
    magic_max = (
        int(orch_parsed["inputs"]["InpMagicRangeMax"]["value"])
        if orch_parsed and "InpMagicRangeMax" in orch_parsed["inputs"]
        else 20261199
    )

    seen_magics: dict[int, str] = {}
    engine_reports: dict[str, dict[str, Any]] = {}
    for eid, contract in ENGINE_PARITY_CONTRACTS.items():
        e_errs: list[str] = []
        reg_entry = reg_engines.get(eid)
        if reg_entry is None:
            e_errs.append(f"{eid} missing from PORTFOLIO-REGISTRY.json")
            engine_reports[eid] = {"ok": False, "errors": e_errs}
            continue

        expected_rel = f"tooling/ai-engines/exports/{contract['file']}"
        if reg_entry.get("mq5_export") != expected_rel:
            e_errs.append(f"Registry mq5_export={reg_entry.get('mq5_export')!r} != {expected_rel!r}")

        ea_path = exports_dir / contract["file"]
        if not ea_path.exists():
            e_errs.append(f"Missing EA source file: {ea_path}")
            engine_reports[eid] = {"ok": False, "errors": e_errs}
            continue

        parsed = parse_mq5_source(ea_path)
        if parsed["audit"]["red_flags"]:
            e_errs.append(f"audit_open_source_mq5 red flags: {parsed['audit']['red_flags']}")
        if "Include/Naqex_PropGuard.mqh" not in parsed["includes"]:
            e_errs.append("Missing #include \"Include/Naqex_PropGuard.mqh\"")
        if "Trade/Trade.mqh" not in parsed["includes"]:
            e_errs.append("Missing #include <Trade/Trade.mqh>")

        # Magic number uniqueness & range check vs Registry + Orchestrator
        reg_magic = int(reg_entry["magic"])
        ea_magic = parsed["inputs"].get("InpMagicNumber", {}).get("value")
        if ea_magic != reg_magic:
            e_errs.append(f"Magic mismatch: EA={ea_magic} vs Registry={reg_magic}")
        if isinstance(ea_magic, int):
            if not (magic_min <= ea_magic <= magic_max):
                e_errs.append(f"Magic {ea_magic} outside Orchestrator range [{magic_min}, {magic_max}]")
            if ea_magic in seen_magics:
                e_errs.append(f"Duplicate magic {ea_magic} colliding with {seen_magics[ea_magic]}")
            seen_magics[ea_magic] = eid

        # Risk % check vs Registry base_risk_pct
        reg_risk = float(reg_entry["base_risk_pct"])
        ea_risk = parsed["inputs"].get("InpRiskPercent", {}).get("value")
        if not isinstance(ea_risk, (int, float)) or abs(float(ea_risk) - reg_risk) > contract["risk_tolerance"]:
            e_errs.append(f"InpRiskPercent={ea_risk} deviates from Registry base_risk_pct={reg_risk}")

        # Expected input defaults check
        for inp_name, exp_val in contract["expected_inputs"].items():
            got_val = parsed["inputs"].get(inp_name, {}).get("value")
            if isinstance(exp_val, float):
                if not isinstance(got_val, (int, float)) or abs(float(got_val) - exp_val) > 1e-9:
                    e_errs.append(f"Input {inp_name}={got_val!r} != expected {exp_val!r}")
            elif got_val != exp_val:
                e_errs.append(f"Input {inp_name}={got_val!r} != expected {exp_val!r}")

        # Symbol tokens check in header/source
        for sym_tok in contract["symbol_tokens"]:
            if sym_tok not in parsed["raw"]:
                e_errs.append(f"Missing expected symbol token '{sym_tok}'")

        # Required formula / PropGuard wiring tokens
        for tok in contract["required_code_tokens"]:
            if tok not in parsed["code"]:
                e_errs.append(f"Missing required code token: {tok}")

        # Anti-lookahead check: never CopyBuffer(..., 0, 0, ...) for D1 ATR
        if contract["requires_d1_atr"]:
            if re.search(r"CopyBuffer\s*\([^,]+,\s*0\s*,\s*0\s*,", parsed["code"]):
                e_errs.append("LOOKAHEAD_RISK: CopyBuffer uses shift=0 instead of causal shift=1")

        # Cross-check frozen Python module & defaults
        py_errs = _check_python_reference(
            contract["python_module"],
            contract["python_symbol"],
            contract.get("python_defaults"),
        )
        e_errs.extend(py_errs)

        engine_reports[eid] = {
            "ok": len(e_errs) == 0,
            "file": contract["file"],
            "magic": ea_magic,
            "asset": reg_entry["asset"],
            "broker_symbol": reg_entry.get("broker_symbol", reg_entry["asset"]),
            "base_risk_pct_registry": reg_risk,
            "base_risk_pct_mq5": ea_risk,
            "dry_run_default": parsed["inputs"].get("InpDryRunLogOnly", {}).get("value"),
            "red_flags": parsed["audit"]["red_flags"],
            "sha256": parsed["sha256"],
            "errors": e_errs,
        }

    # Check exact contiguous magic set 20261122..20261129
    expected_magic_set = set(range(20261122, 20261130))
    if set(seen_magics.keys()) != expected_magic_set:
        global_errors.append(
            f"Magic set {sorted(seen_magics.keys())} != expected contiguous 20261122..20261129"
        )

    # 4. Red-news CSV integrity
    news_report = verify_red_news_csv(exports_dir / "Files/naqex_red_news_utc.csv")

    # 5. Optional compiled .ex5 + MetaEditor64 compile logs check
    all_stems = ["Naqex_AccountOrchestrator"] + sorted(
        Path(c["file"]).stem for c in ENGINE_PARITY_CONTRACTS.values()
    )
    compile_report = (
        verify_compile_logs(ex5_dir, all_stems)
        if ex5_dir is not None
        else {"ok": True, "present": False, "files": {}, "errors": []}
    )
    if require_ex5 and not compile_report["ok"]:
        global_errors.extend(compile_report["errors"])

    # Verify zero stray .ex5 binaries inside tracked exports/ directory
    stray_ex5 = [p.name for p in exports_dir.glob("*.ex5")]
    if stray_ex5:
        global_errors.append(f"Stray binary .ex5 files found in exports/ (must live in .runtime/mt5-compiled-ex5/): {stray_ex5}")

    all_ok = (
        len(global_errors) == 0
        and len(mqh_errors) == 0
        and len(orch_errors) == 0
        and news_report["ok"]
        and all(r["ok"] for r in engine_reports.values())
        and (compile_report["ok"] if require_ex5 else True)
    )

    return {
        "schema": "naqex-mql5-parity-audit-v1",
        "ok": all_ok,
        "engines_checked": len(engine_reports),
        "engines_passed": sum(1 for r in engine_reports.values() if r["ok"]),
        "unique_magics": sorted(seen_magics.keys()),
        "propguard": {
            "ok": len(mqh_errors) == 0,
            "sha256": mqh_parsed["sha256"] if mqh_parsed else None,
            "errors": mqh_errors,
        },
        "orchestrator": {
            "ok": len(orch_errors) == 0,
            "sha256": orch_parsed["sha256"] if orch_parsed else None,
            "errors": orch_errors,
        },
        "red_news_csv": news_report,
        "compile_artifacts": compile_report,
        "engines": engine_reports,
        "global_errors": global_errors,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Automated MQL5 <-> Python parity & safety checker.")
    ap.add_argument("--json", action="store_true", help="Print full JSON report.")
    ap.add_argument("--require-ex5", action="store_true", help="Fail if compiled .ex5 binaries or logs are missing/dirty.")
    ap.add_argument("--ex5-dir", type=Path, default=DEFAULT_EX5_DIR, help="Directory holding compiled .ex5 and logs/.")
    args = ap.parse_args(argv)

    rep = run_parity_audit(ex5_dir=args.ex5_dir, require_ex5=args.require_ex5)
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print(f"MQL5 <-> Python Parity Audit: {'PASS' if rep['ok'] else 'FAIL'} ({rep['engines_passed']}/{rep['engines_checked']} EAs)")
        print(f"  PropGuard:    {'OK' if rep['propguard']['ok'] else 'FAIL'} {rep['propguard']['errors']}")
        print(f"  Orchestrator: {'OK' if rep['orchestrator']['ok'] else 'FAIL'} {rep['orchestrator']['errors']}")
        print(f"  Red-News CSV: {'OK' if rep['red_news_csv']['ok'] else 'FAIL'} ({rep['red_news_csv']['rows']} rows, ccys={rep['red_news_csv'].get('currencies')})")
        print(f"  Compiled EX5: {'OK' if rep['compile_artifacts']['ok'] else 'MISSING/FAIL'} ({len(rep['compile_artifacts']['files'])} checked)")
        for eid, er in rep["engines"].items():
            mark = "OK" if er["ok"] else "FAIL"
            print(f"  [{mark}] {eid:18s} | magic={er.get('magic')} | risk={er.get('base_risk_pct_mq5')} (reg {er.get('base_risk_pct_registry')}) | dry={er.get('dry_run_default')} | {er.get('file')}")
            for msg in er["errors"]:
                print(f"         ERR: {msg}")
        for msg in rep["global_errors"]:
            print(f"  GLOBAL ERR: {msg}")
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
