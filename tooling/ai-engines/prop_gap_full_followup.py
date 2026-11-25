"""Recover one scoped archive interval and measure frozen phase-one cash sensitivity."""
from decimal import Decimal

from prop_gap_full_dev import BASE, N1, PROTOCOL, WORKSPACE, compare_month, month_at
from prop_gap_source_sensitivity import quote_pnl_cents
from prop_n1_screen import verify_commit
from prop_phase1_shortfall import PHASE1_TARGET_CENTS, anniversary, cents, trade_lookup
from prop_v15_evidence import bars_for
from prop_v21_common import compressed, unpack
from prop_v26_common import DEV_END, FIRST, ROOT, V19, read, sha
from quant_core.job_workspace import JobWorkspace
from quant_core.prop_lifecycle_and_parity import bindings
import prop_v21_common as evidence
from pathlib import Path

OCTOBER = ('XAUUSD', '202310')
OCTOBER_SHA = 'dc29013c1f8403d0763de0b5a7462e57eb347b5095c12663da2defb389d58d76'
LATER_CLOCK_REVERSAL = ('20231029 195959701', '20231029 190000076')


def recover(folder):
    path = folder / 'HistData-XAUUSD-202310.zip'
    if sha(path) != OCTOBER_SHA:
        raise ValueError('HISTDATA_OCTOBER_CHANGED')
    rank = next(N1.glob('gaps/*/gap-ranking-manifest.json'))
    with bindings(evidence, JOB=rank.parent):
        gaps = [g for g in unpack('gap-ranking')['gaps'] if (g['asset'], month_at(g['first_unknown'])) == OCTOBER]
    if len(gaps) != 1:
        raise ValueError('HISTDATA_OCTOBER_SCOPE_CHANGED')
    base, strict = ({(t['asset'], t['entry_msc']): t for t in read(V19 / f'Dev-OLHC-{mode}-trades.json')}
                    for mode in ('PRIMARY', 'STRICT'))
    stops = {(r['asset'], r['before'], r['after'], r['id'], r['entry']): r for r in read(V19/'gap-identities.json')['rows']
             if FIRST <= r['first_unknown'] < DEV_END}
    return compare_month(OCTOBER, gaps, path, base, strict, stops, bars_for('XAUUSD', True),
                         outside_order_exception=LATER_CLOCK_REVERSAL)


def reference_failures(view, alternate):
    saved = next((ROOT / 'prop-phase1-shortfall-20261118').glob('*/phase1-windows-manifest.json'))
    with bindings(evidence, JOB=saved.parent):
        windows = unpack('phase1-windows')['cases'][f'OLHC-{view}-100']
    expected = {r['start']: r for r in windows if not r['phase1']}
    path = V19 / f'Dev-OLHC-{view}-100-accounts.json'
    audit = read(V19 / f'Dev-OLHC-{view}-100-audit.json')
    if not audit['passed'] or audit['binding']['accounts'] != sha(path):
        raise ValueError('PHASE1_SENSITIVITY_ORIGINAL_LEDGER_CHANGED')
    lookup = trade_lookup(read(V19 / 'Dev-pack' / f'OLHC-{view}-blocks.json')['blocks'])
    result = []
    for account in read(path):
        start = account['start_msc']
        if account['profile'] != 'BASE_GUARD' or account['kind'] != 'CHALLENGE' or start not in expected:
            continue
        end = anniversary(start)
        accepted = {row['trade']: row['quantity_steps'] for row in account['accepted'] if row['at'] < end}
        closed = {row['trade']: cents(row['net_usd']) for row in account['closed'] if row['phase'] == 1 and row['at'] < end}
        old = expected[start]['phase1_balance_cents']
        if accepted.keys() != closed.keys() or old != 5_000_000 + sum(closed.values()):
            raise ValueError('PHASE1_SENSITIVITY_CASH_MISMATCH')
        delta, repriced = 0, 0
        for index, pnl in closed.items():
            entry, _, family = lookup[index]
            asset = family.split()[0]
            x = alternate.get((asset, entry))
            if x is None:
                continue
            repriced += 1
            adjusted = quote_pnl_cents(asset, x['side'], accepted[index], Decimal(x['entry_price']), Decimal(x['exit_price']))
            delta += adjusted - pnl
        result.append(dict(start=start, repriced=repriced, initial_cents=old, delta_cents=delta,
                           original_deficit_cents=PHASE1_TARGET_CENTS-old,
                           conditional_deficit_cents=max(0, PHASE1_TARGET_CENTS-old-delta)))
    if len(result) != len(expected):
        raise ValueError('PHASE1_SENSITIVITY_COHORT_MISMATCH')
    return result


def main():
    verify_commit(PROTOCOL)
    verify_commit(__file__)
    manifest = next(BASE.glob('*/full-sensitivity-manifest.json'))
    with bindings(evidence, JOB=manifest.parent):
        original = unpack('full-sensitivity')
    additional = recover(manifest.parent)
    alternate = {(r['asset'], r['entry']): r for r in original['paths'] if r['net_cents'] is not None}
    # October is a P1 gap-only observation, so the matched P0 account cohort is unchanged.
    if len(additional['paths']) != 1 or additional['paths'][0]['status'] != 'P1_GAP_ONLY':
        raise ValueError('PHASE1_SENSITIVITY_RECOVERY_UNEXPECTED_MODEL')
    runtime = JobWorkspace(BASE / 'followup', WORKSPACE)
    output = runtime.activate()
    try:
        with bindings(evidence, JOB=output):
            compressed('source-followup', dict(recovered=additional, archive_sha256=OCTOBER_SHA,
                       excluded_later_clock_reversal=LATER_CLOCK_REVERSAL,
                       cash_windows={view: reference_failures(view, alternate) for view in ('PRIMARY', 'STRICT')},
                       initial_manifest=sha(manifest), protocol_sha256=sha(PROTOCOL), code_sha256=sha(Path(__file__))))
        print(output, flush=True)
    finally:
        runtime.close()


if __name__ == '__main__':
    main()
