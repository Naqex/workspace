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
        assert st == 200 and "FTMO_HOME_PC" in html_doc and "10,004.50" in html_doc

        # 5. Simulate PC power loss (> 180s without heartbeat) -> STALE HTML alert fires ONCE (cooldown blocks spam!)
        now_box[0] += 210.0
        staled = mon.check_stale_nodes()
        assert len(staled) == 1
        assert len(emitted) == 1 and "MẤT KẾT NỐI" in emitted[-1] and "3m 30s" in emitted[-1]
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
        assert len(emitted) == 2 and "ĐÃ PHỤC HỒI" in emitted[-1]

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
        assert len(emitted) == 3 and "ORPHAN_NO_SL=1" in emitted[-1] and "CẢNH BÁO KHẨN" in emitted[-1]

        # 8. DELETE /api/nodes/<label> requires Bearer ingest token and prunes stale test nodes cleanly
        st, _ = _req(f"{base}/api/nodes/FTMO_HOME_PC", method="DELETE")
        assert st == 401
        st, raw = _req(
            f"{base}/api/nodes/FTMO_HOME_PC",
            method="DELETE",
            headers={"Authorization": "Bearer secret-test-token-123"},
        )
        assert st == 200 and json.loads(raw)["ok"] is True
        st, raw = _req(f"{base}/api/status?token=view-secret-456")
        assert st == 200 and json.loads(raw)["nodes"] == []
    finally:
        srv.shutdown()
        srv.server_close()


def test_format_duration_vi_and_html_escaping():
    assert deadman_app.format_duration_vi(45) == "45s"
    assert deadman_app.format_duration_vi(210) == "3m 30s"
    assert deadman_app.format_duration_vi(6497) == "1h 48m"
    html_msg, plain_msg = deadman_app.format_alert_message(
        kind="CRITICAL",
        label="NODE<1>&TEST",
        now_ts=1_795_510_560.0,
        hb={"balance": 10000.0, "equity": 10012.5, "open_positions": 1, "orphan_no_sl": 0, "daily_dd_pct": 0.0, "regime": "NORMAL"},
        reasons=["MT5_PROCESS_DOWN"],
    )
    assert "NODE&lt;1&gt;&amp;TEST" in html_msg
    assert "<b>CẢNH BÁO KHẨN</b>" in html_msg
    assert "NODE<1>&TEST" in plain_msg


def test_deadman_fails_closed_when_ingest_token_unset():
    mon = deadman_app.DeadmanMonitor(ingest_token="")
    ok, err = mon.verify_ingest_token("Bearer anything")
    assert ok is False and err == "INGEST_TOKEN_NOT_CONFIGURED"
    # Astra F20: view token fails closed by default when NAQEX_VIEW_TOKEN is empty!
    assert mon.verify_view_token("", "") is False


def test_deadman_f17_retry_failed_alert_broker_disconnect_and_stale_inner_ts():
    now_box = [1_795_500_000.0]
    calls = [0]

    def flaky_send(msg: str) -> dict:
        calls[0] += 1
        if calls[0] == 1:
            return {"sent": [], "errors": ["telegram:timeout"], "configured": True}
        return {"sent": ["telegram"], "errors": [], "configured": True}

    mon = deadman_app.DeadmanMonitor(
        ingest_token="tok",
        view_token="vtok",
        stale_after_sec=180,
        alert_cooldown_sec=900,
        alert_sender=flaky_send,
        clock_fn=lambda: now_box[0],
    )
    # 1. Broker disconnected + replayed stale inner utc_ts -> CRITICAL & tries alert
    r1 = mon.ingest_heartbeat({
        "account_label": "NODE1",
        "mt5_running": True,
        "heartbeat": {"utc_ts": now_box[0] - 400, "terminal_connected": False, "balance": 10000.0, "equity": 10000.0},
    })
    assert r1["status"] == "CRITICAL"
    assert "BROKER_DISCONNECTED" in r1["reasons"]
    assert any(x.startswith("INNER_HEARTBEAT_STALE=") for x in r1["reasons"])
    assert calls[0] == 1

    # 2. First delivery FAILED -> cooldown must NOT be armed -> retries cleanly 15s later!
    now_box[0] += 15.0
    mon.ingest_heartbeat({
        "account_label": "NODE1",
        "mt5_running": True,
        "heartbeat": {"utc_ts": now_box[0] - 415, "terminal_connected": False, "balance": 10000.0, "equity": 10000.0},
    })
    assert calls[0] == 2
    # 3. Second delivery SUCCEEDED -> cooldown IS now armed -> 3rd call 15s later is suppressed!
    now_box[0] += 15.0
    mon.ingest_heartbeat({
        "account_label": "NODE1",
        "mt5_running": True,
        "heartbeat": {"utc_ts": now_box[0] - 430, "terminal_connected": False, "balance": 10000.0, "equity": 10000.0},
    })
    assert calls[0] == 2


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
    assert "heroku-postgresql:essential-0" in app_json["addons"]


def test_win10_home_vps_bootstrap_script_dry_run():
    ps_script = ROOT / "tooling/ai-engines/exports/deployment_kit/vps_kit/setup_win10_home_vps.ps1"
    assert ps_script.is_file()
    proc = subprocess.run(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(ps_script),
            "-HeartbeatJsonPath", "C:\\NaqexMT5\\MQL5\\Files\\naqex_heartbeat.json",
            "-AccountLabel", "FTMO_HOME_PC",
            "-RegisterHerokuHeartbeatTask", "-DryRun",
        ],
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["dry_run"] is True and out["order_send"] == 0
    assert any("DRYRUN_OPENSSH" in a for a in out["actions"])
    assert any("DRYRUN_REGISTER_SCHTASK" in a for a in out["actions"])
