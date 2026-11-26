"""Live telemetry aggregation, 2-step safety-covered emergency flags, and Prop Terms audit."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any

from cockpit.modules.helpers import (
    _load_upcoming_red_news,
    _read_jsonl_tail,
    _safe_read_json,
    as_dict,
    as_list,
)
from cockpit.modules.prop_risk import _compute_positions_mae_mfe
from cockpit.modules.state import EMERGENCY_CONFIRM_CODES, ORDER_SEND_COUNT, ROOT
from quant_core.io_utils import atomic_write_json, atomic_write_text
from quant_factory.prop_terms_auditor import FIRM_BASELINES, audit_prop_terms_text


def build_live_telemetry_payload(root: Path = ROOT) -> dict[str, Any]:
    overnight_dir = root / ".runtime/live-overnight"
    realtick_dir = root / ".runtime/mt5-realtick-results"

    mt5_spreads = _read_jsonl_tail(overnight_dir / "mt5_live_spread_log.jsonl", limit=20)
    crypto_shadow_rows = _read_jsonl_tail(overnight_dir / "crypto_shadow_log.jsonl", limit=20)
    crypto_shadow_latest = _safe_read_json(overnight_dir / "crypto_shadow_latest.json")
    crypto_maker_latest = _safe_read_json(overnight_dir / "crypto_maker_shadow_latest.json")
    crypto_maker_rows = _read_jsonl_tail(overnight_dir / "crypto_maker_shadow.jsonl", limit=20)

    # Parse structured Crypto Shadow L2 telemetry (BTC/ETH/SOL spreads, 10k slip vs 5bps budget, cycle count)
    cs_obj = (
        crypto_shadow_latest
        if isinstance(crypto_shadow_latest, dict)
        else (crypto_shadow_rows[-1] if crypto_shadow_rows else None)
    )
    if isinstance(cs_obj, dict):
        tca = as_dict(cs_obj.get("tca_summary_top15"))
        depth = as_dict(cs_obj.get("orderbook_depth_top15"))
        majors: dict[str, dict[str, Any]] = {}
        for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
            sym_d = depth.get(sym)
            if isinstance(sym_d, dict):
                majors[sym] = {
                    "mid": sym_d.get("mid"),
                    "spread_bps": sym_d.get("spread_bps"),
                    "slip_10k_bps": sym_d.get("slip_10k_bps"),
                    "slip_50k_bps": sym_d.get("slip_50k_bps"),
                    "depth_50k_ok": sym_d.get("depth_50k_ok"),
                }
        s2_live = as_dict(cs_obj.get("sleeve2_f4_4h_ema"))
        s3a_live = as_dict(cs_obj.get("sleeve3a_carry_btc_eth"))
        perp_basis = as_dict(s3a_live.get("perp_live_basis"))
        crypto_shadow_block: dict[str, Any] = {
            "status": "ACTIVE",
            "source": (
                ".runtime/live-overnight/crypto_shadow_latest.json"
                if isinstance(crypto_shadow_latest, dict)
                else ".runtime/live-overnight/crypto_shadow_log.jsonl"
            ),
            "cycle_num": cs_obj.get("cycle_num", len(crypto_shadow_rows)),
            "timestamp_utc": cs_obj.get("timestamp_utc"),
            "order_send_count": int(cs_obj.get("order_send_count", 0)),
            "count": max(len(crypto_shadow_rows), int(cs_obj.get("cycle_num") or 0)),
            "tca_summary": {
                "median_spread_bps": tca.get("median_spread_bps"),
                "median_slip_10k_bps": tca.get("median_slip_10k_bps"),
                "max_slip_10k_bps": tca.get("max_slip_10k_bps"),
                "median_slip_50k_bps": tca.get("median_slip_50k_bps"),
                "budget_10k_bps": tca.get("backtest_assumed_oneway_slip_bps", 5.0),
                "within_budget_10k": tca.get("tca_within_budget_10k"),
            },
            "majors_l2": majors,
            "sleeve2_regime_bull": s2_live.get("btc_regime_bull"),
            "sleeve2_active_count": s2_live.get("active_count"),
            "sleeve3a_funding_btc_ann_pct": as_dict(perp_basis.get("BTCUSDT")).get("next_funding_ann_pct"),
            "sleeve3a_funding_eth_ann_pct": as_dict(perp_basis.get("ETHUSDT")).get("next_funding_ann_pct"),
            "latest": cs_obj,
            "recent": crypto_shadow_rows[-8:],
        }
    else:
        crypto_shadow_block = {
            "status": "pending",
            "source": None,
            "cycle_num": 0,
            "timestamp_utc": None,
            "order_send_count": 0,
            "count": 0,
            "tca_summary": None,
            "majors_l2": {},
            "latest": None,
            "recent": [],
        }

    # Parse Crypto Maker Shadow Probe (`.runtime/live-overnight/crypto_maker_shadow_latest.json`)
    cm_obj = (
        crypto_maker_latest
        if isinstance(crypto_maker_latest, dict)
        else (crypto_maker_rows[-1] if crypto_maker_rows else None)
    )
    if isinstance(cm_obj, dict):
        crypto_maker_block: dict[str, Any] = {
            "status": "ACTIVE",
            "source": (
                ".runtime/live-overnight/crypto_maker_shadow_latest.json"
                if isinstance(crypto_maker_latest, dict)
                else ".runtime/live-overnight/crypto_maker_shadow.jsonl"
            ),
            "cycle_num": cm_obj.get("cycle_num", len(crypto_maker_rows)),
            "timestamp_utc": cm_obj.get("timestamp_utc") or cm_obj.get("generated_utc"),
            "count": max(len(crypto_maker_rows), int(cm_obj.get("cycle_num") or 1)),
            "latest": cm_obj,
        }
    else:
        crypto_maker_block = {
            "status": "pending",
            "source": None,
            "cycle_num": 0,
            "timestamp_utc": None,
            "count": 0,
            "latest": None,
        }

    # Discover MT5 Real-Tick `Model=4` Matrix & Python Reconciliation (prioritize realtick_matrix_summary.json!)
    realtick_summary: dict[str, Any] | None = None
    realtick_source: str | None = None
    if realtick_dir.is_dir():
        for name in (
            "realtick_matrix_summary.json",
            "mt5_vs_python_reconcile.json",
            "realtick_summary.json",
            "summary.json",
        ):
            obj = _safe_read_json(realtick_dir / name)
            if isinstance(obj, dict):
                realtick_summary = obj
                realtick_source = f".runtime/mt5-realtick-results/{name}"
                break

    if isinstance(realtick_summary, dict):
        rec_map = as_dict(realtick_summary.get("reconciliation"))
        engines_compact: list[dict[str, Any]] = []
        for eng_id, rec in rec_map.items():
            if not isinstance(rec, dict):
                continue
            lc = as_dict(rec.get("latency_curve"))
            lat_rows = {
                lat_k: {
                    "ok": v.get("ok"),
                    "trades": v.get("trades"),
                    "net_profit": v.get("net_profit"),
                    "profit_factor": v.get("profit_factor"),
                    "swap_zero_ok": v.get("swap_zero_ok"),
                }
                for lat_k, v in lc.items()
                if isinstance(v, dict)
            }
            py_ref = as_dict(rec.get("python_dev_reference"))
            engines_compact.append({
                "engine_id": eng_id,
                "verdict": rec.get("verdict", "UNKNOWN"),
                "latency_drag_50_to_250ms_usd": rec.get("latency_drag_50_to_250ms_usd"),
                "latency_curve": lat_rows,
                "python_ref_trades": py_ref.get("trades"),
                "python_ref_net_usd": py_ref.get("net_profit_usd"),
            })
        realtick_block: dict[str, Any] = {
            "status": "AVAILABLE",
            "source": realtick_source,
            "generated_utc": realtick_summary.get("generated_utc"),
            "model": realtick_summary.get("model"),
            "window": realtick_summary.get("window"),
            "latencies_ms": realtick_summary.get("latencies_ms", []),
            "engines_run": realtick_summary.get("engines_run", len(engines_compact)),
            "account": realtick_summary.get("account"),
            "engines": engines_compact,
            "data": realtick_summary,
        }
    else:
        realtick_block = {
            "status": "pending",
            "source": None,
            "generated_utc": None,
            "model": None,
            "window": None,
            "latencies_ms": [],
            "engines_run": 0,
            "account": None,
            "engines": [],
            "data": None,
        }

    # Discover MT5 heartbeat JSON (prioritize live sandbox heartbeat -> latest telemetry -> fallback)
    heartbeat_data: dict[str, Any] | None = None
    heartbeat_src: str | None = None
    for cand in (
        root / ".runtime/ftmo-demo-portable-1515343166/MQL5/Files/naqex_heartbeat.json",
        overnight_dir / "naqex_heartbeat.json",
        root / ".runtime/naqex_heartbeat.json",
    ):
        obj = _safe_read_json(cand)
        if isinstance(obj, dict):
            heartbeat_data = obj
            heartbeat_src = cand.relative_to(root).as_posix()
            break

    # Extract MT5 live spread tail + FTMO-Demo live account, open positions & recent execution audit CSV
    mt5_latest: dict[str, Any] | None = mt5_spreads[-1] if mt5_spreads else None
    latest_d = as_dict(mt5_latest)
    mt5_acct_live = as_dict(latest_d.get("account"))
    if heartbeat_data is None and isinstance(mt5_latest, dict):
        hb_wrap = as_dict(latest_d.get("heartbeat"))
        hb_pay = hb_wrap.get("payload")
        if isinstance(hb_pay, dict):
            heartbeat_data = hb_pay
            heartbeat_src = ".runtime/live-overnight/mt5_live_spread_log.jsonl"

    raw_positions = list(as_list(latest_d.get("naqex_positions"))) if isinstance(mt5_latest, dict) else []
    mae_mfe_lookup = (
        _compute_positions_mae_mfe(_read_jsonl_tail(overnight_dir / "mt5_live_spread_log.jsonl", limit=1500))
        if raw_positions
        else {}
    )
    live_positions: list[dict[str, Any]] = []
    for p in raw_positions:
        if not isinstance(p, dict):
            continue
        mm = mae_mfe_lookup.get(int(p["ticket"])) if p.get("ticket") is not None else None
        live_positions.append({
            **p,
            "mae_pips": mm.get("mae_pips") if mm else None,
            "mfe_pips": mm.get("mfe_pips") if mm else None,
            "mae_usd": mm.get("mae_usd") if mm else None,
            "mfe_usd": mm.get("mfe_usd") if mm else None,
        })
    exec_audit_recent: list[dict[str, str]] = []
    exec_csv = root / ".runtime/ftmo-demo-portable-1515343166/MQL5/Files/naqex_exec_audit.csv"
    if exec_csv.is_file():
        try:
            with exec_csv.open("r", encoding="utf-8", errors="replace", newline="") as f:
                exec_audit_recent = list(csv.DictReader(f))[-15:]
        except OSError:
            exec_audit_recent = []

    demo_acct_raw = realtick_block.get("account")
    demo_acct: dict[str, Any] | None = demo_acct_raw if isinstance(demo_acct_raw, dict) else None
    demo_d = as_dict(demo_acct)
    if mt5_latest or demo_acct:
        demo_account_block: dict[str, Any] | None = {
            "login": mt5_acct_live.get("login") or latest_d.get("login") or demo_d.get("login"),
            "server": mt5_acct_live.get("server") or latest_d.get("server") or demo_d.get("server"),
            "balance": (
                mt5_acct_live.get("balance")
                if "balance" in mt5_acct_live
                else (latest_d.get("balance") if "balance" in latest_d else demo_d.get("balance"))
            ),
            "equity": (
                mt5_acct_live.get("equity")
                if "equity" in mt5_acct_live
                else (latest_d.get("equity") if "equity" in latest_d else demo_d.get("equity"))
            ),
            "profit": mt5_acct_live.get("profit"),
            "leverage": mt5_acct_live.get("leverage") or demo_d.get("leverage"),
            "terminal_connected": (
                latest_d.get("terminal_connected")
                if "terminal_connected" in latest_d
                else demo_d.get("terminal_connected")
            ),
        }
    else:
        demo_account_block = None

    mt5_spread_block: dict[str, Any] = {
        "status": "ACTIVE" if mt5_latest else "pending",
        "count": len(mt5_spreads),
        "latest": mt5_latest,
        "recent": mt5_spreads[-8:],
        "open_positions": live_positions,
        "exec_audit_recent": exec_audit_recent,
        "demo_account": demo_account_block,
    }

    emergency_state = read_emergency_cover_state(root)
    ftmo_specs = _safe_read_json(root / "planning/research/FTMO-LIVE-SPECS-ALL-SYMBOLS-20261124.json")
    upcoming_news = _load_upcoming_red_news(root, limit=10)

    return {
        "schema": "naqex-cockpit-live-telemetry-v2",
        "generated_utc": datetime.now(UTC).isoformat(),
        "order_send_count": ORDER_SEND_COUNT,
        "mt5_heartbeat": {
            "status": "LIVE_HEARTBEAT" if heartbeat_data else ("DEMO_VERIFIED" if demo_acct else "pending"),
            "source": heartbeat_src or (realtick_source if demo_acct else None),
            "data": heartbeat_data or demo_acct,
        },
        "mt5_live_spreads": mt5_spread_block,
        "emergency_cover": emergency_state,
        "crypto_shadow": crypto_shadow_block,
        "crypto_maker_shadow": crypto_maker_block,
        "mt5_realtick_tca": realtick_block,
        "ftmo_live_specs_available": ftmo_specs is not None,
        "upcoming_red_news": upcoming_news,
    }


def read_emergency_cover_state(root: Path = ROOT) -> dict[str, Any]:
    state_path = root / ".runtime/live-overnight/naqex_emergency_cover_state.json"
    obj = _safe_read_json(state_path)
    if isinstance(obj, dict):
        return obj
    return {
        "schema": "naqex-emergency-cover-v1",
        "order_send_count": ORDER_SEND_COUNT,
        "state": "NORMAL_COVER_CLOSED",
        "action": "NONE",
        "updated_utc": None,
        "reason": "Safety cover closed; zero emergency flags active.",
    }


def apply_emergency_cover_action(
    root: Path,
    body: dict[str, Any],
    *,
    bridge_dir: Path | None = None,
) -> tuple[HTTPStatus, dict[str, Any]]:
    """Fail-closed 2-step safety-covered emergency flag handler (OrderSend=0)."""
    cover_opened = bool(body.get("cover_opened", False))
    action = str(body.get("action", "")).strip().upper()
    confirm_code = str(body.get("confirm_code", "")).strip().upper()
    reason = str(body.get("reason", "")).strip()[:240] or "operator_triggered"

    if not cover_opened:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "order_send_count": ORDER_SEND_COUNT,
            "error": "SAFETY_COVER_CLOSED: must flip safety cover first (cover_opened=true).",
        }
    expected_code = EMERGENCY_CONFIRM_CODES.get(action)
    if expected_code is None:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "order_send_count": ORDER_SEND_COUNT,
            "error": f"INVALID_ACTION: allowed={sorted(EMERGENCY_CONFIRM_CODES.keys())}",
        }
    if confirm_code != expected_code:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "order_send_count": ORDER_SEND_COUNT,
            "error": f"CONFIRM_CODE_MISMATCH: expected '{expected_code}' for action '{action}'.",
        }

    now_iso = datetime.now(UTC).isoformat()
    new_state = "NORMAL_COVER_CLOSED" if action == "RESET_NORMAL" else f"ARMED_{action}"
    bridge_written = False
    if bridge_dir is not None:
        flag_path = bridge_dir / "naqex_manual_halt.flag"
        bridge_dir.mkdir(parents=True, exist_ok=True)
        if action == "RESET_NORMAL":
            if flag_path.exists():
                flag_path.unlink()
        else:
            atomic_write_text(flag_path, f"{action}|{now_iso}|{reason}\n")
        bridge_written = True

    delivery_status = (
        "WRITTEN_TO_MT5_BRIDGE_AWAITING_ORCH_ACK"
        if bridge_written
        else "LOCAL_AUDIT_ONLY_NOT_DELIVERED_TO_MT5"
    )
    record = {
        "schema": "naqex-emergency-cover-v1",
        "order_send_count": ORDER_SEND_COUNT,
        "state": new_state,
        "action": action,
        "reason": reason,
        "updated_utc": now_iso,
        "mt5_bridge_written": bridge_written,
        "delivery_status": delivery_status,
        "note": (
            "Bridge flag written to MT5 MQL5/Files; requires InpAllowManualHaltFile=true on Orchestrator "
            "for live effect."
            if bridge_written
            else "LOCAL AUDIT ONLY: NOT delivered to remote MT5/VPS! "
            "Open RDP/MT5 directly to halt or flatten live positions."
        ),
    }

    state_path = root / ".runtime/live-overnight/naqex_emergency_cover_state.json"
    atomic_write_json(state_path, record, indent=2, ensure_ascii=False)

    return HTTPStatus.OK, {"ok": True, **record}


def handle_prop_terms_audit_request(body: dict[str, Any]) -> tuple[HTTPStatus, dict[str, Any]]:
    """Offline baseline preview by default; opt-in TypeSafe jev-1.14.0 drift audit when requested."""
    firm = str(body.get("firm", "the5ers_high_stakes")).strip()
    terms_text = str(body.get("terms_text", "")).strip()
    use_typesafe = bool(body.get("use_typesafe", False))

    if firm not in FIRM_BASELINES:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "order_send_count": ORDER_SEND_COUNT,
            "error": f"Unknown firm '{firm}'. Allowed: {sorted(FIRM_BASELINES.keys())}",
        }

    baseline = FIRM_BASELINES[firm]
    if not use_typesafe:
        return HTTPStatus.OK, {
            "ok": True,
            "order_send_count": ORDER_SEND_COUNT,
            "mode": "offline_baseline_preview",
            "firm": firm,
            "baseline": baseline,
            "verdict": "BASELINE_PREVIEW_ONLY",
            "note": (
                "Tích chọn 'Bật AI TypeSafe (jev-1.14.0)' và dán văn bản điều khoản "
                "để kiểm toán drift trực tiếp."
            ),
        }

    if len(terms_text) < 20:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "order_send_count": ORDER_SEND_COUNT,
            "error": "Văn bản điều khoản quá ngắn (< 20 ký tự) để kiểm toán.",
        }

    try:
        res = audit_prop_terms_text(terms_text, firm_id=firm)
        return HTTPStatus.OK, {"ok": True, "order_send_count": ORDER_SEND_COUNT, "mode": "typesafe_jev114", **res}
    except Exception as exc:
        return HTTPStatus.SERVICE_UNAVAILABLE, {
            "ok": False,
            "order_send_count": ORDER_SEND_COUNT,
            "mode": "typesafe_jev114_fail_closed",
            "error": f"Fail-closed TypeSafe error: {exc}",
        }
