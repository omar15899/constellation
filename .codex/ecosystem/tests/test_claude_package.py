"""Exercise dual-native release projection, integrity and relocation offline."""
from __future__ import annotations

from itertools import combinations
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import tomllib
import unittest


sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE / "ecosystem"))
import build as builder
import claude as claude_installer
from validate import validate


class ClaudePackageTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="dual-native-release-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.bundle = self.root / "release"
        self.manifest = builder.build_bundle(self.bundle, source_root=SOURCE)

    def source_copy(self) -> Path:
        target = self.root / "source"
        shutil.copytree(self.bundle, target)
        (target / "bundle.json").unlink()
        for distributed, canonical in (
            (builder.PLUGIN_MANIFEST, "ecosystem/manifests/codex-plugin.json"),
            (builder.CLAUDE_PLUGIN_MANIFEST, "ecosystem/manifests/claude-plugin.json"),
            ("ecosystem/hooks.json", "ecosystem/manifests/codex-hooks.json"),
            ("ecosystem/claude-hooks.json", "ecosystem/manifests/claude-hooks.json"),
        ):
            (target / canonical).parent.mkdir(parents=True, exist_ok=True)
            (target / distributed).replace(target / canonical)
            if distributed.startswith("."):
                (target / distributed).parent.rmdir()
        shutil.rmtree(target / "agents")
        return target

    def test_both_manifests_name_one_release_and_native_component_paths(self) -> None:
        codex = json.loads((self.bundle / builder.PLUGIN_MANIFEST).read_text())
        claude = json.loads((self.bundle / builder.CLAUDE_PLUGIN_MANIFEST).read_text())
        self.assertEqual(codex["name"], claude["name"])
        self.assertEqual(codex["version"], claude["version"])
        self.assertEqual(claude["skills"], "./skills/")
        self.assertNotIn("agents", claude)
        self.assertEqual(claude["hooks"], "./ecosystem/claude-hooks.json")
        self.assertEqual(validate(self.bundle), [])

    def test_markdown_roles_preserve_canonical_body_and_inherit_runtime_choices(self) -> None:
        roles = list((self.bundle / "agents").glob("*.md"))
        expected = {"researcher", "reviewer", "security-reviewer", "verifier"}
        modules = {"coding": {"coder"}, "mathematics": {"mathematician", "counterexample"},
                   "quant-research": {"coder", "mathematician", "counterexample"},
                   "writter": {"editor", "mathematician", "coder"}}
        for module in self.manifest["modules"]:
            expected.update(modules[module])
        self.assertEqual({path.stem for path in roles}, expected)
        for path in roles:
            canonical = tomllib.loads((self.bundle / "ecosystem/agents" / (path.stem + ".toml")).read_text())
            _, metadata, body = path.read_text().split("---", 2)
            fields = {line.split(": ", 1)[0]: json.loads(line.split(": ", 1)[1])
                      for line in metadata.strip().splitlines()}
            self.assertEqual(fields, {"name": canonical["name"].replace("_", "-"),
                                      "description": canonical["description"], "model": "inherit"})
            self.assertEqual(body.strip(), canonical["developer_instructions"].strip())

    def test_every_module_subset_ships_exactly_its_shared_native_roles(self) -> None:
        available = self.manifest["modules"]
        for count in range(1, len(available) + 1):
            for group in combinations(available, count):
                target = self.root / ("subset-" + "-".join(group))
                builder.build_bundle(target, group, self.bundle)
                canonical = {path.stem for path in (target / "ecosystem/agents").glob("*.toml")}
                projected = {path.stem for path in (target / "agents").glob("*.md")}
                self.assertEqual(projected, canonical)
                self.assertEqual(builder.verify_bundle(target)["modules"], list(group))

    def test_relocated_bundle_rebuilds_without_checkout_or_machine_paths(self) -> None:
        relocated = self.root / "another laptop with spaces" / "release"
        relocated.parent.mkdir()
        shutil.move(self.bundle, relocated)
        rebuilt = self.root / "rebuilt"
        manifest = builder.build_bundle(rebuilt, source_root=relocated)
        self.assertEqual(manifest, self.manifest)
        self.assertEqual(validate(rebuilt), [])

    def test_archives_are_byte_reproducible_across_paths(self) -> None:
        rebuilt = self.root / "rebuilt"
        builder.build_bundle(rebuilt, source_root=self.bundle)
        one, two = self.root / "one.zip", self.root / "two.zip"
        builder.write_archive(self.bundle, one)
        builder.write_archive(rebuilt, two)
        self.assertEqual(one.read_bytes(), two.read_bytes())

    def test_generated_role_drift_is_rejected_even_with_refreshed_inventory_hash(self) -> None:
        role = self.bundle / "agents/researcher.md"
        role.write_text(role.read_text().replace('model: "inherit"', 'model: "sonnet"'))
        manifest = json.loads((self.bundle / "bundle.json").read_text())
        manifest["files"]["agents/researcher.md"] = builder.file_record(role)
        (self.bundle / "bundle.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(builder.BundleError, "canonical source"):
            builder.verify_bundle(self.bundle)
        self.assertTrue(any("canonical role" in error for error in validate(self.bundle)))

    def test_canonical_role_change_regenerates_the_native_projection(self) -> None:
        source = self.source_copy()
        role = source / "ecosystem/agents/researcher.toml"
        role.write_text(role.read_text().replace("Explicita la decisión", "Precisa la decisión"))
        rebuilt = self.root / "changed"
        builder.build_bundle(rebuilt, self.manifest["modules"], source_root=source)
        self.assertNotEqual((rebuilt / "agents/researcher.md").read_bytes(),
                            (self.bundle / "agents/researcher.md").read_bytes())
        self.assertEqual(validate(rebuilt), [])

    def test_source_and_bundle_resources_have_one_comparison_mapping(self) -> None:
        for relative in self.manifest["files"]:
            content, mode = builder.source_resource(SOURCE, relative)
            self.assertEqual(hashlib.sha256(content).hexdigest(), self.manifest["files"][relative]["sha256"])
            self.assertEqual(mode, self.manifest["files"][relative]["mode"])

    def test_native_versions_cannot_diverge(self) -> None:
        source = self.source_copy()
        path = source / "ecosystem/manifests/claude-plugin.json"
        metadata = json.loads(path.read_text())
        path.write_text(json.dumps({**metadata, "version": "99.0.0"}))
        with self.assertRaisesRegex(builder.BundleError, "versions differ"):
            builder.build_bundle(self.root / "bad-release", self.manifest["modules"], source_root=source)
        self.assertTrue(any("versions must agree" in error for error in validate(source)))

    def test_duplicate_bundle_keys_cannot_pass_installer_preflight(self) -> None:
        path = self.bundle / "bundle.json"
        original = path.read_text()
        mode = next(iter(self.manifest["files"].values()))["mode"]
        variants = {
            "root": '{"schema":1,' + original[1:],
            "nested-record": original.replace(f'"mode": {mode}',
                                               f'"mode": {mode}, "mode": {mode}', 1),
        }
        for label, text in variants.items():
            with self.subTest(location=label):
                self.assertNotEqual(text, original)
                path.write_text(text)
                with self.assertRaises(builder.BundleError):
                    builder.verify_bundle(self.bundle)
                home = self.root / ("rejected-" + label)
                with self.assertRaises(builder.BundleError):
                    claude_installer.install_bundle(self.bundle, home, check=True)
                self.assertFalse(home.exists())

    def test_duplicate_native_metadata_is_rejected_even_with_matching_inventory(self) -> None:
        variants = (
            (builder.PLUGIN_MANIFEST, "root"),
            (builder.CLAUDE_PLUGIN_MANIFEST, "root"),
            (builder.CLAUDE_PLUGIN_MANIFEST, "author"),
        )
        for index, (relative, location) in enumerate(variants):
            with self.subTest(manifest=relative, location=location):
                candidate = self.root / f"ambiguous-native-{index}"
                shutil.copytree(self.bundle, candidate)
                path = candidate / relative
                text = path.read_text()
                duplicate = ('{"name":"constellation",' + text[1:] if location == "root"
                             else text.replace('"name": "Constellation"',
                                               '"name": "Constellation", "name": "Constellation"', 1))
                self.assertNotEqual(duplicate, text)
                path.write_text(duplicate)
                manifest = json.loads((candidate / "bundle.json").read_text())
                manifest["files"][relative] = builder.file_record(path)
                (candidate / "bundle.json").write_text(json.dumps(manifest))
                with self.assertRaises(builder.BundleError):
                    builder.verify_bundle(candidate)

    def test_source_build_rejects_duplicate_native_metadata_before_creating_output(self) -> None:
        source = self.source_copy()
        variants = (("ecosystem/manifests/codex-plugin.json", "root"),
                    ("ecosystem/manifests/claude-plugin.json", "root"),
                    ("ecosystem/manifests/claude-plugin.json", "author"))
        for index, (relative, location) in enumerate(variants):
            with self.subTest(manifest=relative, location=location):
                candidate = self.root / f"ambiguous-source-{index}"
                shutil.copytree(source, candidate)
                path = candidate / relative
                text = path.read_text()
                duplicate = ('{"name":"constellation",' + text[1:] if location == "root"
                             else text.replace('"name": "Constellation"',
                                               '"name": "Constellation", "name": "Constellation"', 1))
                self.assertNotEqual(duplicate, text)
                path.write_text(duplicate)
                output = self.root / f"rejected-source-{index}"
                with self.assertRaises(builder.BundleError):
                    builder.build_bundle(output, self.manifest["modules"], source_root=candidate)
                self.assertFalse(output.exists())

    def test_bundle_schema_requires_integer_one_and_exact_top_level_fields(self) -> None:
        path = self.bundle / "bundle.json"
        for label, manifest in (("boolean", {**self.manifest, "schema": True}),
                                ("extra-field", {**self.manifest, "unexpected": True})):
            with self.subTest(case=label):
                path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(builder.BundleError, "Unsupported bundle schema"):
                    builder.verify_bundle(self.bundle)

    def test_runtime_choices_cannot_be_added_to_the_canonical_role(self) -> None:
        source = self.source_copy()
        role = source / "ecosystem/agents/researcher.toml"
        role.write_text(role.read_text() + '\nmodel = "opus"\n')
        with self.assertRaisesRegex(builder.BundleError, "inherit runtime choices"):
            builder.build_bundle(self.root / "forced-model", self.manifest["modules"], source_root=source)

    def test_native_hook_failure_policy_is_structurally_required(self) -> None:
        source = self.source_copy()
        path = source / "ecosystem/manifests/claude-hooks.json"
        hooks = json.loads(path.read_text())
        hooks["hooks"]["PreToolUse"][0]["hooks"][0].pop("onFailure")
        path.write_text(json.dumps(hooks))
        self.assertTrue(any("declared failure policy" in error for error in validate(source)))

    def test_only_explicit_installed_metadata_is_permitted(self) -> None:
        receipt = self.bundle / builder.INSTALL_RECEIPT
        receipt.write_text("{}\n")
        receipt.chmod(0o600)
        with self.assertRaises(builder.BundleError):
            builder.verify_bundle(self.bundle)
        self.assertEqual(builder.verify_bundle(self.bundle, installation=True), self.manifest)
        (self.bundle / "unknown.json").write_text("{}\n")
        with self.assertRaises(builder.BundleError):
            builder.verify_bundle(self.bundle, installation=True)

    def test_installed_receipt_must_be_regular_and_have_safe_mode(self) -> None:
        receipt = self.bundle / builder.INSTALL_RECEIPT
        receipt.write_text("{}\n")
        receipt.chmod(0o644)
        with self.assertRaisesRegex(builder.BundleError, "mode 0600"):
            builder.verify_bundle(self.bundle, installation=True)
        receipt.unlink()
        receipt.symlink_to(self.bundle / "bundle.json")
        with self.assertRaises(builder.BundleError):
            builder.verify_bundle(self.bundle, installation=True)

    def test_unlisted_private_source_files_never_enter_either_native_package(self) -> None:
        source = self.source_copy()
        sentinel = ("synthetic-private-" + self.root.name).encode()
        for relative in ("credentials.json", "sessions/synthetic.jsonl", "logs/synthetic.log",
                         ".env", "agents/unrelated.md", "ecosystem/personal.json"):
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(sentinel)
        rebuilt = self.root / "public"
        manifest = builder.build_bundle(rebuilt, self.manifest["modules"], source_root=source)
        for relative in manifest["files"]:
            self.assertNotIn(sentinel, (rebuilt / relative).read_bytes())


if __name__ == "__main__":
    unittest.main()
