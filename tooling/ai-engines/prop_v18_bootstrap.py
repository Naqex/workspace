"""Native lifecycle replay of joint quarter quote/event blocks, no daily proxy."""
from datetime import datetime, timezone
from statistics import median
import subprocess
import time
import numpy as np
from prop_v18_common import *
from prop_v18_blocks import BlockTape, STRIDE
from prop_v18_costs import FrictionAccount, cost_bindings
from prop_v18_audit import audit_path
from prop_v15_campaign import metrics

DAY = 86400000
YEAR = 365.25 * DAY
MC_END = FIRST + int(3 * YEAR)


def draw_plan(tape):
    eligible = [i for i, b in enumerate(tape.blocks) if b["complete"]]
    return np.random.default_rng(SEED).choice(eligible, size=(PATHS, 13))


def sequence_for(tape, draws):
    at = FIRST
    result = []
    for i in draws:
        b = tape.blocks[int(i)]
        if at >= MC_END:
            break
        result.append((int(i), at - b["first"]))
        at += b["end"] - b["first"]
    if at < MC_END:
        raise ValueError("V18_36month_extension_not_covered")
    return result


def verify():
    value = read(FREEZE)
    if json.loads(subprocess.check_output(["git", "show", "HEAD:" + FREEZE.as_posix()])) != value:
        raise ValueError("V18_freeze_not_committed")
    for path, digest in value["code_pins"].items():
        if sha(path) != digest:
            raise ValueError("V18_frozen_code_drift:" + path)
    return value


def historical(tag, mode, pct, *, preflight=False):
    if not preflight:
        verify()
    tape = BlockTape(tag, mode)
    from prop_v14_accounts import monthly_starts
    starts = [(t, False) for t in monthly_starts(FIRST, END)] + [(FIRST, True)]
    accounts = [FrictionAccount(at, END, "SYM_FLAT", rolling=True, standalone=funded,
                                friction_pct=pct) for at, funded in starts]
    sequence = [(i, 0) for i in range(len(tape.blocks))]
    preflight_label = ("preflight-optimized" if (tag, mode) == ("OLHC", "PRIMARY")
                       else f"preflight-{tag}-{mode}-optimized")
    with cost_bindings(pct):
        cache = JOB / (preflight_label + "-native-unaudited.json")
        binding = dict(cost_code=sha("tooling/ai-engines/prop_v18_costs.py"),
                       block_code=sha("tooling/ai-engines/prop_v18_blocks.py"),
                       pack=sha(JOB / f"{tag}-{mode}-blocks.json"), friction=pct)
        if preflight and cache.exists():
            cached = read(cache)
            if cached["binding"] != binding:
                raise ValueError("V18_preflight_native_cache_drift")
            rows = cached["rows"]
        else:
            for slot, (index, shift) in enumerate(sequence):
                tape.walk(index, shift, slot, accounts)
            rows = [dict(a.dump(), kind="STANDALONE_FULL" if funded else "CHALLENGE")
                    for a, (_, funded) in zip(accounts, starts)]
            if preflight:
                save(cache.name, dict(binding=binding, rows=rows, status="NATIVE_NOT_YET_ORACLE_AUDITED"))
        checks = [audit_path(tape, sequence, rows[i]) for i in (0, 48, 72, 90, 104, 105)]
    if preflight:
        original = read(V16 / f"Full-{tag}-{mode}-accounts.json")
        original = [r for r in original if r["cell"] == "SYM_FLAT"]
        fields = ("phase", "phase_passes", "first_breach", "balance_usd", "net_usd",
                  "peak_dd_pct", "static_loss_pct", "worst_daily_loss_pct", "payouts", "trader_payout_usd")
        for a, b in zip(rows, original):
            for key in fields:
                if a[key] != b[key]:
                    raise ValueError("V18_sparse_native_parity:" + key + ":" + str(a["start_msc"]))
            for key, columns in (("accepted", ("at", "asset", "risk_usd", "quantity_steps")),
                                 ("closed", ("at", "phase", "risk_usd", "net_usd"))):
                if [tuple(r[k] for k in columns) for r in a[key]] != [tuple(r[k] for k in columns) for r in b[key]]:
                    raise ValueError("V18_sparse_native_parity:" + key)
    prefix = preflight_label if preflight else f"historical-{tag}-{mode}-{pct}"
    if not preflight:
        save(prefix + "-accounts.json", rows)
    save(prefix + "-audit.json", dict(passed=True, independent_checks=checks,
         native_cash_bridges=len(rows), full_original_V16_parity=preflight,
         copied_source_midnights=True, no_daily_terminal_PnL_surrogate=True,
         native_accounts=str(cache) if preflight else str(JOB / (prefix + "-accounts.json"))))
    event("V18_historical_complete", order=tag, mode=mode, friction=pct,
          preflight=preflight, **metrics(rows))


