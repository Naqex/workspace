"""Compare a completed study batch with a frozen golden batch.

The comparator keeps raw/byte equality visible, while treating Decimal strings
with different scale (``"1.20"`` vs ``"1.2"``) as the same numeric value. This
is useful after a serializer or Decimal fast-path change: event ordering,
fills, risk state and accounting must still match exactly.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Any


NUMERIC_KEYS = frozenset({
    "balance", "floating_pl", "equity", "minimum_observed_equity",
    "minimum_observed_equity_usd", "net_pnl", "gross_quote", "gross_account",
    "spread_cost_account", "commission_account", "slippage_account",
    "financing_account", "quote_to_account_rate", "entry_fill", "exit_fill",
    "fill_price", "mid_close", "quote_mid_close", "bid_close", "ask_close",
    "closeable_quote", "previous_balance", "required_account", "available_account",
    "quantity", "stop_loss", "take_profit", "entry_bid", "entry_ask",
})


def _decimal_equal(left: Any, right: Any, key: str | None) -> bool:
    if key not in NUMERIC_KEYS or not isinstance(left, str) or not isinstance(right, str):
        return False
    try:
        return Decimal(left) == Decimal(right)
    except (InvalidOperation, ValueError):
        return False


def semantic_equal(left: Any, right: Any, key: str | None = None) -> bool:
    """Compare JSON values, allowing only registered Decimal scale changes."""
    if type(left) is not type(right):
        if _decimal_equal(left, right, key):
            return True
        return False
    if isinstance(left, dict):
        if set(left) != set(right):
            return False
        return all(semantic_equal(left[name], right[name], name) for name in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(
            semantic_equal(a, b, None) for a, b in zip(left, right)
        )
    return left == right or _decimal_equal(left, right, key)


def _diff_keys(left: Any, right: Any, key: str | None = None) -> set[str]:
    if semantic_equal(left, right, key):
        return set()
    if isinstance(left, dict) and isinstance(right, dict):
        keys: set[str] = set()
        for name in set(left) | set(right):
            if name not in left or name not in right:
                keys.add(name)
            else:
                keys.update(_diff_keys(left[name], right[name], name))
        return keys
    if isinstance(left, list) and isinstance(right, list):
        keys: set[str] = set()
        for a, b in zip(left, right):
            keys.update(_diff_keys(a, b, None))
        return keys or {key or "value"}
    return {key or "value"}


def _load(path: Path) -> Any:
    return json.loads(path.read_bytes())


def _file_check(current: Path, golden: Path) -> dict[str, Any]:
    if not current.exists() or not golden.exists():
        return {"status": "missing", "current": current.exists(), "golden": golden.exists()}
    current_bytes, golden_bytes = current.read_bytes(), golden.read_bytes()
    current_json, golden_json = _load(current), _load(golden)
    numeric_equal = semantic_equal(current_json, golden_json)
    return {
        "status": "equal" if current_bytes == golden_bytes else (
            "numeric_scale_only" if numeric_equal else "value_mismatch"
        ),
        "byte_equal": current_bytes == golden_bytes,
        "json_equal": current_json == golden_json,
        "numeric_semantic_equal": numeric_equal,
        "differing_keys": sorted(_diff_keys(current_json, golden_json)),
        "current_sha256": hashlib.sha256(current_bytes).hexdigest(),
        "golden_sha256": hashlib.sha256(golden_bytes).hexdigest(),
    }


def compare(current_root: Path, golden_root: Path, *, workers: list[str],
            golden_dirs: dict[str, Path] | None = None) -> dict[str, Any]:
    rows = []
    files = (
        "results.json", "reference-checkpoint.json", "cost-stress-checkpoint.json",
        "reference-decisions.json", "cost-stress-decisions.json",
        "reference-candidate.json", "cost-stress-candidate.json",
    )
    for worker in workers:
        current = current_root / worker / "replay"
        golden = (golden_dirs or {}).get(worker, golden_root / worker) / "replay"
        checks = [{"file": name, **_file_check(current / name, golden / name)} for name in files]
        ledgers = []
        for scenario in ("reference", "cost-stress"):
            current_checkpoint = _load(current / f"{scenario}-checkpoint.json")
            golden_checkpoint = _load(golden / f"{scenario}-checkpoint.json")
            current_ledger = current_checkpoint["execution"]["ledger"]
            golden_ledger = golden_checkpoint["execution"]["ledger"]
            ledgers.append({
                "scenario": scenario,
                "event_count_current": len(current_ledger),
                "event_count_golden": len(golden_ledger),
                "event_byte_equal": current_ledger == golden_ledger,
                "event_semantic_equal": semantic_equal(current_ledger, golden_ledger),
                "differing_keys": sorted(_diff_keys(current_ledger, golden_ledger)),
                "event_hash_current": hashlib.sha256(json.dumps(current_ledger, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                "event_hash_golden": hashlib.sha256(json.dumps(golden_ledger, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            })
        rows.append({
            "worker": worker,
            "checks": checks,
            "all_results_semantic_equal": all(item.get("numeric_semantic_equal", False) for item in checks),
            "all_event_ledgers_semantic_equal": all(item["event_semantic_equal"] for item in ledgers),
            "ledgers": ledgers,
        })
    return {
        "schema": "official-full-batch-golden-parity-v2",
        "current_root": str(current_root),
        "golden_root": str(golden_root),
        "completed_candidates": len(rows),
        "rows": rows,
        "all_results_semantic_equal": all(row["all_results_semantic_equal"] for row in rows),
        "all_event_ledgers_semantic_equal": all(row["all_event_ledgers_semantic_equal"] for row in rows),
        "strict_byte_parity": all(
            item.get("byte_equal", False)
            for row in rows for item in row["checks"]
        ) and all(
            item["event_byte_equal"] for row in rows for item in row["ledgers"]
        ),
        "promotion_authorized": False,
        "market_window_new": False,
        "broker_calls": 0,
        "model_calls": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--golden-comparison", type=Path,
                        help="Existing comparison.json whose result_dir maps each worker")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", nargs="+", required=True)
    args = parser.parse_args(argv)
    golden_dirs = None
    if args.golden_comparison:
        comparison = json.loads(args.golden_comparison.read_bytes())
        golden_dirs = {item["worker"]: Path(item["result_dir"]).parent
                       for item in comparison["candidates"]}
    report = compare(args.current, args.golden, workers=args.workers, golden_dirs=golden_dirs)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "all_results_semantic_equal": report["all_results_semantic_equal"],
        "all_event_ledgers_semantic_equal": report["all_event_ledgers_semantic_equal"],
        "strict_byte_parity": report["strict_byte_parity"],
    }))
    return 0 if report["all_results_semantic_equal"] and report["all_event_ledgers_semantic_equal"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
