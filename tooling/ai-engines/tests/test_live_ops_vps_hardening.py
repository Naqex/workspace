"""Offline 100% CI-safe tests for Home-VPS Hardening v3 (`OrderSend = 0`).

Covers:
  - PowerShell AST syntax parse (zero parse errors) on all 5 scripts in `vps_kit/hardening_v3/`
  - Pure-ASCII / LF-only / Layer-1 OPSEC hygiene across all scripts and `CHAOS-DRILL-PLAYBOOK.md`
  - `-DryRun` and `-WhatIf` execution of `audit_firewall_minimal.ps1`, `rotate_mt5_logs.ps1`,
    `fim_sha256_daily.ps1`, `emergency_killswitch_guard.ps1` (B8 ACK PASS + RED escalation exit 2),
    and `sync_live_vault_readonly.ps1` (1-way pull + Holdout/Dev isolation).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import threading
import time
import unittest
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HARDENING_DIR = ROOT / "tooling/ai-engines/exports/deployment_kit/vps_kit/hardening_v3"

PS1_SCRIPTS = (
    "audit_firewall_minimal.ps1",
    "rotate_mt5_logs.ps1",
    "fim_sha256_daily.ps1",
    "emergency_killswitch_guard.ps1",
    "sync_live_vault_readonly.ps1",
)
PLAYBOOK_MD = HARDENING_DIR / "CHAOS-DRILL-PLAYBOOK.md"

_ANY_LAN_IP_RE = re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b")
_ANY_CGNAT_TS_RE = re.compile(r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b")
_HEROKU_APP_RE = re.compile(r"(?i)\bnaqex-" + "deadman-" + r"[a-z0-9-]+\b")
_TG_BOT_RE = re.compile(r"(?i)@?naqex_" + "guard_" + r"bot\b")
_WIN_USER_PATH_RE = re.compile(
    r"(?i)(?:[A-Z]:|/mnt/[a-z])[\\/]Users[\\/](?!<|YOUR_|user\b|username\b|example\b|runneradmin\b|public\b|default\b)[A-Za-z0-9._-]+"
)
_RAW_IPV4_RE = re.compile(r"\b(?!100\.64\.0\.0/10\b)(?:\d{1,3}\.){3}\d{1,3}\b")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def _run_ps1(script_name: str, args: list[str], *, timeout: int = 30) -> tuple[int, dict, str, str]:
    script_path = HARDENING_DIR / script_name
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
        *args,
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    raw_out = proc.stdout.strip()
    if not raw_out:
        raise AssertionError(f"{script_name} emitted empty stdout (rc={proc.returncode}): stderr={proc.stderr}")
    payload = json.loads(raw_out)
    return proc.returncode, payload, proc.stdout, proc.stderr


def _set_mtime_utc(path: Path, dt_utc: datetime) -> None:
    ts = dt_utc.timestamp()
    os.utime(path, (ts, ts))


def _build_red_news_csv(rows: int = 492) -> str:
    lines = ["utc_ts,ccy,event"]
    base_ts = 1796000000
    for i in range(rows):
        lines.append(f"{base_ts + i * 3600},USD,EVENT_{i:03d}")
    return "\n".join(lines) + "\n"


def _build_fim_fixture(root: Path, *, keep_private: str = "1", extra_ex5: bool = False) -> tuple[Path, Path, dict]:
    mt5 = root / "mt5"
    ex5_dir = mt5 / "MQL5/Experts/Naqex"
    preset_dir = mt5 / "MQL5/Presets"
    files_dir = mt5 / "MQL5/Files"
    cfg_dir = mt5 / "Config"
    for d in (ex5_dir, preset_dir, files_dir, cfg_dir):
        d.mkdir(parents=True, exist_ok=True)

    ex5_file = ex5_dir / "Naqex_Master_Prop7E_v103.ex5"
    ex5_file.write_bytes(b"NAQEX-MASTER-V103-BINARY-FIXTURE")
    if extra_ex5:
        (ex5_dir / "Rogue_Unsigned.ex5").write_bytes(b"ROGUE-EX5")

    set_file = preset_dir / "FTMO_Std10K_v103_Sprint.set"
    set_file.write_text("InpAllowManualHaltFile=true\nInpDryRunLogOnly=true\n", encoding="utf-8")

    csv_file = files_dir / "naqex_red_news_utc.csv"
    csv_file.write_text(_build_red_news_csv(492), encoding="utf-8")

    common_ini = cfg_dir / "common.ini"
    common_ini.write_text(f"[Common]\nKeepPrivate={keep_private}\nNewsEnable=0\n", encoding="utf-8")

    connector_ini = mt5 / "connector.ini"
    connector_ini.write_text("[Common]\nKeepPrivate=1\n", encoding="utf-8")

    manifest = {
        "schema": "naqex-fim-manifest-v3",
        "ex5": {ex5_file.name: _sha256_file(ex5_file)},
        "presets": {set_file.name: _sha256_file(set_file)},
        "red_news_csv_sha256": _sha256_file(csv_file),
        "common_ini_sha256": _sha256_file(common_ini),
    }
    manifest_path = root / "fim_manifest_sha256.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return mt5, manifest_path, manifest


class LiveOpsVpsHardeningTests(unittest.TestCase):
    def test_all_deliverables_exist_lf_clean_and_opsec_guarded(self) -> None:
        self.assertTrue(PLAYBOOK_MD.is_file(), f"Missing playbook: {PLAYBOOK_MD}")

        # 1. All 5 PowerShell scripts: LF-only, pure ASCII (PS 5.1 safe), OPSEC clean
        for name in PS1_SCRIPTS:
            p = HARDENING_DIR / name
            self.assertTrue(p.is_file(), f"Missing script: {p}")
            raw = p.read_bytes()
            self.assertNotIn(b"\r", raw, f"{name} must use LF line endings only")
            self.assertEqual(raw, raw.decode("ascii").encode("ascii"), f"{name} must be pure ASCII for PS 5.1 safety")
            txt = raw.decode("ascii")
            self.assertIsNone(_ANY_LAN_IP_RE.search(txt), f"Real/LAN IP found in {name}")
            for m in _ANY_CGNAT_TS_RE.finditer(txt):
                self.assertEqual(txt[m.start() : m.end() + 3], "100.64.0.0/10", f"CGNAT IP found in {name}")
            self.assertIsNone(_HEROKU_APP_RE.search(txt), f"Real Heroku app name found in {name}")
            self.assertIsNone(_TG_BOT_RE.search(txt), f"Real Telegram handle found in {name}")
            self.assertIsNone(_WIN_USER_PATH_RE.search(txt), f"Hardcoded Windows user path found in {name}")

        # 2. CHAOS-DRILL-PLAYBOOK.md: LF-only, 0 bare $, 0 real IPs, covers all 5 scenarios + reused ops tools
        md_bytes = PLAYBOOK_MD.read_bytes()
        self.assertNotIn(b"\r", md_bytes, "CHAOS-DRILL-PLAYBOOK.md must use LF line endings only")
        md_text = md_bytes.decode("utf-8")
        self.assertNotIn("$", md_text, "CHAOS-DRILL-PLAYBOOK.md must have ZERO bare dollar signs")
        self.assertIsNone(_ANY_LAN_IP_RE.search(md_text), "LAN IP leaked in CHAOS-DRILL-PLAYBOOK.md")
        for m in _ANY_CGNAT_TS_RE.finditer(md_text):
            self.assertEqual(md_text[m.start() : m.end() + 3], "100.64.0.0/10", "CGNAT IP leaked in playbook")
        self.assertIsNone(_HEROKU_APP_RE.search(md_text), "Real Heroku app leaked in playbook")
        self.assertIsNone(_TG_BOT_RE.search(md_text), "Real Telegram handle leaked in playbook")
        self.assertIsNone(_WIN_USER_PATH_RE.search(md_text), "Hardcoded Windows user path leaked in playbook")

        for required_token in (
            "Diễn Tập 1",
            "Diễn Tập 2",
            "Diễn Tập 3",
            "Diễn Tập 4",
            "Diễn Tập 5",
            "20:50 UTC",
            "manual_halt_ack",
            "<= 10s",
            "KeepPrivate=1",
            "node_ctl.py",
            "node_cutover_dryrun.py",
            "ftmo_pre_checkout_guard.py",
            "node_weekly_digest.py",
            "naqex_mt5_watchdog.ps1",
        ):
            self.assertIn(required_token, md_text, f"Playbook missing required section/reference: {required_token}")

        # 3. Test file itself must be LF-only
        self.assertNotIn(b"\r", Path(__file__).read_bytes(), "Test file must be LF-only")

    def test_powershell_ast_parse_zero_errors_all_five_scripts(self) -> None:
        paths_json = json.dumps([str(HARDENING_DIR / name) for name in PS1_SCRIPTS])
        ps_ast_cmd = (
            f"$files = '{paths_json}' | ConvertFrom-Json; "
            "$out = @(); "
            "foreach ($f in $files) { "
            "  $tokens = $null; $errs = $null; "
            "  $ast = [System.Management.Automation.Language.Parser]::ParseFile($f, [ref]$tokens, [ref]$errs); "
            "  $params = @($ast.ParamBlock.Parameters | ForEach-Object { $_.Name.VariablePath.UserPath }); "
            "  $attrs = @($ast.ParamBlock.Attributes | ForEach-Object { $_.Extent.Text }); "
            "  $out += [ordered]@{ "
            "    file = (Split-Path -Leaf $f); "
            "    error_count = @($errs).Count; "
            "    errors = @($errs | ForEach-Object { $_.Message }); "
            "    has_dryrun = ($params -contains 'DryRun'); "
            "    supports_whatif = (($attrs -join ' ') -match 'SupportsShouldProcess') "
            "  } "
            "}; "
            "$out | ConvertTo-Json -Depth 4 -Compress"
        )
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_ast_cmd],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, f"AST parse runner failed: {proc.stderr}")
        parsed = json.loads(proc.stdout.strip())
        self.assertEqual(len(parsed), 5)
        for item in parsed:
            self.assertEqual(item["error_count"], 0, f"AST errors in {item['file']}: {item['errors']}")
            self.assertTrue(item["has_dryrun"], f"{item['file']} missing -DryRun parameter")
            self.assertTrue(item["supports_whatif"], f"{item['file']} missing SupportsShouldProcess (-WhatIf)")

    def test_audit_firewall_minimal_dryrun_and_offline_fixtures(self) -> None:
        # 1. Live read-only -DryRun on local Windows host must succeed with 0 mutations & 0 raw IP leaks
        rc, js, raw_out, stderr = _run_ps1("audit_firewall_minimal.ps1", ["-DryRun"])
        self.assertEqual(rc, 0, f"audit_firewall_minimal -DryRun failed: {stderr} | {raw_out}")
        self.assertTrue(js["dry_run"])
        self.assertEqual(js["order_send_count"], 0)
        self.assertFalse(js["firewall_mutated"])
        self.assertEqual(len(js["required_outbound_allowlist"]), 4)
        self.assertIsNone(_RAW_IPV4_RE.search(raw_out), f"Raw IPv4 leaked in firewall audit output: {raw_out}")

        # 2. Clean hardened VPS offline fixture -> GREEN (exit 0)
        with tempfile.TemporaryDirectory() as td:
            fx_green = Path(td) / "fw_green.json"
            fx_green.write_text(
                json.dumps(
                    {
                        "profiles": [
                            {
                                "name": p,
                                "enabled": True,
                                "default_inbound_action": "Block",
                                "default_outbound_action": "Block",
                            }
                            for p in ("Domain", "Private", "Public")
                        ],
                        "tcp_listeners": [{"port": 22, "address_scope": "LAN_PRIVATE", "process": "sshd"}],
                        "udp_listeners": [{"port": 41641, "address_scope": "TAILSCALE_CGNAT", "process": "tailscaled"}],
                        "rules": [
                            {
                                "name": "Allow-MT5-Heroku-HTTPS",
                                "direction": "Outbound",
                                "action": "Allow",
                                "protocol": "TCP",
                                "remote_port": "443",
                            },
                            {
                                "name": "Allow-NTP",
                                "direction": "Outbound",
                                "action": "Allow",
                                "protocol": "UDP",
                                "remote_port": "123",
                            },
                            {
                                "name": "Allow-Tailscale",
                                "direction": "Outbound",
                                "action": "Allow",
                                "protocol": "UDP",
                                "remote_port": "41641",
                            },
                            {
                                "name": "Allow-SSH-Scoped",
                                "direction": "Inbound",
                                "action": "Allow",
                                "protocol": "TCP",
                                "local_port": "22",
                                "remote_scopes": ["LAN_PRIVATE", "TAILSCALE_CGNAT"],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            rc_g, js_g, _, _ = _run_ps1(
                "audit_firewall_minimal.ps1",
                ["-OfflineFixturePath", str(fx_green), "-StrictExit"],
            )
            self.assertEqual(rc_g, 0, f"Expected GREEN exit 0, got {js_g}")
            self.assertEqual(js_g["verdict"], "GREEN")
            self.assertEqual(js_g["outbound_posture_mode"], "STRICT_ALLOWLIST")
            self.assertEqual(js_g["unauthorized_inbound_count"], 0)
            self.assertTrue(all(f["permitted"] for f in js_g["required_outbound_allowlist"]))

            # 3. Compromised VPS fixture (disabled profile + unauthorized TCP 445/3389 + Any RDP) -> RED (exit 2)
            fx_red = Path(td) / "fw_red.json"
            fx_red.write_text(
                json.dumps(
                    {
                        "profiles": [
                            {
                                "name": "Public",
                                "enabled": False,
                                "default_inbound_action": "Allow",
                                "default_outbound_action": "Allow",
                            }
                        ],
                        "tcp_listeners": [
                            {"port": 445, "address_scope": "ANY_ADDR", "process": "System"},
                            {"port": 3389, "address_scope": "ANY_ADDR", "process": "svchost"},
                        ],
                        "udp_listeners": [],
                        "rules": [
                            {
                                "name": "Bad-RDP-Any",
                                "direction": "Inbound",
                                "action": "Allow",
                                "protocol": "TCP",
                                "local_port": "3389",
                                "remote_scopes": ["ANY_ADDR"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            rc_r, js_r, _, _ = _run_ps1(
                "audit_firewall_minimal.ps1",
                ["-OfflineFixturePath", str(fx_red), "-StrictExit"],
            )
            self.assertEqual(rc_r, 2)
            self.assertEqual(js_r["verdict"], "RED")
            self.assertEqual(js_r["unauthorized_inbound_count"], 2)
            self.assertGreaterEqual(len(js_r["overly_broad_inbound_rules"]), 1)

    def test_rotate_mt5_logs_dryrun_whatif_and_live_retention(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mt5 = root / "mt5"
            term_logs = mt5 / "Logs"
            mql5_logs = mt5 / "MQL5/Logs"
            archive_dir = root / "NaqexBackup/mt5-logs-archive"
            for d in (term_logs, mql5_logs, archive_dir / "mql5"):
                d.mkdir(parents=True, exist_ok=True)

            # Active today log (2026-11-27), recent 3-day log (2026-11-24), old 12-day log (2026-11-15)
            dt_today = datetime(2026, 11, 27, 11, 0, 0, tzinfo=UTC)
            dt_recent = datetime(2026, 11, 24, 12, 0, 0, tzinfo=UTC)
            dt_old = datetime(2026, 11, 15, 12, 0, 0, tzinfo=UTC)
            dt_expired_arc = datetime(2026, 8, 10, 12, 0, 0, tzinfo=UTC)
            dt_keep_arc = datetime(2026, 11, 7, 12, 0, 0, tzinfo=UTC)

            today_mql = mql5_logs / "20261127.log"
            today_mql.write_text("ACTIVE TODAY LOG LINE\n", encoding="utf-8")
            _set_mtime_utc(today_mql, dt_today)

            recent_mql = mql5_logs / "20261124.log"
            recent_mql.write_text("RECENT 3-DAY LOG\n", encoding="utf-8")
            _set_mtime_utc(recent_mql, dt_recent)

            old_mql = mql5_logs / "20261115.log"
            old_mql.write_text("OLD MQL5 LOG CONTENT TO COMPRESS\n" * 20, encoding="utf-8")
            _set_mtime_utc(old_mql, dt_old)

            old_term = term_logs / "20261115.log"
            old_term.write_text("OLD TERMINAL LOG CONTENT TO COMPRESS\n" * 15, encoding="utf-8")
            _set_mtime_utc(old_term, dt_old)

            expired_zip = archive_dir / "mql5/20260810_mql5.zip"
            with zipfile.ZipFile(expired_zip, "w") as zf:
                zf.writestr("20260810.log", "EXPIRED")
            _set_mtime_utc(expired_zip, dt_expired_arc)

            keep_zip = archive_dir / "mql5/20261107_mql5.zip"
            with zipfile.ZipFile(keep_zip, "w") as zf:
                zf.writestr("20261107.log", "KEEP")
            _set_mtime_utc(keep_zip, dt_keep_arc)

            common_args = [
                "-Mt5Root", str(mt5),
                "-ArchiveRoot", str(archive_dir),
                "-NowUtcIsoOverride", "2026-11-27T12:00:00Z",
                "-SimulatedSystemDriveFreeGb", "85.5",
            ]

            # 1. -DryRun: plans compression & pruning, mutates ZERO files
            rc_d, js_d, _, err_d = _run_ps1("rotate_mt5_logs.ps1", [*common_args, "-DryRun"])
            self.assertEqual(rc_d, 0, f"rotate -DryRun failed: {err_d} | {js_d}")
            self.assertTrue(js_d["dry_run"])
            self.assertEqual(js_d["status"], "DRYRUN_READY")
            self.assertEqual(js_d["order_send_count"], 0)
            self.assertIn("mql5/20261127.log", js_d["protected_active_files"])
            self.assertEqual(len(js_d["planned_compress_files"]), 2)
            self.assertEqual(js_d["planned_prune_archives"], ["20260810_mql5.zip"])
            self.assertEqual(js_d["compressed_files"], [])
            self.assertEqual(js_d["pruned_archives"], [])
            self.assertTrue(old_mql.is_file() and old_term.is_file() and expired_zip.is_file())

            # 2. -WhatIf: behaves identically to -DryRun with clean JSON and ZERO writes
            rc_w, js_w, _, err_w = _run_ps1("rotate_mt5_logs.ps1", [*common_args, "-WhatIf"])
            self.assertEqual(rc_w, 0, f"rotate -WhatIf failed: {err_w}")
            self.assertTrue(js_w["dry_run"])
            self.assertTrue(old_mql.is_file() and expired_zip.is_file())

            # 3. Live execution inside isolated tmp_path: compresses >7d, protects today & 3d, prunes >90d
            today_sha = _sha256_file(today_mql)
            rc_l, js_l, _, err_l = _run_ps1("rotate_mt5_logs.ps1", common_args)
            self.assertEqual(rc_l, 0, f"rotate live failed: {err_l} | {js_l}")
            self.assertEqual(js_l["status"], "ROTATED_CLEAN")
            self.assertEqual(len(js_l["compressed_files"]), 2)
            self.assertEqual(js_l["pruned_archives"], ["20260810_mql5.zip"])
            self.assertTrue(today_mql.is_file() and _sha256_file(today_mql) == today_sha)
            self.assertTrue(recent_mql.is_file())
            self.assertFalse(old_mql.exists())
            self.assertFalse(old_term.exists())
            self.assertTrue((archive_dir / "mql5/20261115_mql5.zip").is_file())
            self.assertTrue((archive_dir / "terminal/20261115_terminal.zip").is_file())
            self.assertFalse(expired_zip.exists())
            self.assertTrue(keep_zip.is_file())

            # 4. Low C: free space guard (<= 20 GB) fails closed with exit 2 in live mode
            rc_low, js_low, _, _ = _run_ps1(
                "rotate_mt5_logs.ps1",
                [
                    "-Mt5Root", str(mt5),
                    "-ArchiveRoot", str(archive_dir),
                    "-NowUtcIsoOverride", "2026-11-27T12:00:00Z",
                    "-SimulatedSystemDriveFreeGb", "15.0",
                ],
            )
            self.assertEqual(rc_low, 2)
            self.assertFalse(js_low["disk_guard_passed"])
            self.assertEqual(js_low["status"], "RED_LOW_DISK_AFTER_ROTATE")

            # 5. Broken-latch E: drive is strictly forbidden
            rc_e, js_e, _, _ = _run_ps1(
                "rotate_mt5_logs.ps1",
                ["-Mt5Root", str(mt5), "-ArchiveRoot", r"E:\BadBackup", "-DryRun"],
            )
            self.assertEqual(rc_e, 2)
            self.assertEqual(js_e["status"], "BLOCKED_FORBIDDEN_DRIVE_E")

    def test_fim_sha256_daily_dryrun_green_and_red_tamper_checks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mt5, manifest_path, _ = _build_fim_fixture(root)
            receipt_out = root / "receipts/fim_today.json"

            # 1. Clean fixture -> GREEN (exit 0), DryRun does NOT write receipt file
            rc, js, _, err = _run_ps1(
                "fim_sha256_daily.ps1",
                [
                    "-Mt5Root", str(mt5),
                    "-ManifestPath", str(manifest_path),
                    "-ReceiptOutPath", str(receipt_out),
                    "-DryRun",
                ],
            )
            self.assertEqual(rc, 0, f"FIM GREEN failed: {err} | {js}")
            self.assertEqual(js["verdict"], "GREEN")
            self.assertEqual(js["order_send_count"], 0)
            self.assertTrue(js["dry_run"])
            self.assertFalse(receipt_out.exists())
            self.assertTrue(js["summary"]["keep_private_ok"])
            self.assertTrue(js["summary"]["red_news_ok"])

            # 2. Tampered .ex5 -> RED (exit 2)
            (mt5 / "MQL5/Experts/Naqex/Naqex_Master_Prop7E_v103.ex5").write_bytes(b"TAMPERED-EX5-BYTES")
            rc_t, js_t, _, _ = _run_ps1(
                "fim_sha256_daily.ps1",
                ["-Mt5Root", str(mt5), "-ManifestPath", str(manifest_path), "-DryRun"],
            )
            self.assertEqual(rc_t, 2)
            self.assertEqual(js_t["verdict"], "RED")
            self.assertTrue(any("EX5_SHA256_MISMATCH" in f for f in js_t["failures"]))

        # 3. KeepPrivate=0 in Config\common.ini -> RED (exit 2)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mt5, manifest_path, _ = _build_fim_fixture(root, keep_private="0")
            rc_kp, js_kp, _, _ = _run_ps1(
                "fim_sha256_daily.ps1",
                ["-Mt5Root", str(mt5), "-ManifestPath", str(manifest_path), "-DryRun"],
            )
            self.assertEqual(rc_kp, 2)
            self.assertEqual(js_kp["verdict"], "RED")
            self.assertIn("KEEP_PRIVATE_DISABLED", js_kp["failures"])

        # 4. Unexpected rogue .ex5 -> RED (exit 2)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mt5, manifest_path, _ = _build_fim_fixture(root, extra_ex5=True)
            rc_u, js_u, _, _ = _run_ps1(
                "fim_sha256_daily.ps1",
                ["-Mt5Root", str(mt5), "-ManifestPath", str(manifest_path), "-DryRun"],
            )
            self.assertEqual(rc_u, 2)
            self.assertEqual(js_u["verdict"], "RED")
            self.assertTrue(any("UNEXPECTED_EX5" in f for f in js_u["failures"]))

    def test_emergency_killswitch_guard_b8_ack_pass_and_red_escalation(self) -> None:
        now_ts = 1795780000

        # Case A: -DryRun with InpAllowManualHaltFile=true & manual_halt_ack=true -> PASS (exit 0)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            files_dir = root / "MQL5/Files"
            files_dir.mkdir(parents=True, exist_ok=True)
            preset = root / "active.set"
            preset.write_text(
                "InpAllowManualHaltFile=true\nInpManualHaltFile=naqex_manual_halt.flag\n",
                encoding="utf-8",
            )
            hb_path = files_dir / "naqex_master_v103_heartbeat.json"
            hb_path.write_text(
                json.dumps(
                    {
                        "utc_ts": now_ts - 2,
                        "terminal_connected": True,
                        "manual_halt": True,
                        "manual_halt_ack": True,
                        "open_positions": 0,
                        "regime": "MANUAL_FLATTEN",
                    }
                ),
                encoding="utf-8",
            )
            rc, js, _, err = _run_ps1(
                "emergency_killswitch_guard.ps1",
                [
                    "-Mt5FilesDir", str(files_dir),
                    "-PresetPath", str(preset),
                    "-Action", "FLATTEN_ALL",
                    "-AckTimeoutSec", "2",
                    "-PollIntervalMs", "100",
                    "-NowUtcOverride", str(now_ts),
                    "-DryRun",
                ],
            )
            self.assertEqual(rc, 0, f"Kill-switch ACK PASS failed: {err} | {js}")
            self.assertEqual(js["verdict"], "DRYRUN_ACK_CONFIRMED")
            self.assertTrue(js["manual_halt_ack"])
            self.assertFalse(js["escalation_required"])
            self.assertFalse(js["flag_written"])
            self.assertFalse((files_dir / "naqex_manual_halt.flag").exists())
            self.assertEqual(js["order_send_count"], 0)

        # Case B: -DryRun with manual_halt_ack=false -> CRITICAL RED ESCALATION (exit 2)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            files_dir = root / "MQL5/Files"
            files_dir.mkdir(parents=True, exist_ok=True)
            preset = root / "active.set"
            preset.write_text("InpAllowManualHaltFile=true\n", encoding="utf-8")
            (files_dir / "naqex_master_v103_heartbeat.json").write_text(
                json.dumps(
                    {
                        "utc_ts": now_ts - 3,
                        "terminal_connected": True,
                        "manual_halt": False,
                        "manual_halt_ack": False,
                        "open_positions": 1,
                        "regime": "NORMAL",
                    }
                ),
                encoding="utf-8",
            )
            rc_r, js_r, _, _ = _run_ps1(
                "emergency_killswitch_guard.ps1",
                [
                    "-Mt5FilesDir", str(files_dir),
                    "-PresetPath", str(preset),
                    "-Action", "FLATTEN_ALL",
                    "-AckTimeoutSec", "1",
                    "-PollIntervalMs", "100",
                    "-NowUtcOverride", str(now_ts),
                    "-DryRun",
                ],
            )
            self.assertEqual(rc_r, 2, f"Expected exit 2 RED escalation, got rc={rc_r} js={js_r}")
            self.assertEqual(js_r["verdict"], "CRITICAL_RED_ESCALATION")
            self.assertTrue(js_r["escalation_required"])
            self.assertFalse(js_r["manual_halt_ack"])
            self.assertEqual(js_r["reason_code"], "ACK_TIMEOUT_MANUAL_HALT_UNCONFIRMED")
            steps_joined = " ".join(js_r["immediate_manual_steps"])
            self.assertIn("MT5 Mobile", steps_joined)
            self.assertIn("Algo Trading", steps_joined)
            self.assertIn("20:50 UTC", steps_joined)

        # Case C: Legacy preset InpAllowManualHaltFile=false -> immediate CRITICAL RED ESCALATION (exit 2)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            files_dir = root / "MQL5/Files"
            files_dir.mkdir(parents=True, exist_ok=True)
            preset = root / "legacy.set"
            preset.write_text("InpAllowManualHaltFile=false\n", encoding="utf-8")
            rc_l, js_l, _, _ = _run_ps1(
                "emergency_killswitch_guard.ps1",
                [
                    "-Mt5FilesDir", str(files_dir),
                    "-PresetPath", str(preset),
                    "-Action", "FLATTEN_ALL",
                    "-AckTimeoutSec", "30",
                    "-DryRun",
                ],
            )
            self.assertEqual(rc_l, 2)
            self.assertEqual(js_l["verdict"], "CRITICAL_RED_ESCALATION")
            self.assertEqual(js_l["reason_code"], "CAPABILITY_DISABLED_IN_PRESET")
            self.assertEqual(js_l["ack_timeout_sec"], 10)
            self.assertTrue(js_l["ack_timeout_clamped"])

        # Case D: Live atomic flag write in tmp_path + simulated EA ACK within <= 10s -> GREEN (exit 0)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            files_dir = root / "MQL5/Files"
            files_dir.mkdir(parents=True, exist_ok=True)
            preset = root / "live_optin.set"
            preset.write_text("InpAllowManualHaltFile=true\n", encoding="utf-8")
            hb_path = files_dir / "naqex_master_v103_heartbeat.json"
            flag_path = files_dir / "naqex_manual_halt.flag"
            hb_path.write_text(
                json.dumps(
                    {
                        "utc_ts": int(time.time()),
                        "terminal_connected": True,
                        "manual_halt": False,
                        "manual_halt_ack": False,
                        "open_positions": 1,
                        "regime": "NORMAL",
                    }
                ),
                encoding="utf-8",
            )

            def _sim_ea_ack() -> None:
                deadline = time.time() + 6.0
                while time.time() < deadline:
                    if flag_path.is_file() and "FLATTEN_ALL" in flag_path.read_text(encoding="utf-8"):
                        time.sleep(0.2)
                        hb_path.write_text(
                            json.dumps(
                                {
                                    "utc_ts": int(time.time()),
                                    "terminal_connected": True,
                                    "manual_halt": True,
                                    "manual_halt_ack": True,
                                    "open_positions": 0,
                                    "regime": "MANUAL_FLATTEN",
                                }
                            ),
                            encoding="utf-8",
                        )
                        return
                    time.sleep(0.05)

            worker = threading.Thread(target=_sim_ea_ack, daemon=True)
            worker.start()
            try:
                rc_live, js_live, _, err_live = _run_ps1(
                    "emergency_killswitch_guard.ps1",
                    [
                        "-Mt5FilesDir", str(files_dir),
                        "-PresetPath", str(preset),
                        "-Action", "FLATTEN_ALL",
                        "-AckTimeoutSec", "6",
                        "-PollIntervalMs", "100",
                    ],
                )
            finally:
                worker.join(timeout=3.0)

            self.assertEqual(rc_live, 0, f"Live atomic kill-switch ACK failed: {err_live} | {js_live}")
            self.assertEqual(js_live["verdict"], "GREEN_HALT_ACK_CONFIRMED")
            self.assertTrue(js_live["flag_written"])
            self.assertIsNotNone(js_live["flag_write_utc_ts"])
            self.assertTrue(js_live["manual_halt_ack"])
            self.assertLessEqual(js_live["elapsed_sec"], 10.0)
            self.assertIn("FLATTEN_ALL|", flag_path.read_text(encoding="utf-8"))

    def test_p1_01_stale_ack_with_open_positions_and_p1_02_string_bool_fail_closed(self) -> None:
        now_ts = 1795780500

        # P1-01a: Stale pre-existing manual_halt_ack=true (now - 90s) + open_positions=2 on frozen EA -> exit 2
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            files_dir = root / "MQL5/Files"
            files_dir.mkdir(parents=True, exist_ok=True)
            preset = root / "active.set"
            preset.write_text("InpAllowManualHaltFile=true\n", encoding="utf-8")
            (files_dir / "naqex_master_v103_heartbeat.json").write_text(
                json.dumps(
                    {
                        "utc_ts": now_ts - 90,
                        "terminal_connected": True,
                        "manual_halt": True,
                        "manual_halt_ack": True,
                        "open_positions": 2,
                        "regime": "HALT_NEW_ENTRIES",
                    }
                ),
                encoding="utf-8",
            )
            rc_s, js_s, _, _ = _run_ps1(
                "emergency_killswitch_guard.ps1",
                [
                    "-Mt5FilesDir", str(files_dir),
                    "-PresetPath", str(preset),
                    "-Action", "FLATTEN_ALL",
                    "-AckTimeoutSec", "1",
                    "-PollIntervalMs", "100",
                    "-NowUtcOverride", str(now_ts),
                ],
            )
            self.assertEqual(rc_s, 2, f"Stale pre-write ACK must escalate RED (exit 2), got rc={rc_s} js={js_s}")
            self.assertEqual(js_s["verdict"], "CRITICAL_RED_ESCALATION")
            self.assertEqual(js_s["reason_code"], "ACK_STALE_PRE_WRITE_HEARTBEAT")
            self.assertEqual(js_s["flag_write_utc_ts"], now_ts)
            self.assertTrue(js_s["flag_written"])
            self.assertFalse(js_s["manual_halt_ack"])

        # P1-01b: Fresh post-write heartbeat with manual_halt_ack=true BUT open_positions=2 on FLATTEN_ALL -> exit 2
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            files_dir = root / "MQL5/Files"
            files_dir.mkdir(parents=True, exist_ok=True)
            preset = root / "active.set"
            preset.write_text("InpAllowManualHaltFile=true\n", encoding="utf-8")
            (files_dir / "naqex_master_v103_heartbeat.json").write_text(
                json.dumps(
                    {
                        "utc_ts": now_ts + 1,
                        "terminal_connected": True,
                        "manual_halt": True,
                        "manual_halt_ack": True,
                        "open_positions": 2,
                        "regime": "MANUAL_FLATTEN",
                    }
                ),
                encoding="utf-8",
            )
            rc_o, js_o, _, _ = _run_ps1(
                "emergency_killswitch_guard.ps1",
                [
                    "-Mt5FilesDir", str(files_dir),
                    "-PresetPath", str(preset),
                    "-Action", "FLATTEN_ALL",
                    "-AckTimeoutSec", "1",
                    "-PollIntervalMs", "100",
                    "-NowUtcOverride", str(now_ts),
                ],
            )
            self.assertEqual(rc_o, 2, f"FLATTEN_ALL with open_positions=2 must escalate RED (exit 2), got {js_o}")
            self.assertEqual(js_o["verdict"], "CRITICAL_RED_ESCALATION")
            self.assertEqual(js_o["reason_code"], "FLATTEN_INCOMPLETE_POSITIONS_REMAIN")

        # P1-02a: Stringified "manual_halt_ack": "false" (and "0", "no", "true") MUST NOT coerce to true -> exit 2
        for bad_ack in ("false", "0", "no", "true"):
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                files_dir = root / "MQL5/Files"
                files_dir.mkdir(parents=True, exist_ok=True)
                preset = root / "active.set"
                preset.write_text("InpAllowManualHaltFile=true\n", encoding="utf-8")
                (files_dir / "naqex_master_v103_heartbeat.json").write_text(
                    json.dumps(
                        {
                            "utc_ts": now_ts,
                            "terminal_connected": True,
                            "manual_halt": True,
                            "manual_halt_ack": bad_ack,
                            "open_positions": 0,
                            "regime": "MANUAL_FLATTEN",
                        }
                    ),
                    encoding="utf-8",
                )
                rc_b, js_b, _, _ = _run_ps1(
                    "emergency_killswitch_guard.ps1",
                    [
                        "-Mt5FilesDir", str(files_dir),
                        "-PresetPath", str(preset),
                        "-Action", "FLATTEN_ALL",
                        "-AckTimeoutSec", "1",
                        "-PollIntervalMs", "100",
                        "-NowUtcOverride", str(now_ts),
                        "-DryRun",
                    ],
                )
                self.assertEqual(rc_b, 2, f"String ack {bad_ack!r} must fail closed (exit 2), got {js_b}")
                self.assertEqual(js_b["verdict"], "CRITICAL_RED_ESCALATION")
                self.assertFalse(js_b["manual_halt_ack"])
                self.assertIsNone(js_b["heartbeat"]["manual_halt_ack"])

        # P1-02b: Stringified "allow_manual_halt_file": "false" and "terminal_connected": "false" parse as $false
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            files_dir = root / "MQL5/Files"
            files_dir.mkdir(parents=True, exist_ok=True)
            (files_dir / "naqex_master_v103_heartbeat.json").write_text(
                json.dumps(
                    {
                        "utc_ts": now_ts,
                        "terminal_connected": "false",
                        "allow_manual_halt_file": "false",
                        "manual_halt_ack": True,
                        "open_positions": 0,
                    }
                ),
                encoding="utf-8",
            )
            rc_cap, js_cap, _, _ = _run_ps1(
                "emergency_killswitch_guard.ps1",
                [
                    "-Mt5FilesDir", str(files_dir),
                    "-Action", "FLATTEN_ALL",
                    "-AckTimeoutSec", "1",
                    "-NowUtcOverride", str(now_ts),
                    "-DryRun",
                ],
            )
            self.assertEqual(rc_cap, 2)
            self.assertEqual(js_cap["reason_code"], "CAPABILITY_DISABLED_IN_HEARTBEAT")
            self.assertFalse(js_cap["heartbeat"]["allow_manual_halt"])
            self.assertFalse(js_cap["heartbeat"]["terminal_connected"])

    def test_sync_live_vault_readonly_dryrun_pull_and_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src_dir = root / "node1_source"
            src_dir.mkdir(parents=True, exist_ok=True)
            vault_dir = root / ".runtime/live-vault"

            allowed_files = {
                "naqex_exec_audit.csv": b"utc_ts,symbol,event_type\n1795780000,USDJPY,ORDER_FILL\n",
                "naqex_decision_blackbox_20261127.jsonl": b'{"ts":1795780000,"decision":"ENTRY_OK"}\n',
                "naqex_m1_quote_tape_20261127.csv": b"utc_ts,symbol,bid,ask\n1795780000,USDJPY,150.10,150.11\n",
                "naqex_master_v103_heartbeat.json": b'{"utc_ts":1795780000,"terminal_connected":true}\n',
            }
            for fn, data in allowed_files.items():
                (src_dir / fn).write_bytes(data)
            # Forbidden credential/config files that must NEVER be pulled
            (src_dir / "accounts.dat").write_bytes(b"SECRET-ACCOUNTS-DAT")
            (src_dir / "common.ini").write_bytes(b"[Common]\nKeepPrivate=1\n")

            # 1. -DryRun: zero local writes, zero remote writes, forbidden files excluded
            rc_d, js_d, _, err_d = _run_ps1(
                "sync_live_vault_readonly.ps1",
                ["-OfflineSourceDir", str(src_dir), "-LocalVaultRoot", str(vault_dir), "-DryRun"],
            )
            self.assertEqual(rc_d, 0, f"sync_live_vault -DryRun failed: {err_d} | {js_d}")
            self.assertEqual(js_d["status"], "DRYRUN_PULL_PLAN_READY")
            self.assertEqual(js_d["remote_writes"], 0)
            self.assertEqual(js_d["local_files_written"], 0)
            self.assertEqual(js_d["planned_count"], 4)
            self.assertIn("accounts.dat", js_d["skipped_forbidden_files"])
            self.assertFalse(vault_dir.exists())

            # 2. Live offline 1-way pull: SHA-256 verified, Holdout/Dev isolated, zero forbidden copies
            rc_p, js_p, _, err_p = _run_ps1(
                "sync_live_vault_readonly.ps1",
                ["-OfflineSourceDir", str(src_dir), "-LocalVaultRoot", str(vault_dir)],
            )
            self.assertEqual(rc_p, 0, f"sync_live_vault pull failed: {err_p} | {js_p}")
            self.assertEqual(js_p["status"], "PULLED_CLEAN_VERIFIED")
            self.assertTrue(js_p["sha256_verified"])
            self.assertEqual(js_p["remote_writes"], 0)
            self.assertFalse(js_p["holdout_mixed"])
            self.assertFalse(js_p["dev_cache_mixed"])
            snap_dir = vault_dir / "snapshots" / js_p["snapshot_id"]
            self.assertTrue((snap_dir / "manifest.sha256.json").is_file())
            self.assertFalse((snap_dir / "accounts.dat").exists())
            self.assertFalse((snap_dir / "common.ini").exists())
            for fn in allowed_files:
                self.assertEqual(_sha256_file(snap_dir / fn), _sha256_file(src_dir / fn))

            # 3. Holdout / Dev-cache / E: mixing guard fails closed (exit 2)
            for bad_vault in (
                str(root / "holdout/live-vault"),
                str(root / "dev_cache/live-vault"),
                r"E:\live-vault",
                str(root / "random_dir"),
            ):
                rc_b, js_b, _, _ = _run_ps1(
                    "sync_live_vault_readonly.ps1",
                    ["-OfflineSourceDir", str(src_dir), "-LocalVaultRoot", bad_vault, "-DryRun"],
                )
                self.assertEqual(rc_b, 2, f"Expected bad vault target rejected: {bad_vault}")
                self.assertEqual(js_b["status"], "BLOCKED_FORBIDDEN_VAULT_TARGET")


if __name__ == "__main__":
    unittest.main()
