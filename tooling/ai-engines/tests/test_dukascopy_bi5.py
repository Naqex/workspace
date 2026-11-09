import lzma,struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dukascopy_bi5 import decode_ticks,HOUR

START=1548424800000
def encode(records):return lzma.compress(b''.join(struct.pack('>iiiff',*r) for r in records),format=lzma.FORMAT_ALONE)
def run(raw,**kw):return decode_ticks(raw,hour_start=START,price_factor=1000,**kw)


class BI5Tests(unittest.TestCase):
    def test_known_layout_side_factor_milliseconds_and_duplicate_ordinal(self):
        records=[(71,6738730,6737660,.5,.25),(71,6738800,6737700,.75,.5),(1000,6738900,6737800,1,2)]
        result=run(encode(records));rows=result['rows']
        self.assertEqual(result['record_count'],3)
        self.assertEqual(rows[0],dict(timestamp=START+71,askPrice=6738.73,bidPrice=6737.66,askVolume=.5,bidVolume=.25))
        self.assertEqual(rows[1]['timestamp'],rows[0]['timestamp']);self.assertNotEqual(rows[1]['bidPrice'],rows[0]['bidPrice'])
        self.assertEqual(result['decompressed_bytes'],60)

    def test_truncated_trailing_and_incomplete_record_are_rejected(self):
        raw=encode([(0,2000,1000,1,1)])
        for changed in [raw[:-1],raw+b'extra',lzma.compress(b'\0'*21,format=lzma.FORMAT_ALONE)]:
            with self.subTest(length=len(changed)),self.assertRaises(ValueError):run(changed)

    def test_scope_order_prices_and_volumes(self):
        for bad in [(-1,2000,1000,1,1),(HOUR,2000,1000,1,1),(0,1000,2000,1,1),(0,2000,0,1,1),
                    (0,2000,1000,float('nan'),1),(0,2000,1000,1,float('inf')),(0,2000,1000,-1,1)]:
            with self.subTest(record=bad),self.assertRaises(ValueError):run(encode([bad]))
        with self.assertRaisesRegex(ValueError,'order'):
            run(encode([(10,2000,1000,1,1),(9,2000,1000,1,1)]))

    def test_bounded_resource_and_closed_holdout(self):
        raw=encode([(0,2000,1000,1,1)])
        with self.assertRaisesRegex(ValueError,'oversize'):run(raw,compressed_cap=len(raw)-1)
        with self.assertRaisesRegex(ValueError,'size_cap'):run(raw,uncompressed_cap=19)
        with self.assertRaisesRegex(ValueError,'resource'):run(raw,memory_cap=0)
        with self.assertRaisesRegex(ValueError,'holdout'):
            decode_ticks(raw,hour_start=1735689600000,price_factor=1000)
        with self.assertRaisesRegex(ValueError,'factor'):
            decode_ticks(raw,hour_start=START,price_factor=0)

    def test_valid_compressed_empty_source_is_distinct_from_empty_HTTP_body(self):
        self.assertEqual(run(lzma.compress(b'',format=lzma.FORMAT_ALONE))['record_count'],0)
        with self.assertRaisesRegex(ValueError,'empty'):run(b'')


if __name__=='__main__':unittest.main()
