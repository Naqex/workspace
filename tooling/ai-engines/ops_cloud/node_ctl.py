"""Dev-PC single-command read-only controller for Naqex Home-VPS (`OrderSend = 0`).

Usage:
    python tooling/ai-engines/ops_cloud/node_ctl.py status
    python tooling/ai-engines/ops_cloud/node_ctl.py logs --scope mql5 --days 1 --errors-only
    python tooling/ai-engines/ops_cloud/node_ctl.py integrity
    python tooling/ai-engines/ops_cloud/node_ctl.py maint
    python tooling/ai-engines/ops_cloud/node_ctl.py audit
    python tooling/ai-engines/ops_cloud/node_ctl.py deploy-scripts
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent / "node_scripts"
REMOTE_PYTHON = r"C:\Naqex\tools\python\cpython-3.12-windows-x86_64-none\python.exe"
REMOTE_SCRIPTS_DIR = r"C:\Naqex\scripts"
DEFAULT_HOSTS: tuple[str, ...] = ("naqex-node1", "naqex-node1-ts")

SCRIPT_MAP: dict[str, str] = {
    "status": "node_status.py",
    "logs": "node_logs.py",
    "integrity": "node_integrity.py",
    "maint": "node_maint_check.py",
    "audit": "node_exec_audit.py",
}


def resolve_ssh_host(hosts: tuple[str, ...] = DEFAULT_HOSTS, timeout: int = 4) -> str:
    """Try primary LAN alias first, fall back to Tailscale alias."""
    for host in hosts:
        try:
            r = subprocess.run(
                ["ssh", "-o", f"ConnectTimeout={timeout}", "-o", "BatchMode=yes", host, "echo OK"],
                capture_output=True, text=True, timeout=timeout + 3,
            )
            if r.returncode == 0 and "OK" in r.stdout:
                return host
        except Exception:
            continue
    raise RuntimeError(f"Unable to reach any SSH host in {hosts}")


def run_remote_probe(
    command_key: str,
    extra_args: list[str] | None = None,
    *,
    host: str | None = None,
    timeout: int = 20,
) -> dict:
    if command_key not in SCRIPT_MAP:
        raise ValueError(f"Unknown probe command: {command_key}")
    target_host = host or resolve_ssh_host()
    script_name = SCRIPT_MAP[command_key]
    arg_str = " ".join(extra_args or [])
    remote_cmd = f'"{REMOTE_PYTHON}" "{REMOTE_SCRIPTS_DIR}\\{script_name}" {arg_str}'.strip()
    proc = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes", target_host, remote_cmd],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Remote probe {script_name} failed on {target_host} (rc={proc.returncode}): {proc.stderr.strip()}")
    payload = json.loads(proc.stdout.strip())
    payload["_ssh_host"] = target_host
    return payload


def deploy_scripts(*, host: str | None = None) -> dict:
    target_host = host or resolve_ssh_host()
    subprocess.run(
        ["ssh", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes", target_host, f'if not exist "{REMOTE_SCRIPTS_DIR}" mkdir "{REMOTE_SCRIPTS_DIR}"'],
        check=True, capture_output=True, text=True, timeout=15,
    )
    deployed: list[str] = []
    for name in sorted(SCRIPT_MAP.values()):
        local_p = SCRIPTS_DIR / name
        if not local_p.exists():
            raise FileNotFoundError(f"Missing local script: {local_p}")
        remote_dst = f"{target_host}:C:/Naqex/scripts/{name}"
        subprocess.run(
            ["scp", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes", str(local_p), remote_dst],
            check=True, capture_output=True, text=True, timeout=20,
        )
        deployed.append(name)
    return {"ok": True, "order_send_count": 0, "ssh_host": target_host, "deployed": deployed}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Single-command read-only Naqex Home-VPS controller.")
    ap.add_argument("action", choices=("status", "logs", "integrity", "maint", "audit", "deploy-scripts"))
    ap.add_argument("--host", default=None, help="Explicit SSH host alias (default: auto LAN -> Tailscale).")
    args, unknown = ap.parse_known_args(argv)

    if args.action == "deploy-scripts":
        res = deploy_scripts(host=args.host)
    else:
        res = run_remote_probe(args.action, extra_args=unknown, host=args.host)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
