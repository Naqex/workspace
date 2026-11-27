"""Localhost-only HTTP handler, server factory, and CLI entrypoint for Naqex Cockpit."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from cockpit.modules.automation import (
    build_automation_events_payload,
    build_automation_features_payload,
    build_automation_status_payload,
)
from cockpit.modules.node1 import build_node1_summary_payload
from cockpit.modules.portfolio import build_allocations_payload, build_overview_payload, build_summary_payload
from cockpit.modules.prop_metrix import build_prop_metrix_payload
from cockpit.modules.sprint import build_blackfriday_sprint_payload
from cockpit.modules.state import DEFAULT_HOST, DEFAULT_PORT, MIME_TYPES, ORDER_SEND_COUNT, ROOT, STATIC_DIR
from cockpit.modules.stress import build_stress_payload, compute_vnd_risk_calculator
from cockpit.modules.telemetry import (
    apply_emergency_cover_action,
    build_live_telemetry_payload,
    handle_prop_terms_audit_request,
    read_emergency_cover_state,
)
from quant_factory.ibkr_macro_rebalancer import VALID_MODES, generate_rebalance_plan
from quant_factory.treasury_ledger import DEFAULT_USD_VND_RATE


def _qs_float(qs: dict[str, list[str]], key: str, default: float) -> float:
    vals = qs.get(key)
    if not vals:
        return default
    try:
        return float(vals[0])
    except (ValueError, TypeError):
        return default


def _qs_str(qs: dict[str, list[str]], key: str, default: str) -> str:
    vals = qs.get(key)
    return str(vals[0]) if vals else default


def _qs_flag(qs: dict[str, list[str]], key: str) -> bool:
    return _qs_str(qs, key, "0") in ("1", "true", "yes")


def _qs_int(qs: dict[str, list[str]], key: str, default: int) -> int:
    vals = qs.get(key)
    if not vals:
        return default
    try:
        return int(vals[0])
    except (ValueError, TypeError):
        return default


def make_handler(root: Path = ROOT, static_dir: Path = STATIC_DIR) -> type[BaseHTTPRequestHandler]:
    class CockpitHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            # Keep stdout/stderr quiet during automated smoke tests
            return

        def _send_bytes(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, code: int, payload: Any) -> None:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send_bytes(code, raw, "application/json; charset=utf-8")

        def _serve_static(self, rel_name: str) -> None:
            try:
                target = (static_dir / rel_name).resolve()
                base = static_dir.resolve()
                target.relative_to(base)
            except Exception:
                self._send_json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
                return
            if not target.is_file():
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            mime = MIME_TYPES.get(target.suffix.lower(), "application/octet-stream")
            self._send_bytes(HTTPStatus.OK, target.read_bytes(), mime)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            qs = parse_qs(parsed.query)

            if path in ("/", "/index.html"):
                self._serve_static("index.html")
                return
            if path.startswith("/static/"):
                self._serve_static(path[len("/static/") :])
                return
            if path == "/api/health":
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "service": "naqex-cockpit",
                        "order_send_count": ORDER_SEND_COUNT,
                        "utc": datetime.now(UTC).isoformat(),
                    },
                )
                return
            if path == "/api/summary":
                self._send_json(HTTPStatus.OK, build_summary_payload(root))
                return
            if path == "/api/overview":
                cap_u = _qs_float(qs, "capital_usd", 50_000.0)
                fx_r = _qs_float(qs, "usd_vnd", DEFAULT_USD_VND_RATE)
                self._send_json(HTTPStatus.OK, build_overview_payload(root, capital_usd=cap_u, usd_vnd_rate=fx_r))
                return
            if path == "/api/allocations":
                self._send_json(HTTPStatus.OK, build_allocations_payload(root))
                return
            if path == "/api/live-telemetry":
                self._send_json(HTTPStatus.OK, build_live_telemetry_payload(root))
                return
            if path == "/api/prop-metrix":
                prog = _qs_str(qs, "program", "ftmo_free_trial_10k")
                offline = _qs_flag(qs, "offline")
                self._send_json(
                    HTTPStatus.OK,
                    build_prop_metrix_payload(root, program=prog, allow_cloud_fetch=not offline),
                )
                return
            if path == "/api/emergency-cover":
                self._send_json(HTTPStatus.OK, read_emergency_cover_state(root))
                return
            if path == "/api/blackfriday-sprint":
                nocache = _qs_flag(qs, "nocache")
                self._send_json(HTTPStatus.OK, build_blackfriday_sprint_payload(root, use_cache=not nocache))
                return
            if path == "/api/node1-summary":
                offline = _qs_flag(qs, "offline")
                nocache = _qs_flag(qs, "nocache")
                self._send_json(
                    HTTPStatus.OK,
                    build_node1_summary_payload(root, allow_ssh=not offline, use_cache=not nocache),
                )
                return
            if path == "/api/automation/status":
                self._send_json(HTTPStatus.OK, build_automation_status_payload(root))
                return
            if path == "/api/automation/events":
                limit = _qs_int(qs, "limit", 50)
                ev_type = _qs_str(qs, "type", "") or None
                sev = _qs_str(qs, "severity", "") or None
                self._send_json(
                    HTTPStatus.OK,
                    build_automation_events_payload(root, limit=limit, event_type=ev_type, severity=sev),
                )
                return
            if path == "/api/automation/features":
                self._send_json(HTTPStatus.OK, build_automation_features_payload(root))
                return
            if path == "/api/stress":
                cap_u = _qs_float(qs, "capital_usd", 50_000.0)
                fx_r = _qs_float(qs, "usd_vnd", DEFAULT_USD_VND_RATE)
                self._send_json(HTTPStatus.OK, build_stress_payload(root, capital_usd=cap_u, usd_vnd_rate=fx_r))
                return
            if path == "/api/vnd-calculator":
                res = compute_vnd_risk_calculator(
                    capital_vnd=_qs_float(qs, "capital_vnd", 250_000_000.0),
                    usd_vnd_rate=_qs_float(qs, "usd_vnd", DEFAULT_USD_VND_RATE),
                    prop_nominal_usd=_qs_float(qs, "prop_nominal_usd", 10_000.0),
                    risk_profile=_qs_str(qs, "risk_profile", "balanced"),
                    cost_mult=_qs_float(qs, "cost_mult", 1.0),
                    root=root,
                )
                self._send_json(HTTPStatus.OK, res)
                return
            if path == "/api/rebalancer":
                mode = _qs_str(qs, "mode", "M5_VOL_PARITY_TREND_GUARD")
                if mode not in VALID_MODES:
                    mode = "M5_VOL_PARITY_TREND_GUARD"
                eq = _qs_float(qs, "equity_usd", 25_000.0)
                try:
                    plan = generate_rebalance_plan(
                        mode=mode,
                        equity_usd=max(100.0, eq),
                        cache_dir=root / ".runtime/macro-etf-cache",
                    )
                    self._send_json(HTTPStatus.OK, plan)
                except Exception as exc:
                    self._send_json(
                        HTTPStatus.OK,
                        {
                            "schema": "naqex-ibkr-macro-rebalance-v1",
                            "order_send_count": ORDER_SEND_COUNT,
                            "dry_run_only": True,
                            "available": False,
                            "reason": str(exc),
                        },
                    )
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found", "path": path})

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path not in ("/api/vnd-calculator", "/api/emergency-cover", "/api/prop-terms-audit"):
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(min(length, 65_536))
                body = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
                return
            if parsed.path == "/api/emergency-cover":
                status_c, payload = apply_emergency_cover_action(root, body)
                self._send_json(status_c, payload)
                return
            if parsed.path == "/api/prop-terms-audit":
                status_c, payload = handle_prop_terms_audit_request(body)
                self._send_json(status_c, payload)
                return
            res = compute_vnd_risk_calculator(
                capital_vnd=float(body.get("capital_vnd", 250_000_000.0)),
                usd_vnd_rate=float(body.get("usd_vnd", DEFAULT_USD_VND_RATE)),
                prop_nominal_usd=float(body.get("prop_nominal_usd", 10_000.0)),
                risk_profile=str(body.get("risk_profile", "balanced")),
                cost_mult=float(body.get("cost_mult", 1.0)),
                root=root,
            )
            self._send_json(HTTPStatus.OK, res)

    return CockpitHandler


def create_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    root: Path = ROOT,
    static_dir: Path = STATIC_DIR,
) -> ThreadingHTTPServer:
    if host not in ("127.0.0.1", "localhost"):
        raise ValueError(f"Cockpit server MUST bind strictly to localhost/127.0.0.1, refused '{host}'")
    return ThreadingHTTPServer((host, port), make_handler(root=root, static_dir=static_dir))


def main() -> int:
    ap = argparse.ArgumentParser(description="Naqex Quant Pod Local Web Control Room (127.0.0.1)")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = ap.parse_args()

    srv = create_server(host=args.host, port=args.port)
    actual_port = srv.server_address[1]
    print(
        f"Naqex Quant Pod Cockpit listening at http://{args.host}:{actual_port} (OrderSend=0, Read-Only)",
        flush=True,
    )
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0
