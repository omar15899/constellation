"""English packaging behavior and preservation of the shared executable contract.

These source-only tests do not invoke a model or alter a personal installation.
Native discovery, trust and semantic instruction quality require separate evidence.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE / "ecosystem"))
import build as subject
from validate import validate


class EnglishPackagingTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="constellation-language-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def source_copy(self) -> Path:
        """Copy only packaged canonical resources and the fixed English inventory."""
        target = self.root / "source"
        for relative in sorted({subject.source_path(path)
                                for path in subject.allowed_files(subject.MODULES)}):
            origin = subject.regular_file(SOURCE, relative)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origin, destination)
        for relative in sorted(subject.translation_files()):
            destination = target / "ecosystem/locales/en" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE / "ecosystem/locales/en" / relative, destination)
        return target

    def build(self, name: str, source: Path = SOURCE, *, language: str = "en",
              modules: tuple[str, ...] | None = None) -> Path:
        result = self.root / name
        subject.build_bundle(result, modules=modules, source_root=source, language=language)
        return result

    def test_default_and_explicit_spanish_match_without_reading_overlays(self) -> None:
        source = self.source_copy()
        shutil.rmtree(source / "ecosystem/locales")
        default, explicit = self.root / "default", self.root / "explicit"
        self.assertEqual(subject.build_bundle(default, source_root=source),
                         subject.build_bundle(explicit, source_root=source, language="es"))
        for relative in subject.allowed_files(subject.MODULES):
            expected, mode = subject.source_resource(source, relative)
            self.assertEqual((default / relative).read_bytes(), expected)
            self.assertEqual(stat.S_IMODE((default / relative).stat().st_mode), mode)

    def test_english_uses_complete_overlays_and_one_canonical_agent_body(self) -> None:
        bundle = self.build("english")
        self.assertEqual(set(subject.verify_bundle(bundle)["files"]), subject.allowed_files(subject.MODULES))
        self.assertEqual(validate(bundle), [])
        for relative in subject.allowed_files(subject.MODULES):
            canonical = subject.source_path(relative)
            content, mode = subject.source_resource(SOURCE, relative)
            if canonical in subject.translation_files():
                content = (SOURCE / "ecosystem/locales/en" / canonical).read_bytes()
                if relative.startswith("agents/"):
                    content = subject.render_claude_agent(content)
            self.assertEqual((bundle / relative).read_bytes(), content, relative)
            self.assertEqual(stat.S_IMODE((bundle / relative).stat().st_mode), mode, relative)

    def test_archives_are_reproducible_across_relocation_and_portable_rebuild(self) -> None:
        first = self.build("first")
        moved = self.root / "another location with spaces"
        shutil.copytree(first, moved)
        second = self.build("second", moved, language="es")
        a, b = self.root / "first.zip", self.root / "second.zip"
        subject.write_archive(first, a)
        subject.write_archive(second, b)
        self.assertEqual(a.read_bytes(), b.read_bytes())
        # The shipped builder works without the checkout or translation tree.
        result = subprocess.run([sys.executable, "-I", "-B", str(moved / "ecosystem/build.py"),
                                 "--output", str(self.root / "via-cli")],
                                cwd=self.root, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(subject.verify_bundle(self.root / "via-cli"), subject.verify_bundle(first))

    def test_all_module_subsets_preserve_english_bytes(self) -> None:
        full = self.build("full")
        for module in subject.MODULES:
            with self.subTest(module=module):
                direct = self.build("direct-" + module, modules=(module,))
                rebuilt = self.build("rebuilt-" + module, full, language="es", modules=(module,))
                self.assertEqual(subject.verify_bundle(direct), subject.verify_bundle(rebuilt))
                self.assertEqual(validate(direct), [])

    def test_portable_input_rejects_language_conversion(self) -> None:
        bundle = self.build("english")
        with self.assertRaisesRegex(subject.BundleError, "preserve their language"):
            self.build("converted", bundle)
        self.assertFalse((self.root / "converted").exists())

    def test_unknown_language_is_rejected_before_output(self) -> None:
        with self.assertRaisesRegex(subject.BundleError, "Language must"):
            self.build("unknown", language="fr")
        self.assertFalse((self.root / "unknown").exists())

    def test_missing_translation_fails_even_for_unrelated_module_subset(self) -> None:
        source = self.source_copy()
        (source / "ecosystem/locales/en/skills/writter/SKILL.md").unlink()
        with self.assertRaisesRegex(subject.BundleError, "missing"):
            self.build("missing", source, modules=("coding",))
        self.assertFalse((self.root / "missing").exists())

    def test_extra_translation_or_executable_is_rejected(self) -> None:
        source = self.source_copy()
        extra = source / "ecosystem/locales/en/ecosystem/hooks.py"
        extra.write_text("raise RuntimeError('must never execute')\n")
        with self.assertRaisesRegex(subject.BundleError, "inventory"):
            self.build("extra", source)
        self.assertFalse((self.root / "extra").exists())

    def test_linked_locale_file_and_directory_are_rejected(self) -> None:
        source = self.source_copy()
        skill = source / "ecosystem/locales/en/skills/coding/SKILL.md"
        original = skill.read_bytes()
        skill.unlink()
        skill.symlink_to(source / "skills/coding/SKILL.md")
        with self.assertRaisesRegex(subject.BundleError, "Symlink"):
            self.build("file-link", source)
        skill.unlink()
        skill.write_bytes(original)
        locale = source / "ecosystem/locales/en"
        moved = source / "translations"
        locale.rename(moved)
        locale.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(subject.BundleError, "Symlink"):
            self.build("directory-link", source)
        self.assertFalse((self.root / "directory-link").exists())

    def test_empty_or_invalid_utf8_translation_is_rejected(self) -> None:
        source = self.source_copy()
        path = source / "ecosystem/locales/en/skills/coding/SKILL.md"
        for content in (b" \n", b"\xff"):
            with self.subTest(content=content):
                path.write_bytes(content)
                with self.assertRaisesRegex(subject.BundleError, "Invalid English text"):
                    self.build("invalid", source)
                self.assertFalse((self.root / "invalid").exists())

    def test_progress_translation_changes_only_authorized_display_constants(self) -> None:
        canonical = (SOURCE / "ecosystem/runtime/progress.py").read_bytes()
        translated = (SOURCE / "ecosystem/locales/en/ecosystem/runtime/progress.py").read_bytes()
        self.assertNotEqual(canonical, translated)
        subject._check_progress_translation(canonical, translated)
        # Valid alternative wording is allowed, but no import, validation or key changes.
        valid = canonical.replace("Objetivos".encode(), b"Objectives")
        subject._check_progress_translation(canonical, valid)
        bad = canonical.replace(b'"objectives"', b'"goals"')
        with self.assertRaisesRegex(subject.BundleError, "non-display constant"):
            subject._check_progress_translation(canonical, bad)
        with self.assertRaisesRegex(subject.BundleError, "executable structure"):
            subject._check_progress_translation(canonical, canonical + b"\nimport os\n")

    def test_changed_progress_logic_is_rejected_without_execution(self) -> None:
        source = self.source_copy()
        path = source / "ecosystem/locales/en/ecosystem/runtime/progress.py"
        marker = self.root / "must-not-exist"
        path.write_text(path.read_text() + "\nfrom pathlib import Path\nPath(" + repr(str(marker)) + ").touch()\n")
        with self.assertRaisesRegex(subject.BundleError, "executable structure"):
            self.build("changed-code", source)
        self.assertFalse(marker.exists())
        self.assertFalse((self.root / "changed-code").exists())


if __name__ == "__main__":
    unittest.main()
