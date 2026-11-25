"""Naqex Quant Pod Treasury Ledger, Prop->Own-Book Crossover Tracker & GIPS-Lite Monthly Fact Sheet Generator.

Strictly offline accounting & reporting module (`ORDER_SEND_COUNT = 0`, zero network/broker calls).
Implements:
  - Multi-prop & own-book event ledger (challenge fees, cash vs Hub-Credit refunds, 80%/90% profit splits,
    own-book deposits/withdrawals/PnL, and operational expenses).
  - Automatic 3-bucket payout discipline (`capital-scaling-prop-to-own-book.md`):
      * Bucket 1: Challenge Reserve (default 30% until capped at `reserve_cap_mult * avg_ticket_usd`;
                  overflow spills cleanly into Own-Book Seed!)
      * Bucket 2: Own-Book Seed (default 50% in Phase 1-2, 70% in Phase 3+)
      * Bucket 3: Ops, Infra & Tax Provision (default 20%)
  - Automated Prop vs Own-Book Crossover Tracker with parallel USD and VND reporting.
  - GIPS-lite Monthly Fact Sheet generator (Markdown + standalone flat-dark HTML) using
    Time-Weighted Returns (TWR), strict simulated-vs-live disclosure, and zero bare `$` in Markdown prose.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import html
import json
import math
from pathlib import Path
from typing import Any

ORDER_SEND_COUNT = 0
DEFAULT_USD_VND_RATE = 25_500.0


@dataclass
class PropAccountRecord:
    account_id: str
    firm: str
    phase: str  # CHALLENGE_P1 | CHALLENGE_P2 | FUNDED | CLOSED
    nominal_usd: float
    ticket_fee_usd: float
    split_pct: float = 0.80
    status: str = "ACTIVE"


@dataclass
class TreasuryEvent:
    date: str  # YYYY-MM-DD
    event_type: str  # CHALLENGE_FEE | FEE_REFUND | PROP_PAYOUT | OWN_BOOK_DEPOSIT | OWN_BOOK_WITHDRAWAL | OWN_BOOK_PNL | OPS_EXPENSE
    amount_usd: float  # Gross amount (for PROP_PAYOUT: gross profit before split; signed for OWN_BOOK_PNL)
    account_id: str = ""
    firm: str = ""
    split_pct: float = 0.80
    is_hub_credit: bool = False
    note: str = ""


@dataclass
class BucketPolicy:
    reserve_pct: float = 0.30
    own_book_pct: float = 0.50
    ops_tax_pct: float = 0.20
    reserve_cap_tickets: float = 5.0
    reference_ticket_usd: float = 168.0

    def validate(self) -> None:
        total = self.reserve_pct + self.own_book_pct + self.ops_tax_pct
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Bucket policy percentages must sum to 1.0, got {total:.6f}")
        if min(self.reserve_pct, self.own_book_pct, self.ops_tax_pct) < 0.0:
            raise ValueError("Bucket policy percentages must be non-negative")


@dataclass
class TreasuryLedger:
    pod_name: str = "Naqex One-Person Quant Pod"
    usd_vnd_rate: float = DEFAULT_USD_VND_RATE
    policy: BucketPolicy = field(default_factory=BucketPolicy)
    accounts: list[PropAccountRecord] = field(default_factory=list)
    events: list[TreasuryEvent] = field(default_factory=list)

    def add_account(self, account: PropAccountRecord) -> None:
        self.accounts.append(account)

    def add_event(self, event: TreasuryEvent) -> None:
        self.events.append(event)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "naqex-treasury-ledger-v1",
            "pod_name": self.pod_name,
            "usd_vnd_rate": self.usd_vnd_rate,
            "policy": asdict(self.policy),
            "accounts": [asdict(a) for a in self.accounts],
            "events": [asdict(e) for e in self.events],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "TreasuryLedger":
        pol = BucketPolicy(**raw.get("policy", {}))
        pol.validate()
        accs = [PropAccountRecord(**a) for a in raw.get("accounts", [])]
        evs = [TreasuryEvent(**e) for e in raw.get("events", [])]
        return cls(
            pod_name=str(raw.get("pod_name", "Naqex One-Person Quant Pod")),
            usd_vnd_rate=float(raw.get("usd_vnd_rate", DEFAULT_USD_VND_RATE)),
            policy=pol,
            accounts=accs,
            events=evs,
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "TreasuryLedger":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def compute_summary(self) -> dict[str, Any]:
        self.policy.validate()
        ordered = sorted(self.events, key=lambda e: e.date)

        # Reference ticket for 5x reserve cap
        active_tickets = [a.ticket_fee_usd for a in self.accounts if a.ticket_fee_usd > 0]
        ref_ticket = (
            max(active_tickets) if active_tickets else self.policy.reference_ticket_usd
        )
        reserve_cap_usd = self.policy.reserve_cap_tickets * ref_ticket

        total_fees_paid = 0.0
        total_cash_refunds = 0.0
        total_hub_credits = 0.0
        total_gross_prop_profit = 0.0
        total_net_prop_payouts = 0.0
        total_own_deposits = 0.0
        total_own_withdrawals = 0.0
        total_own_pnl = 0.0
        total_ops_expenses = 0.0

        bucket_reserve = 0.0
        bucket_own_seed = 0.0
        bucket_ops_tax = 0.0
        own_book_equity = 0.0

        # Peak out-of-pocket cash drawdown before self-funding
        cum_cash_flow = 0.0
        max_oop_usd = 0.0

        payout_allocations: list[dict[str, Any]] = []
        by_firm: dict[str, dict[str, float]] = defaultdict(
            lambda: {"fees_usd": 0.0, "refunds_cash_usd": 0.0, "hub_credits_usd": 0.0, "net_payouts_usd": 0.0}
        )

        for ev in ordered:
            et = ev.event_type.upper()
            amt = float(ev.amount_usd)
            firm_key = ev.firm or "UNSPECIFIED"

            if et == "CHALLENGE_FEE":
                fee = abs(amt)
                total_fees_paid += fee
                by_firm[firm_key]["fees_usd"] += fee
                # Spend from Challenge Reserve first if funded, else out-of-pocket
                if bucket_reserve >= fee:
                    bucket_reserve -= fee
                else:
                    rem = fee - bucket_reserve
                    bucket_reserve = 0.0
                    cum_cash_flow -= rem
                    max_oop_usd = max(max_oop_usd, -cum_cash_flow)

            elif et == "FEE_REFUND":
                ref = abs(amt)
                if ev.is_hub_credit:
                    total_hub_credits += ref
                    by_firm[firm_key]["hub_credits_usd"] += ref
                else:
                    total_cash_refunds += ref
                    by_firm[firm_key]["refunds_cash_usd"] += ref
                    bucket_reserve += ref
                    cum_cash_flow += ref

            elif et == "PROP_PAYOUT":
                gross = max(0.0, amt)
                split = float(ev.split_pct)
                net = gross * split
                total_gross_prop_profit += gross
                total_net_prop_payouts += net
                by_firm[firm_key]["net_payouts_usd"] += net
                cum_cash_flow += net

                # 3-bucket allocation with reserve cap overflow spilling into Own-Book Seed
                raw_res = net * self.policy.reserve_pct
                raw_own = net * self.policy.own_book_pct
                raw_ops = net * self.policy.ops_tax_pct

                room_in_reserve = max(0.0, reserve_cap_usd - bucket_reserve)
                alloc_res = min(raw_res, room_in_reserve)
                overflow_to_own = raw_res - alloc_res
                alloc_own = raw_own + overflow_to_own
                alloc_ops = raw_ops

                bucket_reserve += alloc_res
                bucket_own_seed += alloc_own
                bucket_ops_tax += alloc_ops
                own_book_equity += alloc_own

                payout_allocations.append({
                    "date": ev.date,
                    "firm": firm_key,
                    "account_id": ev.account_id,
                    "gross_usd": round(gross, 2),
                    "split_pct": round(split * 100.0, 1),
                    "net_usd": round(net, 2),
                    "to_reserve_usd": round(alloc_res, 2),
                    "to_own_book_usd": round(alloc_own, 2),
                    "overflow_to_own_usd": round(overflow_to_own, 2),
                    "to_ops_tax_usd": round(alloc_ops, 2),
                })

            elif et == "OWN_BOOK_DEPOSIT":
                dep = abs(amt)
                total_own_deposits += dep
                own_book_equity += dep
                cum_cash_flow -= dep
                max_oop_usd = max(max_oop_usd, -cum_cash_flow)

            elif et == "OWN_BOOK_WITHDRAWAL":
                wd = abs(amt)
                total_own_withdrawals += wd
                own_book_equity = max(0.0, own_book_equity - wd)
                cum_cash_flow += wd

            elif et == "OWN_BOOK_PNL":
                total_own_pnl += amt
                own_book_equity = max(0.0, own_book_equity + amt)

            elif et == "OPS_EXPENSE":
                exp = abs(amt)
                total_ops_expenses += exp
                bucket_ops_tax -= exp
                cum_cash_flow -= exp

        active_funded = [a for a in self.accounts if a.status == "ACTIVE" and a.phase == "FUNDED"]
        active_prop_nominal_usd = sum(a.nominal_usd for a in active_funded)
        weighted_split = (
            sum(a.nominal_usd * a.split_pct for a in active_funded) / active_prop_nominal_usd
            if active_prop_nominal_usd > 0
            else 0.80
        )

        crossover = compute_prop_own_crossover(
            own_book_equity_usd=own_book_equity,
            active_prop_nominal_usd=active_prop_nominal_usd,
            prop_expected_ann_ret=0.10,
            own_pod_expected_ann_ret=0.22,
            avg_prop_split=weighted_split,
            firm_counterparty_haircut=0.10,
            annual_prop_fees_usd=max(0.0, total_fees_paid - total_cash_refunds),
            usd_vnd_rate=self.usd_vnd_rate,
        )

        net_prop_cash_usd = total_net_prop_payouts + total_cash_refunds - total_fees_paid
        total_liquid_wealth_usd = own_book_equity + bucket_reserve + max(0.0, bucket_ops_tax)

        return {
            "schema": "naqex-treasury-summary-v1",
            "order_send_count": ORDER_SEND_COUNT,
            "pod_name": self.pod_name,
            "usd_vnd_rate": self.usd_vnd_rate,
            "prop_accounting": {
                "active_funded_accounts": len(active_funded),
                "active_prop_nominal_usd": round(active_prop_nominal_usd, 2),
                "weighted_split_pct": round(weighted_split * 100.0, 2),
                "total_fees_paid_usd": round(total_fees_paid, 2),
                "total_cash_refunds_usd": round(total_cash_refunds, 2),
                "total_hub_credits_usd": round(total_hub_credits, 2),
                "total_gross_profit_usd": round(total_gross_prop_profit, 2),
                "total_net_payouts_usd": round(total_net_prop_payouts, 2),
                "net_prop_cashflow_usd": round(net_prop_cash_usd, 2),
                "max_out_of_pocket_usd": round(max_oop_usd, 2),
                "by_firm": {
                    k: {mk: round(mv, 2) for mk, mv in v.items()}
                    for k, v in sorted(by_firm.items())
                },
            },
            "buckets": {
                "challenge_reserve_usd": round(bucket_reserve, 2),
                "challenge_reserve_cap_usd": round(reserve_cap_usd, 2),
                "reserve_fill_pct": round(
                    100.0 * min(1.0, bucket_reserve / max(1.0, reserve_cap_usd)), 1
                ),
                "own_book_seed_from_prop_usd": round(bucket_own_seed, 2),
                "ops_tax_provision_usd": round(bucket_ops_tax, 2),
                "ops_expenses_paid_usd": round(total_ops_expenses, 2),
            },
            "own_book": {
                "equity_usd": round(own_book_equity, 2),
                "equity_vnd": round(own_book_equity * self.usd_vnd_rate, 0),
                "direct_deposits_usd": round(total_own_deposits, 2),
                "withdrawals_usd": round(total_own_withdrawals, 2),
                "realized_pnl_usd": round(total_own_pnl, 2),
                "total_liquid_wealth_usd": round(total_liquid_wealth_usd, 2),
                "total_liquid_wealth_vnd": round(total_liquid_wealth_usd * self.usd_vnd_rate, 0),
            },
            "crossover": crossover,
            "payout_allocations": payout_allocations,
        }


@dataclass
class SettledCashEvent:
    """Round-3 Settled-Cash Ledger event (strictly separates out-of-pocket, receivable, settled cash & hub credit)."""

    date: str  # YYYY-MM-DD (event / request date)
    event_type: str  # OUT_OF_POCKET_FEE | OPS_CASH_OUT | HUB_CREDIT_GRANT | PAYOUT_APPROVED | PAYOUT_SETTLED | EXTERNAL_CASH_REFUND | TAX_PAID
    amount_usd: float
    account_id: str = ""
    firm: str = ""
    settled_date: str = ""  # YYYY-MM-DD when cash actually lands in bank/wallet
    withdrawal_fee_usd: float = 0.0
    fx_bank_fee_usd: float = 0.0
    operator_hours: float = 0.0
    cycle_id: str = ""
    note: str = ""


def compute_settled_cash_summary(
    events: list[SettledCashEvent],
    *,
    as_of_date: str | None = None,
    required_next_ticket_fee_usd: float = 168.0,
    required_buffer_tickets: float = 2.0,
    usd_vnd_rate: float = DEFAULT_USD_VND_RATE,
) -> dict[str, Any]:
    """Audit real settled cashflow per Astra Round-3 blueprint (replaces premature 30/50/20 & Gate-42)."""
    ordered = sorted(events, key=lambda e: (e.date, e.settled_date or e.date))
    out_of_pocket_usd = 0.0
    ops_and_tax_paid_usd = 0.0
    hub_credits_usd = 0.0
    external_cash_refunds_usd = 0.0
    receivable_payouts_usd = 0.0
    settled_payouts_net_usd = 0.0
    total_withdrawal_and_fx_fees_usd = 0.0
    total_operator_hours = 0.0
    settled_positive_cycles: set[str] = set()
    peak_out_of_pocket_usd = 0.0
    running_cash_balance_usd = 0.0

    for ev in ordered:
        et = ev.event_type.upper()
        amt = max(0.0, float(ev.amount_usd))
        total_operator_hours += max(0.0, float(ev.operator_hours))
        is_settled_by_cutoff = (as_of_date is None) or ((ev.settled_date or ev.date) <= as_of_date)

        if et == "OUT_OF_POCKET_FEE":
            out_of_pocket_usd += amt
            running_cash_balance_usd -= amt
            peak_out_of_pocket_usd = max(peak_out_of_pocket_usd, -running_cash_balance_usd)
        elif et in ("OPS_CASH_OUT", "TAX_PAID"):
            ops_and_tax_paid_usd += amt
            out_of_pocket_usd += amt
            running_cash_balance_usd -= amt
            peak_out_of_pocket_usd = max(peak_out_of_pocket_usd, -running_cash_balance_usd)
        elif et == "HUB_CREDIT_GRANT":
            # Non-withdrawable firm credit — NEVER counts as settled cash or principal recovery!
            hub_credits_usd += amt
        elif et == "EXTERNAL_CASH_REFUND":
            if is_settled_by_cutoff:
                external_cash_refunds_usd += amt
                running_cash_balance_usd += amt
            else:
                receivable_payouts_usd += amt
        elif et == "PAYOUT_APPROVED":
            # Approved but not yet landed — strictly receivable, earns 0 yield until settled!
            net_after_fees = max(0.0, amt - max(0.0, ev.withdrawal_fee_usd) - max(0.0, ev.fx_bank_fee_usd))
            receivable_payouts_usd += net_after_fees
        elif et == "PAYOUT_SETTLED":
            fees = max(0.0, float(ev.withdrawal_fee_usd)) + max(0.0, float(ev.fx_bank_fee_usd))
            total_withdrawal_and_fx_fees_usd += fees
            net_landed = max(0.0, amt - fees)
            if is_settled_by_cutoff:
                settled_payouts_net_usd += net_landed
                running_cash_balance_usd += net_landed
                if net_landed > 0.0:
                    settled_positive_cycles.add(ev.cycle_id or f"{ev.firm}:{ev.date}")
            else:
                receivable_payouts_usd += net_landed

    total_settled_inflows_usd = settled_payouts_net_usd + external_cash_refunds_usd
    net_settled_cash_usd = total_settled_inflows_usd - out_of_pocket_usd
    principal_recovered = (out_of_pocket_usd > 0.0 and net_settled_cash_usd >= 0.0) or (
        out_of_pocket_usd == 0.0 and total_settled_inflows_usd > 0.0
    )
    principal_shortfall_usd = max(0.0, out_of_pocket_usd - total_settled_inflows_usd)
    required_reserve_usd = max(0.0, required_next_ticket_fee_usd * required_buffer_tickets)
    allocatable_surplus_usd = max(0.0, net_settled_cash_usd - required_reserve_usd) if principal_recovered else 0.0

    # Astra Round-3 stage promotion gate:
    # >= 2 distinct positive settled payout cycles + principal recovered + surplus >= 2x next ticket fee
    stage_promotion_ready = (
        len(settled_positive_cycles) >= 2
        and principal_recovered
        and net_settled_cash_usd >= required_reserve_usd
    )

    return {
        "schema": "naqex-settled-cash-ledger-v2",
        "order_send_count": ORDER_SEND_COUNT,
        "as_of_date": as_of_date,
        "out_of_pocket_paid_usd": round(out_of_pocket_usd, 2),
        "ops_and_tax_paid_usd": round(ops_and_tax_paid_usd, 2),
        "peak_out_of_pocket_usd": round(peak_out_of_pocket_usd, 2),
        "hub_credits_non_withdrawable_usd": round(hub_credits_usd, 2),
        "receivable_unsettled_usd": round(receivable_payouts_usd, 2),
        "external_cash_refunds_settled_usd": round(external_cash_refunds_usd, 2),
        "settled_payouts_net_usd": round(settled_payouts_net_usd, 2),
        "withdrawal_and_fx_fees_usd": round(total_withdrawal_and_fx_fees_usd, 2),
        "net_settled_cash_usd": round(net_settled_cash_usd, 2),
        "net_settled_cash_vnd": round(net_settled_cash_usd * usd_vnd_rate, 0),
        "principal_recovered": principal_recovered,
        "principal_shortfall_usd": round(principal_shortfall_usd, 2),
        "required_reserve_buffer_usd": round(required_reserve_usd, 2),
        "allocatable_surplus_usd": round(allocatable_surplus_usd, 2),
        "settled_positive_cycles": len(settled_positive_cycles),
        "operator_hours_logged": round(total_operator_hours, 2),
        "stage_promotion_ready": stage_promotion_ready,
    }


def compute_prop_own_crossover(
    *,
    own_book_equity_usd: float,
    active_prop_nominal_usd: float,
    prop_expected_ann_ret: float = 0.10,
    own_pod_expected_ann_ret: float = 0.22,
    avg_prop_split: float = 0.80,
    firm_counterparty_haircut: float = 0.10,
    annual_prop_fees_usd: float = 210.0,
    usd_vnd_rate: float = DEFAULT_USD_VND_RATE,
) -> dict[str, Any]:
    """Exact math comparing expected annual net USD from Prop Firm vs Own-Book Multi-Sleeve Quant Pod."""
    prop_net_annual_usd = (
        active_prop_nominal_usd
        * prop_expected_ann_ret
        * avg_prop_split
        * (1.0 - firm_counterparty_haircut)
        - annual_prop_fees_usd
    )
    own_net_annual_usd = own_book_equity_usd * own_pod_expected_ann_ret
    denom = max(1e-6, own_pod_expected_ann_ret)
    crossover_equity_usd = max(0.0, prop_net_annual_usd / denom)
    if crossover_equity_usd <= 1e-6:
        progress_pct = 100.0 if own_book_equity_usd > 0 else 0.0
    else:
        progress_pct = min(100.0, 100.0 * own_book_equity_usd / crossover_equity_usd)

    own_beats_prop = own_net_annual_usd >= prop_net_annual_usd and own_book_equity_usd > 0
    if own_book_equity_usd >= 50_000.0 and own_beats_prop:
        phase = "PHASE_4_OWN_BOOK_DOMINANT"
    elif own_book_equity_usd >= 25_000.0 or (active_prop_nominal_usd >= 100_000.0 and own_book_equity_usd >= 10_000.0):
        phase = "PHASE_3_HYBRID_BARBELL"
    elif active_prop_nominal_usd >= 10_000.0:
        phase = "PHASE_2_MULTI_PROP_SCALING"
    else:
        phase = "PHASE_1_MICRO_LIVE_PROOF"

    return {
        "own_book_equity_usd": round(own_book_equity_usd, 2),
        "own_book_equity_vnd": round(own_book_equity_usd * usd_vnd_rate, 0),
        "active_prop_nominal_usd": round(active_prop_nominal_usd, 2),
        "expected_prop_net_annual_usd": round(prop_net_annual_usd, 2),
        "expected_own_net_annual_usd": round(own_net_annual_usd, 2),
        "crossover_equity_usd": round(crossover_equity_usd, 2),
        "crossover_equity_vnd": round(crossover_equity_usd * usd_vnd_rate, 0),
        "crossover_progress_pct": round(progress_pct, 1),
        "own_book_beats_prop": own_beats_prop,
        "recommended_phase": phase,
    }


def compute_gips_monthly_stats(monthly_returns: dict[str, float]) -> dict[str, Any]:
    """Compute GIPS-lite Time-Weighted Return (TWR) stats from `YYYY-MM -> float` decimal return map."""
    if not monthly_returns:
        return {
            "months": 0,
            "cumulative_pct": 0.0,
            "cagr_pct": 0.0,
            "ann_vol_pct": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_dd_pct": 0.0,
            "calmar": 0.0,
            "win_month_pct": 0.0,
            "best_month_pct": 0.0,
            "worst_month_pct": 0.0,
            "calendar_table": {},
        }

    ordered_keys = sorted(monthly_returns.keys())
    vals = [float(monthly_returns[k]) for k in ordered_keys]
    n = len(vals)

    eq = 1.0
    peak = 1.0
    max_dd = 0.0
    by_year: dict[str, dict[int, float]] = defaultdict(dict)
    for ym, r in zip(ordered_keys, vals):
        eq *= (1.0 + r)
        peak = max(peak, eq)
        dd = (peak - eq) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
        parts = ym.split("-")
        by_year[parts[0]][int(parts[1])] = r

    cum = eq - 1.0
    yrs = n / 12.0
    cagr = (eq ** (1.0 / max(1e-6, yrs))) - 1.0 if eq > 0 else -1.0
    mean_m = sum(vals) / n
    if n >= 2:
        var_m = sum((x - mean_m) ** 2 for x in vals) / (n - 1)
        sd_m = math.sqrt(max(0.0, var_m))
    else:
        sd_m = 0.0
    ann_vol = sd_m * math.sqrt(12.0)
    sharpe = (mean_m / sd_m) * math.sqrt(12.0) if sd_m > 1e-12 else 0.0
    downside = [min(0.0, x) for x in vals]
    down_rms = math.sqrt(sum(d * d for d in downside) / n)
    sortino = (mean_m / down_rms) * math.sqrt(12.0) if down_rms > 1e-12 else 0.0
    calmar = cagr / max_dd if max_dd > 1e-9 else 0.0
    win_pct = 100.0 * sum(1 for x in vals if x > 0.0) / n

    calendar_table: dict[str, dict[str, float | None]] = {}
    for yr in sorted(by_year.keys()):
        row: dict[str, float | None] = {}
        ytd_factor = 1.0
        for m in range(1, 13):
            if m in by_year[yr]:
                rm = by_year[yr][m]
                row[f"{m:02d}"] = round(rm * 100.0, 2)
                ytd_factor *= (1.0 + rm)
            else:
                row[f"{m:02d}"] = None
        row["YTD"] = round((ytd_factor - 1.0) * 100.0, 2)
        calendar_table[yr] = row

    return {
        "months": n,
        "start_month": ordered_keys[0],
        "end_month": ordered_keys[-1],
        "cumulative_pct": round(cum * 100.0, 2),
        "cagr_pct": round(cagr * 100.0, 2),
        "ann_vol_pct": round(ann_vol * 100.0, 2),
        "sharpe": round(sharpe, 2),
        "sortino": round(sortino, 2),
        "max_dd_pct": round(max_dd * 100.0, 2),
        "calmar": round(calmar, 2),
        "win_month_pct": round(win_pct, 1),
        "best_month_pct": round(max(vals) * 100.0, 2),
        "worst_month_pct": round(min(vals) * 100.0, 2),
        "calendar_table": calendar_table,
    }


def daily_returns_to_monthly(daily_returns: dict[str, float]) -> dict[str, float]:
    """Compound `YYYY-MM-DD -> float` daily returns into exact `YYYY-MM -> float` monthly TWR."""
    factors: dict[str, float] = defaultdict(lambda: 1.0)
    for dk in sorted(daily_returns.keys()):
        r = float(daily_returns[dk])
        if math.isfinite(r):
            factors[dk[:7]] *= (1.0 + r)
    return {ym: f - 1.0 for ym, f in sorted(factors.items())}


def generate_gips_factsheet_md(
    ledger: TreasuryLedger,
    monthly_returns: dict[str, float],
    *,
    return_provenance: str = "SIMULATED_DEV_SEALED_NOT_LIVE_GIPS",
    as_of_utc: str | None = None,
) -> str:
    """Render a clean GIPS-lite Monthly Fact Sheet in Markdown (zero bare `$` pairs in prose)."""
    ts = as_of_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summ = ledger.compute_summary()
    stats = compute_gips_monthly_stats(monthly_returns)
    prop = summ["prop_accounting"]
    bkt = summ["buckets"]
    own = summ["own_book"]
    xo = summ["crossover"]

    lines = [
        f"# {ledger.pod_name} — GIPS-Lite Monthly Fact Sheet",
        "",
        f"- **As-Of UTC:** `{ts}` · **Provenance Tag:** `{return_provenance}` · **OrderSend:** `{ORDER_SEND_COUNT}`",
        f"- **Reporting Currency:** `USD` (Quy đổi tham chiếu `1 USD = {ledger.usd_vnd_rate:,.0f} VND`)",
        f"- **Window:** `{stats.get('start_month', 'N/A')} .. {stats.get('end_month', 'N/A')}` (`{stats['months']}` tháng)",
        "",
        "> **Tuyên bố Minh bạch (GIPS-Lite Compliance Disclosure):** Báo cáo tách bạch hoàn toàn giữa hiệu suất mô phỏng/backtest (`SIMULATED_*`) và kết quả giao dịch tiền thật (`LIVE_VERIFIED`). Không bao giờ ghép chung lợi suất mô phỏng vào chuỗi live. Mọi lợi suất tính theo Time-Weighted Return (TWR) ròng sau chi phí ước tính, lãi suất tiền mặt nhàn rỗi `0%` bảo thủ.",
        "",
        "## 1. Chỉ số Hiệu suất Chính (TWR — Ròng Sau Phí)",
        "",
        "| Chỉ số | Giá trị | Chỉ số | Giá trị |",
        "|---|---:|---|---:|",
        f"| Tổng lợi suất tích lũy (ITD) | `{stats['cumulative_pct']:+.2f}%` | Tỷ lệ tháng dương | `{stats['win_month_pct']:.1f}%` |",
        f"| Lợi suất kép năm (CAGR) | `{stats['cagr_pct']:+.2f}%` | Tháng tốt nhất | `{stats['best_month_pct']:+.2f}%` |",
        f"| Biến động năm (Ann Vol) | `{stats['ann_vol_pct']:.2f}%` | Tháng xấu nhất | `{stats['worst_month_pct']:+.2f}%` |",
        f"| Sharpe Ratio (`Rf = 0%`) | `{stats['sharpe']:.2f}` | Max Drawdown (tháng) | `{stats['max_dd_pct']:.2f}%` |",
        f"| Sortino Ratio | `{stats['sortino']:.2f}` | Calmar Ratio | `{stats['calmar']:.2f}` |",
        "",
        "## 2. Bảng Lợi suất Theo Tháng (Calendar TWR `%`)",
        "",
        "| Năm | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 | T9 | T10 | T11 | T12 | **YTD** |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for yr, row in sorted(stats["calendar_table"].items()):
        cells = []
        for m in range(1, 13):
            v = row[f"{m:02d}"]
            cells.append("—" if v is None else f"{v:+.2f}%")
        ytd_v = row["YTD"]
        ytd_str = f"**{ytd_v:+.2f}%**" if ytd_v is not None else "—"
        lines.append(f"| `{yr}` | " + " | ".join(cells) + f" | {ytd_str} |")

    lines.extend([
        "",
        "## 3. Ngân quỹ Đa Quỹ, Dự phòng 3 Ngăn & Điểm Giao Cắt Vốn Riêng",
        "",
        "| Hạng mục Ngân quỹ | Giá trị (`USD`) | Quy đổi (`VND`) | Ghi chú |",
        "|---|---:|---:|---|",
        f"| Tổng danh nghĩa Prop đang Funded | `{prop['active_prop_nominal_usd']:,.2f} USD` | `{prop['active_prop_nominal_usd'] * ledger.usd_vnd_rate:,.0f} VND` | `{prop['active_funded_accounts']}` tài khoản, chia TB `{prop['weighted_split_pct']:.1f}%` |",
        f"| Phí thi đã trả / Hoàn phí tiền mặt | `{prop['total_fees_paid_usd']:,.2f} / {prop['total_cash_refunds_usd']:,.2f} USD` | — | Hub Credit không rút: `{prop['total_hub_credits_usd']:,.2f} USD` |",
        f"| Tổng Payout ròng nhận về (sau chia) | `{prop['total_net_payouts_usd']:,.2f} USD` | `{prop['total_net_payouts_usd'] * ledger.usd_vnd_rate:,.0f} VND` | Vốn túi đỉnh (`Max OOP`): `{prop['max_out_of_pocket_usd']:,.2f} USD` |",
        f"| Ngăn 1 — Quỹ Đệm Thi Quỹ (`Reserve`) | `{bkt['challenge_reserve_usd']:,.2f} USD` | `{bkt['challenge_reserve_usd'] * ledger.usd_vnd_rate:,.0f} VND` | Đầy `{bkt['reserve_fill_pct']:.1f}%` trần `{bkt['challenge_reserve_cap_usd']:,.2f} USD` |",
        f"| Ngăn 2 — Sổ Vốn Riêng (`Own Book`) | `{own['equity_usd']:,.2f} USD` | `{own['equity_vnd']:,.0f} VND` | Gốc từ Prop: `{bkt['own_book_seed_from_prop_usd']:,.2f} USD`, PnL: `{own['realized_pnl_usd']:+,.2f} USD` |",
        f"| Ngăn 3 — Dự phòng Hạ tầng & Thuế | `{bkt['ops_tax_provision_usd']:,.2f} USD` | `{bkt['ops_tax_provision_usd'] * ledger.usd_vnd_rate:,.0f} VND` | Đã chi Ops: `{bkt['ops_expenses_paid_usd']:,.2f} USD` |",
        f"| **Điểm giao cắt Own-Book > Prop** | **`{xo['crossover_equity_usd']:,.2f} USD`** | **`{xo['crossover_equity_vnd']:,.0f} VND`** | Tiến độ: **`{xo['crossover_progress_pct']:.1f}%`** (`{xo['recommended_phase']}`) |",
        "",
    ])
    return "\n".join(lines)


def generate_gips_factsheet_html(
    ledger: TreasuryLedger,
    monthly_returns: dict[str, float],
    *,
    return_provenance: str = "SIMULATED_DEV_SEALED_NOT_LIVE_GIPS",
    as_of_utc: str | None = None,
) -> str:
    """Render a self-contained flat-dark institutional GIPS-lite Monthly Fact Sheet HTML (zero external CDNs)."""
    ts = as_of_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summ = ledger.compute_summary()
    stats = compute_gips_monthly_stats(monthly_returns)
    prop = summ["prop_accounting"]
    bkt = summ["buckets"]
    own = summ["own_book"]
    xo = summ["crossover"]

    esc = html.escape
    month_rows = []
    for yr, row in sorted(stats["calendar_table"].items()):
        tds = [f"<td class='mono'>{esc(yr)}</td>"]
        for m in range(1, 13):
            v = row[f"{m:02d}"]
            if v is None:
                tds.append("<td class='muted'>—</td>")
            else:
                cls = "pos" if v >= 0 else "neg"
                tds.append(f"<td class='mono {cls}'>{v:+.2f}%</td>")
        ytd = row["YTD"]
        ycls = "pos" if (ytd or 0.0) >= 0 else "neg"
        tds.append(f"<td class='mono strong {ycls}'>{(f'{ytd:+.2f}%' if ytd is not None else '—')}</td>")
        month_rows.append("<tr>" + "".join(tds) + "</tr>")

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(ledger.pod_name)} — GIPS-Lite Monthly Fact Sheet</title>
<style>
  :root {{ --bg:#0b0f17; --surf:#121824; --line:#222938; --txt:#e5e7eb; --muted:#9ca3af; --pos:#16c784; --neg:#ef4444; --acc:#3b82f6; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:24px; background:var(--bg); color:var(--txt); font:14px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }}
  .wrap {{ max-width:1120px; margin:0 auto; }}
  header {{ border-bottom:1px solid var(--line); padding-bottom:14px; margin-bottom:18px; display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:12px; }}
  h1 {{ margin:0; font-size:20px; letter-spacing:-0.01em; }}
  .meta {{ color:var(--muted); font-size:12px; }}
  .badge {{ display:inline-block; padding:2px 8px; border:1px solid var(--line); background:var(--surf); font-size:11px; color:var(--acc); font-family:Consolas,monospace; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(175px,1fr)); gap:10px; margin-bottom:18px; }}
  .kpi {{ background:var(--surf); border:1px solid var(--line); padding:12px; }}
  .kpi .lbl {{ color:var(--muted); font-size:11px; text-transform:uppercase; }}
  .kpi .val {{ font-size:20px; font-weight:600; margin-top:4px; font-variant-numeric:tabular-nums; font-family:Consolas,monospace; }}
  section {{ background:var(--surf); border:1px solid var(--line); padding:16px; margin-bottom:16px; }}
  h2 {{ margin:0 0 12px; font-size:14px; text-transform:uppercase; letter-spacing:0.04em; color:var(--muted); }}
  table {{ width:100%; border-collapse:collapse; font-size:12.5px; }}
  th, td {{ border-bottom:1px solid var(--line); padding:7px 8px; text-align:right; }}
  th:first-child, td:first-child {{ text-align:left; }}
  th {{ color:var(--muted); font-weight:500; }}
  .mono {{ font-family:Consolas,monospace; font-variant-numeric:tabular-nums; }}
  .pos {{ color:var(--pos); }}
  .neg {{ color:var(--neg); }}
  .muted {{ color:var(--muted); }}
  .strong {{ font-weight:700; }}
  .disc {{ font-size:12px; color:var(--muted); border-left:3px solid var(--acc); padding-left:12px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>{esc(ledger.pod_name)} — GIPS-Lite Monthly Fact Sheet</h1>
      <div class="meta">As-Of UTC: {esc(ts)} · Window: {esc(str(stats.get('start_month','N/A')))} .. {esc(str(stats.get('end_month','N/A')))} ({stats['months']} tháng)</div>
    </div>
    <div><span class="badge">{esc(return_provenance)}</span> <span class="badge">OrderSend={ORDER_SEND_COUNT}</span></div>
  </header>

  <div class="grid">
    <div class="kpi"><div class="lbl">CAGR (TWR)</div><div class="val {'pos' if stats['cagr_pct'] >= 0 else 'neg'}">{stats['cagr_pct']:+.2f}%</div></div>
    <div class="kpi"><div class="lbl">Sharpe (Rf=0%)</div><div class="val">{stats['sharpe']:.2f}</div></div>
    <div class="kpi"><div class="lbl">Max Drawdown</div><div class="val neg">-{stats['max_dd_pct']:.2f}%</div></div>
    <div class="kpi"><div class="lbl">Calmar Ratio</div><div class="val">{stats['calmar']:.2f}</div></div>
    <div class="kpi"><div class="lbl">Own Book Equity</div><div class="val">{own['equity_usd']:,.0f} USD</div></div>
    <div class="kpi"><div class="lbl">Crossover Progress</div><div class="val">{xo['crossover_progress_pct']:.1f}%</div></div>
  </div>

  <section>
    <h2>Calendar Monthly Returns (TWR %)</h2>
    <table>
      <thead><tr><th>Year</th><th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th><th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th><th>YTD</th></tr></thead>
      <tbody>{''.join(month_rows)}</tbody>
    </table>
  </section>

  <section>
    <h2>Treasury &amp; Prop-to-Own-Book Crossover</h2>
    <table>
      <thead><tr><th>Line Item</th><th>USD</th><th>VND ({ledger.usd_vnd_rate:,.0f})</th><th>Notes</th></tr></thead>
      <tbody>
        <tr><td>Active Funded Prop Nominal</td><td class="mono">{prop['active_prop_nominal_usd']:,.2f} USD</td><td class="mono">{prop['active_prop_nominal_usd']*ledger.usd_vnd_rate:,.0f} VND</td><td>{prop['active_funded_accounts']} accts · avg split {prop['weighted_split_pct']:.1f}%</td></tr>
        <tr><td>Challenge Reserve (Bucket 1)</td><td class="mono">{bkt['challenge_reserve_usd']:,.2f} USD</td><td class="mono">{bkt['challenge_reserve_usd']*ledger.usd_vnd_rate:,.0f} VND</td><td>{bkt['reserve_fill_pct']:.1f}% of {bkt['challenge_reserve_cap_usd']:,.0f} USD cap</td></tr>
        <tr><td>Own Book Equity (Bucket 2)</td><td class="mono">{own['equity_usd']:,.2f} USD</td><td class="mono">{own['equity_vnd']:,.0f} VND</td><td>Seed from prop: {bkt['own_book_seed_from_prop_usd']:,.2f} USD</td></tr>
        <tr><td>Ops &amp; Tax Provision (Bucket 3)</td><td class="mono">{bkt['ops_tax_provision_usd']:,.2f} USD</td><td class="mono">{bkt['ops_tax_provision_usd']*ledger.usd_vnd_rate:,.0f} VND</td><td>Ops paid: {bkt['ops_expenses_paid_usd']:,.2f} USD</td></tr>
        <tr><td>Crossover Threshold (Own &gt; Prop)</td><td class="mono strong">{xo['crossover_equity_usd']:,.2f} USD</td><td class="mono strong">{xo['crossover_equity_vnd']:,.0f} VND</td><td>{esc(xo['recommended_phase'])}</td></tr>
      </tbody>
    </table>
  </section>

  <div class="disc">
    <strong>GIPS-Lite Provenance Disclosure:</strong> Return stream tagged <code>{esc(return_provenance)}</code>. Simulated/backtest series are strictly segregated from audited live brokerage/prop statements. Idle cash earns 0% conservative return. OrderSend=0.
  </div>
</div>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Naqex Treasury Ledger & GIPS-Lite Fact Sheet CLI")
    ap.add_argument("--ledger", type=Path, help="Path to treasury ledger JSON")
    ap.add_argument("--export-md", type=Path, help="Optional Markdown fact sheet output path")
    ap.add_argument("--export-html", type=Path, help="Optional HTML fact sheet output path")
    args = ap.parse_args()

    ledger = TreasuryLedger.load(args.ledger) if args.ledger and args.ledger.exists() else TreasuryLedger()
    summary = ledger.compute_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.export_md:
        args.export_md.parent.mkdir(parents=True, exist_ok=True)
        args.export_md.write_text(generate_gips_factsheet_md(ledger, {}), encoding="utf-8", newline="\n")
    if args.export_html:
        args.export_html.parent.mkdir(parents=True, exist_ok=True)
        args.export_html.write_text(generate_gips_factsheet_html(ledger, {}), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
