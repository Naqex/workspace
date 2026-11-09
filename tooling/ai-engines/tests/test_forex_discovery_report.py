import contextlib,hashlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import forex_discovery_report as reporter
import forex_h4_pilot as pilot
sys.path.insert(0,str(reporter.V2/'tests'))
from test_forex_discovery_candidates import bar
from trading_workspace_v2.forex_discovery_candidates import RANGE_FADE
from trading_workspace_v2.replay_tick_execution import BrokerReplayTick


class DiscoveryReportTests(unittest.TestCase):
    def test_real_sealed_synthetic_batch_reconciles_and_refuses_mismatched_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);protocol=root/'protocol.md';protocol.write_text('Generated fixture only')
            inputs=dict(schema='forex-h4-inputs-v1',
                warmup=dict(path=str(root/'w.csv'),sha256='a'*64,first_day='20211201',last_day='20211231'),
                development=dict(path=str(root/'d.csv'),sha256='b'*64,first_day='20220103',last_day='20220331'))
            input_path=root/'inputs.json';input_path.write_text(json.dumps(inputs))
            ticks=[BrokerReplayTick(time_msc=pilot.START+i*3600000+1,sequence=i+1,bid='1.10000',ask='1.10020') for i in range(48)]
            argv=['--input-dir',str(root),'--input-manifest',str(input_path),'--candidate',RANGE_FADE,
                '--research-protocol',str(protocol),'--account-spec',str(root/'spec.json'),
                '--account-spec-sha256','c'*64,'--output-dir',str(root/'replay')]
            with patch.object(pilot,'observed_account_spec',return_value=dict(sha256='c'*64,
                    debit_buy_usd_per_lot='9.3',debit_sell_usd_per_lot='-.31')),\
                 patch.object(pilot,'inspect_qdm',return_value=(dict(ticks=48,complete_h4=81),[bar(i) for i in range(-81,0)])),\
                 patch.object(pilot,'read_qdm_ticks',return_value=iter(ticks)),contextlib.redirect_stdout(io.StringIO()):
                # Each scenario requires its own iterator.
                with patch.object(pilot,'read_qdm_ticks',side_effect=lambda *args,**kwargs:iter(ticks)):
                    pilot.main(argv)
            manifest=json.loads((root/'replay/manifest.json').read_bytes())
            (root/'batch-terminal.json').write_text(json.dumps(dict(status='completed_verified',
                workers=[dict(worker='fixture',result_dir=str(root/'replay'))])))
            screen=dict(schema='forex-h4-flat-feasibility-screen-v1',portfolio_simulated=False,
                inputs=manifest['inputs'],protocol_sha256=manifest['research_protocol']['sha256'],
                source_files={name:hashlib.sha256((reporter.V2/name).read_bytes()).hexdigest() for name in reporter.SCREEN_SOURCE_FILES},
                rows=[dict(candidate=RANGE_FADE,reason='no_entry_opportunities_in_window',flat_entry_opportunities=0)])
            path=root/'screen.json';path.write_text(json.dumps(screen))
            result=reporter.build_report(root,path)
            self.assertEqual(len(result['rows']),2)
            self.assertEqual(result['decisions']['fixture'],'inconclusive_insufficient_fills')
            self.assertFalse(result['promotion_authorized'])
            self.assertIn('ledger DD',reporter.render(result))
            for change in ('protocol','candidate','duplicate','portfolio','source'):
                from copy import deepcopy
                bad=deepcopy(screen)
                if change=='protocol':bad['protocol_sha256']='0'*64
                if change=='candidate':bad['rows']=[]
                if change=='duplicate':bad['rows']*=2
                if change=='portfolio':bad['portfolio_simulated']=True
                if change=='source':bad['source_files'].pop('scripts/forex_signal_screen.py')
                path.write_text(json.dumps(bad))
                with self.subTest(change=change),self.assertRaises(ValueError):reporter.build_report(root,path)


if __name__=='__main__':unittest.main()
