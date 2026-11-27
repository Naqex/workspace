"""Offline 100% CI-safe guard tests for `stage_total_offensive_2_when_flat.ps1` (`OrderSend = 0`)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

AI_ENGINES = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_ENGINES.parents[1]
STAGE_SCRIPT = AI_ENGINES / "exports/deployment_kit/vps_kit/stage_total_offensive_2_when_flat.ps1"
AUDIT_REPORT = REPO_ROOT / "planning/research/NODE1-PRE-NFP-STAGING-AUDIT-20261127.md"

_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6_RE = re.compile(
    r"(?:\b(?:[0-9a-fA-F]{1,4}:){3,7}[0-9a-fA-F]{1,4}\b"
    r"|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F:]{1,20}"
    r"|::[0-9a-fA-F:]{1,20})"
)
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def _make_clean_status() -> dict:
    return {
        "checked_utc": "2026-11-27T06:38:55Z",
        "order_send_count": 0,
        "heartbeat": {
            "terminal_connected": True,
            "positions_state": "CONFIRMED",
            "open_positions": 0,
            "total_account_positions": 0,
            "pending_orders": 0,
            "orphan_no_sl": 0,
            "age_sec": 12,
        },
        "ntp_offset": "-00.1056509s",
        "disks": {
            "C": {"free_gb": 91.7, "total_gb": 118.6},
            "D": {"free_gb": 465.6, "total_gb": 465.8},
        },
    }


def _make_clean_integrity() -> dict:
    return {
        "checked_utc": "2026-11-27T06:38:58Z",
        "order_send_count": 0,
        "ok": True,
        "common_ini": {"exists": True, "keep_private": "1", "has_login_override": False},
        "connector_ini": {"exists": True, "keep_private": None, "has_login_override": False},
    }


def _populate_fixture(
    root: Path,
    *,
    status: dict | None = None,
    integrity: dict | None = None,
    source_files: dict[str, bytes] | None = None,
) -> tuple[Path, Path]:
    (root / "status.json").write_text(
        json.dumps(status if status is not None else _make_clean_status(), indent=2),
        encoding="utf-8",
    )
    (root / "integrity.json").write_text(
        json.dumps(integrity if integrity is not None else _make_clean_integrity(), indent=2),
        encoding="utf-8",
    )
    src_dir = root / "source"
    src_dir.mkdir(parents=True, exist_ok=True)
    files = (
        source_files
        if source_files is not None
        else {
            "Naqex_Master_Prop7E.ex5": b"EX5-STAGING-FIXTURE-PAYLOAD-V101",
            "naqex_red_news_utc.csv": b"utc_ts,ccy,event\n1796391000,USD,US_NFP\n",
            "FTMO_Std10K_MasterProp7E_C10_P1_4x_L70.set": b"InpDryRunLogOnly=true\nInpGuardDryRunLogOnly=true\n",
        }
    )
    for name, data in files.items():
        (src_dir / name).write_bytes(data)

    # Sentinel live MT5 folder that must NEVER be modified by staging
    live_ex5_dir = root / "mt5_live" / "MQL5" / "Experts" / "Naqex"
    live_ex5_dir.mkdir(parents=True, exist_ok=True)
    sentinel = live_ex5_dir / "Naqex_Master_Prop7E.ex5"
    sentinel.write_bytes(b"LIVE-PRODUCTION-DO-NOT-OVERWRITE-SENTINEL")
    return src_dir, sentinel


def _run_stage_ps1(
    fixture_dir: Path,
    extra_args: list[str] | None = None,
    *,
    env_override: dict[str, str] | None = None,
) -> tuple[int, dict, str, str]:
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(STAGE_SCRIPT),
        "-OfflineFixtureDir",
        str(fixture_dir),
        "-LocalVerifyPython",
        sys.executable,
    ]
    if extra_args:
        cmd.extend(extra_args)
    env = None
    if env_override is not None:
        env = dict(os.environ)
        env.update(env_override)
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
        env=env,
    )
    payload = json.loads(proc.stdout.strip())
    return proc.returncode, payload, proc.stdout, proc.stderr


class Node1StagingGuardTests(unittest.TestCase):
    def test_script_and_audit_report_exist_and_are_lf_clean(self) -> None:
        self.assertTrue(STAGE_SCRIPT.is_file(), f"Missing script: {STAGE_SCRIPT}")
        self.assertTrue(AUDIT_REPORT.is_file(), f"Missing report: {AUDIT_REPORT}")

        ps_bytes = STAGE_SCRIPT.read_bytes()
        self.assertNotIn(b"\r", ps_bytes, "PS1 script must be LF-only")
        # Pure ASCII prevents Windows PowerShell 5.1 BOM-less encoding corruption
        self.assertEqual(ps_bytes, ps_bytes.decode("ascii").encode("ascii"))

        md_bytes = AUDIT_REPORT.read_bytes()
        self.assertNotIn(b"\r", md_bytes, "Audit report must be LF-only")
        md_text = md_bytes.decode("utf-8")
        self.assertNotIn("$", md_text, "Audit report must have zero bare dollar signs")
        self.assertIsNone(_IPV4_RE.search(md_text), "Audit report must not expose raw IPv4")
        self.assertIsNone(_IPV6_RE.search(md_text), "Audit report must not expose raw IPv6")
        self.assertIsNone(_URL_RE.search(md_text), "Audit report must not expose raw URLs")
        # Ensure no unredacted 9-10 digit broker login numbers appear (excluding documented UTC epoch timestamps)
        non_epoch_ids = [m.group(0) for m in re.finditer(r"\b\d{9,10}\b", md_text) if not m.group(0).startswith("1796")]
        self.assertEqual(non_epoch_ids, [], f"Potential raw broker login IDs in report: {non_epoch_ids}")
        for required_milestone in ("04/12/2026", "08/12/2026", "14/12/2026"):
            self.assertIn(required_milestone, md_text)

        test_bytes = Path(__file__).read_bytes()
        self.assertNotIn(b"\r", test_bytes, "Test file must be LF-only")

    def test_dryrun_flat_passes_with_zero_writes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, sentinel = _populate_fixture(root)
            sentinel_sha = _sha256_file(sentinel)

            rc, js, _, stderr = _run_stage_ps1(root, ["-DryRun"])
            self.assertEqual(rc, 0, f"DryRun failed: {js} | stderr={stderr}")
            self.assertEqual(js["status"], "DRYRUN_READY_FLAT")
            self.assertTrue(js["dry_run"])
            self.assertEqual(js["order_send_count"], 0)
            self.assertEqual(js["live_ex5_overwrites"], 0)
            self.assertFalse(js["autotrading_touched"])
            self.assertEqual(js["staged_count"], 0)
            self.assertEqual(js["planned_count"], 3)
            self.assertFalse((root / "staging" / "total-offensive-2").exists())
            self.assertEqual(_sha256_file(sentinel), sentinel_sha)

    def test_flat_stages_cleanly_with_two_sided_sha256_match_and_zero_live_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src_dir, sentinel = _populate_fixture(root)
            sentinel_sha = _sha256_file(sentinel)
            sentinel_mtime = sentinel.stat().st_mtime_ns

            rc, js, _, stderr = _run_stage_ps1(root)
            self.assertEqual(rc, 0, f"Staging failed: {js} | stderr={stderr}")
            self.assertEqual(js["status"], "STAGED_CLEAN_FLAT")
            self.assertFalse(js["dry_run"])
            self.assertTrue(js["sha256_verified"])
            self.assertEqual(js["sha256_mismatches"], [])
            self.assertEqual(js["staged_count"], 3)
            self.assertEqual(js["order_send_count"], 0)
            self.assertEqual(js["live_ex5_overwrites"], 0)
            self.assertFalse(js["autotrading_touched"])

            staged_dir = root / "staging" / "total-offensive-2"
            self.assertTrue(staged_dir.is_dir())
            for src_file in src_dir.iterdir():
                dst_file = staged_dir / src_file.name
                self.assertTrue(dst_file.is_file(), f"Missing staged file: {src_file.name}")
                expected_sha = _sha256_file(src_file)
                self.assertEqual(_sha256_file(dst_file), expected_sha)
                self.assertEqual(js["local_sha256"][src_file.name], expected_sha)
                self.assertEqual(js["remote_sha256"][src_file.name], expected_sha)

            # Live MT5 sentinel file must be untouched bit-for-bit
            self.assertEqual(_sha256_file(sentinel), sentinel_sha)
            self.assertEqual(sentinel.stat().st_mtime_ns, sentinel_mtime)

    def test_open_positions_gt_zero_blocks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            st = _make_clean_status()
            st["heartbeat"]["open_positions"] = 1
            st["heartbeat"]["total_account_positions"] = 1
            _populate_fixture(root, status=st)

            rc, js, _, _ = _run_stage_ps1(root)
            self.assertEqual(rc, 2)
            self.assertEqual(js["status"], "BLOCKED_OPEN_POSITIONS")
            self.assertIn("flat_positions_zero", js["failed_gates"])
            self.assertEqual(js["staged_count"], 0)
            self.assertFalse(js["sha256_verified"])
            self.assertFalse((root / "staging" / "total-offensive-2").exists())

    def test_ntp_drift_blocks_fail_closed(self) -> None:
        for bad_ntp in ("+1.250s", "-1.000s", "unknown"):
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                st = _make_clean_status()
                st["ntp_offset"] = bad_ntp
                _populate_fixture(root, status=st)

                rc, js, _, _ = _run_stage_ps1(root)
                self.assertEqual(rc, 2, f"Expected NTP block for {bad_ntp!r}, got {js}")
                self.assertEqual(js["status"], "BLOCKED_NTP_DRIFT")
                self.assertIn("ntp_drift_within_limit", js["failed_gates"])
                self.assertFalse((root / "staging" / "total-offensive-2").exists())

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            st = _make_clean_status()
            st["ntp_offset_ms"] = 1000.0
            _populate_fixture(root, status=st)

            rc, js, _, _ = _run_stage_ps1(root)
            self.assertEqual(rc, 2)
            self.assertEqual(js["status"], "BLOCKED_NTP_DRIFT")
            self.assertIn("ntp_drift_within_limit", js["failed_gates"])

    def test_disconnected_and_stale_heartbeat_block_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            st = _make_clean_status()
            st["heartbeat"]["terminal_connected"] = False
            _populate_fixture(root, status=st)

            rc, js, _, _ = _run_stage_ps1(root)
            self.assertEqual(rc, 2)
            self.assertEqual(js["status"], "BLOCKED_BROKER_DISCONNECTED")
            self.assertIn("broker_connected_and_fresh", js["failed_gates"])

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            st = _make_clean_status()
            st["heartbeat"]["age_sec"] = 360
            _populate_fixture(root, status=st)

            rc, js, _, _ = _run_stage_ps1(root)
            self.assertEqual(rc, 2)
            self.assertEqual(js["status"], "BLOCKED_STALE_HEARTBEAT")
            self.assertIn("broker_connected_and_fresh", js["failed_gates"])

    def test_low_disk_blocks_fail_closed(self) -> None:
        for low_gb in (19.9, 20.0):
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                st = _make_clean_status()
                st["disks"]["C"]["free_gb"] = low_gb
                _populate_fixture(root, status=st)

                rc, js, _, _ = _run_stage_ps1(root)
                self.assertEqual(rc, 2, f"Expected low-disk block for {low_gb}, got {js}")
                self.assertEqual(js["status"], "BLOCKED_LOW_DISK")
                self.assertIn("disk_c_free_above_min", js["failed_gates"])
                self.assertFalse((root / "staging" / "total-offensive-2").exists())

    def test_keep_private_disabled_or_login_override_blocks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ig = _make_clean_integrity()
            ig["common_ini"]["keep_private"] = "0"
            _populate_fixture(root, integrity=ig)

            rc, js, _, _ = _run_stage_ps1(root)
            self.assertEqual(rc, 2)
            self.assertEqual(js["status"], "BLOCKED_KEEP_PRIVATE")
            self.assertIn("keep_private_enabled", js["failed_gates"])
            self.assertFalse((root / "staging" / "total-offensive-2").exists())

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ig = _make_clean_integrity()
            ig["connector_ini"]["has_login_override"] = True
            _populate_fixture(root, integrity=ig)

            rc, js, _, _ = _run_stage_ps1(root)
            self.assertEqual(rc, 2)
            self.assertEqual(js["status"], "BLOCKED_KEEP_PRIVATE")
            self.assertIn("keep_private_enabled", js["failed_gates"])

    def test_live_mt5_and_forbidden_paths_are_rejected(self) -> None:
        forbidden_targets = [
            r"C:\Naqex\mt5\MQL5\Experts\Naqex",
            r"C:\Naqex\mt5\MQL5\Files",
            r"C:\Naqex\mt5",
            r"E:\staging\total-offensive-2",
            r"C:\Naqex\staging\..\mt5\MQL5\Experts",
            r"C:\Naqex\staging\.",
            r"C:\Naqex\staging\other-campaign",
            r"C:\Naqex\staging\total-offensive-2\.",
            r"C:\Naqex\staging\total-offensive-2\..",
            r"C:\Naqex\staging\total-offensive-2\sub.",
            r"C:\Naqex\staging\total-offensive-2-evil",
            r"C:\Naqex\staging\total-offensive-2\\sub",
        ]
        for bad_target in forbidden_targets:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                _populate_fixture(root)

                rc, js, _, _ = _run_stage_ps1(root, ["-RemoteStagingDir", bad_target])
                self.assertEqual(rc, 2, f"Forbidden target not blocked: {bad_target}")
                self.assertEqual(js["status"], "BLOCKED_FORBIDDEN_TARGET_PATH")
                self.assertIn("isolated_staging_target", js["failed_gates"])
                self.assertEqual(js["live_ex5_overwrites"], 0)
                self.assertFalse((root / "staging" / "total-offensive-2").exists())

        # Trailing forward-slash under canonical isolated root is accepted cleanly
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _populate_fixture(root)
            rc, js, _, _ = _run_stage_ps1(
                root,
                ["-DryRun", "-RemoteStagingDir", "C:/Naqex/staging/total-offensive-2/"],
            )
            self.assertEqual(rc, 0, f"Canonical trailing-slash staging path failed: {js}")
            self.assertEqual(js["status"], "DRYRUN_READY_FLAT")

    def test_verifier_sha_mismatch_non_json_and_ok_false_fail_closed(self) -> None:
        # 1. Two-sided SHA-256 mismatch -> exit 1 + SHA256_VERIFICATION_FAILED
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _populate_fixture(root)
            site_dir = root / "site_mismatch"
            site_dir.mkdir()
            (site_dir / "sitecustomize.py").write_text(
                "import json, os, sys\n"
                'print(json.dumps({"ok": True, "files": {"Naqex_Master_Prop7E.ex5": "0" * 64}}))\n'
                "sys.stdout.flush()\n"
                "os._exit(0)\n",
                encoding="utf-8",
            )
            rc, js, _, stderr = _run_stage_ps1(root, env_override={"PYTHONPATH": str(site_dir)})
            self.assertEqual(rc, 1, f"Expected exit 1 on SHA mismatch, got rc={rc} js={js} err={stderr}")
            self.assertEqual(js["status"], "SHA256_VERIFICATION_FAILED")
            self.assertFalse(js["sha256_verified"])
            self.assertIn("Naqex_Master_Prop7E.ex5", js["sha256_mismatches"])
            self.assertEqual(js["order_send_count"], 0)

        # 2. Non-JSON verifier output -> fail-closed sanitized JSON (never unhandled ConvertFrom-Json crash)
        syn_ipv4 = ".".join(("198", "51", "100", "99"))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _populate_fixture(root)
            site_dir = root / "site_nonjson"
            site_dir.mkdir()
            (site_dir / "sitecustomize.py").write_text(
                "import os, sys\n"
                f'print("NOT_JSON_OUTPUT {syn_ipv4} token=LeakVerifier99")\n'
                "sys.stdout.flush()\n"
                "os._exit(0)\n",
                encoding="utf-8",
            )
            rc, js, raw_stdout, raw_stderr = _run_stage_ps1(root, env_override={"PYTHONPATH": str(site_dir)})
            self.assertEqual(rc, 1, f"Expected exit 1 on non-JSON verifier output, got rc={rc}")
            self.assertEqual(js["status"], "SHA256_VERIFICATION_FAILED")
            self.assertFalse(js["sha256_verified"])
            self.assertIn("non-JSON", js["message"])
            self.assertEqual(raw_stderr.strip(), "")
            self.assertNotIn(syn_ipv4, raw_stdout)
            self.assertNotIn("LeakVerifier99", raw_stdout)

        # 3. Verifier reporting ok=false -> fail-closed SHA256_VERIFICATION_FAILED
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _populate_fixture(root)
            site_dir = root / "site_okfalse"
            site_dir.mkdir()
            (site_dir / "sitecustomize.py").write_text(
                "import json, os, sys\n"
                'print(json.dumps({"ok": False, "files": {}}))\n'
                "sys.stdout.flush()\n"
                "os._exit(0)\n",
                encoding="utf-8",
            )
            rc, js, _, _ = _run_stage_ps1(root, env_override={"PYTHONPATH": str(site_dir)})
            self.assertEqual(rc, 1)
            self.assertEqual(js["status"], "SHA256_VERIFICATION_FAILED")
            self.assertFalse(js["sha256_verified"])
            self.assertIn("expected true", js["message"])

    def test_forbidden_credential_files_and_bad_ssh_alias_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _populate_fixture(root, source_files={"accounts.dat": b"SECRET-BROKER-LOGIN"})
            rc, js, _, _ = _run_stage_ps1(root)
            self.assertEqual(rc, 2)
            self.assertEqual(js["status"], "BLOCKED_FORBIDDEN_CREDENTIAL_FILE")
            self.assertFalse((root / "staging" / "total-offensive-2").exists())

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _populate_fixture(root)
            rc, js, _, _ = _run_stage_ps1(root, ["-SshAlias", "-oProxyCommand=calc"])
            self.assertEqual(rc, 2)
            self.assertEqual(js["status"], "BLOCKED_INVALID_SSH_ALIAS")

    def test_opsec_scrubber_strips_ips_ipv6_urls_tokens_logins_and_usernames(self) -> None:
        syn_ipv4_a = ".".join(("198", "51", "100", "42"))
        syn_ipv4_b = ".".join(("203", "0", "113", "7"))
        syn_ipv6 = ":".join(("2001", "db8", "85a3", "", "8a2e", "370", "7334"))
        syn_url = "https" + "://deadman-synthetic.invalid/api?token=TokSynth99"
        syn_login = 9999001234
        syn_user = "ops" + "@" + "node.invalid"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            st = _make_clean_status()
            st["_ssh_host"] = "naqex-node1-ts"
            st["heartbeat"]["account_login"] = syn_login
            st["heartbeat"]["positions_state"] = (
                f"CONFIRMED {syn_ipv4_a} {syn_ipv4_b} {syn_ipv6} {syn_url} password=SynthPass99 {syn_user} $500"
            )
            _populate_fixture(root, status=st)

            rc, js, raw_stdout, raw_stderr = _run_stage_ps1(root)
            self.assertEqual(rc, 2)
            blob = raw_stdout + "\n" + raw_stderr
            self.assertIsNone(_IPV4_RE.search(blob), f"IPv4 leaked in output: {blob}")
            self.assertIsNone(_IPV6_RE.search(blob), f"IPv6 leaked in output: {blob}")
            self.assertIsNone(_URL_RE.search(blob), f"URL leaked in output: {blob}")
            for secret in (
                syn_ipv4_a,
                syn_ipv4_b,
                "TokSynth99",
                "SynthPass99",
                str(syn_login),
                "deadman-synthetic.invalid",
                syn_user,
                "_ssh_host",
                "$",
            ):
                self.assertNotIn(secret, blob, f"OPSEC leak {secret!r} found in output")

            # Current local Windows username must never leak via tmp_path
            cur_user = os.environ.get("USERNAME", "").strip()
            if cur_user and len(cur_user) >= 3:
                self.assertNotIn(cur_user.lower(), blob.lower(), "Local Windows username leaked in stdout")
            self.assertEqual(js["order_send_count"], 0)


if __name__ == "__main__":
    unittest.main()
