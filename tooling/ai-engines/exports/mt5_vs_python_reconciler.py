"""MT5 Real-Tick Strategy Tester Report Parser & Python Frozen-Engine Reconciler.

Parses MetaTrader 5 build 6230 Strategy Tester HTML reports (UTF-16LE / UTF-8) and
Tester/Agent logs, verifies `swap = 0`, SL attachment, commission parity, and latency
degradation (`50ms -> 150ms -> 250ms`), and reconciles Development-window (`< 2025-01-01`)
runs against frozen Python tapes from `quant_factory.data_store.build_or_load_frozen_tapes()`.

STRICT HOLDOUT RULE: NEVER loads or inspects Holdout `>= 2025-01-01` Python tapes.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from typing import Any

EXPORTS_DIR = Path(__file__).resolve().parent
AI_ENGINES_DIR = EXPORTS_DIR.parent
REPO_ROOT = AI_ENGINES_DIR.parents[1]

for p in (AI_ENGINES_DIR, EXPORTS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


class _TableExtractor(HTMLParser):
    """Lightweight stdlib HTML table parser for MT5 Strategy Tester `.htm` reports."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._in_tr = False
        self._in_cell = False
        self._cur_row: list[str] = []
        self._cur_cell: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t == "tr":
            self._in_tr = True
            self._cur_row = []
        elif t in ("td", "th") and self._in_tr:
            self._in_cell = True
            self._cur_cell = []

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in ("td", "th") and self._in_cell:
            txt = " ".join("".join(self._cur_cell).split())
            self._cur_row.append(txt)
            self._in_cell = False
            self._cur_cell = []
        elif t == "tr" and self._in_tr:
            if any(c for c in self._cur_row):
                self.rows.append(self._cur_row)
            self._in_tr = False
            self._cur_row = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cur_cell.append(data)


