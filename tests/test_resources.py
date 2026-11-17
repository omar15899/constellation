"""Verify the inherited resource closure without reopening retired sources."""
from pathlib import Path
import hashlib
import json
import tomllib
import unittest

from constellation.claude import agent_document

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
        # Native Markdown is now generated from these exact preserved roles.
        # Keep historical projection provenance without treating duplicate
        # adapter copies as another maintained source of instructions.
        adapters = inventory['derived_adapters']
        self.assertEqual(len(adapters), 8)
        self.assertEqual({row['source'] for row in adapters}, set(agents))
        for row in adapters:
            canonical = SOURCE / row['source']
            data = tomllib.loads(canonical.read_text())
            self.assertEqual(row['generator'], 'constellation.claude.agent_document')
            self.assertEqual(row['runtime_destination'],
                             f"native/claude/agents/{data['name']}.md")
            provenance = row['previous_projection']
            self.assertEqual(provenance['category'], 'native-adapter')
            self.assertEqual(provenance['source_sha256'],
                             hashlib.sha256(canonical.read_bytes()).hexdigest())
            self.assertEqual(agent_document(data).split('---\n', 2)[2].strip(),
                             data['developer_instructions'].strip())


if __name__ == '__main__':
    unittest.main()
