"""Registered V4 policy; existing lifecycle and joint tick replay remain owners."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import numpy as np

from prop_campaign_source import ROOT, PARENT, Prices, START, END, FINAL, HOUR, DAY
from prop_campaign_source import read, write_json, digest, stamp
from prop_portfolio_common import JOB as V3, V1, MODELS
from prop_portfolio_accounts import PortfolioAccount, replay, VALUE, SLIP, FIELDS

JOB = ROOT / "prop-cocore-v4-20261114"
PROTOCOL = Path("planning/research/PROP-COCORE-V4-PROTOCOL-20261114.md")
DECISION = Path("planning/research/PROP-COCORE-V4-DECISION-20261114.json")


def event(stage, **values):
    JOB.mkdir(parents=True, exist_ok=True)
    row = dict(stage=stage, utc=datetime.now(timezone.utc).isoformat(), **values)
    write_json(JOB / "status.json", row)
    with (JOB / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    print(row, flush=True)


class MeasuredAccount(PortfolioAccount):
    """Instrument admissions and funded peaks without changing policy decisions."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entry_audit = []
        self.funded_peaks = dict(equity_usd=50000., balance_usd=50000.,
                                equity_after14_usd=None, equity_after30_usd=None,
                                flat_balance_after14_usd=None,
                                flat_balance_after30_usd=None)

    def funded_point(self, at, equity):
        if self.phase != 3 or self.funded_first is None:
            return
        p = self.funded_peaks
        p["equity_usd"] = max(p["equity_usd"], equity / 1000)
        p["balance_usd"] = max(p["balance_usd"], self.balance / 1000)
        for days in (14, 30):
            if at >= self.funded_first + days * DAY:
                key = f"equity_after{days}_usd"
                p[key] = max(p[key] or -float("inf"), equity / 1000)
                if not self.active:
                    key = f"flat_balance_after{days}_usd"
                    p[key] = max(p[key] or -float("inf"), self.balance / 1000)

    def action(self, kind, at, i, trades, quote, mult=0):
        before = len(self.accepted)
        old = self.rejected.copy() if kind == "entry" else None
        phase = self.phase
        super().action(kind, at, i, trades, quote, mult)
        if kind == "entry" and self.start <= at < self.end:
            reasons = list((self.rejected - old).elements())
            t = trades[i]
            accepted = len(self.accepted) > before
            self.entry_audit.append(dict(
                trade=i, at=at, asset=t["asset"], phase=phase,
                accepted=accepted, reason=reasons[0] if reasons else
                ("ACCEPTED" if accepted else "AFTER_BREACH"),
                risk_usd=self.accepted[-1]["risk_usd"] if accepted else None,
            ))
        self.funded_point(at, self.balance + self.float)

    def segment(self, rows, trades, cache):
        if self.phase == 3 and self.funded_first is not None and len(rows):
            values = np.full(len(rows), self.balance + sum(self.accrued.values()),
                             dtype="int64")
            for i, (q, _) in self.active.items():
                t = trades[i]
                field = FIELDS[t["asset"]][0 if t["side"] == "BUY" else 1]
                sign = 1 if t["side"] == "BUY" else -1
                values += (sign * q * VALUE[t["asset"]] *
                           (rows[field].astype("int64") - t["entry_price_units"])
                           - q * SLIP[t["asset"]])
            self.funded_peaks["equity_usd"] = max(
                self.funded_peaks["equity_usd"], int(values.max()) / 1000)
            for days in (14, 30):
                mask = rows["t"] >= self.funded_first + days * DAY
                if np.any(mask):
                    key = f"equity_after{days}_usd"
                    self.funded_peaks[key] = max(
                        self.funded_peaks[key] or -float("inf"),
                        int(values[mask].max()) / 1000)
        super().segment(rows, trades, cache)

    def dump(self):
        row = super().dump()
        row.update(entry_audit=self.entry_audit, funded_peaks=self.funded_peaks,
                   reward_interval_days=self.reward_interval_days)
        return row


