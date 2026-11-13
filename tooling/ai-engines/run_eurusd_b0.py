"""Run one registered B0 attempt, cache-only and restricted to 2021warmup/2022-24."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
import traceback

from eurusd_b0_source import bounds, digest, prepare, read_session, write_json
import eurusd_b0 as b0


def execute(config_path):
    config_path = Path(config_path).resolve()
    cfg = json.loads(config_path.read_bytes())
    root = Path(cfg['workspace']).resolve()
    output = Path(cfg['output']).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output/'result.json').exists():
        raise ValueError('B0_attempt_already_has_result_use_review_not_rerun')
    began, cpu = time.monotonic(), time.process_time()
    stage = 'preflight'
    event_count = 0
    def event(**fields):
        nonlocal stage, event_count
        if (output/'CANCEL').exists():
            raise InterruptedError('B0_cancel_requested')
        if time.monotonic()-began > cfg['deadline_seconds']:
            raise TimeoutError('B0_attempt_deadline')
        stage = fields.get('stage', stage)
        event_count += 1
        row = dict(sequence=event_count, utc=datetime.now(timezone.utc).isoformat(), pid=os.getpid(),
                   config_sha256=digest(config_path), **fields)
        with (output/'events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(row, ensure_ascii=False)+'\n')
        write_json(output/'status.json', row)
        print(json.dumps(row), flush=True)
    # A rejected second writer must not publish failure/status into the live attempt.
    with (output/'writer.lock').open('x') as stream:
        stream.write(str(os.getpid()))
    try:
        if cfg['candidate'] != 'eurusd-b0-v1' or cfg['years'] != [2022, 2023, 2024]:
            raise ValueError('B0_exact_version_and_years_required')
        for source in cfg['sources']:
            bounds(source['first_day'], source['last_day'])
        if [(s['first_day'], s['last_day']) for s in cfg['sources']] != [
                ('20211101', '20211231'), ('20220101', '20221231'),
                ('20230101', '20231231'), ('20240101', '20241231')]:
            raise ValueError('B0_source_partitions_changed')
        for relative, expected in cfg['source_pins'].items():
            if digest(root/relative) != expected:
                raise ValueError('B0_implementation_changed_after_freeze:'+relative)
        if digest(root/cfg['protocol']) != cfg['protocol_sha256']:
            raise ValueError('B0_protocol_changed_after_freeze')
        b0.bind_native(root/'projects/trader/foundation_v2')
        event(stage='preflight_verified', strict_status='BLOCKED_BY_CALENDAR')
        seals = []
        views = []
        prep_began = time.monotonic()
        for source in cfg['sources']:
            destination = Path(cfg['prepared'])/source['first_day']
            seals.append(prepare(source, destination, event))
            views.append(json.loads((destination/'bars.json').read_bytes()))
        prep_seconds = time.monotonic()-prep_began
        m15 = [row for v in views for row in v['m15']]
        h1 = [row for v in views for row in v['h1']]
        if any(b[0] <= a[0] for bars in (m15, h1) for a, b in zip(bars, bars[1:])):
            raise ValueError('B0_partition_overlap')
        feature_began = time.monotonic()
        f = b0.features(m15, h1)
        event(stage='features_ready', m15_observed=len(m15), h1_observed=len(h1),
              complete_m15=len(f), indicator_seed=cfg['sources'][0]['first_day'])
        feature_seconds = time.monotonic()-feature_began
        rows, years, annuals = [], [], []
        simulation_began = time.monotonic()
        for year, seal, source in zip(cfg['years'], seals[1:], cfg['sources'][1:]):
            year_dir = output/str(year)
            year_dir.mkdir(exist_ok=True)
            accounts = {name: b0.Account() for name in ('reference', 'stress')}
            days = {name: [] for name in accounts}
            destination = Path(cfg['prepared'])/source['first_day']
            # Include weekdays with no source quotes, rather than dropping absent sessions.
            from datetime import date, timedelta
            day = date(year, 1, 1)
            while day.year == year:
                if day.weekday() < 5:
                    label = day.isoformat()
                    path = destination/(label+'.ticks')
                    quotes = read_session(path) if path.exists() else []
                    for scenario, account in accounts.items():
                        d = b0.run_day(label, f, quotes, account, scenario)
                        if d.get('open_position') is not None:
                            write_json(year_dir/(label+'-unresolved.json'), d)
                            raise ValueError('B0_unresolved_position_stop_do_not_reset_or_fabricate_flat')
                        days[scenario].append(d)
                day += timedelta(days=1)
                if day.day == 1:
                    event(stage='conditional_replay', year=year, through=day.isoformat())
            for scenario, account in accounts.items():
                detail = dict(year=year, scenario=scenario, days=days[scenario])
                write_json(year_dir/(scenario+'-details.json'), detail)
                funnel = {}
                for d in days[scenario]:
                    for key, value in d['counters'].items():
                        funnel[key] = funnel.get(key, 0)+value
                write_json(year_dir/(scenario+'-funnel.json'), dict(year=year, scenario=scenario, counters=funnel))
                summary = b0.summarize(year, scenario, days[scenario], account)
                write_json(year_dir/(scenario+'-summary.json'), summary)
                rows.append(summary)
            annuals.append(dict(year=year, input_ticks=seal['ticks'], session_ticks=seal['session_ticks'],
                observed_m15=len(views[len(annuals)+1]['m15']),
                incomplete_m15=sum(r[5] != 15 for r in views[len(annuals)+1]['m15']),
                observed_h1=len(views[len(annuals)+1]['h1']),
                incomplete_h1=sum(r[5] != 60 for r in views[len(annuals)+1]['h1'])))
            event(stage='year_reconciled', year=year)
        simulation_seconds = time.monotonic()-simulation_began
        pooled = []
        for scenario in ('reference', 'stress'):
            selected = [r for r in rows if r['scenario'] == scenario]
            total = sum(round(r['conditional_net_usd']*100) for r in selected)
            offset = 0
            peak = b0.INITIAL_CENTS
            dd = 0
            for r in selected:
                minimum = round(r['minimum_equity_usd']*100)+offset
                dd = max(dd, peak-minimum, round(r['max_equity_dd_usd']*100))
                peak = max(peak, round(r['peak_equity_usd']*100)+offset)
                offset += round(r['conditional_net_usd']*100)
            pooled.append(dict(scenario=scenario, conditional_net_usd=total/100,
                net_r0=total/b0.R0_CENTS, pooled_equity_dd_usd=dd/100,
                pooled_cumulative_r_dd=dd/b0.R0_CENTS,
                zero_compounding=True, annual_capital_resets=True))
        result = dict(schema='eurusd-b0-result-v1', candidate=cfg['candidate'],
            config_sha256=digest(config_path), protocol_sha256=cfg['protocol_sha256'],
            source_pins=cfg['source_pins'], rows=rows, coverage=annuals, pooled=pooled,
            strict_status='BLOCKED_BY_CALENDAR', strict_net_usd=None, prop_qualified=False,
            note='Conditional economics before historical known-at news/target-session admission; not a full B0 qualification.',
            trial_budget=dict(alpha_versions_used=['B0'], b1_used=False, xau_used=False),
            closed_price_years=[2025, 2026], broker_calls=0, network_requests=0,
            timing=dict(preparation_wall_seconds=prep_seconds, features_wall_seconds=feature_seconds,
                simulation_wall_seconds=simulation_seconds, total_wall_seconds=time.monotonic()-began,
                process_cpu_seconds=time.process_time()-cpu),
            preparation_seal_sha256=[digest(Path(cfg['prepared'])/s['first_day']/'seal.json') for s in cfg['sources']])
        write_json(output/'result.json', result)
        event(stage='completed_conditional_reconciled', result_sha256=digest(output/'result.json'))
        return result
    except BaseException as error:
        write_json(output/'failure.json', dict(stage=stage, error_type=type(error).__name__,
                   code=str(error) if isinstance(error, (ValueError, TimeoutError, InterruptedError)) else 'see_trace_locations',
                   locations=[dict(file=f.filename, line=f.lineno, function=f.name)
                              for f in traceback.extract_tb(error.__traceback__)],
                   wall_seconds=time.monotonic()-began))
        raise
    finally:
        lock = output/'writer.lock'
        if lock.exists() and lock.read_text() == str(os.getpid()):
            lock.unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    execute(parser.parse_args().config)