def decode_mt5_text(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    if b"\x00" in raw[:200]:
        return raw.decode("utf-16-le", errors="replace")
    return raw.decode("utf-8", errors="replace")


def _parse_float(raw: str | None) -> float | None:
    if not raw:
        return None
    cleaned = raw.replace("\xa0", "").replace(" ", "").replace(",", "")
    m = re.search(r"[-+]?\d+(?:\.\d+)?", cleaned)
    return float(m.group(0)) if m else None


def _parse_count_and_pct(raw: str | None) -> tuple[int | None, float | None]:
    if not raw:
        return None, None
    m_cnt = re.search(r"(\d+)", raw.replace(" ", ""))
    m_pct = re.search(r"\(([-+]?\d+(?:\.\d+)?)%\)", raw.replace(" ", ""))
    return (int(m_cnt.group(1)) if m_cnt else None), (float(m_pct.group(1)) if m_pct else None)


def _parse_abs_and_pct(raw: str | None) -> tuple[float | None, float | None]:
    if not raw:
        return None, None
    s = raw.replace("\xa0", " ").strip()
    m = re.search(r"([-+]?[\d\s]+(?:\.\d+)?)\s*\(([-+]?\d+(?:\.\d+)?)%\)", s)
    if m:
        return _parse_float(m.group(1)), float(m.group(2))
    return _parse_float(s), None


def parse_mt5_html_report(html_path: Path) -> dict[str, Any]:
    """Parse an MT5 Strategy Tester `.htm` report into structured summary KPIs + deals list."""
    if not html_path.exists():
        return {"ok": False, "error": f"Report missing: {html_path}"}

    text = decode_mt5_text(html_path)
    parser = _TableExtractor()
    parser.feed(text)

    kv: dict[str, str] = {}
    deals: list[dict[str, Any]] = []
    in_deals = False
    deals_header_idx: dict[str, int] = {}

    for row in parser.rows:
        # Detect Deals table header
        lower_cells = [c.lower() for c in row]
        if "deal" in lower_cells and "direction" in lower_cells and "profit" in lower_cells:
            in_deals = True
            deals_header_idx = {name: i for i, name in enumerate(lower_cells)}
            continue
        if in_deals:
            if len(row) >= 10 and re.match(r"^\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2}", row[0]):
                def _col(name: str, default_idx: int) -> str:
                    idx = deals_header_idx.get(name, default_idx)
                    return row[idx] if idx < len(row) else ""

                dtype = _col("type", 3).lower()
                if dtype in ("buy", "sell"):
                    deals.append(
                        {
                            "time": _col("time", 0),
                            "day": _col("time", 0)[:10].replace(".", "-"),
                            "deal_id": _col("deal", 1),
                            "symbol": _col("symbol", 2),
                            "type": dtype,
                            "direction": _col("direction", 4).lower(),
                            "volume": _parse_float(_col("volume", 5)) or 0.0,
                            "price": _parse_float(_col("price", 6)) or 0.0,
                            "order": _col("order", 7),
                            "commission": _parse_float(_col("commission", 8)) or 0.0,
                            "swap": _parse_float(_col("swap", 9)) or 0.0,
                            "profit": _parse_float(_col("profit", 10)) or 0.0,
                            "balance": _parse_float(_col("balance", 11)) or 0.0,
                            "comment": _col("comment", 12),
                        }
                    )
            continue

        # Summary key-value pairs (MT5 puts 1 to 3 key:value pairs per <tr>)
        for i in range(0, len(row) - 1):
            label = row[i].strip()
            if label.endswith(":"):
                val = row[i + 1].strip()
                kv[label[:-1].strip().lower()] = val

    eq_dd_abs, eq_dd_pct = _parse_abs_and_pct(kv.get("equity drawdown maximal"))
    bal_dd_abs, bal_dd_pct = _parse_abs_and_pct(kv.get("balance drawdown maximal"))
    win_cnt, win_pct = _parse_count_and_pct(kv.get("profit trades (% of total)"))
    loss_cnt, loss_pct = _parse_count_and_pct(kv.get("loss trades (% of total)"))

    out_deals = [d for d in deals if d["direction"] == "out"]
    in_deals = [d for d in deals if d["direction"] == "in"]
    swap_total = round(sum(d["swap"] for d in deals), 4)
    comm_total = round(sum(d["commission"] for d in deals), 4)
    sl_exits = sum(1 for d in out_deals if "sl " in d["comment"].lower() or d["comment"].lower().startswith("[sl"))
    entry_days = sorted({d["day"] for d in in_deals})

    return {
        "ok": True,
        "report_file": str(html_path),
        "expert": kv.get("expert"),
        "symbol": kv.get("symbol"),
        "period": kv.get("period"),
        "history_quality_pct": _parse_float(kv.get("history quality")),
        "bars": int(_parse_float(kv.get("bars")) or 0),
        "ticks": int(_parse_float(kv.get("ticks")) or 0),
        "initial_deposit": _parse_float(kv.get("initial deposit")),
        "total_net_profit": _parse_float(kv.get("total net profit")),
        "gross_profit": _parse_float(kv.get("gross profit")),
        "gross_loss": _parse_float(kv.get("gross loss")),
        "profit_factor": _parse_float(kv.get("profit factor")),
        "expected_payoff": _parse_float(kv.get("expected payoff")),
        "recovery_factor": _parse_float(kv.get("recovery factor")),
        "sharpe_ratio": _parse_float(kv.get("sharpe ratio")),
        "balance_dd_abs": bal_dd_abs,
        "balance_dd_pct": bal_dd_pct,
        "equity_dd_abs": eq_dd_abs,
        "equity_dd_pct": eq_dd_pct,
        "total_trades": int(_parse_float(kv.get("total trades")) or 0),
        "total_deals": int(_parse_float(kv.get("total deals")) or 0),
        "profit_trades": win_cnt,
        "win_rate_pct": win_pct,
        "loss_trades": loss_cnt,
        "loss_rate_pct": loss_pct,
        "deals_parsed": len(deals),
        "in_deals_count": len(in_deals),
        "out_deals_count": len(out_deals),
        "sl_exits_count": sl_exits,
        "swap_total_usd": swap_total,
        "swap_zero_ok": abs(swap_total) < 1e-6,
        "commission_total_usd": comm_total,
        "entry_days": entry_days,
        "deals": deals,
    }


def parse_tester_logs(log_paths: list[Path]) -> dict[str, Any]:
    """Scan MT5 Tester & Agent logs for errors, retcodes, INIT_FAILED, or spread/news blocks."""
    issues: list[str] = []
    propguard_errs: list[str] = []
    dryrun_lines = 0
    order_send_fails = 0
    for lp in log_paths:
        if not lp.exists():
            continue
        text = decode_mt5_text(lp)
        for line in text.splitlines():
            low = line.lower()
            if "[dryrun-guard]" in low or "[dryrun]" in low:
                dryrun_lines += 1
            if "[propguard-err]" in low:
                propguard_errs.append(line.strip())
                order_send_fails += 1
            if any(
                tok in low
                for tok in (
                    "init_failed",
                    "initialization failed",
                    "retcode=10030",
                    "unsupported filling",
                    "invalid stops",
                    "not enough money",
                    "no history data",
                    "tester not started",
                    "array out of range",
                )
            ):
                issues.append(f"{lp.name}: {line.strip()}")
    return {
        "logs_scanned": len([p for p in log_paths if p.exists()]),
        "dryrun_signal_lines": dryrun_lines,
        "order_send_fails": order_send_fails,
        "propguard_errs": propguard_errs[:20],
        "issues": issues[:30],
        "clean": len(issues) == 0 and order_send_fails == 0,
    }


def compute_python_dev_window_metrics(
    engine_id: str,
    window_start_iso: str,
    window_end_iso: str,
    *,
    initial_deposit: float = 10000.0,
    risk_pct_map: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compute matching-window KPIs from frozen Dev Python tapes STRICTLY for `< 2025-01-01`."""
    if window_end_iso >= "2025-01-01":
        return {
            "available": False,
            "reason": "HOLDOUT_SEALED_SKIPPED: Python reconciliation strictly restricted to Dev < 2025-01-01",
        }

    from quant_factory.data_store import build_or_load_frozen_tapes, load_registry  # noqa: E402

    reg = load_registry()
    risk_lookup = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    if risk_pct_map:
        risk_lookup.update(risk_pct_map)

    bundle = build_or_load_frozen_tapes()
    tapes = bundle["tapes"]
    if engine_id not in tapes:
        return {"available": False, "reason": f"Engine {engine_id} not in frozen tapes"}

    risk_frac = risk_lookup.get(engine_id, 0.005)
    day_map = tapes[engine_id]
    matched_days = sorted(d for d in day_map if window_start_iso <= d <= window_end_iso)

    eq = float(initial_deposit)
    peak = eq
    max_dd_pct = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    wins = 0
    for dk in matched_days:
        row, _stamps, _marks = day_map[dk]
        net_r = float(row["net_R"])
        pnl_usd = eq * risk_frac * net_r
        eq += pnl_usd
        if pnl_usd >= 0:
            gross_profit += pnl_usd
            wins += 1
        else:
            gross_loss += pnl_usd
        if eq > peak:
            peak = eq
        dd = ((peak - eq) / peak) * 100.0 if peak > 0 else 0.0
        if dd > max_dd_pct:
            max_dd_pct = dd

    n = len(matched_days)
    net_usd = eq - initial_deposit
    pf = (gross_profit / abs(gross_loss)) if gross_loss < 0 else (99.0 if gross_profit > 0 else 0.0)
    return {
        "available": True,
        "window": f"{window_start_iso}..{window_end_iso}",
        "trades": n,
        "net_profit_usd": round(net_usd, 2),
        "gross_profit_usd": round(gross_profit, 2),
        "gross_loss_usd": round(gross_loss, 2),
        "profit_factor": round(pf, 2),
        "win_rate_pct": round((wins / n) * 100.0, 2) if n else 0.0,
        "max_dd_pct": round(max_dd_pct, 2),
        "entry_days": matched_days,
    }


def reconcile_engine_runs(
    engine_id: str,
    runs_by_latency: dict[int, dict[str, Any]],
    *,
    window_start_iso: str,
    window_end_iso: str,
    py_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build multi-latency reconciliation + diagnostic verdict for a single EA."""
    latencies = sorted(runs_by_latency.keys())
    primary_lat = 50 if 50 in runs_by_latency else (latencies[0] if latencies else None)
    primary = runs_by_latency.get(primary_lat) if primary_lat is not None else None

    if py_metrics is None:
        py_metrics = compute_python_dev_window_metrics(engine_id, window_start_iso, window_end_iso)

    diagnostics: list[str] = []
    latency_curve: dict[str, Any] = {}
    for lat in latencies:
        r = runs_by_latency[lat]
        rep = r.get("report", {})
        log = r.get("logs", {})
        latency_curve[f"{lat}ms"] = {
            "ok": bool(rep.get("ok")),
            "trades": rep.get("total_trades"),
            "net_profit": rep.get("total_net_profit"),
            "profit_factor": rep.get("profit_factor"),
            "equity_dd_pct": rep.get("equity_dd_pct"),
            "win_rate_pct": rep.get("win_rate_pct"),
            "swap_total_usd": rep.get("swap_total_usd"),
            "swap_zero_ok": rep.get("swap_zero_ok"),
            "commission_total_usd": rep.get("commission_total_usd"),
            "history_quality_pct": rep.get("history_quality_pct"),
            "ticks": rep.get("ticks"),
            "log_clean": log.get("clean"),
            "log_issues_count": len(log.get("issues", [])),
        }
        if not rep.get("ok"):
            diagnostics.append(f"{lat}ms: report parse failed ({rep.get('error')})")
        elif (rep.get("total_trades") or 0) == 0:
            diagnostics.append(f"{lat}ms: ZERO_TRADES (check symbol availability, spread cap, or window)")
        if rep.get("ok") and not rep.get("swap_zero_ok", True):
            diagnostics.append(f"{lat}ms: SWAP_VIOLATION ({rep.get('swap_total_usd')} USD != 0)")
        if log and not log.get("clean", True):
            diagnostics.append(f"{lat}ms: LOG_ISSUES ({len(log.get('issues', []))})")

    overlap_stats: dict[str, Any] = {}
    if primary and primary.get("report", {}).get("ok") and py_metrics.get("available"):
        mt5_days = set(primary["report"].get("entry_days", []))
        py_days = set(py_metrics.get("entry_days", []))
        union = mt5_days | py_days
        inter = mt5_days & py_days
        overlap_stats = {
            "mt5_days": len(mt5_days),
            "py_days": len(py_days),
            "common_days": len(inter),
            "jaccard_pct": round((len(inter) / len(union)) * 100.0, 1) if union else 100.0,
            "mt5_only_days": len(mt5_days - py_days),
            "py_only_days": len(py_days - mt5_days),
        }

    net_50 = latency_curve.get("50ms", {}).get("net_profit")
    net_250 = latency_curve.get("250ms", {}).get("net_profit")
    latency_drag = round(net_250 - net_50, 2) if (net_50 is not None and net_250 is not None) else None

    return {
        "engine_id": engine_id,
        "window": f"{window_start_iso}..{window_end_iso}",
        "latency_curve": latency_curve,
        "latency_drag_50_to_250ms_usd": latency_drag,
        "python_dev_reference": {k: v for k, v in py_metrics.items() if k != "entry_days"},
        "day_overlap": overlap_stats,
        "diagnostics": diagnostics,
        "verdict": "PASS" if len(diagnostics) == 0 else "NEEDS_REVIEW",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Reconcile MT5 Real-Tick Strategy Tester reports against Python frozen engines.")
    ap.add_argument("--results-dir", type=Path, default=REPO_ROOT / ".runtime/mt5-realtick-results")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    summary_path = args.results_dir / "realtick_matrix_summary.json"
    if not summary_path.exists():
        print(f"No real-tick summary found at {summary_path}", file=sys.stderr)
        return 1
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        for eid, item in data.get("reconciliation", {}).items():
            c50 = item.get("latency_curve", {}).get("50ms", {})
            py = item.get("python_dev_reference", {})
            print(
                f"[{item['verdict']:12s}] {eid:18s} | MT5_50ms: tr={c50.get('trades')} net={c50.get('net_profit')} "
                f"PF={c50.get('profit_factor')} DD={c50.get('equity_dd_pct')}% swap={c50.get('swap_total_usd')} | "
                f"Py: tr={py.get('trades')} net={py.get('net_profit_usd')} | diag={item['diagnostics']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
