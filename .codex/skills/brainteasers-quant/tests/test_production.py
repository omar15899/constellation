"""Behavioral checks for timing, static slides, preservation and review freshness."""
from __future__ import annotations

import copy
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import shutil
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/production.py"
SPEC = importlib.util.spec_from_file_location("production", SCRIPT)
production = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(production)


def register_fixture_engine(root: Path, engine: Path) -> str:
    """Authorize only the synthetic engine in this test's temporary directory."""
    root, engine = root.resolve(), engine.resolve()
    if not engine.is_relative_to(root):
        raise ValueError("Fixture engine must belong to the temporary test")
    home = root / "codex-fixture"
    home.mkdir(mode=0o700, exist_ok=True)
    files = {}
    for path in sorted(engine.rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            files[path.relative_to(engine).as_posix()] = {
                "sha256": hashlib.sha256(data).hexdigest(), "size": len(data),
                "mode": "100755" if path.stat().st_mode & 0o111 else "100644"}
    policy = home / "brainteasers-engine.json"
    policy.write_text(json.dumps({"schema": 1, "tree": "a" * 40, "files": files}))
    policy.chmod(0o600)
    return str(home)


class ProductionTests(unittest.TestCase):
    def test_cli_scaffolds_in_an_explicit_relocated_course_and_rejects_an_unselected_engine(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "course with spaces/asincronas"
            output.mkdir(parents=True)
            system = root / "trusted engine"
            scripts = system / "scripts"
            scripts.mkdir(parents=True)
            (system / "fixture.sty").write_text(r"\ProvidesPackage{fixture}" + "\n")
            (scripts / "nuevo_video.sh").write_text(
                'set -eu\n'
                'folder="$ASINCRONAS_OUT/sesion-01/video-01-example/presentacion"\n'
                'mkdir -p "$folder"\n'
                'engine=$(cd "$(dirname "$0")/.." && pwd -P)\n'
                'printf "%s\\n" "\\documentclass{beamer}" "\\input{$engine/fixture.sty}" > "$folder/main.tex"\n')
            self.enterContext(patch.dict(os.environ, {"CODEX_HOME": register_fixture_engine(root, system)}))
            plan = root / "plan.json"
            plan.write_text(json.dumps({"session": 1, "videos": [
                {"number": 1, "slug": "example", "title": "Example", "seconds": 1800}]}))
            cmd = [sys.executable, "-I", "-B", str(SCRIPT), "init", str(plan), "--output", str(output)]
            refused = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
            self.assertEqual(refused.returncode, 2)
            self.assertFalse(any(output.iterdir()))
            result = subprocess.run(cmd + ["--system", str(system)], cwd=root,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            created = json.loads(result.stdout)["created"]
            self.assertEqual(created, [str((output / "sesion-01/video-01-example").resolve())])
            generated = (Path(created[0]) / "presentacion/main.tex").read_text()
            self.assertIn(r"\documentclass[handout]{beamer}", generated)
            self.assertIn(r"\input{" + str(system.resolve() / "fixture.sty") + "}", generated)

    def test_static_slides_reject_multiple_pages_for_one_frame(self):
        nav = r"\beamer@framepages {1}{1}\beamer@framepages {2}{2}"
        pages = production.overlay_map(nav, 2)
        self.assertEqual([(p["page"], p["frame"], p["overlays"]) for p in pages], [(1, 1, 1), (2, 2, 1)])
        with self.assertRaisesRegex(production.ProductionError, "one PDF page per frame"):
            production.overlay_map(r"\beamer@framepages {1}{1}\beamer@framepages {2}{4}", 4)
        with self.assertRaisesRegex(production.ProductionError, "mapping"):
            production.overlay_map(r"\beamer@framepages {1}{1}\beamer@framepages {3}{3}", 3)

    @unittest.skipUnless(shutil.which("lualatex"), "LuaLaTeX required for rendered scaffold behavior")
    def test_initializer_turns_template_reveals_into_one_static_page(self):
        import pymupdf

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            plan.write_text(json.dumps({"session": 1, "videos": [
                {"number": 1, "slug": "example", "title": "Example", "seconds": 1800}]}))
            entry = root / "sesion-01/video-01-example/presentacion/main.tex"
            system = root / "system"
            system.mkdir()
            (system / "README.md").write_text("Synthetic engine for a mocked scaffold")
            self.enterContext(patch.dict(os.environ, {"CODEX_HOME": register_fixture_engine(root, system)}))

            real_run = subprocess.run
            def scaffold(argv, *args, **kwargs):
                if Path(argv[0]).name == "git":
                    return real_run(argv, *args, **kwargs)
                output_entry = Path(kwargs["env"]["ASINCRONAS_OUT"]) / entry.relative_to(root)
                output_entry.parent.mkdir(parents=True)
                output_entry.write_text(r"\documentclass[10pt,aspectratio=169]{beamer}" +
                                 r"\begin{document}\begin{frame}Alpha\pause Beta\end{frame}" +
                                 r"\begin{frame}Gamma\end{frame}\end{document}")
                return SimpleNamespace(returncode=0)

            with patch.object(production.subprocess, "run", side_effect=scaffold):
                production.initialize(plan, root, root / "system")
            cache = root / "tex-cache"
            cache.mkdir()
            result = subprocess.run(["lualatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                                    cwd=entry.parent, capture_output=True, text=True, timeout=120,
                                    env={**os.environ, "TEXMFCACHE": str(cache), "TEXMFVAR": str(cache)})
            self.assertEqual(result.returncode, 0, result.stdout[-1500:])
            with pymupdf.open(entry.with_suffix(".pdf")) as pdf:
                self.assertEqual(len(pdf), 2)
                self.assertIn("Alpha", pdf[0].get_text())
                self.assertIn("Beta", pdf[0].get_text())
                self.assertIn("Gamma", pdf[1].get_text())
                self.assertEqual(len(production.overlay_map(entry.with_suffix(".nav").read_text(), len(pdf))), 2)

    def test_timing_rejects_gap_despite_correct_total(self):
        def guion(starts):
            return SimpleNamespace(bloques=[SimpleNamespace(inicio_s=a, fin_s=b, linea=i)
                                            for i, (a, b) in enumerate(starts)],
                                   meta_int=lambda _: 60)
        self.assertEqual(production.timeline(guion([(0, 20), (20, 60)])), (60, []))
        self.assertTrue(production.timeline(guion([(0, 20), (21, 60)]))[1])
        self.assertTrue(production.timeline(guion([(0, 20), (19, 60)]))[1])
        self.assertEqual(production.session_duration([380, 540, 515, 550]), [])
        self.assertTrue(production.session_duration([380]))
        self.assertTrue(production.session_duration([1800, 1800]))

    def review_fixture(self):
        report = {"inventory": {"source.tex": "abc", "presentacion.pdf": "def"},
                  "mechanical_passed": True, "legacy_passed": True,
                  "complete_session": True, "pages": [{"id": "v1/p001"}, {"id": "v1/p002"}],
                  "videos": [{"path": "/tmp/v1"}]}
        report["audit_fingerprint"] = production.fingerprint(report)
        review = {"audit_fingerprint": report["audit_fingerprint"],
                  "pages": {p["id"]: "Test evidence of page geometry and legibility." for p in report["pages"]},
                  "checks": {k: "Test evidence of an actual documented inspection." for k in production.REVIEW_CHECKS},
                  "unresolved": [], "oral_rehearsal": {}}
        return report, review

    def test_missing_page_stale_source_and_stale_pdf_rejected(self):
        report, review = self.review_fixture()
        for name in ("source.tex", "presentacion.pdf"):
            changed = {**report["inventory"], name: "changed"}
            with self.assertRaisesRegex(production.ProductionError, "changed"):
                production.validate_review(report, review, changed)
        del review["pages"]["v1/p002"]
        with self.assertRaisesRegex(production.ProductionError, "Every physical page"):
            production.validate_review(report, review, report["inventory"])

    def test_artifact_review_does_not_invent_oral_rehearsal(self):
        report, review = self.review_fixture()
        self.assertEqual(production.validate_review(report, review, report["inventory"]),
                         {"artifacts_reviewed": True, "recording_ready": False})
        review["oral_rehearsal"] = {"v1": {"confirmed": True, "evidence": "Test fixture simulates an explicitly confirmed rehearsal."}}
        self.assertTrue(production.validate_review(report, review, report["inventory"])["recording_ready"])
        report["legacy_passed"] = False
        report["audit_fingerprint"] = production.fingerprint(report)
        review["audit_fingerprint"] = report["audit_fingerprint"]
        self.assertFalse(production.validate_review(report, review, report["inventory"])["recording_ready"])

    def test_general_identity_review_does_not_replace_palette_or_tikz_inspection(self):
        report, complete = self.review_fixture()
        for dimension in ("palette", "tikz_quality"):
            with self.subTest(dimension=dimension):
                incomplete = copy.deepcopy(complete)
                del incomplete["checks"][dimension]
                with self.assertRaisesRegex(production.ProductionError, dimension):
                    production.validate_review(report, incomplete, report["inventory"])
        self.assertTrue(production.validate_review(report, complete, report["inventory"])["artifacts_reviewed"])

    def test_visual_checks_require_evidence_instead_of_a_success_flag(self):
        report, complete = self.review_fixture()
        for dimension in ("palette", "tikz_quality"):
            for value in (True, "", "Perfecto"):
                with self.subTest(dimension=dimension, value=value):
                    incomplete = copy.deepcopy(complete)
                    incomplete["checks"][dimension] = value
                    with self.assertRaisesRegex(production.ProductionError, dimension):
                        production.validate_review(report, incomplete, report["inventory"])

    def test_documented_visual_defect_still_blocks_a_fully_reviewed_session(self):
        report, review = self.review_fixture()
        for defect in ("Figure 2 uses an unapproved magenta instead of the session 02 palette.",
                       "Figure 3 has a label crossing the arrowhead in the final PDF."):
            with self.subTest(defect=defect):
                review["unresolved"] = [defect]
                with self.assertRaisesRegex(production.ProductionError, "Unresolved"):
                    production.validate_review(report, review, report["inventory"])

    def test_mechanical_failure_or_unresolved_observation_blocks_acceptance(self):
        report, review = self.review_fixture()
        review["unresolved"] = ["A label overlaps the arrowhead."]
        with self.assertRaises(production.ProductionError):
            production.validate_review(report, review, report["inventory"])
        review["unresolved"] = []
        report["mechanical_passed"] = False
        report["audit_fingerprint"] = production.fingerprint(report)
        review["audit_fingerprint"] = report["audit_fingerprint"]
        with self.assertRaises(production.ProductionError):
            production.validate_review(report, review, report["inventory"])

    def test_plan_rejects_collisions_before_creating_anything(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = {"session": 3, "videos": [
                {"number": 1, "slug": "first", "title": "Primero", "seconds": 900},
                {"number": 2, "slug": "second", "title": "Segundo", "seconds": 900}]}
            occupied = root / "sesion-03/video-02-existing"
            occupied.mkdir(parents=True)
            with self.assertRaisesRegex(production.ProductionError, "already exists"):
                production.validate_plan(plan, root)
            self.assertFalse((root / "sesion-03/video-01-first").exists())
            occupied.rmdir()
            for title in ("Una & otra", "A|B", "x\\alpha"):
                bad = copy.deepcopy(plan)
                bad["videos"][1]["title"] = title
                with self.assertRaises(production.ProductionError):
                    production.validate_plan(bad, root)
            self.assertEqual(len(production.validate_plan(plan, root)), 2)

    def test_failed_compile_never_reviews_stale_pdf(self):
        with TemporaryDirectory() as tmp:
            target = Path(tmp) / "video-01-example"
            (target / "presentacion").mkdir(parents=True)
            (target / "presentacion/main.tex").write_text("bad TeX")
            (target / "build").mkdir()
            stale = target / "build/presentacion.pdf"
            stale.write_bytes(b"stale-pdf")
            (target / "build/production").mkdir()
            acceptance = target / "build/production/acceptance.json"
            acceptance.write_text(json.dumps({"artifacts_reviewed": True}))
            parser = SimpleNamespace(parsear_guion=lambda _: (None, ["No guion"]))
            system = Path(tmp) / "system"
            system.mkdir()
            (system / "README.md").write_text("Synthetic engine for a mocked compilation")
            self.enterContext(patch.dict(os.environ, {"CODEX_HOME": register_fixture_engine(Path(tmp), system)}))
            with patch.object(production, "load_parser", return_value=parser), \
                 patch.object(production, "command", return_value=1), \
                 patch.object(production, "inspect_pdf") as inspect:
                _, report = production.audit(target, Path(tmp) / "system")
            inspect.assert_not_called()
            self.assertFalse(report["mechanical_passed"])
            self.assertEqual(report["pages"], [])
            self.assertIsNone(report["seconds"])
            self.assertEqual(stale.read_bytes(), b"stale-pdf")
            self.assertIsNone(report["videos"][0]["phases"]["entrega"])
            self.assertFalse(json.loads(acceptance.read_text())["artifacts_reviewed"])

    def test_real_files_invalidate_review_after_render_change(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "video-01-example"
            (target / "presentacion").mkdir(parents=True)
            (target / "presentacion/main.tex").write_text("source")
            (target / "build/paginas").mkdir(parents=True)
            (target / "build/presentacion.pdf").write_bytes(b"pdf")
            png = target / "build/paginas/pag-1.png"
            png.write_bytes(b"render-one")
            before = production.inventory(target, root / "system", [target])
            png.write_bytes(b"render-two")
            self.assertNotEqual(before, production.inventory(target, root / "system", [target]))
            png.write_bytes(b"render-one")
            (target / "presentacion/new-figure.tex").write_text("new dependency")
            self.assertNotEqual(before, production.inventory(target, root / "system", [target]))

    def test_session_and_video_runs_share_the_same_lock(self):
        with TemporaryDirectory() as tmp:
            session = Path(tmp) / "sesion-01"
            video = session / "video-01-example"
            child_code = """
import importlib.util, sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('production', sys.argv[1])
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with module.scope_locked(Path(sys.argv[2]), [Path(sys.argv[3])]):
    print('acquired', flush=True)
"""
            child = None
            try:
                with production.scope_locked(video, [video]):
                    child = subprocess.Popen([sys.executable, "-I", "-B", "-c", child_code, str(SCRIPT),
                                              str(session), str(video)], stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE, text=True)
                    with self.assertRaises(subprocess.TimeoutExpired):
                        child.communicate(timeout=0.3)
                stdout, stderr = child.communicate(timeout=5)
                self.assertEqual((child.returncode, stdout.strip(), stderr), (0, "acquired", ""))
            finally:
                if child and child.poll() is None:
                    child.kill()
                    child.communicate()


class OutputAliasTests(unittest.TestCase):
    """Run the production entry points against a disposable course and real tools."""

    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.course = self.root / "course"
        self.video = self.course / "asincronas/sesion-01/video-01-example"
        self.output = self.video / "build/production"
        self.output.mkdir(parents=True)
        self.style = self.video / "presentacion/assets/theme/fixture.sty"
        self.style.parent.mkdir(parents=True)
        self.style.write_text(r"\newcommand{\ExampleText}{Loaded nested style}" + "\n")
        (self.video / "presentacion/main.tex").write_text(
            r"\input{assets/theme/fixture.sty}" + "\n")
        (self.video / "guion-teleprompter.md").write_text("fixture script\n")
        self.external = self.root / "external"
        self.external.mkdir()
        self.victim = self.external / "sentinel"
        self.victim.write_bytes(b"external data\n")
        self.system = self.root / "system"
        scripts = self.system / "scripts"
        scripts.mkdir(parents=True)
        hooks = self.system / "hooks"
        hooks.mkdir()
        (hooks / "comun.py").write_text(
            "from types import SimpleNamespace as S\n"
            "def parsear_guion(path):\n"
            "    return S(bloques=[S(inicio_s=0, fin_s=1800, linea=1, slide=1)],"
            " meta_int=lambda key: 1800), []\n")
        # Produce one real, parseable page without depending on a course installation.
        (scripts / "build.sh").write_text(
            'set -eu\n' + shlex.quote(sys.executable) + ' -I -B - "$1" <<\'PY\'\n'
            'from pathlib import Path\nimport json\nimport os\nimport sys\nimport pymupdf\n'
            'build = Path(sys.argv[1]) / "build"\nbuild.mkdir(exist_ok=True)\n'
            'settings = {k: os.environ.get(k, "") for k in '
            '("HOME", "TEXMFCACHE", "TEXMFVAR", "BRAINTEASERS_ROOT")}\n'
            'course = Path(settings["BRAINTEASERS_ROOT"])\n'
            'print(json.dumps({"settings": settings, "video": Path(sys.argv[1]).name, '
            '"session": Path(sys.argv[1]).parent.name, '
            '"course_relative_video": Path(sys.argv[1]).relative_to(course).as_posix(), '
            '"private_cache_dirs": all(Path(settings[k]).parent == course.parent and '
            'Path(settings[k]).stat().st_mode & 0o077 == 0 for k in ("HOME", "TEXMFVAR", "TEXMFCACHE")), '
            '"usable": '
            '{k: bool(v) and Path(v).is_dir() and os.access(v, os.W_OK) '
            'for k, v in settings.items() if k != "BRAINTEASERS_ROOT"}}))\n'
            'source = Path(sys.argv[1]) / "presentacion/main.tex"\n'
            'include = source.read_text().strip().removeprefix(r"\\input{").removesuffix("}")\n'
            'style = source.parent / include\n'
            'caption = style.read_text().strip().rsplit("{", 1)[1].removesuffix("}")\n'
            '(build / "main.fls").write_text(f"INPUT {source}\\nINPUT {style}\\n")\n'
            'with pymupdf.open() as document:\n'
            '    page = document.new_page(width=1600, height=900)\n'
            '    page.insert_text((50, 50), caption)\n'
            '    document.save(build / "presentacion.pdf")\n'
            '(build / "main.nav").write_text(r"\\beamer@framepages {1}{1}")\n'
            '(build / "main.log").write_text("Compiled fixture")\nPY\n')
        (scripts / "render.sh").write_text(
            'set -eu\n' + shlex.quote(sys.executable) + ' -I -B - "$1" <<\'PY\'\n'
            'from pathlib import Path\nimport sys\nimport pymupdf\n'
            'build = Path(sys.argv[1]) / "build"\npages = build / "paginas"\n'
            'pages.mkdir(exist_ok=True)\n'
            'with pymupdf.open(build / "presentacion.pdf") as document:\n'
            '    document[0].get_pixmap().save(pages / "pag-1.png")\nPY\n')
        (scripts / "validar.py").write_text('print("fixture gate passed")\n')
        self.enterContext(patch.dict(os.environ, {"CODEX_HOME": register_fixture_engine(self.root, self.system)}))

    def review_file(self, path):
        review = json.loads(path.with_name("review-template.json").read_text())
        review["pages"] = dict.fromkeys(review["pages"], "The synthetic page renders its single example.")
        review["checks"] = dict.fromkeys(review["checks"], "This test exercises review of a synthetic PDF.")
        review_path = self.root / "review.json"
        review_path.write_text(json.dumps(review))
        return review_path

    def git(self, root, *args):
        result = subprocess.run(
            ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgSign=false",
             "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
             "-C", str(root), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def cli(self, *args):
        return subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *map(str, args)],
                              cwd=self.course, text=True, capture_output=True, timeout=30)

    def assert_owner_rejects_without_writes(self, tree, *args):
        def snapshot():
            state = {}
            for parent, folders, files in os.walk(tree):
                if ".git" in folders:
                    folders.remove(".git")
                for name in folders:
                    state[(Path(parent) / name).relative_to(tree)] = "directory"
                for name in files:
                    if name != ".git":
                        path = Path(parent) / name
                        state[path.relative_to(tree)] = hashlib.sha256(path.read_bytes()).hexdigest()
            return state

        before = snapshot()
        result = self.cli(*args)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertRegex(result.stderr, r"(?i)(owner|nested|repository|git)")
        self.assertEqual(snapshot(), before)

    def assert_only_git_checks_ran(self, runner):
        self.assertTrue(all(Path(call.args[0][0]).name == "git" for call in runner.call_args_list),
                        "The denied operation invoked a program other than Git")

    def test_cli_rejects_a_video_owned_by_another_repository_before_creating_its_build(self):
        self.git(self.course, "init", "-q")
        self.git(self.video, "init", "-q")
        self.output.rmdir()
        self.output.parent.rmdir()
        for target in (self.video, self.video.parent):
            with self.subTest(target=target):
                self.assert_owner_rejects_without_writes(
                    self.video.parent, "audit", target, "--system", self.system)
                self.assertFalse((self.video / "build").exists())

    def test_cli_rejects_a_linked_worktree_inside_selected_teaching_sources(self):
        self.git(self.course, "init", "-q")
        other = self.root / "fixture-engineering-repo"
        other.mkdir()
        self.git(other, "init", "-q")
        self.git(other, "commit", "--allow-empty", "-m", "Fixture baseline")
        worktree = self.video / "presentacion/other-owner"
        self.git(other, "worktree", "add", "--detach", str(worktree), "HEAD")
        self.assertTrue((worktree / ".git").is_file())
        self.output.rmdir()
        self.output.parent.rmdir()
        self.assert_owner_rejects_without_writes(
            self.video.parent, "audit", self.video, "--system", self.system)
        self.assertFalse((self.video / "build").exists())

    def test_cli_acceptance_checks_current_ownership_even_for_previously_reviewed_files(self):
        self.git(self.root, "init", "-q")
        self.git(self.course, "init", "-q")
        original = self.cli("audit", self.video, "--system", self.system)
        self.assertEqual(original.returncode, 0, original.stdout + original.stderr)
        qa = Path(json.loads(original.stdout)["report"])
        review = self.review_file(qa)
        accepted = self.cli("accept", qa, review)
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        self.assertTrue(json.loads(accepted.stdout)["artifacts_reviewed"])
        self.git(self.video, "init", "-q")
        (self.output / ".lock").unlink()
        self.assert_owner_rejects_without_writes(self.video, "accept", qa, review)
        self.assertFalse((self.output / ".lock").exists())

    def test_cli_never_scaffolds_into_a_session_with_its_own_git_owner(self):
        self.git(self.course, "init", "-q")
        session = self.course / "asincronas/sesion-02"
        session.mkdir()
        self.git(session, "init", "-q")
        (session / "README.md").write_text("Independent session owner\n")
        scaffold = self.system / "scripts/nuevo_video.sh"
        scaffold.write_text(
            'set -eu\nfolder="$ASINCRONAS_OUT/sesion-02/video-01-example/presentacion"\n'
            'mkdir -p "$folder"\nprintf "%s\\n" "\\documentclass{beamer}" > "$folder/main.tex"\n')
        register_fixture_engine(self.root, self.system)
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({"session": 2, "videos": [
            {"number": 1, "slug": "example", "title": "Example", "seconds": 1800}]}))
        self.assert_owner_rejects_without_writes(
            session.parent, "init", plan, "--output", session.parent, "--system", self.system)
        self.assertFalse((session / "video-01-example").exists())

    def test_audit_and_actual_acceptance_preserve_external_links(self):
        import pymupdf

        ambient = self.root / "ambient-home"
        ambient.mkdir()
        with patch.dict(os.environ, {"HOME": str(ambient)}):
            for key in ("TEXMFCACHE", "TEXMFVAR", "BRAINTEASERS_ROOT"):
                os.environ.pop(key, None)
            path, report = production.audit(self.video, self.system)
        self.assertTrue(report["mechanical_passed"], report["errors"])
        self.assertTrue(report["legacy_passed"], report["videos"])
        self.assertEqual(len(report["pages"]), 1)
        seen = json.loads((self.output / "build.log").read_text())
        self.assertEqual((seen["session"], seen["video"]), ("sesion-01", "video-01-example"))
        self.assertTrue(all(seen["usable"].values()), seen)
        self.assertNotEqual(Path(seen["settings"]["HOME"]), ambient)
        self.assertEqual(seen["course_relative_video"], "asincronas/sesion-01/video-01-example")
        self.assertTrue(seen["private_cache_dirs"])
        self.assertFalse(any(ambient.iterdir()))
        with pymupdf.open(self.video / "build/presentacion.pdf") as document:
            self.assertIn("Loaded nested style", document[0].get_text())
        self.assertIn(f"INPUT {self.style}", (self.video / "build/main.fls").read_text())
        self.assertIn(str(self.style), report["inventory"])
        review_path = self.review_file(path)
        self.assertTrue(production.accept(path, review_path)["artifacts_reviewed"])
        acceptance = path.with_name("acceptance.json")
        acceptance.unlink()
        os.link(self.victim, acceptance)
        with self.assertRaises((production.ProductionError, OSError)):
            production.accept(path, review_path)
        self.assertEqual(self.victim.read_bytes(), b"external data\n")

    def test_an_interrupted_new_audit_invalidates_previous_review_even_with_the_old_files(self):
        qa, _ = production.audit(self.video, self.system)
        review = self.review_file(qa)
        self.assertTrue(production.accept(qa, review)["artifacts_reviewed"])
        pdf = self.video / "build/presentacion.pdf"
        previous_pdf = pdf.read_bytes()
        previous_qa = qa.read_bytes()
        with patch.object(production, "_compile_copy", side_effect=RuntimeError("interrupted build")):
            with self.assertRaisesRegex(RuntimeError, "interrupted build"):
                production.audit(self.video, self.system)
        self.assertEqual(pdf.read_bytes(), previous_pdf)
        # Restoring a known-good old report cannot accept it for this later attempt.
        qa.write_bytes(previous_qa)
        with self.assertRaises(production.ProductionError):
            production.accept(qa, review)
        self.assertFalse(json.loads(qa.with_name("acceptance.json").read_text())["artifacts_reviewed"])

    def test_modified_parser_and_unregistered_scaffolder_are_rejected_before_execution(self):
        marker = self.root / "executed"
        parser = self.system / "hooks/comun.py"
        approved = parser.read_bytes()
        parser.write_text("from pathlib import Path\n"
                          f"Path({str(marker)!r}).write_text('parser ran')\n")
        with self.assertRaises((ValueError, production.ProductionError)):
            production.audit(self.video, self.system)
        self.assertFalse(marker.exists())
        self.assertFalse((self.output / "acceptance.json").exists())

        parser.write_bytes(approved)
        script = self.system / "scripts/nuevo_video.sh"
        script.write_text("printf 'scaffolder ran' > " + shlex.quote(str(marker)) + "\n")
        output = self.root / "new-course"
        output.mkdir()
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({"session": 1, "videos": [
            {"number": 1, "slug": "example", "title": "Example", "seconds": 1800}]}))
        with self.assertRaises((ValueError, production.ProductionError)):
            production.initialize(plan, output, self.system)
        self.assertFalse(marker.exists())
        self.assertFalse(any(output.iterdir()))

    def test_audit_rejects_linked_temporary_lock_log_and_pdf_before_tools(self):
        cases = (("production/acceptance.json.tmp", "symlink"),
                 ("production/.lock", "hardlink"),
                 ("production/build.log", "hardlink"),
                 ("presentacion.pdf", "symlink"))
        for index, (name, kind) in enumerate(cases):
            with self.subTest(name=name):
                target = self.root / f"case-{index}" / self.video.name
                shutil.copytree(self.video, target)
                alias = target / "build" / name
                if kind == "symlink":
                    alias.symlink_to(self.victim)
                else:
                    os.link(self.victim, alias)
                try:
                    with patch.object(production, "load_parser", wraps=production.load_parser) as parser, \
                         patch.object(production.subprocess, "run", wraps=subprocess.run) as runner:
                        with self.assertRaises((production.ProductionError, OSError)):
                            production.audit(target, self.system)
                        self.assertEqual(parser.call_count, 0)
                        self.assert_only_git_checks_ran(runner)
                    self.assertEqual(self.victim.read_bytes(), b"external data\n")
                finally:
                    alias.unlink(missing_ok=True)

    def test_audit_rejects_a_link_in_the_parent_of_the_requested_video(self):
        parent = self.root / "alias-course"
        parent.symlink_to(self.video.parent, target_is_directory=True)
        with patch.object(production.subprocess, "run", wraps=subprocess.run) as runner:
            with self.assertRaises((production.ProductionError, OSError)):
                production.audit(parent / self.video.name, self.system)
            self.assert_only_git_checks_ran(runner)
        self.assertFalse((self.output / "acceptance.json").exists())

    def test_replacing_the_output_parent_during_compile_cannot_redirect_publication(self):
        real_run = subprocess.run
        swapped = False

        def replace_parent(argv, *args, **kwargs):
            nonlocal swapped
            if not swapped and any(str(item).endswith("/build.sh") for item in argv):
                swapped = True
                build = self.video / "build"
                build.rename(self.root / "original-build")
                build.symlink_to(self.external, target_is_directory=True)
            return real_run(argv, *args, **kwargs)

        with patch.object(production.subprocess, "run", side_effect=replace_parent):
            with self.assertRaises((production.ProductionError, OSError)):
                production.audit(self.video, self.system)
        self.assertTrue(swapped)
        self.assertEqual(list(self.external.iterdir()), [self.victim])
        self.assertEqual(self.victim.read_bytes(), b"external data\n")

    def test_init_rejects_a_linked_session_and_does_not_run_scaffolding(self):
        output = self.root / "new-course"
        output.mkdir()
        (output / "sesion-01").symlink_to(self.external, target_is_directory=True)
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({"session": 1, "videos": [
            {"number": 1, "slug": "example", "title": "Example", "seconds": 1800}]}))
        with patch.object(production.subprocess, "run", wraps=subprocess.run) as runner:
            with self.assertRaises((production.ProductionError, OSError)):
                production.initialize(plan, output, self.system)
            self.assert_only_git_checks_ran(runner)
        self.assertEqual(list(self.external.iterdir()), [self.victim])

    def test_init_rejects_a_generated_hardlink_before_modifying_a_scaffold(self):
        output = self.root / "new-course"
        output.mkdir()
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({"session": 1, "videos": [
            {"number": 1, "slug": "example", "title": "Example", "seconds": 1800}]}))
        source = b"\\documentclass{beamer}\n"
        self.victim.write_bytes(source)
        (self.system / "scripts/nuevo_video.sh").write_text(
            'set -eu\n'
            'dir="$ASINCRONAS_OUT/sesion-01/video-01-example/presentacion"\n'
            'mkdir -p "$dir"\n'
            'ln ' + shlex.quote(str(self.victim)) + ' "$dir/main.tex"\n')
        register_fixture_engine(self.root, self.system)
        with self.assertRaises((production.ProductionError, OSError)):
            production.initialize(plan, output, self.system)
        self.assertEqual(self.victim.read_bytes(), source)
        self.assertFalse((output / "sesion-01/video-01-example").exists())

    def test_retry_after_second_video_promotion_fails_preserves_complete_work_and_user_edits(self):
        output = self.root / "course-output"
        session = output / "sesion-01"
        session.mkdir(parents=True)
        readme = session / "README.md"
        readme.write_bytes(b"My existing session notes\n")
        (self.system / "scripts/nuevo_video.sh").write_text(
            'set -eu\n'
            'session=$(printf "%02d" "$1")\nnumber=$(printf "%02d" "$2")\n'
            'folder="$ASINCRONAS_OUT/sesion-$session/video-$number-$3"\n'
            'mkdir -p "$folder/presentacion/frames"\n'
            'printf "%s\\n" "\\documentclass{beamer}" > "$folder/presentacion/main.tex"\n'
            'printf "%s\\n" "$5" > "$folder/presentacion/frames/topic.tex"\n'
            'printf "Generated session\\n" > "$ASINCRONAS_OUT/sesion-$session/README.md"\n')
        register_fixture_engine(self.root, self.system)
        plan = self.root / "batch.json"
        plan.write_text(json.dumps({"session": 1, "videos": [
            {"number": 1, "slug": "first", "title": "First topic", "seconds": 900},
            {"number": 2, "slug": "second", "title": "Second topic", "seconds": 900}]}))

        first, second = session / "video-01-first", session / "video-02-second"
        platform = production.platform()
        real_promote = platform.promote_directory_at

        def promote_or_fail(src_fd, src_name, dest_fd, dest_name):
            if dest_name == second.name:
                raise OSError(errno.ENOSPC, "simulated full disk")
            return real_promote(src_fd, src_name, dest_fd, dest_name)

        with patch.object(platform, "promote_directory_at", side_effect=promote_or_fail):
            with self.assertRaisesRegex(production.ProductionError, "simulated full disk"):
                production.initialize(plan, output, self.system)
        self.assertEqual(sorted(session.glob("video-*")), [first])
        self.assertIn(r"\documentclass[handout]{beamer}", (first / "presentacion/main.tex").read_text())
        topic = first / "presentacion/frames/topic.tex"
        self.assertEqual(topic.read_bytes(), b"First topic\n")
        original_inode = topic.stat().st_ino
        self.assertEqual(readme.read_bytes(), b"My existing session notes\n")

        self.assertEqual(production.initialize(plan, output, self.system), [str(first), str(second)])
        self.assertEqual(topic.stat().st_ino, original_inode)
        self.assertEqual((second / "presentacion/frames/topic.tex").read_bytes(), b"Second topic\n")
        self.assertEqual(readme.read_bytes(), b"My existing session notes\n")
        topic.write_bytes(b"My revised first topic\n")
        with self.assertRaises(production.ProductionError):
            production.initialize(plan, output, self.system)
        self.assertEqual(topic.read_bytes(), b"My revised first topic\n")
        self.assertEqual(readme.read_bytes(), b"My existing session notes\n")


if __name__ == "__main__":
    unittest.main()
