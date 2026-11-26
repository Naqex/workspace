"""Bounded read-only reconstruction of saved Development B0 counters."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

from eurusd_b0 import features
from eurusd_b0_source import digest, write_json
from eurusd_funnel_audit import audit_days


def execute(parent, output):
    parent, output = Path(parent), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    began = time.monotonic()
    events = []
    def event(stage, **fields):
        row = dict(sequence=len(events)+1, stage=stage, pid=os.getpid(),
                   utc=datetime.now(timezone.utc).isoformat(), **fields)
        events.append(row)
        with (output/'events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(row)+'\n')
        write_json(output/'status.json', row)
        print(json.dumps(row), flush=True)
    try:
        config = parent/'config-attempt-1.json'
        cfg = json.loads(config.read_bytes())
        frozen = parent/'source-attempt-1/tooling/ai-engines/eurusd_b0.py'
        current = Path(__file__).with_name('eurusd_b0.py')
        if digest(frozen) != cfg['source_pins']['tooling/ai-engines/eurusd_b0.py']:
            raise ValueError('frozen_B0_source_changed')
        if frozen.read_bytes().replace(b'\r\n', b'\n') != current.read_bytes().replace(b'\r\n', b'\n'):
            raise ValueError('B0_indicator_implementation_drift')
        inputs = {str(config): digest(config), str(frozen): digest(frozen)}
        m15, h1 = [], []
        for partition in ('20211101', '20220101', '20230101'):
            base = parent/'prepared-v1'/partition
            seal = json.loads((base/'seal.json').read_bytes())
            expected = next(r['sha256'] for r in seal['files'] if r['name'] == 'bars.json')
            if digest(base/'bars.json') != expected:
                raise ValueError('sealed_bar_content_changed')
            packet = json.loads((base/'bars.json').read_bytes())
            for name, width in (('m15', 900000), ('h1', 3600000)):
                if any(not 1635724800000 <= r[0] < 1704067200000 or r[0]+width > 1704067200000 for r in packet[name]):
                    raise ValueError('EURUSD_2024_diagnostic_closed')
            inputs[str(base/'bars.json')] = expected
            m15.extend(packet['m15'])
            h1.extend(packet['h1'])
        event('frozen_views_verified', input_partitions=[20211101, 20220101, 20230101])
        feature_map = features(m15, h1)
        annual, totals, rejects = [], [], []
        for year in (2022, 2023):
            path = parent/'attempt-1'/str(year)/'stress-details.json'
            inputs[str(path)] = digest(path)
            days = json.loads(path.read_bytes())['days']
            result = audit_days(days, feature_map, year)
            write_json(output/(str(year)+'-details.json'), result)
            annual.append(result['summary'])
            rejects.extend(result['rejected_intents'])
            totals.append(result)
            event('year_counter_parity_verified', year=year)
        combined = {}
        for key in ('exclusive_zone_stages', 'no_setup_subtypes', 'setup_fates', 'trigger_details'):
            counter = Counter()
            for row in annual:
                counter.update(row[key])
            combined[key] = dict(counter)
        from statistics import median
        combined.update(valid_zones=sum(r['valid_zones'] for r in annual),
            confirmed_signal_events=sum(r['confirmed_signal_events'] for r in annual),
            confirmed_unique_zones=sum(r['confirmed_unique_zones'] for r in annual),
            zones_without_confirmation=sum(r['zones_without_confirmation'] for r in annual),
            rejected_events=len(rejects), filled_events=sum(r['filled_events'] for r in annual),
            rejected_sl_median_pips=median(r['natural_sl_pips'] for r in rejects),
            required_sl_median_pips=median(r['minimum_admissible_sl_pips'] for r in rejects),
            required_sl_range_pips=[min(r['minimum_admissible_sl_pips'] for r in rejects),
                                    max(r['minimum_admissible_sl_pips'] for r in rejects)])
        packet = dict(schema='eurusd-B0-development-funnel-audit-v1', annual=annual, combined=combined,
            input_sha256=inputs, frozen_feature_sha256=digest(frozen), current_feature_sha256=digest(current),
            source_sha256={p.name: digest(p) for p in (Path(__file__), Path(__file__).with_name('eurusd_funnel_audit.py'))},
            diagnostic_years=[2022, 2023], indicator_warmup_only='2021-11-01/2021-12-31',
            EURUSD_2024_read=False, price_2025_2026_read=False, new_strategy_backtests=0,
            pnl_recomputed=False, financial_rules_changed=False, new_order_events=0,
            wall_seconds=time.monotonic()-began)
        write_json(output/'result.json', packet)
        event('completed_read_only_counter_audit', result_sha256=digest(output/'result.json'))
        return packet
    except BaseException as error:
        write_json(output/'failure.json', dict(type=type(error).__name__, stage=events[-1]['stage'] if events else 'preflight'))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    execute(args.parent, args.output)
