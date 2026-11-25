"""Generate Clean 9-Chart MT5 Profile (`Naqex_FreeTrial`) for FTMO-Demo (`1515343166`).

Attaches `Naqex_AccountOrchestrator` + all 8 white-box EAs (`Naqex_WB_*.ex5`) using the
verified `deployment_kit/presets/<profile_name>/*.set` presets (default `FTMO_FreeTrial_Demo`
for owner-authorized FTMO-Demo `1515343166`, while keeping `.mq5` source defaults strictly
`InpDryRunLogOnly = true`).

Writes clean UTF-16LE `.chr` files + `order.wnd` into target MT5 `MQL5/Profiles/Charts/Naqex_FreeTrial/`.
NEVER touches `C:\\Program Files\\MetaTrader 5` (Exness Real terminal).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

EXPORTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPORTS_DIR.parents[2]
PRESETS_ROOT = EXPORTS_DIR / "deployment_kit/presets"

if str(EXPORTS_DIR) not in sys.path:
    sys.path.insert(0, str(EXPORTS_DIR))

import verify_deployment_kit as kit  # noqa: E402

DEFAULT_PORTABLE_ROOT = REPO_ROOT / ".runtime/ftmo-demo-portable-1515343166"
DEFAULT_FTMO_APPDATA_ROOT = Path(
    r"C:\Users\MIIKEY\AppData\Roaming\MetaQuotes\Terminal\81A933A9AFC5DE3C23B15CAB19C63850"
)

# Forbidden path guard: NEVER touch the Exness Real MT5 installation
FORBIDDEN_PATH_TOKENS = ("program files\\metatrader 5", "d0e8209f77c8cf37ad8bf550e51ff075")

CHART_PLAN: list[dict[str, Any]] = [
    {
        "chart_file": "chart01.chr",
        "chart_id": 133000000000000001,
        "symbol": "EURUSD",
        "description": "Euro vs United States Dollar",
        "digits": 5,
        "timeframe": "M15",
        "period_type": 0,
        "period_size": 15,
        "expert_stem": "Naqex_AccountOrchestrator",
        "engine_id": "ORCHESTRATOR",
        "window_rect": (0, 0, 560, 260),
    },
    {
        "chart_file": "chart02.chr",
        "chart_id": 133000000000000002,
        "symbol": "USDJPY",
        "description": "US Dollar vs Japanese Yen",
        "digits": 3,
        "timeframe": "M15",
        "period_type": 0,
        "period_size": 15,
        "expert_stem": "Naqex_WB_TOKYO_BOX_USDJPY",
        "engine_id": "E1_USDJPY_TOKYO",
        "window_rect": (560, 0, 1120, 260),
    },
    {
        "chart_file": "chart03.chr",
        "chart_id": 133000000000000003,
        "symbol": "USDJPY",
        "description": "US Dollar vs Japanese Yen",
        "digits": 3,
        "timeframe": "M15",
        "period_type": 0,
        "period_size": 15,
        "expert_stem": "Naqex_WB_EXP080_USDJPY",
        "engine_id": "E2_USDJPY_EXP80",
        "window_rect": (0, 260, 560, 520),
    },
    {
        "chart_file": "chart04.chr",
        "chart_id": 133000000000000004,
        "symbol": "GBPUSD",
        "description": "Great Britain Pound vs US Dollar",
        "digits": 5,
        "timeframe": "M15",
        "period_type": 0,
        "period_size": 15,
        "expert_stem": "Naqex_WB_EXP080_VOLHIGH_GBPUSD",
        "engine_id": "E3_GBPUSD_VH",
        "window_rect": (560, 260, 1120, 520),
    },
    {
        "chart_file": "chart05.chr",
        "chart_id": 133000000000000005,
        "symbol": "US100.cash",
        "description": "NASDAQ 100 Index, Spot CFD",
        "digits": 2,
        "timeframe": "M5",
        "period_type": 0,
        "period_size": 5,
        "expert_stem": "Naqex_WB_SESS_CONT_BRK40_US100",
        "engine_id": "E4_US100_SESS40",
        "window_rect": (0, 520, 560, 780),
    },
    {
        "chart_file": "chart06.chr",
        "chart_id": 133000000000000006,
        "symbol": "US100.cash",
        "description": "NASDAQ 100 Index, Spot CFD",
        "digits": 2,
        "timeframe": "M5",
        "period_type": 0,
        "period_size": 5,
        "expert_stem": "Naqex_WB_IDX_RS_US100_LEAD_1130",
        "engine_id": "E5_US100_RS1130",
        "window_rect": (560, 520, 1120, 780),
    },
    {
        "chart_file": "chart07.chr",
        "chart_id": 133000000000000007,
        "symbol": "EURJPY",
        "description": "Euro vs Japanese Yen",
        "digits": 3,
        "timeframe": "M15",
        "period_type": 0,
        "period_size": 15,
        "expert_stem": "Naqex_WB_VOLCOMP_EXP75_EURJPY",
        "engine_id": "E6_EURJPY_VOLCOMP",
        "window_rect": (1120, 0, 1680, 260),
    },
    {
        "chart_file": "chart08.chr",
        "chart_id": 133000000000000008,
        "symbol": "USDJPY",
        "description": "US Dollar vs Japanese Yen",
        "digits": 3,
        "timeframe": "M5",
        "period_type": 0,
        "period_size": 5,
        "expert_stem": "Naqex_WB_NY_RISK_FLOW_10ET_USDJPY",
        "engine_id": "E7_USDJPY_NY10ET",
        "window_rect": (1120, 260, 1680, 520),
    },
    {
        "chart_file": "chart09.chr",
        "chart_id": 133000000000000009,
        "symbol": "EURUSD",
        "description": "Euro vs United States Dollar",
        "digits": 5,
        "timeframe": "M15",
        "period_type": 0,
        "period_size": 15,
        "expert_stem": "Naqex_WB_FX_USD_BASKET_12U_Z35",
        "engine_id": "S6_FX_USD_BSK",
        "window_rect": (1120, 520, 1680, 780),
    },
]


def assert_safe_mt5_data_dir(data_dir: Path) -> None:
    norm = str(data_dir.resolve()).lower()
    for tok in FORBIDDEN_PATH_TOKENS:
        if tok in norm:
            raise ValueError(f"SAFETY ABORT: Refusing to touch forbidden non-FTMO MT5 path: {data_dir}")


def render_chr_content(spec: dict[str, Any], inputs: dict[str, str], *, allow_algo: bool = True) -> str:
    left, top, right, bottom = spec["window_rect"]
    expert_mode = 1 if allow_algo else 0  # Bit 0 = Allow Algo Trading ONLY (DLL imports strictly OFF!)
    input_lines = "\r\n".join(f"{k}={v}" for k, v in inputs.items())
    return (
        "<chart>\r\n"
        f"id={spec['chart_id']}\r\n"
        f"symbol={spec['symbol']}\r\n"
        f"description={spec['description']}\r\n"
        f"period_type={spec['period_type']}\r\n"
        f"period_size={spec['period_size']}\r\n"
        f"digits={spec['digits']}\r\n"
        "tick_size=0.000000\r\n"
        "position_time=0\r\n"
        "scale_fix=0\r\n"
        "scale_fix11=0\r\n"
        "scale_bar=0\r\n"
        "scale_bar_val=1.000000\r\n"
        "scale=8\r\n"
        "mode=1\r\n"
        "fore=0\r\n"
        "grid=1\r\n"
        "volume=0\r\n"
        "scroll=1\r\n"
        "shift=1\r\n"
        "shift_size=20.000000\r\n"
        "fixed_pos=0.000000\r\n"
        "ticker=1\r\n"
        "ohlc=1\r\n"
        "one_click=0\r\n"
        "one_click_btn=0\r\n"
        "bidline=1\r\n"
        "askline=1\r\n"
        "lastline=0\r\n"
        "days=0\r\n"
        "descriptions=1\r\n"
        "tradelines=1\r\n"
        "tradehistory=1\r\n"
        f"window_left={left}\r\n"
        f"window_top={top}\r\n"
        f"window_right={right}\r\n"
        f"window_bottom={bottom}\r\n"
        "window_type=1\r\n"
        "floating=0\r\n"
        "background_color=0\r\n"
        "foreground_color=16777215\r\n"
        "barup_color=65280\r\n"
        "bardown_color=255\r\n"
        "bullcandle_color=65280\r\n"
        "bearcandle_color=255\r\n"
        "chartline_color=65280\r\n"
        "volumes_color=3329330\r\n"
        "grid_color=3289650\r\n"
        "bidline_color=10061943\r\n"
        "askline_color=255\r\n"
        "lastline_color=49152\r\n"
        "stops_color=255\r\n"
        "windows_total=1\r\n"
        "\r\n"
        "<expert>\r\n"
        f"name={spec['expert_stem']}\r\n"
        f"path=Experts\\Naqex\\{spec['expert_stem']}.ex5\r\n"
        f"expertmode={expert_mode}\r\n"
        "<inputs>\r\n"
        f"{input_lines}\r\n"
        "</inputs>\r\n"
        "</expert>\r\n"
        "\r\n"
        "<window>\r\n"
        "height=100.000000\r\n"
        "objects=0\r\n"
        "\r\n"
        "<indicator>\r\n"
        "name=Main\r\n"
        "path=\r\n"
        "apply=1\r\n"
        "show_data=1\r\n"
        "scale_inherit=0\r\n"
        "scale_line=0\r\n"
        "scale_line_percent=50\r\n"
        "scale_line_value=0.000000\r\n"
        "scale_fix_min=0\r\n"
        "scale_fix_min_val=0.000000\r\n"
        "scale_fix_max=0\r\n"
        "scale_fix_max_val=0.000000\r\n"
        "expertmode=0\r\n"
        "fixed_height=-1\r\n"
        "</indicator>\r\n"
        "</window>\r\n"
        "</chart>\r\n"
    )


def build_mt5_chart_profile(
    *,
    data_dir: Path,
    preset_profile: str = "FTMO_FreeTrial_Demo",
    mt5_profile_name: str = "Naqex_FreeTrial",
    presets_root: Path = PRESETS_ROOT,
    extra_input_overrides: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Write 9 UTF-16LE `.chr` files + `order.wnd` into `<data_dir>/MQL5/Profiles/Charts/<mt5_profile_name>`."""
    assert_safe_mt5_data_dir(data_dir)
    preset_dir = presets_root / preset_profile
    if not preset_dir.exists():
        raise FileNotFoundError(f"Preset profile folder missing: {preset_dir}")

    meta_path = preset_dir / "profile_meta.json"
    meta_attachments: dict[str, dict[str, str]] = {}
    if meta_path.exists():
        meta_obj = json.loads(meta_path.read_text(encoding="utf-8"))
        meta_attachments = meta_obj.get("chart_attachments", {}) or {}

    out_dir = data_dir / "MQL5/Profiles/Charts" / mt5_profile_name
    out_dir.mkdir(parents=True, exist_ok=True)

    charts_written: list[dict[str, Any]] = []
    order_lines: list[str] = []

    for base_spec in CHART_PLAN:
        spec = dict(base_spec)
        eid = spec["engine_id"]
        if eid in meta_attachments and meta_attachments[eid].get("symbol"):
            spec["symbol"] = str(meta_attachments[eid]["symbol"])
        stem = spec["expert_stem"]
        set_path = preset_dir / f"{stem}.set"
        if not set_path.exists():
            raise FileNotFoundError(f"Missing .set preset: {set_path}")
        inputs = kit.parse_set_file(set_path)
        if extra_input_overrides and stem in extra_input_overrides:
            inputs.update(extra_input_overrides[stem])

        # Fail-closed guard: verify Cycle-1 mandatory news & orchestrator inputs are present
        required_keys = ["InpGuardNewsHardBanSec"]
        if stem == "Naqex_AccountOrchestrator":
            required_keys.extend(["InpProfitLockPct", "InpProfitLockMult", "InpDailyResetMode"])
        missing = [k for k in required_keys if k not in inputs]
        if missing:
            raise ValueError(f"Stale preset {set_path.name} missing required Cycle-1 inputs: {missing}")

        chr_text = render_chr_content(spec, inputs, allow_algo=True)
        chr_path = out_dir / spec["chart_file"]
        chr_path.write_bytes(chr_text.encode("utf-16"))  # UTF-16LE with BOM, exact MT5 format
        order_lines.append(spec["chart_file"])
        chart_rec: dict[str, Any] = {
            "chart_file": spec["chart_file"],
            "engine_id": eid,
            "expert": f"Experts\\Naqex\\{stem}.ex5",
            "symbol": spec["symbol"],
            "timeframe": spec["timeframe"],
            "dry_run": inputs.get("InpDryRunLogOnly"),
            "guard_dry_run": inputs.get("InpGuardDryRunLogOnly"),
            "max_spread_pts": inputs.get("InpGuardMaxSpreadPoints"),
            "max_symbol_risk_pct": inputs.get("InpGuardMaxSymbolRiskPct"),
            "news_hard_ban_sec": inputs.get("InpGuardNewsHardBanSec"),
            "magic": inputs.get("InpMagicNumber", "RANGE_20261120_20261199"),
        }
        if stem == "Naqex_AccountOrchestrator":
            chart_rec["profit_lock_pct"] = inputs.get("InpProfitLockPct")
            chart_rec["profit_lock_mult"] = inputs.get("InpProfitLockMult")
            chart_rec["daily_reset_mode"] = inputs.get("InpDailyResetMode")
        charts_written.append(chart_rec)

    order_path = out_dir / "order.wnd"
    order_path.write_bytes(("\r\n".join(order_lines) + "\r\n").encode("utf-16"))

    return {
        "schema": "naqex-mt5-chart-profile-v1",
        "ok": True,
        "data_dir": str(data_dir),
        "profile_dir": str(out_dir),
        "preset_profile": preset_profile,
        "mt5_profile_name": mt5_profile_name,
        "charts_count": len(charts_written),
        "charts": charts_written,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build 9-chart Naqex_FreeTrial MT5 profile for FTMO-Demo.")
    ap.add_argument("--preset-profile", default="FTMO_FreeTrial_Demo", help="Preset profile under deployment_kit/presets/.")
    ap.add_argument("--mt5-profile-name", default="Naqex_FreeTrial", help="MT5 chart profile directory name.")
    ap.add_argument("--data-dir", type=Path, action="append", default=None, help="Target MT5 Data Folder(s).")
    ap.add_argument("--json", action="store_true", help="Output JSON summary.")
    args = ap.parse_args(argv)

    targets = args.data_dir or [p for p in (DEFAULT_PORTABLE_ROOT, DEFAULT_FTMO_APPDATA_ROOT) if p.exists()]
    if not targets:
        print("ERROR: No FTMO MT5 data folder found.", file=sys.stderr)
        return 1

    results = [
        build_mt5_chart_profile(
            data_dir=t,
            preset_profile=args.preset_profile,
            mt5_profile_name=args.mt5_profile_name,
        )
        for t in targets
    ]
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"Built MT5 profile '{r['mt5_profile_name']}' ({r['charts_count']} charts, preset={r['preset_profile']}) -> {r['profile_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
