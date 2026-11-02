"""Exercise dual-native release projection, integrity and relocation offline."""
from __future__ import annotations

from itertools import combinations
import hashlib
import json
import ast
import os
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
from helpers import AVAILABLE_PROFILES


class ClaudePackageTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="dual-native-release-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.bundle = self.root / "release"
        self.manifest = builder.build_bundle(self.bundle, AVAILABLE_PROFILES, source_root=SOURCE)

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
        before = role.read_bytes()
        canonical = tomllib.loads(before.decode("utf-8"))
        instruction = "Synthetic bounded instruction: report the verified fixture result."
        updated = {**canonical, "developer_instructions":
                   canonical["developer_instructions"].rstrip() + "\n\n" + instruction + "\n"}
        role.write_text("\n".join(
            f"{field} = {json.dumps(updated[field], ensure_ascii=False)}"
            for field in ("name", "description", "developer_instructions")) + "\n", encoding="utf-8")
        self.assertNotEqual(role.read_bytes(), before, "Canonical mutation must not be a language-dependent no-op")
        self.assertNotEqual(tomllib.loads(role.read_text(encoding="utf-8"))["developer_instructions"],
                            canonical["developer_instructions"])
        rebuilt = self.root / "changed"
        builder.build_bundle(rebuilt, self.manifest["modules"], source_root=source)
        self.assertNotEqual((rebuilt / "agents/researcher.md").read_bytes(),
                            (self.bundle / "agents/researcher.md").read_bytes())
        self.assertIn(instruction, (rebuilt / "agents/researcher.md").read_text(encoding="utf-8"))
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

    @unittest.skipIf(os.name == "nt", "POSIX receipt mode mutations; actual Windows ACL tests are separate")
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

    @unittest.skipIf(os.name == "nt", "POSIX receipt mode mutations; actual Windows ACL tests are separate")
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


    def test_windows_target_has_uniform_exec_form_and_preserves_failure_policy(self) -> None:
        source = self.source_copy()
        windows = self.root / "Windows package with spaces"
        builder.build_bundle(windows, self.manifest["modules"], source, target="windows-claude")
        self.assertEqual(builder.bundle_target(windows), "windows-claude")
        self.assertEqual(validate(windows), [])
        hooks = json.loads((windows / "ecosystem/claude-hooks.json").read_text())
        for event, groups in hooks["hooks"].items():
            hook = groups[0]["hooks"][0]
            self.assertEqual(hook["command"], "python")
            self.assertEqual(hook["args"][0], "-I")
            self.assertEqual(hook["args"][-1], event)
            self.assertNotIn("shell", hook)
            if event in {"UserPromptSubmit", "PreToolUse"}:
                self.assertEqual(hook["onFailure"], "block")
        # This is structural target verification, not an execution on Windows.
        self.assertEqual(json.loads((windows / builder.CLAUDE_PLUGIN_MANIFEST).read_text())["version"],
                         json.loads((self.bundle / builder.CLAUDE_PLUGIN_MANIFEST).read_text())["version"])

    def test_windows_bundle_rebuild_and_subset_preserve_target_without_sources(self) -> None:
        windows = self.root / "windows"
        source = self.source_copy()
        builder.build_bundle(windows, self.manifest["modules"], source, target="windows-claude")
        relocated = self.root / "relocated Windows package"
        shutil.copytree(windows, relocated)
        rebuilt = self.root / "rebuilt-windows"
        self.assertEqual(builder.build_bundle(rebuilt, source_root=relocated), builder.verify_bundle(windows))
        self.assertEqual(builder.bundle_target(rebuilt), "windows-claude")
        subset = self.root / "windows-subset"
        builder.build_bundle(subset, (self.manifest["modules"][0],), relocated)
        self.assertEqual(builder.bundle_target(subset), "windows-claude")
        self.assertEqual(validate(subset), [])
        with self.assertRaisesRegex(builder.BundleError, "preserve their target"):
            builder.build_bundle(self.root / "conversion", source_root=relocated, target="windows-claude")
        with self.assertRaisesRegex(builder.BundleError, "Target must"):
            builder.build_bundle(self.root / "unknown-target", self.manifest["modules"], source, target="windows")
        self.assertFalse((self.root / "conversion").exists())
        self.assertFalse((self.root / "unknown-target").exists())

    def test_bootstrap_embeds_one_helper_without_importing_package_code(self) -> None:
        raw = (self.bundle / "ecosystem/claude_hooks.py").read_bytes()
        tree = ast.parse(raw)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn("platform_support", node.module or "")
            elif isinstance(node, ast.Import):
                self.assertFalse(any("platform_support" in alias.name for alias in node.names))
        marker = builder._PLATFORM_BEGIN.encode()
        self.assertEqual(raw.count(marker), 1)
        self.assertIn(b"class PlatformError", raw)
        source = self.source_copy()
        rerendered, mode = builder.source_resource(source, "ecosystem/claude_hooks.py")
        self.assertEqual(rerendered, raw)
        self.assertEqual(mode, 0o644)
        with self.assertRaisesRegex(builder.BundleError, "one canonical platform block"):
            builder.render_claude_bootstrap(b"import platform_support\n", b"pass\n")

    def test_current_layout_with_another_version_is_verified_as_data(self) -> None:
        package, manifest = self.current_version_fixture("current-layout-update")
        marker = self.root / "candidate-must-not-execute"
        path = package / "ecosystem/build.py"
        path.write_text("from pathlib import Path\nPath(" + repr(str(marker)) + ").touch()\n")
        manifest["files"]["ecosystem/build.py"] = builder.file_record(path)
        (package / "bundle.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        self.assertEqual(builder.verify_bundle(package), manifest)
        self.assertFalse(marker.exists())

    def test_noncanonical_layouts_are_rejected_even_with_matching_inventory(self) -> None:
        for mutation in ("missing", "relocated"):
            with self.subTest(mutation=mutation):
                package = self.root / ("unsupported-" + mutation)
                shutil.copytree(self.bundle, package)
                marker = self.root / ("must-not-execute-" + mutation)
                payload = package / "ecosystem/build.py"
                payload.write_text("from pathlib import Path\nPath(" + repr(str(marker)) + ").touch()\n")
                files = dict(self.manifest["files"])
                files["ecosystem/build.py"] = builder.file_record(payload)
                if mutation == "missing":
                    relative = "ecosystem/platform_support.py"
                    (package / relative).unlink()
                    files.pop(relative)
                else:
                    relative, moved = "ecosystem/docs/architecture.md", "ecosystem/docs/relocated-architecture.md"
                    (package / relative).replace(package / moved)
                    files.pop(relative)
                    files[moved] = builder.file_record(package / moved)
                manifest = {"schema": 1, "modules": self.manifest["modules"], "files": files}
                (package / "bundle.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
                before = {p.relative_to(package).as_posix(): p.read_bytes()
                          for p in package.rglob("*") if p.is_file()}
                with self.assertRaisesRegex(builder.BundleError, "allowlist"):
                    builder.verify_bundle(package)
                self.assertEqual(before, {p.relative_to(package).as_posix(): p.read_bytes()
                                          for p in package.rglob("*") if p.is_file()})
                self.assertFalse(marker.exists())

    def test_mixed_or_shell_based_native_interpreters_are_rejected(self) -> None:
        data = json.loads((self.bundle / "ecosystem/claude-hooks.json").read_text())
        for change in ("mixed", "shell", "failure-policy"):
            candidate = json.loads(json.dumps(data))
            hook = candidate["hooks"]["PreToolUse"][0]["hooks"][0]
            if change == "mixed":
                hook["command"] = "python" if hook["command"] == "python3" else "python3"
            elif change == "shell":
                hook["command"] = "python -I"
                hook.pop("args")
            else:
                hook.pop("onFailure")
            with self.subTest(change=change), self.assertRaises(builder.BundleError):
                builder.claude_hook_target(candidate)


    def current_version_fixture(self, name: str) -> tuple[Path, dict]:
        """Copy the active layout with another matching safe release identifier."""
        package = self.root / name
        shutil.copytree(self.bundle, package)
        for relative in (builder.PLUGIN_MANIFEST, builder.CLAUDE_PLUGIN_MANIFEST):
            path = package / relative
            data = json.loads(path.read_text())
            data["version"] = "2.0.0"
            path.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")
        manifest = {"schema": 1, "modules": self.manifest["modules"],
                    "files": {relative: builder.file_record(package / relative)
                              for relative in sorted(self.manifest["files"])}}
        (package / "bundle.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        return package, manifest

    @unittest.skipIf(os.name == "nt", "POSIX mutation scenario; native Windows ACL case is separate")
    def test_package_directories_reject_foreign_replacement_across_current_versions(self) -> None:
        alternate, manifest = self.current_version_fixture("directory-access-update")
        for root, verify, expected in (
                (self.bundle, builder.verify_bundle, self.manifest),
                (alternate, builder.verify_bundle, manifest)):
            before = {name: (root / name).read_bytes() for name in expected["files"]}
            for relative in (".", "ecosystem"):
                path = root / relative
                with self.subTest(release=str(root.name), directory=relative):
                    path.chmod(0o777)
                    try:
                        with self.assertRaisesRegex(builder.BundleError, "directory access"):
                            verify(root)
                        self.assertTrue(any("directory access" in error for error in validate(root)))
                    finally:
                        path.chmod(0o755)
                    # Neither readonly nor stronger private protection grants mutation to others.
                    for mode in (0o555, 0o700):
                        path.chmod(mode)
                        try:
                            self.assertEqual(verify(root), expected)
                        finally:
                            path.chmod(0o755)
            self.assertEqual(before, {name: (root / name).read_bytes() for name in expected["files"]})

    @unittest.skipUnless(os.name == "nt", "Requires actual Windows DACL semantics")
    def test_windows_package_directory_add_file_and_delete_child_acl_is_rejected(self) -> None:
        import subprocess

        alternate, manifest = self.current_version_fixture("directory-acl-update")
        executable = shutil.which("icacls")
        self.assertIsNotNone(executable, "Native Windows acceptance requires icacls.exe")
        for root, verify, expected in (
                (self.bundle, builder.verify_bundle, self.manifest),
                (alternate, builder.verify_bundle, manifest)):
            before = {name: (root / name).read_bytes() for name in expected["files"]}
            for relative in (".", "ecosystem"):
                directory = root / relative
                with self.subTest(release=root.name, directory=relative):
                    result = subprocess.run([executable, str(directory), "/grant",
                                             "*S-1-1-0:(WD,DC)"], capture_output=True, timeout=20)
                    self.assertEqual(result.returncode, 0, "Synthetic directory ACL could not be established")
                    try:
                        with self.assertRaisesRegex(builder.BundleError, "directory access"):
                            verify(root)
                    finally:
                        builder._PLATFORM.set_access(directory, 0o755)
                    self.assertEqual(verify(root), expected)
            self.assertEqual(before, {name: (root / name).read_bytes() for name in expected["files"]})


    def test_platform_helper_drift_is_rejected_even_with_refreshed_inventory(self) -> None:
        helper = self.bundle / "ecosystem/platform_support.py"
        marker = self.root / "helper-must-not-execute"
        helper.write_text(helper.read_text() + "\nfrom pathlib import Path\nPath(" + repr(str(marker)) + ").touch()\n")
        manifest = json.loads((self.bundle / "bundle.json").read_text())
        manifest["files"]["ecosystem/platform_support.py"] = builder.file_record(helper)
        (self.bundle / "bundle.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        with self.assertRaisesRegex(builder.BundleError, "canonical platform support"):
            builder.verify_bundle(self.bundle)
        self.assertTrue(any("canonical platform support" in error for error in validate(self.bundle)))
        self.assertFalse(marker.exists())


    def test_malformed_interpreter_and_version_types_fail_without_traceback(self) -> None:
        hooks = json.loads((self.bundle / "ecosystem/claude-hooks.json").read_text())
        for value in (None, False, 1, [], {}):
            candidate = json.loads(json.dumps(hooks))
            candidate["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = value
            with self.subTest(field="command", value=value), self.assertRaises(builder.BundleError):
                builder.claude_hook_target(candidate)
        path = self.bundle / builder.PLUGIN_MANIFEST
        original = json.loads(path.read_text())
        manifest = json.loads((self.bundle / "bundle.json").read_text())
        for value in (None, False, 1, [], {}):
            path.write_text(json.dumps({**original, "version": value}))
            manifest["files"][builder.PLUGIN_MANIFEST] = builder.file_record(path)
            (self.bundle / "bundle.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
            with self.subTest(field="version", value=value), self.assertRaises(builder.BundleError):
                builder.verify_bundle(self.bundle)


    def test_native_inventory_blocks_are_current_and_source_drift_fails_closed(self) -> None:
        source = self.source_copy()
        for relative in ("ecosystem/claude_hooks.py", "ecosystem/hook_entry.py"):
            with self.subTest(entry=relative):
                distributed = (self.bundle / relative).read_bytes()
                self.assertEqual(builder.render_current_inventory(distributed), distributed)
                path = source / relative
                before = path.read_bytes()
                path.write_bytes(before.replace(b'"ecosystem/docs/windows.md",\n', b"", 1))
                self.assertNotEqual(path.read_bytes(), before)
                with self.assertRaisesRegex(builder.BundleError, "inventory is stale"):
                    builder.source_resource(source, relative)
                self.assertEqual(builder.render_current_inventory(path.read_bytes()), before)
                path.write_bytes(before)


if __name__ == "__main__":
    unittest.main()
