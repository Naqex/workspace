"""Unit tests for Naqex Home-VPS pre-built read-only probe scripts & node_ctl wrapper."""
from __future__ import annotations

from datetime import datetime
import json
import pathlib
import sys
from unittest.mock import patch

OPS_CLOUD = pathlib.Path(__file__).resolve().parents[1] / "ops_cloud"
NODE_SCRIPTS = OPS_CLOUD / "node_scripts"
for p in (OPS_CLOUD, NODE_SCRIPTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import node_ctl  # noqa: E402
import node_exec_audit  # noqa: E402
import node_integrity  # noqa: E402
import node_logs  # noqa: E402


def test_node_ctl_read_only_invariants_and_fallback():
    assert node_ctl.ORDER_SEND_CAPABLE is False
    assert node_ctl.ORDER_SEND_COUNT == 0
    for script_name in node_ctl.SCRIPT_MAP.values():
        assert (node_ctl.SCRIPTS_DIR / script_name).exists(), f"Missing {script_name}"

    calls: list[str] = []

    def fake_run(cmd, **_kw):
        host = cmd[5]
        calls.append(host)

        class _R:
            returncode = 0 if host == "naqex-node1-ts" else 255
            stdout = "OK\n" if returncode == 0 else ""
            stderr = ""

        return _R()

    with patch.object(node_ctl.subprocess, "run", side_effect=fake_run):
        chosen = node_ctl.resolve_ssh_host()
    assert chosen == "naqex-node1-ts"
    assert calls == ["naqex-node1", "naqex-node1-ts"]


def test_node_logs_decodes_utf16le_and_filters(tmp_path: pathlib.Path):
    log_dir = tmp_path / "MQL5" / "Logs"
    log_dir.mkdir(parents=True)
    today = datetime.now().strftime("%Y%m%d")
    sample = (
        "AA\t0\t14:25:40.000\tNaqex_EA\t[PROPGUARD-OK] Loaded 492 red-news events\r\n"
        "BB\t0\t14:26:10.000\tNaqex_EA\t[PROPGUARD-WARN] Sample warning line\r\n"
    )
    (log_dir / f"{today}.log").write_bytes(sample.encode("utf-16-le"))

    res_all = node_logs.query_logs(tmp_path, scope="mql5", days=1)
    assert res_all["order_send_count"] == 0
    assert res_all["total_matches"] == 2

    res_err = node_logs.query_logs(tmp_path, scope="mql5", days=1, errors_only=True)
    assert res_err["total_matches"] == 1
    assert "WARN" in res_err["lines"][0]["msg"]


def test_node_integrity_verifies_sha_csv_and_keep_private(tmp_path: pathlib.Path):
    ex5_dir = tmp_path / "MQL5" / "Experts" / "Naqex"
    files_dir = tmp_path / "MQL5" / "Files"
    cfg_dir = tmp_path / "Config"
    for d in (ex5_dir, files_dir, cfg_dir):
        d.mkdir(parents=True)

    ex5 = ex5_dir / "Naqex_Test.ex5"
    ex5.write_bytes(b"binary-fixture")
    csv_rows = ["utc_ts,ccy,event"] + [f"{1700000000 + i},USD,CPI" for i in range(420)]
    csv_path = files_dir / "naqex_red_news_utc.csv"
    csv_path.write_text("\n".join(csv_rows) + "\n", encoding="utf-8")
    exp_sha = tmp_path / "expected.json"
    exp_sha.write_text(
        json.dumps(
            {
                "updated_utc": "2026-11-25T06:36:49Z",
                "ex5": {"Naqex_Test.ex5": node_integrity.sha256_file(ex5)},
                "red_news_csv_sha256": node_integrity.sha256_file(csv_path),
            }
        ),
        encoding="utf-8",
    )
    (cfg_dir / "common.ini").write_bytes("[Common]\r\nKeepPrivate=1\r\n".encode("utf-16-le"))
    (tmp_path / "connector.ini").write_text("[Experts]\r\nEnabled=1\r\n", encoding="utf-8")

    res = node_integrity.audit_integrity(tmp_path, exp_sha)
    assert res["ok"] is True
    assert res["ex5_expected_matched"] == 1
    assert res["red_news_csv"]["rows"] == 420
    assert res["red_news_csv"]["sha_match"] is True
    assert res["common_ini"]["keep_private"] == "1"


def test_node_exec_audit_summarizes_fills_and_rejects(tmp_path: pathlib.Path):
    csv_text = (
        "utc_ts,symbol,event_type,req_price,fill_price,latency_ms,reason\n"
        "1795500000,USDJPY,ORDER_FILL,150.000,150.015,42.5,OK\n"
        "1795500100,GBPUSD,ORDER_REJECT,1.2500,0,18.0,OFF_QUOTES\n"
    )
    (tmp_path / "naqex_exec_audit_test.csv").write_text(csv_text, encoding="utf-8")
    (tmp_path / "naqex_master_shadow.csv").write_text("h1,h2\n1,2\n3,4\n", encoding="utf-8")

    res = node_exec_audit.summarize_exec_audit(tmp_path)
    assert res["order_send_count"] == 0
    assert res["total_audit_rows"] == 2
    assert res["shadow_rows"] == 2
    assert res["fills_by_symbol"] == {"USDJPY": 1}
    assert res["latency_ms"]["median"] == 30.25
    assert len(res["rejects_tail"]) == 1
