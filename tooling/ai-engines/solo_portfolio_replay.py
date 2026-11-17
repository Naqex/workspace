"""S02: fixed Development shared-account replay; no strategy search or broker IO."""
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from statistics import median
import subprocess
import sys

import numpy as np

from prop_campaign_source import Prices, stamp, START, END, HOUR, DAY
from prop_portfolio_accounts import PortfolioAccount, replay
from xau_h1_stage0_scan import funding_events

WORKSPACE = Path(__file__).resolve().parents[2]
ROOT = Path("E:/BACKUP-TRADINGWORKSPACE/solo-system-20261115-04e2/research")
JOB = ROOT / "S02-three-asset-replay"
S01 = ROOT / "S01-gbp-confirmation-source-v2"
PROTOCOL = WORKSPACE / "planning/research/SOLO-THREE-ASSET-REPLAY-PROTOCOL-20261117.md"
S01_COMMIT = "9ca78a6fafa1e52ee2b6f4f243349c80cb910f01"
S01_PINS = {
    "economics-v2/registration.json": "ef048afad1552c42bfeb5cf4a6e587e32eb1741c2d7ee7d314b5c544beeb45a1",
    "economics-v2/run/result.json": "e9e877ac8c5f9faaf9b772b20e6faeee0f7f9f7034f68cd97451dc67712005f4",
    "independent-review-v3/real-audit.json": "f1f7e2ff77b6ed63fff6da2e59e917024b53cbc53933a45682e4c9a5e040b536",
}
EUR_BOUNDARY = ROOT / "three-asset-preparation/EUR-COST-BOUNDARY-AUDIT.json"
EUR_BOUNDARY_SHA = "002b0802803746d3138094af6460d5f30b2961be0383a4a3f14d734242938393"
ASSETS = ("XAUUSD", "EURUSD", "GBPUSD")
MODELS = ("SYM_FLAT", "ASYM_FLAT")
SYSTEMS = {
    "BASELINE_A_EUR": ("XAUUSD", "EURUSD"),
    "CANDIDATE_A_EUR_GBP": ASSETS,
}
RISKS = {"XAUUSD": 150, "EURUSD": 75, "GBPUSD": 75}
CONFIG = {
    "policy": "S02_fixed150_75_75",
    "assets": list(ASSETS),
    "asset_order": "timestamp, asset_rank, source_ordinal",
    "systems": {name: list(assets) for name, assets in SYSTEMS.items()},
    "models": list(MODELS),
    "capital_usd": 50000,
    "fixed_asset_risk_usd": RISKS,
    "common_R_usd": 150,
    "equity_throttle": False,
    "open_stop_risk_cap_usd": 500,
    "daily_realized_halt_usd": 1000,
    "internal_reserve_floor_usd": 46500,
    "daily_loss_usd": 2500,
    "overall_loss_usd": 5000,
    "phase_targets_usd": [5000, 2500],
    "minimum_phase_days": 4,
    "reward_proxy": {"minimum_days": 30, "minimum_profit_usd": 20,
                     "trader_share": 0.8, "debit_all_profit": True,
                     "reset_anchor_and_peak": True},
    "quote_age_buckets_ms": [60000, 900000],
    "accounts": 108,
    "window": {"first": 1640995200000, "end_exclusive": 1704067200000},
    "prices2024_2026_read": False,
}
EVENT_FIELDS = (
    "signal_id", "recipe", "side", "decision_msc", "entry_msc", "entry_quote_index",
    "entry_price_units", "exit_msc", "exit_quote_index", "exit_price_units",
    "stop_units", "deadline_msc", "reason",
)
OPTIONAL_FIELDS = (
    "entry_quote", "deadline_kind", "exit_policy", "protected_stop_units",
    "trigger_msc", "bias_h4_known_at", "known_h4_at",
)
LIMITS = [
    "Development 2022-2023; no fresh out-of-sample evidence",
    "same admitted feeds; not FTMO feed or fill parity",
    "target specs, margin, netting mode and selected-news calendar unverified",
    "fixed funding/slippage and inherited reward/reset convention are declared scenarios",
    "cross-feed tied timestamps use a deterministic asset rank, not broker chronology",
    "overlapping monthly starts are not independent pass probabilities",
    "independent account-path review remains required before any stage promotion",
]


