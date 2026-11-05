"""Read-only dossier for the registered Forex development artifact format.

Checks local artifact invariants, not statistical qualification, trusted
attestation or broker authority. No provider, database or trading calls.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'projects/trader/foundation_v2'))
from trading_workspace_v2.forex_study_registration import (
    HISTORICAL_SCHEMA, HISTORICAL_PURPOSE, inspect_registered_manifest,
)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def status(run_dir: Path, *, stale_seconds=120, now=None):
    if stale_seconds <= 0:
        raise ValueError('stale threshold must be positive')
    receipt = read_json(run_dir / 'receipt.json')
    updated = datetime.fromisoformat(receipt['updated_at_utc'])
    if updated.tzinfo is None:
        raise ValueError('receipt timestamp requires a timezone')
    now = now or datetime.now(timezone.utc)
    age = (now-updated).total_seconds()
    if age < -5:
        raise ValueError('receipt timestamp is ahead of observer clock')
    stage = receipt['stage']
    terminal = stage in {'completed_declared_scenarios', 'preflight_passed_no_simulation', 'failed'}
    return dict(schema='strategy-run-status-v1', run_dir=str(run_dir.resolve()),
        run_id=receipt.get('run_id'), pid=receipt.get('pid'), candidate=receipt.get('candidate'),
        stage=stage, terminal=terminal, last_progress_age_seconds=max(0,round(age,3)),
        health='terminal_reported' if terminal else 'stale_progress_process_state_unknown' if age > stale_seconds else 'recent_progress',
        process_liveness_verified=False, execution_capability=False,
        observed_ticks=receipt.get('observed_ticks'), cursor_index=receipt.get('cursor_index'),
        boundary_utc=receipt.get('boundary_utc'), elapsed_seconds=receipt.get('elapsed_seconds'),
        failed_stage=receipt.get('failed_stage'), error_type=receipt.get('error_type'),
        receipt_path=str(run_dir/'receipt.json'), event_log_path=str(run_dir/'events.jsonl'),
        failure_path=str(run_dir/'failure.json') if (run_dir/'failure.json').is_file() else None,
        cli_resume_supported=False)


def finite(value):
    if isinstance(value, bool):
        raise ValueError('boolean is not a financial amount')
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError('financial amount must be decimal') from error
    if not result.is_finite():
        raise ValueError('financial amount must be finite')
    return result


def inspect(run_dir: Path, *, verify_inputs=False, source_root: Path | None = None):
    run_dir = run_dir.resolve()
    manifest = read_json(run_dir / 'manifest.json')
    receipt = read_json(run_dir / 'receipt.json')
    results = read_json(run_dir / 'results.json')
    quality = read_json(run_dir / 'quality.json')
    historical = manifest.get('schema') == HISTORICAL_SCHEMA
    if ((manifest.get('schema'), manifest.get('purpose')) not in {
                ('forex-h4-development-v1', 'registered_development_not_qualification'),
                (HISTORICAL_SCHEMA, HISTORICAL_PURPOSE)}
            or not isinstance(manifest.get('candidate'), str) or not manifest['candidate']
            or manifest.get('validation_holdout_read') is not False
            or manifest.get('broker_connected') is not False
            or manifest.get('execution_mode') == 'preflight_only_no_simulation'):
        raise ValueError('unsupported development-only evidence scope')
    if receipt.get('stage') != 'completed_declared_scenarios':
        raise ValueError('run is not a completed development study')
    scenarios = [item['name'] for item in manifest['scenarios']]
    if (not scenarios or len(set(scenarios)) != len(scenarios)
            or any(not re.fullmatch(r'[a-z0-9_-]+', name) for name in scenarios)
            or not isinstance(results, list) or len(results) != len(scenarios)
            or {item['scenario'] for item in results} != set(scenarios)):
        raise ValueError('scenario results do not match manifest')
    inputs = manifest['inputs']
    if historical:
        inspect_registered_manifest(manifest, run_dir)
    elif (manifest.get('study_registration') is not None or set(inputs) != {'warmup', 'development'}
            or inputs['warmup']['first_day'] != '20211201'
            or inputs['warmup']['last_day'] != '20211231'
            or inputs['development']['first_day'] != '20220103'
            or inputs['development']['last_day'] not in {'20220114', '20220331'}):
        raise ValueError('input window is not the registered development contract')
    if quality['warmup']['complete_h4'] < 81:
        raise ValueError('study has insufficient reported warmup')
    fingerprints = {name: digest(run_dir / name) for name in
                    ('manifest.json', 'receipt.json', 'quality.json', 'results.json')}
    source_drift, unavailable_sources = [], []
    if source_root is not None:
        source_root = source_root.resolve()
        for relative, expected in manifest['source_files'].items():
            path = (source_root / relative).resolve()
            if not path.is_relative_to(source_root):
                raise ValueError('source pin escapes explicit source root')
            if not path.is_file():
                unavailable_sources.append(relative)
            elif digest(path) != expected:
                source_drift.append(relative)
    if verify_inputs:
        for item in inputs.values():
            path = Path(item['path'])
            if not path.is_absolute() or digest(path) != item['sha256']:
                raise ValueError('input content differs from pinned study')
    summary = []
    for row in results:
        if row.get('candidate') != manifest['candidate']:
            raise ValueError('result candidate differs from manifest')
        if (row.get('strategy_pass') is not False or row.get('prop_pass') is not False
                or row.get('broker_spec_verified') is not False):
            raise ValueError('development result makes an unsupported qualification claim')
        if row.get('independent_accounting') != 'passed' or row.get('candidate_state_roundtrip') != 'passed':
            raise ValueError('result reports failed or missing accounting/state evidence')
        delta = finite(row['balance_delta_usd'])
        if delta != finite(row['realized_trade_net_usd']) - finite(row['financing_debit_usd']):
            raise ValueError('reported cash components do not reconcile')
        for key in ('balance_usd', 'equity_usd', 'minimum_observed_equity_usd'):
            finite(row[key])
        for key in ('observed_ticks', 'entry_fills', 'closed_trades'):
            if type(row.get(key)) is not int or row[key] < 0:
                raise ValueError('result count must be a nonnegative integer')
        if row['observed_ticks'] != quality['development']['ticks']:
            raise ValueError('result tick coverage differs from quality artifact')
        if not isinstance(row.get('pending_entry'), bool) or 'open_position' not in row:
            raise ValueError('result position state is missing')
        if row['closed_trades'] > row['entry_fills']:
            raise ValueError('closed trades exceed entries')
        checkpoint = read_json(run_dir / (row['scenario'] + '-checkpoint.json'))
        execution = checkpoint['execution']
        if (finite(execution['balance']) != finite(row['balance_usd'])
                or finite(execution['equity']) != finite(row['equity_usd'])
                or finite(execution['balance']) - finite(execution['starting_balance']) != delta
                or finite(execution['balance']) + finite(execution['floating_pl']) != finite(execution['equity'])
                or execution.get('position') != row['open_position']
                or (execution.get('pending_market_order') is not None) != row['pending_entry']):
            raise ValueError('result does not match final execution checkpoint')
        fingerprints[row['scenario'] + '-checkpoint.json'] = digest(run_dir / (row['scenario'] + '-checkpoint.json'))
        summary.append({key: row[key] for key in ('scenario', 'balance_delta_usd', 'balance_usd',
            'equity_usd', 'entry_fills', 'closed_trades', 'observed_ticks', 'pending_entry',
            'intrabar_equity_coverage')})
        summary[-1]['open_position'] = row['open_position'] is not None
    protocol = manifest.get('research_protocol', {})
    expected_hash = protocol.get('sha256', '')
    if not re.fullmatch(r'[a-f0-9]{64}', expected_hash):
        raise ValueError('missing protocol content pin')
    # Prefer the frozen attempt copy; a later protocol clarification is not
    # corruption of the historical experiment that pinned an earlier revision.
    protocol_candidates = [run_dir/'protocol.md', run_dir.parent / 'protocol.md', Path(protocol.get('path', ''))]
    protocol_verified = any(path.is_file() and digest(path) == expected_hash for path in protocol_candidates)
    return dict(schema='strategy-evidence-dossier-v1', inspected_at_utc=datetime.now(timezone.utc).isoformat(),
        run_dir=str(run_dir), candidate=manifest['candidate'], source_revision=manifest['source_revision'],
        declared_contract=manifest.get('contract'), declared_risk_usd=manifest.get('risk_usd'),
        inputs={name: {key: item[key] for key in ('sha256', 'first_day', 'last_day')}
                for name, item in inputs.items()},
        scenario_costs=[{key: item[key] for key in ('name', 'commission_usd_per_lot_per_side', 'slippage')
                         if key in item} for item in manifest['scenarios']],
        artifact_sha256=fingerprints, protocol_sha256=expected_hash,
        protocol_content_verified=protocol_verified, input_content_verified=bool(verify_inputs),
        source_comparison_requested=source_root is not None, source_drift=source_drift,
        unavailable_sources=unavailable_sources, scenarios=summary,
        artifact_invariants='checked', numeric_recalculation_performed=False,
        evidence_scope='historical_robustness_exposure_unverified' if historical else 'registered_development_not_oos',
        study_registration=manifest.get('study_registration'), qualification='not_established',
        runtime=manifest.get('runtime'),
        reported_accounting='passed', promotion_authorized=False, manual_filter_measured=False,
        review_checks=dict(artifact_invariants='checked_in_scope',
            protocol_content='verified' if protocol_verified else 'not_verified',
            preregistration_timing='not_attested_by_content_hash',
            input_hashes='verified' if verify_inputs else 'not_requested',
            current_source='not_requested' if source_root is None else
                'different_or_missing' if source_drift or unavailable_sources else 'matched',
            causal_implementation='not_assessed_by_this_tool',
            execution_realism='not_established',
            out_of_sample='not_established_prior_exposure_unverified' if historical else 'not_satisfied_development_only',
            selection_bias_and_uncertainty='not_assessed_by_this_tool',
            firm_specific_rules='not_established', forward_reconciliation='not_assessed_by_this_tool'),
        limitations=['Historical broker costs/spec and complete intrabar coverage are not established.',
                     'Artifact checks do not attest trusted authorship or establish strategy edge.',
                     'Reference/stress scenarios are not independent experiments.',
                     'A matching protocol hash does not attest registration before outcomes.',
                     'Current source drift limits reproduction, not validity of pinned historical evidence.'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='command', required=True)
    command = subparsers.add_parser('inspect')
    command.add_argument('--run-dir', required=True, type=Path)
    command.add_argument('--source-root', type=Path)
    command.add_argument('--verify-inputs', action='store_true')
    status_command = subparsers.add_parser('status')
    status_command.add_argument('--run-dir', required=True, type=Path)
    status_command.add_argument('--stale-seconds', default=120, type=int)
    args = parser.parse_args(argv)
    try:
        report = (status(args.run_dir, stale_seconds=args.stale_seconds) if args.command == 'status' else
                  inspect(args.run_dir, verify_inputs=args.verify_inputs, source_root=args.source_root))
    except (OSError, KeyError, TypeError, ValueError) as error:
        print(json.dumps(dict(status='invalid_evidence', error=str(error), promotion_authorized=False)))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
