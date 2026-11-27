"""Black Friday 30/11 Sprint status payload and Mũi 3 MASTER_PROP7E Real-Tick scenario loader."""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cockpit.modules.helpers import (
    _coerce_opt_float,
    _coerce_opt_int,
    _safe_read_json,
    _sanitize_short_token,
)
from cockpit.modules.sprint_friction import _load_mui1_mui2_friction_and_spreads
from cockpit.modules.state import (
    _SPRINT_CACHE_LOCK,
    BLACKFRIDAY_DEADLINE_DT,
    BLACKFRIDAY_DEADLINE_ICT,
    BLACKFRIDAY_DEADLINE_ISO,
    ORDER_SEND_COUNT,
    ROOT,
    SPRINT_CACHE_TTL_SEC,
    get_sprint_cache,
)


def _detect_realtick_model(
    summ: dict[str, Any],
    rep: dict[str, Any],
    scenario_dir: Path,
    label: str,
) -> tuple[int, str]:
    """Detect MT5 tester modeling mode (4 = Real Ticks, 1 = 1-Minute OHLC) from JSON, tester.ini, or label."""
    model_val = _coerce_opt_int(summ.get("model") if "model" in summ else rep.get("model"))
    if model_val is None:
        ini_p = scenario_dir / "tester.ini"
        if ini_p.is_file():
            try:
                raw_ini = ini_p.read_text(encoding="utf-8", errors="replace")
                m = re.search(r"(?m)^\s*Model\s*=\s*(\d+)\s*$", raw_ini)
                if m:
                    model_val = int(m.group(1))
            except OSError:
                model_val = None
    if model_val is None:
        up_lbl = label.upper()
        model_val = 1 if ("M1OHLC" in up_lbl or "OHLC" in up_lbl) else 4

    if model_val == 4:
        return 4, "Model=4 Real Ticks"
    if model_val == 1:
        return 1, "Model=1 1m OHLC"
    return model_val, f"Model={model_val}"


