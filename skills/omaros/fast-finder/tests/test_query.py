"""Behavior of the installed query CLI against a marked, synthetic Git vault."""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml


QUERY = Path(__file__).resolve().parents[1] / "scripts/query.py"
NOTES = "06_Knowledge_Base"
PRIVATE = f"{NOTES}/Mathematics/Finance/ENGIE/Private"


class QueryCliTest(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="finder_fixture_")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        self.write("05_Projects/OmarOS/Architecture/OmarOS_Architecture.md", "# Fixture\n")

    def write(self, relative: str, content: str) -> Path:
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def note(self, name: str, body: str, **fields: object) -> Path:
        fm = yaml.safe_dump(fields, sort_keys=False, allow_unicode=True)
        return self.write(f"{NOTES}/{name}.md", f"---\n{fm}---\n\n{body}\n")

    def invoke(self, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(QUERY), "--root", str(self.root), *args],
                              text=True, input=stdin, capture_output=True, timeout=15)

    def query(self, *args: str, stdin: str | None = None) -> dict:
        process = self.invoke(*args, stdin=stdin)
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)

    def test_total_occurrences_survive_line_and_output_limits(self) -> None:
        self.write(f"{NOTES}/a.md", ("term term\n" * 10) + "TERM\n")
        self.write(f"{NOTES}/b.md", "term plus term\n")
        count = self.query("content", "term", "--ignore-case")
        self.assertEqual((count["occurrences"], count["matched_files"]), (23, 2))
        self.assertEqual(count["results"], [])
        self.assertFalse(count["partial"])
        for mode in ("hits", "paths"):
            result = self.query("content", "term", "--ignore-case", "--show", mode, "--limit", "1")
            self.assertEqual((result["occurrences"], result["matched_files"]), (23, 2))
            self.assertEqual(len(result["results"]), 1)
            if mode == "hits":
                hit = result["results"][0]
                line = (self.root / hit["path"]).read_text().splitlines()[hit["line"] - 1]
                self.assertIn(line, hit["excerpt"])
                self.assertEqual(hit["matches"], line.casefold().count("term"))
                self.assertEqual(result["total_items"], 12)

    def test_literal_regex_and_exclusion(self) -> None:
        self.write(f"{NOTES}/a.md", "x.y x-y x.y\nx+y\n")
        self.write(f"{NOTES}/b.md", "xx x.y\n")
        literal = self.query("content", "x.y", "--exclude", "**/b.md")
        regex = self.query("content", "x.y", "--regex", "--show", "hits", "--glob", "**/a.md")
        self.assertEqual(literal["occurrences"], 2)
        self.assertEqual(regex["occurrences"], 4)
        self.assertEqual(sorted(hit["matches"] for hit in regex["results"]), [1, 3])

    def test_paths_bound_and_sort_before_limiting(self) -> None:
        for name, size in {"a": 36, "b": 36, "c": 58, "old": 42, "tiny": 1, "large": 100}.items():
            path = self.write(f"{NOTES}/section/{name}.md", "v" * size)
            stamp = datetime(2026, 8, 1 if name == "old" else 10, 12, tzinfo=timezone.utc).timestamp()
            os.utime(path, (stamp, stamp))
        self.write(f"{NOTES}/section/excluded.txt", "z" * 42)
        result = self.query(
            "--path", NOTES, "paths", "--glob", "**/*.md", "--min-size", "30", "--max-size", "60",
            "--since", "2026-08-05", "--until", "2026-08-12", "--sort", "size", "--descending", "--limit", "1",
        )
        self.assertEqual(result["total_items"], 3)
        self.assertFalse(result["partial"])
        first, = result["results"]
        self.assertEqual((Path(first["path"]).name, first["size"]), ("c.md", 58))
        self.assertIn("mtime", first)

    def test_filters_combine_and_group_all_matches(self) -> None:
        shared = dict(title="Vector spaces", status="active", tags=["math", "seminar"], series="A", audience="staff")
        for name, override in [
            ("a", {"state": "retired"}), ("b", {"obsolete": True}), ("c", {"tags": ["physics"]}),
            ("y", {}), ("z", {"series": "B"}),
        ]:
            self.note(name, "Body", **{**shared, **override})
        self.note("d", "Body", **{k: v for k, v in shared.items() if k != "audience"})
        result = self.query(
            "--path", NOTES, "metadata", "--field", "status=active", "--field", "tags=math",
            "--not-field", "state=retired", "--exists", "audience", "--missing", "obsolete",
            "--contains", "title=ector", "--group-by", "series", "--limit", "1",
        )
        self.assertEqual(result["total_items"], 2)
        self.assertFalse(result["partial"])
        self.assertEqual(result["groups"], {"A": 1, "B": 1})
        self.assertEqual(len(result["results"]), 1)

    def test_group_without_value_is_separate_from_literal_label(self) -> None:
        self.note("absent", "Fixture", title="Sin grupo")
        self.note("empty", "Fixture", title="Grupo vacío", series=[])
        self.note("literal", "Fixture", title="Etiqueta literal", series=["<missing>", "<missing>"])
        result = self.query("--path", NOTES, "metadata", "--group-by", "series", "--limit", "0")
        self.assertEqual(result["total_items"], 3)
        self.assertEqual(result["groups"], {"<missing>": 1})
        self.assertEqual(result["missing_group"], 2)
        self.assertEqual(result["results"], [])

    def test_summary_accepts_stdin_and_returns_actual_body(self) -> None:
        text = "El ejemplo conserva la información necesaria."
        self.note("selected", text, title="Nota", status="active", tags=["math", "reference"],
                  updated=date(2026, 11, 2))
        self.note("other", "Otro documento", title="Otra nota")
        for opts, stdin in [([f"{NOTES}/selected.md"], None), (["--stdin"], f"{NOTES}/selected.md\n")]:
            result = self.query("summary", *opts, "--limit", "1", stdin=stdin)
            self.assertEqual(result["total_items"], 1)
            item, = result["results"]
            self.assertEqual((item["title"], item["status"], item["tags"]), ("Nota", "active", ["math", "reference"]))
            self.assertEqual(item["updated"], "2026-11-02")
            self.assertIn(text, item["excerpt"])
        self.assertNotEqual(self.invoke("summary").returncode, 0)
        self.assertEqual(self.query("summary", "--stdin", stdin="")["total_items"], 0)
        self.assertNotEqual(self.invoke("summary", f"{NOTES}/missing.md").returncode, 0)

    def test_invoking_plain_python_preserves_installed_package(self) -> None:
        with tempfile.TemporaryDirectory(prefix="finder_immutable_") as deployment:
            scripts = Path(deployment) / "scripts"
            scripts.mkdir()
            for name in ("query.py", "search.py"):
                shutil.copyfile(QUERY.parent / name, scripts / name)
            original = {p.name: p.read_bytes() for p in scripts.iterdir()}
            env = {key: value for key, value in os.environ.items()
                   if key not in {"PYTHONPYCACHEPREFIX", "PYTHONDONTWRITEBYTECODE"}}
            process = subprocess.run(
                [sys.executable, str(scripts / "query.py"), "--root", str(self.root), "paths"],
                capture_output=True, text=True, timeout=15, env=env,
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(set(scripts.iterdir()), {scripts / name for name in original})
            self.assertEqual({p.name: p.read_bytes() for p in scripts.iterdir()}, original)

    def test_scopes_and_named_files_cannot_bypass_privacy(self) -> None:
        relative = f"{PRIVATE}/Topics/fictitious.md"
        sentinel = "synthetic_restricted_marker"
        self.write(relative, sentinel)
        self.write(f"{NOTES}/ordinary.md", "ordinary synthetic line")
        flags = ("--config", "--include-raw", "--include-archive")
        self.assertEqual(self.query(*flags, "content", sentinel)["occurrences"], 0)
        for args in [(*flags, "--path", PRIVATE, "content", sentinel), (*flags, "summary", relative)]:
            denied = self.invoke(*args)
            self.assertNotEqual(denied.returncode, 0)
            self.assertNotIn(sentinel, denied.stdout + denied.stderr)

    def test_every_query_obeys_git_ownership_ignores_and_alias_boundaries(self) -> None:
        collection = f"{NOTES}/collection"
        visible = f"{collection}/permitted.md"
        pdf = f"{collection}/diagram.pdf"
        marker = "finder_fixture_marker"
        source = f"---\nfixture: accepted\n---\n\n{marker}\n"
        self.write(visible, source)
        self.write(pdf, "%PDF-1.5\n" + marker)
        ignored = f"{collection}/ignored/note.md"
        tracked_ignored = f"{collection}/ignored/tracked.md"
        self.write(tracked_ignored, source)
        subprocess.run(["git", "-C", str(self.root), "add", "--", tracked_ignored], check=True)
        self.write(".gitignore", f"/{collection}/ignored/\n")
        self.write(ignored, source)

        private = self.write(f"{PRIVATE}/Topics/restricted.md", source)
        alias = f"{collection}/public-looking.md"
        os.link(private, self.root / alias)

        embedded = f"{collection}/embedded/note.md"
        child = self.write(embedded, source).parent
        subprocess.run(["git", "init", "-q", str(child)], check=True)
        linked = f"{collection}/linked/note.md"
        child = self.write(linked, source).parent
        with tempfile.TemporaryDirectory(prefix="finder_external_gitdir_") as external:
            subprocess.run(["git", "init", "-q", "--separate-git-dir", str(Path(external) / "metadata"),
                            str(child)], check=True)
            self.assertTrue((child / ".git").is_file())
            credentials = [
                f"{collection}/production.credentials.json",
                f"{collection}/auth.production.json",
                f"{collection}/client-secrets.yaml",
                f"{collection}/secrets.production.md",
                f"{collection}/customer.pem.backup.json",
                f"{collection}/unknown.unclassified",
            ]
            for path in credentials:
                self.write(path, source)
            excluded = [ignored, tracked_ignored, alias, embedded, linked, *credentials]
            for scope in ((), ("--path", collection)):
                flags = (*scope, "--config", "--include-raw", "--include-archive")
                with self.subTest(scope=scope, mode="paths"):
                    paths = self.query(*flags, "paths", "--glob", f"{collection}/**")
                    self.assertEqual({r["path"] for r in paths["results"]}, {visible, pdf})
                    self.assertEqual(paths["total_items"], 2)
                with self.subTest(scope=scope, mode="content"):
                    content = self.query(*flags, "content", marker, "--show", "paths")
                    self.assertEqual((content["occurrences"], content["matched_files"]), (1, 1))
                    self.assertEqual([r["path"] for r in content["results"]], [visible])
                with self.subTest(scope=scope, mode="metadata"):
                    meta = self.query(*flags, "metadata", "--field", "fixture=accepted")
                    self.assertEqual([r["path"] for r in meta["results"]], [visible])
                with self.subTest(scope=scope, mode="summary"):
                    good = self.query(*flags, "summary", visible)
                    self.assertEqual([r["path"] for r in good["results"]], [visible])
                for path in [*excluded, pdf]:
                    with self.subTest(scope=scope, mode="summary-denial", path=path):
                        denied = self.invoke(*flags, "summary", path)
                        self.assertNotEqual(denied.returncode, 0)
                        self.assertNotIn(marker, denied.stdout + denied.stderr)

    def test_changed_authority_after_inventory_discards_every_result(self) -> None:
        """Switch the fixture immediately after inventory, before any file read."""
        change_before_read = """
import os, runpy, subprocess, sys
from pathlib import Path

query, change, scope = sys.argv[1:4]
program = runpy.run_path(query, run_name="query_race_fixture")
search = program["search"]
original = search.allowed_inventory
def changed(root, *args, **kwargs):
    inventory = original(root, *args, **kwargs)
    target = root / scope / "note.md"
    private = root / "06_Knowledge_Base/Mathematics/Finance/ENGIE/Private/Topics"
    if change == "leaf":
        os.replace(private / "note.md", target)
    elif change == "links":
        os.link(target, private / (target.parent.name + "-second-name.md"))
    elif change == "parent":
        target.parent.rename(target.parent.with_name(target.parent.name + "-original"))
        target.parent.symlink_to(private, target_is_directory=True)
    elif change == "owner":
        subprocess.run(["git", "init", "-q", str(target.parent)], check=True)
    elif change == "ignore":
        with (root / ".gitignore").open("a") as stream:
            stream.write("/" + scope + "/note.md\\n")
    return inventory
search.allowed_inventory = changed
sys.argv = [query, *sys.argv[4:]]
program["main"]()
"""
        marker = "synthetic_replacement_body"
        for change in ("leaf", "links", "parent", "owner", "ignore"):
            for mode in ("content", "paths", "metadata", "summary"):
                with self.subTest(change=change, mode=mode):
                    scope = f"{NOTES}/race-{change}-{mode}"
                    relative = f"{scope}/note.md"
                    self.write(relative, "---\nstatus: active\n---\nOriginal fixture\n")
                    self.write(f"{PRIVATE}/Topics/note.md", marker)
                    extra = [marker] if mode == "content" else [relative] if mode == "summary" else []
                    result = subprocess.run(
                        [sys.executable, "-B", "-c", change_before_read, str(QUERY), change, scope,
                         "--root", str(self.root), "--path", scope, mode, *extra],
                        capture_output=True, text=True, timeout=15,
                    )
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertFalse(result.stdout)
                    self.assertNotIn(marker, result.stderr)


if __name__ == "__main__":
    unittest.main()
