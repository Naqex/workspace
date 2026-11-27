"""Sanitized naqex-node1 health summary builder (bounded SSH probe + offline local fallback)."""

from __future__ import annotations

import math
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cockpit.modules.helpers import (
    _coerce_opt_bool,
    _coerce_opt_float,
    _coerce_opt_int,
    _read_jsonl_tail,
    _safe_read_json,
    _sanitize_heroku_status,
    _sanitize_ntp_offset,
    as_dict,
)
from cockpit.modules.state import (
    _NODE1_CACHE_LOCK,
    NODE1_CACHE_TTL_SEC,
    NODE1_SSH_TIMEOUT_SEC,
    ORDER_SEND_COUNT,
    ROOT,
    get_node1_cache,
)


def _probe_node1_via_node_ctl(timeout_sec: float = NODE1_SSH_TIMEOUT_SEC) -> dict[str, Any] | None:
    """Invoke ops_cloud.node_ctl.run_remote_probe('status') bounded strictly by timeout_sec (OrderSend=0)."""
    try:
        from ops_cloud import node_ctl
    except Exception:
        return None

    result_box: dict[str, Any] = {}

    def _worker() -> None:
        try:
            res = node_ctl.run_remote_probe("status", timeout=max(1, int(math.ceil(timeout_sec))))
            if isinstance(res, dict):
                result_box["data"] = res
        except Exception:
            result_box["error"] = True

    th = threading.Thread(target=_worker, daemon=True)
    th.start()
    th.join(timeout=max(0.2, float(timeout_sec)))
    if th.is_alive():
        return None
    data = result_box.get("data")
    return data if isinstance(data, dict) else None


