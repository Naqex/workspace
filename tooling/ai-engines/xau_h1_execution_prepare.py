"""Bounded tick-hour census for the owner-approved, unchanged H1 cohorts."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from xau_h1_stage0_source import START, END, HOUR
from eurusd_b0_source import digest, write_json


def deadline(at):
    if not START <= at < END:
        raise ValueError('development_entry_required')
    dt = datetime.fromtimestamp(at/1000, timezone.utc)
    if dt.weekday() >= 5:
        raise ValueError('weekday_entry_required')
    friday = (dt + timedelta(days=4-dt.weekday())).replace(hour=20, minute=30, second=0, microsecond=0)
    end=min(at+48*HOUR, int(friday.timestamp()*1000))
    if end<=at:raise ValueError('entry_at_or_after_friday_flat')
    return end


def prepare(parent, output, manifests):
    parent, output = Path(parent), Path(output)
    output.mkdir(exist_ok=False)
    measurements = json.loads((parent/'attempt-2/measurements.json').read_bytes())
    hours = set()
    for r in measurements:
        if not r['entry_quote']:
            raise ValueError('parent_entry_missing')
        at = r['entry_quote'][0]; end = deadline(at)
        if end >= END:
            raise ValueError('deadline_touches_closed_year')
        hours.add(end//HOUR*HOUR)
        if r['recipe'] in ('H1A_ASIA', 'H1C_MOMENTUM'):
            hours.update(range(at//HOUR*HOUR, end//HOUR*HOUR+1, HOUR))
    reused = {}
    for path in manifests:
        data = json.loads(Path(path).read_bytes())
        for r in data['hours']:
            if START <= r['at'] < END and r['at'] in hours:
                reused[r['at']] = r
    result = dict(schema='XAU-H1-execution-census-v1', scope_start=START,
        scope_end_exclusive=END, hours=sorted(hours), reused_hours=list(reused.values()),
        parent_measurements_sha256=digest(parent/'attempt-2/measurements.json'),
        endpoint_cohort=608, path_cohort=356, new_hours=len(hours)-len(reused))
    write_json(output/'census.json', result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('hours','reused_hours')}))


if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--parent',required=True);p.add_argument('--output',required=True)
    p.add_argument('--manifest',action='append',required=True);a=p.parse_args()
    prepare(a.parent,a.output,a.manifest)