def read(path):
    return json.loads(Path(path).read_bytes())


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pin(path):
    return {"path": str(Path(path).resolve()), "sha256": digest(path)}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def safe_output(path):
    """Only the one registered study root is writable, including on Windows."""
    path = Path(os.path.abspath(path))
    root = Path(os.path.abspath(JOB))
    require(path.is_relative_to(root), "S02_output_outside_owned_job")
    for part in (path, *path.parents):
        if part.exists():
            stat = part.lstat()
            require(not part.is_symlink() and not (getattr(stat, "st_file_attributes", 0) & 0x400),
                    "S02_output_reparse_point")
    return path


def write_new(path, value):
    path = safe_output(path)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def verify_pin(item):
    require(set(item) == {"path", "sha256"} and digest(item["path"]) == item["sha256"],
            "S02_input_hash_changed")


def historical_producers(pins, commit):
    """Old evidence binds old Git bytes, never modified live research modules."""
    require(commit == S01_COMMIT, "S02_unregistered_prior_producer")
    for item in pins:
        path = Path(item["path"]).resolve()
        require(path.is_relative_to(WORKSPACE), "S02_prior_producer_outside_workspace")
        relative = path.relative_to(WORKSPACE).as_posix()
        blob = subprocess.check_output(["git", "show", commit + ":" + relative], cwd=WORKSPACE)
        lf = blob.replace(b"\r\n", b"\n")
        require(item["sha256"] in {
            hashlib.sha256(data).hexdigest() for data in (blob, lf, lf.replace(b"\n", b"\r\n"))
        }, "S02_historical_producer_hash")


def inherited_inputs():
    """Metadata and hashes only; no binary quote reader is created here."""
    canonical = {}
    for name, checksum in S01_PINS.items():
        item = pin(S01 / name)
        require(item["sha256"] == checksum, "S02_canonical_S01_identity")
        canonical[name] = item
    registration = read(S01 / "economics-v2/registration.json")
    result = read(S01 / "economics-v2/run/result.json")
    review = read(S01 / "independent-review-v3/real-audit.json")
    require(
        registration["schema"] == "solo-gbp-economics-v2"
        and registration["producer_commit"] == S01_COMMIT
        and registration["job_root"] == str(S01.resolve())
        and registration["window"] == CONFIG["window"]
        and registration["prices2024_2026_read"] is False
        and result["registration_sha256"] == S01_PINS["economics-v2/registration.json"]
        and result["parameters"] == registration["parameters"]
        and result["status"] == "ELIGIBLE_FOR_THREE_ASSET_REPLAY_REVIEW"
        and result["raw"] == 300 and result["filled"] == 287
        and result["prices2024_2026_read"] is False
        and review["status"] == "CORRECTNESS_PASS_FOR_DECLARED_SCOPE"
        and (review["raw"], review["filled"], review["rejected"]) == (300, 287, 13)
        and review["economics_version"] == 2
        and review["producer_helpers_imported"] is False
        and review["prices2024_2026_read"] is False,
        "S02_prior_economics_or_review_scope",
    )
    require(len(registration["producer_pins"]) == 40 and len(registration["input_pins"]) == 28,
            "S02_prior_pin_census")
    historical_producers(registration["producer_pins"], registration["producer_commit"])
    inputs = {}
    for item in registration["input_pins"]:
        verify_pin(item)
        inputs[item["path"]] = item
    for path, checksum in review["binding_sha256"].items():
        item = {"path": path, "sha256": checksum}
        verify_pin(item)
        inputs[path] = item
    for name, checksum in result["artifact_sha256"].items():
        require(Path(name).name == name, "S02_prior_artifact_name")
        item = pin(S01 / "economics-v2/run" / name)
        require(item["sha256"] == checksum, "S02_prior_result_artifact")
        inputs[item["path"]] = item
    for item in canonical.values():
        inputs[item["path"]] = item
    boundary = pin(EUR_BOUNDARY)
    require(boundary["sha256"] == EUR_BOUNDARY_SHA, "S02_EUR_cost_boundary_identity")
    boundary_result = read(EUR_BOUNDARY)
    require(boundary_result["status"] == "MEMBERSHIP_UNCHANGED"
            and boundary_result["raw"] == 247 and boundary_result["prices2024_2026_read"] is False,
            "S02_EUR_cost_boundary_scope")
    inputs[boundary["path"]] = boundary
    source_proof = read(S01 / "source-proof.json")
    source_registration = read(S01 / "registration.json")
    require(
        source_proof["status"] == "SOURCE_RECONCILED"
        and source_proof["manifest_sha256"] == digest(S01 / "manifest.json")
        and source_proof["registration_sha256"] == digest(S01 / "registration.json")
        and source_registration["window"] == CONFIG["window"]
        and source_registration["prices2024_2026_read"] is False,
        "S02_prior_source_binding",
    )
    return {
        "producer_commit": S01_COMMIT,
        "canonical": canonical,
        "input_pins": sorted(inputs.values(), key=lambda x: x["path"]),
        "baselines": registration["baselines"],
        "prior_stage0_pass": False,
        "prior_trial_count": 112,
        "source_correction_retained": True,
        "precision_correction_retained": True,
    }


