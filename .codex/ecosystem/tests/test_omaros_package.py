"""The device-wide private profile is opt-in and installs the requested skill names."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE / "ecosystem"))
sys.path.insert(0, str(SOURCE / "ecosystem/tests"))
from build import AVAILABLE_MODULES, MODULES, VAULT_SKILLS, BundleError, allowed_files, build_bundle, verify_bundle
from claude import InstallError as ClaudeInstallError, install_bundle as install_claude
from install import install_bundle
from test_package import SyntheticNativeClient
from validate import validate


class PersonalEdition(unittest.TestCase):
    def test_personal_resources_are_opt_in_and_available_under_real_skill_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            generic = root / "general"
            build_bundle(generic, MODULES, source_root=SOURCE)
            self.assertEqual(sorted(p.name for p in (generic / "skills").iterdir()), sorted(MODULES))
            self.assertFalse((generic / "ecosystem/vault").exists())
            personal = root / "personal"
            build_bundle(personal, AVAILABLE_MODULES, source_root=SOURCE)
            expected_names = sorted((*MODULES, *VAULT_SKILLS))
            self.assertEqual(sorted(p.name for p in (personal / "skills").iterdir()), expected_names)
            self.assertTrue((personal / "ecosystem/vault/workflow.py").is_file())
            self.assertEqual(validate(personal), [])
            self.assertEqual(verify_bundle(personal)["modules"], list(AVAILABLE_MODULES))
            home = root / "codex"
            home.mkdir()
            install_bundle(personal, home, client=SyntheticNativeClient(home))
            receipt = json.loads((home / "constellation/receipt.json").read_text())
            cache = home / "plugins/cache/constellation/constellation" / receipt["version"]
            self.assertEqual(sorted(p.name for p in (cache / "skills").iterdir()), expected_names)
            try_home = root / "claude"
            with self.assertRaisesRegex(ClaudeInstallError, "Codex"):
                install_claude(personal, try_home, check=True)
            self.assertFalse(try_home.exists())

    def test_consistent_partial_inventory_and_check_only_install_reject_missing_methods(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            personal = root / "edited-bundle"
            manifest = build_bundle(personal, AVAILABLE_MODULES, source_root=SOURCE)
            partial = ("coding", "omaros")
            home = root / "codex"
            with self.assertRaisesRegex(BundleError, "all four"):
                install_bundle(personal, home, modules=partial, check=True, client=SyntheticNativeClient(home))
            self.assertFalse(home.exists())
            # Simulate a third-party archive with internally consistent files and hashes but
            # without the general roles required to dispatch vault work.
            admitted = allowed_files(partial)
            for name in manifest["files"].keys() - admitted:
                (personal / name).unlink()
            manifest["files"] = {name: record for name, record in manifest["files"].items() if name in admitted}
            manifest["modules"] = list(partial)
            (personal / "bundle.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(BundleError, "all four"):
                verify_bundle(personal)
            self.assertTrue(validate(personal))

    def test_unsupported_profiles_reject_before_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            partial = [(*[name for name in MODULES if name != missing], "omaros") for missing in MODULES]
            forbidden = [(modules, "posix") for modules in [("omaros",), *partial]]
            for modules, target in [*forbidden, (AVAILABLE_MODULES, "windows-claude")]:
                with self.subTest(modules=modules, target=target), self.assertRaises(BundleError):
                    build_bundle(root / "rejected", modules, source_root=SOURCE, target=target)
                self.assertFalse((root / "rejected").exists())