def monte(tag, mode, pct, *, preflight=False):
    if not preflight:
        verify()
    started = time.perf_counter()
    tape = BlockTape(tag, mode)
    plan = draw_plan(tape)
    count = 8 if preflight else PATHS
    regime = read(JOB / "tournament.json")["bootstrap_regimes"]
    audit_ids = set(np.random.default_rng(SEED + 1).choice(PATHS, size=32, replace=False).tolist())
    if preflight:
        audit_ids = {0, 7}
    outcomes = []
    audits = []
    for path in range(count):
        sequence = sequence_for(tape, plan[path])
        pair = [FrictionAccount(FIRST, MC_END, "SYM_FLAT", rolling=True,
                                standalone=funded, friction_pct=pct) for funded in (False, True)]
        with cost_bindings(pct):
            for slot, (index, shift) in enumerate(sequence):
                tape.walk(index, shift, slot, pair)
            rows = [a.dump() for a in pair]
            if path in audit_ids:
                for r in rows:
                    audits.append(dict(path=path, standalone=r["standalone_funded"],
                                       **audit_path(tape, sequence, r)))
        first_year = int(tape.blocks[sequence[0][0]]["id"][:4])
        r, funded = rows
        passes = {p["phase"]: p["at"] for p in r["phase_passes"]}
        outcomes.append(dict(path=path, first_year=first_year,
            favorable=first_year in regime["favorable_years"], sideways=first_year in regime["sideways_years"],
            phase1=passes.get(1, -1), both=passes.get(2, -1),
            breach=r["first_breach"], funded_breach=funded["first_breach"],
            daily=r["worst_daily_loss_pct"], static=r["static_loss_pct"],
            funded_daily=funded["worst_daily_loss_pct"], funded_static=funded["static_loss_pct"],
            funded_payout_years=[sum(p["trader_usd"] for p in funded["payouts"]
                                   if FIRST + y * YEAR <= p["at"] < FIRST + (y + 1) * YEAR) for y in range(3)],
            funded_payouts=len(funded["payouts"]), challenge_payouts=len(r["payouts"]),
            challenge_trader_usd=r["trader_payout_usd"],
            native_cash_bridges=True))
        if (path + 1) % 100 == 0:
            event("V18_bootstrap_progress", order=tag, mode=mode, friction=pct,
                  paths=path + 1, seconds=time.perf_counter() - started)
    label = f"{tag}-{mode}-{pct}"
    prefix = (("preflight-bootstrap-optimized" if label == "OLHC-PRIMARY-100"
               else "preflight-bootstrap-" + label) if preflight else f"bootstrap-{label}")
    save(prefix + "-paths.json", outcomes)
    groups = {}
    for name, use in (("random", outcomes), ("favorable_start", [r for r in outcomes if r["favorable"]]),
                      ("sideways_start", [r for r in outcomes if r["sideways"]])):
        if not use:
            groups[name] = dict(paths=0)
            continue
        rows = []
        for months in (12, 18, 24, 36):
            limit = FIRST + months / 12 * YEAR
            rows.append(dict(months=months,
                phase1_pct=100 * sum(0 <= r["phase1"] <= limit for r in use) / len(use),
                both_pct=100 * sum(0 <= r["both"] <= limit for r in use) / len(use),
                daily_breach_pct=100 * sum(bool(r["breach"] and r["breach"]["at"] <= limit
                                              and r["breach"]["daily"]) for r in use) / len(use),
                static_breach_pct=100 * sum(bool(r["breach"] and r["breach"]["at"] <= limit
                                               and r["breach"]["overall"]) for r in use) / len(use),
                funded_breach_pct=100 * sum(bool(r["funded_breach"] and r["funded_breach"]["at"] <= limit)
                                           for r in use) / len(use)))
        payout = np.array([r["funded_payout_years"] for r in use])
        groups[name] = dict(paths=len(use), horizons=rows,
            standalone_yearly_USD_P25_P50_P75=np.percentile(payout, [25, 50, 75], axis=0).T.tolist(),
            standalone_mean_annual_USD_P25_P50_P75=np.percentile(payout.mean(axis=1), [25, 50, 75]).tolist(),
            zeros_and_breached_paths_included=True)
    save(prefix + "-summary.json", dict(
        groups=groups, paths=count, seed=SEED, block="joint calendar quarter",
        source="conditional M1 scenario with unchanged source-uncertainty labels",
        duration_months=36, requested24month_prefix_reported=True,
        seconds=time.perf_counter() - started, friction_pct=pct,
        full_native_cash_bridges=2 * count, independent_sample_checks=audits,
        independent_sample_ids=sorted(audit_ids), no_new_signal_search=True,
        probability_interpretation="conditional resampling frequency, not calibrated future success probability"))
    event("V18_bootstrap_complete", order=tag, mode=mode, friction=pct, paths=count,
          seconds=time.perf_counter() - started)


