"""All-account ledger audits, fixed common draws and censored state experiments."""
from datetime import datetime, timezone
from statistics import median
import json
import time
import numpy as np
from prop_v19_common import *
from prop_v19_campaign import Tape, oracle
from prop_v19_accounts import V19Account, V19LedgerOracle
from prop_v18_blocks import BlockTape
from prop_v18_costs import FrictionAccount, FrictionOracle, cost_bindings
from prop_v18_bootstrap import draw_plan, sequence_for, MC_END, YEAR
from quant_core.prop_lifecycle_and_parity import bindings


class ScalarPointOracleMixin:
    """Same independent integer ledger at one quote; avoid one-element arrays."""
    def point(self, at, quote):
        if not self.breach:
            equity = self.cash + self.floating(quote)
            if self.e["rolling"] and equity <= max(self.anchor - 2500000, 45000000):
                self.breach = dict(at=int(at), equity=int(equity))
            self.dd = max(self.dd, self.peak - equity)
            self.daily = max(self.daily, self.anchor - equity)
            self.static = max(self.static, 50000000 - equity)
            self.peak = max(self.peak, equity)
        self.observe(at)


class FastV19Oracle(ScalarPointOracleMixin, V19LedgerOracle):
    pass


class FastV16Oracle(ScalarPointOracleMixin, FrictionOracle):
    pass


def verify():
    frozen = read(FREEZE)
    if json.loads(__import__("subprocess").check_output(["git", "show", "HEAD:" + FREEZE.as_posix()])) != frozen:
        raise ValueError("V19_selection_not_committed")
    for name, digest in frozen["code_pins"].items():
        if sha(name) != digest:
            raise ValueError("V19_frozen_code_changed:" + name)
    return frozen


def audit(tape, sequence, row, baseline=False):
    import prop_v18_audit as previous
    with bindings(previous, FrictionOracle=FastV16Oracle if baseline else FastV19Oracle):
        return previous.audit_path(tape, sequence, row)


def baseline_history(tag, mode, pct):
    verify()
    tape = BlockTape(tag, mode)
    if pct == 100:
        prefix = "preflight-optimized" if (tag, mode) == ("OLHC", "PRIMARY") else f"preflight-{tag}-{mode}-optimized"
        source = V18 / (prefix + "-native-unaudited.json")
        rows = read(source)["rows"]
    else:
        source = V18 / f"historical-{tag}-{mode}-{pct}-accounts.json"
        rows = read(source)
    sequence = [(i, 0) for i in range(len(tape.blocks))]
    checked = []
    with cost_bindings(pct):
        for i, row in enumerate(rows):
            checked.append(audit(tape, sequence, row, True))
            if (i + 1) % 32 == 0:
                event("V19_baseline_history_audit", order=tag, mode=mode, friction=pct, done=i + 1)
    save(f"baseline-history-{tag}-{mode}-{pct}-audit.json",
         dict(passed=True, accounts=len(rows), all_checks=checked, source=str(source),
              source_sha256=sha(source), original_accounts_not_copied_or_changed=True))


def summarize(rows):
    horizons = []
    for months in (12, 18, 24, 36):
        limit = FIRST + months / 12 * YEAR
        horizons.append(dict(months=months,
            phase1_pct=100 * sum(0 <= r["phase1"] <= limit for r in rows) / len(rows),
            both_pct=100 * sum(0 <= r["both"] <= limit for r in rows) / len(rows),
            daily_breach_pct=100 * sum(bool(r["breach"] and r["breach"]["at"] <= limit and r["breach"]["daily"])
                                       for r in rows) / len(rows),
            overall_breach_pct=100 * sum(bool(r["breach"] and r["breach"]["at"] <= limit and r["breach"]["overall"])
                                         for r in rows) / len(rows)))
    completed = [(r["both"] - FIRST) / YEAR * 12 for r in rows if r["both"] >= 0]
    payout = np.array([r["funded_payout_years"] for r in rows])
    return dict(paths=len(rows), horizons=horizons,
                conditional_median_months=median(completed) if completed else None,
                mean_annual_payout_USD=float(payout.mean()),
                annual_payout_P25_P50_P75=np.percentile(payout.mean(axis=1), [25, 50, 75]).tolist(),
                all_path_ledgers_independently_checked=True,
                no_clean_OOS_or_independent_feed=True)


