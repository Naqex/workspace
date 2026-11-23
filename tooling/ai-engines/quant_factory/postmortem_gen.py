"""Blameless Weekly Postmortem Engine (M2.3).

Wires `tca_reconcile.py` + `live_decay_monitor.py` + `ops_monitor.py` to classify
weekly Demo / Live discrepancies objectively into:
  - `Execution TCA Bug`
  - `Alpha Decay`
  - `Regime Shift`
  - `Normal Variance`
and generate a structured Vietnamese/English Markdown blameless postmortem.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Iterable

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.live_decay_monitor import evaluate_live_decay
from quant_factory.ops_monitor import inspect_heartbeat
from quant_factory.report_gen import format_markdown_table
from quant_factory.tca_reconcile import compute_tca_report, load_exec_audit_csv


def classify_discrepancy(
    tca_report: dict,
    decay_report: dict,
    ops_report: dict,
    *,
    vol_ratio: float = 1.0,
    vol_high_thresh: float = 1.60,
    vol_low_thresh: float = 0.50,
) -> dict:
    """Objectively classify discrepancy into Execution TCA Bug, Alpha Decay, Regime Shift, or Normal Variance."""
    tca_v = str(tca_report.get("verdict", "NO_DATA"))
    decay_v = str(decay_report.get("verdict", "NO_LIVE_DATA"))
    ops_s = str(ops_report.get("status", "OK"))
    sprt_state = str((decay_report.get("sprt") or {}).get("state", "INCONCLUSIVE_CONTINUE"))
    vol_shifted = (vol_ratio > vol_high_thresh) or (vol_ratio < vol_low_thresh)

    secondary: list[str] = []
    if tca_v.startswith("RED_") or tca_v == "AMBER_WATCH":
        secondary.extend(tca_report.get("flags", []))
    if ops_s in ("CRITICAL", "WARNING"):
        secondary.extend(ops_report.get("alerts", []))
    if decay_v in ("RED_HALT_ALPHA_DECAY", "AMBER_WATCH_REDUCE_SIZE"):
        secondary.extend(decay_report.get("reasons", []))
    if vol_shifted:
        secondary.append(f"Realized live/dev volatility ratio = {vol_ratio:.2f}x (outside [{vol_low_thresh:.2f}x, {vol_high_thresh:.2f}x])")

    # Priority 1: Execution / Broker / Ops Plumbing failures always take precedence over alpha diagnosis
    if tca_v.startswith("RED_") or ops_s == "CRITICAL" or (tca_v == "AMBER_WATCH" and decay_v not in ("RED_HALT_ALPHA_DECAY",)):
        classification = "Execution TCA Bug"
        severity = "RED" if (tca_v.startswith("RED_") or ops_s == "CRITICAL") else "AMBER"
        actions = [
            "Tạm khóa gửi lệnh live (bật lại `InpDryRunLogOnly = true`) cho đến khi xác minh xong broker/VPS.",
            "Đối chiếu `naqex_exec_audit.csv`: kiểm tra spread spike, retcode reject, latency p90 và vi phạm `swap = 0`.",
            "Kiểm tra `naqex_heartbeat.json`, vị thế orphan không SL và lệch đồng hồ UTC/DST trên MT5 terminal.",
            "KHÔNG chỉnh tham số chiến lược (ATR/SL/trigger) khi nguyên nhân nằm ở tầng khớp lệnh.",
        ]
    # Priority 2: Structural Alpha Decay (CUSUM + SPRT/p05 breach without execution bugs)
    elif decay_v == "RED_HALT_ALPHA_DECAY" and (not vol_shifted or sprt_state == "REJECT_EDGE_DECAYED"):
        classification = "Alpha Decay"
        severity = "RED"
        actions = [
            "Hạ rủi ro hoặc tạm dừng engine bị `RED_HALT_ALPHA_DECAY` theo đúng kill-criteria đã đăng ký trước.",
            "Tách riêng đóng góp từng engine (E1..E7 / S6..S7) để xác định liệu suy giảm là cục bộ 1 engine hay toàn danh mục.",
            "Đưa giả thuyết mới qua `research_council.py` (Proposer -> Critic) trên dữ liệu Development; TUYỆT ĐỐI không tối ưu lại trên tuần vừa lỗ.",
            "Ghi nhận bài học vào `knowledge/topics/alpha-hypothesis-ledger.md`.",
        ]
    # Priority 3: Market Regime Shift (vol compression/expansion or AMBER drawdown/ops brake without structural SPRT rejection)
    elif decay_v in ("AMBER_WATCH_REDUCE_SIZE", "RED_HALT_ALPHA_DECAY") or vol_shifted or ops_s == "WARNING":
        classification = "Regime Shift"
        severity = "AMBER"
        actions = [
            "Giữ nguyên hệ thống phanh tự động (Vol-Brake 20d + Orchestrator AMBER `0.65x` / RED `0.40x`); KHÔNG can thiệp đóng tay giữa lệnh.",
            "Kiểm tra tương quan đuôi (tail correlation) và chế độ biến động (Low-Vol compression vs Crisis High-Vol) bằng `red_team_auditor.py`.",
            "Tiếp tục thu thập mẫu đủ lớn (tối thiểu 20–30 ngày giao dịch) trước khi kết luận Alpha Decay.",
        ]
    else:
        classification = "Normal Variance"
        severity = "GREEN"
        actions = [
            "Giữ nguyên cấu hình hiện tại, không tinh chỉnh tham số theo nhiễu ngắn hạn.",
            "Lưu trữ snapshot báo cáo tuần vào nhật ký vận hành để duy trì chuỗi bằng chứng liên tục.",
        ]

    return {
        "classification": classification,
        "severity": severity,
        "vol_ratio": round(float(vol_ratio), 3),
        "tca_verdict": tca_v,
        "decay_verdict": decay_v,
        "ops_status": ops_s,
        "sprt_state": sprt_state,
        "secondary_signals": secondary,
        "recommended_actions": actions,
    }


def run_weekly_postmortem(
    dev_series: np.ndarray,
    live_series: np.ndarray,
    *,
    tca_events: Iterable[dict] | None = None,
    exec_audit_csv: Path | None = None,
    heartbeat_path: Path | None = None,
    heartbeat_report: dict | None = None,
    now_utc_ts: int | None = None,
    period_label: str = "Weekly Review",
    account_label: str = "NAQEX_MT5_DEMO",
    seed: int = 20261124,
) -> dict:
    """Run full 3-pillar telemetry reconciliation (TCA + Live Decay + Ops Heartbeat) and classify root cause."""
    if tca_events is not None:
        events = list(tca_events)
    elif exec_audit_csv is not None and Path(exec_audit_csv).exists():
        events = load_exec_audit_csv(Path(exec_audit_csv))
    else:
        events = []
    tca_report = compute_tca_report(events)

    decay_report = evaluate_live_decay(dev_series, live_series, seed=seed)

    if heartbeat_report is not None:
        ops_report = heartbeat_report
    elif heartbeat_path is not None:
        ops_report = inspect_heartbeat(Path(heartbeat_path), now_utc_ts=now_utc_ts)
    else:
        ops_report = {"status": "OK", "age_seconds": 0, "alerts": [], "payload": None}

    dev_arr = np.asarray(dev_series, dtype=np.float64)
    dev_arr = dev_arr[np.isfinite(dev_arr)]
    live_arr = np.asarray(live_series, dtype=np.float64)
    live_arr = live_arr[np.isfinite(live_arr)]
    dev_sd = float(np.std(dev_arr, ddof=1)) if len(dev_arr) > 1 else 1e-9
    live_sd = float(np.std(live_arr, ddof=1)) if len(live_arr) >= 5 else dev_sd
    vol_ratio = live_sd / max(dev_sd, 1e-9)

    diagnosis = classify_discrepancy(tca_report, decay_report, ops_report, vol_ratio=vol_ratio)
    return {
        "schema": "naqex-weekly-postmortem-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "period_label": period_label,
        "account_label": account_label,
        "diagnosis": diagnosis,
        "tca_report": tca_report,
        "decay_report": decay_report,
        "ops_report": ops_report,
    }


def render_postmortem_markdown(pm: dict) -> str:
    """Render structured blameless Markdown postmortem from `run_weekly_postmortem` output."""
    diag = pm["diagnosis"]
    tca = pm["tca_report"]
    dec = pm["decay_report"]
    ops = pm["ops_report"]
    cone = dec.get("confidence_cone") or {}
    cusum = dec.get("cusum") or {}
    sprt = dec.get("sprt") or {}

    lines = [
        f"# Blameless Weekly Postmortem — {pm['account_label']} ({pm['period_label']})",
        "",
        f"- **Generated UTC:** `{pm['generated_utc']}`",
        f"- **Root-Cause Classification:** **`{diag['classification']}`** (Severity: **`{diag['severity']}`**)",
        f"- **Realized Vol Ratio (Live / Dev):** `{diag['vol_ratio']:.2f}x`",
        "",
        "## 1. Telemetry Evidence Matrix (3 Pillars)",
        "",
    ]
    headers = ["Pillar", "Status / Verdict", "Key Measurements"]
    rows = [
        [
            "Execution TCA (`tca_reconcile`)",
            tca.get("verdict", "N/A"),
            (
                f"fills={tca['counts']['fills']}, rejects={tca['counts']['rejects']} ({tca['reject_rate_pct']}%), "
                f"slip_R0_mean={tca['adverse_slippage_pct_of_r0']['mean']}%, "
                f"lat_p90={tca['latency_ms']['p90']}ms, swap_viol={tca['swap_violations']}"
            ),
        ],
        [
            "Live Decay (`CUSUM + SPRT + Cone`)",
            dec.get("verdict", "N/A"),
            (
                f"n_live={dec.get('n_live', 0)}, cum={dec.get('live_cum', 0.0)}, "
                f"CUSUM={cusum.get('current_negative_sigma', 0.0)}σ (thr=-{cusum.get('threshold_sigma', 4.5)}σ), "
                f"SPRT={sprt.get('state', 'N/A')} (LLR={sprt.get('llr', 0.0)}), "
                f"cone_pct={cone.get('observed_percentile', 'N/A')}th"
            ),
        ],
        [
            "Ops Heartbeat (`ops_monitor`)",
            ops.get("status", "N/A"),
            f"age={ops.get('age_seconds')}s, alerts={len(ops.get('alerts', []))}",
        ],
    ]
    lines.append(format_markdown_table(headers, rows))

    lines += ["", "## 2. Triggered Signals & Findings", ""]
    if diag["secondary_signals"]:
        for sig in diag["secondary_signals"]:
            lines.append(f"- {sig}")
    else:
        lines.append("- Không có cờ cảnh báo bất thường nào kích hoạt trong tuần.")

    lines += ["", "## 3. Blameless Action Checklist (Zero Mid-Trade Discretion)", ""]
    for i, act in enumerate(diag["recommended_actions"], start=1):
        lines.append(f"{i}. {act}")
    lines.append("")
    return "\n".join(lines)


def generate_weekly_postmortem(
    dev_series: np.ndarray,
    live_series: np.ndarray,
    *,
    output_md: Path | None = None,
    **kwargs,
) -> tuple[dict, str]:
    """Run telemetry reconciliation, render Markdown postmortem, and optionally persist to disk."""
    pm = run_weekly_postmortem(dev_series, live_series, **kwargs)
    md = render_postmortem_markdown(pm)
    if output_md is not None:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(md, encoding="utf-8", newline="\n")
    return pm, md
