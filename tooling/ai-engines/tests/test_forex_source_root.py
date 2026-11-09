from pathlib import Path
import sys,tempfile,types,unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import forex_study_batch as batch


class SourceRootTests(unittest.TestCase):
    def test_missing_checkout_rejected_without_source_change(self):
        original=batch.V2
        with tempfile.TemporaryDirectory() as temp,self.assertRaisesRegex(ValueError,'invalid_forex_source_root'):
            batch.configure_source_root(temp)
        self.assertEqual(batch.V2,original)

    def test_loaded_models_from_another_checkout_cannot_mix(self):
        original=batch.V2
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in ('scripts/forex_h4_pilot.py','trading_workspace_v2/forex_study_registration.py'):
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.touch()
            fake=types.ModuleType('trading_workspace_v2.fixture')
            fake.__file__=str(root.parent/'another-checkout/fixture.py')
            with patch.dict(sys.modules,{'trading_workspace_v2.fixture':fake}):
                with self.assertRaisesRegex(ValueError,'already_loaded'):batch.configure_source_root(root)
        self.assertEqual(batch.V2,original)

    def test_same_checkout_keeps_explicit_source_identity(self):
        original=batch.V2;paths=list(sys.path)
        try:
            batch.configure_source_root(original)
            self.assertEqual(batch.V2,original.resolve())
            self.assertEqual(sys.path[0],str(original.resolve()))
        finally:
            batch.V2=original;sys.path[:]=paths
