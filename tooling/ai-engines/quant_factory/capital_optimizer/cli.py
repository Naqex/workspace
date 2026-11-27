"""CLI entrypoint for the Multi-Firm Prop Capital Scaling & Promo Optimizer v3 (incl. `--x13-shard`)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from quant_core.io_utils import atomic_write_text

from quant_factory.capital_optimizer.constants import (
    DEFAULT_CATALOG_PATH,
    DEFAULT_DERIVED_TAPES_DIR,
    DEFAULT_DERIVED_TAPES_STEM,
    DEFAULT_OUT_JSON,
    DEFAULT_OUT_JSON_V2,
    DEFAULT_OUT_MD,
    DEFAULT_STEP5_REPORT_PATH,
    DEFAULT_X13_SHARD_SEED,
    PRIMARY_VARIANT_DEFAULT,
)
from quant_factory.capital_optimizer.reporting import render_vietnamese_law15_report, save_results_json
from quant_factory.capital_optimizer.study import run_full_capital_promo_study
from quant_factory.capital_optimizer.x13_shard import run_x13_mc_shard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Naqex Multi-Firm Capital Scaling & Promo Optimizer v3 (Dev <= 2024 ONLY)"
    )
    parser.add_argument("--catalog", type=Path, default=None)
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
    # V3 Pure NumPy/Numba X13 Shard Worker Mode
    parser.add_argument(
        "--x13-shard",
        action="store_true",
        help="Run standalone pure NumPy/Numba X13 shard mode (direct frozen_9e_tapes_v2 read, zero data_store/duckdb)",
    )
    parser.add_argument("--job-id", type=str, default="cap_v3_mc_shard0")
    parser.add_argument("--shard-id", type=int, default=0)
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--shard-paths", type=int, default=2_000)
    parser.add_argument("--shard-seed", type=int, default=DEFAULT_X13_SHARD_SEED)
    parser.add_argument("--tapes-dir", type=Path, default=DEFAULT_DERIVED_TAPES_DIR)
    parser.add_argument("--tapes-stem", type=str, default=DEFAULT_DERIVED_TAPES_STEM)
    parser.add_argument("--red-news-cal", type=Path, default=None)
    parser.add_argument("--shard-out-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.x13_shard:
        shard_res = run_x13_mc_shard(
            job_id=args.job_id,
            shard_id=args.shard_id,
            num_shards=args.num_shards,
            n_paths=args.shard_paths,
            horizon_months=args.horizon_months,
            base_seed=args.shard_seed,
            primary_variant=args.primary_variant,
            tapes_dir=args.tapes_dir,
            tapes_stem=args.tapes_stem,
            calendar_path=args.red_news_cal,
            catalog_path=args.catalog,
            out_dir=args.shard_out_dir,
            use_promo_prices=not args.orig_prices,
            allow_stale_catalog=True,
        )
        print(
            json.dumps(
                {
                    "schema": shard_res["schema"],
                    "job_id": shard_res["job_id"],
                    "shard_id": shard_res["shard_id"],
                    "num_shards": shard_res["num_shards"],
                    "n_paths": shard_res["n_paths"],
                    "npz_sha256": shard_res["tape_integrity"]["npz_sha256"],
                    "max_day": shard_res["tape_integrity"]["max_day"],
                    "flat_at_reset_verified": shard_res["flat_at_reset_audit"]["flat_at_reset_verified"],
                    "holdout_rows_analysed": shard_res["holdout_rows_analysed"],
                    "order_send_count": shard_res["order_send_count"],
                    "saved_path": shard_res.get("saved_path"),
                    "elapsed_seconds": shard_res["runtime"]["elapsed_seconds"],
                },
                ensure_ascii=False,
            )
        )
        return 0

    res = run_full_capital_promo_study(
        catalog_path=args.catalog if args.catalog is not None else DEFAULT_CATALOG_PATH,
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
