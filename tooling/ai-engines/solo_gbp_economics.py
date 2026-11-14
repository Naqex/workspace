"""S01 fixed GBP SL-path confirmation; no search or shared-account promotion."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import mean, median
import subprocess

import numpy as np

from solo_gbp_source import (
    WORKSPACE, PARENT, JOB, CELL, PROTOCOL, read, digest, atomic_json,
    output_root, source_pin, verify_pins, census,
)
from prop_campaign_source import Prices, START, END, DAY, HOUR, CALENDAR
from prop_portfolio_common import MODELS
from prop_portfolio_ticks import realize_ticks
from prop_portfolio_sources import deadline, MINUTE
from prop_portfolio_scan import raw_geometry, gap_unknown, metrics, corr, POINTS
from prop_portfolio_accounts import quantity_steps, trade_money, VALUE
from prop_portfolio_confirm import curves
from prop_campaign_exits import costs as gold_costs
from xau_h1_stage0_scan import funding_events

BASELINE = PARENT / "prop-portfolio-v3-20261114"
EUR_CELL = "EURUSD.SWEEP.ASIA.LONDON.DAY"
EXPECTED_RAW, EXPECTED_HOURS = 300, 3576
ADDENDUM = "planning/research/SOLO-GBP-PATH-PARITY-20261115.md"
LEGACY_DECISION = "planning/research/PROP-PORTFOLIO-V3-DECISION-20261114.json"
LEGACY_COMMIT = "ec602f737405dd5cad1cdcd60b72e8dd2e6c75e8"
PARAMETERS = dict(reference_risk_usd=150, marginal_gbp_risk_usd=75,
    core_risk_usd=150, eur_risk_usd=75, friction_cap=.15, retention_min=.60,
    combined_net_R_min=8, pooled_daily_correlation_max=.25,
    contract_base_units=100000, min_lot=.01, lot_step=.01,
    commission_usd_per_lot_round_trip=5, slippage_usd_per_lot_round_trip=4,
    horizon="DAY", hard_tp=None, models=list(MODELS),
    baseline_path_correction="ordinal boundary-minute delta; frozen terminal cash unchanged",
    correlation_risk_usd=75)


def validated_source(job):
    """Reject admission failures before constructing any price/curve reader."""
    job = output_root(job)
    proof = read(job / "source-proof.json")
    if proof.get("status") != "SOURCE_RECONCILED":
        raise ValueError("S01_economics_requires_SOURCE_RECONCILED")
    registration = read(job / "registration.json")
    if (proof.get("registration_sha256") != digest(job / "registration.json") or
            proof.get("manifest_sha256") != digest(job / "manifest.json")):
        raise ValueError("S01_source_proof_binding")
    if (registration.get("schema") != "solo-gbp-source-v1" or
            registration.get("cell") != CELL or registration.get("job_root") != str(job) or
            registration.get("window") != {"first": START, "end_exclusive": END} or
            registration.get("prices2024_2026_read") is not False or
            registration.get("prior_stage0_pass") is not False or
            proof.get("prices2024_2026_read") is not False or
            proof.get("source_only") is not True or
            proof.get("new_financial_outcomes_computed") is not False or
            proof.get("same_ms_order_preserved") is not True):
        raise ValueError("S01_source_scope_or_semantics")
    signals, hours = census(registration["signals"])
    manifest = read(job / "manifest.json")
    if (len(signals) != EXPECTED_RAW or len(hours) != EXPECTED_HOURS or
            hours != registration["hours"] or set(manifest) != set(map(str, hours)) or
            proof.get("expected_hours") != len(hours) or
            proof.get("admitted_hours") != len(hours) or
            proof.get("h1_difference_count") != 0 or proof.get("empty_hours") != [] or
            proof.get("held_path_issue_count") != 0):
        raise ValueError("S01_source_census_or_quality")
    verify_pins(registration)
    for row in signals:
        row["horizon"] = "DAY"
        if deadline(row, row["decision_msc"]) != (row["deadline_msc"], row["deadline_kind"]):
            raise ValueError("S01_frozen_deadline_changed")
    return registration, signals, manifest


def producer_paths():
    """Bind local Python dependencies, including imports inside functions."""
    root = WORKSPACE / "tooling/ai-engines"
    pending = [root / "solo_gbp_economics.py"]
    found = set()
    while pending:
        path = pending.pop()
        if path in found:
            continue
        found.add(path)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            names = ([node.module] if isinstance(node, ast.ImportFrom) and node.module
                     else [n.name for n in node.names] if isinstance(node, ast.Import) else [])
            for name in names:
                dependency = root / (name.split(".")[0] + ".py")
                if dependency.exists():
                    pending.append(dependency)
    found.update((WORKSPACE / PROTOCOL, WORKSPACE / CALENDAR,
                  WORKSPACE / ADDENDUM, WORKSPACE / LEGACY_DECISION,
                  root / "prop_portfolio_select.py", root / "tests/test_solo_gbp_economics.py"))
    return sorted(found)


def baseline_paths(root):
    root = Path(root)
    paths = {"eur_trades": root / "eur-satellite-dev-trades.json",
             "eur_manifest": root / "eur-native-dev-v1/manifest.json",
             "core_manifest": root.parent / "prop-qualification-campaign-20261114/gold-dev-manifest-v2.json"}
    for model in MODELS:
        paths["core_" + model] = root / f"core-curve-{model}.npz"
        paths["eur_" + model] = root / f"native-curve-{EUR_CELL}-{model}.npz"
        paths["core_trades_" + model] = root / f"regime-{model}-dev-trades.json"
        paths["original_core_trades_" + model] = root.parent / "prop-qualification-campaign-20261114" / f"paths-{model}-A0.json"
    return paths


def legacy_producers():
    """Check the actual frozen producer functions, not only NPZ field names."""
    decision = read(WORKSPACE / LEGACY_DECISION)
    declared = {r["path"]: r["sha256"] for r in decision["code_and_rules"]}
    receipt = []
    for name, function in (("prop_portfolio_select", "core_curves"),
                           ("prop_portfolio_confirm", "curves"),
                           ("prop_portfolio_scan", "native_bars")):
        relative = f"tooling/ai-engines/{name}.py"
        archived = subprocess.check_output(["git", "show", LEGACY_COMMIT + ":" + relative], cwd=WORKSPACE)
        lf = archived.replace(b"\r\n", b"\n")
        if declared[relative] not in {hashlib.sha256(content).hexdigest()
                                      for content in (lf, lf.replace(b"\n", b"\r\n"))}:
            raise ValueError("S01_legacy_producer_not_bound_to_decision")
        forms = []
        for source in (archived, (WORKSPACE / relative).read_bytes()):
            tree = ast.parse(source.decode("utf-8-sig"))
            node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function)
            # The separate source-only fix made the gap calendar asset explicit.
            # It changes diagnostics, not native_bars or curve contributions.
            for call in ast.walk(node):
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "gap_unknown":
                    call.keywords = [k for k in call.keywords if k.arg != "asset"]
            forms.append(ast.dump(node, include_attributes=False))
        if forms[0] != forms[1]:
            raise ValueError("S01_legacy_curve_contribution_changed:" + function)
        receipt.append(dict(path=relative, function=function, commit=LEGACY_COMMIT,
                            declared_sha256=declared[relative], semantic_match=True))
    return receipt


def register(job=JOB, baseline=BASELINE):
    job = output_root(job)
    source, _, _ = validated_source(job)
    target = output_root(job / "economics-v1")
    path = output_root(target / "registration.json")
    if path.exists():
        previous = verify_registration(job)
        if previous["baseline_root"] != str(Path(baseline).resolve()):
            raise ValueError("S01_baseline_changed")
        return previous
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()
    producers = []
    for current in producer_paths():
        relative = current.relative_to(WORKSPACE).as_posix()
        committed = subprocess.check_output(["git", "show", head + ":" + relative], cwd=WORKSPACE)
        if committed.replace(b"\r\n", b"\n") != current.read_bytes().replace(b"\r\n", b"\n"):
            raise ValueError("S01_commit_economics_before_registration:" + relative)
        producers.append(source_pin(current))
    baselines = {name: source_pin(p) for name, p in baseline_paths(baseline).items()}
    result = dict(schema="solo-gbp-economics-v1", cell=CELL, job_root=str(job),
        producer_commit=head, producer_pins=producers,
        input_pins=[source_pin(job / name) for name in (
            "registration.json", "manifest.json", "source-proof.json",
            "held-path-quality.json", "h1-reconciliation.json")] + list(baselines.values()),
        baseline_root=str(Path(baseline).resolve()), baselines=baselines,
        parameters=PARAMETERS, window={"first": START, "end_exclusive": END},
        numpy_version=np.__version__, prior_stage0_pass=False,
        prior_stage0_annual=source["prior_stage0_annual"],
        legacy_producers=legacy_producers(),
        prices2024_2026_read=False, created_at_utc=datetime.now(timezone.utc).isoformat(),
        scope="inherited stopped-recipe confirmation; M1-envelope marginal screen only")
    target.mkdir(exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2, ensure_ascii=False, allow_nan=False)
        output.write("\n")
    return result


def verify_registration(job):
    job = output_root(job)
    validated_source(job)
    registration = read(output_root(job / "economics-v1/registration.json"))
    if (registration.get("schema") != "solo-gbp-economics-v1" or
            registration.get("job_root") != str(job) or registration.get("cell") != CELL or
            registration.get("parameters") != PARAMETERS or
            registration.get("window") != {"first": START, "end_exclusive": END} or
            registration.get("numpy_version") != np.__version__ or
            registration.get("prices2024_2026_read") is not False):
        raise ValueError("S01_economics_registration_changed")
    verify_pins(registration)
    if registration.get("legacy_producers") != legacy_producers():
        raise ValueError("S01_legacy_producer_binding_changed")
    required = {str(p.resolve()) for p in producer_paths()}
    if required != {p["path"] for p in registration["producer_pins"]}:
        raise ValueError("S01_economics_producer_census")
    for name, path in baseline_paths(registration["baseline_root"]).items():
        if registration["baselines"].get(name) != source_pin(path):
            raise ValueError("S01_economics_baseline_binding")
    return registration


def assert_day_flat(entry, end):
    if entry // DAY != end // DAY or funding_events(entry, end):
        raise ValueError("S01_DAY_crosses_rollover")


def raw_measurements(signals, reader):
    rows = []
    for row in signals:
        entry = reader.endpoint(row["decision_msc"])
        if entry is None:
            raise ValueError("S01_raw_ENTRY_UNKNOWN")
        end, kind = deadline(row, entry[0])
        if (end, kind) != (row["deadline_msc"], row["deadline_kind"]):
            raise ValueError("S01_entry_changed_frozen_deadline")
        final = reader.endpoint(end)
        if final is None:
            raise ValueError("S01_raw_ENDPOINT_UNKNOWN")
        ticks, _ = reader.path(entry[0], final[0])
        if gap_unknown(ticks["t"], 0, asset="GBPUSD"):
            raise ValueError("S01_raw_HELD_PATH_UNKNOWN")
        assert_day_flat(entry[0], final[0])
        p0, natural, friction, passes = raw_geometry(row, entry)
        sign = 1 if row["side"] == "BUY" else -1
        px = final[1 if sign == 1 else 2]
        gross = sign * (px - p0) / 100000
        rows.append(dict(row, entry_quote=entry, endpoint_quote=final,
            natural_sl_price=natural, natural_sl_pips=natural * 10000,
            friction_price=friction, friction_fraction=friction / natural if natural > 0 else None,
            passes=bool(passes), raw_gross_price=gross, raw_net_price=gross - .00009,
            raw_net_usd_per_lot=gross * 100000 - 9))
        if len(rows) % 25 == 0:
            print(json.dumps({"stage": "S01_raw_measurement", "signals": len(rows),
                              "total": len(signals)}), flush=True)
    return rows


def economics_rows(trades, risk):
    result = []
    for trade in trades:
        assert_day_flat(trade["entry_msc"], trade["exit_msc"])
        quantity = quantity_steps(trade, risk)
        money = trade_money(trade, quantity, "SYM_FLAT", risk)
        if money["swap_usd"] != 0:
            raise ValueError("S01_unexpected_DAY_funding")
        result.append(dict(trade, quantity_steps=quantity, lots=quantity / 100,
                           risk_usd=risk, **money))
    return result


def trade_summary(rows):
    net = sum(r["net_R"] for r in rows)
    winners = sorted((r for r in rows if r["net_R"] > 0), key=lambda r: r["net_R"], reverse=True)
    top = winners[:3]
    positive = sum(r["net_R"] for r in winners)
    return dict(trades=len(rows), winrate=mean(r["net_usd"] > 0 for r in rows) if rows else None,
        mean_net_R=net / len(rows) if rows else None, net_R=net,
        **{key: sum(r[key] for r in rows) for key in
           ("gross_usd", "commission_usd", "slippage_usd", "swap_usd", "net_usd")},
        top3=[{k: r[k] for k in ("signal_id", "day", "side", "net_R")} for r in top],
        top3_fraction_of_positive_R=sum(r["net_R"] for r in top) / positive if positive else None,
        net_R_without_top3=net - sum(r["net_R"] for r in top))


def annual_measurements(raw, trades):
    output = {}
    for year in ("2022", "2023"):
        cohort = [r for r in raw if r["day"].startswith(year)]
        filled = [r for r in trades if r["day"].startswith(year)]
        natural = [r["natural_sl_price"] for r in cohort]
        friction = [r["friction_price"] for r in cohort]
        md = median(natural) if natural else None
        output[year] = dict(raw=len(cohort), filled=len(filled),
            retention=len(filled) / len(cohort) if cohort else None,
            natural_sl_median_pips=md * 10000 if md is not None else None,
            median_friction_over_median_natural_sl=median(friction) / md if md and md > 0 else None,
            passes15=sum(r["passes"] for r in cohort),
            raw_DAY_mean_net_usd_per_lot=mean(r["raw_net_usd_per_lot"] for r in cohort) if cohort else None,
            raw_DAY_net_usd_per_lot_quantiles=(np.quantile(
                [r["raw_net_usd_per_lot"] for r in cohort], [0, .1, .5, .9, 1]).tolist() if cohort else []),
            economics=trade_summary(filled),
            by_side={side: trade_summary([r for r in filled if r["side"] == side])
                     for side in ("BUY", "SELL")},
            by_exit={reason: trade_summary([r for r in filled if r["reason"] == reason])
                     for reason in sorted(set(r["reason"] for r in filled))})
    return output


def gate_reasons(annual, comparison):
    reasons = []
    total = 0
    for year in ("2022", "2023"):
        row = annual[year]
        if row["retention"] is None or not np.isfinite(row["retention"]) or row["retention"] < .60:
            reasons.append(year + ":RETENTION_LT60PCT")
        ratio = row["median_friction_over_median_natural_sl"]
        if ratio is None or not np.isfinite(ratio) or ratio > .15:
            reasons.append(year + ":FRICTION_SCALE")
        net = row["economics"]["net_R"]
        if not np.isfinite(net) or net < 0:
            reasons.append(year + ":NEGATIVE_NET_R")
        total += net
    if not np.isfinite(total) or total < 8:
        reasons.append("COMBINED_NET_LT8R")
    for model in MODELS:
        row = comparison[model]
        rho = row["GBP_to_A_EUR"]["pooled"]
        if rho is None or not np.isfinite(rho) or rho >= .25:
            reasons.append(model + ":A_EUR_CORRELATION")
        old, new = row["baseline_A150_EUR75"], row["plus_GBP75"]
        if (old["max_R_DD"] <= 0 or new["max_R_DD"] <= 0 or
                not all(np.isfinite(v[k]) for v in (old, new) for k in ("total_net_R", "max_R_DD")) or
                new["total_net_R"] / new["max_R_DD"] <= old["total_net_R"] / old["max_R_DD"]):
            reasons.append(model + ":MARGINAL_NET_DD_NOT_IMPROVED_OR_UNDEFINED")
    return reasons


def load_curve(path, prefix=""):
    with np.load(path, allow_pickle=False) as saved:
        result = [saved[prefix + key] for key in ("close", "low", "high")]
    if any(r.shape != (POINTS,) or not np.all(np.isfinite(r)) for r in result):
        raise ValueError("S01_baseline_curve_scope_or_values")
    if np.any(result[1] > result[0] + 1e-8) or np.any(result[0] > result[2] + 1e-8):
        raise ValueError("S01_baseline_curve_envelope")
    return result


class OrdinalBoundedPrices:
    """Clip same-ms quotes at the actual fill, including native_bars() reads."""
    def __init__(self, reader, trades):
        self.reader = reader
        self.files = reader.files
        self.bounds = {(t["entry_msc"], t["exit_msc"]): t for t in trades}
        if len(self.bounds) != len(trades):
            raise ValueError("S01_ambiguous_curve_trade_boundaries")
        self.active = None

    def mask(self, ticks, ordinals):
        t = self.active
        return (((ticks["t"] > t["entry_msc"]) |
                 ((ticks["t"] == t["entry_msc"]) & (ordinals >= t["entry_quote_index"]))) &
                ((ticks["t"] < t["exit_msc"]) |
                 ((ticks["t"] == t["exit_msc"]) & (ordinals <= t["exit_quote_index"]))))

    def path(self, start, end):
        # curves() requests the held path before asking native_bars for each hour.
        self.active = self.bounds[(start, end)]
        ticks, ordinals = self.reader.path(start, end)
        keep = self.mask(ticks, ordinals)
        return ticks[keep], ordinals[keep]

    def hour(self, at):
        if self.active is None:
            raise ValueError("S01_curve_requires_trade_boundary_first")
        ticks = self.reader.hour(at)
        return ticks[self.mask(ticks, np.arange(len(ticks)))]


def corrected_baseline(legacy, trades, reader, asset, model, risk):
    """Replace only boundary-minute marks; costs and post-exit cash cancel."""
    corrected = [curve.copy() for curve in legacy]
    net = 0.
    touched, changed = set(), []
    for row in trades:
        trade = dict(row, asset=asset)
        if not START <= trade["entry_msc"] <= trade["exit_msc"] < END:
            raise ValueError("S01_baseline_trade_outside_Development")
        q = quantity_steps(trade, risk)
        money = gold_costs(trade, model, risk) if asset == "XAUUSD" else trade_money(trade, q, model, risk)
        net += money["net_usd"] / 150
        for event, side in (("entry", "a" if trade["side"] == "BUY" else "b"),
                            ("exit", "b" if trade["side"] == "BUY" else "a")):
            at, ix = trade[event + "_msc"], trade[event + "_quote_index"]
            ticks = reader.hour(at // HOUR * HOUR)
            if (type(ix) is not int or not 0 <= ix < len(ticks) or int(ticks["t"][ix]) != at or
                    int(ticks[side][ix]) != trade[event + "_price_units"]):
                raise ValueError("S01_baseline_frozen_fill_quote_mismatch")
        bounded = OrdinalBoundedPrices(reader, [trade])
        bounded.active = trade
        changes = []
        for minute in sorted({trade["entry_msc"] // MINUTE, trade["exit_msc"] // MINUTE}):
            at = minute * MINUTE
            ticks = reader.hour(at // HOUR * HOUR)
            old = ((ticks["t"] // MINUTE == minute) & (ticks["t"] >= trade["entry_msc"]) &
                   (ticks["t"] <= trade["exit_msc"]))
            new = old & bounded.mask(ticks, np.arange(len(ticks)))
            if not np.any(old) or not np.any(new):
                raise ValueError("S01_baseline_boundary_unknown")
            buy = trade["side"] == "BUY"
            field = "b" if buy else "a"
            views = lambda values: np.array([values[-1], values.min() if buy else values.max(),
                                              values.max() if buy else values.min()], dtype=float)
            difference = ((1 if buy else -1) * q * VALUE[asset] / 150000 *
                          (views(ticks[field][new]) - views(ticks[field][old])))
            index = (at - START) // MINUTE
            until = index + 1
            if np.any(difference) and minute != trade["exit_msc"] // MINUTE:
                # Cumsum carries entry marks across empty minutes until the next
                # observed bar. The exit minute instead resets to cash at +1.
                until = None
                for hour in range((at + MINUTE) // HOUR * HOUR,
                                  trade["exit_msc"] // HOUR * HOUR + HOUR, HOUR):
                    following = reader.hour(hour)
                    following = following[(following["t"] >= at + MINUTE) &
                                          (following["t"] <= trade["exit_msc"])]
                    if len(following):
                        until = (int(following["t"][0]) - START) // MINUTE
                        break
                if until is None:
                    raise ValueError("S01_baseline_next_mark_unknown")
            for curve, delta in zip(corrected, difference):
                curve[index:until] += delta
            touched.add(index)
            if np.any(difference):
                changes.append(dict(minute_msc=at, through_exclusive_msc=START + until * MINUTE,
                                    delta_R=difference.tolist(),
                                    removed_quotes=int(np.count_nonzero(old) - np.count_nonzero(new))))
        if changes:
            changed.append(dict(signal_id=trade["signal_id"], changes=changes))
    if abs(float(legacy[0][-1]) - net) > 1e-7 or any(a[-1] != b[-1] for a, b in zip(legacy, corrected)):
        raise ValueError("S01_baseline_frozen_cash_bridge")
    return corrected, dict(asset=asset, risk_usd=risk, unchanged_trade_events=len(trades),
        frozen_cash_total_R=net, terminal_cash_delta_R=float(corrected[0][-1] - legacy[0][-1]),
        checked_boundary_minutes=len(touched), changed_trades=changed,
        maximum_absolute_path_delta_R=max(float(np.max(np.abs(a - b))) for a, b in zip(legacy, corrected)),
        legacy_metrics=metrics(legacy), corrected_metrics=metrics(corrected))


def baseline_reader(pin):
    manifest = read(pin["path"])
    if any(not START <= int(at) < END for at in manifest):
        raise ValueError("S01_baseline_manifest_outside_Development")
    return Prices(manifest, END)


def unchanged_core_events(regime, original):
    fields = ("signal_id", "side", "decision_msc", "entry_msc", "entry_quote_index", "entry_price_units",
              "exit_msc", "exit_quote_index", "exit_price_units", "stop_units", "deadline_msc", "reason")
    if ([{k: row[k] for k in fields} for row in regime] !=
            [{k: row[k] for k in fields} for row in original]):
        raise ValueError("S01_regime_metadata_changed_original_core_events")


def marginal_comparison(full, small, core, eur):
    baseline = [a + b for a, b in zip(core, eur)]
    joined = [a + b for a, b in zip(baseline, small)]
    reference, gbp, old, new, euro = (metrics(x) for x in (full, small, baseline, joined, eur))
    correlations = lambda sleeve, other: {"pooled": corr(sleeve["daily"], other["daily"]),
        **{str(y): corr(sleeve["daily"], other["daily"], y) for y in (2022, 2023)}}
    return dict(gbp_reference150=reference, gbp_marginal75=gbp,
        baseline_A150_EUR75=old, plus_GBP75=new,
        GBP_to_A_EUR=correlations(gbp, old), GBP_to_EUR=correlations(gbp, euro),
        GBP_reference150_to_A_EUR=correlations(reference, old),
        correlation_gate_basis="actual GBP75 after lot flooring; daily R referenced to150")


def exposure(trades):
    counts = np.zeros(POINTS, dtype=np.int32)
    for trade in trades:
        start, end = trade["entry_msc"], trade["exit_msc"]
        if not START <= start <= end < END:
            raise ValueError("S01_baseline_exposure_outside_Development")
        lo, hi = (start - START) // MINUTE, (end - START) // MINUTE + 1
        counts[lo] += 1
        if hi < POINTS:
            counts[hi] -= 1
    return np.cumsum(counts)


def overlap_summary(gbp, core, eur):
    g, a, e = (exposure(rows) for rows in (gbp, core, eur))
    held = g > 0
    minutes = int(np.count_nonzero(held))
    return dict(clock="UTC M1 occupied buckets; not exact tick concurrency",
        GBP_held_minutes=minutes, GBP_max_concurrent=int(g.max()),
        all_assets_max_concurrent=int((g + a + e).max()),
        GBP_minutes_also_A=int(np.count_nonzero(held & (a > 0))),
        GBP_minutes_also_EUR=int(np.count_nonzero(held & (e > 0))),
        GBP_minutes_also_A_or_EUR=int(np.count_nonzero(held & ((a + e) > 0))),
        GBP_fraction_also_A_or_EUR=float(np.mean((a + e)[held] > 0)) if minutes else None)


def run(job=JOB):
    job = output_root(job)
    registration = verify_registration(job)
    source, signals, manifest = validated_source(job)
    target = output_root(job / "economics-v1/run")
    target.mkdir(exist_ok=False)
    print(json.dumps({"stage": "S01_economics_started", "output": str(target)}), flush=True)
    reader = Prices(manifest, END)
    raw = raw_measurements(signals, reader)
    trades, skipped = realize_ticks(signals, manifest, END, asset="GBPUSD", recipe=CELL)
    if len(trades) + len(skipped) != len(signals) or any("UNKNOWN" in r["reason"] for r in skipped):
        raise ValueError("S01_unknown_cohort_not_omitted")
    money = economics_rows(trades, 150)
    annual = annual_measurements(raw, money)
    print(json.dumps({"stage": "S01_GBP_curves", "trades": len(trades)}), flush=True)
    clipped = OrdinalBoundedPrices(reader, trades)
    full, gaps = curves(trades, clipped, "SYM_FLAT", 150)
    small, small_gaps = curves(trades, clipped, "SYM_FLAT", 75)
    if gaps or small_gaps:
        raise ValueError("S01_curve_held_path_unknown")
    comparisons = {}
    corrected_curves = {}
    baselines = registration["baselines"]
    eur_trades = read(baselines["eur_trades"]["path"])
    core_reader = baseline_reader(baselines["core_manifest"])
    eur_reader = baseline_reader(baselines["eur_manifest"])
    for model in MODELS:
        print(json.dumps({"stage": "S01_baseline_ordinal_correction", "model": model}), flush=True)
        core_trades = read(baselines["core_trades_" + model]["path"])
        unchanged_core_events(core_trades, read(baselines["original_core_trades_" + model]["path"]))
        legacy_core = load_curve(baselines["core_" + model]["path"])
        legacy_eur = load_curve(baselines["eur_" + model]["path"], "small_")
        core, core_delta = corrected_baseline(legacy_core, core_trades, core_reader, "XAUUSD", model, 150)
        eur, eur_delta = corrected_baseline(legacy_eur, eur_trades, eur_reader, "EURUSD", model, 75)
        corrected_curves[model] = {**dict(zip(("core_close", "core_low", "core_high"), core)),
                                   **dict(zip(("eur_close", "eur_low", "eur_high"), eur))}
        comparisons[model] = marginal_comparison(full, small, core, eur)
        comparisons[model]["baseline_ordinal_correction"] = dict(core=core_delta, eur=eur_delta)
        comparisons[model]["overlap"] = overlap_summary(trades, core_trades, eur_trades)
    reasons = gate_reasons(annual, comparisons)
    result = dict(schema="solo-gbp-economics-result-v1", cell=CELL,
        status="INELIGIBLE" if reasons else "ELIGIBLE_FOR_THREE_ASSET_REPLAY_REVIEW",
        reasons=reasons, annual=annual, pooled_economics=trade_summary(money), comparison=comparisons,
        raw=len(raw), filled=len(trades), skipped=skipped,
        prior_stage0_pass=False, prior_stage0_annual=source["prior_stage0_annual"],
        unconditional_raw_edge_pass_claimed=False, prop_qualified=False,
        evidence_level="paired tick exits + conditional M1-envelope additive curves",
        baseline_curve_limitations=["corrected additive M1 curves are not joint three-asset tick replay",
            "baseline correction repairs ordinal bounds only; no new full-path source audit"],
        gbp_curves_clip_entry_exit_ordinals=True,
        exact_shared_account_three_assets=False, prices2024_2026_read=False,
        new_financial_outcomes_computed=True, window={"first": START, "end_exclusive": END},
        parameters=PARAMETERS, registration_sha256=digest(job / "economics-v1/registration.json"),
        units=dict(FX_price="USD/base unit", pip=.0001, lots="100000 base units",
                   curve_R="USD divided by reference150, including risk75 sleeves"))
    # Recheck bindings after computation; changed inputs never receive a sealed verdict.
    verify_registration(job)
    for name in ("raw.json", "trades.json", "gbp-curves.npz", "result.json",
                 *(f"baseline-corrected-{model}.npz" for model in MODELS)):
        output_root(target / name)
        output_root(target / (name + ".tmp"))
    atomic_json(target / "raw.json", raw)
    atomic_json(target / "trades.json", money)
    np.savez_compressed(target / "gbp-curves.npz", close=full[0], low=full[1], high=full[2],
                        small_close=small[0], small_low=small[1], small_high=small[2])
    for model, values in corrected_curves.items():
        np.savez_compressed(target / f"baseline-corrected-{model}.npz", **values)
    result["artifact_sha256"] = {p.name: digest(p) for p in target.iterdir() if p.is_file()}
    atomic_json(target / "result.json", result)
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("register", "run"))
    parser.add_argument("--job", type=Path, default=JOB)
    args = parser.parse_args()
    out = register(args.job) if args.action == "register" else run(args.job)
    print(json.dumps({"action": args.action, "status": out.get("status", "REGISTERED"),
                      "job": str(args.job)}))