def producer_paths():
    folder = WORKSPACE / "tooling/ai-engines"
    pending, found = [folder / "solo_portfolio_replay.py"], set()
    while pending:
        path = pending.pop()
        if path in found:
            continue
        found.add(path)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            names = ([node.module] if isinstance(node, ast.ImportFrom) and node.module else
                     [item.name for item in node.names] if isinstance(node, ast.Import) else [])
            for name in names:
                dependency = folder / (name.split(".")[0] + ".py")
                if dependency.exists():
                    pending.append(dependency)
    found.update((PROTOCOL, folder / "tests/test_solo_portfolio_replay.py",
                  folder / "tests/test_solo_portfolio_accounts.py"))
    return sorted(found)


def current_producers(commit):
    items = []
    for path in producer_paths():
        relative = path.relative_to(WORKSPACE).as_posix()
        blob = subprocess.check_output(["git", "show", commit + ":" + relative], cwd=WORKSPACE)
        require(blob.replace(b"\r\n", b"\n") == path.read_bytes().replace(b"\r\n", b"\n"),
                "S02_commit_code_before_registration")
        items.append(pin(path))
    return items


def metadata_manifest(manifest):
    require(isinstance(manifest, dict) and bool(manifest), "S02_empty_source_manifest")
    for key, item in manifest.items():
        require(isinstance(key, str) and str(int(key)) == key
                and START <= int(key) < END and int(key) % HOUR == 0,
                "S02_manifest_outside_Development")
        require(type(item.get("records")) is int and item["records"] >= 0
                and isinstance(item.get("path"), str)
                and isinstance(item.get("sha256"), str) and len(item["sha256"]) == 64,
                "S02_manifest_record")
    return manifest


def normalized_event(row, asset):
    event = {key: row[key] for key in EVENT_FIELDS}
    event.update({key: row[key] for key in OPTIONAL_FIELDS if key in row})
    event.update(asset=asset, role="CORE" if asset == "XAUUSD" else "SATELLITE", regime_weight=1)
    return event


