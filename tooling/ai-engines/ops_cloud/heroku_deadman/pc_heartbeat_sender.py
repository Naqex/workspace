"""Windows 10 Home-PC Heartbeat Sender -> Heroku Dead-Man's-Switch (Pure Python Stdlib).

Runs silently on your Windows 10 (`i3-7100`) PC alongside MetaTrader 5:
  - Reads `MQL5/Files/naqex_heartbeat.json`
  - Checks whether `terminal64.exe` is running
  - POSTs lightweight telemetry every 60s to your Heroku Dead-Man's-Switch URL using
    `NAQEX_INGEST_TOKEN` from environment variables (ZERO secrets in files/code, `OrderSend = 0`).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ORDER_SEND_COUNT: int = 0
_NO_WINDOW_FLAGS: int = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0


def is_mt5_process_running(process_name: str = "terminal64.exe") -> bool:
    if sys.platform != "win32":
        return True
    try:
        proc = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
            capture_output=True, text=True, timeout=5, check=False,
            creationflags=_NO_WINDOW_FLAGS,
        )
        return process_name.lower() in (proc.stdout or "").lower()
    except Exception:
        return False


def build_heartbeat_envelope(
    heartbeat_path: Path,
    account_label: str,
    *,
    skip_process_check: bool = False,
) -> dict[str, Any]:
    hb_payload: dict[str, Any] = {}
    hb_present = heartbeat_path.is_file()
    if hb_present:
        try:
            hb_payload = json.loads(heartbeat_path.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:
            hb_payload = {"parse_error": str(exc)}
    return {
        "schema": "naqex-pc-heartbeat-envelope-v1",
        "order_send_count": ORDER_SEND_COUNT,
        "sent_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "account_label": account_label,
        "mt5_running": True if skip_process_check else is_mt5_process_running(),
        "heartbeat_present": hb_present,
        "heartbeat": hb_payload,
    }


def send_heartbeat(
    endpoint_url: str,
    token: str,
    envelope: dict[str, Any],
    *,
    timeout_sec: float = 10.0,
) -> dict[str, Any]:
    raw = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        endpoint_url,
        data=raw,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "Naqex-PC-Sender/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Naqex Home-PC -> Heroku Dead-Man's-Switch Sender (OrderSend=0)")
    ap.add_argument("--heartbeat-path", type=Path, required=True, help="Path to MQL5/Files/naqex_heartbeat.json")
    ap.add_argument("--endpoint", default=os.environ.get("NAQEX_DEADMAN_URL", ""), help="https://<app>.herokuapp.com/api/heartbeat")
    ap.add_argument("--account-label", default="FTMO_DEMO_HOME_PC")
    ap.add_argument("--interval-sec", type=int, default=60)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-process-check", action="store_true")
    args = ap.parse_args(argv)

    token = os.environ.get("NAQEX_INGEST_TOKEN", "").strip()
    if not args.dry_run and (not args.endpoint or not token):
        print(
            "ERROR: Set --endpoint (or NAQEX_DEADMAN_URL) and env NAQEX_INGEST_TOKEN before live sending.",
            file=sys.stderr,
        )
        return 2

    while True:
        env = build_heartbeat_envelope(
            args.heartbeat_path,
            args.account_label,
            skip_process_check=args.skip_process_check,
        )
        if args.dry_run:
            dry_msg = json.dumps({"dry_run": True, "endpoint": args.endpoint, "envelope": env}, ensure_ascii=False)
            print(dry_msg, flush=True)
        else:
            try:
                res = send_heartbeat(args.endpoint, token, env)
                print(json.dumps({"ok": True, "response": res}, ensure_ascii=False), flush=True)
            except Exception as exc:
                print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), flush=True)
        if args.once:
            break
        time.sleep(max(15, int(args.interval_sec)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
