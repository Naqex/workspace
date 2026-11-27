"""READ-ONLY MQL5/preset contract drift detector against SSOT `configs/ssot/risk_profiles.json`.

Compares canonical Pydantic-validated `risk_profiles.json` against:
  1. `exports/Include/Naqex_Signals_7E.mqh` (base risk rounding e.g. `0.1606 vs 0.16`, magics)
  2. `exports/Include/Naqex_PropGuard.mqh` (fail-closed defaults, red-news pad/hard-ban, SYMCAP)
  3. `exports/Naqex_AccountOrchestrator.mq5` (explicitly flags `LEGACY_DEPRECATED_DST_BUG`)
  4. `exports/deployment_kit/**/*.set` (arm-locked dry-run, `C10_NEWS_ON` red-news & phase parity)

NEVER mutates any `.mq5`, `.mqh`, or `.set` file. Partitions findings cleanly into
`active_c10_blocking_drifts`, `active_c10_advisory_drifts`, and `legacy_archived_drifts`.
Supports `--check` (exit 1 on any HIGH drift) and `--check-active` (exit 1 only on active C10 HIGH drift).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

try:
    from quant_core.schemas import PhaseKey, PhaseRiskProfile, RiskBrakeProfile, SSOTRiskProfiles
except ImportError:  # pragma: no cover - direct script execution fallback
    _AI_ENGINES = Path(__file__).resolve().parents[1]
    if str(_AI_ENGINES) not in sys.path:
        sys.path.insert(0, str(_AI_ENGINES))
    from quant_core.schemas import PhaseKey, PhaseRiskProfile, RiskBrakeProfile, SSOTRiskProfiles

Severity = Literal["HIGH", "MEDIUM", "INFO"]
DriftScope = Literal["active_c10", "legacy_archived"]

_BASE_RISK_RE = re.compile(r"m_baseRisk\[(\d+)\]\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*;")
_MAGIC_INDEX_RE = re.compile(r"if\s*\(\s*magic\s*==\s*(\d+)\s*\)\s*return\s+(\d+)\s*;")
_INPUT_RE = re.compile(
    r"^\s*(?:input|sinput)\s+([A-Za-z0-9_]+)\s+([A-Za-z0-9_]+)\s*=\s*([^;]+);",
    re.MULTILINE,
)

DEFAULT_AI_ENGINES_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RISK_PROFILES_PATH = DEFAULT_AI_ENGINES_DIR / "configs/ssot/risk_profiles.json"
DEFAULT_EXPORTS_DIR = DEFAULT_AI_ENGINES_DIR / "exports"


@dataclass(frozen=True, slots=True)
class DriftItem:
    code: str
    severity: Severity
    file: str
    field: str
    ssot_value: Any
    observed_value: Any
    detail: str
    line: int | None = None
    scope: DriftScope = "active_c10"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_mql_scalar(raw: str) -> Any:
    val = raw.strip()
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        return val


def _parse_set_file(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16", errors="replace")
    elif raw.startswith(b"\xef\xbb\xbf"):
        text = raw.decode("utf-8-sig", errors="replace")
    else:
        text = raw.decode("utf-8", errors="replace")
    out: dict[str, Any] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(";") or "=" not in stripped:
            continue
        k, v = stripped.split("=", 1)
        out[k.strip()] = _parse_mql_scalar(v)
    return out


def _rel_str(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _check_signals_7e(
    signals_path: Path,
    profile: RiskBrakeProfile,
    base_dir: Path,
) -> list[DriftItem]:
    items: list[DriftItem] = []
    rel = _rel_str(signals_path, base_dir)
    if not signals_path.is_file():
        items.append(
            DriftItem(
                code="MISSING_MQL_TARGET",
                severity="HIGH",
                file=rel,
                field="file",
                ssot_value="exists",
                observed_value="missing",
                detail="Naqex_Signals_7E.mqh not found",
            )
        )
        return items

    text = signals_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    parsed_risks: dict[int, tuple[float, int]] = {}
    parsed_magics: dict[int, tuple[int, int]] = {}
    for line_no, line in enumerate(lines, start=1):
        m_risk = _BASE_RISK_RE.search(line)
        if m_risk:
            parsed_risks[int(m_risk.group(1))] = (float(m_risk.group(2)), line_no)
        m_mag = _MAGIC_INDEX_RE.search(line)
        if m_mag:
            parsed_magics[int(m_mag.group(2))] = (int(m_mag.group(1)), line_no)

    for eng in profile.engines:
        idx = eng.signals_array_index
        if idx not in parsed_risks:
            items.append(
                DriftItem(
                    code="MISSING_BASE_RISK_ENTRY",
                    severity="HIGH",
                    file=rel,
                    field=f"m_baseRisk[{idx}] ({eng.engine_id})",
                    ssot_value=eng.base_risk_pct,
                    observed_value=None,
                    detail=f"Missing m_baseRisk[{idx}] assignment for {eng.engine_id}",
                )
            )
        else:
            obs_risk, ln = parsed_risks[idx]
            delta = round(obs_risk - eng.base_risk_pct, 6)
            if abs(delta) > 1e-9:
                items.append(
                    DriftItem(
                        code="BASE_RISK_ROUNDING_DRIFT",
                        severity="MEDIUM",
                        file=rel,
                        field=f"m_baseRisk[{idx}] ({eng.engine_id})",
                        ssot_value=eng.base_risk_pct,
                        observed_value=obs_risk,
                        detail=(
                            f"{eng.engine_id} base_risk_pct drifts in MQL5 header: "
                            f"SSOT {eng.base_risk_pct} vs MQL5 {obs_risk} (delta={delta:+.4f}%)"
                        ),
                        line=ln,
                    )
                )

        if idx not in parsed_magics:
            items.append(
                DriftItem(
                    code="MISSING_ENGINE_MAGIC",
                    severity="HIGH",
                    file=rel,
                    field=f"EngineIndexFromMagic[{idx}] ({eng.engine_id})",
                    ssot_value=eng.magic,
                    observed_value=None,
                    detail=f"Missing magic mapping for {eng.engine_id}",
                )
            )
        else:
            obs_mag, ln = parsed_magics[idx]
            if obs_mag != eng.magic:
                items.append(
                    DriftItem(
                        code="ENGINE_MAGIC_MISMATCH",
                        severity="HIGH",
                        file=rel,
                        field=f"EngineIndexFromMagic[{idx}] ({eng.engine_id})",
                        ssot_value=eng.magic,
                        observed_value=obs_mag,
                        detail=f"Magic mismatch for {eng.engine_id}: SSOT {eng.magic} vs MQL5 {obs_mag}",
                        line=ln,
                    )
                )
    return items


def _check_prop_guard(
    guard_path: Path,
    profile: RiskBrakeProfile,
    base_dir: Path,
) -> list[DriftItem]:
    items: list[DriftItem] = []
    rel = _rel_str(guard_path, base_dir)
    if not guard_path.is_file():
        items.append(
            DriftItem(
                code="MISSING_MQL_TARGET",
                severity="HIGH",
                file=rel,
                field="file",
                ssot_value="exists",
                observed_value="missing",
                detail="Naqex_PropGuard.mqh not found",
            )
        )
        return items

    text = guard_path.read_text(encoding="utf-8", errors="replace")
    inputs: dict[str, tuple[Any, int]] = {}
    for line_no, line in enumerate(text.splitlines(), start=1):
        m = _INPUT_RE.match(line)
        if m:
            inputs[m.group(2)] = (_parse_mql_scalar(m.group(3)), line_no)

    funded = profile.phases["funded"]
    checks: list[tuple[str, Any, Severity, str]] = [
        ("InpGuardDryRunLogOnly", True, "HIGH", "PROPGUARD_FAIL_CLOSED_DRYRUN_DRIFT"),
        ("InpGuardEnableRedNews", funded.enable_red_news_guard, "HIGH", "PROPGUARD_RED_NEWS_DEFAULT_DRIFT"),
        ("InpGuardNewsPadSec", profile.red_news_pad_sec, "HIGH", "PROPGUARD_NEWS_PAD_DRIFT"),
        ("InpGuardNewsHardBanSec", profile.red_news_hard_ban_sec, "HIGH", "PROPGUARD_NEWS_HARDBAN_DRIFT"),
        (
            "InpGuardMaxDailyLossPct",
            round(funded.kill_daily_dd_frac * 100.0, 4),
            "MEDIUM",
            "PROPGUARD_DEFAULT_DAILY_STOP_DRIFT",
        ),
        (
            "InpGuardMaxSymbolRiskPct",
            round(funded.symcap_frac * 100.0, 4),
            "INFO",
            "PROPGUARD_DEFAULT_SYMCAP_DIFF",
        ),
    ]

    for key, expected, sev, code in checks:
        if key not in inputs:
            items.append(
                DriftItem(
                    code="MISSING_PROPGUARD_INPUT",
                    severity="HIGH",
                    file=rel,
                    field=key,
                    ssot_value=expected,
                    observed_value=None,
                    detail=f"Expected default input {key} missing from Naqex_PropGuard.mqh",
                )
            )
            continue
        obs, ln = inputs[key]
        mismatch = (
            abs(float(obs) - float(expected)) > 1e-6
            if isinstance(expected, float) and isinstance(obs, (int, float)) and not isinstance(obs, bool)
            else obs != expected
        )
        if mismatch:
            items.append(
                DriftItem(
                    code=code,
                    severity=sev,
                    file=rel,
                    field=key,
                    ssot_value=expected,
                    observed_value=obs,
                    detail=(
                        f"Naqex_PropGuard.mqh default {key}={obs!r} differs from "
                        f"SSOT {profile.profile_id} funded={expected!r}"
                    ),
                    line=ln,
                )
            )
    return items


def _check_legacy_orchestrator(orch_path: Path, base_dir: Path) -> tuple[str, list[DriftItem]]:
    items: list[DriftItem] = []
    rel = _rel_str(orch_path, base_dir)
    if not orch_path.is_file():
        return "ABSENT", items

    text = orch_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    def _find_line(needle: str) -> int | None:
        for i, ln in enumerate(lines, start=1):
            if needle in ln:
                return i
        return None

    has_dst_midnight_fix = "PragueMidnightUtcOffsetHours" in text
    uses_time_current_reset = "datetime srvNow = TimeCurrent();" in text
    uses_absolute_amber_brake = "MathMin(riskMult, InpAmberMult)" in text

    defects: list[str] = []
    if not has_dst_midnight_fix:
        defects.append("missing PragueMidnightUtcOffsetHours (1h Prague DST Sunday anchor drift)")
    if uses_time_current_reset:
        defects.append("uses TimeCurrent() instead of ServerNow() for reset anchor")
    if uses_absolute_amber_brake:
        defects.append(
            "uses absolute MathMin(riskMult, InpAmberMult) instead of relative InpBasePhaseMult * InpAmberMult"
        )

    status = "LEGACY_DEPRECATED_DST_BUG" if defects else "OK"
    if defects:
        items.append(
            DriftItem(
                code="LEGACY_DEPRECATED_DST_BUG",
                severity="HIGH",
                file=rel,
                field="CurrentResetStartServerTime / EvaluatePortfolioState",
                ssot_value="Naqex_Master_Prop7E.mq5 (V101-03 PragueMidnightUtcOffsetHours + relative AMBER/RED)",
                observed_value=status,
                detail="Naqex_AccountOrchestrator.mq5 flagged LEGACY_DEPRECATED_DST_BUG: " + "; ".join(defects),
                line=_find_line("CurrentResetStartServerTime") or 1,
                scope="legacy_archived",
            )
        )
    return status, items


def _infer_c10_phase(path: Path, kv: dict[str, Any]) -> PhaseKey | None:
    sku = str(kv.get("InpContractSku", "")).upper()
    stem = path.stem.upper()
    if "C10" not in sku and "C10" not in stem:
        return None
    if "_P1" in sku or "_P1_" in stem:
        return "p1"
    if "_P2" in sku or "_P2_" in stem:
        return "p2"
    if "FUNDED" in sku or "FUNDED" in stem:
        return "funded"
    return None


def _check_c10_set_against_ssot(
    rel: str,
    kv: dict[str, Any],
    phase_key: PhaseKey,
    profile: RiskBrakeProfile,
    phase: PhaseRiskProfile,
) -> list[DriftItem]:
    items: list[DriftItem] = []

    if kv.get("InpGuardEnableRedNews") is not phase.enable_red_news_guard:
        items.append(
            DriftItem(
                code="C10_NEWS_ON_RED_NEWS_DISABLED_DRIFT",
                severity="HIGH",
                file=rel,
                field="InpGuardEnableRedNews",
                ssot_value=phase.enable_red_news_guard,
                observed_value=kv.get("InpGuardEnableRedNews"),
                detail=(
                    f"C10 preset ({phase_key}) has InpGuardEnableRedNews={kv.get('InpGuardEnableRedNews')!r}, "
                    f"violating canonical {profile.profile_id} (requires {phase.enable_red_news_guard!r})"
                ),
            )
        )

    expected_map: dict[str, tuple[Any, str]] = {
        "InpBasePhaseMult": (phase.base_phase_mult, "SET_PHASE_MULT_DRIFT"),
        "InpProfitLockPct": (phase.profit_lock_pct, "SET_PROFIT_LOCK_PCT_DRIFT"),
        "InpProfitLockMult": (phase.profit_lock_mult, "SET_PROFIT_LOCK_MULT_DRIFT"),
        "InpAmberDdPct": (round(profile.amber_dd_frac * 100.0, 4), "SET_AMBER_DD_DRIFT"),
        "InpAmberMult": (profile.amber_mult, "SET_AMBER_MULT_DRIFT"),
        "InpRedDdPct": (round(profile.red_dd_frac * 100.0, 4), "SET_RED_DD_DRIFT"),
        "InpRedMult": (profile.red_mult, "SET_RED_MULT_DRIFT"),
        "InpKillDailyDdPct": (round(phase.kill_daily_dd_frac * 100.0, 4), "SET_KILL_DAILY_DD_DRIFT"),
        "InpKillStaticDdPct": (round(phase.kill_static_dd_frac * 100.0, 4), "SET_KILL_STATIC_DD_DRIFT"),
        "InpMaxSymbolRiskPct": (round(phase.factor_caps.per_symbol_frac * 100.0, 4), "SET_SYMCAP_DRIFT"),
        "InpMaxUsdClusterPct": (round(phase.factor_caps.usd_directional_frac * 100.0, 4), "SET_USD_CAP_DRIFT"),
        "InpMaxJpyClusterPct": (round(phase.factor_caps.jpy_directional_frac * 100.0, 4), "SET_JPY_CAP_DRIFT"),
        "InpMaxIdxClusterPct": (round(phase.factor_caps.us100_index_frac * 100.0, 4), "SET_IDX_CAP_DRIFT"),
        "InpMaxAccountOpenRiskPct": (
            round(phase.factor_caps.total_open_account_frac * 100.0, 4),
            "SET_ACCT_OPEN_CAP_DRIFT",
        ),
        "InpGuardNewsPadSec": (profile.red_news_pad_sec, "SET_NEWS_PAD_DRIFT"),
        "InpGuardNewsHardBanSec": (profile.red_news_hard_ban_sec, "SET_NEWS_HARDBAN_DRIFT"),
    }

    for field_name, (expected_val, code) in expected_map.items():
        if field_name not in kv:
            items.append(
                DriftItem(
                    code="SET_MISSING_REQUIRED_KEY",
                    severity="MEDIUM",
                    file=rel,
                    field=field_name,
                    ssot_value=expected_val,
                    observed_value=None,
                    detail=f"C10 preset ({phase_key}) is missing {field_name}",
                )
            )
            continue
        obs = kv[field_name]
        if isinstance(expected_val, (int, float)) and not isinstance(expected_val, bool):
            if (
                isinstance(obs, bool)
                or not isinstance(obs, (int, float))
                or abs(float(obs) - float(expected_val)) > 1e-6
            ):
                items.append(
                    DriftItem(
                        code=code,
                        severity="HIGH",
                        file=rel,
                        field=field_name,
                        ssot_value=expected_val,
                        observed_value=obs,
                        detail=f"C10 preset ({phase_key}) {field_name}={obs!r} != SSOT {expected_val!r}",
                    )
                )
        elif obs != expected_val:
            items.append(
                DriftItem(
                    code=code,
                    severity="HIGH",
                    file=rel,
                    field=field_name,
                    ssot_value=expected_val,
                    observed_value=obs,
                    detail=f"C10 preset ({phase_key}) {field_name}={obs!r} != SSOT {expected_val!r}",
                )
            )
    return items


def _check_deployment_sets(
    deployment_kit_dir: Path,
    profile: RiskBrakeProfile,
    base_dir: Path,
) -> tuple[int, int, list[DriftItem]]:
    items: list[DriftItem] = []
    if not deployment_kit_dir.is_dir():
        return 0, 0, items

    set_files = sorted(deployment_kit_dir.rglob("*.set"))
    c10_count = 0

    for sf in set_files:
        rel = _rel_str(sf, base_dir)
        kv = _parse_set_file(sf)
        dryrun_scope: DriftScope = "legacy_archived" if "FTMO_FreeTrial_Demo" in sf.parts else "active_c10"

        # Fail-closed arm-lock invariant across ALL tracked deployment presets
        if "InpDryRunLogOnly" in kv and kv["InpDryRunLogOnly"] is not True:
            items.append(
                DriftItem(
                    code="SET_FAIL_CLOSED_DRYRUN_DISARMED",
                    severity="HIGH",
                    file=rel,
                    field="InpDryRunLogOnly",
                    ssot_value=True,
                    observed_value=kv["InpDryRunLogOnly"],
                    detail=f"Tracked preset {rel} has InpDryRunLogOnly={kv['InpDryRunLogOnly']!r} (must be true)",
                    scope=dryrun_scope,
                )
            )
        if "InpGuardDryRunLogOnly" in kv and kv["InpGuardDryRunLogOnly"] is not True:
            items.append(
                DriftItem(
                    code="SET_FAIL_CLOSED_GUARD_DRYRUN_DISARMED",
                    severity="HIGH",
                    file=rel,
                    field="InpGuardDryRunLogOnly",
                    ssot_value=True,
                    observed_value=kv["InpGuardDryRunLogOnly"],
                    detail=(
                        f"Tracked preset {rel} has InpGuardDryRunLogOnly={kv['InpGuardDryRunLogOnly']!r} (must be true)"
                    ),
                    scope=dryrun_scope,
                )
            )

        if sf.name == "Naqex_AccountOrchestrator.set":
            items.append(
                DriftItem(
                    code="LEGACY_ORCHESTRATOR_PRESET",
                    severity="INFO",
                    file=rel,
                    field="target_ea",
                    ssot_value="Naqex_Master_Prop7E.mq5",
                    observed_value="Naqex_AccountOrchestrator.mq5 (LEGACY_DEPRECATED_DST_BUG)",
                    detail="Legacy preset targets deprecated Naqex_AccountOrchestrator.mq5 (DST/absolute-brake bug)",
                    scope="legacy_archived",
                )
            )

        phase_key = _infer_c10_phase(sf, kv)
        if phase_key is not None:
            c10_count += 1
            items.extend(_check_c10_set_against_ssot(rel, kv, phase_key, profile, profile.phases[phase_key]))

    return len(set_files), c10_count, items


def _count_severities(items: list[DriftItem]) -> dict[str, int]:
    return {
        "HIGH": sum(1 for d in items if d.severity == "HIGH"),
        "MEDIUM": sum(1 for d in items if d.severity == "MEDIUM"),
        "INFO": sum(1 for d in items if d.severity == "INFO"),
    }


def run_drift_audit(
    *,
    risk_profiles_path: Path = DEFAULT_RISK_PROFILES_PATH,
    exports_dir: Path = DEFAULT_EXPORTS_DIR,
    profile_id: str | None = None,
) -> dict[str, Any]:
    """Run read-only drift audit comparing SSOT `risk_profiles.json` against MQL5 headers & `.set` files."""
    raw = json.loads(risk_profiles_path.read_text(encoding="utf-8"))
    ssot = SSOTRiskProfiles.model_validate(raw)
    target_pid = profile_id or ssot.primary_profile_id
    if target_pid not in ssot.profiles:
        raise ValueError(f"profile_id {target_pid!r} not found in {risk_profiles_path}")
    profile = ssot.profiles[target_pid]

    base_dir = exports_dir.parent
    signals_path = exports_dir / "Include/Naqex_Signals_7E.mqh"
    guard_path = exports_dir / "Include/Naqex_PropGuard.mqh"
    orch_path = exports_dir / "Naqex_AccountOrchestrator.mq5"
    kit_dir = exports_dir / "deployment_kit"

    drifts: list[DriftItem] = []
    drifts.extend(_check_signals_7e(signals_path, profile, base_dir))
    drifts.extend(_check_prop_guard(guard_path, profile, base_dir))
    orch_status, orch_drifts = _check_legacy_orchestrator(orch_path, base_dir)
    drifts.extend(orch_drifts)
    total_sets, c10_sets, set_drifts = _check_deployment_sets(kit_dir, profile, base_dir)
    drifts.extend(set_drifts)

    active_c10_all = [d for d in drifts if d.scope == "active_c10"]
    active_c10_blocking = [d for d in active_c10_all if d.severity == "HIGH"]
    active_c10_advisory = [d for d in active_c10_all if d.severity != "HIGH"]
    legacy_archived = [d for d in drifts if d.scope == "legacy_archived"]

    severity_counts = _count_severities(drifts)
    active_c10_severity_counts = _count_severities(active_c10_all)
    legacy_archived_severity_counts = _count_severities(legacy_archived)

    code_counts: dict[str, int] = {}
    for d in drifts:
        code_counts[d.code] = code_counts.get(d.code, 0) + 1

    target_hashes: dict[str, str] = {"risk_profiles_ssot": _file_sha256(risk_profiles_path)}
    for label, p in (
        ("Naqex_Signals_7E.mqh", signals_path),
        ("Naqex_PropGuard.mqh", guard_path),
        ("Naqex_AccountOrchestrator.mq5", orch_path),
    ):
        if p.is_file():
            target_hashes[label] = _file_sha256(p)

    return {
        "schema_version": "naqex-mql-contract-drift-v1",
        "read_only": True,
        "mutated_files": 0,
        "order_send_count": 0,
        "profile_id": profile.profile_id,
        "portfolio_id": profile.portfolio_id,
        "orchestrator_status": orch_status,
        "scanned_set_files": total_sets,
        "scanned_c10_set_files": c10_sets,
        "target_sha256": target_hashes,
        "severity_counts": severity_counts,
        "active_c10_severity_counts": active_c10_severity_counts,
        "legacy_archived_severity_counts": legacy_archived_severity_counts,
        "code_counts": dict(sorted(code_counts.items())),
        "has_blocking_drift": severity_counts["HIGH"] > 0,
        "has_active_c10_blocking_drift": len(active_c10_blocking) > 0,
        "active_c10_blocking_count": len(active_c10_blocking),
        "legacy_archived_blocking_count": legacy_archived_severity_counts["HIGH"],
        "legacy_archived_count": len(legacy_archived),
        "active_c10_blocking_drifts": [asdict(item) for item in active_c10_blocking],
        "active_c10_advisory_drifts": [asdict(item) for item in active_c10_advisory],
        "legacy_archived_drifts": [asdict(item) for item in legacy_archived],
        "drifts": [asdict(item) for item in drifts],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero (1) if any HIGH-severity contract drift (active or legacy) is detected (read-only).",
    )
    parser.add_argument(
        "--check-active",
        action="store_true",
        help=(
            "Exit non-zero (1) only if any active C10 HIGH-severity blocking drift is detected "
            "(transparently reports legacy_archived_drifts without failing)."
        ),
    )
    parser.add_argument(
        "--risk-profiles",
        type=Path,
        default=DEFAULT_RISK_PROFILES_PATH,
        help="Path to SSOT risk_profiles.json.",
    )
    parser.add_argument(
        "--exports-dir",
        type=Path,
        default=DEFAULT_EXPORTS_DIR,
        help="Path to exports/ directory containing Include/, Naqex_AccountOrchestrator.mq5, and deployment_kit/.",
    )
    parser.add_argument(
        "--profile-id",
        type=str,
        default=None,
        help="Override profile_id from risk_profiles.json (default: primary_profile_id).",
    )
    args = parser.parse_args(argv)
    report = run_drift_audit(
        risk_profiles_path=args.risk_profiles,
        exports_dir=args.exports_dir,
        profile_id=args.profile_id,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.check and report["has_blocking_drift"]:
        return 1
    if args.check_active and report["has_active_c10_blocking_drift"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
