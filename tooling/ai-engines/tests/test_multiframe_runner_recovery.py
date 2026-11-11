"""CLI lifecycle roundtrip on synthetic quotes; no financial/source downloads."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import run_us500_multiframe as runner
import us500_multiframe as study
from test_us500_multiframe import fixture


class RunnerRecoveryTests(unittest.TestCase):
    def invoke(self,args,pairs,prepared):
        with patch.object(sys,'argv',['runner',*args]),patch.object(runner,'load_year',return_value=({},pairs,{'bindings':{}})),patch.object(study,'prepare',return_value=prepared),redirect_stdout(io.StringIO()):
            runner.main()

    def test_failed_book_preserved_and_resume_reuses_only_sealed_books(self):
        pairs,prepared,_=fixture()
        prepared['counts']={}
        execute=study.execute
        calls=0

        def fail_third(*a,**kw):
            nonlocal calls
            calls+=1
            if calls==3:
                raise RuntimeError('synthetic_failure')
            return execute(*a,**kw)

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            protocol=root/'synthetic.md'
            protocol.write_text('synthetic recovery test, not economic registration',encoding='utf-8')
            args=['--data-root',str(root/'input'),'--output',str(root/'output'),
                  '--protocol',str(protocol),'--protocol-sha256',hashlib.sha256(protocol.read_bytes()).hexdigest(),'--year','2022']
            with patch.object(study,'execute',side_effect=fail_third):
                with self.assertRaisesRegex(RuntimeError,'synthetic_failure'):
                    self.invoke(args,pairs,prepared)
            output=root/'output'
            self.assertEqual(len(list(output.glob('*-seal.json'))),2)
            self.assertEqual(json.loads((output/'progress.json').read_text())['stage'],'failed')
            self.assertFalse((output/'controller.lock').exists())
            original=(output/'2022-R096-reference.json').read_bytes()
            with patch.object(study,'execute',wraps=execute) as spy:
                self.invoke([*args,'--resume-completed'],pairs,prepared)
                self.assertEqual(spy.call_count,55)
            final=json.loads((output/'result.json').read_text())
            self.assertEqual(len(final['rows']),57)
            self.assertEqual(sum(x.get('reused',False) for x in final['timings']),2)
            self.assertEqual(original,(output/'2022-R096-reference.json').read_bytes())
            self.assertTrue((output/'failure.json').exists())
            # A sealed result cannot be silently accepted after mutation.
            (output/'2022-R096-reference.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'completed_book_seal_drift'):
                self.invoke([*args,'--resume-completed'],pairs,prepared)


if __name__=='__main__':
    unittest.main()
