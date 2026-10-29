"""Exercise the portable validator against independent filesystem fixtures."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


SOURCE_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = SOURCE_ROOT / "ecosystem/validate.py"
_SPEC = importlib.util.spec_from_file_location("ecosystem_validation_subject", VALIDATOR_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_VALIDATOR = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_VALIDATOR)
validate = _VALIDATOR.validate
_BUILD_SPEC = importlib.util.spec_from_file_location(
    "ecosystem_validation_builder", SOURCE_ROOT / "ecosystem/build.py"
)
assert _BUILD_SPEC is not None and _BUILD_SPEC.loader is not None
_BUILDER = importlib.util.module_from_spec(_BUILD_SPEC)
_BUILD_SPEC.loader.exec_module(_BUILDER)

# This fixture describes the distribution contract independently of the validator.
CORE_RESOURCES = (
    "ecosystem/platform_support.py", "ecosystem/docs/windows.md",
    "ecosystem/tests/test_platform_support.py", "ecosystem/tests/test_windows_claude.py",
    "ecosystem/tests/windows_acceptance.py",
    "ecosystem/claude.py", "ecosystem/claude_hooks.py", "ecosystem/claude-hooks.json",
    "ecosystem/tests/test_claude_install.py", "ecosystem/tests/test_claude_hooks.py",
    "ecosystem/tests/test_claude_package.py",
    "ecosystem/tests/native_claude_probe.py",
    "ecosystem/runtime/review_gate.py", "ecosystem/runtime/review-policy.json",
    "ecosystem/runtime/__init__.py", "ecosystem/runtime/workflow.py",
    "ecosystem/runtime/workspace.py", "ecosystem/runtime/dispatch.py",
    "ecosystem/runtime/agent_policy.py", "ecosystem/runtime/progress.py",
    "ecosystem/__init__.py", "ecosystem/core.py", "ecosystem/storage.py",
    "ecosystem/cli.py", "ecosystem/hooks.py", "ecosystem/hook_entry.py", "ecosystem/build.py",
    "ecosystem/install.py", "ecosystem/native.py", "ecosystem/validate.py",
    "ecosystem/README.md", "ecosystem/docs/compatibility.md",
    "ecosystem/docs/architecture.md", "ecosystem/docs/migrations.md", "ecosystem/docs/progress.md",
    "ecosystem/requirements-dev.txt", "ecosystem/references/protocol.md",
    "ecosystem/docs/evaluation.md",
    "ecosystem/evals/cases.json", "ecosystem/evals/rubric.json",
    "ecosystem/tests/helpers.py", "ecosystem/tests/test_core.py",
    "ecosystem/tests/test_hooks.py", "ecosystem/tests/test_hook_entry.py", "ecosystem/tests/test_package.py",
    "ecosystem/tests/test_validation.py", "ecosystem/tests/test_capabilities.py",
    "ecosystem/tests/test_progress.py", "ecosystem/tests/test_progress_core.py",
)
ROLES = {
    "coding": ("coder",),
    "mathematics": ("mathematician", "counterexample"),
    "quant-research": ("coder", "mathematician", "counterexample"),
    "writter": ("editor", "mathematician", "coder"),
}
LIFECYCLE_EVENTS = ("UserPromptSubmit", "PreToolUse", "SubagentStart", "SubagentStop", "Stop")


class PackageFixture:
    """A minimal structurally valid package whose scripts must never execute."""

    def __init__(self, root: Path, modules: tuple[str, ...] = ("coding",), *, bundled: bool = False):
        self.root = root
        self.bundled = bundled
        self.modules = modules
        self.manifest_path = ".codex-plugin/plugin.json" if bundled else "ecosystem/manifests/codex-plugin.json"
        for relative in CORE_RESOURCES:
            if relative.endswith(".py"):
                self.write(relative, 'raise RuntimeError("Validation executed package code")\n')
            elif relative.endswith(".json"):
                self.write_json(relative, {})
            else:
                self.write(relative, "A resource needed by the portable fixture.\n")
        # Project a deliberately inert helper without ever importing candidate code.
        helper = (self.root / "ecosystem/platform_support.py").read_bytes()
        bootstrap = ("from __future__ import annotations\n"
                     + _BUILDER._PLATFORM_BEGIN + "\npass\n" + _BUILDER._PLATFORM_END
                     + "\nraise RuntimeError('Validation executed package code')\n").encode()
        self.write("ecosystem/claude_hooks.py",
                   _BUILDER.render_claude_bootstrap(bootstrap, helper).decode())
        self.write_json(self.manifest_path, {
            "name": "constellation", "version": "1.1.0",
            "description": "Portable fixture for package validation.",
            "skills": "./skills/", "hooks": "./ecosystem/hooks.json",
        })
        self.write_json(".claude-plugin/plugin.json" if bundled else "ecosystem/manifests/claude-plugin.json", {
            "name": "constellation", "version": "1.1.0",
            "author": {"name": "Constellation"},
            "description": "Native Claude fixture for package validation.",
            "skills": "./skills/",
            "hooks": "./ecosystem/claude-hooks.json",
        })
        groups = {}
        for event in LIFECYCLE_EVENTS:
            group = {"hooks": [{
                "type": "command",
                "command": f'python3 -I "${{CODEX_HOME:-$HOME/.codex}}/constellation/hook.py" {event}',
                "timeout": 10,
            }]}
            if event == "PreToolUse":
                group["matcher"] = r"^(?:[A-Za-z0-9_]+[.:])*(?:apply_patch|Edit|Write)$"
            groups[event] = [group]
        self.write_json("ecosystem/hooks.json", {
            "description": "Optional lifecycle guards.", "hooks": groups,
        })
        claude_groups = {}
        for event in ("SessionStart", *LIFECYCLE_EVENTS):
            hook = {"type": "command", "command": "python3",
                    "args": ["-I", "${CLAUDE_PLUGIN_ROOT}/ecosystem/claude_hooks.py", event],
                    "timeout": 15}
            if event in {"UserPromptSubmit", "PreToolUse"}:
                hook["onFailure"] = "block"
            group = {"hooks": [hook]}
            if event == "PreToolUse":
                group["matcher"] = "^(Write|Edit|MultiEdit|NotebookEdit)$"
            claude_groups[event] = [group]
        self.write_json("ecosystem/claude-hooks.json", {"hooks": claude_groups})
        roles = ["researcher", "reviewer", "security-reviewer", "verifier"]
        for module in modules:
            self.skill(module)
            self.write(f"skills/{module}/references/workflow.md",
                       "Read [the shared protocol](../../../ecosystem/references/protocol.md).\n")
            self.write(f"skills/{module}/agents/openai.yaml", self.ui_yaml(module))
            roles.extend(ROLES[module])
        for role in roles:
            path = self.write(f"ecosystem/agents/{role}.toml", (
                f'name = "ecosystem_{role.replace("-", "_")}"\n'
                'description = "Perform the assigned role."\n'
                'developer_instructions = "Use the assigned resources and report evidence."\n'
            ))
            if bundled:
                self.write(f"agents/{role}.md", _BUILDER.render_claude_agent(path.read_bytes()).decode())
        if set(modules) & {"mathematics", "writter"}:
            self.write("ecosystem/references/ontology.md", "Objects, spaces and assumptions.\n")
            self.write("ecosystem/references/ontology-examples.md", "A worked example.\n")
        if bundled:
            self.inventory()

    def resource_path(self, relative: str) -> str:
        if self.bundled:
            return relative
        return {"ecosystem/hooks.json": "ecosystem/manifests/codex-hooks.json",
                "ecosystem/claude-hooks.json": "ecosystem/manifests/claude-hooks.json"}.get(relative, relative)

    def write(self, relative: str, content: str) -> Path:
        path = self.root / self.resource_path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        path.chmod(0o644)
        return path

    def write_json(self, relative: str, content: object) -> Path:
        return self.write(relative, json.dumps(content, ensure_ascii=False, indent=2) + "\n")

    def read_json(self, relative: str) -> dict:
        return json.loads((self.root / self.resource_path(relative)).read_text(encoding="utf-8"))

    def skill(self, module: str = "coding", *, name: object | None = None,
              description: object = "Validate a portable package using observable evidence.",
              body: str = "Read [the workflow](references/workflow.md).\n") -> None:
        self.write(f"skills/{module}/SKILL.md", (
            f"---\nname: {json.dumps(module if name is None else name)}\n"
            f"description: {json.dumps(description)}\n---\n\n{body}"
        ))

    @staticmethod
    def ui(module: str = "coding") -> dict:
        return {
            "interface": {
                "display_name": module.capitalize(),
                "short_description": "Check portable resources and evidence",
                "default_prompt": f"Use ${module} to complete this assignment.",
            },
            "policy": {"allow_implicit_invocation": True},
        }

    @classmethod
    def ui_yaml(cls, module: str) -> str:
        interface = cls.ui(module)["interface"]
        return ("interface:\n" + "".join(f"  {key}: {json.dumps(value)}\n" for key, value in interface.items())
                + "policy:\n  allow_implicit_invocation: true\n")

    def inventory(self) -> None:
        files = {}
        for path in sorted(self.root.rglob("*")):
            if path.is_file() and path.name != "bundle.json":
                files[path.relative_to(self.root).as_posix()] = {
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "mode": stat.S_IMODE(path.stat().st_mode),
                }
        self.write_json("bundle.json", {"schema": 1, "modules": list(self.modules), "files": files})


class ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="ecosystem-validation-test-")
        self.addCleanup(temporary.cleanup)
        self.temporary = Path(temporary.name)
        self.package = PackageFixture(self.temporary / "source")
        self.assertEqual(validate(self.package.root), [], "The independent baseline must be valid")

    def assert_rejected(self, path: str, package: PackageFixture | None = None,
                        modules: tuple[str, ...] | None = None) -> list[str]:
        fixture = package or self.package
        path = fixture.resource_path(path)
        errors = validate(fixture.root, modules)
        self.assertIsInstance(errors, list)
        self.assertTrue(errors, "Malformed package was accepted")
        self.assertTrue(all(isinstance(error, str) for error in errors), errors)
        self.assertTrue(any(path in error for error in errors), errors)
        return errors

    def test_valid_source_does_not_execute_package_scripts(self) -> None:
        marker = self.temporary / "candidate-build-executed"
        self.package.write("ecosystem/build.py", (
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('Candidate build.py executed', encoding='utf-8')\n"
        ))
        self.assertEqual(validate(self.package.root), [])
        self.assertFalse(marker.exists(), "The validator executed build.py from the inspected package")

    def test_each_available_module_and_all_modules_validate(self) -> None:
        for modules in (*((module,) for module in ROLES), tuple(ROLES)):
            with self.subTest(modules=modules):
                package = PackageFixture(self.temporary / "-".join(modules), modules)
                self.assertEqual(validate(package.root), [])
                self.assertEqual(validate(package.root, iter(modules)), [])

    def test_module_selection_rejects_invalid_empty_duplicate_or_string_values(self) -> None:
        for modules in ((), ("unknown",), ("coding", "coding"), "coding"):
            with self.subTest(modules=modules):
                self.assertTrue(validate(self.package.root, modules))

    def test_empty_name_description_and_body_are_rejected(self) -> None:
        for field in ("name", "description", "body"):
            for empty in ("", " \n "):
                with self.subTest(field=field, empty=empty):
                    self.package.skill(**{field: empty})
                    self.assert_rejected("skills/coding/SKILL.md")

    def test_skill_name_must_match_its_folder(self) -> None:
        self.package.skill(name="other-skill")
        self.assert_rejected("skills/coding/SKILL.md")

    def test_frontmatter_is_restricted_and_does_not_accept_duplicate_fields(self) -> None:
        variants = (
            'name: "coding"\ndescription: true',
            'name: "coding"\ndescription: "Valid"\ndescription: "Ambiguous"',
            'name: coding\ndescription: "Valid"',
            'name: "coding"\ndescription: "Valid"\nmodel: "future-model"',
            'name: "coding"\ndescription: |\n  A YAML multiline scalar',
        )
        for frontmatter in variants:
            with self.subTest(frontmatter=frontmatter):
                self.package.write("skills/coding/SKILL.md", f"---\n{frontmatter}\n---\nBody.\n")
                self.assert_rejected("skills/coding/SKILL.md")

    def test_missing_shared_reference_is_rejected(self) -> None:
        self.package.write("skills/coding/references/workflow.md",
                           "Read [details](../../../ecosystem/references/missing.md).\n")
        self.assert_rejected("ecosystem/references/missing.md")

    def test_links_to_existing_files_outside_package_are_rejected(self) -> None:
        outside = self.temporary / "outside.md"
        outside.write_text("Public synthetic fixture.\n", encoding="utf-8")
        for target in ("../../../outside.md", "../../%2e%2e/outside.md", str(outside), outside.as_uri()):
            with self.subTest(target=target):
                self.package.skill(body=f"Read [resource]({target}).\n")
                self.assert_rejected("skills/coding")

    def test_contained_links_anchors_and_public_urls_are_accepted(self) -> None:
        self.package.skill(body=(
            "[workflow](references/workflow.md#details) [section](#section) "
            "[source](https://example.com/paper) [mail](mailto:example@example.com)\n"
        ))
        self.assertEqual(validate(self.package.root), [])

    def test_link_normalization_cannot_hide_unresolvable_path_components(self) -> None:
        for target in ("references/missing/../workflow.md", "references/workflow.md/../workflow.md"):
            with self.subTest(target=target):
                self.package.skill(body=f"Read [resource]({target}).\n")
                self.assert_rejected("skills/coding")

    def test_symlinked_file_directory_and_root_are_rejected(self) -> None:
        for kind in ("file", "directory", "root"):
            with self.subTest(kind=kind):
                package = PackageFixture(self.temporary / kind)
                self.assertEqual(validate(package.root), [])
                if kind == "root":
                    alias = self.temporary / "alias"
                    alias.symlink_to(package.root, target_is_directory=True)
                    self.assertTrue(validate(alias))
                    continue
                path = package.root / ("skills/coding/SKILL.md" if kind == "file" else "skills/coding/references")
                outside = self.temporary / f"outside-{kind}"
                path.rename(outside)
                path.symlink_to(outside, target_is_directory=kind == "directory")
                self.assert_rejected("skills/coding", package)

    def test_ui_accepts_json_and_explicit_or_implicit_policy(self) -> None:
        for implicit in (None, True, False):
            with self.subTest(implicit=implicit):
                ui = PackageFixture.ui()
                if implicit is None:
                    del ui["policy"]
                else:
                    ui["policy"]["allow_implicit_invocation"] = implicit
                self.package.write_json("skills/coding/agents/openai.yaml", ui)
                self.assertEqual(validate(self.package.root), [])

    def test_ui_accepts_the_native_namespaced_selector(self) -> None:
        ui = PackageFixture.ui()
        ui["interface"]["default_prompt"] = "Use $constellation:coding for this change."
        self.package.write_json("skills/coding/agents/openai.yaml", ui)
        self.assertEqual(validate(self.package.root), [])

    def test_ui_rejects_invalid_fields_and_invocation_name(self) -> None:
        mutations = (
            ("display_name", ""), ("short_description", "short"),
            ("short_description", "a" * 65), ("default_prompt", "Use $coding-extra."),
            ("default_prompt", "Use $other:coding."),
            ("default_prompt", "Use $coding_bad."), ("default_prompt", "Use $coding:evil."),
            ("brand_color", "red"), ("icon_small", "https://example.com/icon.png"),
            ("future_runtime_override", "enabled"),
        )
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                ui = PackageFixture.ui()
                ui["interface"][field] = value
                self.package.write_json("skills/coding/agents/openai.yaml", ui)
                self.assert_rejected("skills/coding/agents/openai.yaml")

    def test_native_hook_interpreter_wrong_types_are_structural_errors(self) -> None:
        relative = "ecosystem/claude-hooks.json"
        original = self.package.read_json(relative)
        for value in (None, False, 1, [], {}):
            data = json.loads(json.dumps(original))
            data["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = value
            self.package.write_json(relative, data)
            with self.subTest(value=value):
                self.assert_rejected(self.package.resource_path(relative))

    def test_ui_requires_boolean_invocation_policy(self) -> None:
        ui = PackageFixture.ui()
        ui["policy"]["allow_implicit_invocation"] = "false"
        self.package.write_json("skills/coding/agents/openai.yaml", ui)
        self.assert_rejected("skills/coding/agents/openai.yaml")

    def test_ui_rejects_malformed_duplicate_and_general_yaml_metadata(self) -> None:
        valid = PackageFixture.ui_yaml("coding")
        variants = (
            valid.replace('display_name: "Coding"', 'display_name: "Coding"\n  display_name: "Other"'),
            valid.replace("  display_name:", "   display_name:"),
            valid.replace('display_name: "Coding"', "display_name: Coding"),
            '{"interface": {}, "interface": {}}',
            "interface: [invalid]\n",
        )
        for text in variants:
            with self.subTest(text=text):
                self.package.write("skills/coding/agents/openai.yaml", text)
                self.assert_rejected("skills/coding/agents/openai.yaml")

    def test_agent_runtime_overrides_are_rejected_including_unknown_future_fields(self) -> None:
        path = "ecosystem/agents/researcher.toml"
        original = (self.package.root / path).read_text(encoding="utf-8")
        for field in ("model", "model_reasoning_effort", "sandbox_mode", "future_runtime_override"):
            with self.subTest(field=field):
                self.package.write(path, original + f'{field} = "override"\n')
                self.assert_rejected(path)

    def test_agent_required_fields_and_native_name_are_checked(self) -> None:
        path = "ecosystem/agents/researcher.toml"
        values = {"name": "ecosystem_researcher", "description": "Research the task.",
                  "developer_instructions": "Report evidence."}
        for field in values:
            with self.subTest(field=field):
                invalid = dict(values, **{field: ""})
                self.package.write(path, "".join(f"{key} = {json.dumps(value)}\n" for key, value in invalid.items()))
                self.assert_rejected(path)
        values["name"] = "researcher"
        self.package.write(path, "".join(f"{key} = {json.dumps(value)}\n" for key, value in values.items()))
        self.assert_rejected(path)

    def test_unknown_hook_event_and_missing_lifecycle_event_are_rejected(self) -> None:
        original = self.package.read_json("ecosystem/hooks.json")
        for mutation in ("unknown", "missing"):
            with self.subTest(mutation=mutation):
                hooks = json.loads(json.dumps(original))
                if mutation == "unknown":
                    hooks["hooks"]["UnknownEvent"] = hooks["hooks"]["Stop"]
                else:
                    del hooks["hooks"]["Stop"]
                self.package.write_json("ecosystem/hooks.json", hooks)
                self.assert_rejected("ecosystem/hooks.json")

    def test_hook_matcher_cannot_broaden_the_registered_scope(self) -> None:
        hooks = self.package.read_json("ecosystem/hooks.json")
        hooks["hooks"]["PreToolUse"][0]["matcher"] = ".*"
        self.package.write_json("ecosystem/hooks.json", hooks)
        self.assert_rejected("ecosystem/hooks.json")

    def test_hook_commands_require_the_declared_isolated_execution_schema(self) -> None:
        original = self.package.read_json("ecosystem/hooks.json")
        mutations = (
            ("command", "python3 /tmp/other-hook.py Stop"),
            ("command", 'python3 -I "${CODEX_HOME:-$HOME/.codex}/constellation/hook.py" Stop; exit 0'),
            ("type", "prompt"), ("timeout", True), ("timeout", "10"), ("future_option", True),
        )
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                hooks = json.loads(json.dumps(original))
                hooks["hooks"]["Stop"][0]["hooks"][0][field] = value
                self.package.write_json("ecosystem/hooks.json", hooks)
                self.assert_rejected("ecosystem/hooks.json")

    def test_subset_still_requires_common_resources(self) -> None:
        for relative in ("ecosystem/core.py", "ecosystem/runtime/review_gate.py", "ecosystem/references/protocol.md",
                         "ecosystem/agents/verifier.toml", "ecosystem/runtime/progress.py",
                         "ecosystem/tests/test_progress.py", "ecosystem/tests/test_progress_core.py",
                         "ecosystem/docs/progress.md"):
            with self.subTest(relative=relative):
                path = self.package.root / relative
                original = path.read_bytes()
                path.unlink()
                self.assert_rejected(relative, modules=("coding",))
                path.write_bytes(original)

    def test_mathematics_and_writter_require_shared_ontology_resources(self) -> None:
        for module in ("mathematics", "writter"):
            with self.subTest(module=module):
                package = PackageFixture(self.temporary / module, (module,))
                self.assertEqual(validate(package.root), [])
                (package.root / "ecosystem/references/ontology-examples.md").unlink()
                self.assert_rejected("ontology-examples.md", package)

    def test_malformed_manifest_and_escaping_manifest_paths_are_rejected(self) -> None:
        original = self.package.read_json(self.package.manifest_path)
        variants = ("{", "[]", '{"name": "constellation", "name": "other"}',
                    json.dumps(dict(original, skills="../skills/")),
                    json.dumps(dict(original, hooks="/tmp/hooks.json")),
                    json.dumps(dict(original, name="")))
        for text in variants:
            with self.subTest(text=text):
                self.package.write(self.package.manifest_path, text)
                self.assert_rejected(self.package.manifest_path)

    def test_bundle_layout_and_subset_inventory_validate(self) -> None:
        for modules in (("coding",), ("quant-research",), ("mathematics", "writter"), tuple(ROLES)):
            with self.subTest(modules=modules):
                package = PackageFixture(self.temporary / ("bundle-" + "-".join(modules)), modules, bundled=True)
                self.assertFalse((package.root / "ecosystem/plugin.json").exists())
                self.assertEqual(validate(package.root), [])
                self.assertEqual(validate(package.root, modules[:1]), [])

    def test_current_source_and_bundle_cannot_claim_historical_release_identity(self) -> None:
        for bundled in (False, True):
            with self.subTest(bundled=bundled):
                package = PackageFixture(self.temporary / f"historical-identity-{bundled}", bundled=bundled)
                claude_manifest = (".claude-plugin/plugin.json" if bundled
                                   else "ecosystem/manifests/claude-plugin.json")
                for relative in (package.manifest_path, claude_manifest):
                    metadata = package.read_json(relative)
                    package.write_json(relative, {**metadata, "version": "1.3.0"})
                if bundled:
                    package.inventory()
                self.assert_rejected(package.manifest_path, package)

    def test_manifest_description_required_by_builder_is_required_by_validator(self) -> None:
        metadata = self.package.read_json(self.package.manifest_path)
        del metadata["description"]
        self.package.write_json(self.package.manifest_path, metadata)
        with self.assertRaises(_BUILDER.BundleError):
            _BUILDER.build_bundle(self.temporary / "missing-description",
                                  self.package.modules, source_root=self.package.root)
        self.assert_rejected(self.package.manifest_path)

    @unittest.skipIf(os.name == "nt", "Physical POSIX mode corruption; native ACL rejection has dedicated tests")
    def test_bundle_rejects_changed_hash_and_permissions(self) -> None:
        for mutation in ("hash", "mode"):
            with self.subTest(mutation=mutation):
                package = PackageFixture(self.temporary / mutation, bundled=True)
                self.assertEqual(validate(package.root), [])
                path = package.root / "ecosystem/core.py"
                if mutation == "hash":
                    path.write_text("Changed after inventory.\n", encoding="utf-8")
                else:
                    path.chmod(0o755)
                self.assert_rejected("ecosystem/core.py", package)

    @unittest.skipIf(os.name == "nt", "Physical POSIX modes are not Windows ACLs")
    def test_bundle_rejects_unsupported_modes_even_when_inventory_matches(self) -> None:
        for mode in (0o600, 0o664, 0o777):
            with self.subTest(mode=oct(mode)):
                package = PackageFixture(self.temporary / f"mode-{mode:o}", bundled=True)
                path = package.root / "ecosystem/core.py"
                path.chmod(mode)
                inventory = package.read_json("bundle.json")
                inventory["files"]["ecosystem/core.py"]["mode"] = mode
                package.write_json("bundle.json", inventory)
                with self.assertRaises(_BUILDER.BundleError):
                    _BUILDER.verify_bundle(package.root)
                self.assert_rejected("ecosystem/core.py", package)

    def test_bundle_rejects_missing_inventory_resource_or_selected_module(self) -> None:
        package = PackageFixture(self.temporary / "bundle", bundled=True)
        self.assertEqual(validate(package.root), [])
        original = package.read_json("bundle.json")
        for mutation in ("resource", "module"):
            with self.subTest(mutation=mutation):
                inventory = json.loads(json.dumps(original))
                if mutation == "resource":
                    del inventory["files"]["ecosystem/core.py"]
                else:
                    inventory["modules"] = []
                package.write_json("bundle.json", inventory)
                self.assert_rejected("bundle.json", package)

    def test_bundle_rejects_inventory_path_escape(self) -> None:
        package = PackageFixture(self.temporary / "bundle", bundled=True)
        self.assertEqual(validate(package.root), [])
        outside = self.temporary / "outside.md"
        outside.write_text("Synthetic resource.\n", encoding="utf-8")
        inventory = package.read_json("bundle.json")
        inventory["files"]["../outside.md"] = {
            "sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
            "mode": stat.S_IMODE(outside.stat().st_mode),
        }
        package.write_json("bundle.json", inventory)
        self.assert_rejected("bundle.json", package)

    def test_missing_directory_and_non_directory_return_diagnostics(self) -> None:
        self.assertTrue(validate(self.temporary / "missing"))
        file = self.temporary / "file"
        file.write_text("A regular file.\n", encoding="utf-8")
        self.assertTrue(validate(file))

    def test_cli_exit_status_tracks_validation_result(self) -> None:
        command = [sys.executable, "-I", str(VALIDATOR_PATH), "--root", str(self.package.root),
                   "--modules", "coding"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.package.skill(body="")
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("skills/coding/SKILL.md", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


class CurrentPackageTests(unittest.TestCase):
    @staticmethod
    def snapshot(root: Path) -> dict[str, tuple[int, str | None]]:
        return {
            path.relative_to(root).as_posix(): (
                stat.S_IMODE(path.stat().st_mode),
                hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None,
            )
            for path in [root, *root.rglob("*")]
        }

    def test_current_source_or_bundle_passes_structural_validation(self) -> None:
        errors = validate(SOURCE_ROOT)
        self.assertEqual(errors, [], "\n".join(errors))

    def test_real_standalone_bundles_pass_validation(self) -> None:
        modules = [name for name in ROLES
                   if (SOURCE_ROOT / "skills" / name).is_dir()]
        self.assertTrue(modules, "The source must contain an available module")
        with tempfile.TemporaryDirectory(prefix="ecosystem-validation-build-") as temporary:
            for module in modules:
                with self.subTest(module=module):
                    bundle = Path(temporary) / module
                    _BUILDER.build_bundle(bundle, (module,), SOURCE_ROOT)
                    skill_directories = {path.name for path in (bundle / "skills").iterdir()
                                         if path.is_dir()}
                    self.assertEqual(skill_directories, {module})
                    errors = validate(bundle)
                    self.assertEqual(errors, [], "\n".join(errors))
                    self.assertEqual(validate(bundle, (module,)), [])

    def test_bundle_cli_and_supported_api_validation_do_not_mutate_the_bundle(self) -> None:
        available = tuple(name for name in ROLES
                          if (SOURCE_ROOT / "skills" / name).is_dir())
        self.assertTrue(available, "The source must contain an available module")
        selections = list(dict.fromkeys([available, *((module,) for module in available)]))
        environment = dict(os.environ)
        environment.pop("PYTHONDONTWRITEBYTECODE", None)
        environment.pop("PYTHONPYCACHEPREFIX", None)
        api = (
            "from pathlib import Path\n"
            "from ecosystem.validate import validate\n"
            "errors = validate(Path.cwd())\n"
            "print('\\n'.join(errors))\n"
            "raise SystemExit(bool(errors))\n"
        )
        with tempfile.TemporaryDirectory(prefix="ecosystem-validation-readonly-") as temporary:
            for modules in selections:
                bundle = Path(temporary) / "-".join(modules)
                _BUILDER.build_bundle(bundle, modules, SOURCE_ROOT)
                inventory = _BUILDER.verify_bundle(bundle)
                before = self.snapshot(bundle)
                commands = {
                    "cli": [sys.executable, str(bundle / "ecosystem/validate.py"),
                            "--root", str(bundle)],
                    "api": [sys.executable, "-B", "-c", api],
                }
                for invocation, command in commands.items():
                    with self.subTest(modules=modules, invocation=invocation):
                        result = subprocess.run(command, cwd=bundle, env=environment,
                                                capture_output=True, text=True, timeout=20)
                        self.assertEqual(self.snapshot(bundle), before,
                                         f"{invocation} changed package paths, bytes or permissions")
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertEqual(_BUILDER.verify_bundle(bundle), inventory)


if __name__ == "__main__":
    unittest.main()