def _read_local_node1_fallback(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    overnight_dir = root / ".runtime/live-overnight"
    local_hb: dict[str, Any] = {}
    for cand in (
        overnight_dir / "naqex_heartbeat.json",
        root / ".runtime/ftmo-demo-portable-1515343166/MQL5/Files/naqex_heartbeat.json",
        root / ".runtime/naqex_heartbeat.json",
    ):
        obj = _safe_read_json(cand)
        if isinstance(obj, dict):
            local_hb = obj
            break
    spread_tail = _read_jsonl_tail(overnight_dir / "mt5_live_spread_log.jsonl", limit=5)
    latest_snap = spread_tail[-1] if spread_tail else {}
    return local_hb, latest_snap


def build_node1_summary_payload(
    root: Path = ROOT,
    *,
    allow_ssh: bool = True,
    timeout_sec: float = NODE1_SSH_TIMEOUT_SEC,
    use_cache: bool = True,
    ttl_sec: float = NODE1_CACHE_TTL_SEC,
) -> dict[str, Any]:
    """Read-only 30s cached, strictly sanitized naqex-node1 health summary (ZERO raw IPs/URLs/tokens)."""
    cache_key = (str(root.resolve()), bool(allow_ssh))
    mono_now = time.monotonic()
    cache_map = get_node1_cache()
    if use_cache and ttl_sec > 0.0:
        with _NODE1_CACHE_LOCK:
            cached = cache_map.get(cache_key)
            if cached is not None and (mono_now - cached[0]) < ttl_sec:
                return dict(cached[1])

    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw_ssh = _probe_node1_via_node_ctl(timeout_sec=timeout_sec) if allow_ssh else None

    if isinstance(raw_ssh, dict):
        hb = as_dict(raw_ssh.get("heartbeat"))
        sys_info = as_dict(raw_ssh.get("system"))
        disks = as_dict(raw_ssh.get("disks"))
        disk_c = as_dict(disks.get("C"))
        mt5_procs = raw_ssh.get("mt5_procs")
        if isinstance(mt5_procs, list):
            mt5_running: bool | None = len(mt5_procs) > 0
        else:
            mt5_running = _coerce_opt_bool(raw_ssh.get("mt5_running"))

        bal = _coerce_opt_float(hb["balance"], 2) if "balance" in hb else _coerce_opt_float(raw_ssh.get("balance"), 2)
        eq = _coerce_opt_float(hb["equity"], 2) if "equity" in hb else _coerce_opt_float(raw_ssh.get("equity"), 2)
        open_pos = (
            _coerce_opt_int(hb["open_positions"])
            if "open_positions" in hb
            else _coerce_opt_int(raw_ssh.get("open_positions"))
        )
        payload: dict[str, Any] = {
            "schema": "naqex-node1-summary-v1",
            "generated_utc": now_iso,
            "cache_ttl_sec": int(ttl_sec),
            "order_send_count": ORDER_SEND_COUNT,
            "holdout_sealed": True,
            "connected": True,
            "mt5_running": mt5_running,
            "open_positions": open_pos,
            "balance": bal,
            "equity": eq,
            "propguard_ok_count": _coerce_opt_int(raw_ssh.get("propguard_ok_count")),
            "propguard_warn_count": _coerce_opt_int(raw_ssh.get("propguard_warn_count")),
            "ntp_offset": _sanitize_ntp_offset(raw_ssh.get("ntp_offset")),
            "auto_logon": _coerce_opt_bool(
                sys_info.get("auto_logon") if "auto_logon" in sys_info else raw_ssh.get("auto_logon")
            ),
            "heroku_status": _sanitize_heroku_status(raw_ssh.get("heroku_last"), raw_ssh.get("heroku_last_raw")),
            "free_ram_gb": _coerce_opt_float(
                sys_info.get("free_ram_gb") if "free_ram_gb" in sys_info else raw_ssh.get("free_ram_gb"), 1
            ),
            "c_free_gb": _coerce_opt_float(
                disk_c.get("free_gb") if "free_gb" in disk_c else raw_ssh.get("c_free_gb"), 1
            ),
            "source": "live_ssh",
        }
    else:
        local_hb, latest_snap = _read_local_node1_fallback(root)
        snap_acct = as_dict(latest_snap.get("account"))
        snap_hb = as_dict(latest_snap.get("heartbeat"))
        snap_hb_pay_raw = snap_hb.get("payload")
        snap_hb_pay: dict[str, Any] = snap_hb_pay_raw if isinstance(snap_hb_pay_raw, dict) else snap_hb

        if "balance" in local_hb:
            fb_bal = _coerce_opt_float(local_hb.get("balance"), 2)
        elif "balance" in snap_acct:
            fb_bal = _coerce_opt_float(snap_acct.get("balance"), 2)
        else:
            fb_bal = _coerce_opt_float(snap_hb_pay.get("balance"), 2)

        if "equity" in local_hb:
            fb_eq = _coerce_opt_float(local_hb.get("equity"), 2)
        elif "equity" in snap_acct:
            fb_eq = _coerce_opt_float(snap_acct.get("equity"), 2)
        else:
            fb_eq = _coerce_opt_float(snap_hb_pay.get("equity"), 2)

        if "open_positions" in local_hb:
            fb_pos = _coerce_opt_int(local_hb.get("open_positions"))
        elif "naqex_positions_count" in latest_snap:
            fb_pos = _coerce_opt_int(latest_snap.get("naqex_positions_count"))
        else:
            fb_pos = _coerce_opt_int(snap_hb_pay.get("open_positions"))

        if "terminal_connected" in latest_snap:
            fb_mt5 = _coerce_opt_bool(latest_snap.get("terminal_connected"))
        elif local_hb:
            fb_mt5 = _coerce_opt_bool(local_hb.get("mt5_running"))
        else:
            fb_mt5 = None

        has_local = bool(local_hb or snap_acct or snap_hb_pay)
        payload = {
            "schema": "naqex-node1-summary-v1",
            "generated_utc": now_iso,
            "cache_ttl_sec": int(ttl_sec),
            "order_send_count": ORDER_SEND_COUNT,
            "holdout_sealed": True,
            "connected": False,
            "mt5_running": fb_mt5,
            "open_positions": fb_pos,
            "balance": fb_bal,
            "equity": fb_eq,
            "propguard_ok_count": None,
            "propguard_warn_count": None,
            "ntp_offset": None,
            "auto_logon": None,
            "heroku_status": "LOCAL_CACHE" if has_local else "UNAVAILABLE",
            "free_ram_gb": None,
            "c_free_gb": None,
            "source": "fallback",
        }

    if use_cache and ttl_sec > 0.0:
        with _NODE1_CACHE_LOCK:
            cache_map[cache_key] = (mono_now, payload)
    return dict(payload)
