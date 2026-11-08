from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research_input_admission import CLOCK, SCHEMA, review_fixture
from sealed_m1_review import digest

STAMP = 1640995200000


def save(path, value):
    path.write_text(json.dumps(value), encoding='utf8')


def fixture(root, *, etf=False, stock=False):
    cache = root/'cache'; cache.mkdir()
    protocol = root/'protocol.md'; protocol.write_text('registered fixture', encoding='utf8')
    producer = root/'producer.txt'; producer.write_text('frozen producer', encoding='utf8')
    manifest = dict(requests=[], metadata={}, sourcePins={str(producer): digest(producer)},
                    holdoutRead=False, strategySimulated=False, brokerCalls=0, modelCalls=0)
    result = dict(requests=[], holdoutRead=False, strategySimulated=False, brokerCalls=0, modelCalls=0)
    instrument, symbol = (('aaplususd', 'AAPL.US-USD') if stock else
                          ('ezuususd', 'EZU.US-USD') if etf else ('eurusd', 'EUR-USD'))
    asset = dict(instrument=instrument, provider='Dukascopy', provider_symbol=symbol, kind='fx',
                 base_currency='EUR', quote_currency='USD', price_unit='quote_per_base',
                 price_grid='0.01', adjustment_basis='not_applicable_fx', source_use='fixture_only')
    if etf or stock:
        asset.update(kind='etf_cfd_proxy', base_currency=None,
                     price_unit='quote_per_share_proxy', adjustment_basis='unknown')
    manifest['metadata'][instrument] = dict(code=symbol)
    for side, price in [('bid', 100), ('ask', 101)]:
        raw = dict(timestamp=STAMP, shift=60000, multiplier=.01, open=price, high=price, low=price, close=price,
                   times=[0, 2], opens=[0, 0], highs=[0, 0], lows=[0, 0], closes=[0, 0], volumes=[1, 0])
        save(cache/f'candles%2Fminute%2F{symbol}%2F{side.upper()}%2F2022%2F1%2F1.json', raw)
        rows = [dict(timestamp=STAMP+i*60000, open=price, high=price, low=price, close=price,
                     volume=1 if i==0 else 0) for i in range(3)]
        stem = instrument+'-'+side
        save(root/(stem+'.json'), rows)
        seal = dict(request=stem, rows=3, first=STAMP, last=STAMP+120000, sha256=digest(root/(stem+'.json')))
        save(root/(stem+'-seal.json'), seal); result['requests'].append(seal)
        manifest['requests'].append(dict(instrument=instrument, priceType=side, timeframe='m1',
            ignoreFlats=False, cacheFolderPath=str(cache),
            dates={'from':'2022-01-01T00:00:00Z', 'to':'2022-01-02T00:00:00Z'}))
    save(root/'manifest.json', manifest); save(root/'result.json', result)
    metadata = dict(schema=SCHEMA, clock=CLOCK, data_role='source_fixture', exposure='unknown', clean_oos=False,
                    protocol=dict(path=str(protocol), sha256=digest(protocol)),
                    parent_manifest_sha256=digest(root/'manifest.json'), parent_result_sha256=digest(root/'result.json'),
                    producer_bindings={str(producer): digest(producer)},
                    raw_bindings={str(p.resolve()):digest(p) for p in cache.iterdir()}, assets=[asset])
    save(root/'admission.json', metadata)
    return metadata


class InputAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.metadata = fixture(self.root)

    def review(self):
        save(self.root/'admission.json', self.metadata)
        return review_fixture(self.root, self.root/'admission.json')

    def reseal(self, side, rows):
        stem = 'eurusd-'+side
        save(self.root/(stem+'.json'), rows)
        seal = json.loads((self.root/(stem+'-seal.json')).read_text())
        seal.update(rows=len(rows), first=rows[0]['timestamp'], last=rows[-1]['timestamp'],
                    sha256=digest(self.root/(stem+'.json')))
        save(self.root/(stem+'-seal.json'), seal)
        result = json.loads((self.root/'result.json').read_text())
        result['requests'][0 if side=='bid' else 1] = seal
        save(self.root/'result.json', result)
        self.metadata['parent_result_sha256'] = digest(self.root/'result.json')

    def test_preserves_explicit_zero_volume_and_reports_padding_without_oos_claim(self):
        report = self.review()
        self.assertEqual(report['status'], 'source_fixture_verified_only')
        self.assertEqual(report['exposure'], 'unknown')
        self.assertFalse(report['clean_oos'])
        asset = report['assets'][0]
        self.assertEqual(asset['paired_source_rows'], 2)
        self.assertEqual([(s['native_rows'], s['explicit_rows'], s['padding_rows']) for s in asset['sides']],
                         [(3, 2, 1), (3, 2, 1)])

    def test_rejects_units_clock_role_clean_claim_and_missing_producer(self):
        original = deepcopy(self.metadata)
        mutations = [dict(clock={**CLOCK, 'timestamp_unit':'unix_seconds'}),
                     dict(data_role='final_holdout'), dict(clean_oos=True), dict(exposure='clean'),
                     dict(producer_bindings={})]
        for changes in mutations:
            self.metadata = {**deepcopy(original), **changes}
            with self.subTest(changes=changes), self.assertRaises(ValueError): self.review()
        for field, value in [('price_unit','USD'), ('base_currency','JPY'), ('price_grid','0.001'),
                             ('adjustment_basis','total_return'), ('provider_symbol','WRONG')]:
            self.metadata = deepcopy(original); self.metadata['assets'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.review()

    def test_tampered_parent_or_protocol_rejected_before_reading_quotes(self):
        for path in ('manifest.json', 'protocol.md', 'cache/candles%2Fminute%2FEUR-USD%2FBID%2F2022%2F1%2F1.json'):
            target = self.root/path; original = target.read_bytes(); target.write_bytes(original+b' ')
            with self.subTest(path=path), self.assertRaisesRegex(ValueError,'hash_binding'): self.review()
            target.write_bytes(original)

    def test_missing_or_extra_raw_pin_is_not_silently_ignored(self):
        original = deepcopy(self.metadata['raw_bindings'])
        self.metadata['raw_bindings'] = {}
        with self.assertRaisesRegex(ValueError,'raw_bindings_required'): self.review()
        self.metadata['raw_bindings'] = {**original, 'unrequested-raw-file':'0'*64}
        with self.assertRaisesRegex(ValueError,'raw_census'): self.review()

    def test_resealed_actual_or_padding_price_mutation_still_fails_raw_binding(self):
        original = json.loads((self.root/'eurusd-bid.json').read_text())
        for index in (0, 1):
            rows = deepcopy(original)
            rows[index].update(open=99, high=99, low=99, close=99)
            self.reseal('bid', rows)
            with self.subTest(index=index), self.assertRaisesRegex(ValueError,'price_or_volume_binding'):
                self.review()

    def test_missing_native_bar_or_side_is_not_repaired(self):
        rows = json.loads((self.root/'eurusd-bid.json').read_text())
        self.reseal('bid', rows[1:])
        with self.assertRaisesRegex(ValueError,'full_unfiltered'): self.review()
        self.reseal('bid', rows)
        (self.root/'eurusd-ask.json').unlink()
        with self.assertRaises((ValueError, FileNotFoundError)): self.review()

    def test_duplicate_side_and_holdout_request_are_rejected(self):
        manifest = json.loads((self.root/'manifest.json').read_text())
        original = deepcopy(manifest)
        manifest['requests'][1]['priceType'] = 'bid'
        save(self.root/'manifest.json', manifest)
        self.metadata['parent_manifest_sha256'] = digest(self.root/'manifest.json')
        with self.assertRaisesRegex(ValueError,'duplicate_request'): self.review()
        manifest = original
        manifest['requests'][0]['dates']['to'] = '2025-01-02T00:00:00Z'
        save(self.root/'manifest.json', manifest)
        self.metadata['parent_manifest_sha256'] = digest(self.root/'manifest.json')
        with self.assertRaisesRegex(ValueError,'holdout_closed'): self.review()

    def test_unknown_etf_adjustment_is_visible_and_cannot_be_claimed_verified(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); metadata = fixture(root, etf=True)
            report = review_fixture(root, root/'admission.json')
            self.assertFalse(report['assets'][0]['adjustment_verified'])
            metadata['assets'][0]['adjustment_basis'] = 'total_return'
            save(root/'admission.json', metadata)
            with self.assertRaisesRegex(ValueError,'adjustment_unverified'):
                review_fixture(root, root/'admission.json')

    def test_stock_fixture_preserves_unverified_volume_and_universe_semantics(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); metadata = fixture(root, stock=True)
            asset = metadata['assets'][0]
            asset.update(kind='stock_cfd_proxy',
                         volume_semantics='provider_candle_volume_unverified_exchange_shares',
                         volume_units='provider_native_millions', point_in_time_universe='not_certified')
            manifest = json.loads((root/'manifest.json').read_text())
            for request in manifest['requests']:
                request.update(volumes=True, volumeUnits='millions')
            save(root/'manifest.json', manifest)
            metadata['parent_manifest_sha256'] = digest(root/'manifest.json')
            save(root/'admission.json', metadata)
            report = review_fixture(root, root/'admission.json')
            self.assertEqual(report['status'], 'source_fixture_verified_only')
            self.assertFalse(report['assets'][0]['adjustment_verified'])
            original = deepcopy(asset)
            for key, value in [('volume_semantics', 'exchange_traded_shares'),
                               ('volume_units', 'shares'), ('point_in_time_universe', 'verified'),
                               ('adjustment_basis', 'unadjusted')]:
                metadata['assets'][0] = {**original, key:value}
                save(root/'admission.json', metadata)
                with self.subTest(field=key), self.assertRaises(ValueError):
                    review_fixture(root, root/'admission.json')
            metadata['assets'][0] = original
            save(root/'admission.json', metadata)
            manifest['requests'][0]['volumeUnits'] = 'units'
            save(root/'manifest.json', manifest)
            metadata['parent_manifest_sha256'] = digest(root/'manifest.json')
            save(root/'admission.json', metadata)
            with self.assertRaisesRegex(ValueError, 'volume_scale_required'):
                review_fixture(root, root/'admission.json')


if __name__ == '__main__':
    unittest.main()
