"""Read-only run/receipt projection. Native Paperclip remains the run ledger."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from engine_worker import uuid


ACTIVE = {'queued', 'running'}


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def text(value):
    return value if isinstance(value, str) and 0 < len(value) <= 160 else None


def receipt_for(root, company, run_id, issue_id, engine):
    if root is None:
        return None, 'unavailable'
    base = Path(root).resolve()
    path = base / company / run_id / 'receipt.json'
    try:
        if not path.resolve().is_relative_to(base):
            return None, 'invalid'
        with path.open('rb') as stream:
            wire = stream.read(65537)
        if len(wire) > 65536:
            return None, 'invalid'
        receipt = json.loads(wire)
        if (not isinstance(receipt, dict) or receipt.get('engine') != engine
                or receipt.get('run_id', receipt.get('run')) != run_id
                or receipt.get('issue_id', receipt.get('issue')) != issue_id
                or receipt.get('company_id', company) != company
                or ('models' in receipt and not isinstance(receipt['models'], dict))):
            return None, 'invalid'
        # Only inspect the fixed worker outputs; receipt filenames cannot escape.
        for field, name in [('report_sha256', 'report.md'), ('evidence_sha256', 'evidence.md')]:
            if field not in receipt:
                continue
            artifact = path.parent / name
            if (not artifact.resolve().is_relative_to(base) or not artifact.is_file()
                    or artifact.stat().st_size > 2_000_000):
                return None, 'invalid'
            # Workers hash logical UTF-8 text before Windows writes CRLF.
            if hashlib.sha256(artifact.read_text(encoding='utf-8').encode()).hexdigest() != receipt[field]:
                return None, 'invalid'
        return receipt, 'available'
    except FileNotFoundError:
        return None, 'missing'
    except (OSError, ValueError, TypeError):
        return None, 'invalid'


def elapsed(run, now):
    try:
        start = datetime.fromisoformat(run['startedAt'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(run['finishedAt'].replace('Z', '+00:00')) if run.get('finishedAt') else now
        if not run.get('finishedAt') and run['status'] not in ACTIVE:
            return None
        return number((end - start).total_seconds())
    except (KeyError, TypeError, ValueError):
        return None


def observe_step(api, company, child, engine, artifact_root=None, now=None):
    observation = {'state': 'not_started', 'run': None}
    try:
        # Native endpoint orders by creation time and bounds this view to two runs.
        rows = api('/issues/' + child['id'] + '/runs?view=recent')
        if not rows:
            return {'state': 'unknown' if child['status'] in ('done', 'in_progress') else 'not_started', 'run': None}
        run_id = uuid(rows[0]['runId'])
        run = api('/heartbeat-runs/' + run_id)
    except Exception:
        return {'state': 'unavailable', 'run': None}
    bound_issue = run.get('issueId') or (run.get('contextSnapshot') or {}).get('issueId')
    if (run.get('id') != run_id or run.get('companyId') != company or bound_issue != child['id']
            or run.get('agentId') != rows[0].get('agentId')):
        raise ValueError('workflow_scope')
    receipt, receipt_state = receipt_for(artifact_root, company, run_id, child['id'], engine)
    receipt = receipt or {}
    native_status = run.get('status')
    local_status = receipt.get('status')
    delivered = receipt.get('delivery_status', receipt.get('review_delivery')) == 'published'
    saved = receipt.get('engine_status') == 'completed' or delivered
    if receipt_state == 'invalid':
        state = 'evidence_mismatch'
    elif native_status in ACTIVE:
        state = 'active'
    elif child['status'] == 'cancelled' or native_status == 'cancelled':
        state = 'cancelled'
    elif saved and (not delivered or child['status'] != 'done'):
        state = 'delivery_pending'
    elif local_status in ('preflight', 'running', 'publishing'):
        state = 'interrupted'
    elif native_status == 'succeeded' and child['status'] == 'done' and local_status == 'completed' and delivered:
        state = 'recorded'
    elif native_status in ('failed', 'timed_out') or local_status in ('failed', 'blocked'):
        state = 'failed'
    else:
        state = 'unknown'
    usage = run.get('usageJson') or {}
    # The generic process adapter emits zero counters without observing SDK calls.
    # Those defaults are not a provider receipt for our Python workers.
    if usage.get('billingType', usage.get('billing_type')) == 'unknown' and not any(
            number(usage.get(k)) for k in ('inputTokens', 'input_tokens', 'outputTokens', 'output_tokens')):
        usage = {}
    result = run.get('resultJson') or {}
    requested = []
    if receipt.get('provider_work_started'):
        requested = list(dict.fromkeys(filter(None, [text(receipt.get('model')),
                         *[text(v) for v in (receipt.get('models') or {}).values()]])))
    cost = next((number(row.get(key)) for row in (usage, result)
                 for key in ('costUsd', 'cost_usd', 'total_cost_usd') if number(row.get(key)) is not None), None)
    observation.update(state=state, run={
        'id': run_id, 'status': native_status, 'receipt': receipt_state,
        'seconds': elapsed(run, now or datetime.now(timezone.utc)),
        'requested_models': requested, 'reported_model': text(result.get('model')),
        'input_tokens': number(usage.get('inputTokens', usage.get('input_tokens'))),
        'output_tokens': number(usage.get('outputTokens', usage.get('output_tokens'))),
        'cost_usd': cost, 'accounting_pending': run.get('costAccountingPending') is True,
    })
    return observation
