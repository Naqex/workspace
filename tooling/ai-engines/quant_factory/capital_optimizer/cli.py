"""CLI entrypoint for the Multi-Firm Prop Capital Scaling & Promo Optimizer v2."""

from __future__ import annotations

import argparse
from pathlib import Path

from quant_core.io_utils import atomic_write_text

from quant_factory.capital_optimizer.constants import (
    DEFAULT_CATALOG_PATH,
    DEFAULT_OUT_JSON,
    DEFAULT_OUT_JSON_V2,
    DEFAULT_OUT_MD,
    DEFAULT_STEP5_REPORT_PATH,
    PRIMARY_VARIANT_DEFAULT,
)
from quant_factory.capital_optimizer.reporting import render_vietnamese_law15_report, save_results_json
from quant_factory.capital_optimizer.study import run_full_capital_promo_study


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Naqex Multi-Firm Capital Scaling & Promo Optimizer v2 (Dev <= 2024 ONLY)"
    )
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG_PATH)
    parser.add_argument("--step5", type=Path, default=DEFAULT_STEP5_REPORT_PATH)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-json-v2", type=Path, default=DEFAULT_OUT_JSON_V2)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--n-paths-grid", type=int, default=5_000)
    parser.add_argument("--n-paths-single", type=int, default=10_000)
    parser.add_argument("--horizon-months", type=int, default=36)
    parser.add_argument("--primary-variant", type=str, default=PRIMARY_VARIANT_DEFAULT)
    parser.add_argument(
        "--orig-prices",
        action="store_true",
        help="Use all-regular prices on Day 0 too (instead of BF Day-0 + Regular Retries)",
    )
    parser.add_argument(
        "--allow-stale-catalog",
        action="store_true",
        help="Explicitly override catalog staleness check for offline historical audits",
    )
    args = parser.parse_args(argv)

    res = run_full_capital_promo_study(
        catalog_path=args.catalog,
        step5_path=args.step5,
        n_paths_grid=args.n_paths_grid,
        n_paths_single=args.n_paths_single,
        horizon_months=args.horizon_months,
        use_promo_prices=not args.orig_prices,
        primary_variant=args.primary_variant,
        allow_stale_catalog=args.allow_stale_catalog,
    )
    saved_json = save_results_json(res, args.out_json)
    saved_json_v2 = save_results_json(res, args.out_json_v2) if args.out_json_v2 is not None else None
    md_text = render_vietnamese_law15_report(res)
    atomic_write_text(args.out_md, md_text)
    v2_str = f" | SAVED JSON_V2: {saved_json_v2} ({saved_json_v2.stat().st_size:,} B)" if saved_json_v2 else ""
    print(
        f"SAVED JSON: {saved_json} ({saved_json.stat().st_size:,} B){v2_str} | "
        f"SAVED MD: {args.out_md} ({args.out_md.stat().st_size:,} B) | "
        f"elapsed={res['elapsed_seconds']}s | primary={res['inputs']['primary_variant']} | "
        f"holdout_rows={res['safety_invariants']['holdout_rows_analysed']}"
    )
    return 0
