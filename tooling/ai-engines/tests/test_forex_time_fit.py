import copy
from decimal import Decimal
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import forex_time_fit as timefit
import forex_h4_pilot as pilot
from trading_workspace_v2.replay_tick_execution import BrokerReplayTick


class TimeFitTests(unittest.TestCase):
    def test_sealed_horizons_reconcile_and_tampering_never_qualifies(self):
        ticks=[BrokerReplayTick(time_msc=pilot.START+i*3600000+1,sequence=i+1,
            bid='1.10000',ask='1.10020') for i in range(10)]
        cutoffs=[pilot.START+4*3600000,pilot.START+8*3600000]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch.object(pilot,'read_qdm_ticks',return_value=iter(ticks)):
                result=pilot.run_scenario(Path('unused'),[],'reference',Decimal(0),Decimal(0),
                    root,lambda *args:None,horizon_cutoffs=cutoffs)
            manifest=dict(run_id='synthetic',horizon_cutoffs=cutoffs,scenarios=[dict(name='reference',slippage='0')])
            (root/'quality.json').write_text('{}')
            pilot.seal_scenario(root,manifest,result)
            rows=timefit.inspect_horizons(root,manifest,'reference')
            self.assertEqual([row['observed_ticks'] for row in rows],[4,8])
            self.assertEqual(rows[0]['equity_delta_usd'],'0')
            self.assertEqual(rows[0]['full_prop_time_to_pass'],'not_evaluated')
            self.assertFalse(rows[0]['promotion_authorized'])
            file=root/'reference-horizons.json'
            original=json.loads(file.read_bytes())
            for kind in ('money','future','cutoff','promotion'):
                with self.subTest(kind=kind):
                    modified=copy.deepcopy(original)
                    if kind=='money': modified[0]['checkpoint']['execution'].update(balance='10001',equity='10001')
                    if kind=='future': modified[0]['decisions'].append(dict(time_msc=cutoffs[0]+1))
                    if kind=='cutoff': modified[0]['cutoff_msc']+=1
                    if kind=='promotion': modified[0]['promotion_authorized']=True
                    file.write_text(json.dumps(modified))
                    with self.assertRaisesRegex(ValueError,'seal'):
                        timefit.inspect_horizons(root,manifest,'reference')
                    # Even a freshly checksummed bad packet fails semantic checks.
                    pilot.seal_scenario(root,manifest,result)
                    with self.assertRaises(ValueError):
                        timefit.inspect_horizons(root,manifest,'reference')
                    file.write_text(json.dumps(original)); pilot.seal_scenario(root,manifest,result)


if __name__=='__main__': unittest.main()
