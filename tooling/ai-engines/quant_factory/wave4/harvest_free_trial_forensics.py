"""Strictly Read-Only FTMO Free-Trial Forensics Harvester (`08/12` Milestone — `W4-G12`).

Pulls read-only execution audit CSVs, shadow logs, decision blackbox JSONL, broker deal
exports, and quote tapes from `naqex-node1` via SSH aliases (`naqex-node1-lan` /
`naqex-node1-ts`, NEVER hardcoded LAN/Tailscale IPs or logins) OR loads a deterministic
local `--offline-fixture` directory/manifest for CI verification.

Composes directly with:
  - `ops_cloud/node_ctl.py` (strictly read-only probes ONLY; `deploy-scripts` & all
    remote writes/uploads are hard-blocked fail-closed!)
  - `quant_factory/live_ops/live_broker_tape_ingestor.py` (isolated `live-vault` tape
    ingestion + SHA-256 manifest + zero Dev/Holdout cache contamination verification)
  - `quant_factory/live_ops/live_parity_forensics.py` (`OPS-6` 1-to-1 Python-vs-MT5
    parity, `POSITION_IDENTIFIER` deal aggregation, `W1..L4` geometry & anti-overfit)
  - `quant_core/tca.py` & `quant_factory/tca_reconcile.py` (statement enrichment,
    post-reconcile gate, `swap_usd == 0` enforcement, causal markout curve)

Emits a unified, OPSEC-redacted, SHA-256 stamped Free-Trial Forensics Bundle containing:
  - Verified read-only posture & telemetry (`NTP < 1000 ms`, `expected_login`,
    `expected_server`, `trade_allowed == False`, `OrderSend = 0`, `SSH_WRITE_COUNT = 0`)
  - Realized slippage tail (`P50 / P90 / P95 / P99`) overall & per symbol
  - `US100.cash` SL slippage multiplier vs locked `1.50x` (PASS) / `1.75x` (HARD KILL)
  - `OPS-6` parity metrics (`trade_match_rate`, `ghost_trades`, `missed_trades`,
    `lot_or_sl_drift`, `friction_drift`, `legitimate_guard_blocks`)
  - Ready-to-act `12-13/12` GO / NO-GO decision gate.

HARD SAFETY & IMMUTABILITY INVARIANTS (`[ARCH-02]`, `G02`, `G11`, `G16`):
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `SSH_WRITE_COUNT = 0`.
  - NEVER imports `MetaTrader5`.
  - ZERO bare `assert` statements (100% immune to `python -O` / `python -OO`).
  - ALL `subprocess` calls pass `creationflags=_NO_WINDOW_FLAGS` (`CREATE_NO_WINDOW`).
  - Default `run_mode="dev"` strictly blocks ANY `2025+` (`>= 2025-01-01T00:00:00Z`)
    timestamp via `quant_core.holdout_guard.enforce_pre_holdout_ts`.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import numpy as np

AI_ENGINES_DIR: Final[Path] = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT: Final[Path] = AI_ENGINES_DIR.parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from ops_cloud import node_ctl  # noqa: E402
from quant_core.holdout_guard import (  # noqa: E402
    HOLDOUT_CUTOFF_DAY,
    HOLDOUT_START_UTC_TS,
    HoldoutLockError,
    enforce_pre_holdout_ts,
)
from quant_core.io_utils import atomic_write_text  # noqa: E402
from quant_core.tca import (  # noqa: E402
    EXIT_EVENT_TYPES,
    NON_FILL_EVENT_TYPES,
    VALID_FILL_EVENT_TYPES,
    canonical_payload_sha256,
    enrich_audit_rows_with_statement,
    normalize_symbol_alias,
    parse_exec_audit_row,
    parse_optional_finite_float,
    parse_optional_strict_int,
    point_size_for_symbol,
    validate_tca_post_reconcile,
    write_atomic_sha256_json,
)

from quant_factory.live_ops.live_broker_tape_ingestor import (  # noqa: E402
    DEFAULT_LIVE_VAULT_ROOT,
    ingest_live_broker_tape,
    load_broker_quote_tape,
    verify_live_vault_manifest,
    verify_zero_cache_contamination,
)
from quant_factory.live_ops.live_parity_forensics import (  # noqa: E402
    PARITY_BOT_BUG_GHOST_TRADE,
    PARITY_BOT_BUG_MISSED_TRADE,
    PARITY_EXECUTION_FRICTION_DRIFT,
    PARITY_LEGITIMATE_GUARD_BLOCK,
    PARITY_LOT_OR_SL_DRIFT,
    PARITY_MATCH_CLEAN,
    aggregate_mt5_deals_by_position,
    build_weekly_forensics_report,
    load_decision_blackbox_jsonl,
    load_exec_audit_records,
    load_v103_shadow_csv,
    render_weekly_forensics_markdown,
)
from quant_factory.tca_reconcile import compute_tca_report  # noqa: E402

SCHEMA_VERSION: Final[str] = "naqex-wave4-free-trial-forensics-v1"
ORDER_SEND_CAPABLE: Final[bool] = False
ORDER_SEND_COUNT: Final[int] = 0
SSH_WRITE_COUNT: Final[int] = 0

_NO_WINDOW_FLAGS: Final[int] = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0

DEFAULT_SSH_HOSTS: Final[tuple[str, ...]] = ("naqex-node1-lan", "naqex-node1-ts")
ALLOWED_SSH_HOST_ALIASES: Final[frozenset[str]] = frozenset(
    {"naqex-node1-lan", "naqex-node1-ts", "naqex-node1"}
)
READONLY_NODE_CTL_ACTIONS: Final[frozenset[str]] = frozenset(
    {"status", "audit", "logs", "integrity", "maint"}
)
DEFAULT_REMOTE_FILES_DIR: Final[str] = r"C:\Naqex\mt5\MQL5\Files"
ALLOWED_REMOTE_PREFIXES: Final[tuple[str, ...]] = ("c:/naqex/", "c:\\naqex\\")
ALLOWED_PULL_EXTENSIONS: Final[frozenset[str]] = frozenset({".csv", ".jsonl", ".json", ".log", ".txt"})

MAX_NTP_OFFSET_MS: Final[float] = 1000.0
PROSPECTIVE_TRIAL_START_UTC_TS: Final[int] = int(datetime(2026, 12, 1, 0, 0, 0, tzinfo=UTC).timestamp())
PROSPECTIVE_TRIAL_START_ISO: Final[str] = "2026-12-01T00:00:00Z"

# US100.cash baseline per-leg SL slippage (1.00 index point = 100 broker points @ point=0.01,
# half of the 200.0 pts RT Dev baseline in prop_live_tca_monitor.py) and locked Holdout v2 gates.
US100_BASE_SL_SLIP_PTS: Final[float] = 100.0
US100_PASS_SLIP_MULT: Final[float] = 1.50
US100_KILL_SLIP_MULT: Final[float] = 1.75
MIN_GO_TRADE_MATCH_RATE: Final[float] = 0.98

_IPV4_RE: Final[re.Pattern[str]] = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}")
_WIN_DRIVE_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z]:(?:[\\/]|$)")
_FORBIDDEN_SSH_META: Final[frozenset[str]] = frozenset(">|;&`<$\r\n")
_SAFE_REMOTE_PATH_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z]:[\\/][A-Za-z0-9._\\/@ -]+$")
_READONLY_DIR_CMD_RE: Final[re.Pattern[str]] = re.compile(
    r'^dir\s+/b\s+"([A-Za-z]:[\\/][A-Za-z0-9._\\/@ -]+)"$', re.IGNORECASE
)
_READONLY_PROBE_CMD_RE: Final[re.Pattern[str]] = re.compile(
    r'^"C:\\Naqex\\tools\\python\\[^"<>|;&`$\r\n]+\\python\.exe"\s+'
    r'"C:\\Naqex\\scripts\\(node_status|node_exec_audit|node_logs|node_integrity|node_maint_check)\.py"'
    r'(?:\s+[A-Za-z0-9._:=\\/@," -]+)?$',
    re.IGNORECASE,
)
_FORBIDDEN_WRITE_TOKENS_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:^|[\s\"'\\/])("
    r"mkdir|md|rm|rmdir|rd|del|erase|mv|move|ren|rename|cp|copy|xcopy|robocopy|"
    r"tee|touch|chmod|chown|set-content|add-content|out-file|new-item|remove-item|"
    r"move-item|copy-item|writealltext|writeallbytes|deploy-scripts|deploy|upload|"
    r"put|install|restart|stop-process|taskkill|kill|schtasks|reg|ordersend|order_send|"
    r"encodedcommand"
    r")(?=$|[\s\"'\\/:=])"
)
_FORBIDDEN_LOCAL_DST_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:^|[\\/])("
    r"hot-m1-cache|mt5-m1-cache|new-assets-10-cache|offensive3-d1-cache|"
    r"dev_cache|dev-cache|holdout|native_ftmo_holdout|holdout_2025|"
    r"private_vault|exports|mql5|quant_core|mt5-compiled-ex5"
    r")(?:$|[\\/])"
)
_NTP_SECONDS_RE: Final[re.Pattern[str]] = re.compile(r"^([+-]?\d+(?:\.\d+)?)\s*s$", re.IGNORECASE)
_NTP_MS_RE: Final[re.Pattern[str]] = re.compile(r"^([+-]?\d+(?:\.\d+)?)\s*ms$", re.IGNORECASE)
_DOT_DATE_RE: Final[re.Pattern[str]] = re.compile(r"^(\d{4})\.(\d{2})\.(\d{2})(.*)$")

_SLIPPAGE_NUMERIC_KEYS: Final[tuple[str, ...]] = (
    "adverse_slip_pts",
    "adverse_slip_bps",
    "adverse_slip_r",
    "slippage_pts",
    "sl_slippage_pts",
    "slip_pts",
    "entry_slip_pts",
    "exit_slip_pts",
    "signal_price",
    "fill_price",
    "entry_price",
    "exit_price",
    "close_price",
    "sl_price",
    "lots",
    "volume",
    "spread_pts",
    "latency_ms",
    "pnl_usd",
    "profit",
    "swap_usd",
    "swap",
    "commission_usd",
    "commission",
    "fee_usd",
    "fee",
)

_PULL_FILE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^naqex_exec_audit.*\.csv$", re.IGNORECASE),
    re.compile(r"^naqex_.*shadow.*\.csv$", re.IGNORECASE),
    re.compile(r"^naqex_decision_blackbox_.*\.jsonl$", re.IGNORECASE),
    re.compile(r"^.*(?:deals|statement).*\.(?:csv|json)$", re.IGNORECASE),
    re.compile(r"^(?:mt5_live_spread_log.*|.*quote.*|.*nfp.*|.*cpi.*)\.(?:csv|jsonl)$", re.IGNORECASE),
    re.compile(r"^.*(?:symbol_specs|expected_python_trades).*\.json$", re.IGNORECASE),
)


# ---------------------------------------------------------------------------
# Fail-Closed Exceptions (all subclass ValueError for clean caller handling)
# ---------------------------------------------------------------------------
class HarvestGuardError(ValueError):
    """Base fail-closed error for the Free-Trial Forensics Harvester."""


class ReadOnlyViolationError(HarvestGuardError):
    """Raised whenever any remote SSH write, SCP push, or OrderSend mutation is attempted."""


class TelemetryPreflightError(HarvestGuardError):
    """Raised when NTP, expected_login, expected_server, or trade_allowed==False fails."""


class NonFiniteTelemetryError(HarvestGuardError):
    """Raised when any slippage, price, timestamp, or metric contains NaN/Inf/bool."""


# ---------------------------------------------------------------------------
# Strictly Read-Only SSH / SCP Validators & Pull Helpers
# ---------------------------------------------------------------------------
def validate_ssh_host_alias(host: str) -> str:
    """Allow ONLY approved SSH host aliases (`naqex-node1-lan`/`naqex-node1-ts`/`naqex-node1`).

    Rejects raw IPv4/IPv6 addresses, `user@host`, shell metacharacters, and unlisted hosts.
    """
    if not isinstance(host, str):
        raise ReadOnlyViolationError(f"INVALID_SSH_HOST_ALIAS: expected str, got {type(host).__name__}")
    alias = host.strip()
    if not alias:
        raise ReadOnlyViolationError("INVALID_SSH_HOST_ALIAS: blank host alias rejected")
    if "@" in alias or ":" in alias or _IPV4_RE.search(alias):
        raise ReadOnlyViolationError(
            f"RAW_IP_OR_USER_HOST_FORBIDDEN: {alias!r} must use an allowlisted SSH alias, never a raw IP"
        )
    if any(ch in _FORBIDDEN_SSH_META for ch in alias):
        raise ReadOnlyViolationError(f"UNSAFE_SSH_HOST_ALIAS: shell metacharacters rejected in {alias!r}")
    if alias not in ALLOWED_SSH_HOST_ALIASES:
        raise ReadOnlyViolationError(
            f"UNLISTED_SSH_HOST_ALIAS: {alias!r} not in {sorted(ALLOWED_SSH_HOST_ALIASES)}"
        )
    return node_ctl._validate_host(alias)


def validate_readonly_ssh_command(remote_cmd: str) -> str:
    """Fail-closed gate rejecting ANY SSH write/mutation/redirection or unlisted command."""
    if not isinstance(remote_cmd, str) or not remote_cmd.strip():
        raise ReadOnlyViolationError("SSH_WRITE_GUARD: empty remote command rejected")
    cmd = remote_cmd.strip()
    if any(ch in _FORBIDDEN_SSH_META for ch in cmd):
        raise ReadOnlyViolationError(
            f"SSH_WRITE_FORBIDDEN: shell redirection/chaining metacharacters rejected in {cmd!r}"
        )
    if _FORBIDDEN_WRITE_TOKENS_RE.search(cmd):
        raise ReadOnlyViolationError(
            f"SSH_WRITE_FORBIDDEN: mutating/write command token rejected in {cmd!r}"
        )

    m_dir = _READONLY_DIR_CMD_RE.fullmatch(cmd)
    if m_dir is not None:
        raw_dir = m_dir.group(1)
        if ".." in raw_dir or not raw_dir.lower().startswith(ALLOWED_REMOTE_PREFIXES):
            raise ReadOnlyViolationError(
                f"SSH_REMOTE_PATH_FORBIDDEN: directory listing restricted under C:\\Naqex\\, got {raw_dir!r}"
            )
        return cmd

    if _READONLY_PROBE_CMD_RE.fullmatch(cmd) is not None:
        return cmd

    raise ReadOnlyViolationError(
        f"SSH_UNLISTED_COMMAND_FORBIDDEN: only read-only node probes and C:\\Naqex dir /b are permitted, got {cmd!r}"
    )


def _is_remote_scp_spec(spec: str) -> bool:
    s = str(spec).strip()
    if ":" not in s:
        return False
    if _WIN_DRIVE_RE.match(s):
        return False
    return True


def validate_readonly_scp_pull(remote_src: str, local_dst: Path | str) -> tuple[str, str, Path]:
    """Enforce strictly PULL-ONLY SCP (`<allowed_alias>:C:/Naqex/...` -> isolated local path).

    Any attempt to SCP push/upload (`local -> remote`) or target Dev/Holdout caches fails closed.
    """
    src_str = str(remote_src or "").strip()
    dst_str = str(local_dst or "").strip()
    if not src_str or not dst_str:
        raise ReadOnlyViolationError("SCP_PULL_INVALID: both remote_src and local_dst are required")

    if _is_remote_scp_spec(dst_str):
        raise ReadOnlyViolationError(
            f"SSH_WRITE_FORBIDDEN: SCP push/upload to remote destination {dst_str!r} is strictly prohibited"
        )
    if not _is_remote_scp_spec(src_str):
        raise ReadOnlyViolationError(
            f"SSH_READONLY_PULL_REQUIRED: SCP source {src_str!r} must be '<allowed_alias>:C:/Naqex/...'"
        )

    alias_raw, remote_path_raw = src_str.split(":", 1)
    alias = validate_ssh_host_alias(alias_raw)
    remote_path = remote_path_raw.strip()
    if (
        not remote_path
        or ".." in remote_path
        or any(ch in _FORBIDDEN_SSH_META for ch in remote_path)
        or not _SAFE_REMOTE_PATH_RE.fullmatch(remote_path)
        or not remote_path.lower().startswith(ALLOWED_REMOTE_PREFIXES)
    ):
        raise ReadOnlyViolationError(
            f"SCP_REMOTE_PATH_FORBIDDEN: remote pull restricted to safe C:/Naqex/ files, got {remote_path!r}"
        )

    ext = Path(remote_path.replace("\\", "/")).suffix.lower()
    if ext not in ALLOWED_PULL_EXTENSIONS:
        raise ReadOnlyViolationError(
            f"SCP_REMOTE_EXTENSION_FORBIDDEN: {ext!r} not in {sorted(ALLOWED_PULL_EXTENSIONS)}"
        )

    norm_dst = dst_str.replace("/", "\\")
    if re.match(r"(?i)^E:(?:\\|$)", norm_dst) or re.search(r"(^|\\)\.\.(\\|$)", norm_dst):
        raise ReadOnlyViolationError(f"SCP_LOCAL_DST_FORBIDDEN: unsafe destination {dst_str!r}")
    dst_path = Path(dst_str).resolve(strict=False)
    if re.match(r"(?i)^E:(?:\\|$)", str(dst_path)) or _FORBIDDEN_LOCAL_DST_RE.search(str(dst_path)):
        raise ReadOnlyViolationError(
            f"SCP_LOCAL_DST_CONTAMINATION_BLOCKED: {dst_path} overlaps forbidden Dev/Holdout/Vault path"
        )

    return alias, remote_path.replace("\\", "/"), dst_path


def run_readonly_node_probe(
    action: str,
    *,
    host: str | None = None,
    hosts: Sequence[str] = DEFAULT_SSH_HOSTS,
    extra_args: list[str] | None = None,
    timeout: int = 20,
) -> dict[str, Any]:
    """Execute one strictly read-only `node_ctl` probe (`deploy-scripts` is hard-blocked)."""
    act = str(action or "").strip().lower()
    if act not in READONLY_NODE_CTL_ACTIONS:
        raise ReadOnlyViolationError(
            f"SSH_WRITE_FORBIDDEN: node_ctl action {action!r} is not in read-only allowlist "
            f"{sorted(READONLY_NODE_CTL_ACTIONS)}"
        )

    candidates = (
        (validate_ssh_host_alias(host),)
        if host is not None
        else tuple(validate_ssh_host_alias(h) for h in hosts)
    )
    if not candidates:
        raise ReadOnlyViolationError("SSH_HOST_LIST_EMPTY")

    last_err = ""
    for idx, candidate in enumerate(candidates):
        has_next = idx + 1 < len(candidates)
        try:
            payload = node_ctl.run_remote_probe(act, extra_args=extra_args, host=candidate, timeout=timeout)
            if not isinstance(payload, Mapping):
                raise RuntimeError(f"Unexpected non-mapping probe payload from {candidate}")
            out = dict(payload)
            out["_ssh_host"] = candidate
            return out
        except RuntimeError as exc:
            msg = str(exc)
            if has_next and ("rc=255" in msg or "Unable to reach" in msg):
                last_err = f"{candidate}: {msg}"
                continue
            raise
        except OSError as exc:
            last_err = f"{candidate}: {exc}"
            if has_next:
                continue
            raise RuntimeError(f"Unable to reach any SSH host in {candidates}: {last_err}") from exc

    raise RuntimeError(f"Unable to reach any SSH host in {candidates}: {last_err}")


def run_readonly_ssh_list_files(
    *,
    remote_dir: str = DEFAULT_REMOTE_FILES_DIR,
    host: str | None = None,
    hosts: Sequence[str] = DEFAULT_SSH_HOSTS,
    timeout: int = 15,
) -> tuple[str, list[str]]:
    """List files in remote MT5 Files directory via strictly read-only `ssh` (`CREATE_NO_WINDOW`)."""
    remote_cmd = validate_readonly_ssh_command(f'dir /b "{remote_dir}"')
    candidates = (
        (validate_ssh_host_alias(host),)
        if host is not None
        else tuple(validate_ssh_host_alias(h) for h in hosts)
    )
    last_err = ""
    for idx, candidate in enumerate(candidates):
        has_next = idx + 1 < len(candidates)
        try:
            proc = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes", candidate, remote_cmd],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=_NO_WINDOW_FLAGS,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            last_err = f"{candidate}: {exc}"
            if has_next:
                continue
            raise RuntimeError(f"Unable to reach any SSH host in {candidates}: {last_err}") from exc

        if proc.returncode == 255 and has_next:
            last_err = f"{candidate}: {proc.stderr.strip()}"
            continue
        if proc.returncode != 0:
            raise RuntimeError(
                f"Read-only dir listing failed on {candidate} (rc={proc.returncode}): {proc.stderr.strip()}"
            )
        names = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
        return candidate, names

    raise RuntimeError(f"Unable to reach any SSH host in {candidates}: {last_err}")


def run_readonly_scp_pull(
    remote_src: str,
    local_dst: Path | str,
    *,
    timeout: int = 30,
) -> Path:
    """Pull a single read-only artifact from an allowlisted SSH alias (`CREATE_NO_WINDOW`)."""
    alias, remote_path, dst_path = validate_readonly_scp_pull(remote_src, local_dst)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["scp", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes", f"{alias}:{remote_path}", str(dst_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=_NO_WINDOW_FLAGS,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Read-only SCP pull failed for {alias}:{remote_path} (rc={proc.returncode}): {proc.stderr.strip()}"
        )
    return dst_path


def _is_pullable_forensics_filename(filename: str) -> bool:
    base = Path(filename).name
    if base != filename or ".." in base:
        return False
    return any(rx.fullmatch(base) for rx in _PULL_FILE_PATTERNS)


def pull_readonly_trial_artifacts(
    staging_dir: Path | str,
    *,
    host: str | None = None,
    hosts: Sequence[str] = DEFAULT_SSH_HOSTS,
    remote_files_dir: str = DEFAULT_REMOTE_FILES_DIR,
) -> dict[str, Any]:
    """Pull Free-Trial status, exec audits, shadow logs, deals & quotes strictly read-only (`0` remote writes)."""
    stage_path = Path(staging_dir).resolve(strict=False)
    if _FORBIDDEN_LOCAL_DST_RE.search(str(stage_path)) or re.match(r"(?i)^E:(?:\\|$)", str(stage_path)):
        raise ReadOnlyViolationError(f"STAGING_DIR_FORBIDDEN: {stage_path}")
    stage_path.mkdir(parents=True, exist_ok=True)

    status_payload = run_readonly_node_probe("status", host=host, hosts=hosts)
    active_alias = validate_ssh_host_alias(str(status_payload.get("_ssh_host") or (host or hosts[0])))
    audit_summary = run_readonly_node_probe("audit", host=active_alias)

    _, remote_names = run_readonly_ssh_list_files(remote_dir=remote_files_dir, host=active_alias)
    remote_base_posix = remote_files_dir.replace("\\", "/").rstrip("/")

    pulled_files: list[str] = []
    for fname in sorted(remote_names):
        if not _is_pullable_forensics_filename(fname):
            continue
        remote_spec = f"{active_alias}:{remote_base_posix}/{fname}"
        local_target = stage_path / fname
        run_readonly_scp_pull(remote_spec, local_target)
        pulled_files.append(fname)

    status_out = stage_path / "node_status.json"
    atomic_write_text(
        status_out,
        json.dumps(status_payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    audit_out = stage_path / "node_exec_audit_summary.json"
    atomic_write_text(
        audit_out,
        json.dumps(audit_summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        "ssh_alias": active_alias,
        "ssh_write_count": SSH_WRITE_COUNT,
        "order_send_count": ORDER_SEND_COUNT,
        "staging_dir": str(stage_path),
        "pulled_files": pulled_files,
        "node_status_path": str(status_out),
    }


# ---------------------------------------------------------------------------
# Fail-Closed Telemetry, NTP, Posture & Temporal Guards
# ---------------------------------------------------------------------------
def parse_ntp_offset_ms(status_payload: Mapping[str, Any]) -> float:
    """Parse finite NTP offset in milliseconds from `node_status` or `ntp_check` payload (fail-closed)."""
    if not isinstance(status_payload, Mapping):
        raise TelemetryPreflightError("NTP_PAYLOAD_INVALID: status_payload must be a mapping")

    ntp_check = status_payload.get("ntp_check")
    if isinstance(ntp_check, Mapping):
        if "ok" in ntp_check and ntp_check.get("ok") is not True:
            raise TelemetryPreflightError(f"NTP_CHECK_FAILED: ntp_check.ok={ntp_check.get('ok')!r}")
        raw_ms = ntp_check.get("offset_ms")
        val = parse_optional_finite_float(raw_ms, field_name="ntp_check.offset_ms")
        if val is None:
            raise TelemetryPreflightError("NTP_OFFSET_MISSING: ntp_check.offset_ms is None")
        return float(val)

    if "ntp_offset_ms" in status_payload and status_payload.get("ntp_offset_ms") not in (None, ""):
        val = parse_optional_finite_float(status_payload.get("ntp_offset_ms"), field_name="ntp_offset_ms")
        if val is None:
            raise TelemetryPreflightError("NTP_OFFSET_MISSING: ntp_offset_ms is blank")
        return float(val)

    raw_str = status_payload.get("ntp_offset")
    if isinstance(raw_str, bool) or raw_str is None:
        raise TelemetryPreflightError(f"NTP_OFFSET_MISSING: ntp_offset={raw_str!r}")
    if isinstance(raw_str, (int, float)):
        fv = float(raw_str)
        if not math.isfinite(fv):
            raise NonFiniteTelemetryError(f"NTP_OFFSET_NONFINITE: ntp_offset={raw_str!r}")
        return fv * 1000.0 if abs(fv) < 10.0 else fv

    s = str(raw_str).strip()
    if not s or s.lower() == "unknown":
        raise TelemetryPreflightError(f"NTP_OFFSET_UNAVAILABLE: ntp_offset={raw_str!r}")
    m_ms = _NTP_MS_RE.fullmatch(s)
    if m_ms is not None:
        val = float(m_ms.group(1))
        if not math.isfinite(val):
            raise NonFiniteTelemetryError(f"NTP_OFFSET_NONFINITE: {raw_str!r}")
        return val
    m_s = _NTP_SECONDS_RE.fullmatch(s)
    if m_s is not None:
        val = float(m_s.group(1)) * 1000.0
        if not math.isfinite(val):
            raise NonFiniteTelemetryError(f"NTP_OFFSET_NONFINITE: {raw_str!r}")
        return val
    raise TelemetryPreflightError(f"NTP_OFFSET_UNPARSEABLE: {raw_str!r}")


def _extract_first_present(sources: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> tuple[bool, Any]:
    for src in sources:
        for k in keys:
            if k in src and src[k] is not None and src[k] != "":
                return True, src[k]
    return False, None


def verify_readonly_posture_and_telemetry(
    status_payload: Mapping[str, Any],
    *,
    expected_login: int | None,
    expected_server: str | None,
    max_ntp_offset_ms: float = MAX_NTP_OFFSET_MS,
) -> dict[str, Any]:
    """Fail-closed check of NTP `< 1000 ms`, `expected_login`, `expected_server`, and `trade_allowed == False`."""
    if not isinstance(status_payload, Mapping):
        raise TelemetryPreflightError("STATUS_PAYLOAD_INVALID: expected mapping")

    if (
        expected_login is None
        or isinstance(expected_login, bool)
        or not isinstance(expected_login, int)
        or expected_login <= 0
    ):
        raise TelemetryPreflightError(
            f"EXPECTED_LOGIN_REQUIRED: expected_login must be a strict positive int, got {expected_login!r}"
        )
    if not isinstance(expected_server, str) or not expected_server.strip():
        raise TelemetryPreflightError(
            f"EXPECTED_SERVER_REQUIRED: expected_server must be a non-empty string, got {expected_server!r}"
        )
    exp_server_str = expected_server.strip()

    if (
        isinstance(max_ntp_offset_ms, bool)
        or not math.isfinite(float(max_ntp_offset_ms))
        or not (0.0 < float(max_ntp_offset_ms) <= MAX_NTP_OFFSET_MS)
    ):
        raise TelemetryPreflightError(
            f"INVALID_NTP_THRESHOLD: max_ntp_offset_ms must be in (0, {MAX_NTP_OFFSET_MS}], got {max_ntp_offset_ms!r}"
        )

    offset_ms = parse_ntp_offset_ms(status_payload)
    if abs(offset_ms) >= float(max_ntp_offset_ms):
        raise TelemetryPreflightError(
            f"NTP_OFFSET_BREACH: abs(ntp_offset_ms)={abs(offset_ms):.2f} ms >= {float(max_ntp_offset_ms):.1f} ms"
        )

    sub_sources: list[Mapping[str, Any]] = [status_payload]
    for nested_key in ("terminal_info", "account_info", "heartbeat", "posture"):
        nested = status_payload.get(nested_key)
        if isinstance(nested, Mapping):
            sub_sources.append(nested)

    # Check order_send_count == 0 everywhere present
    for src in sub_sources:
        if "order_send_count" in src and src["order_send_count"] is not None:
            osc = parse_optional_strict_int(src["order_send_count"], field_name="order_send_count")
            if osc != 0:
                raise ReadOnlyViolationError(f"NONZERO_ORDER_SEND_COUNT: observed order_send_count={osc} != 0")
        if "read_only" in src and src["read_only"] is not None:
            if src["read_only"] is not True:
                raise ReadOnlyViolationError(f"READ_ONLY_POSTURE_VIOLATION: read_only={src['read_only']!r}")

    has_login, raw_login = _extract_first_present(sub_sources, ("login", "account_login", "mt5_login"))
    if not has_login:
        raise TelemetryPreflightError("OBSERVED_LOGIN_MISSING: telemetry does not report account login")
    obs_login = parse_optional_strict_int(raw_login, field_name="observed_login")
    if obs_login is None or obs_login <= 0:
        raise TelemetryPreflightError(f"OBSERVED_LOGIN_INVALID: {raw_login!r}")
    if obs_login != expected_login:
        raise TelemetryPreflightError("LOGIN_MISMATCH: observed account login does not match expected_login")

    has_server, raw_server = _extract_first_present(sub_sources, ("server", "broker_server", "mt5_server"))
    if not has_server:
        raise TelemetryPreflightError("OBSERVED_SERVER_MISSING: telemetry does not report broker server")
    obs_server = str(raw_server).strip()
    if obs_server != exp_server_str:
        raise TelemetryPreflightError(
            f"SERVER_MISMATCH: observed server={obs_server!r} != expected_server={exp_server_str!r}"
        )

    # Strict read-only posture: trade_allowed MUST be explicitly boolean False
    found_trade_allowed = False
    trade_allowed_val: Any = None
    for src in sub_sources:
        if "trade_allowed" in src:
            found_trade_allowed = True
            trade_allowed_val = src["trade_allowed"]
            break
    if not found_trade_allowed or trade_allowed_val is not False:
        raise TelemetryPreflightError(
            f"TRADE_ALLOWED_MUST_BE_FALSE: observed trade_allowed={trade_allowed_val!r} "
            "(read-only harvest requires explicit trade_allowed == False)"
        )

    for src in sub_sources:
        if "connected" in src and src["connected"] is not None and src["connected"] is not True:
            raise TelemetryPreflightError(f"TERMINAL_DISCONNECTED: connected={src['connected']!r}")

    login_fp = hashlib.sha256(f"naqex-login:{expected_login}".encode()).hexdigest()[:12]
    return {
        "verified": True,
        "ntp_ok": True,
        "ntp_offset_ms": round(float(offset_ms), 3),
        "ntp_threshold_ms": float(max_ntp_offset_ms),
        "login_verified": True,
        "login_fingerprint": login_fp,
        "server_verified": True,
        "server": exp_server_str,
        "trade_allowed": False,
        "read_only_posture_verified": True,
        "order_send_count": ORDER_SEND_COUNT,
        "ssh_write_count": SSH_WRITE_COUNT,
    }


def _parse_utc_ts_strict(raw: Any, *, field_name: str = "utc_ts") -> float:
    if raw is None or isinstance(raw, bool):
        raise NonFiniteTelemetryError(f"{field_name} must be a valid finite timestamp, got {raw!r}")
    if isinstance(raw, (int, float)):
        fv = float(raw)
        if not math.isfinite(fv) or fv <= 0.0:
            raise NonFiniteTelemetryError(f"{field_name} must be finite > 0, got {raw!r}")
        return fv / 1000.0 if fv >= 1.0e12 else fv
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            raise NonFiniteTelemetryError(f"{field_name} cannot be blank")
        try:
            fv = float(s)
        except ValueError:
            fv = None
        if fv is not None:
            if not math.isfinite(fv) or fv <= 0.0:
                raise NonFiniteTelemetryError(f"{field_name} must be finite > 0, got {raw!r}")
            return fv / 1000.0 if fv >= 1.0e12 else fv
        m_dot = _DOT_DATE_RE.fullmatch(s)
        if m_dot is not None:
            s = f"{m_dot.group(1)}-{m_dot.group(2)}-{m_dot.group(3)}{m_dot.group(4)}"
        if s.endswith(("Z", "z")):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError as exc:
            raise NonFiniteTelemetryError(f"{field_name} invalid ISO timestamp {raw!r}") from exc
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        ts = float(dt.timestamp())
        if not math.isfinite(ts) or ts <= 0.0:
            raise NonFiniteTelemetryError(f"{field_name} resolved <= 0: {raw!r}")
        return ts
    raise NonFiniteTelemetryError(f"{field_name} unsupported timestamp type {type(raw).__name__}")


def enforce_harvest_temporal_guard(
    timestamps_sec: Iterable[float],
    *,
    run_mode: str = "dev",
    context: str = "free_trial_harvester",
) -> dict[str, Any]:
    """Fail-closed temporal/Holdout guard (`dev`: `< 2025-01-01`; `prospective_trial`: `>= 2026-12-01`)."""
    mode = str(run_mode or "").strip().lower()
    if mode not in ("dev", "prospective_trial"):
        raise HarvestGuardError(f"INVALID_RUN_MODE: expected 'dev' or 'prospective_trial', got {run_mode!r}")

    ts_list: list[float] = []
    for idx, raw_t in enumerate(timestamps_sec):
        t = _parse_utc_ts_strict(raw_t, field_name=f"{context}.ts[{idx}]")
        ts_list.append(t)

    if not ts_list:
        return {
            "run_mode": mode,
            "holdout_cutoff_day": HOLDOUT_CUTOFF_DAY,
            "holdout_v1_rows_analysed": 0,
            "checked_timestamps": 0,
            "min_utc": None,
            "max_utc": None,
        }

    int_ts = [int(math.floor(t)) for t in ts_list]
    if mode == "dev":
        # Strictly enforce < 2025-01-01T00:00:00Z via canonical holdout_guard (immune to python -O)
        enforce_pre_holdout_ts(int_ts, stop_ts=HOLDOUT_START_UTC_TS, context=context, allow_empty=True)
    else:
        # Prospective Holdout v2 Free Trial (>= 2026-12-01T00:00:00Z):
        # Strictly forbid any sealed Holdout v1 [2025-01-01, 2026-12-01) or pre-window contamination!
        v1_bad = [t for t in int_ts if HOLDOUT_START_UTC_TS <= t < PROSPECTIVE_TRIAL_START_UTC_TS]
        if v1_bad:
            raise HoldoutLockError(
                f"HOLDOUT_V1_CONTAMINATION [{context}]: detected {len(v1_bad)} timestamp(s) inside "
                f"sealed Holdout v1 [2025-01-01, 2026-12-01): sample={v1_bad[:3]}"
            )
        pre_window = [t for t in int_ts if t < PROSPECTIVE_TRIAL_START_UTC_TS]
        if pre_window:
            raise HoldoutLockError(
                f"PROSPECTIVE_WINDOW_VIOLATION [{context}]: detected {len(pre_window)} timestamp(s) "
                f"before {PROSPECTIVE_TRIAL_START_ISO}: sample={pre_window[:3]}"
            )

    min_t = min(ts_list)
    max_t = max(ts_list)
    return {
        "run_mode": mode,
        "holdout_cutoff_day": HOLDOUT_CUTOFF_DAY,
        "holdout_v1_rows_analysed": 0,
        "checked_timestamps": len(ts_list),
        "min_utc": datetime.fromtimestamp(min_t, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "max_utc": datetime.fromtimestamp(max_t, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _validate_row_finite_fields(row: Mapping[str, Any], *, context: str) -> None:
    for key in _SLIPPAGE_NUMERIC_KEYS:
        if key in row and row[key] not in (None, ""):
            try:
                parse_optional_finite_float(row[key], field_name=f"{context}.{key}")
            except ValueError as exc:
                raise NonFiniteTelemetryError(str(exc)) from exc


def _validate_row_login(row: Mapping[str, Any], *, expected_login: int, context: str) -> None:
    if "account_login" in row and row["account_login"] not in (None, ""):
        row_login = parse_optional_strict_int(row["account_login"], field_name=f"{context}.account_login")
        if row_login is not None and row_login != expected_login:
            raise TelemetryPreflightError(
                f"AUDIT_ROW_LOGIN_MISMATCH [{context}]: row account_login does not match expected_login"
            )


# ---------------------------------------------------------------------------
# Offline Fixture / Staging Directory Loaders
# ---------------------------------------------------------------------------
def _load_csv_dicts_strict(csv_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise HarvestGuardError(f"Empty CSV header in {csv_path.name}")
        for line_no, raw in enumerate(reader, start=2):
            if not raw or all(str(v or "").strip() == "" for v in raw.values()):
                continue
            row = dict(raw)
            _validate_row_finite_fields(row, context=f"{csv_path.name}:{line_no}")
            rows.append(row)
    return rows


def _load_json_rows_strict(
    json_path: Path,
    *,
    list_keys: Sequence[str] = ("deals", "trades", "rows"),
) -> list[dict[str, Any]]:
    def _reject_nonfinite(tok: str) -> Any:
        raise NonFiniteTelemetryError(f"Non-finite JSON constant {tok!r} forbidden in {json_path.name}")

    doc = json.loads(json_path.read_text(encoding="utf-8-sig"), parse_constant=_reject_nonfinite)
    if isinstance(doc, list):
        raw_list = doc
    elif isinstance(doc, Mapping):
        raw_list = []
        for k in list_keys:
            if isinstance(doc.get(k), list):
                raw_list = doc[k]
                break
    else:
        raise HarvestGuardError(f"Unsupported JSON rows structure in {json_path.name}")

    out: list[dict[str, Any]] = []
    for idx, item in enumerate(raw_list):
        if not isinstance(item, Mapping):
            raise HarvestGuardError(f"{json_path.name}[{idx}] must be a JSON object")
        row = dict(item)
        _validate_row_finite_fields(row, context=f"{json_path.name}[{idx}]")
        out.append(row)
    return out


def _discover_source_paths(source_path: Path) -> dict[str, Any]:
    """Resolve input files from a fixture/staging directory OR a JSON fixture manifest."""
    p = Path(source_path)
    if not p.exists():
        raise FileNotFoundError(f"Fixture/staging path not found: {p}")

    if p.is_file() and p.suffix.lower() == ".json":
        def _reject_nf(tok: str) -> Any:
            raise NonFiniteTelemetryError(f"Non-finite JSON constant {tok!r} in {p.name}")

        doc = json.loads(p.read_text(encoding="utf-8-sig"), parse_constant=_reject_nf)
        if not isinstance(doc, Mapping):
            raise HarvestGuardError(f"Fixture manifest must be a JSON object: {p.name}")
        base_dir = p.parent

        def _res_list(key: str) -> list[Path]:
            val = doc.get(key)
            if not val:
                return []
            if isinstance(val, str):
                return [(base_dir / val).resolve()]
            return [(base_dir / str(x)).resolve() for x in val]

        def _res_one(key: str) -> Path | None:
            val = doc.get(key)
            if not val:
                return None
            return (base_dir / str(val)).resolve()

        return {
            "status_payload": doc.get("node_status") if isinstance(doc.get("node_status"), Mapping) else None,
            "node_status_path": _res_one("node_status_path"),
            "exec_audit_paths": _res_list("exec_audit_paths"),
            "shadow_paths": _res_list("shadow_paths"),
            "blackbox_paths": _res_list("blackbox_paths"),
            "deals_paths": _res_list("deals_paths"),
            "expected_trades_path": _res_one("expected_python_trades_path"),
            "quote_tape_paths": _res_list("quote_tape_paths"),
            "symbol_specs_path": _res_one("symbol_specs_path"),
        }

    if not p.is_dir():
        raise HarvestGuardError(f"Fixture/staging path must be a directory or JSON manifest: {p}")

    node_status_path = next(
        (cand for cand in (p / "node_status.json", p / "telemetry.json") if cand.is_file()),
        None,
    )
    exec_audit_paths = sorted(p.glob("naqex_exec_audit*.csv"))
    shadow_paths = sorted(p.glob("naqex_*shadow*.csv"))
    blackbox_paths = sorted(p.glob("naqex_decision_blackbox_*.jsonl"))
    deals_paths = sorted(
        {
            *p.glob("*deals*.csv"),
            *p.glob("*deals*.json"),
            *p.glob("*statement*.csv"),
            *p.glob("*statement*.json"),
        }
    )
    expected_trades_path = next(
        (
            cand
            for cand in (
                p / "expected_python_trades.json",
                p / "expected_python_trades.csv",
            )
            if cand.is_file()
        ),
        None,
    )
    quote_tape_paths = sorted(
        {
            *p.glob("*quote*.csv"),
            *p.glob("*quote*.jsonl"),
            *p.glob("mt5_live_spread_log*.jsonl"),
            *p.glob("*nfp*.csv"),
            *p.glob("*cpi*.csv"),
        }
    )
    symbol_specs_path = next(
        (cand for cand in (p / "broker_symbol_specs.json", p / "symbol_specs.json") if cand.is_file()),
        None,
    )
    return {
        "status_payload": None,
        "node_status_path": node_status_path,
        "exec_audit_paths": exec_audit_paths,
        "shadow_paths": shadow_paths,
        "blackbox_paths": blackbox_paths,
        "deals_paths": deals_paths,
        "expected_trades_path": expected_trades_path,
        "quote_tape_paths": quote_tape_paths,
        "symbol_specs_path": symbol_specs_path,
    }


# ---------------------------------------------------------------------------
# Slippage Tail (P50/P90/P95/P99) & US100.cash SL Slippage vs 1.50x / 1.75x
# ---------------------------------------------------------------------------
def compute_slippage_tail_stats(
    values: Sequence[float],
    *,
    field_name: str = "adverse_slip_pts",
) -> dict[str, Any]:
    """Compute finite `P50 / P90 / P95 / P99` slippage tail statistics (fail-closed on NaN/Inf)."""
    cleaned: list[float] = []
    for idx, v in enumerate(values):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise NonFiniteTelemetryError(f"{field_name}[{idx}] must be numeric (not bool), got {v!r}")
        fv = float(v)
        if not math.isfinite(fv):
            raise NonFiniteTelemetryError(f"{field_name}[{idx}] must be finite (NaN/Inf forbidden), got {v!r}")
        cleaned.append(fv)

    if not cleaned:
        return {
            "count": 0,
            "mean": None,
            "min": None,
            "p50": None,
            "p90": None,
            "p95": None,
            "p99": None,
            "max": None,
        }

    arr = np.asarray(cleaned, dtype=np.float64)
    p50, p90, p95, p99 = np.percentile(arr, [50.0, 90.0, 95.0, 99.0])
    return {
        "count": len(cleaned),
        "mean": round(float(np.mean(arr)), 4),
        "min": round(float(np.min(arr)), 4),
        "p50": round(float(p50), 4),
        "p90": round(float(p90), 4),
        "p95": round(float(p95), 4),
        "p99": round(float(p99), 4),
        "max": round(float(np.max(arr)), 4),
    }


def _extract_us100_sl_slip_pts(
    positions: Sequence[Mapping[str, Any]],
    raw_deals: Sequence[Mapping[str, Any]],
) -> list[float]:
    """Extract strictly finite adverse SL exit slippage in broker points for `US100.cash`."""
    sl_vals: list[float] = []
    seen_pos_ids: set[str] = set()

    # Index canonical position side and entry SL price so closing-leg deal sides never invert sign
    pos_side_by_id: dict[str, str] = {}
    pos_sl_by_id: dict[str, float] = {}
    for pos in positions:
        pid = str(pos.get("position_id") or "").strip()
        if pid:
            pos_side_by_id[pid] = str(pos.get("side") or "").strip().upper()
            psl = parse_optional_finite_float(pos.get("sl_price"), field_name="position.sl_price")
            if psl is not None and psl > 0.0:
                pos_sl_by_id[pid] = psl

    # Prefer explicit SL exit deals when present (supports explicit sl_slippage_pts or sl_price vs fill_price)
    for idx, d in enumerate(raw_deals):
        sym = normalize_symbol_alias(str(d.get("canonical_symbol") or d.get("symbol") or ""))
        if sym != "US100":
            continue
        ev = str(d.get("event_type") or "").strip().upper()
        reason = str(d.get("exit_reason") or d.get("reason") or "").strip().upper()
        comment = str(d.get("comment") or "").strip().upper()
        is_sl_exit = ev == "SL_HIT" or reason == "SL" or "[SL" in comment or "SL_HIT" in comment
        if not is_sl_exit:
            continue

        pos_id = str(d.get("position_id") or d.get("POSITION_IDENTIFIER") or "").strip()
        if "sl_slippage_pts" in d and d["sl_slippage_pts"] not in (None, ""):
            sv = parse_optional_finite_float(d["sl_slippage_pts"], field_name=f"deal[{idx}].sl_slippage_pts")
            if sv is not None:
                sl_vals.append(float(sv))
                if pos_id:
                    seen_pos_ids.add(pos_id)
                continue

        pt = point_size_for_symbol("US100.cash")
        sl_px = parse_optional_finite_float(
            d.get("sl_price") if d.get("sl_price") not in (None, "") else d.get("signal_price"),
            field_name=f"deal[{idx}].sl_price",
        )
        if (sl_px is None or sl_px <= 0.0) and pos_id in pos_sl_by_id:
            sl_px = pos_sl_by_id[pos_id]
        fill_px = parse_optional_finite_float(
            d.get("fill_price") if d.get("fill_price") not in (None, "") else d.get("exit_price"),
            field_name=f"deal[{idx}].fill_price",
        )
        side = str(d.get("position_side") or pos_side_by_id.get(pos_id) or d.get("side") or "").strip().upper()
        if sl_px is not None and fill_px is not None and sl_px > 0.0 and fill_px > 0.0 and pt > 0.0:
            # BUY position SL fills below sl_price -> adverse = (sl_px - fill_px)/pt
            # SELL position SL fills above sl_price -> adverse = (fill_px - sl_px)/pt
            if side in ("BUY", "LONG", "+1", "1"):
                sl_vals.append((sl_px - fill_px) / pt)
                if pos_id:
                    seen_pos_ids.add(pos_id)
            elif side in ("SELL", "SHORT", "-1"):
                sl_vals.append((fill_px - sl_px) / pt)
                if pos_id:
                    seen_pos_ids.add(pos_id)

    # Supplement from aggregated closed positions where exit_reason == "SL" and not already captured
    for idx, pos in enumerate(positions):
        sym = normalize_symbol_alias(str(pos.get("canonical_symbol") or pos.get("symbol") or ""))
        if sym != "US100":
            continue
        pos_id = str(pos.get("position_id") or "").strip()
        if pos_id and pos_id in seen_pos_ids:
            continue
        if str(pos.get("exit_reason") or "").strip().upper() != "SL":
            continue
        sl_px = parse_optional_finite_float(pos.get("sl_price"), field_name=f"position[{idx}].sl_price")
        exit_px = parse_optional_finite_float(pos.get("exit_price"), field_name=f"position[{idx}].exit_price")
        side = str(pos.get("side") or "").strip().upper()
        pt = point_size_for_symbol("US100.cash")
        if sl_px is not None and exit_px is not None and sl_px > 0.0 and exit_px > 0.0 and pt > 0.0:
            if side == "BUY":
                sl_vals.append((sl_px - exit_px) / pt)
            elif side == "SELL":
                sl_vals.append((exit_px - sl_px) / pt)

    return sl_vals


def compute_us100_sl_slippage_gate(
    positions: Sequence[Mapping[str, Any]],
    raw_deals: Sequence[Mapping[str, Any]] = (),
    *,
    base_sl_slip_pts: float = US100_BASE_SL_SLIP_PTS,
    pass_mult: float = US100_PASS_SLIP_MULT,
    kill_mult: float = US100_KILL_SLIP_MULT,
) -> dict[str, Any]:
    """Evaluate `US100.cash` SL exit slippage against locked `1.50x` (PASS) and `1.75x` (KILL) ceilings."""
    if (
        isinstance(base_sl_slip_pts, bool)
        or not math.isfinite(float(base_sl_slip_pts))
        or float(base_sl_slip_pts) <= 0.0
    ):
        raise NonFiniteTelemetryError(f"base_sl_slip_pts must be finite > 0, got {base_sl_slip_pts!r}")

    sl_pts = _extract_us100_sl_slip_pts(positions, raw_deals)
    tail_pts = compute_slippage_tail_stats(sl_pts, field_name="us100_sl_slippage_pts")

    if tail_pts["count"] == 0:
        return {
            "symbol": "US100.cash",
            "canonical_symbol": "US100",
            "base_sl_slip_pts": float(base_sl_slip_pts),
            "pass_mult_threshold": float(pass_mult),
            "kill_mult_threshold": float(kill_mult),
            "sl_sample_count": 0,
            "slippage_pts_tail": tail_pts,
            "multipliers": {
                "mean_mult": None,
                "p50_mult": None,
                "p90_mult": None,
                "p95_mult": None,
                "p99_mult": None,
                "max_mult": None,
                "effective_mult": None,
            },
            "verdict": "NO_US100_SL_SAMPLES",
            "within_1_50x": None,
            "breaches_1_75x_kill": False,
        }

    base = float(base_sl_slip_pts)
    mean_m = round(float(tail_pts["mean"]) / base, 4)
    p50_m = round(float(tail_pts["p50"]) / base, 4)
    p90_m = round(float(tail_pts["p90"]) / base, 4)
    p95_m = round(float(tail_pts["p95"]) / base, 4)
    p99_m = round(float(tail_pts["p99"]) / base, 4)
    max_m = round(float(tail_pts["max"]) / base, 4)
    eff_m = max(mean_m, p50_m)

    if eff_m > float(kill_mult):
        verdict = "KILL_EXCEEDS_1_75X"
    elif eff_m > float(pass_mult):
        verdict = "AMBER_BETWEEN_1_50X_AND_1_75X"
    else:
        verdict = "PASS_WITHIN_1_50X"

    return {
        "symbol": "US100.cash",
        "canonical_symbol": "US100",
        "base_sl_slip_pts": base,
        "pass_mult_threshold": float(pass_mult),
        "kill_mult_threshold": float(kill_mult),
        "sl_sample_count": tail_pts["count"],
        "slippage_pts_tail": tail_pts,
        "multipliers": {
            "mean_mult": mean_m,
            "p50_mult": p50_m,
            "p90_mult": p90_m,
            "p95_mult": p95_m,
            "p99_mult": p99_m,
            "max_mult": max_m,
            "effective_mult": eff_m,
        },
        "verdict": verdict,
        "within_1_50x": bool(eff_m <= float(pass_mult)),
        "breaches_1_75x_kill": bool(eff_m > float(kill_mult)),
    }


def _collect_all_slippage_tails(
    positions: Sequence[Mapping[str, Any]],
    fill_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build overall and per-symbol slippage tail (`P50/P90/P95/P99`) in broker points and bps."""
    pts_all: list[float] = []
    bps_all: list[float] = []
    by_sym_pts: dict[str, list[float]] = {}

    source_rows = list(positions) if positions else list(fill_rows)
    for idx, rec in enumerate(source_rows):
        sym = normalize_symbol_alias(str(rec.get("canonical_symbol") or rec.get("symbol") or ""))
        slip_pts = parse_optional_finite_float(rec.get("adverse_slip_pts"), field_name=f"row[{idx}].adverse_slip_pts")
        if slip_pts is None:
            sig_px = parse_optional_finite_float(rec.get("signal_price"), field_name=f"row[{idx}].signal_price")
            fill_px = parse_optional_finite_float(
                rec.get("entry_price") if rec.get("entry_price") not in (None, "") else rec.get("fill_price"),
                field_name=f"row[{idx}].fill_price",
            )
            pt = point_size_for_symbol(sym or str(rec.get("symbol") or ""))
            side = str(rec.get("side") or "").strip().upper()
            sign = 1.0 if side in ("BUY", "LONG", "+1", "1") else (-1.0 if side in ("SELL", "SHORT", "-1") else 0.0)
            if sig_px and fill_px and pt > 0.0 and sign != 0.0:
                slip_pts = sign * (fill_px - sig_px) / pt
        if slip_pts is None:
            continue
        pts_all.append(float(slip_pts))
        if sym:
            by_sym_pts.setdefault(sym, []).append(float(slip_pts))

        sig_px = parse_optional_finite_float(rec.get("signal_price"), field_name=f"row[{idx}].signal_price")
        pt = point_size_for_symbol(sym or str(rec.get("symbol") or ""))
        if sig_px is not None and sig_px > 0.0 and pt > 0.0:
            bps_all.append((float(slip_pts) * pt / sig_px) * 10_000.0)

    return {
        "overall_adverse_slip_pts": compute_slippage_tail_stats(pts_all, field_name="overall_adverse_slip_pts"),
        "overall_adverse_slip_bps": compute_slippage_tail_stats(bps_all, field_name="overall_adverse_slip_bps"),
        "by_symbol_adverse_slip_pts": {
            s: compute_slippage_tail_stats(vals, field_name=f"{s}.adverse_slip_pts")
            for s, vals in sorted(by_sym_pts.items())
        },
    }


