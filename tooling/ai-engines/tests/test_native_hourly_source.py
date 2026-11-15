from pathlib import Path
import sys
import json
import hashlib
import tempfile
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from quant_core.native_hourly_source import PairedHourlyStore,native_recipes
from quant_core.market_data_store import BAR
from quant_core.ftmo_execution_and_calendar import gold_calendar
from prop_campaign_source import stamp
from prop_v10_signals import recipes
from prop_v6_data import aggregate
from quant_core.vectorized_stage0_scanner import DAY,HOUR


class NativeH1Tests(unittest.TestCase):
    def test_index_source_clock_reuses_known_prebreak_flat_without_next_quote_backfill(self):
        from prop_v11_campaign import us500_source_clock
        from quant_core.vectorized_stage0_scanner import measure
        first=stamp("2023-01-01");end=stamp("2024-01-01");at=stamp("2023-03-24T15:00")
        bars=np.zeros(3,dtype=BAR);bars["t"]=[at,stamp("2023-03-24T20:00"),stamp("2023-03-26T22:00")]
        bars["bo"]=[4100000,4120000,4110000];bars["ao"]=bars["bo"]+1000
        r=dict(id="fixture",family="F4",at=np.array([at]),side=np.array([1]),stop=np.array([4000000]))
        rows=measure("XAUUSD",r,bars,gold_calendar(first,end),first,end)
        self.assertFalse(rows[0]["ok"][0])
        fixed=us500_source_clock(rows,bars)
        self.assertTrue(fixed[0]["ok"][0])
        self.assertEqual(fixed[0]["exit_at"][0],stamp("2023-03-24T20:00"))
        self.assertEqual(fixed[0]["exit_price"][0],4120000)

    def test_us500_proxy_uses_index_units_and_legacy_carry_not_gold_commission_swap(self):
        from prop_v11_campaign import us500_proxy
        from quant_core.vectorized_stage0_scanner import measure
        at=stamp("2023-03-02T12:00");first=stamp("2023-01-01");end=stamp("2024-01-01")
        bars=np.zeros(4,dtype=BAR);bars["t"]=[at,at+int(8.5*HOUR),at+24*HOUR,at+int(32.5*HOUR)]
        bars["bo"]=[4100000,4120000,4140000,4130000];bars["ao"]=bars["bo"]+1000
        recipe=dict(id="fixture",family="F1",at=np.array([at]),side=np.array([1]),stop=np.array([4000000]))
        rows=us500_proxy(measure("XAUUSD",recipe,bars,gold_calendar(first,end),first,end),bars)
        result=rows[1]["model"]["SYM"]
        self.assertAlmostEqual(result["net"][0],34.5)
        self.assertAlmostEqual(result["net_R"][0],34.5/101)
        self.assertEqual(result["commission"][0],1)
        self.assertEqual(result["funding"][0],-2)
        self.assertEqual(rows[1]["friction"][0],3.5)

    def test_native_H1_matches_same_closed_frames_from_M1_without_changing_global_engine(self):
        first=stamp("2022-01-03");n=80*24*60
        rng=np.random.default_rng(28);close=110000+np.cumsum(rng.integers(-2,3,n))
        m=np.zeros(n,dtype=BAR);m["t"]=first+np.arange(n)*60000
        m["bo"]=np.r_[close[0],close[:-1]];m["bc"]=close
        m["bh"]=np.maximum(m["bo"],close)+1;m["bl"]=np.minimum(m["bo"],close)-1
        hours=aggregate(m);native=np.zeros(len(hours),dtype=BAR)
        for i,r in enumerate(hours):
            for k,v in zip(("t","bo","bh","bl","bc"),r[:5]):native[k][i]=v
        end=first+80*DAY;calendar=gold_calendar(first,end)
        baseline=recipes(m,"EURUSD",first,end,calendar)
        adapted=native_recipes(native,"GBPUSD",first,end,calendar)
        self.assertEqual(len(adapted),44)
        self.assertGreater(sum(len(r["at"]) for r in adapted),0)
        for a,b in zip(baseline,adapted):
            self.assertEqual(a["config"],b["config"])
            for field in ("at","side","stop"):np.testing.assert_array_equal(a[field],b[field])
        again=recipes(m,"EURUSD",first,end,calendar)
        np.testing.assert_array_equal(baseline[0]["at"],again[0]["at"])

    def test_hourly_source_verifies_hash_and_reports_unpaired_hour_without_filling(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);first=stamp("2022-01-03")
            books=[]
            for side,count in (("bid",2),("ask",1)):
                path=root/f"{side}.json"
                rows=[dict(timestamp=first+i*HOUR,open="1.10000",high="1.11000",low="1.09000",close="1.10000") for i in range(count)]
                path.write_text(json.dumps(rows))
                books.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                  first=first,last=first+(count-1)*HOUR,side=side,rows=count))
            store=PairedHourlyStore(dict(books=books,first=first,end=first+3*HOUR),first,first+3*HOUR)
            self.assertEqual(len(store.bars()),1)
            self.assertEqual(store.audit["unpaired_hours"],[first+HOUR])
            books[0]["sha256"]="0"*64
            with self.assertRaises(ValueError):store.bars()
