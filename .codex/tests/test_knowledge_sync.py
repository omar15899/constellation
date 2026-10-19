"""Knowledge export contracts exercised against disposable Git repositories."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import knowledge_sync as ks


class KnowledgeFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.hub = self.base / "GitHub"
        self.target = self.base / "OmarOS"
        self.home = self.base / "home"
        self.home.mkdir()
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("GIT_")}
        environment.update({
            "HOME": str(self.home), "CODEX_HOME": str(self.home / ".codex"),
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        })
        self.environment = patch.dict(os.environ, environment, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.initialize(self.hub)
        self.initialize(self.target)
        self.child = self.hub / "ResearchLab"
        self.work = self.hub / "WorkLab"
        self.external = self.hub / "External"
        for root in (self.child, self.work, self.external):
            self.initialize(root)
        self.registry = {
            "schema_version": 1,
            "repositories": [
                {"path": ".", "management": "native"},
                {"path": "ResearchLab", "management": "native"},
                {"path": "WorkLab", "management": "native"},
                {"path": "External", "management": "external"},
            ],
        }
        self.write(self.hub, ".codex/repositories.json", json.dumps(self.registry))
        self.git(self.hub, "add", ".codex/repositories.json")
        self.git(self.hub, "commit", "-qm", "Register fixture repositories")
        self.data = {
            "schema_version": 1,
            "hub_root": str(self.hub),
            "target_root": str(self.target),
            "sources": [{
                "root": str(self.child), "alias": "research-lab",
                "classification": "personal", "local_paths": [],
            }],
        }
        self.policy_path = self.home / ".codex/knowledge-sync.json"
        self.save_policy()

    @staticmethod
    def git(root: Path, *arguments: str, input: bytes | None = None) -> str:
        completed = subprocess.run(
            ["git", "-C", str(root), *arguments], input=input,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
        return completed.stdout.decode("utf-8").strip()

    def initialize(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self.git(root, "init", "-q", "-b", "main")
        self.git(root, "config", "user.name", "Knowledge fixture")
        self.git(root, "config", "user.email", "fixture@example.invalid")
        self.git(root, "config", "commit.gpgsign", "false")
        self.git(root, "config", "core.precomposeunicode", "false")
        self.git(root, "config", "core.hooksPath", str(root / ".git/hooks"))
        self.git(root, "commit", "--allow-empty", "-qm", "Initialize fixture")

    @staticmethod
    def write(root: Path, path: str, content: str | bytes) -> Path:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode() if isinstance(content, str) else content)
        return target

    def commit(self, root: Path, *paths: str) -> str:
        self.git(root, "add", "--", *paths)
        self.git(root, "commit", "-qm", "Add documented fixture")
        return self.git(root, "rev-parse", "HEAD")

    def save_policy(self) -> None:
        self.policy_path.parent.mkdir(parents=True, exist_ok=True)
        self.policy_path.write_text(json.dumps(self.data), encoding="utf-8")

    def policy(self) -> dict:
        self.save_policy()
        return ks.load_policy(self.policy_path)

    def bundle(self, root: Path | None = None) -> dict:
        policy = self.policy()
        source = policy["sources"][0] if root is None else next(
            item for item in policy["sources"] if Path(item["root"]) == root
        )
        return ks.collect_bundle(policy, source)


class KnowledgePolicyTests(KnowledgeFixture):
    def test_personal_and_work_sources_require_exact_explicit_entries(self):
        self.data["sources"].append({
            "root": str(self.work), "alias": "work-lab", "classification": "work",
        })
        loaded = self.policy()
        self.assertEqual({Path(item["root"]) for item in loaded["sources"]},
                         {self.child, self.work})
        self.assertEqual({item["classification"] for item in loaded["sources"]},
                         {"personal", "work"})

    def test_policy_schema_and_required_source_fields_fail_closed(self):
        original = json.loads(json.dumps(self.data))
        for mutation in (
                lambda data: data.update(schema_version=2),
                lambda data: data.update(schema_version=True),
                lambda data: data.update(automatic_export=True),
                lambda data: data["sources"][0].pop("classification"),
                lambda data: data["sources"][0].update(consent="implicit")):
            with self.subTest(mutation=mutation):
                self.data = json.loads(json.dumps(original))
                mutation(self.data)
                with self.assertRaises(ks.KnowledgeError):
                    self.policy()

    def test_target_must_be_distinct_exact_git_root_without_symlink(self):
        target_link = self.base / "LinkedOmarOS"
        target_link.symlink_to(self.target, target_is_directory=True)
        subdirectory = self.target / "notes"
        subdirectory.mkdir()
        for target in (self.hub, subdirectory, target_link):
            with self.subTest(target=target):
                self.data["target_root"] = str(target)
                with self.assertRaises(ks.KnowledgeError):
                    self.policy()

    def test_external_registration_is_not_authorization(self):
        self.data["sources"][0]["root"] = str(self.external)
        with self.assertRaises(ks.KnowledgeError):
            self.bundle()

    def test_repository_must_be_registered_even_when_it_is_a_git_root(self):
        unregistered = self.hub / "Unregistered"
        self.initialize(unregistered)
        self.data["sources"][0]["root"] = str(unregistered)
        with self.assertRaises(ks.KnowledgeError):
            self.bundle()

    def test_subdirectory_cannot_impersonate_registered_repository(self):
        nested = self.child / "docs"
        nested.mkdir()
        self.registry["repositories"].append({"path": "ResearchLab/docs",
                                               "management": "native"})
        self.write(self.hub, ".codex/repositories.json", json.dumps(self.registry))
        self.data["sources"][0]["root"] = str(nested)
        with self.assertRaises(ks.KnowledgeError):
            self.bundle()

    def test_repository_outside_the_hub_is_rejected(self):
        self.data["sources"][0]["root"] = str(self.target)
        with self.assertRaises(ks.KnowledgeError):
            self.policy()

    def test_unsafe_aliases_and_unknown_classification_are_rejected(self):
        for field, value in (("alias", "../outside"), ("alias", "UPPER"),
                             ("alias", "a/b"), ("classification", "external")):
            with self.subTest(field=field, value=value):
                self.data["sources"][0][field] = value
                with self.assertRaises(ks.KnowledgeError):
                    self.policy()
                self.data["sources"][0] = {
                    "root": str(self.child), "alias": "research-lab",
                    "classification": "personal", "local_paths": [],
                }

    def test_duplicate_roots_and_aliases_are_rejected(self):
        for root, alias in ((self.child, "another"), (self.work, "research-lab")):
            with self.subTest(root=root, alias=alias):
                self.data["sources"] = self.data["sources"][:1] + [{
                    "root": str(root), "alias": alias, "classification": "work",
                }]
                with self.assertRaises(ks.KnowledgeError):
                    self.policy()

    def test_root_symlinks_are_rejected(self):
        link = self.hub / "LinkedResearch"
        link.symlink_to(self.child, target_is_directory=True)
        self.registry["repositories"].append({"path": link.name, "management": "native"})
        self.write(self.hub, ".codex/repositories.json", json.dumps(self.registry))
        self.data["sources"][0]["root"] = str(link)
        with self.assertRaises(ks.KnowledgeError):
            self.policy()

    def test_local_path_may_not_escape_repository_or_select_private_area(self):
        for local in ("../elsewhere", "/tmp/reports", "raw", "conversations", ".codex"):
            with self.subTest(local=local):
                self.data["sources"][0]["local_paths"] = [local]
                with self.assertRaises(ks.KnowledgeError):
                    self.policy()

    def test_policy_consent_file_must_stay_outside_both_git_roots(self):
        for root in (self.hub, self.target):
            candidate = self.write(root, ".codex/knowledge-consent.json",
                                   json.dumps(self.data))
            for operation in (ks.load_policy, ks.install):
                with self.subTest(root=root, operation=operation.__name__):
                    with self.assertRaises(ks.KnowledgeError):
                        operation(candidate)
        plist = self.home / "Library/LaunchAgents/com.omar.constellation-knowledge-sync.plist"
        self.assertFalse(plist.exists())


class KnowledgeCollectionTests(KnowledgeFixture):
    def test_head_bytes_are_exported_without_dirty_or_untracked_content(self):
        self.write(self.child, "README.md", "Committed description.\n")
        self.write(self.child, "docs/report.md", "Committed finding.\n")
        revision = self.commit(self.child, "README.md", "docs/report.md")
        self.write(self.child, "README.md", "Uncommitted replacement.\n")
        self.write(self.child, "docs/untracked.md", "Not committed.\n")
        before = self.git(self.child, "status", "--porcelain")

        bundle = self.bundle()

        documents = {item["path"]: item for item in bundle["documents"]}
        self.assertEqual(set(documents), {"README.md", "docs/report.md"})
        self.assertEqual(base64.b64decode(documents["README.md"]["content"]),
                         b"Committed description.\n")
        self.assertEqual(bundle["source"], {
            "root": str(self.child), "alias": "research-lab", "revision": revision,
        })
        self.assertEqual(self.git(self.child, "status", "--porcelain"), before)
        self.assertTrue(all(item["origin"] == "git" for item in documents.values()))

    def test_git_commit_replacement_cannot_change_exported_head_tree(self):
        original = b"Original committed knowledge.\n"
        self.write(self.child, "README.md", original)
        revision = self.commit(self.child, "README.md")
        replacement = self.git(self.child, "hash-object", "-w", "--stdin",
                               input=b"Replacement commit knowledge.\n")
        tree = self.git(self.child, "mktree",
                        input=f"100644 blob {replacement}\tREADME.md\n".encode("ascii"))
        commit = self.git(self.child, "commit-tree", tree, "-p", revision,
                          input=b"Synthetic replacement commit\n")
        self.git(self.child, "replace", revision, commit)
        self.assertEqual(self.git(self.child, "show", "HEAD:README.md"),
                         "Replacement commit knowledge.")

        bundle = self.bundle()

        self.assertEqual(bundle["source"]["revision"], revision)
        self.assertEqual([item["path"] for item in bundle["documents"]], ["README.md"])
        self.assertEqual(base64.b64decode(bundle["documents"][0]["content"]), original)

    def test_git_blob_replacement_cannot_change_exported_document_bytes(self):
        original = b"Original committed blob.\n"
        self.write(self.child, "README.md", original)
        revision = self.commit(self.child, "README.md")
        blob = self.git(self.child, "rev-parse", "HEAD:README.md")
        replacement = self.git(self.child, "hash-object", "-w", "--stdin",
                               input=b"Replacement blob knowledge.\n")
        self.git(self.child, "replace", blob, replacement)
        self.assertEqual(self.git(self.child, "cat-file", "blob", blob),
                         "Replacement blob knowledge.")

        bundle = self.bundle()

        self.assertEqual(bundle["source"]["revision"], revision)
        self.assertEqual(base64.b64decode(bundle["documents"][0]["content"]), original)

    def test_document_formats_are_selected_with_asset_directory_boundaries(self):
        allowed = {
            "README.md": b"# Research\n",
            "src/design.rst": b"Design\n======\n",
            "derivations/proof.tex": b"\\begin{proof}A proof.\\end{proof}\n",
            "references.bib": b"@misc{fixture,title={A fixture}}\n",
            "notes/design.txt": b"Documented decisions.\n",
            "docs/appendix.pdf": b"%PDF-1.7\nfixture\x00",
            "documentation/design.docx": b"PK\x03\x04fixture\x00",
            "reports/talk.pptx": b"PK\x03\x04fixture slides\x00",
            "figures/shape.png": b"\x89PNG\r\n\x1a\nfixture\x00",
        }
        excluded = {
            "appendix.pdf": b"%PDF-1.7\nunscoped asset",
            "src/shape.png": b"unscoped image",
            "src/implementation.py": b"pass\n",
            "docs/archive.zip": b"unsupported archive",
        }
        for path, content in {**allowed, **excluded}.items():
            self.write(self.child, path, content)
        self.commit(self.child, *allowed, *excluded)

        documents = {item["path"]: item for item in self.bundle()["documents"]}

        self.assertEqual(set(documents), set(allowed))
        for path, content in allowed.items():
            with self.subTest(path=path):
                self.assertEqual(base64.b64decode(documents[path]["content"]), content)

    def test_private_directories_and_active_instruction_documents_are_excluded(self):
        excluded = [
            ".private/hidden.md", "docs/.private/hidden.md", "node_modules/manual.md",
            "logs/entry.md", "transcripts/example.md", "conversations/example.md",
            "prompts/example.md", "raw/example.md", "data/description.md",
            "tests/example.md", "fixtures/example.md", "docs-vault/example.md", "docs/vault/example.md",
            "AGENTS.md", "docs/CLAUDE.md", "SKILL.md", "review/REVIEW.md",
        ]
        for path in excluded:
            self.write(self.child, path, "Synthetic excluded fixture.\n")
        self.write(self.child, "docs/findings.md", "Permitted research finding.\n")
        self.commit(self.child, *excluded, "docs/findings.md")

        documents = self.bundle()["documents"]

        self.assertEqual([item["path"] for item in documents], ["docs/findings.md"])

    def test_build_manifests_and_prompt_templates_are_never_documents(self):
        excluded = [
            "CMakeLists.txt", "cpp/CMakeLists.txt", "docs/CMakeLists.txt",
            "requirements.txt", "requirements.cloud.txt", "constraints.cloud.txt",
            "docs/requirements-dev.txt", "docs/constraints_test.txt",
            "docs/requirements311.txt", "docs/constraintsprod.txt",
            "cpp/thirdparty/blake3/README.md", "third-party/manual.md",
            "docs/HANDOFF_PROMPT.md", "docs/master_prompt.md", "docs/PrOmPtS-guide.md",
        ]
        allowed = ["README.md", "docs/requirements.md", "docs/guion-teleprompter.md"]
        for name in excluded + allowed:
            self.write(self.child, name, "Synthetic selection fixture.\n")
        self.commit(self.child, *excluded, *allowed)
        self.assertEqual({item["path"] for item in self.bundle()["documents"]}, set(allowed))
        for name in excluded:
            with self.subTest(name=name):
                self.assertFalse(ks._selected(name, {name}))
                self.data["sources"][0]["include_paths"] = [name]
                with self.assertRaises(ks.KnowledgeError):
                    self.bundle()

    def test_explicit_hidden_document_paths_export_only_the_selected_head_files(self):
        self.write(self.child, ".codex/RESEARCH.md", "Committed research method.\n")
        self.write(self.child, ".claude/docs/domain.md", "Committed domain documentation.\n")
        self.write(self.child, ".codex/unselected.md", "Unselected hidden document.\n")
        self.commit(self.child, ".codex/RESEARCH.md", ".claude/docs/domain.md",
                    ".codex/unselected.md")
        self.assertEqual(self.bundle()["documents"], [])
        self.data["sources"][0]["include_paths"] = [
            ".codex/RESEARCH.md", ".claude/docs/domain.md",
        ]
        self.write(self.child, ".codex/RESEARCH.md", "Dirty replacement.\n")
        documents = {item["path"]: item for item in self.bundle()["documents"]}
        self.assertEqual(set(documents), {".codex/RESEARCH.md", ".claude/docs/domain.md"})
        self.assertEqual(base64.b64decode(documents[".codex/RESEARCH.md"]["content"]),
                         b"Committed research method.\n")
        self.assertTrue(all(item["origin"] == "git" for item in documents.values()))

    def test_explicit_hidden_selection_cannot_override_private_or_active_document_veto(self):
        for path in (".codex/prompts/example.md", ".codex/AGENTS.md", "raw/report.md"):
            with self.subTest(path=path):
                self.write(self.child, path, "Synthetic excluded document.\n")
                self.commit(self.child, path)
                self.data["sources"][0]["include_paths"] = [path]
                with self.assertRaises(ks.KnowledgeError):
                    self.bundle()

    def test_explicit_hidden_selection_is_limited_to_supported_document_areas(self):
        for path in (".private/method.md", ".claude/other.md", ".codex/.private/method.md"):
            with self.subTest(path=path):
                self.write(self.child, path, "Synthetic hidden document.\n")
                self.commit(self.child, path)
                self.data["sources"][0]["include_paths"] = [path]
                with self.assertRaises(ks.KnowledgeError):
                    self.bundle()

    def test_bundle_is_deterministic_and_hashes_cover_exact_payloads(self):
        self.write(self.child, "notes/z.md", "Last.\n")
        self.write(self.child, "README.md", "First.\n")
        self.commit(self.child, "notes/z.md", "README.md")
        first = self.bundle()
        second = self.bundle()
        self.assertEqual(first, second)
        self.assertEqual([item["path"] for item in first["documents"]],
                         sorted(item["path"] for item in first["documents"]))
        for item in first["documents"]:
            content = base64.b64decode(item["content"], validate=True)
            self.assertEqual(item["sha256"], hashlib.sha256(content).hexdigest())
        payload = {key: value for key, value in first.items() if key != "bundle_hash"}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False).encode("utf-8")
        self.assertEqual(first["bundle_hash"], hashlib.sha256(canonical).hexdigest())

    def test_eligible_git_symlink_is_rejected_without_dereferencing(self):
        outside = self.write(self.base, "outside.md", "Outside fixture.\n")
        (self.child / "README.md").symlink_to(outside)
        self.commit(self.child, "README.md")
        with self.assertRaises(ks.KnowledgeError):
            self.bundle()

    def test_regular_executable_git_document_mode_is_supported(self):
        document = self.write(self.child, "docs/executable.md", "Regular document.\n")
        document.chmod(0o755)
        self.commit(self.child, "docs/executable.md")
        self.assertTrue(self.git(self.child, "ls-tree", "HEAD", "docs/executable.md")
                        .startswith("100755 "))
        documents = self.bundle()["documents"]
        self.assertEqual([item["path"] for item in documents], ["docs/executable.md"])

    def test_unicode_and_case_collisions_are_rejected_in_git_tree(self):
        for names in (("Readme.md", "README.md"), ("caf\u00e9.md", "cafe\u0301.md")):
            with self.subTest(names=names):
                root = self.hub / ("Collision" + str(len(names[0])))
                self.initialize(root)
                self.registry["repositories"].append({"path": root.name,
                                                       "management": "native"})
                self.write(self.hub, ".codex/repositories.json", json.dumps(self.registry))
                blob = self.git(root, "hash-object", "-w", "--stdin", input=b"Collision fixture.\n")
                for name in names:
                    self.git(root, "-c", "core.ignorecase=false", "update-index", "--add",
                             "--cacheinfo", f"100644,{blob},{name}")
                self.git(root, "commit", "-qm", "Record colliding paths")
                self.data["sources"] = [{"root": str(root), "alias": "collision",
                                         "classification": "personal"}]
                with self.assertRaises(ks.KnowledgeError):
                    self.bundle()

    def test_normalized_file_directory_prefix_collisions_are_rejected_in_git_tree(self):
        blob = self.git(self.child, "hash-object", "-w", "--stdin",
                        input=b"Synthetic prefix collision.\n")
        child_tree = self.git(self.child, "mktree",
                              input=f"100644 blob {blob}\tchild.md\n".encode("ascii"))
        for file_name, directory_name in (
                ("A.md", "a.md"), ("caf\u00e9.md", "cafe\u0301.md"),
                ("\u0390.md", "\u03aa\u0301.md"), ("\u03aa\u0301.md", "\u0390.md"),
                ("\u03b0.md", "\u03ab\u0301.md"), ("\u03ab\u0301.md", "\u03b0.md")):
            with self.subTest(file_name=file_name, directory_name=directory_name):
                entries = (f"100644 blob {blob}\t{file_name}\n"
                           f"040000 tree {child_tree}\t{directory_name}\n")
                docs_tree = self.git(self.child, "mktree", input=entries.encode("utf-8"))
                root_tree = self.git(self.child, "mktree",
                                     input=f"040000 tree {docs_tree}\tdocs\n".encode("ascii"))
                revision = self.git(self.child, "commit-tree", root_tree,
                                    "-p", self.git(self.child, "rev-parse", "HEAD"),
                                    input=b"Record normalized prefix collision\n")
                self.git(self.child, "update-ref", "HEAD", revision)
                paths = self.git(self.child, "-c", "core.quotepath=false", "ls-tree",
                                 "-r", "--name-only", "HEAD").splitlines()
                self.assertEqual(set(paths), {
                    f"docs/{file_name}", f"docs/{directory_name}/child.md",
                })
                with self.assertRaises(ks.KnowledgeError):
                    self.bundle()

    def test_resource_limits_reject_oversized_documents_counts_and_payloads(self):
        self.write(self.child, "README.md", "123456789\n")
        self.write(self.child, "docs/report.md", "abcdefghij\n")
        self.commit(self.child, "README.md", "docs/report.md")
        for constant, limit in (("MAX_FILE_BYTES", 8), ("MAX_REPO_BYTES", 12),
                                ("MAX_DOCUMENTS", 1), ("MAX_BUNDLE_BYTES", 32)):
            with self.subTest(constant=constant), patch.object(ks, constant, limit):
                with self.assertRaises(ks.KnowledgeError):
                    self.bundle()

    def test_local_reports_need_explicit_roots_and_allowed_basenames(self):
        self.write(self.child, "README.md", "Committed.\n")
        self.commit(self.child, "README.md")
        local = {
            "output/report.md": b"Local research report.\n",
            "output/nested/diagnostics.md": b"Local diagnostics.\n",
            "output/sleeve_diagnostics.md": b"Local sleeve diagnostics.\n",
            "output/comparison_2026-10-19.md": b"Local comparison.\n",
        }
        excluded = {
            "output/other.md": b"Unapproved local basename.\n",
            "elsewhere/report.md": b"Outside explicitly selected root.\n",
            "output/raw/report.md": b"Excluded raw fixture.\n",
        }
        for path, content in {**local, **excluded}.items():
            self.write(self.child, path, content)
        self.assertEqual([item["path"] for item in self.bundle()["documents"]], ["README.md"])
        self.data["sources"][0]["local_paths"] = ["output"]
        documents = {item["path"]: item for item in self.bundle()["documents"]}
        self.assertEqual(set(documents), {"README.md", *local})
        for path, content in local.items():
            self.assertEqual(documents[path]["origin"], "local")
            self.assertEqual(base64.b64decode(documents[path]["content"]), content)

    def test_explicit_local_root_and_nested_reports_reject_symlink_components(self):
        report_root = self.child / "output"
        report_root.mkdir()
        outside = self.base / "outside"
        self.write(outside, "report.md", "External synthetic report.\n")
        self.data["sources"][0]["local_paths"] = ["output"]
        (report_root / "nested").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ks.KnowledgeError):
            self.bundle()
        (report_root / "nested").unlink()
        report_root.rmdir()
        report_root.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ks.KnowledgeError):
            self.bundle()

    def test_committed_report_precedes_dirty_copy_in_explicit_local_report_root(self):
        self.write(self.child, "output/report.md", "Committed report.\n")
        self.commit(self.child, "output/report.md")
        self.write(self.child, "output/report.md", "Dirty report.\n")
        self.data["sources"][0]["local_paths"] = ["output"]
        documents = self.bundle()["documents"]
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["origin"], "git")
        self.assertEqual(base64.b64decode(documents[0]["content"]), b"Committed report.\n")

    def test_local_report_copies_direct_figures_and_tables_within_authorized_roots(self):
        self.write(self.child, "output/reports/report.md", (
            "# Results\n\n![Figure](../figures/curve.png#figure)\n\n"
            "[Metrics](<../tables/metrics.md>)\n\n"
            "[Outside](../../outside.pdf)\n\n"
            "[Remote](https://example.invalid/research.pdf)\n"
        ))
        figure = b"\x89PNG\r\n\x1a\nsynthetic figure\x00"
        table = b"| Value |\n| --- |\n| 3 |\n\n![Nested](../figures/nested.png)\n"
        self.write(self.child, "output/figures/curve.png", figure)
        self.write(self.child, "output/tables/metrics.md", table)
        self.write(self.child, "output/figures/nested.png", b"Unrequested nested dependency")
        self.write(self.child, "output/figures/unreferenced.png", b"Unreferenced asset")
        self.write(self.child, "outside.pdf", b"%PDF-1.7\nOutside explicitly authorized roots")
        self.data["sources"][0]["local_paths"] = ["output"]
        documents = {item["path"]: item for item in self.bundle()["documents"]}
        self.assertEqual(set(documents), {
            "output/reports/report.md", "output/figures/curve.png", "output/tables/metrics.md",
        })
        self.assertEqual(base64.b64decode(documents["output/figures/curve.png"]["content"]), figure)
        self.assertEqual(base64.b64decode(documents["output/tables/metrics.md"]["content"]), table)
        self.assertTrue(all(item["origin"] == "local" for item in documents.values()))

    def test_local_report_copies_balanced_parenthesis_angle_and_encoded_inline_destinations(self):
        report = (
            '# Results\n\n![Raw](figures/plot(a).png)\n'
            '![Nested](figures/plot((b)).png "Nested plot")\n'
            '![Angle](<figures/angle(c).png> "Angle plot")\n'
            "![Encoded](figures/encoded%28d%29.png 'Encoded title')\n"
            '![Brackets](figures/%5Bencoded%5D.png)\n'
            '![Spaces](<figures/space name(e).png>)\n'
            r'![Escaped](figures/plot\(one\).png)' '\n'
            r'![Right](figures/foo\).png)' '\n'
            r'![Invalid bare space](figures/escaped\ space.png)' '\n'
        )
        assets = {
            "output/figures/plot(a).png", "output/figures/plot((b)).png",
            "output/figures/angle(c).png", "output/figures/encoded(d).png",
            "output/figures/[encoded].png", "output/figures/space name(e).png",
            "output/figures/plot(one).png", "output/figures/foo).png",
        }
        self.write(self.child, "output/report.md", report)
        contents = {}
        for path in assets:
            contents[path] = b"\x89PNG\r\n\x1a\n" + path.encode("utf-8")
            self.write(self.child, path, contents[path])
        self.write(self.child, "output/figures/escaped space.png", b"Invalid bare link must not select this asset")
        self.data["sources"][0]["local_paths"] = ["output"]
        self.assertEqual(ks._dependencies("output/report.md", report, ["output"]), sorted(assets))

        documents = {item["path"]: item for item in self.bundle()["documents"]}

        self.assertEqual(set(documents), {"output/report.md", *assets})
        for path, content in contents.items():
            self.assertEqual(base64.b64decode(documents[path]["content"]), content)
        self.assertTrue(all(item["origin"] == "local" for item in documents.values()))

    def test_inline_link_parser_finishes_malformed_inputs_within_subprocess_timeout(self):
        script = r'''
import importlib.util
import json
import sys

spec = importlib.util.spec_from_file_location("knowledge_parser_fixture", sys.argv[1])
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
malformed = [
    "[x](" + "a" * 100_000,
    "[x](chart.png " + " " * 100_000,
    "[x](" * 25_000,
]
for index, text in enumerate(malformed):
    assert module._dependencies("output/report.md", text, ["output"]) == [], index
positive = (
    '[Chart](figures/curve.png "Quoted title")\n'
    '[Angle](<figures/with space.png> "Angle title")\n'
    '[Encoded](figures/%5Bcurve%5D.png)\n'
    "[Table](tables/metrics.md 'Table title')\n"
)
expected = sorted([
    "output/figures/curve.png", "output/figures/with space.png",
    "output/figures/[curve].png", "output/tables/metrics.md",
])
assert module._dependencies("output/report.md", positive, ["output"]) == expected
print(json.dumps({"malformed": len(malformed), "positive": len(expected)}))
'''
        result = subprocess.run([
            sys.executable, "-I", "-S", "-c", script, str(Path(ks.__file__)),
        ], capture_output=True, text=True, timeout=3)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"malformed": 3, "positive": 4})

    def test_local_report_includes_tracked_asset_from_head_despite_dirty_working_copy(self):
        original = b"\x89PNG\r\n\x1a\ncommitted chart\x00"
        self.write(self.child, "output/chart.png", original)
        revision = self.commit(self.child, "output/chart.png")
        self.write(self.child, "output/chart.png", b"Dirty chart must never be copied")
        self.write(self.child, "output/report.md", "# Results\n\n![Chart](chart.png)\n")
        self.data["sources"][0]["local_paths"] = ["output"]
        before = self.git(self.child, "status", "--porcelain")

        bundle = self.bundle()

        documents = {item["path"]: item for item in bundle["documents"]}
        self.assertEqual(set(documents), {"output/report.md", "output/chart.png"})
        self.assertEqual(documents["output/report.md"]["origin"], "local")
        self.assertEqual(documents["output/chart.png"]["origin"], "git")
        self.assertEqual(base64.b64decode(documents["output/chart.png"]["content"]), original)
        self.assertEqual(bundle["source"]["revision"], revision)
        self.assertEqual(self.git(self.child, "status", "--porcelain"), before)

    def test_explicit_local_report_symlink_is_rejected(self):
        outside = self.write(self.base, "report.md", "External synthetic report.\n")
        report_root = self.child / "output"
        report_root.mkdir()
        (report_root / "report.md").symlink_to(outside)
        self.data["sources"][0]["local_paths"] = ["output"]
        with self.assertRaises(ks.KnowledgeError):
            self.bundle()


class KnowledgeRaceTests(KnowledgeFixture):
    def prepare_source_swap(self):
        original = b"Authorized original research.\n"
        self.write(self.child, "README.md", original)
        revision = self.commit(self.child, "README.md")
        outside = self.base / "OutsideRepository"
        self.initialize(outside)
        self.write(outside, "README.md", "Outside repository must never be exported.\n")
        self.commit(outside, "README.md")
        return self.policy(), outside, original, revision

    def assert_original_or_rejected(self, operation, original: bytes, revision: str,
                                    additional: dict[str, bytes] | None = None):
        try:
            bundle = operation()
        except ks.KnowledgeError:
            return
        self.assertEqual(bundle["source"]["revision"], revision)
        expected = {"README.md": original, **(additional or {})}
        self.assertEqual([item["path"] for item in bundle["documents"]], sorted(expected))
        for document in bundle["documents"]:
            self.assertEqual(base64.b64decode(document["content"]), expected[document["path"]])

    def prepare_local_source_swap(self):
        policy, outside, original, revision = self.prepare_source_swap()
        report = b"Original local finding.\n\n![Chart](chart.png)\n"
        chart = b"\x89PNG\r\n\x1a\noriginal local chart\x00"
        self.write(self.child, "output/report.md", report)
        self.write(self.child, "output/chart.png", chart)
        self.write(outside, "output/report.md", "Outside local report.\n\n![Chart](chart.png)\n")
        self.write(outside, "output/chart.png", b"Outside local chart must never be exported")
        self.data["sources"][0]["local_paths"] = ["output"]
        return self.policy(), outside, original, revision, {
            "output/report.md": report, "output/chart.png": chart,
        }

    def test_source_root_swap_after_authorization_cannot_export_outside_repository(self):
        policy, outside, original, revision = self.prepare_source_swap()
        preserved = self.base / "PreservedResearch"
        authorize = ks._authorize
        swapped = False

        def replace_after_authorization(*args, **kwargs):
            nonlocal swapped
            result = authorize(*args, **kwargs)
            if not swapped:
                self.child.rename(preserved)
                self.child.symlink_to(outside, target_is_directory=True)
                swapped = True
            return result

        try:
            with patch.object(ks, "_authorize", side_effect=replace_after_authorization):
                self.assert_original_or_rejected(
                    lambda: ks.collect_bundle(policy, policy["sources"][0]), original, revision,
                )
            self.assertTrue(swapped, "The authorization boundary was not exercised")
        finally:
            if swapped:
                self.child.unlink()
                preserved.rename(self.child)

    def test_source_root_swap_at_git_launch_cannot_export_outside_repository(self):
        policy, outside, original, revision = self.prepare_source_swap()
        preserved = self.base / "PreservedResearch"
        real_run = subprocess.run
        swapped = False

        def replace_at_git_launch(arguments, *args, **kwargs):
            nonlocal swapped
            if isinstance(arguments, (list, tuple)) and "HEAD^{commit}" in arguments and not swapped:
                self.child.rename(preserved)
                self.child.symlink_to(outside, target_is_directory=True)
                swapped = True
            return real_run(arguments, *args, **kwargs)

        try:
            with patch.object(ks.subprocess, "run", side_effect=replace_at_git_launch):
                self.assert_original_or_rejected(
                    lambda: ks.collect_bundle(policy, policy["sources"][0]), original, revision,
                )
            self.assertTrue(swapped, "The Git process launch boundary was not exercised")
        finally:
            if swapped:
                self.child.unlink()
                preserved.rename(self.child)

    def test_real_repository_swap_after_authorization_cannot_export_outside_git_or_local_bytes(self):
        policy, outside, original, revision, local = self.prepare_local_source_swap()
        preserved = self.base / "PreservedResearch"
        authorize = ks._authorize
        swapped = False

        def replace_after_authorization(*args, **kwargs):
            nonlocal swapped
            result = authorize(*args, **kwargs)
            if not swapped:
                self.child.rename(preserved)
                outside.rename(self.child)
                swapped = True
            return result

        try:
            with patch.object(ks, "_authorize", side_effect=replace_after_authorization):
                self.assert_original_or_rejected(
                    lambda: ks.collect_bundle(policy, policy["sources"][0]), original, revision, local,
                )
            self.assertTrue(swapped, "The real-directory authorization race was not exercised")
        finally:
            if swapped:
                self.child.rename(outside)
                preserved.rename(self.child)

    def test_real_repository_swap_before_local_collection_cannot_export_outside_reports_or_assets(self):
        policy, outside, original, revision, local = self.prepare_local_source_swap()
        preserved = self.base / "PreservedResearch"
        local_documents = ks._local_documents
        swapped = False

        def replace_before_local_collection(*args, **kwargs):
            nonlocal swapped
            if not swapped:
                self.child.rename(preserved)
                outside.rename(self.child)
                swapped = True
            return local_documents(*args, **kwargs)

        try:
            with patch.object(ks, "_local_documents", side_effect=replace_before_local_collection):
                self.assert_original_or_rejected(
                    lambda: ks.collect_bundle(policy, policy["sources"][0]), original, revision, local,
                )
            self.assertTrue(swapped, "The real-directory local collection race was not exercised")
        finally:
            if swapped:
                self.child.rename(outside)
                preserved.rename(self.child)

    def test_git_executable_is_absolute_before_helper_enters_source_directory(self):
        real_git = Path(shutil.which("git")).resolve(strict=True)
        caller = self.base / "TrustedCaller"
        caller_tools = caller / "relative-tools"
        caller_tools.mkdir(parents=True)
        (caller_tools / "git").symlink_to(real_git)
        source_git = self.write(self.child, "relative-tools/git",
                                "# Inert executable fixture; must never be invoked.\n")
        source_git.chmod(0o755)
        original_cwd = Path.cwd()
        real_run = subprocess.run
        calls = []

        def inspect_without_running_source_executable(arguments, *args, **kwargs):
            self.assertIsInstance(arguments, (list, tuple))
            self.assertIn(ks.GIT_HELPER, arguments,
                          "Refusing to launch an uninspected executable from the source fixture")
            executable = Path(arguments[list(arguments).index(ks.GIT_HELPER) + 2])
            self.assertTrue(executable.is_absolute(),
                            "Git must be selected before the helper changes directory")
            self.assertEqual(executable.resolve(strict=True), real_git)
            calls.append(executable)
            return real_run(arguments, *args, **kwargs)

        try:
            os.chdir(caller)
            with patch.dict(os.environ, {"PATH": "relative-tools" + os.pathsep + os.environ["PATH"]}), \
                    patch.object(ks.subprocess, "run", side_effect=inspect_without_running_source_executable):
                result = ks._git(self.child, "rev-parse", "--show-toplevel")
        finally:
            os.chdir(original_cwd)
        self.assertEqual(result.decode("utf-8").strip(), str(self.child))
        self.assertEqual(calls, [real_git])


class KnowledgeDeliveryTests(KnowledgeFixture):
    def setUp(self):
        super().setUp()
        self.write(self.child, "README.md", "Synthetic research result.\n")
        self.commit(self.child, "README.md")
        self.receiver = self.write(self.target, ".codex/knowledge_import.py",
                                   '"""Receiver process fixture; intercepted by the transport test."""\n')

    def receiver_transport(self, *, reject_alias: str | None = None,
                           receipt_changes: dict | None = None,
                           malformed_alias: str | None = None,
                           raw_receipt: str = ""):
        real_run = subprocess.run
        deliveries = []

        def run(arguments, *args, **kwargs):
            if isinstance(arguments, (list, tuple)) and str(self.receiver) in arguments:
                self.assertFalse(kwargs.get("shell", False))
                self.assertEqual(list(arguments)[1:], [str(self.receiver), "--policy",
                                                     str(self.policy_path), "import"])
                bundle = json.loads(kwargs["input"])
                deliveries.append(bundle)
                receipt = {
                    "schema_version": 1, "status": "RECEIVED_LOCAL",
                    "bundle_hash": bundle["bundle_hash"],
                    "alias": bundle["source"]["alias"],
                    "revision": bundle["source"]["revision"],
                    "count": len(bundle["documents"]), "changed": [],
                    "at": "2026-10-19T00:00:00Z",
                }
                receipt.update(receipt_changes or {})
                output = (raw_receipt if bundle["source"]["alias"] == malformed_alias
                          else json.dumps(receipt))
                if not kwargs.get("text") and not kwargs.get("encoding"):
                    output = output.encode("utf-8")
                returncode = 1 if bundle["source"]["alias"] == reject_alias else 0
                if returncode and kwargs.get("check"):
                    raise subprocess.CalledProcessError(
                        returncode, arguments, output=output, stderr="Synthetic receiver failure",
                    )
                return subprocess.CompletedProcess(arguments, returncode, stdout=output,
                                                   stderr="" if isinstance(output, str) else b"")
            return real_run(arguments, *args, **kwargs)

        return patch.object(ks.subprocess, "run", side_effect=run), deliveries

    def test_sync_sends_complete_stdin_bundle_and_reports_only_local_receipt(self):
        transport, deliveries = self.receiver_transport()
        with transport:
            result = ks.sync(self.policy_path)
        self.assertEqual(len(deliveries), 1)
        self.assertEqual(base64.b64decode(deliveries[0]["documents"][0]["content"]),
                         b"Synthetic research result.\n")
        self.assertEqual(result["scope"], "local")
        self.assertEqual(result["errors"], [])
        self.assertEqual(len(result["receipts"]), 1)
        self.assertEqual(result["receipts"][0]["status"], "RECEIVED_LOCAL")
        self.assertNotIn("published", result)
        self.assertEqual(self.git(self.target, "log", "--format=%s"), "Initialize fixture")

    def test_receiver_failure_keeps_other_sources_deliverable(self):
        self.write(self.work, "docs/report.md", "Synthetic work report.\n")
        self.commit(self.work, "docs/report.md")
        self.data["sources"].insert(0, {
            "root": str(self.work), "alias": "work-lab", "classification": "work",
        })
        self.save_policy()
        transport, deliveries = self.receiver_transport(reject_alias="work-lab")
        with transport:
            result = ks.sync(self.policy_path)
        self.assertEqual({item["source"]["alias"] for item in deliveries},
                         {"work-lab", "research-lab"})
        self.assertEqual([item["alias"] for item in result["receipts"]], ["research-lab"])
        self.assertEqual([item["alias"] for item in result["errors"]], ["work-lab"])
        self.assertEqual(result["scope"], "local")

    def test_unmatched_receiver_receipt_is_not_counted_as_success(self):
        for replacement in ({"bundle_hash": "0" * 64}, {"alias": "different-source"},
                            {"revision": "0" * 40}, {"count": 99},
                            {"count": True}, {"schema_version": True},
                            {"status": "PUBLISHED"}, {"schema_version": 2}):
            with self.subTest(replacement=replacement):
                transport, _ = self.receiver_transport(receipt_changes=replacement)
                with transport:
                    result = ks.sync(self.policy_path)
                self.assertEqual(result["receipts"], [])
                self.assertEqual([item["alias"] for item in result["errors"]], ["research-lab"])

    def test_malformed_receipts_are_isolated_and_other_sources_continue(self):
        self.write(self.work, "docs/report.md", "Synthetic work report.\n")
        self.commit(self.work, "docs/report.md")
        self.data["sources"].insert(0, {
            "root": str(self.work), "alias": "work-lab", "classification": "work",
        })
        self.save_policy()
        for raw in ("{broken", "null", "[]", ""):
            with self.subTest(raw=raw):
                transport, deliveries = self.receiver_transport(
                    malformed_alias="work-lab", raw_receipt=raw,
                )
                with transport:
                    result = ks.sync(self.policy_path)
                self.assertEqual({item["source"]["alias"] for item in deliveries},
                                 {"work-lab", "research-lab"})
                self.assertEqual([item["alias"] for item in result["receipts"]], ["research-lab"])
                self.assertEqual([item["alias"] for item in result["errors"]], ["work-lab"])

    def test_repo_filter_does_not_authorize_a_registered_native_source(self):
        transport, deliveries = self.receiver_transport()
        with transport, self.assertRaises(ks.KnowledgeError):
            ks.sync(self.policy_path, repo=self.work.name)
        self.assertEqual(deliveries, [])

    def test_collection_failure_is_isolated_and_does_not_send_invalid_source(self):
        outside = self.write(self.base, "outside.md", "Outside fixture.\n")
        (self.work / "README.md").symlink_to(outside)
        self.commit(self.work, "README.md")
        self.data["sources"].insert(0, {
            "root": str(self.work), "alias": "work-lab", "classification": "work",
        })
        self.save_policy()
        transport, deliveries = self.receiver_transport()
        with transport:
            result = ks.sync(self.policy_path)
        self.assertEqual([item["source"]["alias"] for item in deliveries], ["research-lab"])
        self.assertEqual([item["alias"] for item in result["errors"]], ["work-lab"])
        self.assertEqual([item["alias"] for item in result["receipts"]], ["research-lab"])


class KnowledgeEnrollmentTests(KnowledgeFixture):
    def test_status_distinguishes_registration_from_export_consent(self):
        result = ks.status(self.policy_path)
        self.assertEqual(result["scope"], "local")
        serialized_pending = json.dumps(result["pending"])
        self.assertIn("WorkLab", serialized_pending)
        self.assertNotIn("ResearchLab", serialized_pending)
        self.assertIn("External", json.dumps(result["external"]))
        self.assertNotIn("External", serialized_pending)

    def test_status_discovers_only_unregistered_direct_git_roots_without_authorizing_them(self):
        unregistered = self.hub / "UnregisteredResearch"
        self.initialize(unregistered)
        self.initialize(self.hub / ".HiddenResearch")
        self.initialize(self.hub / "Container/NestedResearch")
        outside = self.base / "OutsideResearch"
        self.initialize(outside)
        (self.hub / "LinkedResearch").symlink_to(outside, target_is_directory=True)
        (self.hub / "Scratch").mkdir()
        registry_before = (self.hub / ".codex/repositories.json").read_bytes()
        policy_before = self.policy_path.read_bytes()

        result = ks.status(self.policy_path)

        discovered = [item for item in result["pending"]
                      if item["management"] == "unregistered"]
        self.assertEqual({Path(item["root"]) for item in discovered}, {unregistered})
        self.assertNotIn(unregistered, {Path(item["root"]) for item in result["enrolled"]})
        self.assertEqual((self.hub / ".codex/repositories.json").read_bytes(), registry_before)
        self.assertEqual(self.policy_path.read_bytes(), policy_before)

    def test_enrollment_registers_new_git_root_and_preserves_other_sources_and_metadata(self):
        new_repo = self.hub / "NewResearch"
        self.initialize(new_repo)
        self.registry["repositories"][1]["description"] = "Preserve this metadata"
        self.write(self.hub, ".codex/repositories.json", json.dumps(self.registry))
        existing = self.policy_path.read_bytes()
        ks.enroll(self.policy_path, new_repo.name, "work", local_paths=["output"],
                  hub_root=self.hub)
        policy = ks.load_policy(self.policy_path)
        original = json.loads(existing)["sources"][0]
        preserved = [item for item in policy["sources"] if item["root"] == original["root"]]
        self.assertEqual(preserved, [original])
        added = [item for item in policy["sources"] if Path(item["root"]) == new_repo]
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0]["classification"], "work")
        self.assertEqual(added[0]["local_paths"], ["output"])
        registry = json.loads((self.hub / ".codex/repositories.json").read_text())
        self.assertEqual(registry["repositories"][:4], self.registry["repositories"])
        self.assertIn({"path": "NewResearch", "management": "native"},
                      registry["repositories"])

    def test_enrollment_preserves_concurrent_registry_edits_and_retries_without_partial_consent(self):
        registry_path = self.hub / ".codex/repositories.json"
        for index, phase in enumerate(("after_snapshot", "before_registry_write")):
            with self.subTest(phase=phase):
                new_repo = self.hub / f"NewResearch{index}"
                concurrent_repo = self.hub / f"ConcurrentResearch{index}"
                self.initialize(new_repo)
                self.initialize(concurrent_repo)
                policy_before = self.policy_path.read_bytes()
                concurrent_entry = {
                    "path": concurrent_repo.name, "management": "native",
                    "description": "Independent registry update must survive enrollment",
                }
                concurrent_bytes = None
                real_read = ks._read
                real_write = ks._write

                def inject_concurrent_entry(snapshot):
                    nonlocal concurrent_bytes
                    registry = json.loads(snapshot)
                    registry["repositories"].append(concurrent_entry)
                    concurrent_bytes = (json.dumps(registry, indent=2) + "\n").encode("utf-8")
                    registry_path.write_bytes(concurrent_bytes)

                def edit_after_snapshot(path, *args, **kwargs):
                    snapshot = real_read(path, *args, **kwargs)
                    if Path(path) == registry_path and concurrent_bytes is None:
                        inject_concurrent_entry(snapshot)
                    return snapshot

                def edit_before_registry_write(path, *args, **kwargs):
                    if Path(path) == registry_path and concurrent_bytes is None:
                        inject_concurrent_entry(registry_path.read_bytes())
                    return real_write(path, *args, **kwargs)

                interception = (patch.object(ks, "_read", side_effect=edit_after_snapshot)
                                if phase == "after_snapshot" else
                                patch.object(ks, "_write", side_effect=edit_before_registry_write))
                with interception, self.assertRaises(ks.KnowledgeError):
                    ks.enroll(self.policy_path, new_repo.name, "work", hub_root=self.hub)
                self.assertIsNotNone(concurrent_bytes, "The concurrent registry edit was not exercised")
                self.assertEqual(registry_path.read_bytes(), concurrent_bytes)
                self.assertEqual(self.policy_path.read_bytes(), policy_before)
                self.assertNotIn(new_repo.name, {
                    entry["path"] for entry in json.loads(concurrent_bytes)["repositories"]
                })

                result = ks.enroll(self.policy_path, new_repo.name, "work", hub_root=self.hub)
                self.assertEqual(result["status"], "ENROLLED_LOCAL")
                registry = json.loads(registry_path.read_bytes())
                self.assertIn(concurrent_entry, registry["repositories"])
                self.assertIn({"path": new_repo.name, "management": "native"},
                              registry["repositories"])
                policy = ks.load_policy(self.policy_path)
                sources = {source["root"]: source for source in policy["sources"]}
                self.assertEqual(sources[str(new_repo)]["classification"], "work")
                for source in json.loads(policy_before)["sources"]:
                    self.assertEqual(sources[source["root"]], source)

    def test_enrollment_never_overwrites_concurrent_existing_or_new_consent_policy(self):
        for index, phase in enumerate(("existing", "bootstrap")):
            with self.subTest(phase=phase):
                new_repo = self.hub / f"PolicyConflict{index}"
                self.initialize(new_repo)
                policy_path = (self.policy_path if phase == "existing" else
                               self.home / ".codex/concurrent-bootstrap-policy.json")
                external_bytes = None
                real_write = ks._write

                def edit_consent_before_write(path, *args, **kwargs):
                    nonlocal external_bytes
                    if Path(path) == policy_path and external_bytes is None:
                        if phase == "existing":
                            external = json.loads(policy_path.read_bytes())
                            external["sources"][0]["classification"] = "work"
                        else:
                            external = {
                                "schema_version": 1, "hub_root": str(self.hub),
                                "target_root": str(self.target), "sources": [],
                            }
                        external_bytes = (json.dumps(external, indent=2) + "\n").encode("utf-8")
                        policy_path.write_bytes(external_bytes)
                    return real_write(path, *args, **kwargs)

                with patch.object(ks, "_write", side_effect=edit_consent_before_write), \
                        self.assertRaises(ks.KnowledgeError):
                    ks.enroll(policy_path, new_repo.name, "personal", hub_root=self.hub,
                              target_root=self.target)
                self.assertIsNotNone(external_bytes, "The concurrent policy edit was not exercised")
                self.assertEqual(policy_path.read_bytes(), external_bytes)
                policy = ks.load_policy(policy_path)
                self.assertNotIn(str(new_repo), {source["root"] for source in policy["sources"]})
                status = ks.status(policy_path)
                self.assertIn(new_repo, {Path(item["root"]) for item in status["pending"]})
                self.assertNotIn(new_repo, {Path(item["root"]) for item in status["enrolled"]})

                result = ks.enroll(policy_path, new_repo.name, "personal", hub_root=self.hub,
                                   target_root=self.target)
                self.assertEqual(result["status"], "ENROLLED_LOCAL")
                sources = {source["root"]: source for source in ks.load_policy(policy_path)["sources"]}
                self.assertEqual(sources[str(new_repo)]["classification"], "personal")
                for source in json.loads(external_bytes)["sources"]:
                    self.assertEqual(sources[source["root"]], source)

    def test_enrollment_never_converts_external_repository_management(self):
        before = (self.hub / ".codex/repositories.json").read_bytes()
        policy_before = self.policy_path.read_bytes()
        with self.assertRaises(ks.KnowledgeError):
            ks.enroll(self.policy_path, self.external.name, "work", hub_root=self.hub)
        self.assertEqual((self.hub / ".codex/repositories.json").read_bytes(), before)
        self.assertEqual(self.policy_path.read_bytes(), policy_before)

    def test_enrollment_cannot_create_consent_file_inside_source_hub_or_target(self):
        new_repo = self.hub / "NewResearch"
        self.initialize(new_repo)
        registry_before = (self.hub / ".codex/repositories.json").read_bytes()
        for root in (self.hub, self.target):
            candidate = root / ".codex/new-knowledge-consent.json"
            with self.subTest(root=root), self.assertRaises(ks.KnowledgeError):
                ks.enroll(candidate, new_repo.name, "personal", hub_root=self.hub,
                          target_root=self.target)
            self.assertFalse(candidate.exists())
            self.assertEqual((self.hub / ".codex/repositories.json").read_bytes(), registry_before)

    def test_cli_bootstraps_new_policy_with_explicit_hub_target_and_classification(self):
        new_repo = self.hub / "NewResearch"
        self.initialize(new_repo)
        new_policy = self.home / ".codex/new-knowledge-policy.json"
        result = subprocess.run([
            sys.executable, str(Path(ks.__file__)), "--policy", str(new_policy),
            "--hub", str(self.hub), "--target", str(self.target), "enroll",
            "--repo", new_repo.name, "--classification", "personal",
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "ENROLLED_LOCAL")
        policy = ks.load_policy(new_policy)
        self.assertEqual(policy["hub_root"], str(self.hub))
        self.assertEqual(policy["target_root"], str(self.target))
        self.assertEqual(len(policy["sources"]), 1)
        self.assertEqual(policy["sources"][0]["root"], str(new_repo))
        self.assertEqual(policy["sources"][0]["classification"], "personal")

    def test_install_creates_verifiable_plist_without_loading_launchd(self):
        real_run = subprocess.run

        def without_launch(arguments, *args, **kwargs):
            self.assertNotIn("launchctl", str(arguments[0]))
            return real_run(arguments, *args, **kwargs)

        with patch.object(ks.subprocess, "run", side_effect=without_launch):
            result = ks.install(self.policy_path, interval=900)
        self.assertEqual(result["status"], "INSTALLED_NOT_LOADED")
        installed = Path(result["path"])
        self.assertEqual(installed,
                         self.home / "Library/LaunchAgents/com.omar.constellation-knowledge-sync.plist")
        with installed.open("rb") as stream:
            plist = plistlib.load(stream)
        self.assertEqual(plist["StartInterval"], 900)
        self.assertTrue(plist["RunAtLoad"])
        arguments = plist["ProgramArguments"]
        self.assertIsInstance(arguments, list)
        self.assertIn(str(self.policy_path), arguments)
        self.assertIn("sync", arguments)
        self.assertNotIn("/bin/sh", arguments)


if __name__ == "__main__":
    unittest.main()