def monte(tag, mode, pct, *, baseline=False, preflight=False):
    if not preflight:
        frozen = verify()
    else:
        frozen = dict(selected_profile=read(JOB / "Dev-fit.json")["profiles"][0])
    tape = BlockTape(tag, mode) if baseline else Tape(tag, mode, dev=preflight)
    draws = draw_plan(tape)
    if not preflight and not np.array_equal(draws, np.load(V18 / "bootstrap-common-draws.npy")):
        raise ValueError("V19_not_same_V18_draws")
    count = 4 if preflight else PATHS
    label = ("preflight-MC" if preflight else "MC") + f"-{'V16' if baseline else 'V19'}-{tag}-{mode}-{pct}"
    binding = dict(pack=sha((V18 if baseline else JOB / ("Dev-pack" if preflight else "Full-pack")) /
                           f"{tag}-{mode}-blocks.json"),
                   selected=frozen["selected_profile"], baseline=baseline, friction=pct,
                   stress_code=sha(__file__), policy_code=sha("tooling/ai-engines/prop_v19_accounts.py"),
                   oracle_adapter=sha("tooling/ai-engines/prop_v18_audit.py"), count=count, seed=SEED)
    manifest = JOB / f"{label}-binding.json"
    if manifest.exists():
        if read(manifest) != binding:
            raise ValueError("V19_MC_resume_binding_changed")
    else:
        save(manifest.name, binding)
    journal = JOB / f"{label}-paths.jsonl"
    outcomes = [json.loads(v) for v in journal.read_text().splitlines()] if journal.exists() else []
    if [r["path"] for r in outcomes] != list(range(len(outcomes))):
        raise ValueError("V19_MC_resume_not_contiguous")
    started = time.perf_counter()
    with journal.open("a", encoding="utf-8") as output, cost_bindings(pct):
        for path in range(len(outcomes), count):
            sequence = sequence_for(tape, draws[path])
            accounts = []
            for funded in (False, True):
                kwargs = dict(rolling=True, standalone=funded, friction_pct=pct)
                if not baseline:
                    kwargs["profile"] = frozen["selected_profile"]
                accounts.append((FrictionAccount if baseline else V19Account)(FIRST, MC_END, "SYM_FLAT", **kwargs))
            for slot, (index, shift) in enumerate(sequence):
                tape.walk(index, shift, slot, accounts)
            rows = [a.dump() for a in accounts]
            try:
                checks = [audit(tape, sequence, r, baseline) for r in rows]
            except Exception:
                save(f"{label}-failed-path-{path}.json", dict(path=path, native=rows, sequence=sequence))
                raise
            challenge, funded = rows
            passes = {p["phase"]: p["at"] for p in challenge["phase_passes"]}
            r = dict(path=path, first_year=int(tape.blocks[sequence[0][0]]["id"][:4]),
                phase1=passes.get(1, -1), both=passes.get(2, -1), breach=challenge["first_breach"],
                funded_breach=funded["first_breach"], daily=challenge["worst_daily_loss_pct"],
                static=challenge["static_loss_pct"], funded_daily=funded["worst_daily_loss_pct"],
                funded_static=funded["static_loss_pct"],
                funded_payout_years=[sum(p["trader_usd"] for p in funded["payouts"]
                    if FIRST + year * YEAR <= p["at"] < FIRST + (year + 1) * YEAR) for year in range(3)],
                independent_full_ledger_checks=checks,
                native_ledger_sha256=[__import__("hashlib").sha256(
                    json.dumps(row, sort_keys=True).encode()).hexdigest() for row in rows])
            output.write(json.dumps(r) + "\n")
            output.flush()
            outcomes.append(r)
            if (path + 1) % 100 == 0:
                event("V19_MC_progress", case=label, paths=path + 1,
                      seconds=time.perf_counter() - started)
    summary = summarize(outcomes)
    if baseline and not preflight:
        old = read(V18 / f"bootstrap-{tag}-{mode}-{pct}-summary.json")["groups"]["random"]["horizons"]
        for a, b in zip(summary["horizons"], old):
            if (a["phase1_pct"], a["both_pct"]) != (b["phase1_pct"], b["both_pct"]):
                raise ValueError("V19_baseline_resampling_not_V18_parity")
    save(f"{label}-summary.json", dict(**summary, seconds_this_attempt=time.perf_counter() - started,
         journal_sha256=sha(journal), accounts_fully_audited=2 * len(outcomes),
         baseline=baseline, mode=mode, order=tag, friction=pct, binding=binding))
    event("V19_MC_complete", case=label, paths=count, seconds=time.perf_counter() - started)


