"""Naqex Heroku Cloud Dead-Man's-Switch & Remote Telemetry Monitor.

Budget-calibrated for GitHub Student Heroku Credits (`312 USD`, `2026-10-01 -> 2028-09-30`):
  - `1 × Basic Dyno` (`7 USD/mo`, 24/7 no sleep)
  - `1 × Heroku Postgres Essential-0` (`5 USD/mo`, durable state surviving 24h dyno restarts)
  - Total: `12 USD/mo <= 13 USD/mo` Student cap (~264 USD / 312 USD over 22 months = 0 USD billed to card)

Endpoints:
  - `POST /api/heartbeat`  (Bearer `NAQEX_INGEST_TOKEN` required; fail-closed if unset)
  - `GET  /health`         (Lightweight readiness endpoint, zero secrets)
  - `GET  /api/status`     (JSON telemetry snapshot; protected by `NAQEX_VIEW_TOKEN` if set)
  - `GET  /`               (Mobile-friendly flat-dark status dashboard; auto-refresh 30s)

Hard Safety Invariants:
  - `ORDER_SEND_COUNT = 0` (100% read-only monitor; NEVER holds broker passwords or places orders)
  - Auto-prunes `naqex_heartbeat_log` to `10,000` rows so Postgres Essential-0 never fills over 24 months
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hmac
import html
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import threading
import time
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlparse
import urllib.request

try:
    import psycopg  # type: ignore[import-not-found]
except Exception:
    psycopg = None

ORDER_SEND_COUNT: int = 0
DEFAULT_STALE_AFTER_SEC: int = 180
DEFAULT_CHECK_INTERVAL_SEC: int = 15
DEFAULT_ALERT_COOLDOWN_SEC: int = 900
MAX_HISTORY_PER_NODE: int = 200
MAX_PG_HEARTBEAT_ROWS: int = 10_000
VN_TZ = timezone(timedelta(hours=7))


def format_duration_vi(seconds: float) -> str:
    """Format seconds into concise human-readable duration (e.g. 45s, 3m 15s, 1h 48m)."""
    sec = max(0, int(round(seconds)))
    if sec < 60:
        return f"{sec}s"
    mins, rem_s = divmod(sec, 60)
    if mins < 60:
        return f"{mins}m {rem_s:02d}s" if rem_s else f"{mins}m"
    hrs, rem_m = divmod(mins, 60)
    if hrs < 24:
        return f"{hrs}h {rem_m:02d}m" if rem_m else f"{hrs}h"
    days, rem_h = divmod(hrs, 24)
    return f"{days}d {rem_h}h" if rem_h else f"{days}d"


def format_reason_vi(code: str) -> str:
    """Translate machine health codes into clear Vietnamese SRE descriptions."""
    c = str(code or "").strip()
    if c == "MT5_PROCESS_DOWN":
        return "Tiến trình MT5 (terminal64.exe) đã dừng"
    if c == "BROKER_DISCONNECTED":
        return "MT5 mất kết nối máy chủ sàn (terminal_connected=false)"
    if c == "POSITIONS_STATE_UNKNOWN":
        return "Không xác định được số lệnh mở do mất kết nối sàn"
    if c == "DAILY_ANCHOR_UNRECOVERED":
        return "Chưa khôi phục được mốc số dư đầu ngày sau gián đoạn — đã khóa mở lệnh mới"
    if c.startswith("EXPECTED_NODE_MISSING"):
        return "Máy chủ dự kiến chưa gửi nhịp tim nào sau khi khởi động dịch vụ"
    if c.startswith("INNER_HEARTBEAT_STALE="):
        age = c.split("=", 1)[1]
        return f"Dữ liệu nhịp tim bên trong MT5 đã cũ ({age}) — nghi treo EA hoặc phát lại snapshot cũ"
    if c.startswith("INNER_HEARTBEAT_FUTURE="):
        skew = c.split("=", 1)[1]
        return f"Đồng hồ MT5 lệch về tương lai ({skew}) — cần kiểm tra NTP"
    if c == "KILL_SWITCH_ACTIVE":
        return "Kill-Switch bảo vệ tài khoản đã kích hoạt"
    if c.startswith("ORPHAN_NO_SL="):
        cnt = c.split("=", 1)[1]
        return f"Phát hiện {cnt} lệnh mở KHÔNG CÓ Stop Loss"
    if c.startswith("DAILY_DD="):
        val = c.split("=", 1)[1]
        return f"Drawdown ngày đã chạm {val}"
    if c.startswith("REGIME="):
        reg = c.split("=", 1)[1]
        return f"Chế độ quản trị rủi ro chuyển sang {reg}"
    if c.startswith("NO_HEARTBEAT_"):
        return "Mất tín hiệu nhịp tim từ máy chủ"
    return c


def _fmt_money(val: Any) -> str:
    try:
        return f"{float(val):,.2f} USD"
    except Exception:
        return "—"


def format_alert_message(
    *,
    kind: str,
    label: str,
    now_ts: float,
    hb: dict[str, Any] | None = None,
    reasons: list[str] | None = None,
    age_sec: float | None = None,
    stale_after_sec: int = DEFAULT_STALE_AFTER_SEC,
) -> tuple[str, str]:
    """Build clean, scannable SRE alerts as (telegram_html, plain_text)."""
    hb = hb or {}
    reasons = reasons or []
    dt_utc = datetime.fromtimestamp(now_ts, timezone.utc)
    dt_vn = dt_utc.astimezone(VN_TZ)
    ts_str = f"{dt_vn.strftime('%H:%M:%S')} ICT ({dt_utc.strftime('%H:%M')} UTC)"

    eq = hb.get("equity")
    bal = hb.get("balance")
    pnl_part = ""
    try:
        if eq is not None and bal is not None:
            pnl = float(eq) - float(bal)
            pnl_part = f" · PnL {pnl:+.2f} USD"
    except Exception:
        pnl_part = ""

    open_pos = hb.get("open_positions")
    orphan = hb.get("orphan_no_sl")
    regime = str(hb.get("regime") or "NORMAL").upper()
    dd_day = hb.get("daily_dd_pct")

    header_map = {
        "STALE": ("🔴", "MẤT KẾT NỐI", "PC_OFFLINE"),
        "CRITICAL": ("🚨", "CẢNH BÁO KHẨN", "CRITICAL"),
        "WARNING": ("🟡", "LƯU Ý RỦI RO", "WARNING"),
        "RECOVERED": ("🟢", "ĐÃ PHỤC HỒI", "RECOVERED"),
    }
    icon, title_vi, tag = header_map.get(kind, ("ℹ️", kind, kind))
    esc_label = html.escape(label)

    html_lines = [f"{icon} <b>{title_vi}</b> · <code>{esc_label}</code>", ""]
    plain_lines = [f"[{tag}] {label}"]

    if kind == "STALE":
        dur = format_duration_vi(age_sec or 0.0)
        thr = format_duration_vi(stale_after_sec)
        html_lines.append(f"<b>Trạng thái:</b> Mất nhịp tim <code>{html.escape(dur)}</code> (ngưỡng <code>{html.escape(thr)}</code>)")
        plain_lines.append(f"Trạng thái: Mất nhịp tim {dur} (ngưỡng {thr})")
    elif kind == "RECOVERED":
        html_lines.append("<b>Trạng thái:</b> Hệ thống đã kết nối &amp; hoạt động bình thường (<code>OK</code>)")
        plain_lines.append("Trạng thái: Hệ thống đã kết nối & hoạt động bình thường (OK)")
    else:
        html_lines.append("<b>Nguyên nhân:</b>")
        plain_lines.append("Nguyên nhân:")
        for r in reasons:
            desc = format_reason_vi(r)
            html_lines.append(f"• {html.escape(desc)} (<code>{html.escape(r)}</code>)")
            plain_lines.append(f"- {desc} ({r})")

    if eq is not None or bal is not None or open_pos is not None:
        html_lines.append("")
        html_lines.append("<b>Tài khoản gần nhất:</b>")
        eq_txt = _fmt_money(eq)
        bal_txt = _fmt_money(bal)
        html_lines.append(f"• Equity: <code>{html.escape(eq_txt)}</code> (Bal <code>{html.escape(bal_txt)}</code>{html.escape(pnl_part)})")
        plain_lines.append(f"Equity: {eq_txt} | Bal: {bal_txt}{pnl_part}")

        dd_txt = f"{float(dd_day):.2f}%" if dd_day is not None else "—"
        pos_txt = str(open_pos) if open_pos is not None else "—"
        orp_txt = str(orphan) if orphan is not None else "—"
        html_lines.append(
            f"• Lệnh mở: <code>{html.escape(pos_txt)}</code> · Thiếu SL: <code>{html.escape(orp_txt)}</code> "
            f"· DD ngày: <code>{html.escape(dd_txt)}</code> · <code>{html.escape(regime)}</code>"
        )
        plain_lines.append(f"Lệnh mở: {pos_txt} | Thiếu SL: {orp_txt} | DD ngày: {dd_txt} | {regime}")

    html_lines.append(f"<b>Thời điểm:</b> <code>{html.escape(ts_str)}</code>")
    plain_lines.append(f"Thời điểm: {ts_str}")

    if kind == "STALE":
        html_lines.append("")
        html_lines.append("👉 <i>Kiểm tra nguồn điện, mạng nhà hoặc mở RDP <code>100.72.70.18</code></i>")
        plain_lines.append("Hành động: Kiểm tra nguồn điện, mạng nhà hoặc mở RDP 100.72.70.18")
    elif kind in ("CRITICAL", "WARNING"):
        html_lines.append("")
        html_lines.append("👉 <i>Kiểm tra ngay trên RDP <code>100.72.70.18</code> hoặc bảng điều khiển</i>")
        plain_lines.append("Hành động: Kiểm tra ngay trên RDP 100.72.70.18 hoặc bảng điều khiển")

    return "\n".join(html_lines), " | ".join(plain_lines)


@dataclass
class NodeState:
    account_label: str
    first_seen_ts: float
    last_seen_ts: float
    last_payload: dict[str, Any] = field(default_factory=dict)
    status: str = "OK"  # OK | WARNING | CRITICAL | STALE
    active_reasons: list[str] = field(default_factory=list)
    last_alert_key: str = ""
    last_alert_ts: float = 0.0
    history: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=MAX_HISTORY_PER_NODE))


class PostgresStore:
    """Lightweight durable persistence over Heroku Postgres Essential-0 (`DATABASE_URL`)."""

    def __init__(self, database_url: str) -> None:
        if psycopg is None:
            raise RuntimeError("psycopg is required when DATABASE_URL is configured")
        # Heroku exports postgres://; psycopg3 accepts postgresql://
        self.dsn = database_url.replace("postgres://", "postgresql://", 1) if database_url.startswith("postgres://") else database_url
        self._init_schema()

    def _connect(self):
        return psycopg.connect(self.dsn, autocommit=True, connect_timeout=8)

    def _init_schema(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS naqex_nodes (
                    account_label TEXT PRIMARY KEY,
                    first_seen_ts DOUBLE PRECISION NOT NULL,
                    last_seen_ts DOUBLE PRECISION NOT NULL,
                    status TEXT NOT NULL,
                    active_reasons_json TEXT NOT NULL,
                    last_payload_json TEXT NOT NULL,
                    last_alert_key TEXT NOT NULL DEFAULT '',
                    last_alert_ts DOUBLE PRECISION NOT NULL DEFAULT 0.0
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS naqex_heartbeat_log (
                    id BIGSERIAL PRIMARY KEY,
                    ts DOUBLE PRECISION NOT NULL,
                    account_label TEXT NOT NULL,
                    status TEXT NOT NULL,
                    equity DOUBLE PRECISION,
                    balance DOUBLE PRECISION,
                    open_positions INTEGER,
                    orphan_no_sl INTEGER,
                    regime TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS naqex_alert_log (
                    id BIGSERIAL PRIMARY KEY,
                    ts DOUBLE PRECISION NOT NULL,
                    utc TEXT NOT NULL,
                    account_label TEXT NOT NULL,
                    event_key TEXT NOT NULL,
                    text TEXT NOT NULL,
                    dispatch_json TEXT NOT NULL
                );
            """)

    def load_state(self) -> tuple[dict[str, NodeState], list[dict[str, Any]]]:
        nodes: dict[str, NodeState] = {}
        alerts: list[dict[str, Any]] = []
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT account_label, first_seen_ts, last_seen_ts, status, active_reasons_json, "
                "last_payload_json, last_alert_key, last_alert_ts FROM naqex_nodes"
            )
            for row in cur.fetchall():
                label, f_ts, l_ts, st, reasons_j, pay_j, a_key, a_ts = row
                try:
                    reasons = json.loads(reasons_j)
                except Exception:
                    reasons = []
                try:
                    payload = json.loads(pay_j)
                except Exception:
                    payload = {}
                nodes[label] = NodeState(
                    account_label=label,
                    first_seen_ts=float(f_ts),
                    last_seen_ts=float(l_ts),
                    last_payload=payload,
                    status=str(st),
                    active_reasons=list(reasons),
                    last_alert_key=str(a_key or ""),
                    last_alert_ts=float(a_ts or 0.0),
                )
            cur.execute(
                "SELECT utc, account_label, event_key, text, dispatch_json "
                "FROM naqex_alert_log ORDER BY id DESC LIMIT 50"
            )
            for utc_s, label, ev_k, txt, disp_j in reversed(cur.fetchall()):
                try:
                    disp = json.loads(disp_j)
                except Exception:
                    disp = {}
                alerts.append({
                    "utc": utc_s,
                    "account_label": label,
                    "event_key": ev_k,
                    "text": txt,
                    "dispatch": disp,
                })
        return nodes, alerts

    def save_node_and_heartbeat(self, node: NodeState, hb_entry: dict[str, Any]) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO naqex_nodes (
                    account_label, first_seen_ts, last_seen_ts, status,
                    active_reasons_json, last_payload_json, last_alert_key, last_alert_ts
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (account_label) DO UPDATE SET
                    last_seen_ts = EXCLUDED.last_seen_ts,
                    status = EXCLUDED.status,
                    active_reasons_json = EXCLUDED.active_reasons_json,
                    last_payload_json = EXCLUDED.last_payload_json,
                    last_alert_key = EXCLUDED.last_alert_key,
                    last_alert_ts = EXCLUDED.last_alert_ts
                """,
                (
                    node.account_label,
                    node.first_seen_ts,
                    node.last_seen_ts,
                    node.status,
                    json.dumps(node.active_reasons, ensure_ascii=False),
                    json.dumps(node.last_payload, ensure_ascii=False),
                    node.last_alert_key,
                    node.last_alert_ts,
                ),
            )
            cur.execute(
                """
                INSERT INTO naqex_heartbeat_log (
                    ts, account_label, status, equity, balance, open_positions, orphan_no_sl, regime
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    float(hb_entry["ts"]),
                    node.account_label,
                    str(hb_entry["status"]),
                    hb_entry.get("equity"),
                    hb_entry.get("balance"),
                    hb_entry.get("open_positions"),
                    hb_entry.get("orphan_no_sl"),
                    hb_entry.get("regime"),
                ),
            )
            # Periodic rolling cap so Essential-0 1GB storage never overflows over 24 months
            if int(hb_entry["ts"]) % 10 == 0:
                cur.execute(
                    "DELETE FROM naqex_heartbeat_log WHERE id NOT IN "
                    f"(SELECT id FROM naqex_heartbeat_log ORDER BY id DESC LIMIT {MAX_PG_HEARTBEAT_ROWS})"
                )

    def save_alert(self, node: NodeState, alert_rec: dict[str, Any], ts: float) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO naqex_alert_log (ts, utc, account_label, event_key, text, dispatch_json)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    float(ts),
                    alert_rec["utc"],
                    alert_rec["account_label"],
                    alert_rec["event_key"],
                    alert_rec["text"],
                    json.dumps(alert_rec["dispatch"], ensure_ascii=False),
                ),
            )
            cur.execute(
                "UPDATE naqex_nodes SET status=%s, active_reasons_json=%s, last_alert_key=%s, last_alert_ts=%s "
                "WHERE account_label=%s",
                (
                    node.status,
                    json.dumps(node.active_reasons, ensure_ascii=False),
                    node.last_alert_key,
                    node.last_alert_ts,
                    node.account_label,
                ),
            )

    def heartbeat_row_count(self) -> int:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM naqex_heartbeat_log")
            r = cur.fetchone()
            return int(r[0]) if r else 0

    def delete_node(self, account_label: str) -> bool:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM naqex_nodes WHERE account_label = %s", (account_label,))
            return bool(cur.rowcount and cur.rowcount > 0)


