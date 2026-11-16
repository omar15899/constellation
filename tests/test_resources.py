"""Verify the inherited resource closure without reopening retired sources."""
from pathlib import Path
import hashlib
import json
import unittest

SOURCE = Path(__file__).resolve().parents[1]


class InheritedResourcesTests(unittest.TestCase):
    def test_every_inventoried_resource_matches_and_all_eight_agents_are_exact(self):
        inventory = json.loads((SOURCE / 'resource-inventory.json').read_text())
        self.assertEqual(len(inventory['entries']), 161)
        seen = set()
        agents = []
        for item in inventory['files']:
            relative = item['destination']
            self.assertNotIn(relative, seen)
            seen.add(relative)
            path = SOURCE / relative
            self.assertTrue(path.resolve().is_relative_to(SOURCE), relative)
            self.assertFalse(path.is_symlink(), relative)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item['sha256'], relative)
            if item['category'] == 'agent':
                agents.append(relative)
                self.assertEqual(item['source_sha256'], item['sha256'], relative)
        self.assertEqual(len(agents), 8)


if __name__ == '__main__':
    unittest.main()
