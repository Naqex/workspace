"""Production Ops Monitor: MT5 Heartbeat Watchdog, Orphan Position Detector & Dry-Run Safe Webhook Bridge.

Reads `naqex_heartbeat.json` (written every 15s by `Naqex_AccountOrchestrator.mq5`) and checks:
  - Heartbeat staleness (> 180s -> VPS/MT5 disconnect alert)
  - Kill-Switch activation or RED/AMBER brake regime transitions
  - Orphan / no-SL positions (`orphan_no_sl > 0`)
  - Dry-run vs live safety state
Never stores or reads secrets from repo; webhook dispatch is opt-in via env var `NAQEX_ALERT_WEBHOOK_URL`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import time
import urllib.request


def inspect_heartbeat(
    heartbeat_path: Path,
    *,
    now_utc_ts: int | None = None,
    stale_after_sec: int = 180,
) -> dict:
    now_ts = int(now_utc_ts if now_utc_ts is not None else time.time())
    if not heartbeat_path.exists():
        return {
            "status": "CRITICAL",
            "alerts": [f"Missing MT5 heartbeat file: {heartbeat_path.name}"],
            "age_seconds": None,
            "payload": None,
        }
    data = json.loads(heartbeat_path.read_text(encoding="utf-8"))
    age = max(0, now_ts - int(data.get("utc_ts", 0)))
    alerts = []
    status = "OK"

    if age > stale_after_sec:
        status = "CRITICAL"
        alerts.append(f"HEARTBEAT_STALE: last update {age}s ago (> {stale_after_sec}s) — check VPS/MT5 terminal")
    if bool(data.get("kill_switch", False)):
        status = "CRITICAL"
        alerts.append(f"GLOBAL_KILLSWITCH_ACTIVE: daily_dd={data.get('daily_dd_pct')}% static_dd={data.get('static_dd_pct')}%")
    if int(data.get("orphan_no_sl", 0)) > 0:
        status = "CRITICAL"
        alerts.append(f"ORPHAN_NO_SL_POSITIONS: count={data.get('orphan_no_sl')} — manual inspection required")
    regime = str(data.get("regime", "NORMAL"))
    if regime in ("AMBER_BRAKE", "RED_BRAKE"):
        if status == "OK":
            status = "WARNING"
        alerts.append(f"RISK_REGIME={regime} (risk_mult={data.get('risk_mult')}x, static_dd={data.get('static_dd_pct')}%)")

    return {
        "status": status,
        "age_seconds": age,
        "alerts": alerts,
        "payload": data,
    }


def format_alert_message(report: dict, *, account_label: str = "NAQEX_MT5") -> str:
    st = report["status"]
    p = report.get("payload") or {}
    header = f"[{st}] {account_label} | Eq={p.get('equity', 'N/A')} | DD_day={p.get('daily_dd_pct', 'N/A')}% | DD_stat={p.get('static_dd_pct', 'N/A')}% | Mult={p.get('risk_mult', 'N/A')}x"
    if not report["alerts"]:
        return header + " | All guards healthy."
    return header + "\n" + "\n".join(f" - {a}" for a in report["alerts"])


def dispatch_alert(report: dict, *, account_label: str = "NAQEX_MT5", dry_run: bool = True) -> dict:
    """Format alert payload; only posts to NAQEX_ALERT_WEBHOOK_URL if dry_run=False AND env var is set."""
    msg = format_alert_message(report, account_label=account_label)
    url = os.environ.get("NAQEX_ALERT_WEBHOOK_URL", "").strip()
    if dry_run or not url:
        return {"sent": False, "dry_run": True, "message": msg}
    body = json.dumps({"text": msg, "content": msg}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return {"sent": True, "dry_run": False, "http_status": resp.status, "message": msg}