def _merge_audit_and_deal_legs(
    enriched_audit_rows: Sequence[Mapping[str, Any]],
    deal_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Combine enriched audit fill rows and broker deal export legs without duplicating deal_ids."""
    combined: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str]] = set()

    for row in enriched_audit_rows:
        ev = str(row.get("event_type") or "").strip().upper()
        if ev in NON_FILL_EVENT_TYPES:
            continue
        pos_id = str(row.get("position_id") or "").strip()
        deal_id = str(row.get("deal_id") or row.get("ticket") or "").strip()
        leg = "EXIT" if ev in EXIT_EVENT_TYPES else "ENTRY"
        if deal_id:
            seen_keys.add((pos_id, deal_id, leg))
        combined.append(dict(row))

    for row in deal_rows:
        ev = str(row.get("event_type") or "").strip().upper()
        if ev in NON_FILL_EVENT_TYPES:
            continue
        pos_id = str(row.get("position_id") or row.get("POSITION_IDENTIFIER") or "").strip()
        deal_id = str(row.get("deal_id") or row.get("deal") or row.get("ticket") or "").strip()
        leg_raw = str(row.get("leg") or row.get("deal_entry") or "").strip().upper()
        leg = "EXIT" if (ev in EXIT_EVENT_TYPES or leg_raw in ("EXIT", "OUT", "DEAL_ENTRY_OUT")) else "ENTRY"
        if deal_id and (pos_id, deal_id, leg) in seen_keys:
            continue
        if deal_id:
            seen_keys.add((pos_id, deal_id, leg))
        rec = dict(row)
        if not rec.get("event_type"):
            is_sl_reason = str(rec.get("exit_reason") or "").upper() == "SL"
            rec["event_type"] = "SL_HIT" if is_sl_reason else ("EXIT" if leg == "EXIT" else "ORDER_FILL")
        combined.append(rec)

    return combined


def _derive_expected_from_shadow(shadow_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for s in shadow_rows:
        ev = str(s.get("event_type") or "").strip().upper()
        if ev in ("SHADOW_INTENT", "DRYRUN_SIGNAL", "DRYRUN_SIGNAL_V103"):
            out.append(
                {
                    "symbol": s.get("symbol"),
                    "side": s.get("side"),
                    "utc_ts": s.get("utc_ts"),
                    "magic": s.get("magic", 0),
                    "signal_id": s.get("signal_id") or s.get("intent_id") or "",
                    "entry_price": s.get("expected_entry"),
                    "sl_price": s.get("expected_sl"),
                    "lots": s.get("expected_lot"),
                }
            )
    return out


def _evaluate_go_nogo_decision(
    *,
    telemetry: Mapping[str, Any],
    ops6_report: Mapping[str, Any],
    tca_report: Mapping[str, Any],
    us100_sl_gate: Mapping[str, Any],
    positions_count: int,
    min_trade_match_rate: float = MIN_GO_TRADE_MATCH_RATE,
) -> dict[str, Any]:
    """Synthesize the `12-13/12` GO / NO-GO decision gate from verified parity, TCA, and US100 SL telemetry."""
    parity = ops6_report["parity_report"]
    pcounts = parity["counts"]
    ghost_trades = int(pcounts.get(PARITY_BOT_BUG_GHOST_TRADE, 0))
    missed_trades = int(pcounts.get(PARITY_BOT_BUG_MISSED_TRADE, 0))
    lot_sl_drift = int(pcounts.get(PARITY_LOT_OR_SL_DRIFT, 0))
    friction_drift = int(pcounts.get(PARITY_EXECUTION_FRICTION_DRIFT, 0))
    match_rate = float(parity.get("trade_match_rate", 0.0))
    actionable_expected = int(parity.get("actionable_expected_count", 0))
    swap_violations = int(tca_report.get("swap_violations", 0))
    tca_verdict = str(tca_report.get("verdict") or "")

    hard_blockers: list[str] = []
    amber_warnings: list[str] = []

    if not telemetry.get("verified", False):
        hard_blockers.append("TELEMETRY_PREFLIGHT_UNVERIFIED")
    if ghost_trades > 0:
        hard_blockers.append(f"GHOST_TRADES_DETECTED:{ghost_trades}")
    if missed_trades > 0:
        hard_blockers.append(f"MISSED_TRADES_DETECTED:{missed_trades}")
    if lot_sl_drift > 0:
        hard_blockers.append(f"LOT_OR_SL_DRIFT_DETECTED:{lot_sl_drift}")
    if actionable_expected > 0 and match_rate < float(min_trade_match_rate) - 1e-12:
        hard_blockers.append(f"TRADE_MATCH_RATE_BELOW_GATE:{match_rate:.4f}<{float(min_trade_match_rate):.4f}")
    if swap_violations > 0:
        hard_blockers.append(f"SWAP_NONZERO_VIOLATIONS:{swap_violations}")
    if tca_verdict.startswith("RED_"):
        hard_blockers.append(f"TCA_RED_VERDICT:{tca_verdict}")
    if us100_sl_gate.get("verdict") == "KILL_EXCEEDS_1_75X":
        hard_blockers.append(
            f"US100_SL_SLIPPAGE_KILL:{us100_sl_gate['multipliers']['effective_mult']}x>1.75x"
        )

    if us100_sl_gate.get("verdict") == "AMBER_BETWEEN_1_50X_AND_1_75X":
        amber_warnings.append(
            f"US100_SL_SLIPPAGE_AMBER:{us100_sl_gate['multipliers']['effective_mult']}x_in_(1.50x,1.75x]"
        )
    elif us100_sl_gate.get("verdict") == "NO_US100_SL_SAMPLES":
        amber_warnings.append("US100_SL_SAMPLES_ZERO")
    if tca_verdict == "AMBER_WATCH":
        amber_warnings.append("TCA_AMBER_WATCH")
    if friction_drift > 0:
        amber_warnings.append(f"PARITY_FRICTION_DRIFT_COUNT:{friction_drift}")
    if positions_count == 0:
        amber_warnings.append("ZERO_EXECUTED_POSITIONS")

    if hard_blockers:
        decision = "NO_GO"
    elif amber_warnings:
        decision = "CONDITIONAL_REVIEW"
    else:
        decision = "GO_READY"

    return {
        "decision": decision,
        "decision_window": "2026-12-12..2026-12-13",
        "trade_match_rate": round(match_rate, 6),
        "ghost_trades": ghost_trades,
        "missed_trades": missed_trades,
        "lot_or_sl_drift": lot_sl_drift,
        "friction_drift": friction_drift,
        "legitimate_guard_blocks": int(pcounts.get(PARITY_LEGITIMATE_GUARD_BLOCK, 0)),
        "match_clean_count": int(pcounts.get(PARITY_MATCH_CLEAN, 0)),
        "swap_violations": swap_violations,
        "us100_sl_verdict": us100_sl_gate.get("verdict"),
        "us100_sl_effective_mult": us100_sl_gate["multipliers"]["effective_mult"],
        "hard_blockers": hard_blockers,
        "amber_warnings": amber_warnings,
    }


# ---------------------------------------------------------------------------
# End-to-End Read-Only Forensics Pipeline
# ---------------------------------------------------------------------------
def harvest_free_trial_forensics(
    *,
    source_dir_or_manifest: Path | str,
    expected_login: int | None,
    expected_server: str | None,
    account_alias: str = "FTMO_FREE_TRIAL_V101",
    period_label: str = "FTMO_FREE_TRIAL_08_12",
    run_mode: str = "dev",
    vault_root: Path | str | None = None,
    hot_m1_cache_dir: Path | str | None = None,
    holdout_dir: Path | str | None = None,
    max_ntp_offset_ms: float = MAX_NTP_OFFSET_MS,
    us100_base_sl_slip_pts: float = US100_BASE_SL_SLIP_PTS,
    output_json: Path | str | None = None,
    output_md: Path | str | None = None,
) -> dict[str, Any]:
    """Run complete fail-closed read-only Free-Trial Forensics on pulled or offline fixture artifacts."""
    sources = _discover_source_paths(Path(source_dir_or_manifest))

    # 1. Load & verify node telemetry + read-only posture fail-closed
    status_payload = sources["status_payload"]
    if status_payload is None:
        ns_path: Path | None = sources["node_status_path"]
        if ns_path is None or not ns_path.is_file():
            raise TelemetryPreflightError(
                "NODE_STATUS_MISSING: node_status.json / telemetry.json is required for NTP & posture verification"
            )

        def _reject_nf(tok: str) -> Any:
            raise NonFiniteTelemetryError(f"Non-finite JSON constant {tok!r} in {ns_path.name}")

        status_payload = json.loads(ns_path.read_text(encoding="utf-8-sig"), parse_constant=_reject_nf)

    verified_telemetry = verify_readonly_posture_and_telemetry(
        status_payload,
        expected_login=expected_login,
        expected_server=expected_server,
        max_ntp_offset_ms=max_ntp_offset_ms,
    )
    exp_login_int = int(expected_login)  # type: ignore[arg-type]

    # 2. Load audit CSVs, shadow CSVs, blackbox JSONLs, deals & expected Python trades (fail-closed on NaN)
    audit_rows: list[dict[str, Any]] = []
    for ap in sources["exec_audit_paths"]:
        # Pre-scan raw CSV for non-finite extra slippage columns before canonical parsing
        _load_csv_dicts_strict(ap)
        loaded = load_exec_audit_records(ap)
        for idx, row in enumerate(loaded):
            _validate_row_finite_fields(row, context=f"{ap.name}[{idx}]")
            _validate_row_login(row, expected_login=exp_login_int, context=f"{ap.name}[{idx}]")
        audit_rows.extend(loaded)

    shadow_rows: list[dict[str, Any]] = []
    for sp in sources["shadow_paths"]:
        _load_csv_dicts_strict(sp)
        loaded_sh = load_v103_shadow_csv(sp)
        for idx, row in enumerate(loaded_sh):
            _validate_row_finite_fields(row, context=f"{sp.name}[{idx}]")
            _validate_row_login(row, expected_login=exp_login_int, context=f"{sp.name}[{idx}]")
        shadow_rows.extend(loaded_sh)

    blackbox_rows: list[dict[str, Any]] = []
    for bp in sources["blackbox_paths"]:
        loaded_bb = load_decision_blackbox_jsonl(bp, allow_truncated_tail=False)
        for idx, row in enumerate(loaded_bb):
            _validate_row_finite_fields(row, context=f"{bp.name}[{idx}]")
        blackbox_rows.extend(loaded_bb)

    deal_rows: list[dict[str, Any]] = []
    for dp in sources["deals_paths"]:
        loaded_dl = _load_csv_dicts_strict(dp) if dp.suffix.lower() == ".csv" else _load_json_rows_strict(dp)
        for idx, row in enumerate(loaded_dl):
            _validate_row_login(row, expected_login=exp_login_int, context=f"{dp.name}[{idx}]")
        deal_rows.extend(loaded_dl)

    expected_trades: list[dict[str, Any]] = []
    expected_source = "none"
    exp_path: Path | None = sources["expected_trades_path"]
    if exp_path is not None:
        expected_trades = (
            _load_csv_dicts_strict(exp_path)
            if exp_path.suffix.lower() == ".csv"
            else _load_json_rows_strict(exp_path, list_keys=("trades", "expected_python_trades", "signals"))
        )
        expected_source = exp_path.name
    elif shadow_rows:
        expected_trades = _derive_expected_from_shadow(shadow_rows)
        expected_source = "shadow_csv_derived"

    # 3. Collect ALL timestamps across all inputs and enforce Holdout / Temporal Guard BEFORE analysis
    all_timestamps: list[float] = []
    for collection_name, rows in (
        ("exec_audit", audit_rows),
        ("shadow", shadow_rows),
        ("blackbox", blackbox_rows),
        ("deals", deal_rows),
        ("expected_python_trades", expected_trades),
    ):
        for idx, row in enumerate(rows):
            for ts_key in ("utc_ts", "entry_utc_ts", "exit_utc_ts", "close_time", "utc_time"):
                if row.get(ts_key) not in (None, ""):
                    ts_val = _parse_utc_ts_strict(row[ts_key], field_name=f"{collection_name}[{idx}].{ts_key}")
                    all_timestamps.append(ts_val)

    quote_tape_paths: list[Path] = list(sources["quote_tape_paths"])
    raw_quote_ticks: list[dict[str, Any]] = []
    for qp in quote_tape_paths:
        ticks = load_broker_quote_tape(qp, deduplicate=False)
        for tk in ticks:
            all_timestamps.append(float(tk["utc_ts"]))
        raw_quote_ticks.extend(ticks)

    temporal_guard = enforce_harvest_temporal_guard(
        all_timestamps,
        run_mode=run_mode,
        context=f"free_trial_harvester:{account_alias}",
    )

    # 4. Ingest broker quote tape into isolated live-vault (if provided) via live_broker_tape_ingestor
    tape_vault_summary: dict[str, Any] | None = None
    m1_bars_by_symbol: dict[str, list[dict[str, Any]]] | None = None
    if quote_tape_paths:
        eff_vault_root = DEFAULT_LIVE_VAULT_ROOT if vault_root is None else Path(vault_root)
        ingest_res = ingest_live_broker_tape(
            account_alias=account_alias,
            quote_tape_paths=quote_tape_paths,
            symbol_specs_path=sources["symbol_specs_path"],
            vault_root=eff_vault_root,
            hot_m1_cache_dir=hot_m1_cache_dir,
            holdout_dir=holdout_dir,
            write_m1_bars=True,
        )
        manifest_check = verify_live_vault_manifest(ingest_res["account_vault_dir"])
        if not manifest_check["valid"]:
            raise HarvestGuardError(f"LIVE_VAULT_MANIFEST_INVALID: {manifest_check['mismatches']}")
        isolation_check = verify_zero_cache_contamination(
            ingest_res["account_vault_dir"],
            hot_m1_cache_dir=hot_m1_cache_dir,
            holdout_dir=holdout_dir,
        )
        if not isolation_check["clean"]:
            raise HarvestGuardError(f"LIVE_VAULT_CONTAMINATION_DETECTED: {isolation_check}")
        m1_bars_by_symbol = ingest_res["m1_bars_by_symbol"]
        tape_vault_summary = {
            "ingested": True,
            "ticks_count": int(ingest_res["ticks_count"]),
            "symbols_ingested": list(ingest_res["manifest"]["symbols_ingested"]),
            "manifest_report_sha256": manifest_check["report_sha256"],
            "manifest_verified": True,
            "checked_files": int(manifest_check["checked_files"]),
            "zero_cache_contamination": True,
        }

    # 5. Enrich audit rows with broker deal/statement export & run canonical TCA gate
    enrichment_stats: dict[str, int] = {
        "matched_rows": 0,
        "unmatched_rows": 0,
        "swap_enriched_count": 0,
        "pnl_enriched_count": 0,
    }
    if audit_rows and deal_rows:
        enriched_audit, enrichment_stats = enrich_audit_rows_with_statement(audit_rows, deal_rows)
    else:
        enriched_audit = list(audit_rows)

    combined_deals = _merge_audit_and_deal_legs(enriched_audit, deal_rows)

    # Validate TCA post-reconcile across BOTH audit rows and merged broker deals (NaN/Inf, FILL_UNRESOLVED, swap)
    tca_input_raw = enriched_audit if enriched_audit else combined_deals
    tca_input: list[dict[str, Any]] = []
    for raw_r in tca_input_raw:
        if all(k in raw_r for k in ("signal_price", "fill_price", "sl_price", "spread_pts", "latency_ms")):
            tca_input.append(dict(raw_r))
        else:
            tca_input.append(parse_exec_audit_row(raw_r, require_core_fields=False))

    if combined_deals:
        validate_tca_post_reconcile(combined_deals, require_zero_swap=False, swap_tolerance_usd=0.0)
    if tca_input:
        validate_tca_post_reconcile(tca_input, require_zero_swap=False, swap_tolerance_usd=0.0)
    tca_report = compute_tca_report(
        tca_input,
        quote_series=raw_quote_ticks if raw_quote_ticks else None,
        require_zero_swap_raise=False,
        enforce_post_reconcile=True,
    )

    # 6. Aggregate positions & check aggregated position-level swap violations too
    positions = aggregate_mt5_deals_by_position(combined_deals)
    pos_swap_violations = sum(
        1 for pos in positions if pos.get("swap_usd") is not None and abs(float(pos["swap_usd"])) > 0.0
    )
    if pos_swap_violations > int(tca_report.get("swap_violations", 0)):
        tca_report = dict(tca_report)
        tca_report["swap_violations"] = pos_swap_violations
        tca_report["verdict"] = "RED_SWAP_VIOLATION"
        tca_report["flags"] = list(tca_report.get("flags") or []) + [
            f"{pos_swap_violations} aggregated position(s) carried non-zero swap (violates swap=0 contract)"
        ]

    guard_records = list(blackbox_rows) + list(shadow_rows) + [
        r for r in audit_rows if str(r.get("event_type") or "").strip().upper() in NON_FILL_EVENT_TYPES
    ]
    ops6_report = build_weekly_forensics_report(
        expected_python_trades=expected_trades,
        actual_mt5_trades=positions,
        decision_blackbox=guard_records,
        broker_tape_by_symbol=m1_bars_by_symbol,
        tca_report=tca_report,
        ops_report={"status": "OK", "alerts": []},
        account_alias=account_alias,
        period_label=period_label,
    )

    # 7. Slippage Tail (P50/P90/P95/P99) & US100.cash SL Slippage vs 1.50x / 1.75x
    fill_only_rows = [
        r for r in combined_deals if str(r.get("event_type") or "").strip().upper() in VALID_FILL_EVENT_TYPES
    ]
    slippage_tail = _collect_all_slippage_tails(positions, fill_only_rows)
    us100_sl_gate = compute_us100_sl_slippage_gate(
        positions,
        combined_deals,
        base_sl_slip_pts=us100_base_sl_slip_pts,
        pass_mult=US100_PASS_SLIP_MULT,
        kill_mult=US100_KILL_SLIP_MULT,
    )

    # 8. Synthesize 12-13/12 GO / NO-GO Decision & OPSEC-clean Forensics Bundle
    go_nogo = _evaluate_go_nogo_decision(
        telemetry=verified_telemetry,
        ops6_report=ops6_report,
        tca_report=tca_report,
        us100_sl_gate=us100_sl_gate,
        positions_count=len(positions),
    )

    bundle: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "account_alias": account_alias,
        "period_label": period_label,
        "hard_invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "ssh_write_count": SSH_WRITE_COUNT,
            "holdout_v1_rows_analysed": 0,
            "read_only_harvest": True,
        },
        "telemetry_posture": verified_telemetry,
        "temporal_guard": temporal_guard,
        "inputs_summary": {
            "exec_audit_files": [p.name for p in sources["exec_audit_paths"]],
            "shadow_files": [p.name for p in sources["shadow_paths"]],
            "blackbox_files": [p.name for p in sources["blackbox_paths"]],
            "deals_files": [p.name for p in sources["deals_paths"]],
            "quote_tape_files": [p.name for p in quote_tape_paths],
            "expected_trades_source": expected_source,
            "audit_rows_count": len(audit_rows),
            "shadow_rows_count": len(shadow_rows),
            "blackbox_rows_count": len(blackbox_rows),
            "deal_rows_count": len(deal_rows),
            "aggregated_positions_count": len(positions),
            "expected_python_trades_count": len(expected_trades),
            "statement_enrichment": enrichment_stats,
        },
        "live_broker_tape_vault": tape_vault_summary,
        "slippage_tail": slippage_tail,
        "us100_sl_slippage_gate": us100_sl_gate,
        "tca_report": tca_report,
        "ops6_forensics": ops6_report,
        "go_nogo_decision": go_nogo,
    }

    if output_json is not None:
        receipt = write_atomic_sha256_json(output_json, bundle)
        bundle["report_sha256"] = receipt["report_sha256"]
    else:
        bundle["report_sha256"] = canonical_payload_sha256(bundle)

    if output_md is not None:
        md_text = render_weekly_forensics_markdown(ops6_report)
        atomic_write_text(Path(output_md), md_text, encoding="utf-8", newline="\n")

    return bundle


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------
def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Strictly Read-Only FTMO Free-Trial Forensics Harvester (OrderSend=0, 0 SSH writes)."
    )
    src_group = parser.add_mutually_exclusive_group(required=True)
    src_group.add_argument(
        "--offline-fixture",
        type=Path,
        default=None,
        help="Local fixture directory or JSON manifest for deterministic offline/CI forensics (zero SSH).",
    )
    src_group.add_argument(
        "--remote-pull",
        action="store_true",
        help="Pull read-only artifacts via allowlisted SSH alias (naqex-node1-lan -> naqex-node1-ts).",
    )
    parser.add_argument("--host", type=str, default=None, help="Explicit allowlisted SSH alias (optional).")
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=WORKSPACE_ROOT / ".runtime" / "live-vault" / "staging_free_trial",
        help="Local staging directory for --remote-pull artifacts.",
    )
    parser.add_argument("--expected-login", type=int, required=True, help="Expected MT5 account login (fail-closed).")
    parser.add_argument("--expected-server", type=str, required=True, help="Expected MT5 broker server (fail-closed).")
    parser.add_argument("--account-alias", type=str, default="FTMO_FREE_TRIAL_V101")
    parser.add_argument("--period-label", type=str, default="FTMO_FREE_TRIAL_08_12")
    parser.add_argument(
        "--run-mode",
        choices=("dev", "prospective_trial"),
        default="dev",
        help="Temporal/Holdout enforcement mode ('dev': < 2025-01-01; 'prospective_trial': >= 2026-12-01).",
    )
    parser.add_argument("--vault-root", type=Path, default=None, help="Isolated live-vault root directory.")
    parser.add_argument("--us100-base-sl-slip-pts", type=float, default=US100_BASE_SL_SLIP_PTS)
    parser.add_argument("--output-json", type=Path, default=None, help="Optional output path for SHA-256 JSON bundle.")
    parser.add_argument("--output-md", type=Path, default=None, help="Optional output path for OPS-6 Markdown summary.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        if args.remote_pull:
            pull_meta = pull_readonly_trial_artifacts(args.staging_dir, host=args.host)
            src_dir = Path(pull_meta["staging_dir"])
        else:
            src_dir = Path(args.offline_fixture)

        bundle = harvest_free_trial_forensics(
            source_dir_or_manifest=src_dir,
            expected_login=args.expected_login,
            expected_server=args.expected_server,
            account_alias=args.account_alias,
            period_label=args.period_label,
            run_mode=args.run_mode,
            vault_root=args.vault_root,
            us100_base_sl_slip_pts=args.us100_base_sl_slip_pts,
            output_json=args.output_json,
            output_md=args.output_md,
        )
        print(json.dumps(bundle, indent=2, ensure_ascii=False))
        return 0
    except (HarvestGuardError, HoldoutLockError, ValueError, FileNotFoundError, RuntimeError) as exc:
        err_payload = {
            "schema": SCHEMA_VERSION,
            "status": "FAIL_CLOSED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "order_send_count": ORDER_SEND_COUNT,
            "ssh_write_count": SSH_WRITE_COUNT,
        }
        print(json.dumps(err_payload, indent=2, ensure_ascii=False), file=sys.stderr)
        return 1


__all__ = [
    "ALLOWED_SSH_HOST_ALIASES",
    "DEFAULT_REMOTE_FILES_DIR",
    "DEFAULT_SSH_HOSTS",
    "MAX_NTP_OFFSET_MS",
    "MIN_GO_TRADE_MATCH_RATE",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PROSPECTIVE_TRIAL_START_ISO",
    "PROSPECTIVE_TRIAL_START_UTC_TS",
    "READONLY_NODE_CTL_ACTIONS",
    "SCHEMA_VERSION",
    "SSH_WRITE_COUNT",
    "US100_BASE_SL_SLIP_PTS",
    "US100_KILL_SLIP_MULT",
    "US100_PASS_SLIP_MULT",
    "HarvestGuardError",
    "NonFiniteTelemetryError",
    "ReadOnlyViolationError",
    "TelemetryPreflightError",
    "build_arg_parser",
    "compute_slippage_tail_stats",
    "compute_us100_sl_slippage_gate",
    "enforce_harvest_temporal_guard",
    "harvest_free_trial_forensics",
    "main",
    "parse_ntp_offset_ms",
    "pull_readonly_trial_artifacts",
    "run_readonly_node_probe",
    "run_readonly_scp_pull",
    "run_readonly_ssh_list_files",
    "validate_readonly_scp_pull",
    "validate_readonly_ssh_command",
    "validate_ssh_host_alias",
    "verify_readonly_posture_and_telemetry",
]


if __name__ == "__main__":
    raise SystemExit(main())
