"""Relocation checks without running personal integrations or reading their data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import plistlib
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ResourceMigrationTests(unittest.TestCase):
    def test_inventory_preserves_all_entries_and_exact_eight_agents(self):
        inventory = json.loads((ROOT / "resource-inventory.json").read_text())
        self.assertEqual(len(inventory["entries"]), 161)
        self.assertEqual(len({(e["group"], e["name"]) for e in inventory["entries"]}), 161)
        for entry in inventory["entries"]:
            self.assertTrue((ROOT / entry["destination"] / "SKILL.md").is_file())
        agents = [r for r in inventory["files"] if r["category"] == "agent"]
        self.assertEqual(len(agents), 8)
        for record in agents:
            self.assertEqual(record["source_sha256"], record["sha256"])
        for record in inventory["files"]:
            path = ROOT / record["destination"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record["sha256"], str(path))

    def test_all_preserved_python_resources_compile(self):
        for root in (ROOT / "skills", ROOT / "resources"):
            for path in root.rglob("*.py"):
                with self.subTest(path=str(path.relative_to(ROOT))):
                    compile(path.read_bytes(), str(path), "exec")

    def test_daemon_templates_reference_real_scripts_without_old_prefixes(self):
        for path in (ROOT / "skills").rglob("*.plist"):
            data = plistlib.loads(path.read_bytes())
            for arg in data.get("ProgramArguments", []):
                self.assertNotIn("__REPO_ROOT__//Users", arg)
                self.assertNotIn("OmarOS//Users", arg)
                if arg.startswith(str(ROOT)) and arg.endswith(".py"):
                    self.assertTrue(Path(arg).is_file(), arg)
            cwd = data.get("WorkingDirectory")
            if cwd:
                self.assertTrue(Path(cwd).is_dir(), cwd)

    def test_skill_tree_contains_no_private_execution_state(self):
        for path in (ROOT / "skills").rglob("*"):
            if path.is_file():
                self.assertNotIn(path.suffix, {".jsonl", ".db", ".sqlite", ".log", ".pem", ".key"})
                self.assertFalse(path.name.startswith(".env"))


if __name__ == "__main__":
    unittest.main()
