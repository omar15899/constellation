"""Search against fixtures where relevance, privacy and freshness are observable."""
import importlib.util
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "scripts/search.py"
spec = importlib.util.spec_from_file_location("finder", MODULE)
finder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(finder)


class SearchTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def note(self, path, title, body="", status="active", tags="[math]"):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"---\ntitle: {title}\nstatus: {status}\ntags: {tags}\nupdated: 2026-09-05\n---\n# {title}\n{body}\n")
        return target

    def test_cli_uses_receiver_root_and_rejects_other_project(self):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        self.note("06_Knowledge_Base/Mathematics/a.md", "Receiver note", "martingala")
        nested = self.root / "06_Knowledge_Base/Mathematics"
        command = [sys.executable, str(MODULE), "martingala"]
        wrong = subprocess.run(command, cwd=nested, text=True, capture_output=True)
        self.assertEqual(wrong.returncode, 2)
        self.assertNotIn("Receiver note", wrong.stdout)
        marker = self.root / finder.VAULT_MARKER
        marker.parent.mkdir(parents=True)
        marker.write_text("Fixture marker.")
        found = subprocess.run(command, cwd=nested, text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(found.stdout)["results"][0]["title"], "Receiver note")
        wrong_root = subprocess.run(command + ["--root", str(nested)], cwd=nested, text=True, capture_output=True)
        self.assertEqual(wrong_root.returncode, 2)

    def test_private_area_and_secrets_are_never_returned_even_if_explicit(self):
        paths = [finder.RESTRICTED / "Topics/private.md", Path("config/credentials.json"),
                 Path(".codex/sessions/fixture.md")]
        for path in paths:
            self.note(path, "Test content", "pruebasecreta")
        self.assertEqual(finder.search(self.root, "pruebasecreta", config=True)["results"], [])
        for path in paths:
            with self.assertRaises(ValueError):
                finder.search(self.root, "pruebasecreta", scopes=[str(path)], config=True)

    def test_explicit_gitignored_file_is_never_searched(self):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        (self.root / ".gitignore").write_text("/synthetic_private/\n")
        path = self.note("synthetic_private/topic.md", "Synthetic note", "blocked")
        with self.assertRaisesRegex(ValueError, "Git ignore"):
            finder.search(self.root, "blocked", scopes=[str(path.relative_to(self.root))])
        self.assertFalse(finder.search(self.root, "blocked", scopes=["."])["results"])

    def test_case_aliases_do_not_open_restricted_data(self):
        hidden = [
            Path(finder.RESTRICTED.as_posix().lower()) / "Topics/hidden.md",
            Path(".CODEX/Log/event.md"), Path(".CLAUDE/Run/event.md"),
            Path(".codeX/CACHE/hidden.md"), Path(".cOdex/State/hidden.md"),
            Path("09_data_sources/source.md"), Path("99_ARCHIVE/old.md"),
            Path("13_health/hidden.md"), Path("16_relationships_and_people/hidden.md"),
        ]
        for name in hidden:
            self.note(name, "Dato restringido ficticio", "marcadornodistribuible")
        public = self.note("06_Knowledge_Base/visible.md", "Nota pública ficticia")
        observed = []
        spawn = subprocess.Popen

        def record(command, *args, **kwargs):
            if "--json" in command:
                for fd in kwargs["pass_fds"]:
                    info = os.fstat(fd)
                    observed.append((info.st_dev, info.st_ino))
            return spawn(command, *args, **kwargs)

        with patch.object(subprocess, "Popen", side_effect=record):
            self.assertFalse(finder.search(self.root, "marcadornodistribuible", config=True)["results"])
        # Observe the actual inherited inodes; a filter after reading would
        # return no hits but would hand skipped private bytes to the scanner.
        stat_result = public.stat()
        self.assertEqual(observed, [(stat_result.st_dev, stat_result.st_ino)])
        for name in hidden[:6]:
            with self.assertRaises(ValueError):
                finder.search(self.root, "marcadornodistribuible", config=True, scopes=[str(name.parent)])

    def test_inventory_rejects_leaf_and_directory_replacement_before_read(self):
        sentinel = "fixture_restricted_bytes"
        for kind in ("leaf", "parent"):
            for use_content_scan in (False, True):
                with self.subTest(kind=kind, content=use_content_scan), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp).resolve()
                    public = root / "collection" / "safe.md"
                    public.parent.mkdir()
                    public.write_text("Public source.")
                    restricted = root / finder.RESTRICTED / "safe.md"
                    restricted.parent.mkdir(parents=True)
                    restricted.write_text(sentinel)
                    discover = finder.allowed_inventory

                    def replaced(*args, **kwargs):
                        result = discover(*args, **kwargs)
                        if kind == "leaf":
                            public.unlink()
                            public.symlink_to(restricted)
                        else:
                            public.parent.rename(root / "original")
                            public.parent.symlink_to(restricted.parent, target_is_directory=True)
                        return result

                    with patch.object(finder, "allowed_inventory", side_effect=replaced):
                        with self.assertRaises((OSError, ValueError)):
                            finder.search(root, sentinel if use_content_scan else "", fields={"status": "private"})

    def test_hardlinked_and_compound_key_names_are_not_eligible(self):
        public = self.note("06_Knowledge_Base/good.md", "allowed", "scopemarker")
        hard = self.note(finder.RESTRICTED / "secret.md", "restricted", "scopemarker")
        os.link(hard, self.root / "public_alias.md")
        for name in ["id_rsa.backup.txt", "id_ed25519.pub.json", "session.keytab.old.md", "credentials-prod.json"]:
            self.note(name, "restricted", "scopemarker")
        result = finder.search(self.root, "scopemarker", config=True)
        self.assertEqual([x["path"] for x in result["results"]], [str(public.resolve())])

    def test_bare_repository_has_its_own_scope_even_without_dot_git_or_suffix(self):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        self.note("works/normal.md", "Public", "baresentinel")
        other = self.root / "works" / "ordinary-name"
        subprocess.run(["git", "init", "--bare", "-q", str(other)], check=True)
        (other / "README.md").write_text("baresentinel")
        for scopes in ([], ["works"]):
            rows = finder.search(self.root, "baresentinel", scopes=scopes)["results"]
            self.assertEqual([Path(row["path"]).name for row in rows], ["normal.md"])
        with self.assertRaisesRegex(ValueError, "Git owner"):
            finder.search(self.root, "baresentinel", scopes=["works/ordinary-name"])

    def test_administrative_owner_created_after_inventory_aborts_before_read(self):
        parent = self.root / "works" / "mobile-checkout"
        parent.mkdir(parents=True)
        (parent / "README.md").write_text("fixturebarebytes")
        discover = finder.allowed_inventory

        def become_foreign(*args, **kwargs):
            inventory = discover(*args, **kwargs)
            subprocess.run(["git", "init", "--bare", "-q", str(parent)], check=True)
            return inventory

        with patch.object(finder, "allowed_inventory", side_effect=become_foreign):
            with self.assertRaisesRegex(ValueError, "Git owner"):
                finder.search(self.root, "fixturebarebytes")

    def test_multi_term_title_beats_single_term_noise(self):
        self.note("06_Knowledge_Base/Mathematics/a.md", "Esperanza condicionada", "Una regla de predicción")
        self.note("01_Daily_Life/b.md", "Esperanza", "esperanza " * 100)
        result = finder.search(self.root, "busca mis notas sobre esperanza condicionada")
        self.assertEqual(result["results"][0]["title"], "Esperanza condicionada")

    def test_accents_match_and_real_excerpt_line(self):
        path = self.note("06_Knowledge_Base/Mathematics/a.md", "Teoría de la medida", "Una σ-álgebra organiza información.")
        result = finder.search(self.root, "teoria medida")["results"][0]
        line = path.read_text().splitlines()[result["line"] - 1]
        self.assertEqual(line, result["excerpt"])

    def test_private_domains_excluded_unless_scoped(self):
        self.note("13_Health/medical.md", "martingala privada")
        self.note("06_Knowledge_Base/Mathematics/normal.md", "martingala pública")
        result = finder.search(self.root, "martingala")
        self.assertEqual(len(result["results"]), 1)
        result = finder.search(self.root, "martingala", scopes=["13_Health"])
        self.assertEqual(len(result["results"]), 1)
        self.assertIn("13_Health", result["results"][0]["path"])

    def test_archives_and_transcripts_are_not_ordinary_hits(self):
        self.note("99_Archive/old.md", "martingala")
        self.note("09_Data_Sources/Codex_Conversations/rendered/chat.md", "martingala")
        self.assertFalse(finder.search(self.root, "martingala")["results"])
        self.assertEqual(len(finder.search(self.root, "martingala", archive=True, raw=True)["results"]), 1)

    def test_fields_are_exact_and_combined(self):
        self.note("02_Tasks_and_Execution/one.md", "One", status="active", tags="[math, probability]")
        self.note("02_Tasks_and_Execution/two.md", "Two", status="draft", tags="[math]")
        result = finder.search(self.root, "", fields={"status": "active", "tags": "math"})
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["title"], "One")

    def test_path_only_hit_reports_an_actual_line(self):
        path = self.note("06_Knowledge_Base/Mathematics/martingala.md", "Introducción")
        result = finder.search(self.root, "martingala")["results"][0]
        self.assertEqual(path.read_text().splitlines()[result["line"] - 1], result["excerpt"])

    def test_markdown_extension_case_preserves_path_body_and_field_search(self):
        paths = []
        for index, extension in enumerate(("MD", "Md", "mD")):
            paths.append(self.note(
                f"06_Knowledge_Base/Mathematics/cartera{index}.{extension}",
                "Introducción", f"Presupuesto{index} sin aportación externa.",
            ).resolve())
        for index, path in enumerate(paths):
            with self.subTest(extension=path.suffix):
                by_path = finder.search(self.root, f"cartera{index}")["results"]
                self.assertEqual([hit["path"] for hit in by_path], [str(path)])
                by_body = finder.search(self.root, f"presupuesto{index}")["results"]
                self.assertEqual([hit["path"] for hit in by_body], [str(path)])
                self.assertEqual(
                    path.read_text().splitlines()[by_body[0]["line"] - 1],
                    by_body[0]["excerpt"],
                )
        filtered = finder.search(self.root, "", fields={"status": "active"})["results"]
        self.assertEqual({hit["path"] for hit in filtered}, {str(path) for path in paths})

    def test_uppercase_markdown_preserves_privacy_exclusions(self):
        public = self.note("06_Knowledge_Base/Mathematics/a.MD", "martingala").resolve()
        archive = self.note("99_Archive/old.MD", "martingala").resolve()
        for path in (
            "09_Data_Sources/Codex_Conversations/rendered/chat.MD",
            "13_Health/medical.MD",
            "16_Relationships_and_People/private.MD",
            ".codex/secrets/private.MD",
            ".env.MD",
        ):
            self.note(path, "martingala")
        ordinary = finder.search(self.root, "martingala")["results"]
        self.assertEqual([hit["path"] for hit in ordinary], [str(public)])
        expanded = finder.search(
            self.root, "martingala", config=True, archive=True, raw=True,
        )["results"]
        self.assertEqual({hit["path"] for hit in expanded}, {str(public), str(archive)})

    def test_non_markdown_extensions_keep_their_existing_allowlist(self):
        public = self.note("06_Knowledge_Base/Mathematics/a.MD", "fixturepublico").resolve()
        ordinary_json = self.note("06_Knowledge_Base/Mathematics/a.json", "fixturepublico").resolve()
        for path in (
            "auth.JSON",
            "credentials.JSON",
            ".codex/auth.JSON",
            ".codex/credentials.JSON",
            ".codex/lower/auth.json",
            ".codex/lower/credentials.json",
        ):
            self.note(path, "fixturepublico")
        result = finder.search(self.root, "fixturepublico", config=True)["results"]
        self.assertEqual(
            {hit["path"] for hit in result},
            {str(public), str(ordinary_json)},
        )

    def test_dot_scope_means_vault(self):
        self.note("06_Knowledge_Base/Mathematics/a.md", "martingala")
        self.assertEqual(len(finder.search(self.root, "martingala", scopes=["."])["results"]), 1)

    def test_no_cached_stale_results_after_edit(self):
        path = self.note("06_Knowledge_Base/Mathematics/a.md", "martingala")
        self.assertTrue(finder.search(self.root, "martingala")["results"])
        path.write_text("Nada relacionado\n")
        self.assertFalse(finder.search(self.root, "martingala")["results"])

    def test_truncated_results_are_labeled(self):
        for i in range(5):
            self.note(f"06_Knowledge_Base/Mathematics/martingala_{i}.md", "martingala")
        self.assertTrue(finder.search(self.root, "martingala", max_candidates=2)["partial"])

    def test_external_scope_and_symlink_are_rejected(self):
        with self.assertRaises(ValueError):
            finder.search(self.root, "x", scopes=["../outside"])
        with tempfile.TemporaryDirectory() as external:
            path = Path(external) / "private.md"
            path.write_text("martingala\n")
            (self.root / "leak.md").symlink_to(path)
            self.assertFalse(finder.search(self.root, "martingala")["results"])

    def test_config_is_explicit_and_ignores_secrets(self):
        self.note(".codex/example.md", "hooks")
        self.note(".codex/secrets/private.md", "hooks")
        self.assertFalse(finder.search(self.root, "hooks")["results"])
        self.assertEqual(len(finder.search(self.root, "hooks", config=True)["results"]), 1)


if __name__ == "__main__":
    unittest.main()
