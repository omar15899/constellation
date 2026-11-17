"""Behavior checks for the preserved shared documentation utility."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'official_docs_under_test', SOURCE / 'resources/automations/official_docs.py')
assert SPEC and SPEC.loader
docs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(docs)


class OfficialDocsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name).resolve()

    def populate(self):
        with patch.object(docs, 'fetch', side_effect=lambda url, provider:
                          (b'# Synthetic official reference\nSubagent example.\n',
                           url, '2026-11-16T00:00:00+00:00')):
            return docs.refresh(self.home, 'claude')

    def test_shared_cli_verifies_and_searches_without_network(self):
        self.populate()
        command = [sys.executable, str(SOURCE / 'constellation.py'), 'docs',
                   '--home', str(self.home), '--provider', 'claude']
        verified = subprocess.run([*command, 'verify'], capture_output=True, text=True)
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertEqual(json.loads(verified.stdout)['integrity'], 'verified')
        searched = subprocess.run([*command, 'search', 'subagent', '--limit', '1'],
                                  capture_output=True, text=True)
        self.assertEqual(searched.returncode, 0, searched.stderr)
        self.assertEqual(len(json.loads(searched.stdout)), 1)

    def test_failed_refresh_preserves_current_reference(self):
        self.populate()
        root = self.home / '.claude/docs/official'
        before = {p.name: p.read_bytes() for p in root.iterdir()}
        with patch.object(docs, 'fetch', side_effect=OSError('offline')):
            with self.assertRaises(OSError):
                docs.refresh(self.home, 'claude')
        self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})
        self.assertEqual(docs.verify(self.home, 'claude')['integrity'], 'verified')

    def test_changed_reference_is_rejected(self):
        self.populate()
        (self.home / '.claude/docs/official/settings.md').write_text('# Altered\n')
        with self.assertRaises(docs.DocsError):
            docs.verify(self.home, 'claude')

    def test_linked_reference_is_rejected(self):
        self.populate()
        path = self.home / '.claude/docs/official/settings.md'
        retained = self.home / 'retained.md'
        path.rename(retained)
        path.symlink_to(retained)
        with self.assertRaises((docs.DocsError, OSError)):
            docs.verify(self.home, 'claude')
        self.assertTrue(retained.is_file())

    def test_external_or_credentialled_urls_are_rejected(self):
        for url in ('https://example.com/doc.md',
                    'https://name:password@code.claude.com/docs/en/hooks.md',
                    'http://code.claude.com/docs/en/hooks.md'):
            with self.subTest(url=url), self.assertRaises(docs.DocsError):
                docs.validate_url(url, 'claude')


if __name__ == '__main__':
    unittest.main()