def validate_trade_metadata(trades, manifests):
    require(bool(trades), "S02_empty_trade_cohort")
    seen = set()
    for trade in trades:
        asset = trade["asset"]
        require(asset in ASSETS and trade["side"] in ("BUY", "SELL"), "S02_asset_or_side")
        require(trade["signal_id"] not in seen, "S02_duplicate_signal")
        seen.add(trade["signal_id"])
        integer_fields = ("decision_msc", "entry_msc", "exit_msc", "deadline_msc",
                          "entry_quote_index", "exit_quote_index", "entry_price_units",
                          "exit_price_units", "stop_units")
        require(all(type(trade[key]) is int for key in integer_fields), "S02_trade_integer_units")
        decision, entry, exit_at, deadline = (
            trade[key] for key in ("decision_msc", "entry_msc", "exit_msc", "deadline_msc"))
        require(START <= decision <= entry <= exit_at < END and entry < deadline < END
                and entry - decision <= 60000 and exit_at <= deadline + 60000,
                "S02_trade_clock_or_Development")
        require(min(trade["entry_quote_index"], trade["exit_quote_index"]) >= 0
                and min(trade["entry_price_units"], trade["exit_price_units"], trade["stop_units"]) > 0,
                "S02_trade_ordinal_or_quote")
        for key in ("bias_h4_known_at", "known_h4_at"):
            if trade.get(key) is not None:
                require(type(trade[key]) is int and trade[key] <= decision, "S02_future_signal_context")
        require(not (entry < stamp("2023-01-01") <= exit_at), "S02_annual_cutoff_not_flat")
        if asset == "XAUUSD":
            require(trade["recipe"] == "A" and trade.get("exit_policy") == "A0"
                    and trade.get("protected_stop_units") is None and trade.get("trigger_msc") is None,
                    "S02_nonoriginal_Gold_recipe")
            require(trade["reason"] in ("SL", "TIME_48H", "FRIDAY_CLOSE", "HOLIDAY_FLAT"),
                    "S02_Gold_exit_kind")
        else:
            require(trade["recipe"] == ("SAT1" if asset == "EURUSD"
                                       else "GBPUSD.SWEEP.ASIA.LONDON.DAY"),
                    "S02_FX_recipe")
            require(trade["reason"] in ("SL", "DAY", "FRIDAY_CLOSE", "HOLIDAY_FLAT")
                    and trade.get("deadline_kind") in ("DAY", "FRIDAY_CLOSE", "HOLIDAY_FLAT"),
                    "S02_FX_exit_kind")
            require(entry // DAY == exit_at // DAY and not funding_events(entry, exit_at),
                    "S02_FX_not_flat_before_rollover")
        needed = set(range(entry // HOUR * HOUR, exit_at // HOUR * HOUR + HOUR, HOUR))
        needed.add(decision // HOUR * HOUR)
        if trade["reason"] != "SL":
            needed.add(deadline // HOUR * HOUR)
        require(all(str(hour) in manifests[asset] for hour in needed),
                "S02_held_hour_unadmitted")


def load_inputs(lineage):
    """Load only previously sealed Development books, retaining a single union."""
    baselines = lineage["baselines"]
    core = {}
    for model in MODELS:
        rows = read(baselines["core_trades_" + model]["path"])
        original = read(baselines["original_core_trades_" + model]["path"])
        core[model] = [normalized_event(row, "XAUUSD") for row in rows]
        require(core[model] == [normalized_event(row, "XAUUSD") for row in original],
                "S02_Gold_regime_changed_original_events")
    require(core[MODELS[0]] == core[MODELS[1]], "S02_Gold_cost_models_changed_events")
    eur = [normalized_event(row, "EURUSD") for row in read(baselines["eur_trades"]["path"])]
    gbp = [normalized_event(row, "GBPUSD") for row in read(S01 / "economics-v2/run/trades.json")]
    require((len(core[MODELS[0]]), len(eur), len(gbp)) == (210, 236, 287),
            "S02_frozen_asset_census")
    manifests = {
        "XAUUSD": metadata_manifest(read(baselines["core_manifest"]["path"])),
        "EURUSD": metadata_manifest(read(baselines["eur_manifest"]["path"])),
        "GBPUSD": metadata_manifest(read(S01 / "manifest.json")),
    }
    trades = sorted(core[MODELS[0]] + eur + gbp,
                    key=lambda row: (row["entry_msc"], ASSETS.index(row["asset"]),
                                     row["entry_quote_index"], row["signal_id"]))
    validate_trade_metadata(trades, manifests)
    return trades, manifests


def register():
    root = safe_output(JOB)
    if (root / "registration.json").exists():
        return verify_registration()
    require((START, END) == (CONFIG["window"]["first"], CONFIG["window"]["end_exclusive"]),
            "S02_runtime_cutoff_changed")
    lineage = inherited_inputs()
    trades, manifests = load_inputs(lineage)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()
    registration = {
        "schema": "solo-three-asset-replay-registration-v1", "job_root": str(root),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "producer_commit": commit, "producer_pins": current_producers(commit),
        "lineage": lineage, "config": CONFIG, "python_version": sys.version,
        "numpy_version": np.__version__, "prices2024_2026_read": False,
        "trade_census": dict(Counter(row["asset"] for row in trades)),
        "manifest_hours": {asset: len(manifest) for asset, manifest in manifests.items()},
        "new_financial_outcomes_computed": False, "quote_readers_created": False,
    }
    root.mkdir(exist_ok=True)
    write_new(root / "registration.json", registration)
    return registration


def verify_registration():
    root = safe_output(JOB)
    row = read(root / "registration.json")
    require(
        row.get("schema") == "solo-three-asset-replay-registration-v1"
        and row.get("job_root") == str(root) and row.get("config") == CONFIG
        and row.get("prices2024_2026_read") is False
        and row.get("python_version") == sys.version and row.get("numpy_version") == np.__version__,
        "S02_registration_scope_or_environment",
    )
    expected = {str(path.resolve()) for path in producer_paths()}
    require(expected == {item["path"] for item in row["producer_pins"]},
            "S02_producer_pin_census")
    for item in row["producer_pins"]:
        verify_pin(item)
    require(current_producers(row["producer_commit"]) == row["producer_pins"],
            "S02_uncommitted_registered_producer")
    require(row["lineage"] == inherited_inputs(), "S02_inherited_binding_changed")
    trades, manifests = load_inputs(row["lineage"])
    require(row["trade_census"] == dict(Counter(t["asset"] for t in trades))
            and row["manifest_hours"] == {a: len(m) for a, m in manifests.items()},
            "S02_registered_source_census")
    return row


class DevelopmentPrices(Prices):
    def __init__(self, manifest):
        metadata_manifest(manifest)  # Reject before the legacy reader can silently filter.
        super().__init__(manifest, cutoff=END)

    def hour(self, at):
        rows = super().hour(at)
        require(not len(rows) or bool(np.all(rows["b"] > 0)), "S02_nonpositive_source_quote")
        return rows


def check_trade_path(trade, reader):
    """Executable quote/ordinal/first-SL proof only; no sizing or PnL."""
    decision, entry_at, exit_at, deadline = (
        trade[key] for key in ("decision_msc", "entry_msc", "exit_msc", "deadline_msc"))
    entry = reader.endpoint(decision)
    require(entry is not None and entry[0] == entry_at
            and entry[3] == trade["entry_quote_index"], "S02_entry_not_first_native_quote")
    buy = trade["side"] == "BUY"
    require(entry[2 if buy else 1] == trade["entry_price_units"], "S02_entry_executable_side")
    if "entry_quote" in trade:
        require(trade["entry_quote"] == entry[:3], "S02_saved_entry_quote")
    require(entry[1] > trade["stop_units"] if buy else entry[2] < trade["stop_units"],
            "S02_natural_stop_executable_side")
    rows = reader.hour(exit_at // HOUR * HOUR)
    ordinal = trade["exit_quote_index"]
    require(ordinal < len(rows) and int(rows["t"][ordinal]) == exit_at,
            "S02_exit_native_ordinal")
    field = "b" if buy else "a"
    require(int(rows[field][ordinal]) == trade["exit_price_units"], "S02_exit_executable_side")
    path, ordinals = reader.path(entry_at, exit_at)
    keep = ((path["t"] > entry_at) | (ordinals >= trade["entry_quote_index"])) & (
        (path["t"] < exit_at) | (ordinals <= ordinal))
    path, ordinals = path[keep], ordinals[keep]
    require(len(path) and (int(path["t"][0]), int(ordinals[0])) == (entry_at, entry[3])
            and (int(path["t"][-1]), int(ordinals[-1])) == (exit_at, ordinal),
            "S02_held_ordinal_bounds")
    hit = np.flatnonzero(
        (path[field] <= trade["stop_units"] if buy else path[field] >= trade["stop_units"])
        & (path["t"] < deadline))
    if trade["reason"] == "SL":
        require(len(hit) and int(hit[0]) == len(path) - 1, "S02_not_first_natural_SL")
    else:
        finish = reader.endpoint(deadline)
        require(not len(hit) and finish is not None
                and (finish[0], finish[3]) == (exit_at, ordinal), "S02_time_close_or_prior_SL")
        if trade["asset"] != "XAUUSD":
            require(trade["reason"] == trade["deadline_kind"], "S02_time_close_reason")
    return len(path)


def preflight_prices(trades, manifests, progress):
    readers = {asset: DevelopmentPrices(manifests[asset]) for asset in ASSETS}
    held_ticks = 0
    for number, trade in enumerate(trades, 1):
        held_ticks += check_trade_path(trade, readers[trade["asset"]])
        if number % 100 == 0:
            progress("preflight_trade_paths", trades=number, total=len(trades))
    return readers, {
        "status": "SOURCE_PATH_PREFLIGHT_PASS", "trades_checked": len(trades),
        "held_tick_visits": held_ticks,
        "source_hours_read": {a: len(r.accessed) for a, r in readers.items()},
        "no_price_synthesis": True, "new_financial_outcomes_computed": False,
        "prices2024_2026_read": False,
        "limits": ["observed native paths only; elapsed stale intervals measured separately",
                   "signals/ATR/calendar deadlines inherited, not independently regenerated"],
    }


def account_specs():
    scopes = [
        ("ANNUAL_2022", START, stamp("2023-01-01"), False),
        ("ANNUAL_2023", stamp("2023-01-01"), END, False),
        ("CONTINUOUS_DEV", START, END, False),
    ] + [(f"MONTHLY_{year}_{month:02d}", stamp(f"{year}-{month:02d}-01"), END, True)
         for year in (2022, 2023) for month in range(1, 13)]
    return [
        {"account_id": f"{model}:{system}:{scope}", "model": model, "system": system,
         "scope": scope, "start": start, "end": end, "rolling": rolling,
         "included_assets": list(included)}
        for model in MODELS for system, included in SYSTEMS.items()
        for scope, start, end, rolling in scopes
    ]


def make_accounts(specs):
    require(specs == account_specs(), "S02_noncanonical_account_specs")
    return [
        PortfolioAccount(
            s["start"], s["end"], s["model"], rolling=s["rolling"], fixed_risk=150,
            assets=ASSETS, included_assets=tuple(s["included_assets"]),
            fixed_asset_risk=dict(RISKS), track_quote_age=True, common_risk_usd=150,
            include_satellite=True, scaled=False,
        ) for s in specs
    ]


def native_account_identity(row, spec):
    expected = {
        "cell": spec["model"], "start_msc": spec["start"], "end_msc": spec["end"],
        "rolling": spec["rolling"], "assets": list(ASSETS),
        "included_assets": spec["included_assets"], "fixed_asset_risk": RISKS,
        "common_risk_usd": 150, "policy": "fixed_asset_risk_joint_ticks",
        "d1_scaled": False, "include_satellite": True,
        "accounting_model": "legacy_accrued_funding_until_exit_one_leg_float_slip",
        "reward_model": "legacy_30day_80pct_flat_proxy_resets_anchor",
        "target_specs_news_margin_and_forward_verified": False,
    }
    require(all(key in row and row[key] == value for key, value in expected.items()),
            "S02_native_account_identity")
    require(type(row["rolling"]) is bool and type(row["d1_scaled"]) is bool
            and type(row["include_satellite"]) is bool,
            "S02_native_account_boolean_identity")


def bind_account_rows(rows, specs):
    require(specs == account_specs() and len(rows) == len(specs), "S02_replay_account_census")
    for row, spec in zip(rows, specs):
        native_account_identity(row, spec)
        require(not any(key in row for key in ("account_id", "model", "system", "scope")),
                "S02_native_row_already_labeled")
    return [
        dict(row, account_id=spec["account_id"], model=spec["model"],
             system=spec["system"], scope=spec["scope"])
        for row, spec in zip(rows, specs)
    ]


def compact_account(row):
    net, dd_usd = row["net_usd"], row["peak_dd_pct"] * 500
    require(abs(row["portfolio_common_R"] - net / 150) < 1e-8
            and abs(row["equity_DD_common_R"] - dd_usd / 150) < 1e-8,
            "S02_common_R_accounting")
    closed = sorted((item["net_usd"] for item in row["closed"]), reverse=True)
    top = [value for value in closed if value > 0][:3]
    return {
        "account_id": row["account_id"], "system": row["system"], "model": row["model"],
        "scope": row["scope"], "entries": row["entries"], "closed_trades": row["closed_trades"],
        "net_usd": net, "portfolio_common_R": net / 150,
        "mean_own_risk_trade_R": row["mean_net_R"],
        "equity_DD_usd": dd_usd, "equity_DD_common_R": dd_usd / 150,
        "peak_dd_pct": row["peak_dd_pct"], "static_loss_pct": row["static_loss_pct"],
        "worst_daily_loss_pct": row["worst_daily_loss_pct"],
        "Net_over_equity_DD": net / dd_usd if dd_usd > 0 else None,
        "top3_net_usd": top, "net_without_top3_usd": net - sum(top),
        "max_concurrency": row["max_concurrency"],
        "maximum_open_stop_risk_pct": row["maximum_open_stop_risk_pct"],
        "first_breach": row["first_breach"], "rejections": row["rejections"],
        "quote_age_coverage": row["quote_age_coverage"],
    }


def lifecycle_summary(rows):
    p1 = [row for row in rows if len(row["phase_passes"]) >= 1]
    p2 = [row for row in rows if len(row["phase_passes"]) >= 2]
    elapsed = lambda row, phase: (row["phase_passes"][phase]["at"] - row["start_msc"]) / DAY
    funded_paths = set()
    for row in p2:
        content = {
            "accepted": [a for a in row["accepted"] if a["phase"] == 3],
            "closed": [a for a in row["closed"] if a["phase"] == 3],
            "payouts": row["payouts"],
        }
        if content["accepted"]:
            funded_paths.add(hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest())
    return {
        "starts": len(rows), "phase1_passes": len(p1), "both_phases_passed": len(p2),
        "observed_breach_accounts": sum(row["first_breach"] is not None for row in rows),
        "phase1_median_days_among_completions": median(elapsed(r, 0) for r in p1) if p1 else None,
        "both_median_days_among_completions": median(elapsed(r, 1) for r in p2) if p2 else None,
        "phase1_right_censored_or_failed": len(rows) - len(p1),
        "both_right_censored_or_failed": len(rows) - len(p2),
        "phase1_right_censored": sum(not r["phase_passes"] and r["first_breach"] is None for r in rows),
        "phase1_failed_before_completion": sum(not r["phase_passes"] and r["first_breach"] is not None for r in rows),
        "both_right_censored": sum(len(r["phase_passes"]) < 2 and r["first_breach"] is None for r in rows),
        "both_failed_before_completion": sum(len(r["phase_passes"]) < 2 and r["first_breach"] is not None for r in rows),
        "distinct_observed_funded_paths": len(funded_paths),
        "reward_proxy_events": sum(len(row["payouts"]) for row in rows),
        "reward_proxy_trader_usd": sum(row["trader_payout_usd"] for row in rows),
        "probability_interpretation": False,
    }


def summarize(rows):
    specs = account_specs()
    require(len(rows) == len(specs) and len({row["account_id"] for row in rows}) == len(specs),
            "S02_result_account_census")
    for row, spec in zip(rows, specs):
        require(all(row.get(key) == spec[key] for key in ("account_id", "model", "system", "scope")),
                "S02_result_selector_binding")
        native_account_identity(row, spec)
    require(all(row["cash_bridge_verified"] for row in rows),
            "S02_incomplete_accounts_or_cash_bridge")
    diagnostic = [compact_account(row) for row in rows if not row["rolling"]]
    lifecycle = {}
    reasons = []
    for model in MODELS:
        for system in SYSTEMS:
            subset = [row for row in rows if row["model"] == model and row["system"] == system
                      and row["rolling"]]
            require(len(subset) == 24, "S02_monthly_census")
            lifecycle[f"{model}:{system}"] = lifecycle_summary(subset)
        full = {row["system"]: row for row in diagnostic
                if row["model"] == model and row["scope"] == "CONTINUOUS_DEV"}
        baseline = full["BASELINE_A_EUR"]["Net_over_equity_DD"]
        candidate = full["CANDIDATE_A_EUR_GBP"]["Net_over_equity_DD"]
        if baseline is None or candidate is None or candidate <= baseline:
            reasons.append(f"NET_DD_NOT_IMPROVED:{model}")
        for row in diagnostic:
            if (row["model"] == model and row["system"] == "CANDIDATE_A_EUR_GBP"
                    and row["scope"].startswith("ANNUAL_") and row["net_usd"] < 0):
                reasons.append(f"NEGATIVE_ANNUAL:{model}:{row['scope']}")
    if any(row["first_breach"] is not None for row in rows if row["rolling"]):
        reasons.append("MODELED_LIFECYCLE_BREACH")
    if any(row["quote_age_coverage"].get("path_complete") is not True for row in rows):
        reasons.append("DATA_PATH_INCOMPLETE")
    return {
        "status": ("INCONCLUSIVE_PATH" if "DATA_PATH_INCOMPLETE" in reasons else
                   "NUMERICAL_GATES_NOT_MET" if reasons else
                   "NUMERICAL_GATES_PASSED_AWAITING_INDEPENDENT_REVIEW"),
        "reasons": reasons, "diagnostic_accounts": diagnostic, "lifecycle": lifecycle,
        "common_R_usd": 150, "prop_qualified": False, "independent_result_review": "PENDING",
        "historical_validation_released": False, "prices2024_2026_read": False,
        "limits": LIMITS,
    }


def report_markdown(summary):
    lines = ["# S02 — shared-account Development replay", "",
             f"Status: **{summary['status']}**. Prop qualified: **false**.", "",
             "Giá trị R của danh mục = USD/150; không cộng R theo risk riêng từng lệnh.", "",
             "| Model | System | Scope | NetUSD | EquityDD USD | Daily loss % |",
             "|---|---|---|---:|---:|---:|"]
    for row in summary["diagnostic_accounts"]:
        lines.append(f"|{row['model']}|{row['system']}|{row['scope']}|"
                     f"{row['net_usd']:.2f}|{row['equity_DD_usd']:.2f}|"
                     f"{row['worst_daily_loss_pct']:.4f}|")
    lines += ["", "## Lifecycle proxy", "",
              "| Model / System | P1 /24 | P2 /24 | Breach | Proxy payouts |",
              "|---|---:|---:|---:|---:|"]
    for name, row in summary["lifecycle"].items():
        lines.append(f"|{name}|{row['phase1_passes']}|{row['both_phases_passed']}|"
                     f"{row['observed_breach_accounts']}|{row['reward_proxy_events']}|")
    lines += ["", "Các monthly starts chồng lấn; không coi tỷ lệ này là xác suất pass tương lai.",
              "Đối soát độc lập result và target rules/news/margin/feed/forward vẫn còn mở.", "",
              "Reasons: " + (", ".join(summary["reasons"]) or "none at numerical screen"), ""]
    return "\n".join(lines)


def execute(action):
    require(action in ("preflight", "run"), "S02_unregistered_action")
    root = safe_output(JOB)
    # A missing registration must not leave an empty attempt without a receipt.
    registration_hash = digest(root / "registration.json")
    folder = safe_output(root / ("preflight-1" if action == "preflight" else "attempt-1"))
    folder.mkdir(exist_ok=False)
    identity = {
        "action": action, "pid": os.getpid(), "started_utc": datetime.now(timezone.utc).isoformat(),
        "registration_sha256": registration_hash,
        "new_financial_outcomes_computed": action == "run", "prices2024_2026_read": False,
    }
    write_new(folder / "execution-start.json", identity)
    log = safe_output(folder / "events.jsonl")
    with log.open("x", encoding="utf-8"):
        pass

    def progress(stage, **fields):
        item = {"utc": datetime.now(timezone.utc).isoformat(), "stage": stage, **fields}
        with log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(item, allow_nan=False) + "\n")
        print(json.dumps(item), flush=True)

    try:
        registration = verify_registration()
        trades, manifests = load_inputs(registration["lineage"])
        progress("preflight_started", trades=len(trades))
        readers, proof = preflight_prices(trades, manifests, progress)
        write_new(folder / "preflight.json", proof)
        if action == "preflight":
            verify_registration()
            result = dict(proof, registration_sha256=identity["registration_sha256"])
        else:
            specs = account_specs()
            accounts = make_accounts(specs)
            write_new(folder / "trades.json", trades)
            write_new(folder / "manifests.json", manifests)
            write_new(folder / "account-specs.json", specs)
            progress("shared_account_replay_started", accounts=len(accounts))
            rows = replay(trades, readers, accounts, end=END, assets=ASSETS, progress=progress)
            rows = bind_account_rows(rows, specs)
            summary = summarize(rows)
            verify_registration()
            write_new(folder / "accounts.json", rows)
            write_new(folder / "summary.json", summary)
            with safe_output(folder / "REPORT.md").open("x", encoding="utf-8") as stream:
                stream.write(report_markdown(summary))
            result = {
                "schema": "solo-three-asset-replay-result-v1", "config": CONFIG,
                "status": summary["status"], "reasons": summary["reasons"],
                "registration_sha256": identity["registration_sha256"],
                "accounts": len(rows), "trades": len(trades), "prop_qualified": False,
                "independent_result_review": "PENDING", "prices2024_2026_read": False,
                "historical_validation_released": False, "limits": LIMITS,
            }
        result["artifact_sha256"] = {
            path.name: digest(path) for path in folder.iterdir()
            if path.is_file() and path.name not in ("events.jsonl",)
        }
        write_new(folder / "result.json", result)
        finish = dict(identity, finished_utc=datetime.now(timezone.utc).isoformat(),
                      status="COMPLETED", result_sha256=digest(folder / "result.json"),
                      numerical_status=result["status"])
        write_new(folder / "execution-finish.json", finish)
        progress("completed", status=result["status"])
        return finish
    except Exception as error:
        write_new(folder / "failure.json", dict(
            identity, failed_utc=datetime.now(timezone.utc).isoformat(),
            status="FAILED", error_type=type(error).__name__, error=str(error),
        ))
        raise


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("register", "preflight", "run"))
    args = parser.parse_args()
    outcome = register() if args.action == "register" else execute(args.action)
    print(json.dumps({"action": args.action, "status": outcome.get("status", "REGISTERED")}))
