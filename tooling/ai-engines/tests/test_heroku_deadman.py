"""Integration & unit tests for Naqex Heroku Dead-Man's-Switch & Windows 10 PC Heartbeat Sender."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import threading
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
HEROKU_DIR = ROOT / "tooling/ai-engines/ops_cloud/heroku_deadman"
if str(HEROKU_DIR) not in sys.path:
    sys.path.insert(0, str(HEROKU_DIR))

import app as deadman_app  # noqa: E402
import pc_heartbeat_sender as pc_sender  # noqa: E402


def _req(url: str, *, method: str = "GET", headers: dict | None = None, body: dict | None = None) -> tuple[int, str]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    hdrs = dict(headers or {})
    if body is not None:
        hdrs.setdefault("Content-Type", "application/json")
    r = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def test_deadman_auth_alerts_stale_recovery_and_mobile_dashboard():
    assert deadman_app.ORDER_SEND_COUNT == 0
    now_box = [1_795_500_000.0]
    emitted: list[str] = []

    def fake_send(msg: str) -> dict:
        emitted.append(msg)
        return {"sent": ["mock"], "errors": [], "configured": True}

    mon = deadman_app.DeadmanMonitor(
        ingest_token="secret-test-token-123",
        view_token="view-secret-456",
        stale_after_sec=180,
        alert_cooldown_sec=900,
        alert_sender=fake_send,
        clock_fn=lambda: now_box[0],
    )
    srv = deadman_app.create_server(mon, host="127.0.0.1", port=0)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    base = f"http://127.0.0.1:{port}"

    try:
        # 1. Health endpoint works without auth
        st, raw = _req(f"{base}/health")
        assert st == 200 and json.loads(raw)["order_send_count"] == 0

        # 2. Ingest fails closed without valid Bearer token
        st, raw = _req(f"{base}/api/heartbeat", method="POST", body={"account_label": "PC1"})
        assert st == 401 and json.loads(raw)["error"] == "MISSING_BEARER_TOKEN"

        st, raw = _req(
            f"{base}/api/heartbeat",
            method="POST",
            headers={"Authorization": "Bearer wrong-token"},
            body={"account_label": "PC1"},
        )
        assert st == 401 and json.loads(raw)["error"] == "INVALID_BEARER_TOKEN"

        # 3. Valid healthy heartbeat ingests cleanly with 0 alerts
        st, raw = _req(
            f"{base}/api/heartbeat",
            method="POST",
            headers={"Authorization": "Bearer secret-test-token-123"},
            body={
                "account_label": "FTMO_HOME_PC",
                "mt5_running": True,
                "heartbeat": {"balance": 10000.0, "equity": 10004.5, "open_positions": 1, "orphan_no_sl": 0, "regime": "NORMAL", "kill_switch": False},
            },
        )
        assert st == 200 and json.loads(raw)["status"] == "OK"
        assert len(emitted) == 0

        # 4. Mobile dashboard requires view token when configured
        st, _ = _req(f"{base}/")
        assert st == 401
        st, html_doc = _req(f"{base}/?token=view-secret-456")
        assert st == 200 and "FTMO_HOME_PC" in html_doc and "10004.5" in html_doc

        # 5. Simulate PC power loss (> 180s without heartbeat) -> STALE alert fires ONCE (cooldown blocks spam!)
        now_box[0] += 210.0
        staled = mon.check_stale_nodes()
        assert len(staled) == 1
        assert len(emitted) == 1 and "[PC_OFFLINE]" in emitted[-1]
        # Second check 30s later within cooldown -> no duplicate spam
        now_box[0] += 30.0
        mon.check_stale_nodes()
        assert len(emitted) == 1

        # 6. PC comes back online -> RECOVERED alert fires immediately!
        st, raw = _req(
            f"{base}/api/heartbeat",
            method="POST",
            headers={"Authorization": "Bearer secret-test-token-123"},
            body={
                "account_label": "FTMO_HOME_PC",
                "mt5_running": True,
                "heartbeat": {"balance": 10000.0, "equity": 10005.0, "open_positions": 1, "orphan_no_sl": 0, "regime": "NORMAL", "kill_switch": False},
            },
        )
        assert st == 200
        assert len(emitted) == 2 and "[RECOVERED]" in emitted[-1]

        # 7. Orphan no-SL position -> CRITICAL alert fires immediately!
        st, raw = _req(
            f"{base}/api/heartbeat",
            method="POST",
            headers={"Authorization": "Bearer secret-test-token-123"},
            body={
                "account_label": "FTMO_HOME_PC",
                "mt5_running": True,
                "heartbeat": {"balance": 10000.0, "equity": 9980.0, "open_positions": 1, "orphan_no_sl": 1, "regime": "NORMAL", "kill_switch": False},
            },
        )
        assert st == 200 and json.loads(raw)["status"] == "CRITICAL"
        assert len(emitted) == 3 and "ORPHAN_NO_SL=1" in emitted[-1]
    finally:
        srv.shutdown()
        srv.server_close()


def test_deadman_fails_closed_when_ingest_token_unset():
    mon = deadman_app.DeadmanMonitor(ingest_token="")
    ok, err = mon.verify_ingest_token("Bearer anything")
    assert ok is False and err == "INGEST_TOKEN_NOT_CONFIGURED"


def test_pc_heartbeat_sender_dry_run_and_heroku_manifest(tmp_path: Path):
    assert pc_sender.ORDER_SEND_COUNT == 0
    hb = tmp_path / "naqex_heartbeat.json"
    hb.write_text(json.dumps({"utc_ts": 1795500000, "balance": 10000.0, "equity": 10004.0, "open_positions": 1, "orphan_no_sl": 0}), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable, "-X", "utf8",
            str(HEROKU_DIR / "pc_heartbeat_sender.py"),
            "--heartbeat-path", str(hb),
            "--endpoint", "https://example.herokuapp.com/api/heartbeat",
            "--account-label", "TEST_PC",
            "--once", "--dry-run", "--skip-process-check",
        ],
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["dry_run"] is True
    assert out["envelope"]["order_send_count"] == 0
    assert out["envelope"]["heartbeat"]["equity"] == 10004.0

    # Verify Heroku deploy files exist & valid JSON
    assert (HEROKU_DIR / "Procfile").read_text(encoding="utf-8").strip() == "web: python app.py"
    app_json = json.loads((HEROKU_DIR / "app.json").read_text(encoding="utf-8"))
    assert app_json["formation"]["web"]["size"] == "basic"
