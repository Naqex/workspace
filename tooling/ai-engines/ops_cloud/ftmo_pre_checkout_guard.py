"""Fail-Closed Read-Only FTMO Pre-Checkout CGNAT, Geo-IP & 14-Day Red-News Guard (`OrderSend = 0`).

Checks mandatory pre-checkout compliance gates before purchasing an FTMO Standard 10K Black Friday
account on Monday 30/11/2026:
  1. Non-US Geo-IP verification (FTMO strictly prohibits US-located IPs/VPNs!)
  2. CGNAT (`100.64.0.0/10`) & double-NAT detection on `naqex-node1` (excluding Tailscale adapter)
  3. Next 14-day FTMO Standard Restricted News schedule (UTC & ICT `UTC+7`) from 492-row CSV
  4. `node_cutover_dryrun.py` 10/10 readiness integration

STRICT OPSEC INVARIANT:
  - Raw IPv4/IPv6 addresses, router IPs, and ISP names are evaluated strictly in-memory and NEVER
    emitted to stdout, JSON, logs, or files — ONLY sanitized boolean flags and ISO country code!
  - ZERO `OrderSend`, ZERO MT5 launches, ZERO remote writes, ZERO bare `$` in reports.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
import ipaddress
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0

OPS_CLOUD_DIR = Path(__file__).resolve().parent
AI_ENGINES_DIR = OPS_CLOUD_DIR.parent
EXPORTS_DIR = AI_ENGINES_DIR / "exports"
DEFAULT_NEWS_CSV = EXPORTS_DIR / "Files/naqex_red_news_utc.csv"
ICT_TZ = timezone(timedelta(hours=7))

for p in (OPS_CLOUD_DIR, EXPORTS_DIR, AI_ENGINES_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import node_ctl  # noqa: E402
import node_cutover_dryrun as cutover  # noqa: E402

_CGNAT_NET = ipaddress.ip_network("100.64.0.0/10")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6_RE = re.compile(
    r"(?:\b(?:[0-9a-fA-F]{1,4}:){3,7}[0-9a-fA-F]{1,4}\b|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F:]{1,20}|::[0-9a-fA-F:]{1,20})"
)
_FORBIDDEN_NET_KEYS = {
    "ip", "wan_ip", "public_ip", "router_ip", "hop_ips", "raw_hops", "isp", "org", "asn",
    "_ssh_host", "password", "token", "webhook", "secret", "account_login",
}


def strict_opsec_scrub(obj: Any) -> Any:
    """Recursively strip all IPv4, IPv6, URLs, secrets, ISP fields, and bare dollar signs."""
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if str(k).lower() in _FORBIDDEN_NET_KEYS:
                continue
            out[k] = strict_opsec_scrub(v)
        return out
    if isinstance(obj, list):
        return [strict_opsec_scrub(x) for x in obj]
    if isinstance(obj, str):
        s = cutover.sanitize_text(obj)
        s = _IPV6_RE.sub("[REDACTED_IPV6]", s)
        s = _IPV4_RE.sub("[REDACTED_IP]", s)
        return s.replace("$", "USD ")
    return obj


def classify_network_signals(
    *,
    country_code: str | None,
    geo_lookup_ok: bool,
    hop_ips: list[str] | None = None,
    non_tailscale_iface_ips: list[str] | None = None,
    is_cgnat_override: bool | None = None,
    double_nat_override: bool | None = None,
    probe_source: str = "offline",
) -> dict[str, Any]:
    """Classify Geo-IP & CGNAT strictly in memory; returns ONLY sanitized booleans & country_code (0 raw IPs)."""
    cc = str(country_code or "UNKNOWN").strip().upper()[:8] or "UNKNOWN"
    is_us = cc in ("US", "USA")

    cgnat_detected = False
    double_nat_detected = False

    for raw in (non_tailscale_iface_ips or []):
        try:
            ip_obj = ipaddress.ip_address(raw.strip())
            if isinstance(ip_obj, ipaddress.IPv4Address) and ip_obj in _CGNAT_NET:
                cgnat_detected = True
        except ValueError:
            continue

    # Inspect traceroute hops 2..3 (hop 1 is expected home LAN router)
    hops = list(hop_ips or [])
    for idx, raw in enumerate(hops):
        try:
            ip_obj = ipaddress.ip_address(raw.strip())
        except ValueError:
            continue
        if not isinstance(ip_obj, ipaddress.IPv4Address):
            continue
        if idx >= 1:
            if ip_obj in _CGNAT_NET:
                cgnat_detected = True
            elif ip_obj.is_private:
                double_nat_detected = True

    if is_cgnat_override is not None:
        cgnat_detected = bool(is_cgnat_override)
    if double_nat_override is not None:
        double_nat_detected = bool(double_nat_override)

    non_us_ok = bool(geo_lookup_ok) and (not is_us) and cc not in ("UNKNOWN", "", "NONE")

    if not geo_lookup_ok:
        rec = "Khong xac minh duoc ma quoc gia IP cong cong; kiem tra ket noi mang truoc khi thanh toan."
    elif is_us:
        rec = "CHAN CUNG: Phat hien IP dinh vi Hoa Ky (US) - FTMO cam tuyet doi IP/VPN My!"
    elif cgnat_detected:
        rec = "CANH BAO CGNAT: Nha mang VN dang cap dai CGNAT; xin IPv4 cong cong rieng truoc giai doan Funded va luu xac nhan email FTMO."
    elif double_nat_detected:
        rec = "LUU Y DOUBLE-NAT: Phat hien lop NAT trung gian (router/modem); kiem tra bridge mode neu can IP rieng."
    else:
        rec = "DAT CHUAN: IP ngoai My va khong phat hien dau hieu CGNAT tren duong truyen."

    return {
        "probe_source": probe_source,
        "geo_lookup_ok": bool(geo_lookup_ok),
        "country_code": cc,
        "is_us_ip_blocked": is_us,
        "non_us_verified": non_us_ok,
        "is_cgnat": cgnat_detected,
        "double_nat_suspected": double_nat_detected,
        "recommendation": rec,
    }


def probe_node1_network_readonly(*, host: str | None = None, timeout: int = 20) -> dict[str, Any]:
    """Run strictly read-only geo/CGNAT classification inside naqex-node1 so NO raw IP crosses SSH stdout."""
    target_host = host or node_ctl.resolve_ssh_host()
    py_remote = "\n".join(
        [
            "import ipaddress, json, re, subprocess, urllib.request",
            "cc = 'UNKNOWN'",
            "ok = False",
            "cgnat_net = ipaddress.ip_network('100.64.0.0/10')",
            "try:",
            "    t = urllib.request.urlopen('https://www.cloudflare.com/cdn-cgi/trace', timeout=6).read().decode('utf-8', 'ignore')",
            "    m = re.search(r'^loc=([A-Z]{2})', t, re.M)",
            "    if m:",
            "        cc = m.group(1)",
            "        ok = True",
            "except Exception:",
            "    pass",
            "cgnat = False",
            "dnat = False",
            "ps = \"@(Get-NetIPAddress -AddressFamily IPv4 -EA 0 | Where-Object { $_.InterfaceAlias -notmatch 'Tailscale|Loopback' } | Select-Object -ExpandProperty IPAddress) -join ','\"",
            "r1 = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True, timeout=6)",
            "for tok in r1.stdout.strip().split(','):",
            "    try:",
            "        ip = ipaddress.ip_address(tok.strip())",
            "        if ip in cgnat_net:",
            "            cgnat = True",
            "    except Exception:",
            "        pass",
            "r2 = subprocess.run(['tracert', '-d', '-h', '3', '-w', '800', '1.1.1.1'], capture_output=True, text=True, timeout=12)",
            "hop_idx = 0",
            "for ln in r2.stdout.splitlines():",
            "    hm = re.match(r'^\\s*(\\d+)\\s+.*?((\\d{1,3}\\.){3}\\d{1,3})', ln)",
            "    if not hm:",
            "        continue",
            "    hop_idx = int(hm.group(1))",
            "    try:",
            "        ip = ipaddress.ip_address(hm.group(2))",
            "        if hop_idx >= 2 and ip in cgnat_net:",
            "            cgnat = True",
            "        elif hop_idx >= 2 and ip.is_private:",
            "            dnat = True",
            "    except Exception:",
            "        pass",
            "print(json.dumps({'geo_lookup_ok': ok, 'country_code': cc, 'is_cgnat': cgnat, 'double_nat_suspected': dnat, 'hops_seen': hop_idx}))",
        ]
    ) + "\n"
    proc = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=6", "-o", "BatchMode=yes", target_host, f'"{node_ctl.REMOTE_PYTHON}" -'],
        input=py_remote,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return classify_network_signals(
            country_code="UNKNOWN",
            geo_lookup_ok=False,
            probe_source="node1_ssh_error",
        )
    data = json.loads(proc.stdout.strip().splitlines()[-1])
    return classify_network_signals(
        country_code=data.get("country_code"),
        geo_lookup_ok=bool(data.get("geo_lookup_ok")),
        is_cgnat_override=bool(data.get("is_cgnat")),
        double_nat_override=bool(data.get("double_nat_suspected")),
        probe_source="node1_readonly_ssh",
    )


def extract_upcoming_red_news(
    csv_path: Path = DEFAULT_NEWS_CSV,
    *,
    now_utc: datetime | None = None,
    horizon_days: int = 14,
) -> dict[str, Any]:
    """Extract upcoming restricted red-news events over `[now_utc, now_utc + horizon_days]` + Dec 2026 count."""
    ref = now_utc or datetime.now(timezone.utc)
    start_ts = int(ref.timestamp())
    end_ts = int((ref + timedelta(days=horizon_days)).timestamp())

    if not csv_path.is_file():
        return {
            "ok": False,
            "total_csv_rows": 0,
            "horizon_days": horizon_days,
            "upcoming_count": 0,
            "dec_2026_count": 0,
            "events": [],
        }

    total_rows = 0
    dec_2026_count = 0
    upcoming: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_ts = (row.get("utc_ts") or "").strip()
            if not raw_ts:
                continue
            ts = int(raw_ts)
            ccy = (row.get("ccy") or "").strip().upper()
            ev = (row.get("event") or "").strip()
            total_rows += 1
            dt_u = datetime.fromtimestamp(ts, tz=timezone.utc)
            if dt_u.year == 2026 and dt_u.month == 12:
                dec_2026_count += 1
            if start_ts <= ts <= end_ts:
                dt_ict = dt_u.astimezone(ICT_TZ)
                upcoming.append(
                    {
                        "utc_ts": ts,
                        "utc_iso": dt_u.strftime("%Y-%m-%d %H:%M UTC"),
                        "ict_iso": dt_ict.strftime("%Y-%m-%d %H:%M ICT"),
                        "ccy": ccy,
                        "event": ev,
                        "pre_flatten_utc": f"{(dt_u - timedelta(seconds=300)).strftime('%H:%M:%S')}..{(dt_u - timedelta(seconds=135)).strftime('%H:%M:%S')}",
                    }
                )
    upcoming.sort(key=lambda x: (x["utc_ts"], x["ccy"], x["event"]))
    return {
        "ok": total_rows >= 492,
        "total_csv_rows": total_rows,
        "window_start_utc": ref.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_end_utc": (ref + timedelta(days=horizon_days)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "horizon_days": horizon_days,
        "upcoming_count": len(upcoming),
        "dec_2026_count": dec_2026_count,
        "events": upcoming,
    }


def evaluate_pre_checkout(
    *,
    network: dict[str, Any],
    news: dict[str, Any],
    cutover_result: dict[str, Any],
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Combine Geo-IP/CGNAT, 14-day Red-News, and 10/10 cutover gates into final pre-checkout verdict."""
    hard_blocks: list[str] = []
    warnings: list[str] = []

    if not network.get("geo_lookup_ok"):
        hard_blocks.append("GEO_IP_LOOKUP_FAILED")
    if network.get("is_us_ip_blocked"):
        hard_blocks.append("US_IP_PROHIBITED_BY_FTMO")
    if not news.get("ok"):
        hard_blocks.append("RED_NEWS_CSV_INCOMPLETE")
    if cutover_result.get("verdict") != "READY_FOR_CUTOVER":
        hard_blocks.append(f"CUTOVER_NOT_READY:{','.join(cutover_result.get('failed_gates', []))}")

    if network.get("is_cgnat"):
        warnings.append("CGNAT_DETECTED_REQUEST_PUBLIC_IPV4_BEFORE_FUNDED")
    if network.get("double_nat_suspected"):
        warnings.append("DOUBLE_NAT_DETECTED_VERIFY_ROUTER_WAN")

    verdict = "PRE_CHECKOUT_READY" if (not hard_blocks and not warnings) else "ACTION_REQUIRED"

    payload = {
        "schema": "naqex-ftmo-pre-checkout-guard-v1",
        "checked_utc": (now_utc or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "order_send_count": ORDER_SEND_COUNT,
        "verdict": verdict,
        "hard_blocks": hard_blocks,
        "warnings": warnings,
        "network": network,
        "cutover": {
            "verdict": cutover_result.get("verdict"),
            "gates_passed": cutover_result.get("gates_passed"),
            "gates_total": cutover_result.get("gates_total"),
            "failed_gates": cutover_result.get("failed_gates", []),
            "target_preset": cutover_result.get("target_preset"),
        },
        "red_news": news,
    }
    return strict_opsec_scrub(payload)


def render_pre_checkout_vi(result: dict[str, Any]) -> str:
    """Render concise plain-Vietnamese pre-checkout report (0 bare $, 0 real IPs/tokens)."""
    net = result["network"]
    cut = result["cutover"]
    rn = result["red_news"]
    v_vi = (
        "SAN SANG THANH TOAN (PRE_CHECKOUT_READY)"
        if result["verdict"] == "PRE_CHECKOUT_READY"
        else "CAN XU LY TRUOC KHI MUA / FUNDED (ACTION_REQUIRED)"
    )
    lines = [
        "============================================================",
        "CONG KIEM TRA TRUOC THANH TOAN FTMO 10K (CHI DOC | OrderSend=0)",
        f"Thoi diem UTC : {result['checked_utc']}",
        f"Phan quyet    : {v_vi}",
        "============================================================",
        "1. Dia ly IP & CGNAT (da an 100% dia chi IP that):",
        f"   - Quoc gia={net['country_code']} | Ngoai My={net['non_us_verified']} | Chan IP My={net['is_us_ip_blocked']}",
        f"   - CGNAT (100.64/10)={net['is_cgnat']} | Double-NAT={net['double_nat_suspected']} | Nguon={net['probe_source']}",
        f"   - Khuyen nghi: {net['recommendation']}",
        "2. Cong san sang naqex-node1 (node_cutover_dryrun):",
        f"   - Ket qua: {cut['verdict']} ({cut['gates_passed']}/{cut['gates_total']} cong DAT) | Preset={cut['target_preset']}",
        f"3. Lich tin do FTMO Standard {rn['horizon_days']} ngay toi (CSV {rn['total_csv_rows']} dong | Thang 12/2026: {rn['dec_2026_count']} su kien):",
    ]
    if not rn["events"]:
        lines.append("   - Khong co su kien tin do nao trong cua so da chon.")
    else:
        for ev in rn["events"][:20]:
            lines.append(f"   - {ev['ict_iso']} ({ev['utc_iso']}) | {ev['ccy']:3s} | {ev['event']} | Xa truoc: {ev['pre_flatten_utc']} UTC")
        if len(rn["events"]) > 20:
            lines.append(f"   - ... (+{len(rn['events']) - 20} su kien khac trong JSON)")
    if result["hard_blocks"]:
        lines.append(f"CHAN CUNG  : {', '.join(result['hard_blocks'])}")
    if result["warnings"]:
        lines.append(f"CANH BAO   : {', '.join(result['warnings'])}")
    lines.append("============================================================")
    return strict_opsec_scrub("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Read-only FTMO pre-checkout CGNAT, Geo-IP & 14-day Red-News guard (OrderSend=0).")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live-readonly", action="store_true", help="Run read-only probes on naqex-node1.")
    mode.add_argument("--offline-fixture", type=Path, help="Offline JSON fixture with network + cutover probe data.")
    ap.add_argument("--preset", type=str, default=cutover.DEFAULT_PRESET)
    ap.add_argument("--news-csv", type=Path, default=DEFAULT_NEWS_CSV)
    ap.add_argument("--days", type=int, default=14, help="Upcoming red-news lookahead horizon in days.")
    ap.add_argument("--host", type=str, default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    local_kit = cutover.verify_local_kit_and_preset(args.preset)
    now_dt: datetime | None = None

    if args.offline_fixture is not None:
        fx = json.loads(args.offline_fixture.read_text(encoding="utf-8"))
        if fx.get("now_utc"):
            now_dt = datetime.fromisoformat(str(fx["now_utc"]).replace("Z", "+00:00"))
        net_in = fx.get("network", {})
        net = classify_network_signals(
            country_code=net_in.get("country_code"),
            geo_lookup_ok=bool(net_in.get("geo_lookup_ok", True)),
            hop_ips=net_in.get("hop_ips"),
            non_tailscale_iface_ips=net_in.get("non_tailscale_iface_ips"),
            is_cgnat_override=net_in.get("is_cgnat"),
            double_nat_override=net_in.get("double_nat_suspected"),
            probe_source="offline_fixture",
        )
        cut_res = cutover.evaluate_cutover_readiness(
            status=fx.get("status", {}),
            integrity=fx.get("integrity", {}),
            maint=fx.get("maint", {}),
            audit=fx.get("audit", {}),
            local_kit=local_kit,
            now_utc=now_dt,
        )
    else:
        st, ig, mt, au = cutover.run_live_readonly_probes(host=args.host)
        cut_res = cutover.evaluate_cutover_readiness(
            status=st, integrity=ig, maint=mt, audit=au, local_kit=local_kit, now_utc=now_dt,
        )
        net = probe_node1_network_readonly(host=args.host)

    news = extract_upcoming_red_news(args.news_csv, now_utc=now_dt, horizon_days=args.days)
    result = evaluate_pre_checkout(network=net, news=news, cutover_result=cut_res, now_utc=now_dt)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(render_pre_checkout_vi(result))
    return 0 if result["verdict"] == "PRE_CHECKOUT_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