def freeze():
    tournament = read(JOB / "tournament.json")
    if tournament["diagnostic_velocity_reference"]["version"] != "V16":
        raise ValueError("V18_reference_adapter")
    if not read(JOB / "preflight-optimized-audit.json")["passed"]:
        raise ValueError("V18_preflight_missing")
    for tag in ("OLHC", "OHLC"):
        for mode in ("PRIMARY", "STRICT"):
            label = ("preflight-optimized" if (tag, mode) == ("OLHC", "PRIMARY")
                     else f"preflight-{tag}-{mode}-optimized")
            if not read(JOB / (label + "-audit.json"))["full_original_V16_parity"]:
                raise ValueError("V18_all_source_modes_need_parity")
            r = read(JOB / f"{tag}-{mode}-blocks.json")
            if not r["no_swap"] or not r["no_hard_TP"]:
                raise ValueError("V18_SYM_ASYM_reuse_not_valid")
    sources = [PROTOCOL, *sorted(Path("tooling/ai-engines").glob("prop_v18_*.py")),
               *[Path("tooling/ai-engines") / n for n in (
                   "prop_v15_accounts.py", "prop_v14_accounts.py", "prop_cocore_v4.py",
                   "prop_v6_account.py", "prop_v5_account.py", "prop_campaign_accounts.py",
                   "prop_portfolio_accounts.py", "prop_portfolio_policy.py",
                   "prop_v6_replay.py", "xau_h1_execution.py", "xau_h1_stage0_scan.py",
                   "independent_ledger_auditor.py")]]
    value = dict(schema="V18-frozen-diagnostic-stress-v1", tournament_sha256=sha(JOB / "tournament.json"),
        diagnostic_reference="V16", champion_qualified=False, seed=SEED, paths=PATHS,
        friction_pct=[100, 125, 150], source_modes=["PRIMARY", "STRICT"], orderings=["OLHC", "OHLC"],
        code_pins={str(p): sha(p) for p in sources},
        block_receipts={f"{tag}-{mode}": sha(JOB / f"{tag}-{mode}-blocks.json")
                        for tag in ("OLHC", "OHLC") for mode in ("PRIMARY", "STRICT")},
        native_parity_receipts={label: sha(JOB / (label + "-audit.json")) for label in (
            "preflight-optimized", "preflight-OLHC-STRICT-optimized",
            "preflight-OHLC-PRIMARY-optimized", "preflight-OHLC-STRICT-optimized")},
        independent_sample_size=32, independent_sample_seed=SEED + 1,
        surcharge="additional half-spread + slippage per side, rounded upward to order cent",
        source_clock_preserved=True, later_history_already_exposed=True,
        SYM_ASYM_reuse="All source trades intraday and no hard TP: identical fees and zero funding.")
    with FREEZE.open("x", encoding="utf-8") as f:
        json.dump(value, f, indent=2)
    save("freeze.json", value)
    event("V18_freeze_needs_commit")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("preflight", "preflight_monte", "historical", "monte", "freeze"))
    p.add_argument("--tag", choices=("OLHC", "OHLC"), default="OLHC")
    p.add_argument("--mode", choices=("PRIMARY", "STRICT"), default="PRIMARY")
    p.add_argument("--friction", type=int, choices=(100, 125, 150), default=100)
    a = p.parse_args()
    if a.stage == "freeze":
        freeze()
    elif a.stage in ("preflight", "historical"):
        historical(a.tag, a.mode, a.friction, preflight=a.stage == "preflight")
    else:
        monte(a.tag, a.mode, a.friction, preflight=a.stage == "preflight_monte")
