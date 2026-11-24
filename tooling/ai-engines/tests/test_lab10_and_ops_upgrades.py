"""Deterministic tests for Lab #10 (v2 Robust Alpha, Walk-Forward SL/TP, Dynamic Prop Pacing),
MQL5 ResolveExecutedFillPrice + Manual Halt Bridge, Upgraded Control Room 2-Step Safety Cover,
and VPS 24/5 1-Click Deployment & Flat-Only Sync scripts.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import threading
import urllib.error
import urllib.request

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
AI_ENGINES = ROOT / "tooling/ai-engines"
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from cockpit import server as cockpit_server
from quant_factory import lab10_v2_robust_prop_accelerator as lab10


def _http_json(url: str, *, method: str = "GET", body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def test_lab10_catalog_walkforward_sltp_and_pacing_invariants():
    assert lab10.ORDER_SEND_CAPABLE is False
    cat = lab10.build_lab10_catalog()
    assert len(cat) == 16
    assert len({c["id"] for c in cat}) == 16
    assert len({c["fam"] for c in cat}) == 4

    # Conservative SL-before-TP tie-break on M1 bar: hits both -100 SL and +200 TP on bar 1 -> MUST return -1.0R
    row = {"stop_risk_with_cost_usd": 100.0}
    marks_both = np.array([[0.0, 250.0, -120.0, 50.0]], dtype=np.float64)
    assert lab10.simulate_trade_sl_tp_on_marks(row, marks_both, 1.0, 2.0) == -1.0

    # Clean TP hit without touching SL -> returns +2.0R
    marks_tp = np.array([[0.0, 40.0, -20.0, 30.0], [30.0, 210.0, 10.0, 190.0]], dtype=np.float64)
    assert lab10.simulate_trade_sl_tp_on_marks(row, marks_tp, 1.0, 2.0) == 2.0

    # Verify committed Lab 10 report maintains strict Holdout 2025+ seal
    rep = json.loads((ROOT / "planning/research/LAB10-V2-ROBUST-ALPHA-WF-AND-PROP-PACING-20261124.json").read_text(encoding="utf-8"))
    assert rep["holdout_rows_analysed"] == 0
    assert rep["order_send_count"] == 0
    assert rep["study_1a_discovery"]["m_total"] == 16
    assert rep["study_1b_walk_forward_sl_tp"]["port_7e_aggregate"]["n_oos_trades"] > 2000


def test_mql5_propguard_fill_price_fix_and_compiled_ex5():
    pg_src = (ROOT / "tooling/ai-engines/exports/Include/Naqex_PropGuard.mqh").read_text(encoding="utf-8")
    assert "ResolveExecutedFillPrice" in pg_src
    assert "HistoryDealGetDouble(deal, DEAL_PRICE)" in pg_src
    assert "InpGuardDryRunLogOnly     = true;" in pg_src

    orch_src = (ROOT / "tooling/ai-engines/exports/Naqex_AccountOrchestrator.mq5").read_text(encoding="utf-8")
    assert "InpDryRunLogOnly      = true;" in orch_src
    assert "InpAllowManualHaltFile = false;" in orch_src

    ex5_files = list((ROOT / ".runtime/mt5-compiled-ex5").glob("*.ex5"))
    assert len(ex5_files) >= 9
    assert list((ROOT / "tooling/ai-engines/exports").glob("*.ex5")) == []


def test_cockpit_safety_cover_2step_and_prop_terms_audit(tmp_path: Path):
    assert cockpit_server.ORDER_SEND_COUNT == 0
    srv = cockpit_server.create_server(host="127.0.0.1", port=0, root=tmp_path)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    base = f"http://127.0.0.1:{port}"
    try:
        # 1. HTML includes Row 4 safety cover & live positions & prop terms auditor
        with urllib.request.urlopen(f"{base}/", timeout=10) as resp:
            html = resp.read().decode("utf-8")
        assert "btn-toggle-cover" in html
        assert "tbl-live-pos" in html
        assert "inp-pta-firm" in html

        # 2. Fail-closed when cover is closed (cover_opened=False)
        st, js = _http_json(
            f"{base}/api/emergency-cover",
            method="POST",
            body={"cover_opened": False, "action": "HALT_NEW_ENTRIES", "confirm_code": "HALT"},
        )
        assert st == 400 and js["ok"] is False and "SAFETY_COVER_CLOSED" in js["error"]

        # 3. Fail-closed when confirm code is wrong
        st, js = _http_json(
            f"{base}/api/emergency-cover",
            method="POST",
            body={"cover_opened": True, "action": "FLATTEN_ALL", "confirm_code": "HALT"},
        )
        assert st == 400 and js["ok"] is False and "CONFIRM_CODE_MISMATCH" in js["error"]

        # 4. Succeeds cleanly with cover opened + exact confirm code (OrderSend=0!)
        st, js = _http_json(
            f"{base}/api/emergency-cover",
            method="POST",
            body={"cover_opened": True, "action": "HALT_NEW_ENTRIES", "confirm_code": "HALT", "reason": "unit_test"},
        )
        assert st == 200 and js["ok"] is True and js["state"] == "ARMED_HALT_NEW_ENTRIES" and js["order_send_count"] == 0

        # 5. Reset back to normal
        st, js = _http_json(
            f"{base}/api/emergency-cover",
            method="POST",
            body={"cover_opened": True, "action": "RESET_NORMAL", "confirm_code": "RESET"},
        )
        assert st == 200 and js["state"] == "NORMAL_COVER_CLOSED"

        # 6. Offline Prop Terms baseline preview
        st, js = _http_json(
            f"{base}/api/prop-terms-audit",
            method="POST",
            body={"firm": "the5ers_high_stakes", "terms_text": "", "use_typesafe": False},
        )
        assert st == 200 and js["ok"] is True and js["mode"] == "offline_baseline_preview"
        assert js["order_send_count"] == 0

        # 7. Live telemetry endpoint exposes open_positions, exec_audit_recent & emergency_cover
        st, js = _http_json(f"{base}/api/live-telemetry")
        assert st == 200 and "emergency_cover" in js
        assert "open_positions" in js["mt5_live_spreads"]
        assert "exec_audit_recent" in js["mt5_live_spreads"]
    finally:
        srv.shutdown()
        srv.server_close()


def test_vps_24x5_install_and_flat_only_sync_scripts(tmp_path: Path):
    vps_dir = ROOT / "tooling/ai-engines/exports/deployment_kit/vps_kit"
    install_ps = vps_dir / "install_vps_24x5.ps1"
    sync_ps = vps_dir / "sync_updated_ex5_when_flat.ps1"
    assert install_ps.is_file() and sync_ps.is_file()

    # 1. Dry-run VPS installer verifies all 9 .ex5 + presets + SHA256 cleanly
    mt5_target = tmp_path / "vps_mt5"
    p1 = subprocess.run(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(install_ps),
            "-TargetMt5Root", str(mt5_target),
            "-PresetProfile", "The5ers_HighStakes_P1_Balanced",
            "-RegisterWatchdogTask", "-DryRun",
        ],
        capture_output=True, text=True, check=False,
    )
    assert p1.returncode == 0, p1.stderr
    out1 = json.loads(p1.stdout)
    assert out1["dry_run"] is True and out1["order_send"] == 0 and out1["ex5_count"] == 9

    # 2. Fail-closed flat-only updater MUST refuse with exit code 2 when open_positions == 1!
    files_dir = mt5_target / "MQL5" / "Files"
    files_dir.mkdir(parents=True, exist_ok=True)
    (files_dir / "naqex_heartbeat.json").write_text(json.dumps({"open_positions": 1, "utc_ts": 1795498000}), encoding="utf-8")
    p2 = subprocess.run(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(sync_ps),
            "-TargetMt5Root", str(mt5_target),
            "-DryRun",
        ],
        capture_output=True, text=True, check=False,
    )
    assert p2.returncode == 2
    assert json.loads(p2.stdout)["status"] == "BLOCKED_OPEN_POSITIONS"

    # 3. Succeeds cleanly in DryRun when open_positions == 0!
    (files_dir / "naqex_heartbeat.json").write_text(json.dumps({"open_positions": 0, "utc_ts": 1795498000}), encoding="utf-8")
    p3 = subprocess.run(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(sync_ps),
            "-TargetMt5Root", str(mt5_target),
            "-DryRun",
        ],
        capture_output=True, text=True, check=False,
    )
    assert p3.returncode == 0, p3.stderr
    out3 = json.loads(p3.stdout)
    assert out3["status"] == "DRYRUN_READY_FLAT" and out3["files_count"] >= 9
