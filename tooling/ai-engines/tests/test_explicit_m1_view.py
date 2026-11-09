from datetime import datetime,timezone
import json
from pathlib import Path
import sys,tempfile,unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from explicit_m1_view import prepare,cache_path,POLICY
from sealed_m1_review import digest,review

CALENDAR=Path(__file__).resolve().parents[1]/'fixtures/nyse-2022.json'


def write(path,value):path.write_text(json.dumps(value),encoding='utf8')


def fixture(root, *, asymmetric=False):
    parent=root/'parent';parent.mkdir();cache=parent/'cache';cache.mkdir()
    manifest=dict(requests=[])
    result=dict(status='downloaded_verified_M1_sides_needs_calendar_review',requests=[],
                strategySimulated=False,holdoutRead=False,brokerCalls=0,modelCalls=0)
    for q in range(1,5):
        lower=datetime(2022,3*(q-1)+1,1,tzinfo=timezone.utc)
        upper=datetime(2023,1,1,tzinfo=timezone.utc) if q==4 else datetime(2022,3*q+1,1,tzinfo=timezone.utc)
        stamp=int(lower.timestamp()*1000)
        for side,offset in [('bid',0),('ask',.1)]:
            request=dict(instrument='usa500idxusd',timeframe='m1',priceType=side,ignoreFlats=False,
                         dates=dict(**{'from':lower.isoformat(),'to':upper.isoformat()}),cacheFolderPath=str(cache))
            if asymmetric and q==1:
                steps=[0,2,1] if side=='bid' else [0,3]
                deltas=[0,10,0] if side=='bid' else [0,10]
                prices=[100+offset,100+offset,100.01+offset if side=='bid' else 100+offset,100.01+offset]
                volumes=[1,0,0,1]
                raw_volumes=[1,0,1] if side=='bid' else [1,1]
            else:
                steps=[0,2];deltas=[0,1000];prices=[100+offset,100+offset,101+offset]
                volumes=[1,0,0];raw_volumes=[1,0]
            native=[dict(timestamp=stamp+index*60000,open=price,high=price,low=price,close=price,volume=volumes[index])
                    for index,price in enumerate(prices)]
            raw=dict(timestamp=stamp,shift=60000,multiplier=.001,open=100+offset,high=100+offset,
                     low=100+offset,close=100+offset,times=steps,opens=deltas,highs=deltas,lows=deltas,closes=deltas,
                     volumes=raw_volumes)
            write(cache_path(request,stamp),raw)
            stem=f'q{q}-{side}';path=parent/f'{stem}.json';write(path,native)
            seal=dict(request=stem,rows=len(native),first=native[0]['timestamp'],last=native[-1]['timestamp'],sha256=digest(path))
            write(parent/f'{stem}-seal.json',seal)
            manifest['requests'].append(request);result['requests'].append(seal)
    write(parent/'manifest.json',manifest);write(parent/'result.json',result)
    protocol=root/'protocol.md';protocol.write_text('Synthetic source-only correction fixture, no trading.',encoding='utf8')
    return parent,protocol


class ExplicitM1ViewTests(unittest.TestCase):
    def test_real_source_zero_volume_survives_but_native_padding_does_not(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);parent,protocol=fixture(root);output=root/'explicit'
            old=review(parent,CALENDAR,.001)
            self.assertFalse(old['source_presence_verified'])
            self.assertEqual(old['coverage_basis'],'decoded_timestamps_only')
            with self.assertRaisesRegex(ValueError,'explicit_source_observation_proof_required'):
                review(parent,CALENDAR,.001,require_explicit_source=True)
            proof=prepare(parent,CALENDAR,protocol,output)
            checked=review(output,CALENDAR,.001,require_explicit_source=True)
            self.assertTrue(checked['source_presence_verified'])
            self.assertEqual(checked['source_observation_policy'],POLICY)
            self.assertEqual(checked['rows_per_side'],8)
            rows=json.loads((output/'q1-bid.json').read_text())
            self.assertEqual([r['volume'] for r in rows],[1,0])
            self.assertEqual(rows[1]['timestamp']-rows[0]['timestamp'],120000)
            self.assertEqual(proof['quarters'][0]['sides'][0]['removed_padding'],1)

    def test_asymmetric_source_minute_is_journaled_not_filled_on_other_side(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);parent,protocol=fixture(root,asymmetric=True);output=root/'explicit'
            proof=prepare(parent,CALENDAR,protocol,output)
            journal=json.loads((output/'q1-unpaired-explicit.json').read_text())
            self.assertEqual(len(journal['bid']),1)
            self.assertEqual(journal['bid'][0]['volume'],0)
            self.assertEqual(journal['ask'],[])
            self.assertEqual(proof['quarters'][0]['paired_rows'],2)
            self.assertTrue(review(output,CALENDAR,.001,require_explicit_source=True)['source_presence_verified'])

    def test_a_source_only_label_without_proof_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);parent,_=fixture(root)
            m=json.loads((parent/'manifest.json').read_text());m['sourceObservationPolicy']=POLICY;write(parent/'manifest.json',m)
            r=json.loads((parent/'result.json').read_text());r['sourceObservationPolicy']=POLICY;write(parent/'result.json',r)
            with self.assertRaisesRegex(ValueError,'source_observation_proof_binding'):review(parent,CALENDAR,.001)

    def test_changed_raw_cache_and_changed_view_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);parent,protocol=fixture(root);output=root/'explicit';proof=prepare(parent,CALENDAR,protocol,output)
            cache=Path(proof['quarters'][0]['sides'][0]['responses'][0]['path']);original=cache.read_bytes()
            cache.write_bytes(original+b' ')
            with self.assertRaisesRegex(ValueError,'input_or_code_changed'):review(output,CALENDAR,.001,require_explicit_source=True)
            cache.write_bytes(original)
            path=output/'q1-bid.json';path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'seal_binding'):review(output,CALENDAR,.001,require_explicit_source=True)

    def test_wrong_validator_even_with_rehashed_proof_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);parent,protocol=fixture(root);output=root/'explicit';prepare(parent,CALENDAR,protocol,output)
            path=output/'source-observation-proof.json';proof=json.loads(path.read_text());proof['validator_sha256']='0'*64;write(path,proof)
            result=json.loads((output/'result.json').read_text());result['sourceObservationProofSha256']=digest(path);write(output/'result.json',result)
            with self.assertRaisesRegex(ValueError,'source_observation_proof_contract'):review(output,CALENDAR,.001,require_explicit_source=True)

    def test_missing_raw_cannot_fall_back_to_native_or_network(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);parent,protocol=fixture(root);output=root/'explicit'
            next((parent/'cache').iterdir()).unlink()
            with self.assertRaisesRegex(ValueError,'source_cache_required_no_network_fallback'):
                prepare(parent,CALENDAR,protocol,output)
            self.assertTrue((output/'failure.json').is_file())
            self.assertFalse((output/'result.json').exists())


if __name__=='__main__':unittest.main()
