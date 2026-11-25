"""Fail-Closed Read-Only Cutover & DR Pre-Flight Verifier for `naqex-node1` (`OrderSend = 0`).

Verifies every mandatory precondition before cutting over `naqex-node1` from legacy 9 charts to
single-authority `Naqex_Master_Prop7E.ex5` or onboarding a paid Black Friday FTMO 10K account:
  1. Broker connected, heartbeat fresh (<= 180s), `positions_state == CONFIRMED`
  2. Strictly flat (`open_positions == 0`, `total_account_positions == 0`, `pending_orders == 0`, `orphan_no_sl == 0`)
  3. MT5 credential & config safety (`KeepPrivate == 1`, no `Login=` override in `connector.ini`)
  4. Windows 24/5 lock (`AutoAdminLogon == 1`, `wu_reboot == false`, `cbs_reboot == false`, `NoAutoUpdate == 1`)
  5. Local & remote binary integrity (`10/10` `.ex5` SHA-256 match, `0` mismatches)
  6. Red-news calendar parity (`>= 492` rows + exact SHA-256 match vs local `naqex_red_news_utc.csv`)
  7. Target `.set` preset exists & passes `verify_deployment_kit.py` fail-closed schema audit
  8. Backup freshness (`D:\\NaqexBackup\\daily\\` latest daily snapshot <= 2 days old)
  9. Execution audit hygiene (`0` `FILL_UNRESOLVED` events)

STRICTLY READ-ONLY: ZERO `OrderSend`, ZERO MT5/MetaEditor launches, ZERO remote writes, ZERO IP/secret leaks.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0

OPS_CLOUD_DIR = Path(__file__).resolve().parent
AI_ENGINES_DIR = OPS_CLOUD_DIR.parent
EXPORTS_DIR = AI_ENGINES_DIR / "exports"
KIT_DIR = EXPORTS_DIR / "deployment_kit"
REPO_ROOT = AI_ENGINES_DIR.parents[1]
DEFAULT_EX5_DIR = REPO_ROOT / ".runtime/mt5-compiled-ex5"
DEFAULT_PRESET = "FTMO_Std10K_MasterProp7E_P1_Sprint_4x.set"

for p in (OPS_CLOUD_DIR, EXPORTS_DIR, AI_ENGINES_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import node_ctl  # noqa: E402
import verify_deployment_kit as kit  # noqa: E402

_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_SECRET_KV_RE = re.compile(r"(?i)\b(password|passwd|token|api[_-]?key|secret|webhook)\s*[:=]\s*\S+")
_BACKUP_DATE_RE = re.compile(r"(\d{4})[-_]?(\d{2})[-_]?(\d{2})")
_REDACT_KEYS = {"_ssh_host", "password", "token", "webhook", "api_key", "secret"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sanitize_text(text: str) -> str:
    out = _URL_RE.sub("[REDACTED_URL]", text)
    out = _SECRET_KV_RE.sub(r"\1=[REDACTED]", out)
    out = _IPV4_RE.sub("[REDACTED_IP]", out)
    out = out.replace("$", "USD ")
    return out


def sanitize_output(obj: Any) -> Any:
    """Recursively strip IPs, URLs, secrets, and bare dollar signs from any JSON payload."""
    if isinstance(obj, dict):
        cleaned: dict[str, Any] = {}
        for k, v in obj.items():
            if str(k).lower() in _REDACT_KEYS:
                continue
            cleaned[k] = sanitize_output(v)
        return cleaned
    if isinstance(obj, list):
        return [sanitize_output(x) for x in obj]
    if isinstance(obj, str):
        return sanitize_text(obj)
    return obj


def parse_backup_age_days(latest_backup_name: str | None, *, now_utc: datetime | None = None) -> tuple[bool, int | None, str]:
    """Parse latest backup folder date under `D:\\NaqexBackup\\daily\\` and return (parsed_ok, age_days, date_iso)."""
    if not latest_backup_name or not isinstance(latest_backup_name, str):
        return False, None, "MISSING"
    m = _BACKUP_DATE_RE.search(latest_backup_name.strip())
    if not m:
        return False, None, "UNPARSEABLE"
    try:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        bak_dt = datetime(y, mo, d, tzinfo=timezone.utc)
    except ValueError:
        return False, None, "INVALID_DATE"
    ref = now_utc or datetime.now(timezone.utc)
    ref_day = datetime(ref.year, ref.month, ref.day, tzinfo=timezone.utc)
    age_days = max(0, (ref_day - bak_dt).days)
    return True, age_days, f"{y:04d}-{mo:02d}-{d:02d}"


def verify_local_kit_and_preset(
    preset_name: str,
    *,
    exports_dir: Path = EXPORTS_DIR,
    kit_dir: Path = KIT_DIR,
    ex5_dir: Path = DEFAULT_EX5_DIR,
    require_local_ex5: bool = True,
) -> dict[str, Any]:
    """Verify local deployment kit, 10/10 compiled `.ex5` SHA-256, 492-row CSV SHA, and target `.set` preset."""
    preset_rel = preset_name.replace("\\", "/").lstrip("/")
    candidates = [
        kit_dir / "presets" / preset_rel,
        kit_dir / preset_rel,
        Path(preset_name),
    ]
    preset_path: Path | None = None
    for cand in candidates:
        if cand.is_file():
            preset_path = cand
            break

    has_ex5_dir = ex5_dir.is_dir() and len(list(ex5_dir.glob("*.ex5"))) >= 10
    kit_rep = kit.verify_kit(
        exports_dir=exports_dir,
        kit_dir=kit_dir,
        ex5_dir=ex5_dir,
        require_ex5=(require_local_ex5 and has_ex5_dir),
    )

    csv_path = exports_dir / "Files/naqex_red_news_utc.csv"
    local_csv_rows = 0
    local_csv_sha = ""
    if csv_path.is_file():
        lines = [ln for ln in csv_path.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
        local_csv_rows = max(0, len(lines) - 1)
        local_csv_sha = sha256_file(csv_path).lower()

    preset_kv: dict[str, str] = {}
    preset_fail_closed = False
    if preset_path is not None:
        preset_kv = kit.parse_set_file(preset_path)
        preset_fail_closed = (
            preset_kv.get("InpDryRunLogOnly") == "true"
            and preset_kv.get("InpGuardDryRunLogOnly") == "true"
            and preset_kv.get("InpGuardEnableRedNews") == "true"
        )

    return {
        "preset_name": preset_name,
        "preset_exists": preset_path is not None,
        "preset_fail_closed": preset_fail_closed,
        "preset_sku": preset_kv.get("InpContractSku", ""),
        "kit_ok": bool(kit_rep.get("ok")),
        "kit_errors": list(kit_rep.get("errors", []))[:10],
        "local_ex5_verified_count": int(kit_rep.get("verified_ex5_files", 0)),
        "local_ex5_dir_present": has_ex5_dir,
        "local_csv_rows": local_csv_rows,
        "local_csv_sha16": local_csv_sha[:16],
    }


def evaluate_cutover_readiness(
    *,
    status: dict[str, Any],
    integrity: dict[str, Any],
    maint: dict[str, Any],
    audit: dict[str, Any],
    local_kit: dict[str, Any],
    max_heartbeat_age_sec: int = 180,
    max_backup_age_days: int = 2,
    required_ex5_count: int = 10,
    required_red_news_rows: int = 492,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate all fail-closed cutover preconditions and return sanitized readiness verdict."""
    gates: list[dict[str, Any]] = []

    def add_gate(gate_id: str, passed: bool, detail: str, remediation: str = "") -> None:
        gates.append(
            {
                "id": gate_id,
                "status": "PASS" if passed else "BLOCK",
                "detail": detail,
                "remediation": "" if passed else remediation,
            }
        )

    hb = status.get("heartbeat") if isinstance(status.get("heartbeat"), dict) else {}
    sys_info = status.get("system") if isinstance(status.get("system"), dict) else {}

    # Gate 1: Broker connection & fresh confirmed heartbeat
    term_conn = hb.get("terminal_connected") is True
    pos_state = str(hb.get("positions_state") or "UNKNOWN")
    age_sec = hb.get("age_sec")
    age_ok = isinstance(age_sec, (int, float)) and 0 <= float(age_sec) <= max_heartbeat_age_sec
    add_gate(
        "terminal_connected_and_heartbeat_fresh",
        term_conn and pos_state == "CONFIRMED" and age_ok,
        f"terminal_connected={term_conn}, positions_state={pos_state}, age_sec={age_sec} (max {max_heartbeat_age_sec}s)",
        "Kiem tra MT5 dang chay tren naqex-node1, ket noi broker xanh va naqex_heartbeat.json cap nhat < 180s.",
    )

    # Gate 2: Strictly flat (0 Naqex positions, 0 total account positions, 0 pending orders)
    open_pos = hb.get("open_positions")
    total_pos = hb.get("total_account_positions", open_pos)
    pending_ord = hb.get("pending_orders", 0)
    flat_ok = (
        isinstance(open_pos, int)
        and open_pos == 0
        and isinstance(total_pos, int)
        and total_pos == 0
        and isinstance(pending_ord, int)
        and pending_ord == 0
    )
    add_gate(
        "flat_positions_zero",
        flat_ok,
        f"open_positions={open_pos}, total_account_positions={total_pos}, pending_orders={pending_ord}",
        "TUYET DOI KHONG cutover khi con vi the/lenh cho; doi phang lenh 100% (sau 20:55 UTC hoac cuoi tuan).",
    )

    # Gate 3: Zero orphan no-SL positions
    orphan = hb.get("orphan_no_sl")
    orphan_ok = isinstance(orphan, int) and orphan == 0
    add_gate(
        "orphan_no_sl_zero",
        orphan_ok,
        f"orphan_no_sl={orphan}",
        "Kiem tra ngay tab Trade tren MT5 va dong/dat SL cho vi the thieu SL truoc khi thao tac.",
    )

    # Gate 4: KeepPrivate == 1 and no Login= override in connector.ini
    common_ini = integrity.get("common_ini") if isinstance(integrity.get("common_ini"), dict) else {}
    conn_ini = integrity.get("connector_ini") if isinstance(integrity.get("connector_ini"), dict) else {}
    kp_ok = str(common_ini.get("keep_private")) == "1" and not bool(conn_ini.get("has_login_override"))
    add_gate(
        "keep_private_and_ini_clean",
        kp_ok,
        f"KeepPrivate={common_ini.get('keep_private')}, connector_login_override={conn_ini.get('has_login_override')}",
        "Dat KeepPrivate=1 trong Config/common.ini va xoa dong Login= trong connector.ini.",
    )

    # Gate 5: Windows 24/5 locks (AutoAdminLogon=1, wu_reboot=false, cbs_reboot=false, NoAutoUpdate=1)
    wu_rb = bool(maint.get("wu_reboot_required")) or bool(sys_info.get("wu_reboot"))
    cbs_rb = bool(maint.get("cbs_reboot_pending")) or bool(sys_info.get("cbs_reboot"))
    auto_logon_val = maint.get("auto_admin_logon", sys_info.get("auto_logon"))
    au_pol = maint.get("au_policy") if isinstance(maint.get("au_policy"), dict) else {}
    no_auto_upd = au_pol.get("NoAutoUpdate", sys_info.get("no_auto_update"))
    win_ok = (not wu_rb) and (not cbs_rb) and str(auto_logon_val) == "1" and str(no_auto_upd) == "1"
    add_gate(
        "windows_24x5_autologon_and_no_reboot",
        win_ok,
        f"AutoAdminLogon={auto_logon_val}, NoAutoUpdate={no_auto_upd}, wu_reboot={wu_rb}, cbs_reboot={cbs_rb}",
        "Bat AutoAdminLogon=1, khoa NoAutoUpdate=1 va khoi dong lai sach (khi phang lenh) neu con co reboot.",
    )

    # Gate 6: 10/10 .ex5 SHA-256 integrity (both local deployment kit and remote node)
    rem_found = int(integrity.get("ex5_found_count", 0) or 0)
    rem_matched = int(integrity.get("ex5_expected_matched", 0) or 0)
    rem_mismatches = integrity.get("ex5_mismatches") or []
    loc_ex5_cnt = int(local_kit.get("local_ex5_verified_count", 0) or 0)
    ex5_ok = (
        len(rem_mismatches) == 0
        and rem_found >= required_ex5_count
        and rem_matched >= required_ex5_count
        and loc_ex5_cnt >= required_ex5_count
    )
    add_gate(
        "ex5_sha256_10_of_10_match",
        ex5_ok,
        f"remote_found={rem_found}/{required_ex5_count}, remote_matched={rem_matched}/{required_ex5_count}, mismatches={len(rem_mismatches)}, local_verified={loc_ex5_cnt}/{required_ex5_count}",
        "Chay sync_updated_ex5_when_flat.ps1 -IncludeMasterEx5 -RequireManifest khi phang lenh de dong bo du 10/10 file .ex5.",
    )

    # Gate 7: 492-row red-news CSV exact SHA-256 match
    rem_csv = integrity.get("red_news_csv") if isinstance(integrity.get("red_news_csv"), dict) else {}
    rem_rows = int(rem_csv.get("rows", 0) or 0)
    rem_sha16 = str(rem_csv.get("sha256") or "").lower()
    loc_rows = int(local_kit.get("local_csv_rows", 0) or 0)
    loc_sha16 = str(local_kit.get("local_csv_sha16") or "").lower()
    sha_same = bool(rem_sha16 and loc_sha16 and rem_sha16 == loc_sha16)
    csv_ok = (
        bool(rem_csv.get("exists"))
        and rem_csv.get("sha_match") is not False
        and rem_rows >= required_red_news_rows
        and loc_rows >= required_red_news_rows
        and sha_same
    )
    add_gate(
        "red_news_492_csv_sha_match",
        csv_ok,
        f"remote_rows={rem_rows}, local_rows={loc_rows}, sha16_match={sha_same} (rem={rem_sha16 or 'NONE'}, loc={loc_sha16 or 'NONE'})",
        "Dong bo lai naqex_red_news_utc.csv (492 dong) bang sync_updated_ex5_when_flat.ps1 truoc khi chay.",
    )

    # Gate 8: Target .set preset exists, fail-closed, and full deployment kit schema PASS
    preset_ok = (
        bool(local_kit.get("preset_exists"))
        and bool(local_kit.get("preset_fail_closed"))
        and bool(local_kit.get("kit_ok"))
    )
    add_gate(
        "target_preset_and_kit_schema_valid",
        preset_ok,
        f"preset={local_kit.get('preset_name')}, exists={local_kit.get('preset_exists')}, fail_closed={local_kit.get('preset_fail_closed')}, kit_ok={local_kit.get('kit_ok')}",
        "Kiem tra lai ten file .set trong deployment_kit/presets/ va chay verify_deployment_kit.py --require-ex5.",
    )

    # Gate 9: D:\NaqexBackup\daily\ backup freshness
    latest_bak = maint.get("latest_daily_backup")
    bak_parsed, bak_age, bak_iso = parse_backup_age_days(latest_bak, now_utc=now_utc)
    bak_ok = bak_parsed and bak_age is not None and bak_age <= max_backup_age_days
    add_gate(
        "daily_backup_fresh",
        bak_ok,
        f"latest_daily_backup={latest_bak} (parsed={bak_iso}, age_days={bak_age}, max={max_backup_age_days}d)",
        "Chay lai tac vu sao luu Naqex_DailyBackup vao D:\\NaqexBackup\\daily\\ truoc khi cutover.",
    )

    # Gate 10: Execution audit has zero FILL_UNRESOLVED & PropGuard zero warnings
    events_by_type = audit.get("events_by_type") if isinstance(audit.get("events_by_type"), dict) else {}
    fill_unres = int(events_by_type.get("FILL_UNRESOLVED", 0) or 0)
    pg_warn = int(status.get("propguard_warn_count", 0) or 0)
    audit_ok = (fill_unres == 0) and (pg_warn == 0)
    add_gate(
        "exec_audit_and_propguard_clean",
        audit_ok,
        f"FILL_UNRESOLVED={fill_unres}, propguard_warn_count={pg_warn}, total_audit_rows={audit.get('total_audit_rows', 0)}",
        "Ra soat naqex_exec_audit.csv va log MQL5 xu ly dut diem canh bao PropGuard / FILL_UNRESOLVED.",
    )

    failed_gates = [g["id"] for g in gates if g["status"] != "PASS"]
    verdict = "READY_FOR_CUTOVER" if not failed_gates else "BLOCKED"

    raw_result = {
        "schema": "naqex-node-cutover-dryrun-v1",
        "checked_utc": (now_utc or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "order_send_count": ORDER_SEND_COUNT,
        "verdict": verdict,
        "target_preset": local_kit.get("preset_name"),
        "target_sku": local_kit.get("preset_sku", ""),
        "gates_passed": sum(1 for g in gates if g["status"] == "PASS"),
        "gates_total": len(gates),
        "failed_gates": failed_gates,
        "gates": gates,
        "node_snapshot": {
            "regime": hb.get("regime"),
            "dry_run": hb.get("dry_run"),
            "open_positions": open_pos,
            "orphan_no_sl": orphan,
            "ntp_offset": status.get("ntp_offset"),
            "propguard_ok_count": status.get("propguard_ok_count"),
            "latest_daily_backup": latest_bak,
            "remote_ex5_found": rem_found,
            "remote_ex5_matched": rem_matched,
            "remote_csv_rows": rem_rows,
        },
    }
    return sanitize_output(raw_result)


def render_vietnamese_report(result: dict[str, Any]) -> str:
    """Render a crisp, plain-Vietnamese cutover readiness report (zero bare dollar signs, zero IPs)."""
    verdict_vi = (
        "SAN SANG CHUYEN DOI (READY_FOR_CUTOVER)"
        if result["verdict"] == "READY_FOR_CUTOVER"
        else "DANG BI CHAN (BLOCKED - CHUA DU DIEU KIEN)"
    )
    lines = [
        f"=== KIEM TRA TIEN CHUYEN DOI NAQEX-NODE1 (CHI DOC, OrderSend=0) ===",
        f"Thoi diem UTC : {result['checked_utc']}",
        f"Preset muc tieu: {result['target_preset']} ({result.get('target_sku') or 'N/A'})",
        f"Phan quyet    : {verdict_vi} ({result['gates_passed']}/{result['gates_total']} cong DAT)",
        "",
        "Chi tiet tung cong an toan:",
    ]
    for g in result["gates"]:
        tag = "[DAT] " if g["status"] == "PASS" else "[CHAN]"
        lines.append(f"  {tag} {g['id']}: {g['detail']}")
        if g.get("remediation"):
            lines.append(f"         -> Khac phuc: {g['remediation']}")
    return sanitize_text("\n".join(lines))


def run_live_readonly_probes(
    *,
    host: str | None = None,
    timeout: int = 20,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Run all 4 read-only node_ctl probes (`status`, `integrity`, `maint`, `audit`) with OrderSend=0."""
    st = node_ctl.run_remote_probe("status", host=host, timeout=timeout)
    ig = node_ctl.run_remote_probe("integrity", host=host, timeout=timeout)
    mt = node_ctl.run_remote_probe("maint", host=host, timeout=timeout)
    au = node_ctl.run_remote_probe("audit", host=host, timeout=timeout)
    return st, ig, mt, au


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Read-only pre-flight cutover verifier for naqex-node1 (OrderSend=0).")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline-fixture", type=Path, help="Path to offline JSON fixture with status/integrity/maint/audit.")
    mode.add_argument("--live-readonly", action="store_true", help="Query naqex-node1 strictly read-only via node_ctl.py.")
    ap.add_argument("--preset", type=str, default=DEFAULT_PRESET, help="Target .set preset filename in deployment_kit/presets/.")
    ap.add_argument("--host", type=str, default=None, help="Optional SSH alias override for --live-readonly.")
    ap.add_argument("--max-heartbeat-age", type=int, default=180)
    ap.add_argument("--max-backup-age-days", type=int, default=2)
    ap.add_argument("--json", action="store_true", help="Print sanitized JSON payload only.")
    args = ap.parse_args(argv)

    try:
        if args.offline_fixture is not None:
            fixture = json.loads(args.offline_fixture.read_text(encoding="utf-8"))
            st = fixture.get("status", {})
            ig = fixture.get("integrity", {})
            mt = fixture.get("maint", {})
            au = fixture.get("audit", {})
            now_override = fixture.get("now_utc")
            now_dt = datetime.fromisoformat(now_override.replace("Z", "+00:00")) if now_override else None
        else:
            st, ig, mt, au = run_live_readonly_probes(host=args.host)
            now_dt = None

        local_kit = verify_local_kit_and_preset(args.preset)
        result = evaluate_cutover_readiness(
            status=st,
            integrity=ig,
            maint=mt,
            audit=au,
            local_kit=local_kit,
            max_heartbeat_age_sec=args.max_heartbeat_age,
            max_backup_age_days=args.max_backup_age_days,
            now_utc=now_dt,
        )
    except Exception as exc:
        err_payload = sanitize_output({"ok": False, "order_send_count": 0, "verdict": "ERROR", "error": str(exc)})
        print(json.dumps(err_payload, indent=2, ensure_ascii=False), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(render_vietnamese_report(result))
        print("\n--- JSON ---")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["verdict"] == "READY_FOR_CUTOVER" else 2


if __name__ == "__main__":
    raise SystemExit(main())
