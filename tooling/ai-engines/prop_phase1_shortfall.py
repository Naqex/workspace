"""Measure the first 12 months of sealed Development account ledgers."""
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from prop_campaign_accounts import CAPITAL
from prop_v18_blocks import STRIDE
from prop_v21_common import compressed
from prop_v26_common import DEV_END, FIRST, ROOT, V19, read, sha
from quant_core.job_workspace import JobWorkspace
from quant_core.prop_lifecycle_and_parity import bindings
from quant_core.vectorized_stage0_scanner import DAY
import prop_v21_common as evidence

PHASE1_TARGET_CENTS = CAPITAL // 10 + 500_000
FAMILIES = ("EURUSD F5", "XAUUSD F3", "XAUUSD F4")


def cents(usd):
    return int(Decimal(str(usd)) * 100)


def anniversary(start):
    date = datetime.fromtimestamp(start / 1000, timezone.utc)
    if date.day != 1 or start % DAY:
        raise ValueError("PHASE1_START_IS_NOT_UTC_MONTH_OPEN")
    return int(date.replace(year=date.year + 1).timestamp() * 1000)


def trade_lookup(blocks):
    lookup = {}
    for slot, block in enumerate(blocks):
        if not FIRST <= block["first"] < block["end"] <= DEV_END or len(block["trades"]) >= STRIDE:
            raise ValueError("PHASE1_BLOCK_OUTSIDE_DEVELOPMENT")
        for index, trade in enumerate(block["trades"]):
            entry, exit_at = trade["entry_msc"], trade["exit_msc"]
            family = f'{trade["asset"]} {trade["id"].split("|")[1].split(":")[0]}'
            if (family not in FAMILIES or not block["first"] <= entry <= exit_at < block["end"]
                    or entry // DAY != exit_at // DAY):
                raise ValueError("PHASE1_UNREGISTERED_TRADE_OR_OVERNIGHT_EXPOSURE")
            lookup[slot * STRIDE + index] = (entry, exit_at, family)
    return lookup


def measure(account, lookup, cutoff):
    start = account["start_msc"]
    passes = {item["phase"]: item for item in account["phase_passes"]}
    phase1 = passes.get(1)
    phase1_within = phase1 is not None and phase1["at"] < cutoff
    both_within = 2 in passes and passes[2]["at"] < cutoff
    breach = account["first_breach"]
    breached = breach is not None and breach["at"] < cutoff
    accepted = {item["trade"]: item for item in account["accepted"] if item["at"] < cutoff}
    closed = {item["trade"]: item for item in account["closed"] if item["at"] < cutoff}
    # Month boundaries are flat. If that assumption fails, this method cannot measure cash.
    if accepted.keys() != closed.keys():
        raise ValueError("PHASE1_NONFLAT_MONTH_BOUNDARY")

    cash = dict.fromkeys(FAMILIES, 0)
    counts = Counter()
    for index, row in closed.items():
        entry, exit_at, family = lookup[index]
        fill = accepted[index]
        if (not start <= entry <= row["at"] <= exit_at < cutoff
                or fill["at"] != entry or fill["phase"] != row["phase"]):
            raise ValueError("PHASE1_LEDGER_TRADE_MISMATCH")
        if row["phase"] == 1:
            cash[family] += cents(row["net_usd"])
            counts[family] += 1
    balance = CAPITAL // 10 + sum(cash.values())
    if phase1_within and balance != cents(phase1["balance_usd"]):
        raise ValueError("PHASE1_PASS_CASH_BRIDGE")
    if cutoff == account["end_msc"] and not phase1_within and balance != cents(account["balance_usd"]):
        raise ValueError("PHASE1_TERMINAL_CASH_BRIDGE")
    return dict(start=start, cutoff_exclusive=cutoff, phase1=phase1_within, both=both_within,
                breach=breached, phase1_closed_counts={key: counts[key] for key in FAMILIES},
                phase1_pnl_cents=cash, phase1_balance_cents=balance,
                shortfall_cents=0 if phase1_within else max(0, PHASE1_TARGET_CENTS - balance))


def collect():
    results, pins = {}, {}
    for ordering in ("OLHC", "OHLC"):
        for view in ("PRIMARY", "STRICT"):
            case = f"{ordering}-{view}-100"
            accounts_path = V19 / f"Dev-{case}-accounts.json"
            audit_path = V19 / f"Dev-{case}-audit.json"
            blocks_path = V19 / "Dev-pack" / f"{ordering}-{view}-blocks.json"
            pins.update({str(path.relative_to(V19)): sha(path) for path in (accounts_path, audit_path, blocks_path)})
            audit, accounts = read(audit_path), read(accounts_path)
            if not (audit["passed"] and audit["accounts"] == len(accounts)
                    and audit["binding"]["accounts"] == pins[accounts_path.name]):
                raise ValueError("PHASE1_LEDGER_AUDIT_BINDING")
            lookup = trade_lookup(read(blocks_path)["blocks"])
            cohort = [item for item in accounts if item["profile"] == "BASE_GUARD"
                      and item["kind"] == "CHALLENGE"]
            if any(item["end_msc"] != DEV_END for item in cohort):
                raise ValueError("PHASE1_ACCOUNT_END_OUTSIDE_DEVELOPMENT")
            results[case] = [measure(item, lookup, cutoff) for item in cohort
                             if (cutoff := anniversary(item["start_msc"])) <= DEV_END]
    return dict(cases=results, input_pins=pins, target_cents=PHASE1_TARGET_CENTS,
                first=FIRST, development_end_exclusive=DEV_END)


def main():
    root = JobWorkspace(ROOT / "prop-phase1-shortfall-20261118", Path(__file__).resolve().parents[2])
    output = root.activate()
    try:
        result = collect()
        result["code_sha256"] = sha(__file__)
        with bindings(evidence, JOB=output):
            compressed("phase1-windows", result)
        print(output, flush=True)
    finally:
        root.close()


if __name__ == "__main__":
    main()
