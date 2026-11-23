"""Automated Sequential MT5 Real-Tick Strategy Tester Runner (`Model=4`) for FTMO-Demo (`1515343166`).

Launches the authenticated FTMO-Demo portable terminal (`terminal64.exe /portable /config:<ini>`)
sequentially for all 8 white-box EAs across a multi-latency execution sweep (`50ms / 150ms / 250ms`)
using `Model=4` ("Every tick based on real ticks").

SAFETY & FAIL-CLOSED INVARIANTS:
  - NEVER touches `C:\\Program Files\\MetaTrader 5` (Exness Real) — raises immediately if passed.
  - NEVER embeds passwords in `.ini` files — reuses authenticated FTMO-Demo session (`1515343166`).
  - Verifies `FTMO-LIVE-SPECS-ALL-SYMBOLS-20261124.json` confirms `server == "FTMO-Demo"`,
    `login == 1515343166`, and `trade_mode == "ACCOUNT_TRADE_MODE_DEMO"`.
  - `.mq5` source files remain strictly `InpDryRunLogOnly = true`; Strategy Tester `.set` files
    enable simulated trades ONLY inside MT5's offline/historical Strategy Tester sandbox.
  - Stores all HTML reports, tester logs & JSON summaries in gitignored `.runtime/mt5-realtick-results/`.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any

EXPORTS_DIR = Path(__file__).resolve().parent
AI_ENGINES_DIR = EXPORTS_DIR.parent
REPO_ROOT = AI_ENGINES_DIR.parents[1]

for p in (AI_ENGINES_DIR, EXPORTS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import mt5_vs_python_reconciler as recon  # noqa: E402
import verify_deployment_kit as kit  # noqa: E402

DEFAULT_PORTABLE_ROOT = REPO_ROOT / ".runtime/ftmo-demo-portable-1515343166"
DEFAULT_EX5_DIR = REPO_ROOT / ".runtime/mt5-compiled-ex5"
DEFAULT_RESULTS_DIR = REPO_ROOT / ".runtime/mt5-realtick-results"
DEFAULT_SPECS_PATH = REPO_ROOT / "planning/research/FTMO-LIVE-SPECS-ALL-SYMBOLS-20261124.json"
FORBIDDEN_PATH_TOKENS = ("program files\\metatrader 5", "d0e8209f77c8cf37ad8bf550e51ff075")

# All 8 white-box EAs mapped to exact FTMO-Demo symbol and chart timeframe
ENGINE_TEST_PLAN: list[dict[str, Any]] = [
    {"engine_id": "E1_USDJPY_TOKYO", "stem": "Naqex_WB_TOKYO_BOX_USDJPY", "symbol": "USDJPY", "period": "M15"},
    {"engine_id": "E2_USDJPY_EXP80", "stem": "Naqex_WB_EXP080_USDJPY", "symbol": "USDJPY", "period": "M15"},
    {"engine_id": "E3_GBPUSD_VH", "stem": "Naqex_WB_EXP080_VOLHIGH_GBPUSD", "symbol": "GBPUSD", "period": "M15"},
    {"engine_id": "E4_US100_SESS40", "stem": "Naqex_WB_SESS_CONT_BRK40_US100", "symbol": "US100.cash", "period": "M5"},
    {"engine_id": "E5_US100_RS1130", "stem": "Naqex_WB_IDX_RS_US100_LEAD_1130", "symbol": "US100.cash", "period": "M5"},
    {"engine_id": "E6_EURJPY_VOLCOMP", "stem": "Naqex_WB_VOLCOMP_EXP75_EURJPY", "symbol": "EURJPY", "period": "M15"},
    {"engine_id": "E7_USDJPY_NY10ET", "stem": "Naqex_WB_NY_RISK_FLOW_10ET_USDJPY", "symbol": "USDJPY", "period": "M5"},
    {"engine_id": "S6_FX_USD_BSK", "stem": "Naqex_WB_FX_USD_BASKET_12U_Z35", "symbol": "EURUSD", "period": "M15"},
]


def assert_safe_portable_root(portable_root: Path) -> None:
    norm = str(portable_root.resolve()).lower()
    for tok in FORBIDDEN_PATH_TOKENS:
        if tok in norm:
            raise ValueError(f"SAFETY ABORT: Refusing to run Strategy Tester on forbidden path: {portable_root}")


def verify_ftmo_demo_specs(specs_path: Path = DEFAULT_SPECS_PATH) -> dict[str, Any]:
    if not specs_path.exists():
        raise FileNotFoundError(f"Missing FTMO-Demo specs verification artifact: {specs_path}")
    data = json.loads(specs_path.read_text(encoding="utf-8"))
    acc = data.get("account", {})
    if acc.get("trade_mode") != "ACCOUNT_TRADE_MODE_DEMO":
        raise RuntimeError(f"SAFETY ABORT: Specs account is not DEMO: {acc}")
    if acc.get("server") != "FTMO-Demo":
        raise RuntimeError(f"SAFETY ABORT: Specs server != FTMO-Demo: {acc.get('server')}")
    if int(acc.get("login", 0)) != 1515343166:
        raise RuntimeError(f"SAFETY ABORT: Specs login != 1515343166: {acc.get('login')}")
    return data


def sync_ex5_and_files_to_portable(
    *,
    portable_root: Path = DEFAULT_PORTABLE_ROOT,
    ex5_dir: Path = DEFAULT_EX5_DIR,
    exports_dir: Path = EXPORTS_DIR,
) -> None:
    assert_safe_portable_root(portable_root)
    exp_dst = portable_root / "MQL5/Experts/Naqex"
    files_dst = portable_root / "MQL5/Files"
    tester_dst = portable_root / "MQL5/Profiles/Tester"
    for d in (exp_dst, files_dst, tester_dst):
        d.mkdir(parents=True, exist_ok=True)
    for ex5 in sorted(ex5_dir.glob("*.ex5")):
        shutil.copy2(ex5, exp_dst / ex5.name)
    news_src = exports_dir / "Files/naqex_red_news_utc.csv"
    if news_src.exists():
        shutil.copy2(news_src, files_dst / news_src.name)


def build_tester_set_file(
    *,
    stem: str,
    preset_profile: str = "FTMO_FreeTrial_Demo",
    tester_utc_offset_h: int = 2,
    out_path: Path,
) -> Path:
    """Create Strategy Tester `.set` enabling simulated trades & isolated from live GlobalVariables."""
    src_set = EXPORTS_DIR / "deployment_kit/presets" / preset_profile / f"{stem}.set"
    kv = kit.parse_set_file(src_set)
    # Inside Strategy Tester, enable simulated execution & isolate from single-chart orchestrator GV
    kv["InpDryRunLogOnly"] = "false"
    kv["InpGuardDryRunLogOnly"] = "false"
    kv["InpGuardUseOrchestrator"] = "false"
    kv["InpGuardTesterUtcOffsetH"] = str(int(tester_utc_offset_h))
    lines = [
        f"; Auto-generated Strategy Tester preset for {stem} (from {preset_profile})",
        "; Simulation ONLY inside MT5 Strategy Tester; .mq5 defaults remain InpDryRunLogOnly=true",
    ]
    for k, v in kv.items():
        lines.append(f"{k}={v}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return out_path


def render_tester_ini(
    *,
    expert_rel: str,
    set_filename: str,
    symbol: str,
    period: str,
    from_date: str,
    to_date: str,
    report_stem: str,
    execution_mode_ms: int = 50,
    model: int = 4,
    deposit: int = 10000,
    leverage: int = 30,
) -> str:
    """Render clean MT5 Strategy Tester `.ini` (NO Login/Password — reuses saved authenticated FTMO-Demo session!)."""
    return (
        "[Common]\r\n"
        "ProxyEnable=0\r\n"
        "NewsEnable=0\r\n"
        "KeepPrivate=0\r\n"
        "\r\n"
        "[Tester]\r\n"
        f"Expert={expert_rel}\r\n"
        f"ExpertParameters={set_filename}\r\n"
        f"Symbol={symbol}\r\n"
        f"Period={period}\r\n"
        f"Model={int(model)}\r\n"
        f"ExecutionMode={int(execution_mode_ms)}\r\n"
        "Optimization=0\r\n"
        f"FromDate={from_date}\r\n"
        f"ToDate={to_date}\r\n"
        "ForwardMode=0\r\n"
        f"Deposit={int(deposit)}\r\n"
        "Currency=USD\r\n"
        "ProfitInPips=0\r\n"
        f"Leverage=1:{int(leverage)}\r\n"
        f"Report={report_stem}\r\n"
        "ReplaceReport=1\r\n"
        "ShutdownTerminal=1\r\n"
        "Visual=0\r\n"
        "UseLocal=1\r\n"
        "UseRemote=0\r\n"
        "UseCloud=0\r\n"
    )


def _clear_old_tester_logs(portable_root: Path) -> None:
    for p in list((portable_root / "Tester/logs").glob("*.log")):
        try:
            p.unlink()
        except OSError:
            pass
    for agent_dir in (portable_root / "Tester").glob("Agent-*"):
        for p in (agent_dir / "logs").glob("*.log"):
            try:
                p.unlink()
            except OSError:
                pass


def run_single_tester_job(
    *,
    portable_root: Path,
    engine_spec: dict[str, Any],
    latency_ms: int,
    from_date: str,
    to_date: str,
    results_dir: Path,
    model: int = 4,
    deposit: int = 10000,
    leverage: int = 100,
    tester_utc_offset_h: int = 2,
    timeout_sec: int = 240,
) -> dict[str, Any]:
    """Execute one MT5 Real-Tick Strategy Tester run and archive its HTML report + logs."""
    assert_safe_portable_root(portable_root)
    terminal_exe = portable_root / "terminal64.exe"
    if not terminal_exe.exists():
        raise FileNotFoundError(f"FTMO portable terminal64.exe missing: {terminal_exe}")

    eid = engine_spec["engine_id"]
    stem = engine_spec["stem"]
    run_tag = f"{eid}_{latency_ms}ms"
    run_dir = results_dir / run_tag
    run_dir.mkdir(parents=True, exist_ok=True)

    set_name = f"naqex_rt_{eid}.set"
    build_tester_set_file(
        stem=stem,
        tester_utc_offset_h=tester_utc_offset_h,
        out_path=portable_root / "MQL5/Profiles/Tester" / set_name,
    )

    report_stem = f"naqex_rt_{run_tag}"
    for stale in (portable_root / f"{report_stem}.htm", portable_root / f"{report_stem}.html"):
        if stale.exists():
            stale.unlink()

    ini_path = run_dir / "tester.ini"
    ini_text = render_tester_ini(
        expert_rel=f"Naqex\\{stem}",
        set_filename=set_name,
        symbol=engine_spec["symbol"],
        period=engine_spec["period"],
        from_date=from_date,
        to_date=to_date,
        report_stem=report_stem,
        execution_mode_ms=latency_ms,
        model=model,
        deposit=deposit,
        leverage=leverage,
    )
    ini_path.write_text(ini_text, encoding="ascii")

    _clear_old_tester_logs(portable_root)

    t0 = time.perf_counter()
    timed_out = False
    try:
        proc = subprocess.run(
            [str(terminal_exe), "/portable", f"/config:{ini_path}"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        rc = int(proc.returncode)
    except subprocess.TimeoutExpired:
        timed_out = True
        rc = -999
        # Cleanly stop only processes inside this exact portable root
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-Process terminal64,metatester64 -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -like '{portable_root}*' }} | Stop-Process -Force -ErrorAction SilentlyContinue",
            ],
            capture_output=True,
            check=False,
        )
    elapsed = round(time.perf_counter() - t0, 2)

    # Archive HTML report and tester/agent logs
    archived_report: Path | None = None
    for cand in (portable_root / f"{report_stem}.htm", portable_root / f"{report_stem}.html"):
        if cand.exists():
            dst = run_dir / cand.name
            shutil.copy2(cand, dst)
            archived_report = dst
            try:
                cand.unlink()
            except OSError:
                pass
            break
    # Remove generated PNG charts in portable root to keep runtime clean
    for png in portable_root.glob(f"{report_stem}*.png"):
        try:
            png.unlink()
        except OSError:
            pass

    archived_logs: list[Path] = []
    for lp in sorted((portable_root / "Tester/logs").glob("*.log")):
        dst = run_dir / f"tester_{lp.name}"
        shutil.copy2(lp, dst)
        archived_logs.append(dst)
    for agent_dir in sorted((portable_root / "Tester").glob("Agent-*")):
        for lp in sorted((agent_dir / "logs").glob("*.log")):
            dst = run_dir / f"{agent_dir.name}_{lp.name}"
            shutil.copy2(lp, dst)
            archived_logs.append(dst)

    parsed_report = recon.parse_mt5_html_report(archived_report) if archived_report else {"ok": False, "error": "No HTML report emitted"}
    parsed_logs = recon.parse_tester_logs(archived_logs)

    result = {
        "engine_id": eid,
        "stem": stem,
        "symbol": engine_spec["symbol"],
        "period": engine_spec["period"],
        "latency_ms": latency_ms,
        "model": model,
        "from_date": from_date,
        "to_date": to_date,
        "exit_code": rc,
        "timed_out": timed_out,
        "elapsed_sec": elapsed,
        "report_path": str(archived_report) if archived_report else None,
        "report": {k: v for k, v in parsed_report.items() if k != "deals"},
        "deals_count": len(parsed_report.get("deals", [])),
        "logs": parsed_logs,
    }
    (run_dir / "parsed_result.json").write_text(
        json.dumps({**result, "deals": parsed_report.get("deals", [])}, indent=2, ensure_ascii=False),
        encoding="utf-8",
        newline="\n",
    )
    return result


def run_suite(
    *,
    portable_root: Path = DEFAULT_PORTABLE_ROOT,
    specs_path: Path = DEFAULT_SPECS_PATH,
    results_dir: Path = DEFAULT_RESULTS_DIR,
    from_date: str = "2024.09.01",
    to_date: str = "2024.12.31",
    latencies: list[int] | None = None,
    engines: list[str] | None = None,
    model: int = 4,
    tester_utc_offset_h: int = 2,
    timeout_sec: int = 240,
) -> dict[str, Any]:
    """Run full sequential Real-Tick Strategy Tester suite & Python reconciliation."""
    specs = verify_ftmo_demo_specs(specs_path)
    leverage = int(specs["account"].get("leverage", 100))
    sync_ex5_and_files_to_portable(portable_root=portable_root)
    results_dir.mkdir(parents=True, exist_ok=True)

    lat_list = latencies or [50, 150, 250]
    plan = [e for e in ENGINE_TEST_PLAN if not engines or e["engine_id"] in engines]

    win_start_iso = from_date.replace(".", "-")
    win_end_iso = to_date.replace(".", "-")

    runs_by_engine: dict[str, dict[int, dict[str, Any]]] = {}
    for eng in plan:
        eid = eng["engine_id"]
        runs_by_engine[eid] = {}
        for lat in lat_list:
            print(f"[REALTICK] Running {eid} ({eng['symbol']} {eng['period']}) @ {lat}ms | {from_date}..{to_date} (Model={model})...")
            sys.stdout.flush()
            res = run_single_tester_job(
                portable_root=portable_root,
                engine_spec=eng,
                latency_ms=lat,
                from_date=from_date,
                to_date=to_date,
                results_dir=results_dir,
                model=model,
                leverage=leverage,
                tester_utc_offset_h=tester_utc_offset_h,
                timeout_sec=timeout_sec,
            )
            runs_by_engine[eid][lat] = res
            rep = res["report"]
            print(
                f"   -> rc={res['exit_code']} ({res['elapsed_sec']}s) ok={rep.get('ok')} "
                f"trades={rep.get('total_trades')} net={rep.get('total_net_profit')} "
                f"PF={rep.get('profit_factor')} DD={rep.get('equity_dd_pct')}% "
                f"swap={rep.get('swap_total_usd')} log_clean={res['logs'].get('clean')}"
            )
            sys.stdout.flush()

    reconciliation: dict[str, Any] = {}
    for eid, lat_map in runs_by_engine.items():
        reconciliation[eid] = recon.reconcile_engine_runs(
            eid,
            lat_map,
            window_start_iso=win_start_iso,
            window_end_iso=win_end_iso,
        )

    summary = {
        "schema": "naqex-mt5-realtick-matrix-v1",
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "account": specs["account"],
        "model": model,
        "window": f"{win_start_iso}..{win_end_iso}",
        "latencies_ms": lat_list,
        "tester_utc_offset_h": tester_utc_offset_h,
        "engines_run": len(plan),
        "reconciliation": reconciliation,
    }
    out_file = results_dir / "realtick_matrix_summary.json"
    out_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Sequential MT5 Real-Tick Strategy Tester runner for FTMO-Demo 1515343166.")
    ap.add_argument("--portable-root", type=Path, default=DEFAULT_PORTABLE_ROOT)
    ap.add_argument("--specs", type=Path, default=DEFAULT_SPECS_PATH)
    ap.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    ap.add_argument("--from-date", default="2024.09.01")
    ap.add_argument("--to-date", default="2024.12.31")
    ap.add_argument("--latencies", type=int, nargs="+", default=[50, 150, 250])
    ap.add_argument("--engines", type=str, nargs="*", default=None)
    ap.add_argument("--model", type=int, default=4, help="MT5 Tester Model: 4=Every tick based on real ticks, 1=1m OHLC.")
    ap.add_argument("--utc-offset", type=int, default=2, help="Server UTC offset for Strategy Tester.")
    ap.add_argument("--timeout", type=int, default=240)
    args = ap.parse_args(argv)

    run_suite(
        portable_root=args.portable_root,
        specs_path=args.specs,
        results_dir=args.results_dir,
        from_date=args.from_date,
        to_date=args.to_date,
        latencies=args.latencies,
        engines=args.engines,
        model=args.model,
        tester_utc_offset_h=args.utc_offset,
        timeout_sec=args.timeout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
