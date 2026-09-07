"""A failed Git status must never become evidence of a clean worktree."""

from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import discover_repos as discovery


class GitStateTests(unittest.TestCase):
    def test_successful_status_distinguishes_clean_and_dirty(self):
        for porcelain, expected in (("", "clean"), (" M README.md\n", "dirty")):
            with self.subTest(expected=expected), patch.object(
                discovery.subprocess, "run",
                return_value=subprocess.CompletedProcess([], 0, porcelain, ""),
            ):
                self.assertEqual(discovery.git_state("/fixture")["state"], expected)

    def test_git_error_is_unknown_even_with_empty_stdout(self):
        with patch.object(discovery.subprocess, "run", return_value=
                          subprocess.CompletedProcess([], 128, "", "not a repository")):
            self.assertEqual(discovery.git_state("/fixture")["state"], "unknown")

    def test_timeout_or_missing_binary_is_unknown(self):
        for error in (subprocess.TimeoutExpired("git", 5), FileNotFoundError("git")):
            with self.subTest(error=type(error).__name__), patch.object(
                discovery.subprocess, "run", side_effect=error,
            ):
                self.assertEqual(discovery.git_state("/fixture")["state"], "unknown")


if __name__ == "__main__":
    unittest.main()
