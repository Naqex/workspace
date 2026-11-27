"""Offline CI-safe + `@pytest.mark.local_cache` tests for Holdout v2 Pre-Registration & 3-Sleeve Dev Study.

Tests enforce:
  - 100% `-O` safety (ZERO bare `assert` statements in guarded production modules; tested under `python -O`).
  - Fail-closed 1-byte tamper rejection on manifest JSON, `.sha256` sidecar, internal canonical hash,
    locked prospective thresholds, and every frozen artifact.
  - Strict pre-window temporal lock (`frozen_utc < 2026-12-01T00:00:00Z`).
  - Strict pre-holdout date slicing (`<= 2024-12-31`, `holdout_rows_analysed == 0`) on both synthetic
    `tmp_path` parquets (CI offline) and real local caches (`@pytest.mark.local_cache`).
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from experiments import three_sleeve_top1_roadmap_study as roadmap
from quant_core.holdout_guard import HoldoutLockError
from quant_core.io_utils import repo_root_from, sha256_bytes, sha256_file, sha256_json_canonical
from quant_factory import preregister_holdout_v2 as prereg

REPO_ROOT = repo_root_from(__file__)
EXPECTED_HOLD_LOCK_SHA = "f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486"


def _seed_synthetic_repo(root: Path, *, include_v103: bool = False) -> dict[str, Path]:
    """Create a minimal synthetic repo layout in `tmp_path` containing all frozen artifact slots."""
    created: dict[str, Path] = {}
    for spec in prereg.FROZEN_ARTIFACT_SPECS:
        if not spec.required and not include_v103:
            continue
        p = root / spec.rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = f"// synthetic artifact {spec.key} ({spec.role})\nvalue=12345\n"
        p.write_text(payload, encoding="utf-8", newline="\n")
        created[spec.key] = p
    return created


def _rehash_manifest_and_sidecar(out_dir: Path, manifest: dict[str, Any], *, update_payload_sha: bool = True) -> None:
    """Helper for adversarial negative-mutation tests that re-sign tampered manifests."""
    obj = dict(manifest)
    if update_payload_sha:
        body = {k: v for k, v in obj.items() if k != "manifest_payload_sha256"}
        obj["manifest_payload_sha256"] = sha256_json_canonical(body)
    text = prereg.serialize_manifest_json(obj)
    m_path = out_dir / prereg.MANIFEST_FILENAME
    s_path = out_dir / prereg.SIDECAR_FILENAME
    m_path.write_text(text, encoding="utf-8", newline="\n")
    digest = sha256_bytes(text.encode("utf-8"))
    s_path.write_text(f"{digest}  {prereg.MANIFEST_FILENAME}\n", encoding="utf-8", newline="\n")


class TestHoldoutV2PreRegistrationContract:
    """100% offline CI-safe tests for `preregister_holdout_v2.py`."""

    def test_freeze_and_verify_happy_path_without_v103(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        out_dir = tmp_path / "out"
        _seed_synthetic_repo(repo, include_v103=False)

        rc_freeze = prereg.main(
            [
                "--freeze",
                "--repo-root",
                str(repo),
                "--out-dir",
                str(out_dir),
                "--now-utc",
                "2026-11-27T12:00:00Z",
            ]
        )
        assert rc_freeze == 0

        m_path = out_dir / prereg.MANIFEST_FILENAME
        s_path = out_dir / prereg.SIDECAR_FILENAME
        assert m_path.is_file()
        assert s_path.is_file()
        # LF-only verification
        assert b"\r\n" not in m_path.read_bytes()
        assert b"\r\n" not in s_path.read_bytes()

        manifest = json.loads(m_path.read_text(encoding="utf-8"))
        assert manifest["schema_version"] == prereg.SCHEMA_VERSION
        assert manifest["frozen_utc"] == "2026-11-27T12:00:00Z"
        assert manifest["holdout_v2_prospective_start_utc"] == "2026-12-01T00:00:00Z"
        assert manifest["order_send_count"] == 0
        assert manifest["holdout_rows_analysed"] == 0

        thr = manifest["thresholds"]
        assert thr["min_live_demo_cal_days"] == 90
        assert thr["max_adverse_slippage_mult"] == 1.50
        assert thr["kill_adverse_slippage_mult"] == 1.75
        assert thr["required_swap_usd"] == 0.0
        assert thr["max_parameter_retunes_after_unlock"] == 0
        assert thr["single_shot_unlock_only"] is True

        v103_entry = manifest["artifacts"]["tooling/ai-engines/exports/Naqex_Master_Prop7E_v103.mq5"]
        assert v103_entry["present"] is False
        assert v103_entry["sha256"] is None
        assert v103_entry["bytes"] == 0

        rc_verify = prereg.main(["--verify", "--repo-root", str(repo), "--out-dir", str(out_dir)])
        assert rc_verify == 0

    def test_freeze_and_verify_happy_path_with_v103(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        out_dir = tmp_path / "out"
        _seed_synthetic_repo(repo, include_v103=True)

        res = prereg.freeze_preregistration(
            repo_root=repo,
            out_dir=out_dir,
            dry_run=False,
            now_utc="2026-11-30T23:59:59Z",
        )
        assert res["artifacts_hashed"] == 8
        assert res["artifacts_total_slots"] == 8
        ver = prereg.verify_preregistration(repo_root=repo, out_dir=out_dir)
        assert ver["status"] == "VERIFIED_PASS"
        assert ver["verified_artifacts"] == 8
        assert ver["absent_optional_artifacts"] == []

    def test_dry_run_writes_zero_files(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        repo = tmp_path / "repo"
        out_dir = tmp_path / "out_dry"
        _seed_synthetic_repo(repo, include_v103=False)

        rc = prereg.main(
            [
                "--freeze",
                "--dry-run",
                "--repo-root",
                str(repo),
                "--out-dir",
                str(out_dir),
                "--now-utc",
                "2026-11-27T08:00:00Z",
            ]
        )
        assert rc == 0
        assert not (out_dir / prereg.MANIFEST_FILENAME).exists()
        assert not (out_dir / prereg.SIDECAR_FILENAME).exists()
        printed = json.loads(capsys.readouterr().out)
        assert printed["dry_run"] is True
        assert printed["artifacts_hashed"] == 7

    @pytest.mark.parametrize("bad_ts", ["2026-12-01T00:00:00Z", "2026-12-15T12:00:00Z", "2027-01-01T00:00:00Z"])
    def test_freeze_rejects_on_or_after_prospective_start(self, tmp_path: Path, bad_ts: str) -> None:
        repo = tmp_path / "repo"
        out_dir = tmp_path / "out"
        _seed_synthetic_repo(repo, include_v103=False)

        with pytest.raises(prereg.PreRegistrationError, match="PREREGISTRATION_WINDOW_CLOSED"):
            prereg.freeze_preregistration(repo_root=repo, out_dir=out_dir, dry_run=False, now_utc=bad_ts)

        rc = prereg.main(["--freeze", "--repo-root", str(repo), "--out-dir", str(out_dir), "--now-utc", bad_ts])
        assert rc != 0
        assert not (out_dir / prereg.MANIFEST_FILENAME).exists()

    @pytest.mark.parametrize(
        "artifact_key",
        [
            "Naqex_Master_Prop7E.mq5",
            "Naqex_PropGuard.mqh",
            "Naqex_Signals_7E.mqh",
            "Naqex_Master_Prop7E_v103.mq5",
            "firms_catalog.json",
            "risk_profiles.json",
            "naqex_red_news_utc.csv",
            "NATIVE_FTMO_HOLDOUT_LOCK.json",
        ],
    )
    def test_verify_rejects_1byte_same_size_tamper_on_every_artifact(self, tmp_path: Path, artifact_key: str) -> None:
        repo = tmp_path / "repo"
        out_dir = tmp_path / "out"
        created = _seed_synthetic_repo(repo, include_v103=True)
        prereg.freeze_preregistration(repo_root=repo, out_dir=out_dir, now_utc="2026-11-27T12:00:00Z")

        # Mutate EXACTLY 1 byte keeping byte length identical (proves SHA-256 catches bit flips, not just size!)
        target = created[artifact_key]
        raw = bytearray(target.read_bytes())
        raw[-2] = ord("9") if raw[-2] != ord("9") else ord("8")
        target.write_bytes(bytes(raw))

        with pytest.raises(prereg.PreRegistrationError, match="ARTIFACT_HASH_TAMPER_DETECTED"):
            prereg.verify_preregistration(repo_root=repo, out_dir=out_dir)

        rc = prereg.main(["--verify", "--repo-root", str(repo), "--out-dir", str(out_dir)])
        assert rc != 0

    def test_verify_rejects_1byte_manifest_and_sidecar_and_contract_tampers(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        out_dir = tmp_path / "out"
        _seed_synthetic_repo(repo, include_v103=False)
        prereg.freeze_preregistration(repo_root=repo, out_dir=out_dir, now_utc="2026-11-27T12:00:00Z")

        m_path = out_dir / prereg.MANIFEST_FILENAME
        s_path = out_dir / prereg.SIDECAR_FILENAME
        orig_m = m_path.read_bytes()
        orig_s = s_path.read_bytes()

        # 1. Flip 1 byte in manifest JSON -> sidecar mismatch
        m_path.write_bytes(orig_m + b" ")
        with pytest.raises(prereg.PreRegistrationError, match="MANIFEST_TAMPER_DETECTED"):
            prereg.verify_preregistration(repo_root=repo, out_dir=out_dir)
        m_path.write_bytes(orig_m)

        # 2. Flip 1 hex char in sidecar -> sidecar mismatch
        bad_s = bytearray(orig_s)
        bad_s[0] = ord("0") if bad_s[0] != ord("0") else ord("1")
        s_path.write_bytes(bytes(bad_s))
        with pytest.raises(prereg.PreRegistrationError, match="MANIFEST_TAMPER_DETECTED"):
            prereg.verify_preregistration(repo_root=repo, out_dir=out_dir)

        # 2b. Whitespace / CRLF / non-UTF-8 1-byte tamper on sidecar MUST fail closed with PreRegistrationError
        for tampered_sidecar in (
            orig_s + b" ",
            orig_s + b"\n",
            b" " + orig_s,
            orig_s.replace(b"\n", b"\r\n"),
            b"\xff" + orig_s[1:],
        ):
            s_path.write_bytes(tampered_sidecar)
            with pytest.raises(prereg.PreRegistrationError):
                prereg.verify_preregistration(repo_root=repo, out_dir=out_dir)
            rc_bad_s = prereg.main(["--verify", "--repo-root", str(repo), "--out-dir", str(out_dir)])
            assert rc_bad_s == 1
        s_path.write_bytes(orig_s)

        # 3. Rewrite manifest + sidecar WITHOUT updating internal manifest_payload_sha256
        loaded = json.loads(orig_m.decode("utf-8"))
        loaded["active_candidate"] = "TAMPERED_CAND"
        _rehash_manifest_and_sidecar(out_dir, loaded, update_payload_sha=False)
        with pytest.raises(prereg.PreRegistrationError, match="MANIFEST_PAYLOAD_TAMPER_DETECTED"):
            prereg.verify_preregistration(repo_root=repo, out_dir=out_dir)

        # 4. Even if attacker re-signs BOTH internal payload sha AND sidecar, threshold tampering fails closed!
        for bad_mut in (
            {"min_live_demo_cal_days": 89},
            {"max_adverse_slippage_mult": 1.60},
            {"kill_adverse_slippage_mult": 2.00},
            {"required_swap_usd": 0.01},
            {"max_parameter_retunes_after_unlock": 1},
            {"single_shot_unlock_only": False},
            {"min_pass_ann_return_frac": -99.0},
            {"min_conditional_ann_return_frac": -0.01},
            {"min_pass_calmar": 0.0},
            {"min_healthy_core_engines": 0},
            {"total_core_engines": 0},
            {"min_healthy_core_engines": 8},
        ):
            base = json.loads(orig_m.decode("utf-8"))
            base["thresholds"].update(bad_mut)
            _rehash_manifest_and_sidecar(out_dir, base, update_payload_sha=True)
            with pytest.raises(prereg.PreRegistrationError):
                prereg.verify_preregistration(repo_root=repo, out_dir=out_dir)

        # 4b. Deleting a required threshold key in a re-signed manifest fails closed!
        for drop_key in ("min_pass_calmar", "min_pass_ann_return_frac", "min_healthy_core_engines"):
            base_drop = json.loads(orig_m.decode("utf-8"))
            del base_drop["thresholds"][drop_key]
            _rehash_manifest_and_sidecar(out_dir, base_drop, update_payload_sha=True)
            with pytest.raises(prereg.PreRegistrationError, match="thresholds key mismatch"):
                prereg.verify_preregistration(repo_root=repo, out_dir=out_dir)

        # 5. Restoring clean manifest passes, then post-freeze appearance of unregistered v103 fails closed!
        m_path.write_bytes(orig_m)
        s_path.write_bytes(orig_s)
        assert prereg.verify_preregistration(repo_root=repo, out_dir=out_dir)["status"] == "VERIFIED_PASS"

        v103_path = repo / "tooling/ai-engines/exports/Naqex_Master_Prop7E_v103.mq5"
        v103_path.write_text("// smuggled post-freeze\n", encoding="utf-8", newline="\n")
        with pytest.raises(prereg.PreRegistrationError, match="UNREGISTERED_ARTIFACT_APPEARED_POST_FREEZE"):
            prereg.verify_preregistration(repo_root=repo, out_dir=out_dir)

    def test_evaluate_prospective_outcome_thresholds(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _seed_synthetic_repo(repo, include_v103=False)
        manifest = prereg.build_preregistration_manifest(repo, now_utc="2026-11-27T12:00:00Z")

        good_obs = {
            "live_demo_cal_days": 90,
            "adverse_slippage_mult": 1.20,
            "swap_usd": 0.0,
            "parameter_retunes": 0,
            "missing_sl_orders": 0,
            "fill_unresolved_events": 0,
            "parity_restart_errors": 0,
            "ann_return_frac": 0.065,
            "float_peak_dd_frac": 0.055,
            "daily_dd_frac": 0.021,
            "calmar": 1.18,
            "healthy_core_engines": 6,
        }
        assert prereg.evaluate_prospective_outcome(manifest, good_obs)["verdict"] == "PASS"

        # Insufficient calendar days (< 90)
        assert (
            prereg.evaluate_prospective_outcome(manifest, {**good_obs, "live_demo_cal_days": 89})["verdict"]
            == "BLOCKED_INSUFFICIENT_DAYS"
        )
        # Slippage between 1.50x and 1.75x -> CONDITIONAL
        assert (
            prereg.evaluate_prospective_outcome(manifest, {**good_obs, "adverse_slippage_mult": 1.60})["verdict"]
            == "CONDITIONAL"
        )
        # Hard kills
        for kill_override in (
            {"adverse_slippage_mult": 1.76},
            {"swap_usd": -0.01},
            {"parameter_retunes": 1},
            {"missing_sl_orders": 1},
            {"ann_return_frac": -0.005},
            {"float_peak_dd_frac": 0.095},
        ):
            res = prereg.evaluate_prospective_outcome(manifest, {**good_obs, **kill_override})
            assert res["verdict"] == "KILL", f"Expected KILL for {kill_override}, got {res}"

        # Poisoned negative / out-of-range telemetry MUST fail closed with PreRegistrationError (never PASS!)
        for poisoned_obs in (
            {"live_demo_cal_days": -1},
            {"adverse_slippage_mult": -1.0},
            {"float_peak_dd_frac": -0.05},
            {"daily_dd_frac": -0.01},
            {"parameter_retunes": -1},
            {"missing_sl_orders": -1},
            {"fill_unresolved_events": -1},
            {"parity_restart_errors": -1},
            {"healthy_core_engines": -1},
            {"healthy_core_engines": 8},
        ):
            with pytest.raises(prereg.PreRegistrationError):
                prereg.evaluate_prospective_outcome(manifest, {**good_obs, **poisoned_obs})

    def test_zero_bare_assert_and_zero_ordersend_ast_in_owned_modules(self) -> None:
        targets = (
            REPO_ROOT / "tooling/ai-engines/quant_factory/preregister_holdout_v2.py",
            REPO_ROOT / "tooling/ai-engines/experiments/three_sleeve_top1_roadmap_study.py",
        )
        for path in targets:
            src = path.read_text(encoding="utf-8")
            assert "\r\n" not in src, f"CRLF detected in {path}"
            tree = ast.parse(src, filename=str(path))
            asserts = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
            assert asserts == [], f"Bare assert found in {path.name} at lines {asserts} (unsafe under python -O!)"
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    fn_name = ""
                    if isinstance(node.func, ast.Name):
                        fn_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        fn_name = node.func.attr
                    assert fn_name.lower() != "ordersend" and fn_name.lower() != "order_send", (
                        f"Forbidden live order call {fn_name!r} found in {path.name}"
                    )


class TestThreeSleeveHoldoutCutoffAndMathOffline:
    """100% offline CI-safe tests for `three_sleeve_top1_roadmap_study.py`."""

    def test_enforce_dev_cutoff_strict_works_under_python_O(self) -> None:
        roadmap.enforce_dev_cutoff_strict(["2024-12-30", "2024-12-31"])
        with pytest.raises(HoldoutLockError):
            roadmap.enforce_dev_cutoff_strict(["2024-12-31", "2025-01-01"])
        with pytest.raises(ValueError):
            roadmap.enforce_dev_cutoff_strict(["2026-11-20"])
        with pytest.raises(HoldoutLockError):
            roadmap.enforce_dev_cutoff_strict(["2024-12-31"], cutoff_day="2025-06-01")
        with pytest.raises(HoldoutLockError):
            roadmap.enforce_dev_cutoff_strict([], allow_empty=False)

    def test_raw_python_O_subprocess_enforces_cutoff_and_tamper_rejection(self, tmp_path: Path) -> None:
        """Verify outside pytest assertion-rewriting that `python -O` still fails closed."""
        repo = tmp_path / "repo_opt"
        out_dir = tmp_path / "out_opt"
        created = _seed_synthetic_repo(repo, include_v103=False)
        prereg.freeze_preregistration(repo_root=repo, out_dir=out_dir, now_utc="2026-11-27T12:00:00Z")
        # Tamper 1 byte in risk_profiles.json
        rp = created["risk_profiles.json"]
        raw = bytearray(rp.read_bytes())
        raw[0] = ord("X") if raw[0] != ord("X") else ord("Y")
        rp.write_bytes(bytes(raw))

        # 1. CLI --verify under raw `python -O` MUST return non-zero
        proc_v = subprocess.run(
            [
                sys.executable,
                "-O",
                str(REPO_ROOT / "tooling/ai-engines/quant_factory/preregister_holdout_v2.py"),
                "--verify",
                "--repo-root",
                str(repo),
                "--out-dir",
                str(out_dir),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc_v.returncode != 0
        assert "ARTIFACT_HASH_TAMPER_DETECTED" in proc_v.stderr

        # 2. Holdout cutoff guard under raw `python -O` MUST raise HoldoutLockError
        snippet = (
            f"import sys; sys.path.insert(0, {str(REPO_ROOT / 'tooling/ai-engines')!r}); "
            "from experiments.three_sleeve_top1_roadmap_study import enforce_dev_cutoff_strict; "
            "enforce_dev_cutoff_strict(['2024-12-31', '2025-01-01'])"
        )
        proc_c = subprocess.run(
            [sys.executable, "-O", "-c", snippet],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc_c.returncode != 0
        assert "HOLDOUT" in proc_c.stderr

    def test_slice_daily_map_pre_holdout_and_poisoned_input_rejection(self) -> None:
        raw = {"2024-12-30": 0.01, "2024-12-31": -0.005, "2025-01-01": 0.05, "2026-11-20": 0.09}
        sliced, excluded = roadmap.slice_daily_map_pre_holdout(raw)
        assert sorted(sliced.keys()) == ["2024-12-30", "2024-12-31"]
        assert excluded == 2
        with pytest.raises(ValueError):
            roadmap.slice_daily_map_pre_holdout({"2024-12-30": float("nan")})

    def test_synthetic_parquet_loaders_discard_2025_2026_rows(self, tmp_path: Path) -> None:
        dates = ["2024-12-27", "2024-12-30", "2024-12-31", "2025-01-02", "2026-11-20"]
        prices = [100.0, 101.0, 102.0, 999.0, 1500.0]

        # Macro ETF cache
        macro_dir = tmp_path / "macro"
        macro_dir.mkdir()
        tbl_etf = pa.table(
            {
                "date": dates,
                "open": prices,
                "high": prices,
                "low": prices,
                "close": prices,
                "adjclose": prices,
                "volume": [1e6] * len(dates),
            }
        )
        pq.write_table(tbl_etf, macro_dir / "SPY.parquet")
        pq.write_table(tbl_etf, macro_dir / "TLT.parquet")
        mp = roadmap.load_macro_etf_dev_panel(cache_dir=macro_dir)
        assert max(mp["dates"]) == "2024-12-31"
        assert mp["holdout_rows_analysed"] == 0
        assert mp["excluded_post_cutoff_rows"] == 4

        # ETF40 cache
        etf40_dir = tmp_path / "etf40"
        etf40_dir.mkdir()
        pq.write_table(tbl_etf, etf40_dir / "SPY.parquet")
        pq.write_table(tbl_etf, etf40_dir / "GLD.parquet")
        p4, p7 = roadmap.load_etf40_dev_panels(cache_dir=etf40_dir)
        assert max(p4["dates"]) == "2024-12-31"
        assert max(p7["dates"]) == "2024-12-31"
        assert p7["holdout_rows_analysed"] == 0
        assert p7["excluded_post_cutoff_rows"] == 4

        # Crypto Spot 1d + Funding cache
        cry_dir = tmp_path / "crypto"
        (cry_dir / "1d").mkdir(parents=True)
        (cry_dir / "funding" / "rates").mkdir(parents=True)
        (cry_dir / "funding" / "perp_1d").mkdir(parents=True)
        ts_ms = [int(datetime.fromisoformat(d).replace(tzinfo=UTC).timestamp() * 1000) for d in dates]
        tbl_spot = pa.table(
            {
                "open_time_ms": ts_ms,
                "open": prices,
                "high": prices,
                "low": prices,
                "close": prices,
                "volume": [100.0] * len(dates),
                "quote_volume": [1e7] * len(dates),
                "trades": [1000] * len(dates),
            }
        )
        pq.write_table(tbl_spot, cry_dir / "1d" / "BTCUSDT.parquet")
        tbl_fr = pa.table(
            {
                "funding_time_ms": ts_ms,
                "funding_rate": [0.0001] * len(dates),
                "mark_price": prices,
            }
        )
        pq.write_table(tbl_fr, cry_dir / "funding" / "rates" / "BTCUSDT.parquet")
        tbl_pk = pa.table(
            {
                "open_time_ms": ts_ms,
                "open": prices,
                "high": prices,
                "low": prices,
                "close": prices,
                "quote_volume": [1e7] * len(dates),
            }
        )
        pq.write_table(tbl_pk, cry_dir / "funding" / "perp_1d" / "BTCUSDT.parquet")

        sp = roadmap.load_crypto_spot_dev_panel(cache_dir=cry_dir)
        assert max(sp["dates"]) == "2024-12-31"
        assert sp["holdout_rows_analysed"] == 0
        assert sp["excluded_post_cutoff_rows"] == 2

        fp = roadmap.load_crypto_funding_dev_panel(cache_dir=cry_dir, spot_panel=sp)
        assert max(fp["dates"]) == "2024-12-31"
        assert fp["holdout_rows_analysed"] == 0
        assert fp["excluded_post_cutoff_rows"] == 4

    def test_alignment_starved_months_cex_cap_and_capital_tiers(self) -> None:
        # Weekend compounding: Sat (+1%) + Sun (+1%) + Mon (+1%) -> Monday = 1.01^3 - 1
        s_map = {
            "S1": {"2024-12-06": 0.01, "2024-12-09": 0.02},
            "S2": {
                "2024-12-06": 0.0,
                "2024-12-07": 0.01,  # Sat
                "2024-12-08": 0.01,  # Sun
                "2024-12-09": 0.01,  # Mon
            },
        }
        biz, mat, names = roadmap.align_daily_sleeves_business_days(s_map, start_day="2024-12-06", end_day="2024-12-09")
        assert biz == ["2024-12-06", "2024-12-09"]
        assert names == ["S1", "S2"]
        assert mat[1, 1] == pytest.approx((1.01**3) - 1.0, rel=1e-12)

        with pytest.raises(HoldoutLockError):
            roadmap.align_daily_sleeves_business_days(s_map, start_day="2024-12-06", end_day="2025-01-01")

        # Starved-month calculation across 4 months (2 positive, 2 starved consecutively)
        m_dates = ["2024-01-15", "2024-02-15", "2024-03-15", "2024-04-15"]
        m_rets = np.array([0.02, -0.01, 0.0, 0.03], dtype=np.float64)
        st = roadmap.compute_starved_month_stats(m_dates, m_rets)
        assert st["n_months"] == 4
        assert st["starved_months_le_0"] == 2
        assert st["starved_month_rate_pct"] == 50.0
        assert st["max_consec_starved_months"] == 2

        # Hard CEX <= 25% cap enforcement
        rng_mat = np.full((4, 3), 0.001, dtype=np.float64)
        _, ok_meta = roadmap.simulate_monthly_rebalanced_portfolio(
            m_dates, rng_mat, np.array([0.40, 0.25, 0.35]), [0.0, 15.0, 5.0], cex_indices=(1,)
        )
        assert ok_meta["cex_weight_pct"] == 25.0
        with pytest.raises(ValueError, match="CEX_CAP_VIOLATION"):
            roadmap.simulate_monthly_rebalanced_portfolio(
                m_dates, rng_mat, np.array([0.39, 0.26, 0.35]), [0.0, 15.0, 5.0], cex_indices=(1,)
            )

        tiers = roadmap.build_capital_threshold_schedule(25_765.94)
        assert len(tiers) == 5
        assert tiers[0]["max_cex_pct"] == 0.0
        assert tiers[1]["max_cex_pct"] == 0.0
        assert all(float(t["max_cex_pct"]) <= 25.0 for t in tiers)


@pytest.mark.local_cache
class TestLocalCachePreHoldoutSlicing:
    """Real local-cache slicing & repo pre-registration tests (skipped in offline CI via `-m 'not local_cache'`)."""

    def test_real_macro_etf_and_etf40_caches_strict_dev_slice(self) -> None:
        if not roadmap.DEFAULT_MACRO_ETF_CACHE.is_dir() or not roadmap.DEFAULT_ETF40_CACHE.is_dir():
            pytest.skip("Local ETF caches not present")

        macro_panel = roadmap.load_macro_etf_dev_panel()
        assert max(macro_panel["dates"]) <= roadmap.DEV_MAX_DATE
        assert macro_panel["holdout_rows_analysed"] == 0
        assert macro_panel["excluded_post_cutoff_rows"] > 0

        p4, p7 = roadmap.load_etf40_dev_panels()
        assert max(p4["dates"]) <= roadmap.DEV_MAX_DATE
        assert max(p7["dates"]) <= roadmap.DEV_MAX_DATE
        assert p7["holdout_rows_analysed"] == 0
        assert p7["excluded_post_cutoff_rows"] > 0

    def test_real_crypto_spot_and_funding_caches_strict_dev_slice(self) -> None:
        if not roadmap.DEFAULT_CRYPTO_CACHE.is_dir():
            pytest.skip("Local crypto-spot-cache not present")

        sp = roadmap.load_crypto_spot_dev_panel()
        assert max(sp["dates"]) <= roadmap.DEV_MAX_DATE
        assert sp["holdout_rows_analysed"] == 0
        assert sp["excluded_post_cutoff_rows"] > 0

        fp = roadmap.load_crypto_funding_dev_panel(spot_panel=sp)
        assert max(fp["dates"]) <= roadmap.DEV_MAX_DATE
        assert fp["holdout_rows_analysed"] == 0
        assert fp["excluded_post_cutoff_rows"] > 0

    def test_real_repo_preregister_freeze_to_tmp_and_verify(self, tmp_path: Path) -> None:
        lock_path = REPO_ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"
        if not lock_path.is_file():
            pytest.skip("Holdout lock missing")
        sha_before = sha256_file(lock_path)
        assert sha_before == EXPECTED_HOLD_LOCK_SHA

        res = prereg.freeze_preregistration(
            repo_root=REPO_ROOT,
            out_dir=tmp_path,
            dry_run=False,
            now_utc="2026-11-27T12:00:00Z",
        )
        assert res["artifacts_hashed"] >= 7
        ver = prereg.verify_preregistration(repo_root=REPO_ROOT, out_dir=tmp_path)
        assert ver["status"] == "VERIFIED_PASS"
        assert ver["holdout_rows_analysed"] == 0
        assert ver["order_send_count"] == 0
        # Confirm NATIVE_FTMO_HOLDOUT_LOCK.json was NEVER mutated
        assert sha256_file(lock_path) == EXPECTED_HOLD_LOCK_SHA