class CoCoreAccount(MeasuredAccount):
    open_cap_milli = 800000
    internal_floor_milli = 46000000
    cap_rejection = "OPEN_STOP_RISK_1P6PCT_CAP"
    floor_rejection = "INTERNAL_STATIC_8PCT_RESERVE"

    def __init__(self, *args, reward_days=14, **kwargs):
        if reward_days not in (14, 30):
            raise ValueError("unregistered_reward_schedule")
        super().__init__(*args, **kwargs)
        self.reward_interval_days = reward_days

    def risk_request(self, equity, role, weight):
        if not self.rolling:
            return self.fixed_risk
        if self.phase not in (1, 2, 3) or role not in ("CORE", "SATELLITE") or weight != 1:
            raise ValueError("unregistered_cocore_role_or_weight")
        risk = (200, 175, 125)[self.phase - 1]
        return min(risk, 90) if equity <= 47000000 else (
            min(risk, 150) if equity <= 48000000 else risk)

    def dump(self):
        return dict(super().dump(), policy="V4_equal_cocore_200_175_125",
                    open_risk_cap_pct=1.6, internal_reserve_pct=8.)


def inputs(validation=False):
    if validation:
        release = read(JOB / "validation-release.json")
        blob = subprocess.check_output([
            "git", "show", release["decision_commit"] + ":" + DECISION.as_posix()])
        if json.loads(blob) != read(DECISION):
            raise ValueError("committed_V4_decision_changed")
        for pin in read(DECISION)["code_and_rules"]:
            if digest(pin["path"]) != pin["sha256"]:
                raise ValueError("V4_frozen_code_changed:" + pin["path"])
        trades = read(V3 / "system-trades.json")
        gold = read(PARENT / "attempt-2/binary-manifest.json")
        eur = read(V3 / "system-eur-manifest.json")
        end = FINAL
    else:
        core = read(V1 / "paths-SYM_FLAT-A0.json")
        trades = [dict(t, asset="XAUUSD", role="CORE", regime_weight=1) for t in core]
        trades += read(V3 / "eur-satellite-dev-trades.json")
        gold = read(V1 / "gold-dev-manifest-v2.json")
        eur = read(V3 / "eur-native-dev-v1/manifest.json")
        end = END
    trades.sort(key=lambda t: (t["entry_msc"], t["role"] == "SATELLITE"))
    if any(not START <= t["entry_msc"] <= t["exit_msc"] < end for t in trades):
        raise ValueError("V4_trade_outside_admitted_window")
    readers = dict(XAUUSD=Prices(gold, end), EURUSD=Prices(eur, end))
    return trades, readers, end


def development():
    trades, readers, end = inputs()
    accounts = [
        CoCoreAccount(stamp(f"{year}-{month:02d}-01"), end, model, rolling=True)
        for model in MODELS for year in (2022, 2023) for month in range(1, 13)]
    # Fixed-reference EUR books measure risk; they do not select new parameters.
    eur = [t for t in trades if t["asset"] == "EURUSD"]
    for year in (2022, 2023):
        a = CoCoreAccount(stamp(f"{year}-01-01"), stamp(f"{year+1}-01-01"),
                          "SYM_FLAT", fixed_risk=150)
        accounts.append(a)
    original = accounts[-2:]
    rows = replay(trades, readers, accounts[:48], end=end, progress=event)
    write_json(JOB / "development-accounts.json", rows)
    # Reuse the same bounded readers, with only EUR events; no joint/account reset.
    eur_rows = replay(eur, readers, original, end=end, progress=event)
    write_json(JOB / "eur-development-books.json", eur_rows)
    eligible = all(not r["first_breach"] and r["static_loss_pct"] <= 8.2
                   and r["worst_daily_loss_pct"] < 5 for r in rows)
    write_json(JOB / "risk-decision.json", dict(
        eligible=eligible, trial_count=1, years=[2022, 2023],
        worst_static_pct=max(r["static_loss_pct"] for r in rows),
        worst_daily_pct=max(r["worst_daily_loss_pct"] for r in rows),
        rule="sole equal-risk policy; no retuning after outcomes"))
    event("development_complete", accounts=len(rows), eligible=eligible)


