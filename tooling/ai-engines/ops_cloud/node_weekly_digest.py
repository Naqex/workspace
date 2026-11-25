"""1-Command Read-Only Morning / Weekly Ops Digest for `naqex-node1` (`OrderSend = 0`).

Aggregates `node_ctl.py` (`status`, `integrity`, `maint`, `audit`), `node_cutover_dryrun.py`,
and optional local `.runtime/live-overnight/prop_challenge_scoreboard.json` into a compact
(<= 35 lines) plain-Vietnamese Morning/Weekly Ops Digest and sanitized JSON payload.

STRICTLY READ-ONLY: ZERO `OrderSend`, ZERO MT5 launches, ZERO remote writes, ZERO IPs/secrets/bare `$`.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0

OPS_CLOUD_DIR = Path(__file__).resolve().parent
AI_ENGINES_DIR = OPS_CLOUD_DIR.parent
REPO_ROOT = AI_ENGINES_DIR.parents[1]
DEFAULT_SCOREBOARD_PATH = REPO_ROOT / ".runtime/live-overnight/prop_challenge_scoreboard.json"

for p in (OPS_CLOUD_DIR, AI_ENGINES_DIR / "exports", AI_ENGINES_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import node_cutover_dryrun as cutover  # noqa: E402


def load_optional_scoreboard(path: Path = DEFAULT_SCOREBOARD_PATH) -> dict[str, Any]:
    """Read local challenge scoreboard JSON gracefully (never fails when absent)."""
    if not path.is_file():
        return {"present": False, "status": "ABSENT"}
    try:
        raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        if not isinstance(raw, dict):
            return {"present": False, "status": "INVALID"}
        return {
            "present": True,
            "status": str(raw.get("verdict") or raw.get("status") or "AVAILABLE"),
            "trades": raw.get("total_trades", raw.get("trades")),
            "net_usd": raw.get("net_pnl_usd", raw.get("net_usd")),
            "swap_zero_ok": raw.get("swap_zero_ok"),
            "updated_utc": raw.get("generated_utc", raw.get("updated_utc")),
        }
    except Exception as exc:
        return {"present": False, "status": f"READ_ERR:{type(exc).__name__}"}


def build_ops_digest(
    *,
    status: dict[str, Any] | None,
    integrity: dict[str, Any] | None,
    maint: dict[str, Any] | None,
    audit: dict[str, Any] | None,
    local_kit: dict[str, Any],
    scoreboard: dict[str, Any],
    probe_error: str | None = None,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Build sanitized Morning/Weekly Ops Digest combining all node probes & cutover verdict."""
    ts_str = (now_utc or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    if probe_error or status is None or integrity is None or maint is None or audit is None:
        raw = {
            "schema": "naqex-node-ops-digest-v1",
            "checked_utc": ts_str,
            "order_send_count": ORDER_SEND_COUNT,
            "overall_status": "OFFLINE",
            "probe_error": probe_error or "Remote probe payload incomplete",
            "cutover_verdict": "BLOCKED",
            "gates_passed": 0,
            "gates_total": 10,
            "failed_gates": ["remote_ssh_unreachable"],
            "node": {},
            "infra": {},
            "integrity": {},
            "audit": {},
            "scoreboard": scoreboard,
        }
        return cutover.sanitize_output(raw)

    cut_res = cutover.evaluate_cutover_readiness(
        status=status,
        integrity=integrity,
        maint=maint,
        audit=audit,
        local_kit=local_kit,
        now_utc=now_utc,
    )
    hb = status.get("heartbeat") if isinstance(status.get("heartbeat"), dict) else {}
    sys_i = status.get("system") if isinstance(status.get("system"), dict) else {}
    disks = status.get("disks") if isinstance(status.get("disks"), dict) else {}
    hk = status.get("heroku_last") if isinstance(status.get("heroku_last"), dict) else {}
    ev_map = audit.get("events_by_type") if isinstance(audit.get("events_by_type"), dict) else {}
    lat_info = audit.get("latency_ms") if isinstance(audit.get("latency_ms"), dict) else {}
    rem_csv = integrity.get("red_news_csv") if isinstance(integrity.get("red_news_csv"), dict) else {}
    common_ini = integrity.get("common_ini") if isinstance(integrity.get("common_ini"), dict) else {}

    is_healthy = (
        cut_res["verdict"] == "READY_FOR_CUTOVER"
        or (
            hb.get("terminal_connected") is True
            and int(hb.get("orphan_no_sl", 1) or 0) == 0
            and not bool(hb.get("kill_switch"))
            and int(status.get("propguard_warn_count", 0) or 0) == 0
            and not bool(maint.get("wu_reboot_required"))
            and not bool(maint.get("cbs_reboot_pending"))
        )
    )
    overall = "HEALTHY" if is_healthy else "DEGRADED"

    raw = {
        "schema": "naqex-node-ops-digest-v1",
        "checked_utc": ts_str,
        "order_send_count": ORDER_SEND_COUNT,
        "overall_status": overall,
        "cutover_verdict": cut_res["verdict"],
        "target_preset": cut_res["target_preset"],
        "gates_passed": cut_res["gates_passed"],
        "gates_total": cut_res["gates_total"],
        "failed_gates": cut_res["failed_gates"],
        "node": {
            "terminal_connected": hb.get("terminal_connected"),
            "regime": hb.get("regime"),
            "dry_run": hb.get("dry_run"),
            "age_sec": hb.get("age_sec"),
            "balance_usd": hb.get("balance"),
            "equity_usd": hb.get("equity"),
            "daily_dd_pct": hb.get("daily_dd_pct"),
            "static_dd_pct": hb.get("static_dd_pct"),
            "open_positions": hb.get("open_positions"),
            "orphan_no_sl": hb.get("orphan_no_sl"),
            "kill_switch": hb.get("kill_switch"),
            "propguard_ok_count": status.get("propguard_ok_count"),
            "propguard_warn_count": status.get("propguard_warn_count"),
        },
        "infra": {
            "ntp_offset": status.get("ntp_offset"),
            "uptime_hr": sys_i.get("uptime_hr"),
            "free_ram_gb": sys_i.get("free_ram_gb"),
            "disk_c_free_gb": (disks.get("C") or {}).get("free_gb"),
            "disk_d_free_gb": (disks.get("D") or {}).get("free_gb"),
            "heroku_status": hk.get("status") or ("OK" if hk.get("ok") else "UNKNOWN"),
            "auto_admin_logon": maint.get("auto_admin_logon", sys_i.get("auto_logon")),
            "wu_reboot": bool(maint.get("wu_reboot_required") or sys_i.get("wu_reboot")),
            "cbs_reboot": bool(maint.get("cbs_reboot_pending") or sys_i.get("cbs_reboot")),
            "latest_daily_backup": maint.get("latest_daily_backup"),
        },
        "integrity": {
            "keep_private": common_ini.get("keep_private"),
            "ex5_matched": integrity.get("ex5_expected_matched"),
            "ex5_found": integrity.get("ex5_found_count"),
            "ex5_mismatches": len(integrity.get("ex5_mismatches") or []),
            "red_news_rows": rem_csv.get("rows"),
            "red_news_sha16": rem_csv.get("sha256"),
        },
        "audit": {
            "total_rows": audit.get("total_audit_rows", 0),
            "order_fills": ev_map.get("ORDER_FILL", 0),
            "fill_unresolved": ev_map.get("FILL_UNRESOLVED", 0),
            "median_latency_ms": lat_info.get("median"),
        },
        "scoreboard": scoreboard,
    }
    return cutover.sanitize_output(raw)


def render_morning_digest_vi(digest: dict[str, Any]) -> str:
    """Render a crisp <= 35-line plain-Vietnamese Morning/Weekly Ops Digest (0 bare $, 0 IPs/URLs)."""
    ov = digest.get("overall_status", "OFFLINE")
    ov_vi = {"HEALTHY": "KHOE MANH (XANH)", "DEGRADED": "CAN CHU Y (VANG/DO)", "OFFLINE": "MAT KET NOI (OFFLINE)"}.get(ov, ov)

    lines = [
        "============================================================",
        f"BAN TIN VAN HANH NAQEX-NODE1 (CHI DOC | OrderSend=0)",
        f"Thoi diem UTC : {digest.get('checked_utc')} | Trang thai: {ov_vi}",
        "============================================================",
    ]
    if ov == "OFFLINE":
        lines.extend([
            f"- Loi ket noi : {digest.get('probe_error', 'Khong truy cap duoc SSH')}",
            "- Hanh dong   : Kiem tra nguon/mang naqex-node1 va canh bao Telegram.",
            f"- Cutover     : BLOCKED (0/10 cong)",
        ])
    else:
        nd = digest.get("node", {})
        inf = digest.get("infra", {})
        ig = digest.get("integrity", {})
        au = digest.get("audit", {})
        sb = digest.get("scoreboard", {})

        lat_med = au.get("median_latency_ms")
        lat_str = f"{lat_med}ms" if lat_med is not None else "N/A"
        sb_trades = sb.get("trades") if sb.get("trades") is not None else 0
        sb_net = f"{sb.get('net_usd')} USD" if sb.get("net_usd") is not None else "N/A"
        sb_swap = sb.get("swap_zero_ok") if sb.get("swap_zero_ok") is not None else "N/A"
        lines.extend([
            "1. MT5 & Quan tri rui ro:",
            f"   - Ket noi={nd.get('terminal_connected')} | Che do={nd.get('regime')} | DryRun={nd.get('dry_run')} | HbAge={nd.get('age_sec')}s",
            f"   - So du={nd.get('balance_usd')} USD | Von rong={nd.get('equity_usd')} USD | DD ngay={nd.get('daily_dd_pct')}% | DD tinh={nd.get('static_dd_pct')}%",
            f"   - Vi the mo={nd.get('open_positions')} | Lenh thieu SL={nd.get('orphan_no_sl')} | KillSwitch={nd.get('kill_switch')}",
            f"   - PropGuard: OK={nd.get('propguard_ok_count')} | Canh bao={nd.get('propguard_warn_count')}",
            "2. Toan ven nhi phan & Lich tin do:",
            f"   - EX5 SHA-256: khop {ig.get('ex5_matched')}/{ig.get('ex5_found')} (lech={ig.get('ex5_mismatches')}) | KeepPrivate={ig.get('keep_private')}",
            f"   - Tin do CSV : {ig.get('red_news_rows')} dong (sha16={ig.get('red_news_sha16')})",
            "3. Ha tang 24/5 & Sao luu:",
            f"   - NTP={inf.get('ntp_offset')} | Uptime={inf.get('uptime_hr')}h | RAM trong={inf.get('free_ram_gb')} GB | O C={inf.get('disk_c_free_gb')} GB / D={inf.get('disk_d_free_gb')} GB",
            f"   - AutoLogon={inf.get('auto_admin_logon')} | Reboot cho (WU/CBS)={inf.get('wu_reboot')}/{inf.get('cbs_reboot')} | Heroku={inf.get('heroku_status')}",
            f"   - Sao luu ngay gan nhat (D:\\NaqexBackup\\daily): {inf.get('latest_daily_backup')}",
            "4. Nhat ky khop lenh & Bang diem Challenge:",
            f"   - Audit CSV  : {au.get('total_rows')} dong | Fills={au.get('order_fills')} | Unresolved={au.get('fill_unresolved')} | Tre P50={lat_str}",
            (
                f"   - Scoreboard : {sb.get('status')} | Lenh={sb_trades} | Rong={sb_net} | Swap0={sb_swap}"
                if sb.get("present")
                else f"   - Scoreboard : {sb.get('status')} (chua co file cuc bo)"
            ),
            "5. Cong san sang chuyen doi (Cutover Pre-Flight):",
            f"   - Phan quyet : {digest.get('cutover_verdict')} ({digest.get('gates_passed')}/{digest.get('gates_total')} cong DAT) | Preset={digest.get('target_preset')}",
        ])
        failed = digest.get("failed_gates") or []
        if failed:
            lines.append(f"   - Cong chan  : {', '.join(failed)}")

    lines.append("============================================================")
    return cutover.sanitize_text("\n".join(lines[:35]))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="1-Command Read-Only Morning/Weekly Ops Digest for naqex-node1 (OrderSend=0).")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live-readonly", action="store_true", help="Query naqex-node1 read-only via node_ctl.py.")
    mode.add_argument("--offline-fixture", type=Path, help="Read offline JSON fixture with status/integrity/maint/audit.")
    ap.add_argument("--preset", type=str, default=cutover.DEFAULT_PRESET)
    ap.add_argument("--scoreboard", type=Path, default=DEFAULT_SCOREBOARD_PATH)
    ap.add_argument("--host", type=str, default=None)
    ap.add_argument("--json", action="store_true", help="Emit sanitized JSON only.")
    args = ap.parse_args(argv)

    sb = load_optional_scoreboard(args.scoreboard)
    local_kit = cutover.verify_local_kit_and_preset(args.preset)
    now_dt: datetime | None = None
    st = ig = mt = au = None
    probe_err: str | None = None

    if args.offline_fixture is not None:
        try:
            fx = json.loads(args.offline_fixture.read_text(encoding="utf-8"))
            st, ig, mt, au = fx.get("status"), fx.get("integrity"), fx.get("maint"), fx.get("audit")
            if fx.get("now_utc"):
                now_dt = datetime.fromisoformat(str(fx["now_utc"]).replace("Z", "+00:00"))
        except Exception as exc:
            probe_err = f"Fixture read error: {exc}"
    else:
        try:
            st, ig, mt, au = cutover.run_live_readonly_probes(host=args.host)
        except Exception as exc:
            probe_err = str(exc)

    digest = build_ops_digest(
        status=st,
        integrity=ig,
        maint=mt,
        audit=au,
        local_kit=local_kit,
        scoreboard=sb,
        probe_error=probe_err,
        now_utc=now_dt,
    )
    if args.json:
        print(json.dumps(digest, indent=2, ensure_ascii=False))
    else:
        print(render_morning_digest_vi(digest))
    return 0 if digest["overall_status"] == "HEALTHY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
