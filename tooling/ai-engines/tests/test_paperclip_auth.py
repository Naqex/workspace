import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import paperclip_setup


class OperatorAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.store = root / '.runtime/paperclip/auth.json'
        self.store.parent.mkdir(parents=True)
        self.patcher = patch.object(paperclip_setup, 'ROOT', root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.origin = f"http://{paperclip_setup.SERVICES['host']}:{paperclip_setup.SERVICES['paperclipPort']}"

    def write(self, credentials):
        self.store.write_text(json.dumps({'version': 1, 'credentials': credentials}), encoding='utf-8')

    def test_local_mode_without_credentials_and_unrelated_origins(self):
        self.assertNotIn('Authorization', paperclip_setup.operator_headers(self.origin))
        self.write({'http://127.0.0.1:3100': {'token': 'other-instance'}})
        self.assertNotIn('Authorization', paperclip_setup.operator_headers(self.origin))

    def test_native_cli_credential_is_used_for_exact_project_origin(self):
        self.write({self.origin: {'apiBase': self.origin, 'token': 'test-board-token'}})
        with patch.object(paperclip_setup, 'urlopen') as request:
            request.return_value.__enter__.return_value.read.return_value = b'[]'
            self.assertEqual(paperclip_setup.api('/companies'), [])
            sent = request.call_args.args[0]
            self.assertEqual(sent.full_url, self.origin + '/api/companies')
            self.assertEqual(sent.get_header('Authorization'), 'Bearer test-board-token')

    def test_invalid_store_never_falls_back_to_implicit_authority(self):
        self.write({self.origin: {'apiBase': 'http://127.0.0.1:3100', 'token': 'wrong'}})
        with patch.object(paperclip_setup, 'urlopen') as request:
            with self.assertRaises(ValueError): paperclip_setup.api('/companies')
            request.assert_not_called()

    def test_revoked_credential_is_not_retried_anonymously(self):
        self.write({self.origin: {'apiBase': self.origin, 'token': 'revoked'}})
        with patch.object(paperclip_setup, 'urlopen', side_effect=HTTPError(self.origin, 401, 'Unauthorized', {}, None)) as request:
            with self.assertRaises(HTTPError): paperclip_setup.api('/companies')
            self.assertEqual(request.call_count, 1)


if __name__ == '__main__':
    unittest.main()
