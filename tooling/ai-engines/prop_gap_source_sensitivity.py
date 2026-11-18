"""Bounded HistData sensitivity and adjacent-minute comparison in Development."""
import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from html.parser import HTMLParser
import io
from pathlib import Path
from statistics import median
import subprocess
from urllib.parse import urlencode
import zipfile

from prop_n1_screen import BASE as N1
from prop_replay_regression import BASE, PROTOCOL, WORKSPACE, net, verify_commit
from prop_v15_accounts import exact_quantity
from prop_v15_evidence import bars_for
from prop_v21_common import compressed, unpack
from prop_v26_common import FIRST, DEV_END, V19, read, sha
from quant_core.job_workspace import JobWorkspace
from quant_core.prop_lifecycle_and_parity import bindings
import prop_v21_common as evidence

EST = timezone(timedelta(hours=-5))
MINUTE = 60_000
MONTHS = ('202105', '202107', '202201')
CENT = Decimal('.01')
HOST = 'https://www.histdata.com'


class DownloadForm(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.fields = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'form':
            self.active = attrs.get('id') == 'file_down' and attrs.get('action') == '/get.php'
        if self.active and tag == 'input' and attrs.get('type') == 'hidden':
            self.fields[attrs['name']] = attrs['value']

    def handle_endtag(self, tag):
        if tag == 'form':
            self.active = False


def fetch(month, folder, asset='EURUSD'):
    year, number = month[:4], int(month[4:])
    page = f'{HOST}/download-free-forex-historical-data/?/ascii/tick-data-quotes/{asset.lower()}/{year}/{number}'
    curl = ['curl.exe', '-q', '--fail', '--silent', '--show-error', '--proto', '=https',
            '--connect-timeout', '8', '--max-time', '40', '--max-filesize', '33554432']
    form = DownloadForm()
    form.feed(subprocess.check_output([*curl, page], timeout=45).decode('utf-8', 'replace'))
    expected = dict(date=year, datemonth=month, platform='ASCII', timeframe='T', fxpair=asset)
    if {k: form.fields.get(k) for k in expected} != expected or not form.fields.get('tk'):
        raise ValueError('HISTDATA_DOWNLOAD_FORM_NOT_AVAILABLE')
    request = urlencode(dict(expected, tk=form.fields['tk'])).encode('ascii')
    downloaded = subprocess.run([*curl, '--referer', page, '--data-binary', '@-', HOST + '/get.php'],
                                input=request, capture_output=True, check=True, timeout=45).stdout
    path = folder / f'HistData-{asset}-{month}.zip'
    with path.open('xb') as stream:
        stream.write(downloaded)
    if not zipfile.is_zipfile(path):
        raise ValueError(f'HISTDATA_NOT_ZIP_{month}')
    return path, page


def observed_ticks(path, month, start, end, *, wanted_minutes=None, asset='EURUSD'):
    low, high = [datetime.fromtimestamp(t / 1000, EST).strftime('%Y%m%d %H%M%S') for t in (start, end)]
    wanted = {datetime.fromtimestamp(t / 1000, EST).strftime('%Y%m%d %H%M') for t in wanted_minutes} if wanted_minutes is not None else None
    rows = []
    previous = ''
    with zipfile.ZipFile(path) as archive:
        member = archive.getinfo(f'DAT_ASCII_{asset}_T_{month}.csv')
        if member.file_size > 350_000_000:
            raise ValueError('HISTDATA_MEMBER_TOO_LARGE')
        with archive.open(member) as raw, io.TextIOWrapper(raw, encoding='ascii') as text:
            for line in text:
                fields = line.rstrip('\r\n').split(',')
                date = fields[0]
                if len(fields) != 4 or len(date) != 18 or date[:6] != month or date < previous:
                    raise ValueError('HISTDATA_TICK_SCHEMA_SCOPE_OR_ORDER')
                previous = date
                if not low <= date[:15] <= high or (wanted is not None and date[:13] not in wanted):
                    continue
                at = int(datetime.strptime(date, '%Y%m%d %H%M%S%f').replace(tzinfo=EST).timestamp() * 1000)
                if not FIRST <= at < DEV_END:
                    raise ValueError('HISTDATA_DEVELOPMENT_FENCE')
                if not start <= at <= end:
                    continue
                bid, ask = map(Decimal, fields[1:3])
                if not bid.is_finite() or not ask.is_finite() or not 0 < bid <= ask:
                    raise ValueError('HISTDATA_INVALID_BID_ASK')
                rows.append((at, bid, ask))
    return rows


def assess(t, rows, gaps, strict):
    entry, deadline = t['entry_msc'], t['deadline_msc']
    qty = exact_quantity(t, 150)
    buy = t['side'] == 'BUY'
    gold = t['asset'] == 'XAUUSD'
    stop = Decimal(t['stop_units']) / (1000 if gold else 100000)
    exit_field = 1 if buy else 2
    def hit(row):
        return row[exit_field] <= stop if buy else row[exit_field] >= stop
    observations = []
    for g in gaps:
        first, after = g['first_unknown'], g['after']
        inside = [r for r in rows if first <= r[0] < after]
        observations.append(dict(first_unknown=first, after=after, count=len(inside),
                                 before_count=sum(g['before'] <= r[0] < first for r in rows),
                                 after_count=sum(after <= r[0] < after + MINUTE for r in rows),
                                 stop_crossings=sum(map(hit, inside)),
                                 min_bid=str(min(r[1] for r in inside)) if inside else None,
                                 max_ask=str(max(r[2] for r in inside)) if inside else None))
    result = dict(entry=entry, gaps=observations, side=t['side'], stop=str(stop), qty=qty,
                  original_primary_cents=net(t, qty), original_strict_cents=net(strict, qty),
                  net_cents=None, status='ENDPOINT_UNAVAILABLE')
    opening = next((r for r in rows if entry <= r[0] <= entry + MINUTE), None)
    closing = next((r for r in rows if deadline <= r[0] <= deadline + MINUTE), None)
    if opening is None or closing is None:
        return result
    span = [r for r in rows if opening[0] <= r[0] <= closing[0]]
    crossing = next((r for r in span if hit(r)), None)
    exit_ = closing if crossing is None else crossing
    held = [r for r in span if r[0] <= exit_[0]]
    max_gap = max((b[0] - a[0] for a, b in zip(held, held[1:])), default=0)
    result['max_intertick_gap_ms'] = max_gap
    if max_gap > 3 * MINUTE:
        result['status'] = 'INTERTICK_GAP'
        return result
    original_entry = opening[2 if buy else 1]
    gross = (Decimal(qty * (1 if gold else 1000) * (1 if buy else -1)) *
             (exit_[exit_field] - original_entry)).quantize(CENT, rounding=ROUND_HALF_UP)
    if gold:
        fees = sum((price * qty * Decimal('.000007')).quantize(CENT, rounding=ROUND_HALF_UP)
                   for price in (original_entry, exit_[exit_field])) + qty * Decimal('.40')
    else:
        fees = 2 * (Decimal(qty) * Decimal('.035')).quantize(CENT, rounding=ROUND_HALF_UP) + qty * Decimal('.02')
    result.update(status='HORIZON' if crossing is None else 'SL', entry_at=opening[0], exit_at=exit_[0],
                  entry_price=str(original_entry), exit_price=str(exit_[exit_field]), net_cents=int((gross - fees) * 100))
    return result


def audit_cached_overlap():
    verify_commit(PROTOCOL)
    verify_commit(__file__)
    parent = next(BASE.glob('histdata-gaps/*/tick-sensitivity-manifest.json'))
    with bindings(evidence, JOB=parent.parent):
        original = unpack('tick-sensitivity')
    rank_path = next(N1.glob('gaps/*/gap-ranking-manifest.json'))
    if sha(rank_path) != original['ranking_manifest_sha256']:
        raise ValueError('HISTDATA_RANKING_MANIFEST_CHANGED')
    with bindings(evidence, JOB=rank_path.parent):
        ranked = unpack('gap-ranking')['gaps']
    bars = bars_for('EURUSD', True)
    result, adjacent = [], {}
    for source in original['results']:
        month = source['month']
        if month not in MONTHS:
            raise ValueError('HISTDATA_SCOPE_CHANGED')
        file = parent.parent / f'HistData-EURUSD-{month}.zip'
        if sha(file) != source['sha256']:
            raise ValueError('HISTDATA_INPUT_HASH_CHANGED')
        scope = [g for g in ranked if g['asset'] == 'EURUSD'
                 and datetime.fromtimestamp(g['first_unknown'] / 1000, EST).strftime('%Y%m') == month]
        needed = {t for g in scope for t in range(g['before'], g['after'] + MINUTE, MINUTE)}
        rows = observed_ticks(file, month, min(needed), max(needed) + MINUTE, wanted_minutes=needed)
        by_minute = defaultdict(list)
        for row in rows:
            by_minute[row[0] // MINUTE * MINUTE].append(row)
        for gap in scope:
            count = sum(len(by_minute[at]) for at in range(gap['first_unknown'], gap['after'], MINUTE))
            result.append(dict(first_unknown=gap['first_unknown'], after=gap['after'], count=count))
            for at in (gap['before'], gap['after']):
                minute = by_minute[at]
                index = int(bars['t'].searchsorted(at))
                if minute and index < len(bars) and bars['t'][index] == at:
                    adjacent[at] = [float(abs(Decimal(int(bars[field][index])) / 100000 - tick[1]) * 10000)
                                    for field, tick in (('bo', minute[0]), ('bc', minute[-1]))]
    differences = [value for pair in adjacent.values() for value in pair]
    value = dict(gaps=result, adjacent=dict(pairs=len(adjacent), fields=len(differences),
        exact=sum(value == 0 for value in differences), median_abs_pips=median(differences) if differences else None,
        max_abs_pips=max(differences) if differences else None, by_minute=adjacent),
        input_manifest_sha256=sha(parent), ranking_manifest_sha256=sha(rank_path), protocol_sha256=sha(PROTOCOL))
    runtime = JobWorkspace(BASE / 'histdata-overlap', WORKSPACE)
    try:
        with bindings(evidence, JOB=runtime.activate()):
            compressed('cached-month-overlap', value)
        print(len(result), sum(g['count'] > 0 for g in result), value['adjacent']['fields'], flush=True)
    finally:
        runtime.close()


def main():
    verify_commit(PROTOCOL)
    verify_commit(__file__)
    runtime = JobWorkspace(BASE / 'histdata-gaps', WORKSPACE)
    output = runtime.activate()
    try:
        rank_path = next(N1.glob('gaps/*/gap-ranking-manifest.json'))
        with bindings(evidence, JOB=rank_path.parent):
            ranked = unpack('gap-ranking')['gaps'][:10]
        grouped = defaultdict(list)
        for gap in ranked:
            if gap['asset'] != 'EURUSD' or len(gap['trades']) != 1:
                raise ValueError('HISTDATA_REGISTRATION_RANKING_CHANGED')
            grouped[gap['trades'][0]['entry']].append(gap)
        primary = {t['entry_msc']: t for t in read(V19 / 'Dev-OLHC-PRIMARY-trades.json') if t['asset'] == 'EURUSD'}
        strict = {t['entry_msc']: t for t in read(V19 / 'Dev-OLHC-STRICT-trades.json') if t['asset'] == 'EURUSD'}
        months = {datetime.fromtimestamp(t / 1000, EST).strftime('%Y%m'): t for t in grouped}
        if len(grouped) != 3 or set(months) != set(MONTHS):
            raise ValueError('HISTDATA_REGISTRATION_MONTH_SET')
        results = []
        for month, entry in sorted(months.items()):
            t = primary[entry]
            if t['mode'] != 'P0' or t['deadline_msc'] - entry >= 17 * 60 * MINUTE or t['deadline_msc'] % 86400000 >= 21 * 60 * MINUTE:
                raise ValueError('HISTDATA_UNSUPPORTED_STRATEGY_OR_FUNDING')
            path, page = fetch(month, output)
            gaps = grouped[entry]
            rows = observed_ticks(path, month, min(entry, *(g['before'] for g in gaps)),
                                  max(t['deadline_msc'] + MINUTE, *(g['after'] + MINUTE for g in gaps)))
            results.append(dict(month=month, page=page, sha256=sha(path), observed_ticks=len(rows),
                                **assess(t, rows, gaps, strict[entry])))
            print(month, len(rows), results[-1]['status'], flush=True)
        with bindings(evidence, JOB=output):
            compressed('tick-sensitivity', dict(results=results, ranking_manifest_sha256=sha(rank_path),
                       protocol_sha256=sha(PROTOCOL), provider_independence_certified=False, source_backfilled=False))
    finally:
        runtime.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cached-overlap', action='store_true')
    (audit_cached_overlap if parser.parse_args().cached_overlap else main)()