def freeze():
    third = read(JOB / "third-sleeve-audit.json")
    if third["selected"]:
        raise ValueError("third_sleeve_requires_admitted_native_adapter")
    files = list(Path("tooling/ai-engines").glob("prop_cocore_*.py")) + [
        Path("tooling/ai-engines/prop_campaign_accounts.py"),
        Path("tooling/ai-engines/prop_portfolio_accounts.py"), PROTOCOL]
    decision = dict(
        schema="PROP-COCORE-V4-COMPOSITION-v1",
        utc=datetime.now(timezone.utc).isoformat(),
        core=["XAUUSD.A_Original", "EURUSD.SWEEP.ASIA.LONDON.DAY"],
        third_sleeve=[], risk_usd=[200, 175, 125], open_cap_usd=800,
        internal_floor_usd=46000, throttle_equity_usd=[48000, 47000],
        throttle_risk_caps_usd=[150, 90], daily_halt_usd=1000,
        reward_days=[14, 30], reward_primary_days=14,
        reward_proxy=dict(min_profit_usd=20, trader_share=.8,
                          debit_share=1, administrative_delay_days=0),
        development=read(JOB / "risk-decision.json"),
        third_audit_sha256=digest(JOB / "third-sleeve-audit.json"),
        code_and_rules=[dict(path=p.as_posix(), sha256=digest(p)) for p in sorted(files)],
        input_pins=[dict(path=str(p), sha256=digest(p)) for p in (
            V3 / "system-trades.json", V3 / "system-eur-manifest.json",
            PARENT / "attempt-2/binary-manifest.json")],
        selection="2022-2023", historical_validation="2024 already exposed",
        prices2024_used_for_selection=False, prices2025_2026_read=False)
    write_json(DECISION, decision)
    write_json(JOB / "composition-freeze.json", decision)
    event("V4_frozen_needs_commit")


def release():
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    blob = subprocess.check_output(["git", "show", head + ":" + DECISION.as_posix()])
    if json.loads(blob) != read(DECISION):
        raise ValueError("V4_decision_not_committed")
    write_json(JOB / "validation-release.json", dict(
        decision_commit=head, committed_blob_sha256=hashlib.sha256(blob).hexdigest(),
        utc=datetime.now(timezone.utc).isoformat(), cutoff=FINAL))
    event("V4_validation_released", commit=head)


def validation():
    trades, readers, end = inputs(True)
    accounts = [
        CoCoreAccount(stamp(f"{year}-{month:02d}-01"), end, model,
                      rolling=True, reward_days=days)
        for model in MODELS for days in (14, 30)
        for year in (2022, 2023, 2024) for month in range(1, 13)]
    diagnostics = [
        MeasuredAccount(stamp(start), end, "ASYM_FLAT", rolling=True)
        for start in ("2022-01-01", "2022-02-01")]
    rows = replay(trades, readers, accounts + diagnostics, end=end, progress=event)
    write_json(JOB / "validation-accounts.json", rows[:144])
    write_json(JOB / "v3-funded-paths.json", rows[144:])
    eur = [t for t in trades if t["asset"] == "EURUSD"]
    a = CoCoreAccount(stamp("2024-01-01"), end, "SYM_FLAT", fixed_risk=150)
    write_json(JOB / "eur-validation-book.json", replay(eur, readers, [a], end=end))
    event("V4_validation_complete", accounts=144)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("development", "freeze", "release", "validation"))
    globals()[p.parse_args().stage]()
