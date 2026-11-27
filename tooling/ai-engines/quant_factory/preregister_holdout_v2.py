"""Cryptographic Pre-Registration CLI & Tamper-Detection Verifier for `holdout_v2_prospective (>= 2026-12-01)`.

Generates and verifies `HOLDOUT-V2-PREREGISTRATION-20261127.json` + `.sha256` BEFORE `2026-12-01T00:00:00Z`.

Hard safety invariants (immune to `python -O` / `python -OO` — ZERO bare `assert` statements):
  - Read-only on all frozen code artifacts and `planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json` (NEVER mutates them).
  - `ORDER_SEND_COUNT = 0`, `HOLDOUT_ROWS_ANALYSED = 0`.
  - Enforces pre-window freeze timestamp strictly `< 2026-12-01T00:00:00Z` on `--freeze` AND `--verify`.
  - Locks exact prospective Pass/Kill thresholds (`>= 90` live/demo calendar days, adverse slippage `<= 1.50x`,
    hard kill `> 1.75x`, `swap_usd == 0.00`, `0` parameter re-tuning after unlock, single-shot unlock only).
  - Fails closed (raises `PreRegistrationError(ValueError)` / exits non-zero) on ANY 1-byte tamper in the
    manifest JSON, `.sha256` sidecar, internal canonical digest, threshold contract, or any frozen artifact.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

AI_ENGINES_DIR = Path(__file__).resolve().parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.holdout_guard import HOLDOUT_CUTOFF_DAY  # noqa: E402
from quant_core.io_utils import (  # noqa: E402
    atomic_write_text,
    repo_root_from,
    sha256_bytes,
    sha256_file,
    sha256_json_canonical,
)

SCHEMA_VERSION: str = "naqex-holdout-v2-preregistration-v1"
PREREGISTRATION_ID: str = "HOLDOUT-V2-PREREGISTRATION-20261127"
MANIFEST_FILENAME: str = "HOLDOUT-V2-PREREGISTRATION-20261127.json"
SIDECAR_FILENAME: str = "HOLDOUT-V2-PREREGISTRATION-20261127.sha256"
DEFAULT_OUT_SUBDIR: str = "planning/research"

HOLDOUT_V1_STATUS: str = "CONSUMED_2025_2026_COMMIT_521926f"
HOLDOUT_V2_STATUS: str = "SEALED_PROSPECTIVE"
PROSPECTIVE_START_DAY: str = "2026-12-01"
PROSPECTIVE_START_UTC: str = "2026-12-01T00:00:00Z"
PROSPECTIVE_START_DT: datetime = datetime(2026, 12, 1, 0, 0, 0, tzinfo=UTC)

ACTIVE_CANDIDATE: str = "C10_NEWS_ON"
PORTFOLIO_ID: str = "PORT_7E"
ORDER_SEND_COUNT: int = 0
HOLDOUT_ROWS_ANALYSED: int = 0

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_SIDECAR_LINE_RE = re.compile(r"\A([0-9a-f]{64})  ([^\r\n]+)\n\Z")


class PreRegistrationError(ValueError):
    """Fail-closed error raised on invalid pre-registration window, contract, or 1-byte tamper."""


@dataclass(frozen=True, slots=True)
class ArtifactSpec:
    """Declarative specification for one frozen code/config/lock artifact."""

    key: str
    rel_path: str
    role: str
    required: bool


FROZEN_ARTIFACT_SPECS: tuple[ArtifactSpec, ...] = (
    ArtifactSpec(
        key="Naqex_Master_Prop7E.mq5",
        rel_path="tooling/ai-engines/exports/Naqex_Master_Prop7E.mq5",
        role="master_ea_v101_production",
        required=True,
    ),
    ArtifactSpec(
        key="Naqex_PropGuard.mqh",
        rel_path="tooling/ai-engines/exports/Include/Naqex_PropGuard.mqh",
        role="propguard_risk_shield_include",
        required=True,
    ),
    ArtifactSpec(
        key="Naqex_Signals_7E.mqh",
        rel_path="tooling/ai-engines/exports/Include/Naqex_Signals_7E.mqh",
        role="signals_7e_include",
        required=True,
    ),
    ArtifactSpec(
        key="Naqex_Master_Prop7E_v103.mq5",
        rel_path="tooling/ai-engines/exports/Naqex_Master_Prop7E_v103.mq5",
        role="master_ea_v103_pareto_candidate",
        required=False,
    ),
    ArtifactSpec(
        key="firms_catalog.json",
        rel_path="tooling/ai-engines/configs/ssot/firms_catalog.json",
        role="ssot_prop_firms_catalog",
        required=True,
    ),
    ArtifactSpec(
        key="risk_profiles.json",
        rel_path="tooling/ai-engines/configs/ssot/risk_profiles.json",
        role="ssot_risk_profiles",
        required=True,
    ),
    ArtifactSpec(
        key="naqex_red_news_utc.csv",
        rel_path="tooling/ai-engines/exports/Files/naqex_red_news_utc.csv",
        role="official_red_news_calendar_csv",
        required=True,
    ),
    ArtifactSpec(
        key="NATIVE_FTMO_HOLDOUT_LOCK.json",
        rel_path="planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json",
        role="immutable_dev_holdout_lock_readonly",
        required=True,
    ),
)


def default_locked_thresholds() -> dict[str, Any]:
    """Return immutable prospective Pass/Kill thresholds locked before `2026-12-01T00:00:00Z`."""
    return {
        "min_live_demo_cal_days": 90,
        "max_adverse_slippage_mult": 1.50,
        "kill_adverse_slippage_mult": 1.75,
        "required_swap_usd": 0.0,
        "max_parameter_retunes_after_unlock": 0,
        "max_missing_sl_orders": 0,
        "max_fill_unresolved_events": 0,
        "max_parity_restart_errors": 0,
        "max_ntp_offset_ms": 1000,
        "min_pass_ann_return_frac": 0.040,
        "min_conditional_ann_return_frac": 0.010,
        "min_pass_calmar": 0.70,
        "max_float_peak_dd_frac": 0.075,
        "kill_float_peak_dd_frac": 0.090,
        "max_daily_dd_frac": 0.030,
        "kill_daily_dd_frac": 0.040,
        "min_healthy_core_engines": 5,
        "total_core_engines": 7,
        "single_shot_unlock_only": True,
        "requires_explicit_owner_g6_approval": True,
        "requires_written_firm_ea_clearance": True,
    }


def _parse_utc_iso(value: Any, *, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise PreRegistrationError(f"{field_name} must be a non-empty ISO-8601 UTC string")
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise PreRegistrationError(f"{field_name} is not valid ISO-8601: {value!r}") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise PreRegistrationError(f"{field_name} must be timezone-aware UTC: {value!r}")
    return dt.astimezone(UTC)


def _format_utc_iso(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _reject_json_nonfinite(token: str) -> Any:
    raise PreRegistrationError(f"Non-finite JSON constant forbidden in manifest: {token!r}")


def _strict_loads_json(raw_text: str) -> dict[str, Any]:
    try:
        loaded = json.loads(raw_text, parse_constant=_reject_json_nonfinite)
    except PreRegistrationError:
        raise
    except json.JSONDecodeError as exc:
        raise PreRegistrationError(f"Malformed manifest JSON: {exc}") from exc
    if not isinstance(loaded, dict):
        raise PreRegistrationError(f"Manifest root must be a JSON object, got {type(loaded).__name__}")
    return loaded


def _require_strict_int(value: Any, name: str) -> int:
    if type(value) is not int:
        raise PreRegistrationError(f"{name} must be a strict int (not bool/float/str), got {value!r}")
    return value


def _require_finite_float(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PreRegistrationError(f"{name} must be a finite number (not bool), got {value!r}")
    out = float(value)
    if not math.isfinite(out):
        raise PreRegistrationError(f"{name} must be finite (NaN/Inf forbidden), got {value!r}")
    return out


def validate_thresholds_contract(thresholds: Any) -> None:
    """Fail-closed validation of locked Holdout v2 prospective Pass/Kill thresholds."""
    if not isinstance(thresholds, Mapping):
        raise PreRegistrationError("thresholds must be a JSON mapping")

    expected_keys = set(default_locked_thresholds().keys())
    actual_keys = set(thresholds.keys())
    missing_keys = sorted(expected_keys - actual_keys)
    extra_keys = sorted(actual_keys - expected_keys)
    if missing_keys or extra_keys:
        raise PreRegistrationError(f"thresholds key mismatch: missing={missing_keys}, extra={extra_keys}")

    min_days = _require_strict_int(thresholds.get("min_live_demo_cal_days"), "thresholds.min_live_demo_cal_days")
    if min_days < 90:
        raise PreRegistrationError(f"thresholds.min_live_demo_cal_days must be >= 90, got {min_days}")

    max_slip = _require_finite_float(
        thresholds.get("max_adverse_slippage_mult"), "thresholds.max_adverse_slippage_mult"
    )
    kill_slip = _require_finite_float(
        thresholds.get("kill_adverse_slippage_mult"), "thresholds.kill_adverse_slippage_mult"
    )
    if not (0.0 < max_slip <= 1.50):
        raise PreRegistrationError(f"thresholds.max_adverse_slippage_mult must be in (0, 1.50], got {max_slip}")
    if kill_slip < max_slip or kill_slip > 1.75:
        raise PreRegistrationError(
            f"thresholds.kill_adverse_slippage_mult must be in [{max_slip}, 1.75], got {kill_slip}"
        )

    req_swap = _require_finite_float(thresholds.get("required_swap_usd"), "thresholds.required_swap_usd")
    if req_swap != 0.0:
        raise PreRegistrationError(f"thresholds.required_swap_usd must equal 0.00 exactly, got {req_swap}")

    max_retunes = _require_strict_int(
        thresholds.get("max_parameter_retunes_after_unlock"),
        "thresholds.max_parameter_retunes_after_unlock",
    )
    if max_retunes != 0:
        raise PreRegistrationError(f"thresholds.max_parameter_retunes_after_unlock must be 0, got {max_retunes}")

    for zero_field in (
        "max_missing_sl_orders",
        "max_fill_unresolved_events",
        "max_parity_restart_errors",
    ):
        zval = _require_strict_int(thresholds.get(zero_field), f"thresholds.{zero_field}")
        if zval != 0:
            raise PreRegistrationError(f"thresholds.{zero_field} must be 0, got {zval}")

    max_ntp = _require_strict_int(thresholds.get("max_ntp_offset_ms"), "thresholds.max_ntp_offset_ms")
    if not (0 < max_ntp <= 1000):
        raise PreRegistrationError(f"thresholds.max_ntp_offset_ms must be in (0, 1000], got {max_ntp}")

    min_pass_ret = _require_finite_float(
        thresholds.get("min_pass_ann_return_frac"), "thresholds.min_pass_ann_return_frac"
    )
    min_cond_ret = _require_finite_float(
        thresholds.get("min_conditional_ann_return_frac"), "thresholds.min_conditional_ann_return_frac"
    )
    if not (0.0 < min_pass_ret <= 1.0):
        raise PreRegistrationError(f"thresholds.min_pass_ann_return_frac must be in (0, 1.0], got {min_pass_ret}")
    if not (0.0 <= min_cond_ret <= min_pass_ret):
        raise PreRegistrationError(
            f"thresholds.min_conditional_ann_return_frac must be in [0, {min_pass_ret}], got {min_cond_ret}"
        )

    min_calmar = _require_finite_float(thresholds.get("min_pass_calmar"), "thresholds.min_pass_calmar")
    if min_calmar <= 0.0:
        raise PreRegistrationError(f"thresholds.min_pass_calmar must be > 0, got {min_calmar}")

    max_peak_dd = _require_finite_float(thresholds.get("max_float_peak_dd_frac"), "thresholds.max_float_peak_dd_frac")
    kill_peak_dd = _require_finite_float(
        thresholds.get("kill_float_peak_dd_frac"), "thresholds.kill_float_peak_dd_frac"
    )
    if not (0.0 < max_peak_dd <= kill_peak_dd <= 0.10):
        raise PreRegistrationError(f"peak DD thresholds invalid: max={max_peak_dd}, kill={kill_peak_dd}")

    max_daily_dd = _require_finite_float(thresholds.get("max_daily_dd_frac"), "thresholds.max_daily_dd_frac")
    kill_daily_dd = _require_finite_float(thresholds.get("kill_daily_dd_frac"), "thresholds.kill_daily_dd_frac")
    if not (0.0 < max_daily_dd <= kill_daily_dd <= 0.05):
        raise PreRegistrationError(f"daily DD thresholds invalid: max={max_daily_dd}, kill={kill_daily_dd}")

    total_eng = _require_strict_int(thresholds.get("total_core_engines"), "thresholds.total_core_engines")
    min_healthy = _require_strict_int(thresholds.get("min_healthy_core_engines"), "thresholds.min_healthy_core_engines")
    if total_eng < 1:
        raise PreRegistrationError(f"thresholds.total_core_engines must be >= 1, got {total_eng}")
    if not (1 <= min_healthy <= total_eng):
        raise PreRegistrationError(
            f"thresholds.min_healthy_core_engines must be in [1, {total_eng}], got {min_healthy}"
        )

    for bool_field in (
        "single_shot_unlock_only",
        "requires_explicit_owner_g6_approval",
        "requires_written_firm_ea_clearance",
    ):
        if thresholds.get(bool_field) is not True:
            raise PreRegistrationError(f"thresholds.{bool_field} must be True")


def hash_frozen_artifacts(
    repo_root: Path,
    *,
    specs: tuple[ArtifactSpec, ...] = FROZEN_ARTIFACT_SPECS,
) -> dict[str, dict[str, Any]]:
    """Compute read-only byte sizes and SHA-256 digests for all frozen artifacts."""
    root = Path(repo_root).resolve()
    out: dict[str, dict[str, Any]] = {}
    for spec in sorted(specs, key=lambda s: s.rel_path):
        target = (root / spec.rel_path).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise PreRegistrationError(f"Artifact path escapes repo_root: {spec.rel_path!r}") from exc

        if target.is_file():
            size_bytes = target.stat().st_size
            if size_bytes <= 0:
                raise PreRegistrationError(f"Frozen artifact is empty (0 bytes): {spec.rel_path}")
            digest = sha256_file(target)
            out[spec.rel_path] = {
                "key": spec.key,
                "role": spec.role,
                "required": spec.required,
                "present": True,
                "bytes": int(size_bytes),
                "sha256": digest,
            }
        else:
            if spec.required:
                raise PreRegistrationError(f"Required frozen artifact missing: {spec.rel_path}")
            out[spec.rel_path] = {
                "key": spec.key,
                "role": spec.role,
                "required": spec.required,
                "present": False,
                "bytes": 0,
                "sha256": None,
            }
    return out


def build_preregistration_manifest(
    repo_root: Path,
    *,
    now_utc: datetime | str | None = None,
    specs: tuple[ArtifactSpec, ...] = FROZEN_ARTIFACT_SPECS,
) -> dict[str, Any]:
    """Construct the canonical cryptographic Holdout v2 pre-registration manifest (pure, read-only)."""
    if now_utc is None:
        frozen_dt = datetime.now(UTC)
    elif isinstance(now_utc, datetime):
        if now_utc.tzinfo is None or now_utc.utcoffset() is None:
            raise PreRegistrationError("now_utc datetime must be timezone-aware UTC")
        frozen_dt = now_utc.astimezone(UTC)
    else:
        frozen_dt = _parse_utc_iso(now_utc, field_name="now_utc")

    # Fail-closed temporal gate: pre-registration MUST be frozen strictly BEFORE 2026-12-01T00:00:00Z!
    if frozen_dt >= PROSPECTIVE_START_DT:
        raise PreRegistrationError(
            f"PREREGISTRATION_WINDOW_CLOSED: frozen_utc={_format_utc_iso(frozen_dt)} "
            f"must be strictly before holdout_v2_prospective start ({PROSPECTIVE_START_UTC})"
        )

    artifacts = hash_frozen_artifacts(repo_root, specs=specs)
    thresholds = default_locked_thresholds()
    validate_thresholds_contract(thresholds)

    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "preregistration_id": PREREGISTRATION_ID,
        "frozen_utc": _format_utc_iso(frozen_dt),
        "dev_cutoff_day": HOLDOUT_CUTOFF_DAY,
        "holdout_v1_status": HOLDOUT_V1_STATUS,
        "holdout_v2_status": HOLDOUT_V2_STATUS,
        "holdout_v2_prospective_start_day": PROSPECTIVE_START_DAY,
        "holdout_v2_prospective_start_utc": PROSPECTIVE_START_UTC,
        "active_candidate": ACTIVE_CANDIDATE,
        "portfolio_id": PORTFOLIO_ID,
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
        "thresholds": thresholds,
        "artifacts": artifacts,
    }
    payload_sha = sha256_json_canonical(body)
    return {**body, "manifest_payload_sha256": payload_sha}


def serialize_manifest_json(manifest: Mapping[str, Any]) -> str:
    """Serialize manifest deterministically with LF-only line endings and NaN/Inf forbidden."""
    return json.dumps(dict(manifest), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def freeze_preregistration(
    *,
    repo_root: Path,
    out_dir: Path,
    dry_run: bool = False,
    now_utc: datetime | str | None = None,
    specs: tuple[ArtifactSpec, ...] = FROZEN_ARTIFACT_SPECS,
) -> dict[str, Any]:
    """Build (and unless `dry_run=True`, atomically write) manifest JSON + `.sha256` sidecar."""
    manifest = build_preregistration_manifest(repo_root, now_utc=now_utc, specs=specs)
    json_text = serialize_manifest_json(manifest)
    file_sha256 = sha256_bytes(json_text.encode("utf-8"))

    target_dir = Path(out_dir)
    manifest_path = target_dir / MANIFEST_FILENAME
    sidecar_path = target_dir / SIDECAR_FILENAME

    if not dry_run:
        atomic_write_text(manifest_path, json_text, encoding="utf-8", newline="\n")
        atomic_write_text(sidecar_path, f"{file_sha256}  {MANIFEST_FILENAME}\n", encoding="utf-8", newline="\n")

    return {
        "mode": "freeze",
        "dry_run": bool(dry_run),
        "manifest_path": str(manifest_path),
        "sidecar_path": str(sidecar_path),
        "file_sha256": file_sha256,
        "manifest_payload_sha256": manifest["manifest_payload_sha256"],
        "frozen_utc": manifest["frozen_utc"],
        "artifacts_hashed": sum(1 for v in manifest["artifacts"].values() if v["present"]),
        "artifacts_total_slots": len(manifest["artifacts"]),
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
        "manifest": manifest,
    }


def verify_preregistration(
    *,
    repo_root: Path,
    out_dir: Path,
    specs: tuple[ArtifactSpec, ...] = FROZEN_ARTIFACT_SPECS,
) -> dict[str, Any]:
    """Fail-closed tamper verification across sidecar `.sha256`, manifest JSON, thresholds, and disk artifacts.

    Raises `PreRegistrationError` on ANY 1-byte tamper, missing required file, unexpected optional file
    appearance, non-zero `order_send_count` / `holdout_rows_analysed`, invalid window, or altered threshold.
    """
    root = Path(repo_root).resolve()
    target_dir = Path(out_dir)
    manifest_path = target_dir / MANIFEST_FILENAME
    sidecar_path = target_dir / SIDECAR_FILENAME

    if not manifest_path.is_file():
        raise PreRegistrationError(f"Manifest JSON missing: {manifest_path}")
    if not sidecar_path.is_file():
        raise PreRegistrationError(f"Sidecar SHA-256 missing: {sidecar_path}")

    sidecar_bytes = sidecar_path.read_bytes()
    if b"\r" in sidecar_bytes:
        raise PreRegistrationError(f"SIDECAR_TAMPER_DETECTED: CR byte forbidden in LF-only sidecar {sidecar_path.name}")
    try:
        sidecar_text = sidecar_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PreRegistrationError(f"Sidecar SHA-256 is not valid UTF-8: {exc}") from exc

    m_line = _SIDECAR_LINE_RE.fullmatch(sidecar_text)
    if m_line is None:
        raise PreRegistrationError(f"SIDECAR_TAMPER_DETECTED: malformed sidecar SHA-256 format in {sidecar_path.name}")
    expected_file_sha, sidecar_fname = m_line.group(1), m_line.group(2)
    if sidecar_fname != MANIFEST_FILENAME:
        raise PreRegistrationError(f"Sidecar filename mismatch: expected {MANIFEST_FILENAME!r}, got {sidecar_fname!r}")

    raw_bytes = manifest_path.read_bytes()
    actual_file_sha = sha256_bytes(raw_bytes)
    if actual_file_sha != expected_file_sha:
        raise PreRegistrationError(
            f"MANIFEST_TAMPER_DETECTED: sidecar sha256={expected_file_sha} != actual={actual_file_sha}"
        )

    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PreRegistrationError(f"Manifest is not valid UTF-8: {exc}") from exc

    manifest = _strict_loads_json(raw_text)

    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise PreRegistrationError(
            f"Unexpected schema_version: expected {SCHEMA_VERSION!r}, got {manifest.get('schema_version')!r}"
        )
    if manifest.get("preregistration_id") != PREREGISTRATION_ID:
        raise PreRegistrationError(f"Unexpected preregistration_id: {manifest.get('preregistration_id')!r}")
    if manifest.get("dev_cutoff_day") != HOLDOUT_CUTOFF_DAY:
        raise PreRegistrationError(
            f"dev_cutoff_day must equal {HOLDOUT_CUTOFF_DAY!r}, got {manifest.get('dev_cutoff_day')!r}"
        )
    if manifest.get("holdout_v2_prospective_start_utc") != PROSPECTIVE_START_UTC:
        raise PreRegistrationError(f"holdout_v2_prospective_start_utc must equal {PROSPECTIVE_START_UTC!r}")
    if manifest.get("holdout_v2_prospective_start_day") != PROSPECTIVE_START_DAY:
        raise PreRegistrationError(f"holdout_v2_prospective_start_day must equal {PROSPECTIVE_START_DAY!r}")
    if _require_strict_int(manifest.get("order_send_count"), "order_send_count") != 0:
        raise PreRegistrationError("order_send_count must be 0")
    if _require_strict_int(manifest.get("holdout_rows_analysed"), "holdout_rows_analysed") != 0:
        raise PreRegistrationError("holdout_rows_analysed must be 0")

    frozen_dt = _parse_utc_iso(manifest.get("frozen_utc"), field_name="frozen_utc")
    if frozen_dt >= PROSPECTIVE_START_DT:
        raise PreRegistrationError(
            f"PREREGISTRATION_TIMESTAMP_INVALID: frozen_utc={manifest.get('frozen_utc')} >= {PROSPECTIVE_START_UTC}"
        )

    recorded_payload_sha = manifest.get("manifest_payload_sha256")
    if not isinstance(recorded_payload_sha, str) or _SHA256_HEX_RE.fullmatch(recorded_payload_sha) is None:
        raise PreRegistrationError("manifest_payload_sha256 is missing or not a valid 64-hex SHA-256")
    body_without_self = {k: v for k, v in manifest.items() if k != "manifest_payload_sha256"}
    recomputed_payload_sha = sha256_json_canonical(body_without_self)
    if recomputed_payload_sha != recorded_payload_sha:
        raise PreRegistrationError(
            f"MANIFEST_PAYLOAD_TAMPER_DETECTED: recorded={recorded_payload_sha} != actual={recomputed_payload_sha}"
        )

    validate_thresholds_contract(manifest.get("thresholds"))

    recorded_artifacts = manifest.get("artifacts")
    if not isinstance(recorded_artifacts, Mapping) or not recorded_artifacts:
        raise PreRegistrationError("artifacts must be a non-empty mapping")

    expected_paths = {s.rel_path for s in specs}
    recorded_paths = set(recorded_artifacts.keys())
    if recorded_paths != expected_paths:
        missing_k = sorted(expected_paths - recorded_paths)
        extra_k = sorted(recorded_paths - expected_paths)
        raise PreRegistrationError(f"Artifact slot set mismatch: missing={missing_k}, extra={extra_k}")

    verified_count = 0
    absent_optional: list[str] = []
    for spec in sorted(specs, key=lambda s: s.rel_path):
        entry = recorded_artifacts[spec.rel_path]
        if not isinstance(entry, Mapping):
            raise PreRegistrationError(f"Artifact entry for {spec.rel_path} must be a mapping")
        rec_present = entry.get("present")
        if type(rec_present) is not bool:
            raise PreRegistrationError(f"Artifact {spec.rel_path}: present must be bool")
        if spec.required and not rec_present:
            raise PreRegistrationError(f"Required artifact recorded absent: {spec.rel_path}")

        disk_path = (root / spec.rel_path).resolve()
        try:
            disk_path.relative_to(root)
        except ValueError as exc:
            raise PreRegistrationError(f"Artifact path escapes repo_root: {spec.rel_path!r}") from exc

        disk_exists = disk_path.is_file()
        if rec_present:
            if not disk_exists:
                raise PreRegistrationError(f"ARTIFACT_MISSING_ON_DISK: {spec.rel_path}")
            rec_bytes = _require_strict_int(entry.get("bytes"), f"artifacts[{spec.rel_path}].bytes")
            rec_sha = entry.get("sha256")
            if not isinstance(rec_sha, str) or _SHA256_HEX_RE.fullmatch(rec_sha) is None:
                raise PreRegistrationError(f"Artifact {spec.rel_path}: invalid sha256 {rec_sha!r}")
            actual_bytes = disk_path.stat().st_size
            if actual_bytes != rec_bytes:
                raise PreRegistrationError(
                    f"ARTIFACT_SIZE_TAMPER_DETECTED [{spec.rel_path}]: expected={rec_bytes} B, actual={actual_bytes} B"
                )
            actual_sha = sha256_file(disk_path)
            if actual_sha != rec_sha:
                raise PreRegistrationError(
                    f"ARTIFACT_HASH_TAMPER_DETECTED [{spec.rel_path}]: expected={rec_sha}, actual={actual_sha}"
                )
            verified_count += 1
        else:
            if disk_exists:
                raise PreRegistrationError(
                    f"UNREGISTERED_ARTIFACT_APPEARED_POST_FREEZE: {spec.rel_path} "
                    f"(re-freeze before {PROSPECTIVE_START_UTC} if intended)"
                )
            if entry.get("sha256") is not None or _require_strict_int(entry.get("bytes"), "bytes") != 0:
                raise PreRegistrationError(
                    f"Absent optional artifact {spec.rel_path} must have bytes=0 and sha256=null"
                )
            absent_optional.append(spec.rel_path)

    return {
        "mode": "verify",
        "status": "VERIFIED_PASS",
        "manifest_path": str(manifest_path),
        "sidecar_path": str(sidecar_path),
        "file_sha256": actual_file_sha,
        "manifest_payload_sha256": recomputed_payload_sha,
        "frozen_utc": manifest["frozen_utc"],
        "verified_artifacts": verified_count,
        "absent_optional_artifacts": absent_optional,
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
    }


def evaluate_prospective_outcome(
    manifest: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate observed prospective Holdout v2 metrics against locked Pass/Kill thresholds (fail-closed)."""
    thresholds = manifest.get("thresholds")
    validate_thresholds_contract(thresholds)
    if not isinstance(thresholds, Mapping):
        raise PreRegistrationError("thresholds missing")

    cal_days = _require_strict_int(observed.get("live_demo_cal_days"), "observed.live_demo_cal_days")
    adverse_slip = _require_finite_float(observed.get("adverse_slippage_mult"), "observed.adverse_slippage_mult")
    swap_usd = _require_finite_float(observed.get("swap_usd"), "observed.swap_usd")
    retunes = _require_strict_int(observed.get("parameter_retunes"), "observed.parameter_retunes")
    missing_sl = _require_strict_int(observed.get("missing_sl_orders", 0), "observed.missing_sl_orders")
    fill_unresolved = _require_strict_int(observed.get("fill_unresolved_events", 0), "observed.fill_unresolved_events")
    parity_errs = _require_strict_int(observed.get("parity_restart_errors", 0), "observed.parity_restart_errors")
    ann_ret = _require_finite_float(observed.get("ann_return_frac"), "observed.ann_return_frac")
    float_peak_dd = _require_finite_float(observed.get("float_peak_dd_frac"), "observed.float_peak_dd_frac")
    daily_dd = _require_finite_float(observed.get("daily_dd_frac"), "observed.daily_dd_frac")
    calmar = _require_finite_float(observed.get("calmar"), "observed.calmar")
    healthy_eng = _require_strict_int(observed.get("healthy_core_engines"), "observed.healthy_core_engines")
    total_eng = int(thresholds["total_core_engines"])

    for int_name, int_val in (
        ("observed.live_demo_cal_days", cal_days),
        ("observed.parameter_retunes", retunes),
        ("observed.missing_sl_orders", missing_sl),
        ("observed.fill_unresolved_events", fill_unresolved),
        ("observed.parity_restart_errors", parity_errs),
    ):
        if int_val < 0:
            raise PreRegistrationError(f"{int_name} must be >= 0, got {int_val}")

    for flt_name, flt_val in (
        ("observed.adverse_slippage_mult", adverse_slip),
        ("observed.float_peak_dd_frac", float_peak_dd),
        ("observed.daily_dd_frac", daily_dd),
    ):
        if flt_val < 0.0:
            raise PreRegistrationError(f"{flt_name} must be >= 0.0, got {flt_val}")

    if not (0 <= healthy_eng <= total_eng):
        raise PreRegistrationError(f"observed.healthy_core_engines must be in [0, {total_eng}], got {healthy_eng}")

    reasons: list[str] = []
    if retunes > int(thresholds["max_parameter_retunes_after_unlock"]):
        reasons.append(f"KILL_POST_UNLOCK_RETUNE: parameter_retunes={retunes} > 0")
    if swap_usd != float(thresholds["required_swap_usd"]):
        reasons.append(f"KILL_NONZERO_SWAP: swap_usd={swap_usd} != 0.00")
    if missing_sl > 0:
        reasons.append(f"KILL_MISSING_SL: missing_sl_orders={missing_sl}")
    if fill_unresolved > 0:
        reasons.append(f"KILL_FILL_UNRESOLVED: fill_unresolved_events={fill_unresolved}")
    if parity_errs > 0:
        reasons.append(f"KILL_PARITY_ERROR: parity_restart_errors={parity_errs}")
    if adverse_slip > float(thresholds["kill_adverse_slippage_mult"]):
        reasons.append(
            f"KILL_ADVERSE_SLIPPAGE: {adverse_slip:.2f}x > {float(thresholds['kill_adverse_slippage_mult']):.2f}x"
        )
    if float_peak_dd > float(thresholds["kill_float_peak_dd_frac"]):
        reasons.append(f"KILL_PEAK_DD: {float_peak_dd:.4f} > {float(thresholds['kill_float_peak_dd_frac']):.4f}")
    if daily_dd > float(thresholds["kill_daily_dd_frac"]):
        reasons.append(f"KILL_DAILY_DD: {daily_dd:.4f} > {float(thresholds['kill_daily_dd_frac']):.4f}")
    if ann_ret <= 0.0:
        reasons.append(f"KILL_NONPOSITIVE_RETURN: ann_return_frac={ann_ret:.4f} <= 0.0")

    if reasons:
        return {"verdict": "KILL", "reasons": reasons}

    if cal_days < int(thresholds["min_live_demo_cal_days"]):
        return {
            "verdict": "BLOCKED_INSUFFICIENT_DAYS",
            "reasons": [f"live_demo_cal_days={cal_days} < required {int(thresholds['min_live_demo_cal_days'])}"],
        }

    cond_reasons: list[str] = []
    if adverse_slip > float(thresholds["max_adverse_slippage_mult"]):
        cond_reasons.append(
            f"adverse_slippage_mult={adverse_slip:.2f}x exceeds pass ceiling "
            f"{float(thresholds['max_adverse_slippage_mult']):.2f}x (below hard kill)"
        )
    if ann_ret < float(thresholds["min_pass_ann_return_frac"]):
        cond_reasons.append(f"ann_return_frac={ann_ret:.4f} < {float(thresholds['min_pass_ann_return_frac']):.4f}")
    if calmar < float(thresholds["min_pass_calmar"]):
        cond_reasons.append(f"calmar={calmar:.2f} < {float(thresholds['min_pass_calmar']):.2f}")
    if float_peak_dd > float(thresholds["max_float_peak_dd_frac"]):
        cond_reasons.append(
            f"float_peak_dd_frac={float_peak_dd:.4f} > {float(thresholds['max_float_peak_dd_frac']):.4f}"
        )
    if daily_dd > float(thresholds["max_daily_dd_frac"]):
        cond_reasons.append(f"daily_dd_frac={daily_dd:.4f} > {float(thresholds['max_daily_dd_frac']):.4f}")
    if healthy_eng < int(thresholds["min_healthy_core_engines"]):
        cond_reasons.append(f"healthy_core_engines={healthy_eng} < {int(thresholds['min_healthy_core_engines'])}")

    if cond_reasons:
        return {"verdict": "CONDITIONAL", "reasons": cond_reasons}
    return {"verdict": "PASS", "reasons": []}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cryptographic Pre-Registration CLI & Tamper Verifier for holdout_v2_prospective (>= 2026-12-01)."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--freeze",
        action="store_true",
        help="Generate HOLDOUT-V2-PREREGISTRATION-20261127.json + .sha256 strictly before 2026-12-01.",
    )
    mode.add_argument(
        "--verify",
        action="store_true",
        help="Verify manifest JSON, .sha256 sidecar, locked thresholds, and every frozen artifact byte-for-byte.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output/target directory for manifest + sidecar (default: <repo_root>/planning/research).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root for resolving frozen artifact paths (default: auto-detected).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --freeze: compute and print manifest without writing any file to disk.",
    )
    parser.add_argument(
        "--now-utc",
        type=str,
        default=None,
        help="Optional ISO-8601 UTC timestamp override (testing only; still subject to < 2026-12-01T00:00:00Z).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve() if args.repo_root is not None else repo_root_from(__file__)
    out_dir = Path(args.out_dir).resolve() if args.out_dir is not None else (repo_root / DEFAULT_OUT_SUBDIR)

    try:
        if args.freeze:
            result = freeze_preregistration(
                repo_root=repo_root,
                out_dir=out_dir,
                dry_run=bool(args.dry_run),
                now_utc=args.now_utc,
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        if args.verify:
            if args.dry_run:
                raise PreRegistrationError("--dry-run cannot be combined with --verify")
            result = verify_preregistration(repo_root=repo_root, out_dir=out_dir)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
    except PreRegistrationError as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL_CLOSED",
                    "error": str(exc),
                    "order_send_count": ORDER_SEND_COUNT,
                    "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
                },
                indent=2,
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1
    return 1


__all__ = [
    "ACTIVE_CANDIDATE",
    "ArtifactSpec",
    "DEFAULT_OUT_SUBDIR",
    "FROZEN_ARTIFACT_SPECS",
    "HOLDOUT_ROWS_ANALYSED",
    "HOLDOUT_V1_STATUS",
    "HOLDOUT_V2_STATUS",
    "MANIFEST_FILENAME",
    "ORDER_SEND_COUNT",
    "PORTFOLIO_ID",
    "PREREGISTRATION_ID",
    "PROSPECTIVE_START_DAY",
    "PROSPECTIVE_START_UTC",
    "SCHEMA_VERSION",
    "SIDECAR_FILENAME",
    "PreRegistrationError",
    "build_arg_parser",
    "build_preregistration_manifest",
    "default_locked_thresholds",
    "evaluate_prospective_outcome",
    "freeze_preregistration",
    "hash_frozen_artifacts",
    "main",
    "serialize_manifest_json",
    "validate_thresholds_contract",
    "verify_preregistration",
]


if __name__ == "__main__":
    raise SystemExit(main())