def dispatch_alert_message(
    text: str,
    *,
    html_text: str = "",
    telegram_bot_token: str = "",
    telegram_chat_id: str = "",
    webhook_url: str = "",
    timeout_sec: float = 10.0,
) -> dict[str, Any]:
    """Send alert via Telegram Bot API (HTML format) and/or Discord/Slack webhook (pure stdlib)."""
    sent: list[str] = []
    errors: list[str] = []

    if telegram_bot_token and telegram_chat_id:
        url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        tg_body: dict[str, Any] = {
            "chat_id": telegram_chat_id,
            "text": html_text or text,
            "disable_web_page_preview": True,
        }
        if html_text:
            tg_body["parse_mode"] = "HTML"
        payload = json.dumps(tg_body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                if 200 <= resp.status < 300:
                    sent.append("telegram")
                else:
                    errors.append(f"telegram:http_{resp.status}")
        except Exception as exc:
            errors.append(f"telegram:{exc}")

    if webhook_url:
        payload = json.dumps({"text": text, "content": text}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "Naqex-Deadman/1.2"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                if 200 <= resp.status < 300:
                    sent.append("webhook")
                else:
                    errors.append(f"webhook:http_{resp.status}")
        except Exception as exc:
            errors.append(f"webhook:{exc}")

    return {"sent": sent, "errors": errors, "configured": bool((telegram_bot_token and telegram_chat_id) or webhook_url)}


class DeadmanMonitor:
    """Thread-safe state tracker + Dead-Man's-Switch alert evaluator with optional Postgres persistence."""

    def __init__(
        self,
        *,
        ingest_token: str,
        view_token: str = "",
        require_view_token: bool = True,
        stale_after_sec: int = DEFAULT_STALE_AFTER_SEC,
        alert_cooldown_sec: int = DEFAULT_ALERT_COOLDOWN_SEC,
        expected_nodes: list[str] | tuple[str, ...] | None = None,
        alert_sender: Callable[[str], dict[str, Any]] | None = None,
        clock_fn: Callable[[], float] = time.time,
        pg_store: PostgresStore | None = None,
    ) -> None:
        self.ingest_token = ingest_token.strip()
        self.view_token = view_token.strip()
        self.require_view_token = bool(require_view_token)
        self.stale_after_sec = max(30, int(stale_after_sec))
        self.alert_cooldown_sec = max(30, int(alert_cooldown_sec))
        self._clock = clock_fn
        self._started_ts = float(clock_fn())
        self.expected_nodes: list[str] = [
            str(x).strip() for x in (expected_nodes or []) if str(x).strip()
        ]
        self._alert_sender = alert_sender or self._default_alert_sender
        self._store = pg_store
        self._lock = threading.Lock()
        self._nodes: dict[str, NodeState] = {}
        self._channel_cooldown: dict[tuple[str, str, str], float] = {}
        self.alerts_emitted: deque[dict[str, Any]] = deque(maxlen=100)

        if self._store is not None:
            try:
                loaded_nodes, loaded_alerts = self._store.load_state()
                self._nodes.update(loaded_nodes)
                for a in loaded_alerts:
                    self.alerts_emitted.append(a)
            except Exception as exc:
                print(f"[WARN] Postgres load_state failed, continuing in-memory: {exc}", flush=True)

    def _default_alert_sender(
        self,
        text: str,
        html_text: str = "",
        *,
        skip_channels: set[str] | None = None,
    ) -> dict[str, Any]:
        skip = skip_channels or set()
        return dispatch_alert_message(
            text,
            html_text=html_text,
            telegram_bot_token="" if "telegram" in skip else os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(),
            telegram_chat_id="" if "telegram" in skip else os.environ.get("TELEGRAM_CHAT_ID", "").strip(),
            webhook_url="" if "webhook" in skip else os.environ.get("ALERT_WEBHOOK_URL", "").strip(),
        )

    def verify_ingest_token(self, auth_header: str) -> tuple[bool, str]:
        if not self.ingest_token:
            return False, "INGEST_TOKEN_NOT_CONFIGURED"
        prefix = "Bearer "
        if not auth_header.startswith(prefix):
            return False, "MISSING_BEARER_TOKEN"
        supplied = auth_header[len(prefix):].strip()
        if not hmac.compare_digest(supplied, self.ingest_token):
            return False, "INVALID_BEARER_TOKEN"
        return True, "OK"

    def verify_view_token(self, query_token: str, header_token: str) -> bool:
        if not self.view_token:
            return not self.require_view_token
        supplied = (query_token or header_token or "").strip()
        return bool(supplied) and hmac.compare_digest(supplied, self.view_token)

    def _evaluate_heartbeat_health(self, payload: dict[str, Any], now_ts: float | None = None) -> tuple[str, list[str]]:
        status = "OK"
        reasons: list[str] = []

        hb = payload.get("heartbeat") if isinstance(payload.get("heartbeat"), dict) else payload
        if payload.get("mt5_running") is False:
            status = "CRITICAL"
            reasons.append("MT5_PROCESS_DOWN")
        if hb.get("terminal_connected") is False:
            status = "CRITICAL"
            reasons.append("BROKER_DISCONNECTED")
        if str(hb.get("positions_state") or "").upper() == "UNKNOWN" or (hb.get("open_positions") is not None and int(hb.get("open_positions")) < 0):
            status = "CRITICAL"
            reasons.append("POSITIONS_STATE_UNKNOWN")
        if str(hb.get("anchor_state") or "").upper() == "UNRECOVERED_AFTER_GAP":
            status = "CRITICAL"
            reasons.append("DAILY_ANCHOR_UNRECOVERED")
        if now_ts is not None and hb.get("utc_ts") is not None:
            try:
                inner_ts = float(hb["utc_ts"])
                if inner_ts > 0.0:
                    inner_age = now_ts - inner_ts
                    if inner_age > self.stale_after_sec:
                        status = "CRITICAL"
                        reasons.append(f"INNER_HEARTBEAT_STALE={int(inner_age)}s")
                    elif inner_age < -60.0:
                        status = "CRITICAL"
                        reasons.append(f"INNER_HEARTBEAT_FUTURE={int(-inner_age)}s")
            except (TypeError, ValueError):
                status = "CRITICAL"
                reasons.append("INNER_HEARTBEAT_INVALID_TS")
        if bool(hb.get("kill_switch", False)):
            status = "CRITICAL"
            reasons.append("KILL_SWITCH_ACTIVE")
        orphan = int(hb.get("orphan_no_sl") or 0)
        if orphan > 0:
            status = "CRITICAL"
            reasons.append(f"ORPHAN_NO_SL={orphan}")
        daily_dd = float(hb.get("daily_dd_pct") or 0.0)
        if daily_dd >= 2.5:
            status = "CRITICAL"
            reasons.append(f"DAILY_DD={daily_dd:.2f}%")
        regime = str(hb.get("regime") or "NORMAL").upper()
        if regime in ("AMBER_BRAKE", "RED_BRAKE", "MANUAL_HALT", "MANUAL_FLATTEN"):
            if status == "OK":
                status = "WARNING"
            reasons.append(f"REGIME={regime}")
        return status, reasons

    def _emit_alert(self, node: NodeState, event_key: str, text: str, now: float, *, html_text: str = "") -> None:
        if node.last_alert_key == event_key and (now - node.last_alert_ts) < self.alert_cooldown_sec:
            return
        # R2-08: Per-channel cooldown prevents re-spamming Telegram if only secondary webhook failed!
        already_sent_channels = {
            ch for (lbl, ek, ch), ts in self._channel_cooldown.items()
            if lbl == node.account_label and ek == event_key and (now - ts) < self.alert_cooldown_sec
        }
        if self._alert_sender == self._default_alert_sender:
            res = self._default_alert_sender(text, html_text=html_text, skip_channels=already_sent_channels)
        else:
            res = self._alert_sender(html_text or text)
        sent_list = list(res.get("sent") or []) if isinstance(res, dict) else []
        for ch in sent_list:
            self._channel_cooldown[(node.account_label, event_key, str(ch))] = now
        has_errors = bool(res.get("errors")) if isinstance(res, dict) else False
        was_sent = bool(sent_list) if isinstance(res, dict) else True
        is_configured = bool(res.get("configured", True)) if isinstance(res, dict) else True
        if (not has_errors and was_sent) or (not is_configured):
            node.last_alert_key = event_key
            node.last_alert_ts = now
        rec = {
            "utc": datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "account_label": node.account_label,
            "event_key": event_key,
            "text": text,
            "dispatch": res,
        }
        self.alerts_emitted.append(rec)
        if self._store is not None:
            try:
                self._store.save_alert(node, rec, now)
            except Exception:
                pass

    def delete_node(self, label: str) -> bool:
        key = str(label or "").strip()
        if not key:
            return False
        with self._lock:
            existed_mem = key in self._nodes
            self._nodes.pop(key, None)
            existed_db = False
            if self._store is not None:
                try:
                    existed_db = self._store.delete_node(key)
                except Exception as exc:
                    print(f"[WARN] Postgres delete_node error: {exc}", flush=True)
            return bool(existed_mem or existed_db)

    def ingest_heartbeat(self, body: dict[str, Any]) -> dict[str, Any]:
        now = float(self._clock())
        label = str(body.get("account_label") or "NAQEX_HOME_PC").strip()[:64] or "NAQEX_HOME_PC"
        status, reasons = self._evaluate_heartbeat_health(body, now_ts=now)

        with self._lock:
            prev = self._nodes.get(label)
            prev_status = prev.status if prev is not None else "OK"
            if prev is None:
                node = NodeState(account_label=label, first_seen_ts=now, last_seen_ts=now)
                self._nodes[label] = node
            else:
                node = prev
                node.last_seen_ts = now

            node.last_payload = body
            node.status = status
            node.active_reasons = reasons
            hb = body.get("heartbeat") if isinstance(body.get("heartbeat"), dict) else body
            hb_entry = {
                "ts": int(now),
                "status": status,
                "equity": hb.get("equity"),
                "balance": hb.get("balance"),
                "open_positions": hb.get("open_positions"),
                "orphan_no_sl": hb.get("orphan_no_sl"),
                "regime": hb.get("regime"),
            }
            node.history.append(hb_entry)

            if self._store is not None:
                try:
                    self._store.save_node_and_heartbeat(node, hb_entry)
                except Exception as exc:
                    print(f"[WARN] Postgres save_node_and_heartbeat error: {exc}", flush=True)

            if prev_status in ("STALE", "CRITICAL", "WARNING") and status == "OK":
                html_msg, plain_msg = format_alert_message(
                    kind="RECOVERED",
                    label=label,
                    now_ts=now,
                    hb=hb,
                    stale_after_sec=self.stale_after_sec,
                )
                self._emit_alert(node, "RECOVERED", plain_msg, now, html_text=html_msg)
            elif status in ("CRITICAL", "WARNING"):
                stable_keys = [
                    r.split("=", 1)[0] if r.startswith(("INNER_HEARTBEAT_STALE=", "INNER_HEARTBEAT_FUTURE=", "DAILY_DD=")) else r
                    for r in reasons
                ]
                key = f"{status}:{'|'.join(stable_keys)}"
                html_msg, plain_msg = format_alert_message(
                    kind=status,
                    label=label,
                    now_ts=now,
                    hb=hb,
                    reasons=reasons,
                    stale_after_sec=self.stale_after_sec,
                )
                self._emit_alert(node, key, plain_msg, now, html_text=html_msg)

            return {
                "ok": True,
                "order_send_count": ORDER_SEND_COUNT,
                "persistence": "postgres" if self._store is not None else "memory",
                "account_label": label,
                "status": status,
                "reasons": reasons,
                "received_utc": datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

    def check_stale_nodes(self) -> list[dict[str, Any]]:
        now = float(self._clock())
        staled: list[dict[str, Any]] = []
        with self._lock:
            # R2-08: Alert if an expected node NEVER registered (e.g., after DB fallback or fresh boot!)
            for exp_lbl in self.expected_nodes:
                if exp_lbl not in self._nodes and (now - self._started_ts) > self.stale_after_sec:
                    ghost = NodeState(
                        account_label=exp_lbl,
                        first_seen_ts=self._started_ts,
                        last_seen_ts=self._started_ts,
                        status="STALE",
                        active_reasons=["EXPECTED_NODE_MISSING"],
                    )
                    self._nodes[exp_lbl] = ghost
            for node in self._nodes.values():
                age = now - node.last_seen_ts
                if age > self.stale_after_sec:
                    node.status = "STALE"
                    if "EXPECTED_NODE_MISSING" not in node.active_reasons:
                        node.active_reasons = [f"NO_HEARTBEAT_{int(age)}s_GT_{self.stale_after_sec}s"]
                    hb = node.last_payload.get("heartbeat") if isinstance(node.last_payload.get("heartbeat"), dict) else node.last_payload
                    html_msg, plain_msg = format_alert_message(
                        kind="STALE",
                        label=node.account_label,
                        now_ts=now,
                        hb=hb,
                        age_sec=age,
                        stale_after_sec=self.stale_after_sec,
                    )
                    self._emit_alert(node, "STALE_OFFLINE", plain_msg, now, html_text=html_msg)
                    staled.append({"account_label": node.account_label, "age_s": int(age)})
        return staled

    def snapshot(self) -> dict[str, Any]:
        now = float(self._clock())
        pg_rows = None
        if self._store is not None:
            try:
                pg_rows = self._store.heartbeat_row_count()
            except Exception:
                pg_rows = None

        with self._lock:
            nodes_out = []
            for label in sorted(self._nodes.keys()):
                n = self._nodes[label]
                age = max(0, int(now - n.last_seen_ts))
                hb = n.last_payload.get("heartbeat") if isinstance(n.last_payload.get("heartbeat"), dict) else n.last_payload
                nodes_out.append({
                    "account_label": n.account_label,
                    "status": "STALE" if age > self.stale_after_sec else n.status,
                    "age_sec": age,
                    "mt5_running": n.last_payload.get("mt5_running"),
                    "account_login": hb.get("account_login"),
                    "account_server": hb.get("account_server"),
                    "build_version": hb.get("build_version"),
                    "positions_state": hb.get("positions_state"),
                    "anchor_state": hb.get("anchor_state"),
                    "manual_halt_ack": hb.get("manual_halt_ack"),
                    "balance": hb.get("balance"),
                    "equity": hb.get("equity"),
                    "daily_dd_pct": hb.get("daily_dd_pct"),
                    "static_dd_pct": hb.get("static_dd_pct"),
                    "open_positions": hb.get("open_positions"),
                    "total_account_positions": hb.get("total_account_positions"),
                    "pending_orders": hb.get("pending_orders"),
                    "orphan_no_sl": hb.get("orphan_no_sl"),
                    "regime": hb.get("regime"),
                    "kill_switch": hb.get("kill_switch"),
                    "reasons": n.active_reasons,
                    "last_seen_utc": datetime.fromtimestamp(n.last_seen_ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "history_count": len(n.history),
                })
            return {
                "schema": "naqex-heroku-deadman-v2",
                "order_send_count": ORDER_SEND_COUNT,
                "persistence": "postgres" if self._store is not None else "memory",
                "pg_heartbeat_rows": pg_rows,
                "credit_expires_utc": "2028-09-30",
                "utc": datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "stale_after_sec": self.stale_after_sec,
                "nodes": nodes_out,
                "recent_alerts": list(self.alerts_emitted)[-10:],
            }


def render_mobile_html(snap: dict[str, Any]) -> str:
    rows = []
    for n in snap["nodes"]:
        st = str(n["status"])
        cls = "ok" if st == "OK" else ("warn" if st == "WARNING" else "crit")
        age_txt = format_duration_vi(n["age_sec"])
        eq_txt = f"{float(n['equity']):,.2f}" if n["equity"] is not None else "—"
        rows.append(
            f"<tr>"
            f"<td><strong>{html.escape(str(n['account_label']))}</strong></td>"
            f"<td><span class='badge {cls}'>{html.escape(st)}</span></td>"
            f"<td class='num'>{html.escape(age_txt)}</td>"
            f"<td class='num'>{html.escape(eq_txt)}</td>"
            f"<td class='num'>{html.escape(str(n['open_positions'] if n['open_positions'] is not None else '—'))}</td>"
            f"<td class='num'>{html.escape(str(n['orphan_no_sl'] if n['orphan_no_sl'] is not None else '—'))}</td>"
            f"<td>{html.escape(str(n['regime'] or '—'))}</td>"
            f"</tr>"
        )
    table_body = "".join(rows) if rows else "<tr><td colspan='7'>Chưa nhận được nhịp tim nào từ máy chủ.</td></tr>"
    alerts = "".join(
        f"<li><code>{html.escape(a['utc'])}</code> — {html.escape(a['text'])}</li>"
        for a in reversed(snap["recent_alerts"])
    ) or "<li>Chưa có cảnh báo nào.</li>"
    db_info = f"Postgres ({snap['pg_heartbeat_rows']} rows)" if snap.get("persistence") == "postgres" else "Memory"

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="30">
<title>Naqex Dead-Man's-Switch</title>
<style>
body{{margin:0;padding:16px;background:#0b0f17;color:#e6ebf5;font-family:-apple-system,Segoe UI,sans-serif;font-size:14px}}
.wrap{{max-width:860px;margin:0 auto}}
h1{{font-size:17px;margin:0 0 6px}}
.meta{{color:#8b97ad;font-size:12px;margin-bottom:14px}}
table{{width:100%;border-collapse:collapse;background:#121824;border:1px solid #222b3d;margin-bottom:16px}}
th,td{{padding:8px 10px;border-bottom:1px solid #222b3d;text-align:left;font-family:ui-monospace,Consolas,monospace;font-size:12.5px}}
th{{color:#8b97ad;font-size:11px;text-transform:uppercase}}
.num{{text-align:right}}
.badge{{padding:2px 7px;border:1px solid;font-weight:700;font-size:11px}}
.ok{{color:#16c784;border-color:#1e4d3a;background:#0d231b}}
.warn{{color:#f59e0b;border-color:#5c4011;background:#261b08}}
.crit{{color:#ef4444;border-color:#5f1d1d;background:#260d0d}}
ul{{padding-left:18px;font-size:12.5px;line-height:1.6}}
</style>
</head>
<body><div class="wrap">
<h1>Naqex Cloud Dead-Man's-Switch</h1>
<div class="meta">UTC: {html.escape(snap['utc'])} · Lưu trữ: {html.escape(db_info)} · Ngưỡng mất tín hiệu: {html.escape(format_duration_vi(snap['stale_after_sec']))} · OrderSend=0 · Hạn Credit: {html.escape(str(snap.get('credit_expires_utc','—')))}</div>
<table><thead><tr><th>Máy / Tài khoản</th><th>Trạng thái</th><th class="num">Tuổi nhịp</th><th class="num">Equity</th><th class="num">Lệnh mở</th><th class="num">Thiếu SL</th><th>Chế độ</th></tr></thead>
<tbody>{table_body}</tbody></table>
<h2 style="font-size:14px;margin:0 0 8px">Cảnh báo gần nhất</h2>
<ul>{alerts}</ul>
</div></body></html>"""


def make_handler(monitor: DeadmanMonitor):
    class DeadmanHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            raw = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
            self.send_response(int(status))
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            if parsed.path == "/health":
                self._send_json(HTTPStatus.OK, {
                    "ok": True,
                    "service": "naqex-heroku-deadman",
                    "persistence": "postgres" if monitor._store is not None else "memory",
                    "order_send_count": ORDER_SEND_COUNT,
                })
                return
            q_tok = (qs.get("token") or [""])[0]
            h_tok = self.headers.get("X-Naqex-View-Token", "")
            if not monitor.verify_view_token(q_tok, h_tok):
                self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "UNAUTHORIZED_VIEW"})
                return
            snap = monitor.snapshot()
            if parsed.path == "/api/status":
                self._send_json(HTTPStatus.OK, snap)
                return
            if parsed.path in ("/", "/index.html"):
                body = render_mobile_html(snap).encode("utf-8")
                self.send_response(int(HTTPStatus.OK))
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "NOT_FOUND"})

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            length = min(max(0, int(self.headers.get("Content-Length", "0") or 0)), 65_536)
            raw = self.rfile.read(length) if length > 0 else b""
            if parsed.path != "/api/heartbeat":
                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "NOT_FOUND"})
                return
            ok_auth, auth_err = monitor.verify_ingest_token(self.headers.get("Authorization", ""))
            if not ok_auth:
                code = HTTPStatus.SERVICE_UNAVAILABLE if auth_err == "INGEST_TOKEN_NOT_CONFIGURED" else HTTPStatus.UNAUTHORIZED
                self._send_json(code, {"ok": False, "error": auth_err, "order_send_count": ORDER_SEND_COUNT})
                return
            try:
                body = json.loads(raw.decode("utf-8")) if raw else {}
                if not isinstance(body, dict):
                    raise ValueError("JSON body must be an object")
            except Exception as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": f"INVALID_JSON:{exc}"})
                return
            res = monitor.ingest_heartbeat(body)
            self._send_json(HTTPStatus.OK, res)

        def do_DELETE(self) -> None:
            parsed = urlparse(self.path)
            if not parsed.path.startswith("/api/nodes/"):
                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "NOT_FOUND"})
                return
            ok_auth, auth_err = monitor.verify_ingest_token(self.headers.get("Authorization", ""))
            if not ok_auth:
                code = HTTPStatus.SERVICE_UNAVAILABLE if auth_err == "INGEST_TOKEN_NOT_CONFIGURED" else HTTPStatus.UNAUTHORIZED
                self._send_json(code, {"ok": False, "error": auth_err, "order_send_count": ORDER_SEND_COUNT})
                return
            label = unquote(parsed.path[len("/api/nodes/"):]).strip()
            deleted = monitor.delete_node(label)
            self._send_json(
                HTTPStatus.OK if deleted else HTTPStatus.NOT_FOUND,
                {"ok": deleted, "deleted_label": label, "order_send_count": ORDER_SEND_COUNT},
            )

    return DeadmanHandler


def create_server(
    monitor: DeadmanMonitor,
    *,
    host: str = "0.0.0.0",
    port: int = 8000,
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(monitor))


def main() -> int:
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    db_url = os.environ.get("DATABASE_URL", "").strip()
    pg_store: PostgresStore | None = None
    if db_url:
        try:
            pg_store = PostgresStore(db_url)
            print("[OK] Connected to Heroku Postgres Essential-0 durable store.", flush=True)
        except Exception as exc:
            print(f"[WARN] Postgres init failed ({exc}); falling back to in-memory ring buffer.", flush=True)

    req_view = os.environ.get("NAQEX_REQUIRE_VIEW_TOKEN", "true").strip().lower() not in ("0", "false", "no")
    exp_nodes_raw = os.environ.get("EXPECTED_NODES", "").strip()
    expected_nodes = [x.strip() for x in exp_nodes_raw.split(",") if x.strip()] if exp_nodes_raw else []
    monitor = DeadmanMonitor(
        ingest_token=os.environ.get("NAQEX_INGEST_TOKEN", ""),
        view_token=os.environ.get("NAQEX_VIEW_TOKEN", ""),
        require_view_token=req_view,
        stale_after_sec=int(os.environ.get("STALE_AFTER_SEC", str(DEFAULT_STALE_AFTER_SEC))),
        alert_cooldown_sec=int(os.environ.get("ALERT_COOLDOWN_SEC", str(DEFAULT_ALERT_COOLDOWN_SEC))),
        expected_nodes=expected_nodes,
        pg_store=pg_store,
    )
    stop_ev = threading.Event()

    def _watch_loop() -> None:
        interval = max(5, int(os.environ.get("CHECK_INTERVAL_SEC", str(DEFAULT_CHECK_INTERVAL_SEC))))
        while not stop_ev.wait(interval):
            try:
                monitor.check_stale_nodes()
            except Exception:
                pass

    th = threading.Thread(target=_watch_loop, daemon=True)
    th.start()
    srv = create_server(monitor, host=host, port=port)
    print(f"Naqex Heroku Dead-Man's-Switch listening on {host}:{port} (OrderSend=0, store={'postgres' if pg_store else 'memory'})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_ev.set()
        srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