class OpeningStateMixin:
    """A hypothetical observed starting state, not a hidden trade/capital reset."""
    def __init__(self, *args, opening_adjustment=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.opening_adjustment = int(opening_adjustment)
        self.balance = self.anchor = 50000000 + self.opening_adjustment
        self.peak = max(50000000, self.balance)
        self.static = max(0, -self.opening_adjustment)
        self.recovered_at = self.start if self.balance >= 50000000 else None

    def observe_policy(self, at, equity):
        super().observe_policy(at, equity)
        if self.recovered_at is None and not self.active and self.balance >= 50000000:
            self.recovered_at = at

    def dump(self):
        import prop_campaign_accounts as base
        import prop_v6_account as harvest
        # Only the terminal cash-bridge opening entry changes; thresholds and all
        # trading/phase transitions still use the unchanged $50k static account.
        with bindings(base, CAPITAL=50000000 + self.opening_adjustment), \
                bindings(harvest, CAPITAL=50000000 + self.opening_adjustment):
            row = super().dump()
        return dict(row, opening_adjustment_milli=self.opening_adjustment,
                    recovery_at=self.recovered_at)


class OpeningV19(OpeningStateMixin, V19Account):
    pass


class OpeningV16(OpeningStateMixin, FrictionAccount):
    pass


class OpeningOracleMixin:
    def __init__(self, expected, trades):
        super().__init__(expected, trades)
        shift = expected["opening_adjustment_milli"]
        self.cash = self.anchor = 50000000 + shift
        self.peak = max(50000000, self.cash)
        self.static = max(0, -shift)
        self.recovered = expected["start_msc"] if self.cash >= 50000000 else None

    def point(self, at, quote):
        super().point(at, quote)
        if self.recovered is None and not self.open and self.cash >= 50000000:
            self.recovered = at

    def finish(self):
        result = super().finish()
        if self.recovered != self.e["recovery_at"]:
            raise ValueError("V19_state_recovery_timestamp")
        return result


class OpeningV19Oracle(OpeningOracleMixin, FastV19Oracle):
    pass


class OpeningV16Oracle(OpeningOracleMixin, FastV16Oracle):
    pass


def states():
    frozen = verify()
    from quant_core.asymmetric_opportunity_optimizer import state_geometry, first_passage_summary
    import prop_v18_audit as previous
    # All 24 complete Dev quarters are eligible, including the boundary quarter
    # ending exactly at Dev_END; no 2024+ price enters this estimate.
    tapes = {True: BlockTape("OLHC", "PRIMARY"), False: Tape("OLHC", "PRIMARY", dev=True)}
    eligible = [i for i, b in enumerate(tapes[True].blocks) if b["first"] < DEV_END and b["end"] <= DEV_END]
    draws = np.random.default_rng(SEED).choice(eligible, size=(256, 13))
    results = []
    for baseline in (True, False):
        tape = tapes[baseline]
        for state in (.08, .05, .02, 0, -.02, -.04, -.06, -.08):
            label = f"states-{'V16' if baseline else 'V19'}-{state:+.2f}"
            rows = []
            for path in range(len(draws)):
                sequence = sequence_for(tape, draws[path])
                kwargs = dict(rolling=True, friction_pct=100, opening_adjustment=round(state * 50000000))
                if not baseline:
                    kwargs["profile"] = frozen["selected_profile"]
                account = (OpeningV16 if baseline else OpeningV19)(FIRST, MC_END, "SYM_FLAT", **kwargs)
                with cost_bindings(100):
                    for slot, (index, shift) in enumerate(sequence):
                        tape.walk(index, shift, slot, [account])
                    row = account.dump()
                    with bindings(previous, FrictionOracle=OpeningV16Oracle if baseline else OpeningV19Oracle):
                        checked = previous.audit_path(tape, sequence, row)
                passes = {p["phase"]: p["at"] for p in row["phase_passes"]}
                rows.append(dict(path=path, recovery_at=row["recovery_at"], both=passes.get(2),
                                 breach=row["first_breach"], audit=checked))
            recovery = [(r["recovery_at"] - FIRST) / YEAR * 12 if r["recovery_at"] is not None else None for r in rows]
            funded = [(r["both"] - FIRST) / YEAR * 12 if r["both"] is not None else None for r in rows]
            failed = sum(bool(r["breach"]) for r in rows)
            summary = dict(policy="V16" if baseline else "V19", **state_geometry(state),
                recovery=first_passage_summary(recovery, 36, failed),
                funded=first_passage_summary(funded, 36, failed))
            save(label + ".json", dict(summary=summary, paths=rows, all_independent_audited=True))
            results.append(summary)
            event("V19_state_complete", case=label, recovery=summary["recovery"], funded=summary["funded"])
    save("state-first-passage.json", dict(rows=results, paths_per_state=256,
         only_Development_quarters=True, future_expected_time_not_identified=True,
         automatic_reset_or_new_account=False, challenge_fee_unknown=True))


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("monte", "states", "baseline_history"))
    p.add_argument("--tag", choices=("OLHC", "OHLC"), default="OLHC")
    p.add_argument("--mode", choices=("PRIMARY", "STRICT"), default="PRIMARY")
    p.add_argument("--friction", type=int, choices=(100, 150), default=100)
    p.add_argument("--baseline", action="store_true")
    p.add_argument("--preflight", action="store_true")
    a = p.parse_args()
    if a.stage == "states":
        states()
    elif a.stage == "baseline_history":
        baseline_history(a.tag, a.mode, a.friction)
    else:
        monte(a.tag, a.mode, a.friction, baseline=a.baseline, preflight=a.preflight)
