import unittest,tempfile,json,hashlib
from pathlib import Path
from unittest.mock import patch
from quant_core.research_fast_fail import *

class FastFailTests(unittest.TestCase):
    def profile(self):return dict(format='.py',findings=[])
    def metrics(self):return dict(net_R=10.,equity_R_DD=5.,static_R_loss=2.,worst_daily_R=1.,max_open_risk_USD=300.,cluster_R=[4.,6.],development_years=[2018,2023],SL_active_validated=True,signal_contract_status='CAUSAL_FROZEN')
    def test_scale_missing_nan_and_retention_are_not_passes(self):
        for kw in ({},dict(friction=float('nan'),median_stop=10,retention=1),dict(friction=1,median_stop=20,retention=.4)):
            self.assertFalse(toxicity_scale(self.profile(),**kw)['passed'])
    def test_cost_gate_boundary_and_scalper_flag(self):
        self.assertTrue(toxicity_scale(self.profile(),friction=1.2,median_stop=10,retention=.5)['passed'])
        self.assertIn('FRICTION_FRAGILITY_SCALPER',toxicity_scale(self.profile(),friction=3,median_stop=10,retention=1)['reasons'])
    def test_decimal_twelve_percent_equality_is_inclusive_without_tolerance(self):
        self.assertGreater(.084/.7,.12)
        self.assertTrue(toxicity_scale(self.profile(),friction=.084,median_stop=.7,retention=.5)['passed'])
        self.assertIn('STAGE0_FRICTION_SCALE_FAIL',toxicity_scale(self.profile(),friction=.084000000001,median_stop=.7,retention=.5)['reasons'])
        self.assertTrue(toxicity_scale(self.profile(),friction=.083999999999,median_stop=.7,retention=.5)['passed'])
    def test_improved_net_with_worse_DD_fails(self):
        base=self.metrics();c=dict(base,net_R=15,equity_R_DD=6)
        self.assertFalse(development_gate(c,base,inputs_sha256='a',recipe_sha256='b')['passed'])
    def test_endpoint_or_later_evidence_cannot_be_promoted(self):
        base=self.metrics()
        for override in (dict(SL_active_validated=False),dict(development_years=[2024,2026])):
            c=dict(base,net_R=15,equity_R_DD=4,**override)
            self.assertFalse(development_gate(c,base,inputs_sha256='a',recipe_sha256='b')['passed'])
    def test_invalid_magnitudes_boolean_clusters_and_baseline_scope_fail(self):
        base=self.metrics();c=dict(base,net_R=15,equity_R_DD=4)
        for value in (dict(c,static_R_loss=-1),dict(c,cluster_R=[True,True])):
            self.assertFalse(development_gate(value,base,inputs_sha256='a',recipe_sha256='b')['passed'])
        self.assertFalse(development_gate(c,dict(base,development_years=[2024,2026]),inputs_sha256='a',recipe_sha256='b')['passed'])
    def test_gate3_needs_real_committed_freeze_and_unchanged_source(self):
        base=self.metrics();d=development_gate(dict(base,net_R=15,equity_R_DD=4),base,inputs_sha256='a',recipe_sha256='b')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);src=root/'source';src.write_bytes(b'canonical');freeze=dict(decision_sha256=content_hash(d),source_pins={'source':hashlib.sha256(b'canonical').hexdigest()})
            p=root/'freeze.json';p.write_text(json.dumps(freeze))
            with patch('quant_core.research_fast_fail.subprocess.check_output',return_value=json.dumps(freeze).encode()):
                self.assertTrue(require_gate3(d,p,repository=root,observed_inputs_sha256='a',observed_recipe_sha256='b')['eligible_for_replay'])
                src.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'CHANGED'):require_gate3(d,p,repository=root,observed_inputs_sha256='a',observed_recipe_sha256='b')
