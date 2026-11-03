#!/usr/bin/env python3
"""Offline behavior tests for the local public-documentation snapshot tool."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.request import Request

SPEC = importlib.util.spec_from_file_location("official_docs", Path(__file__).parents[1] / "profiles" / "official_docs.py")
assert SPEC and SPEC.loader
docs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(docs)


class DocumentationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name).resolve()
        self.selection = {"guide.md": "https://code.claude.com/docs/en/guide.md"}
        self.sources = patch.object(docs, "sources", return_value=self.selection)
        self.sources.start()
        self.addCleanup(self.sources.stop)

    def fetch(self, url, provider):
        return b"# Guide\n\nSubagents preserve context.\n", url, "2026-11-03T00:00:00+00:00"

    def refresh(self):
        with patch.object(docs, "fetch", side_effect=self.fetch):
            return docs.refresh(self.home, "claude")

    def snapshot(self):
        return self.home / ".claude/docs/official"

    def test_refresh_verify_and_search_without_network(self):
        result = self.refresh()
        self.assertEqual(result["files"], 1)
        with patch.object(docs, "fetch", side_effect=AssertionError("network forbidden")):
            self.assertEqual(docs.verify(self.home, "claude")["integrity"], "verified")
            matches = docs.search(self.home, "claude", "SUBAGENTS")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["line"], 3)
        manifest = json.loads((self.snapshot() / "manifest.json").read_text())
        self.assertEqual(manifest["files"]["guide.md"]["url"], self.selection["guide.md"])
        self.assertIn("official source", (self.snapshot() / "INDEX.md").read_text())

    def test_tampered_document_fails_verify_and_search(self):
        self.refresh()
        (self.snapshot() / "guide.md").write_text("# Modified\n")
        with self.assertRaises(docs.DocsError):
            docs.verify(self.home, "claude")
        with self.assertRaises(docs.DocsError):
            docs.search(self.home, "claude", "Modified")

    def test_failed_download_preserves_current_snapshot(self):
        self.refresh()
        before = (self.snapshot() / "manifest.json").read_bytes()
        with patch.object(docs, "fetch", side_effect=OSError("provider unavailable")):
            with self.assertRaises(OSError):
                docs.refresh(self.home, "claude")
        self.assertEqual((self.snapshot() / "manifest.json").read_bytes(), before)
        self.assertEqual(docs.verify(self.home, "claude")["integrity"], "verified")

    def test_failed_promotion_restores_current_snapshot(self):
        self.refresh()
        before = (self.snapshot() / "manifest.json").read_bytes()
        real_rename = Path.rename

        def rename(path, target):
            if path.name.startswith(".official.next-"):
                raise OSError("promotion failed")
            return real_rename(path, target)

        with patch.object(docs, "fetch", side_effect=self.fetch), patch.object(Path, "rename", rename):
            with self.assertRaises(OSError):
                docs.refresh(self.home, "claude")
        self.assertEqual((self.snapshot() / "manifest.json").read_bytes(), before)
        self.assertEqual(docs.verify(self.home, "claude")["integrity"], "verified")

    def test_next_refresh_restores_interrupted_promotion(self):
        self.refresh()
        self.snapshot().rename(self.snapshot().parent / ".official.previous")
        with patch.object(docs, "fetch", side_effect=OSError("offline")):
            with self.assertRaises(OSError):
                docs.refresh(self.home, "claude")
        self.assertEqual(docs.verify(self.home, "claude")["integrity"], "verified")

    def test_two_refreshes_keep_one_recoverable_previous_snapshot(self):
        self.refresh()
        self.refresh()
        self.refresh()
        previous = self.snapshot().parent / ".official.previous"
        self.assertTrue(previous.is_dir())
        docs.inspect_snapshot(previous, "claude")

    def test_symlink_directory_is_rejected_without_touching_target(self):
        outside = self.home / "outside"
        outside.mkdir()
        (self.home / ".claude").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(docs.DocsError):
            self.refresh()
        self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_document_and_lock_are_rejected(self):
        self.refresh()
        document = self.snapshot() / "guide.md"
        original = self.home / "outside.md"
        document.rename(original)
        document.symlink_to(original)
        with self.assertRaises((docs.DocsError, OSError)):
            docs.verify(self.home, "claude")
        lock = self.snapshot().parent / ".official.lock"
        lock.unlink()
        lock.symlink_to(original)
        with self.assertRaises((docs.DocsError, OSError)):
            self.refresh()

    def test_external_urls_credentials_and_redirects_are_rejected(self):
        for url in ("http://code.claude.com/docs/a.md", "https://evil.example/a.md",
                    "https://code.claude.com.evil.example/a.md", "https://user:secret@code.claude.com/docs/a.md",
                    "https://code.claude.com:444/docs/a.md"):
            with self.subTest(url=url), self.assertRaises(docs.DocsError):
                docs.validate_url(url, "claude")
        handler = docs.OfficialRedirects("claude")
        with self.assertRaises(docs.DocsError):
            handler.redirect_request(Request(self.selection["guide.md"]), None, 302, "Found", {}, "https://evil.example")
        self.assertIsNotNone(handler.redirect_request(Request(self.selection["guide.md"]), None, 302, "Found", {},
                                                     "https://code.claude.com/docs/en/other.md"))

    def test_html_empty_and_oversized_content_rejected(self):
        for content, kind in ((b"", "text/plain"), (b"<html>error</html>", "text/html"),
                              (b"<!doctype html><html>oops", "text/plain"),
                              (b"# Fake\x00body", "text/plain"), (b"not documentation", "text/plain")):
            with self.subTest(content=content), self.assertRaises(docs.DocsError):
                docs.validate_text(content, kind)
        with patch.object(docs, "MAX_BYTES", 5), self.assertRaises(docs.DocsError):
            docs.validate_text(b"# Too large\n", "text/plain")
        docs.validate_text(b"> ## Official documentation\n", "text/markdown")
        docs.validate_text(b'---\ntitle: "Codex Manual"\n---\n\n# Manual\n', "application/octet-stream")

    def test_untracked_files_and_bad_provenance_rejected(self):
        self.refresh()
        extra = self.snapshot() / "untracked.md"
        extra.write_text("# unexpected\n")
        with self.assertRaises(docs.DocsError):
            docs.verify(self.home, "claude")
        extra.unlink()
        manifest_path = self.snapshot() / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"]["guide.md"]["final_url"] = "https://evil.example/a.md"
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaises(docs.DocsError):
            docs.verify(self.home, "claude")

    def test_search_limit_and_empty_query(self):
        self.refresh()
        self.assertEqual(len(docs.search(self.home, "claude", "Guide", limit=1)), 1)
        with self.assertRaises(docs.DocsError):
            docs.search(self.home, "claude", "   ")


if __name__ == "__main__":
    unittest.main(verbosity=2)