def _load_mui3_master_prop7e_scenarios(root: Path) -> dict[str, Any]:
    rt_dir = root / ".runtime/mt5-realtick-results"
    scenarios: list[dict[str, Any]] = []
    if rt_dir.is_dir():
        for jf in sorted(rt_dir.glob("MASTER_PROP7E_*/parsed_result.json")):
            obj = _safe_read_json(jf)
            if not isinstance(obj, dict):
                continue
            summ_raw = obj.get("summary")
            rep_raw = obj.get("report")
            summ: dict[str, Any] = summ_raw if isinstance(summ_raw, dict) else obj
            rep: dict[str, Any] = rep_raw if isinstance(rep_raw, dict) else obj
            label_clean = _sanitize_short_token(summ.get("label") or jf.parent.name, jf.parent.name, 64)
            model_num, model_badge = _detect_realtick_model(summ, rep, jf.parent, label_clean)

            lat_ms = _coerce_opt_int(summ.get("latency_ms"))
            if lat_ms is None:
                m_lat = re.search(r"_(\d+)ms\b", label_clean, re.IGNORECASE)
                if m_lat:
                    lat_ms = int(m_lat.group(1))

            swap_val = _coerce_opt_float(
                rep.get("swap_total_usd") if "swap_total_usd" in rep else summ.get("total_swap_usd"), 2
            )
            swap_zero_ok = (
                bool(rep.get("swap_zero_ok"))
                if "swap_zero_ok" in rep
                else (swap_val is not None and abs(swap_val) <= 1e-9)
            )
            net_by_sym_raw = summ.get("net_by_symbol_usd")
            net_by_sym = (
                {
                    _sanitize_short_token(k, "SYM", 24): round(float(v), 2)
                    for k, v in net_by_sym_raw.items()
                    if isinstance(v, (int, float)) and not isinstance(v, bool)
                }
                if isinstance(net_by_sym_raw, dict)
                else {}
            )
            try:
                mtime_ts = jf.stat().st_mtime
                mtime_iso: str | None = datetime.fromtimestamp(mtime_ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            except OSError:
                mtime_ts = 0.0
                mtime_iso = None
            log_errs = summ.get("log_errors")
            scenarios.append({
                "label": label_clean,
                "model": model_num,
                "model_badge": model_badge,
                "is_real_ticks": model_num == 4,
                "latency_ms": lat_ms,
                "base_phase_mult": _coerce_opt_float(summ.get("base_phase_mult"), 2),
                "ok": bool(rep.get("ok") if "ok" in rep else summ.get("report_ok", False)),
                "from_date": _sanitize_short_token(summ.get("from_date"), "", 24),
                "to_date": _sanitize_short_token(summ.get("to_date"), "", 24),
                "period": _sanitize_short_token(rep.get("period"), "", 48),
                "leverage": _coerce_opt_int(summ.get("leverage")),
                "elapsed_s": _coerce_opt_float(summ.get("elapsed_s"), 1),
                "total_trades": _coerce_opt_int(
                    rep.get("total_trades") if "total_trades" in rep else summ.get("total_trades")
                ),
                "win_rate_pct": _coerce_opt_float(rep.get("win_rate_pct"), 2),
                "total_net_profit_usd": _coerce_opt_float(
                    rep.get("total_net_profit") if "total_net_profit" in rep else summ.get("total_net_profit"), 2
                ),
                "profit_factor": _coerce_opt_float(rep.get("profit_factor"), 2),
                "sharpe_ratio": _coerce_opt_float(rep.get("sharpe_ratio"), 2),
                "balance_dd_pct": _coerce_opt_float(rep.get("balance_dd_pct"), 2),
                "equity_dd_pct": _coerce_opt_float(rep.get("equity_dd_pct"), 2),
                "swap_total_usd": swap_val,
                "swap_zero_ok": swap_zero_ok,
                "commission_total_usd": _coerce_opt_float(
                    rep.get("commission_total_usd") if "commission_total_usd" in rep else summ.get("total_comm_usd"),
                    2,
                ),
                "propguard_ok_lines": _coerce_opt_int(summ.get("propguard_ok_lines")),
                "propguard_warn_lines": _coerce_opt_int(summ.get("propguard_warn_lines")),
                "order_rejects": _coerce_opt_int(summ.get("order_rejects")),
                "log_errors_count": len(log_errs) if isinstance(log_errs, list) else 0,
                "net_by_symbol_usd": net_by_sym,
                "updated_utc": mtime_iso,
                "_mtime": mtime_ts,
            })

    if not scenarios:
        return {
            "status": "pending",
            "available": False,
            "scenarios_count": 0,
            "model4_count": 0,
            "model1_count": 0,
            "latest": None,
            "scenarios": [],
        }

    # Display Model=4 Real Ticks first, then Model=1 1m OHLC, sorted deterministically by label
    scenarios.sort(key=lambda x: (0 if x["model"] == 4 else 1, x["label"]))
    latest_item = max(scenarios, key=lambda x: (x["_mtime"], x["label"]))
    cleaned = [{k: v for k, v in s.items() if k != "_mtime"} for s in scenarios]
    latest_clean = {k: v for k, v in latest_item.items() if k != "_mtime"}
    return {
        "status": "AVAILABLE",
        "available": True,
        "scenarios_count": len(cleaned),
        "model4_count": sum(1 for s in cleaned if s["model"] == 4),
        "model1_count": sum(1 for s in cleaned if s["model"] == 1),
        "latest": latest_clean,
        "scenarios": cleaned,
    }


def build_blackfriday_sprint_payload(
    root: Path = ROOT,
    *,
    now_utc: datetime | None = None,
    use_cache: bool = True,
    ttl_sec: float = SPRINT_CACHE_TTL_SEC,
) -> dict[str, Any]:
    """Read-only 30s cached Black Friday 30/11 sprint status, Mũi 1-3 metrics & Layer-2 vault mount status."""
    cache_key = str(root.resolve())
    mono_now = time.monotonic()
    cache_map = get_sprint_cache()
    if use_cache and now_utc is None and ttl_sec > 0.0:
        with _SPRINT_CACHE_LOCK:
            cached = cache_map.get(cache_key)
            if cached is not None and (mono_now - cached[0]) < ttl_sec:
                return dict(cached[1])

    now_dt = now_utc.astimezone(UTC) if now_utc is not None else datetime.now(UTC)
    delta_s = (BLACKFRIDAY_DEADLINE_DT - now_dt).total_seconds()
    expired = delta_s <= 0.0
    rem_s = max(0, int(delta_s))
    rem_days, rem_after_days = divmod(rem_s, 86_400)
    rem_hours_in_day = rem_after_days // 3_600
    rem_hours_total = rem_s // 3_600
    rem_minutes = (rem_s % 3_600) // 60
    countdown_vi = (
        "Đã đến mốc 30/11 16:00 (ICT)"
        if expired
        else f"Còn {rem_days} ngày {rem_hours_in_day} giờ {rem_minutes:02d} phút"
    )

    mui3 = _load_mui3_master_prop7e_scenarios(root)
    mui12 = _load_mui1_mui2_friction_and_spreads(root)
    vault_status = "MOUNTED" if (root / "private_vault" / "owner").exists() else "NOT_MOUNTED"

    payload: dict[str, Any] = {
        "schema": "naqex-blackfriday-sprint-v1",
        "generated_utc": now_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cache_ttl_sec": int(ttl_sec),
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_sealed": True,
        "deadline_iso": BLACKFRIDAY_DEADLINE_ISO,
        "deadline_ict": BLACKFRIDAY_DEADLINE_ICT,
        "remaining_hours": rem_hours_total,
        "remaining_minutes": rem_minutes,
        "remaining_days": rem_days,
        "remaining_hours_in_day": rem_hours_in_day,
        "remaining_seconds": rem_s,
        "expired": expired,
        "countdown_vi": countdown_vi,
        "private_vault_status": vault_status,
        "mui3_realtick": mui3,
        "mui1_mui2": mui12,
    }

    if use_cache and now_utc is None and ttl_sec > 0.0:
        with _SPRINT_CACHE_LOCK:
            cache_map[cache_key] = (mono_now, payload)
    return dict(payload)
