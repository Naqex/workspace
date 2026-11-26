"""Regression tests proving zero split-brain across all 3 L8 monolith façades."""

from __future__ import annotations

import hashlib
import importlib
import json
import sys
import threading
import urllib.request
from pathlib import Path
from typing import Any

import pytest

_AI_ENGINES = Path(__file__).resolve().parents[1]
if str(_AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINES))


def test_cockpit_facade_syncs_helpers_and_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    from cockpit import server as cs

    called_node1: list[str] = []

    def _fake_probe(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        called_node1.append("probe")
        return {"balance": 10_000.0, "equity": 10_123.45, "mt5_running": True}

    monkeypatch.setattr(cs, "_probe_node1_via_node_ctl", _fake_probe)
    cs.clear_sprint_and_node1_caches()
    n1 = cs.build_node1_summary_payload(cs.ROOT, allow_ssh=True, use_cache=False, ttl_sec=0.0)
    assert called_node1 == ["probe"]
    assert n1["source"] == "live_ssh"
    assert n1["equity"] == pytest.approx(10_123.45)

    called_heroku: list[Path] = []

    def _fake_heroku(root_arg: Path, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        called_heroku.append(root_arg)
        return {
            "account_label": "MOCK_HEROKU_NODE",
            "status": "OK",
            "balance": 100_000.0,
            "equity": 100_250.0,
        }

    monkeypatch.setattr(cs, "_fetch_heroku_node1_cached", _fake_heroku)
    pm = cs.build_prop_metrix_payload(cs.ROOT, allow_cloud_fetch=True)
    assert called_heroku == [cs.ROOT]
    assert "MOCK_HEROKU_NODE" in str(pm["source"]["label"])

    monkeypatch.setattr(cs, "build_summary_payload", lambda *_a, **_kw: {"stub_summary": True})
    monkeypatch.setattr(cs, "build_live_telemetry_payload", lambda *_a, **_kw: {"stub_tel": True})
    monkeypatch.setattr(cs, "build_stress_payload", lambda *_a, **_kw: {"stub_stress": True})
    ov = cs.build_overview_payload(cs.ROOT)
    assert ov["summary"] == {"stub_summary": True}

    # Verify HTTP `/api/summary` route also observes the `build_summary_payload` monkeypatch.
    httpd = cs.create_server(host="127.0.0.1", port=0, root=cs.ROOT)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/summary", timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        assert body == {"stub_summary": True}
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)

    monkeypatch.setattr(cs, "audit_prop_terms_text", lambda text, **_kw: {"stub_audit": text})
    sample_terms = "Sample prop firm terms text with more than twenty characters."
    status_code, res = cs.handle_prop_terms_audit_request({
        "firm": "the5ers_high_stakes",
        "terms_text": sample_terms,
        "use_typesafe": True,
    })
    assert int(status_code) == 200
    assert res["stub_audit"] == sample_terms

    called_mui3: list[bool] = []

    def _fake_mui3(*_a: Any, **_kw: Any) -> dict[str, Any]:
        called_mui3.append(True)
        return {"scenario": "STUB"}

    monkeypatch.setattr(cs, "_load_mui3_master_prop7e_scenarios", _fake_mui3)
    cs.clear_sprint_and_node1_caches()
    sp = cs.build_blackfriday_sprint_payload(cs.ROOT, use_cache=False, ttl_sec=0.0)
    assert called_mui3 == [True]
    assert sp["mui3_realtick"] == {"scenario": "STUB"}


def test_cockpit_direct_script_import_syncs_cache_and_restores_on_teardown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cockpit_dir = str(_AI_ENGINES / "cockpit")
    monkeypatch.syspath_prepend(cockpit_dir)
    sys.modules.pop("server", None)
    srv = importlib.import_module("server")
    try:
        from cockpit import server as cs

        monkeypatch.setattr(srv, "_HEROKU_STATUS_CACHE", (9e12, {"source": "DIRECT_PATCH"}))
        assert cs._HEROKU_STATUS_CACHE == (9e12, {"source": "DIRECT_PATCH"})
        assert srv._fetch_heroku_node1_cached(srv.ROOT) == {"source": "DIRECT_PATCH"}
        assert cs._fetch_heroku_node1_cached(cs.ROOT) == {"source": "DIRECT_PATCH"}
        monkeypatch.undo()
        assert srv._HEROKU_STATUS_CACHE[1] != {"source": "DIRECT_PATCH"}
        assert cs._HEROKU_STATUS_CACHE[1] != {"source": "DIRECT_PATCH"}
    finally:
        sys.modules.pop("server", None)


def test_calibration_probe_facade_syncs_constants_and_helpers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from exports import ftmo_demo_calibration_probe as probe

    lock_p = tmp_path / "lock.json"
    raw = b'{"locked": true}\n'
    lock_p.write_bytes(raw)
    custom_sha = hashlib.sha256(raw).hexdigest()
    monkeypatch.setattr(probe, "EXPECTED_HOLDOUT_LOCK_SHA", custom_sha)
    assert probe.assert_holdout_lock_intact(lock_p) == custom_sha

    called_sum: list[bool] = []

    def _fake_sum(*_a: Any, **_kw: Any) -> dict[str, Any]:
        called_sum.append(True)
        return {
            "schema": "stub-v1",
            "verdict": "STUB_OK",
            "holdout_rows_analysed": 0,
            "inputs": {"spread_log_rows_total": 0, "live_fill_legs_total": 0},
            "portfolio_core4": {},
        }

    monkeypatch.setattr(probe, "summarize_calibration_and_spreads", _fake_sum)
    assert probe.main(["--summarize"]) == 0
    assert called_sum == [True]

    monkeypatch.undo()
    monkeypatch.setattr(probe, "EXPECTED_HOLDOUT_LOCK_SHA", custom_sha)
    baseline_called: list[bool] = []

    def _fake_baselines(*_a: Any, **_kw: Any) -> dict[str, Any]:
        baseline_called.append(True)
        raise RuntimeError("FAKE_BASELINES_HIT")

    monkeypatch.setattr(probe, "compute_dev_m1_spread_baselines", _fake_baselines)
    summary_out = tmp_path / "summary.json"
    with pytest.raises(RuntimeError, match="FAKE_BASELINES_HIT"):
        probe.summarize_calibration_and_spreads(
            spread_log_path=tmp_path / "missing_spreads.jsonl",
            fills_csv_path=tmp_path / "missing_fills.csv",
            summary_json_path=summary_out,
            hot_cache_dir=tmp_path / "unused_cache",
            holdout_lock_path=lock_p,
        )
    assert baseline_called == [True]

    prep_called: list[bool] = []

    def _fake_prep(*_a: Any, **_kw: Any) -> Path:
        prep_called.append(True)
        raise RuntimeError("STOP_BEFORE_MT5_LAUNCH")

    monkeypatch.setattr(probe, "prepare_isolated_portable_terminal", _fake_prep)
    creds = probe.RedactedCredentials(
        login=1515343318,
        password="x",
        server="FTMO-Demo",
        terminal_path=tmp_path / "terminal64.exe",
    )
    portable_dir = tmp_path / "ftmo-demo-portable-1515343318"
    with pytest.raises(RuntimeError, match="STOP_BEFORE_MT5_LAUNCH"):
        probe._connect_isolated_mt5(
            creds=creds,
            portable_dir=portable_dir,
            allow_trading=False,
            process_lister=lambda: [],
        )
    assert prep_called == [True]


def test_capital_optimizer_facade_syncs_constants_and_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quant_factory import prop_capital_promo_optimizer as opt

    called_study: list[bool] = []

    def _fake_study(*_a: Any, **_kw: Any) -> dict[str, Any]:
        called_study.append(True)
        return {
            "elapsed_seconds": 0.1,
            "inputs": {"primary_variant": "V3"},
            "safety_invariants": {"holdout_rows_analysed": 0},
        }

    def _fake_save(_results: dict[str, Any], out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text('{"stub": true}\n', encoding="utf-8")
        return out_path

    monkeypatch.setattr(opt, "run_full_capital_promo_study", _fake_study)
    monkeypatch.setattr(opt, "save_results_json", _fake_save)
    monkeypatch.setattr(opt, "render_vietnamese_law15_report", lambda *_a, **_kw: "# ok\n")
    out_json = tmp_path / "o.json"
    out_json_v2 = tmp_path / "o_v2.json"
    out_md = tmp_path / "report.md"
    rc = opt.main(["--out-json", str(out_json), "--out-json-v2", str(out_json_v2), "--out-md", str(out_md)])
    assert rc == 0
    assert called_study == [True]
    assert out_md.read_text(encoding="utf-8") == "# ok\n"

    monkeypatch.setattr(opt, "HOLDOUT_CUTOFF_DAY", "2024-01-01")
    with pytest.raises(ValueError, match="HOLDOUT_LOCK_VIOLATION"):
        opt.assert_strict_pre_holdout_days(["2024-06-01"])

    bad_cat = tmp_path / "missing_catalog.json"
    monkeypatch.setattr(opt, "DEFAULT_CATALOG_PATH", bad_cat)
    with pytest.raises(FileNotFoundError):
        opt.load_pricing_catalog(allow_fallback=False)
