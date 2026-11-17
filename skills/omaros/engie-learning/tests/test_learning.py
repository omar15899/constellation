"""Behavioral acceptance of private learning capture on fictitious Git vaults."""
from __future__ import annotations

import copy
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "learning.py"
PACKAGE_ROOT = SCRIPT.parents[4]
sys.path.insert(0, str(PACKAGE_ROOT))
from resources.vault import check_profile_binding, vault_binding

SPEC = importlib.util.spec_from_file_location("engie_learning_engine", SCRIPT)
learning = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(learning)


def mark_fixture_vault(root: Path) -> None:
    marker = root / learning.VAULT_MARKER
    marker.parent.mkdir(parents=True)
    marker.write_text("# Mapa ficticio de arquitectura\n")


def enroll(home: Path, root: Path) -> None:
    """Create an isolated project profile for a synthetic vault."""
    home.mkdir(mode=0o700)
    binding = vault_binding(root.resolve())
    profile = {"projects": [{"id": "omaros", "root": binding["root"],
                             "filesystem_identity": {k: binding[k] for k in ("owner", "git_dir")}}]}
    (home / "projects.json").write_text(json.dumps(profile))


class LearningCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="omaros_fictitious_learning_")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "A"
        self.root.mkdir()
        self.device_home = self.base / "device-home"
        user_home = self.base / "user-home"
        user_home.mkdir()
        # Git exports repository overrides when running hooks. Synthetic fixture
        # creation must never inherit those overrides from the test process.
        environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        environment.update(HOME=str(user_home), CODEX_HOME=str(self.device_home))
        self.enterContext(patch.dict(os.environ, environment, clear=True))
        self.git("init", "-q")
        (self.root / ".gitignore").write_text("/" + learning.BASE + "/\n")
        self.engie = self.root / "06_Knowledge_Base/Mathematics/Finance/ENGIE"
        self.engie.mkdir(parents=True)
        (self.engie / "README.md").write_text("# Índice ficticio\n")
        self.antecedent = "06_Knowledge_Base/Mathematics/Finance/fictitious_hedging.md"
        (self.root / self.antecedent).write_text("# Antecedente ficticio de hedging\n")
        mark_fixture_vault(self.root)
        enroll(self.device_home, self.root)
        self.enterContext(patch.object(learning, "check_vault_registration",
            side_effect=lambda home, name, require_bound: check_profile_binding(home / "projects.json", name)))
        self.store = learning.Store(self.root, device_home=self.device_home)

    def alternate_store(self, root: Path) -> learning.Store:
        home = self.base / ("device-" + root.name)
        enroll(home, root)
        return learning.Store(root, device_home=home)

    def skill_caller(self) -> Path:
        """Run the migrated entry in a synthetic central checkout and profile."""
        package = self.device_home / "Constellation"
        script = package / "skills/core/engie-learning/scripts/learning.py"
        caller = self.device_home / "test-skill-caller.py"
        if not script.exists():
            script.parent.mkdir(parents=True)
            shutil.copyfile(SCRIPT, script)
            (package / "resources").mkdir()
            for name in ("__init__.py", "vault.py"):
                shutil.copyfile(PACKAGE_ROOT / "resources" / name, package / "resources" / name)
            (package / "profiles").mkdir()
            shutil.copyfile(self.device_home / "projects.json", package / "profiles/projects.json")
            caller.write_text(
                "import runpy, sys\n"
                f"sys.argv[0] = {str(script)!r}\n"
                f"runpy.run_path({str(script)!r}, run_name='__main__')\n"
            )
        return caller

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True, text=True)

    def capture(self, *, topics: list[str] | None = None, date: str | None = "2026-10-26", hour: int = 10) -> dict:
        titles = {"onboarding_pricer": "Onboarding ficticio de un pricer", "hedging_pricer": "Preparación ficticia del hedging"}
        return {
            "event_id": str(uuid.uuid4()),
            "learned_on": date,
            "captured_at": f"2026-10-26T{hour:02d}:00:00+00:00",
            "summary": "EJEMPLO FICTICIO: revisión del alta y la cobertura de un pricer de prueba.",
            "topics": [{
                "slug": slug,
                "title": titles.get(slug, "Concepto ficticio " + slug),
                "body": "EJEMPLO FICTICIO. La configuración simulada se comprueba en el entorno de pruebas.",
                "provenance": [{"kind": "user", "reference": "Relato ficticio aportado expresamente para esta prueba"}],
                "antecedents": [self.antecedent] if "hedging" in slug else [],
                "conditions": ["Sólo para una mesa y un pricer ficticios"],
                "examples": ["Identificador ficticio PRICER-TEST-001"],
                "questions": [],
                "contradictions": [],
            } for slug in (topics or ["onboarding_pricer"])],
        }

    def save(self, payload: dict) -> dict:
        return self.store.apply(self.store.prepare(payload))

    def topic_path(self, slug: str = "onboarding_pricer") -> Path:
        return self.root / learning.BASE / "Topics" / (slug + ".md")

    def daily_path(self, date: str | None = "2026-10-26") -> Path:
        suffix = f"Daily/{date[:4]}/{date}.md" if date else "Daily/unknown.md"
        return self.root / learning.BASE / suffix

    def assert_code(self, code: str, function, *args, **kwargs) -> learning.CaptureError:
        with self.assertRaises(learning.CaptureError) as result:
            function(*args, **kwargs)
        self.assertEqual(code, result.exception.code)
        return result.exception

    def test_bound_skill_caller_finds_owner_but_rejects_other_project(self) -> None:
        completed = subprocess.run([sys.executable, "-I", "-B", str(self.skill_caller()), "status"], cwd=self.engie,
                                   capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(completed.stdout)["status"], "ready")
        (self.root / learning.VAULT_MARKER).unlink()
        for args in ([], ["--root", str(self.root)]):
            result = subprocess.run([sys.executable, "-I", "-B", str(self.skill_caller()), *args, "status"], cwd=self.engie,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["code"], "wrong_project")
        self.assertFalse(self.store.state.exists())

    def test_private_capture_uses_installed_device_enrollment(self) -> None:
        """A matching marker, ignore policy and a forged CODEX_HOME cannot select another vault."""
        other = self.base / "B"
        shutil.copytree(self.root, other)
        other_home = self.base / "other-device"
        enroll(other_home, other)
        capture = self.capture()
        plan = self.store.prepare(capture)
        with self.assertRaises(learning.CaptureError):
            learning.Store(other, device_home=self.device_home)
        script = str(self.skill_caller())
        for args, payload in [(["prepare"], capture), (["--root", str(other), "apply"], plan),
                              (["query"], None), (["status"], None), (["recover"], None)]:
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, "-I", "-B", script, *args], cwd=other,
                                        env={**os.environ, "CODEX_HOME": str(other_home)},
                                        input=json.dumps(payload) if payload is not None else None,
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(json.loads(result.stdout)["persisted"])
        for root in (other, self.root):
            self.assertFalse((root / learning.BASE).exists())
            self.assertFalse((root / ".git/omaros-learning").exists())
        self.assertEqual(self.store.apply(plan)["status"], "applied")

    def test_cli_ignores_guest_imports_and_codex_home_root_selection(self) -> None:
        sentinel = self.base / "unexpected-guest-import"
        guest = self.base / "guest"
        guest.mkdir()
        for name in ("yaml.py", "argparse.py", "resources.py"):
            (guest / name).write_text(f"from pathlib import Path\nPath({str(sentinel)!r}).touch()\n")
        result = subprocess.run([sys.executable, "-I", "-B", str(self.skill_caller()),
                                 "--root", str(self.root), "status"], cwd=guest,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(sentinel.exists())

    def check_replaced_owner(self, *, replace_gitdir: bool) -> None:
        capture = self.capture()
        plan = self.store.prepare(capture)
        target = self.root / ".git" if replace_gitdir else self.root
        saved = self.base / "original-owner"
        target.rename(saved)
        shutil.copytree(saved, target)
        for operation in (self.store.status, lambda: self.store.prepare(capture),
                          lambda: self.store.apply(plan), self.store.query, self.store.recover,
                          lambda: learning.Store(self.root, device_home=self.device_home)):
            with self.subTest(operation=operation):
                with self.assertRaises(learning.CaptureError):
                    operation()
        self.assertFalse((self.root / learning.BASE).exists())
        self.assertFalse((self.root / ".git/omaros-learning").exists())
        self.assertFalse((saved / ("omaros-learning" if replace_gitdir else ".git/omaros-learning")).exists())

    def test_replaced_git_directory_invalidates_live_store(self) -> None:
        self.check_replaced_owner(replace_gitdir=True)

    def test_replaced_vault_root_invalidates_live_store(self) -> None:
        self.check_replaced_owner(replace_gitdir=False)

    def test_root_replacement_between_journal_and_write_preserves_recovery(self) -> None:
        plan = self.store.prepare(self.capture())
        replacement = self.base / "stand-in"
        original = self.base / "original"
        shutil.copytree(self.root, replacement)
        write_change = self.store._replace

        def replace_owner_before_write(change, observed):
            self.root.rename(original)
            replacement.rename(self.root)
            return write_change(change, observed)

        with patch.object(self.store, "_replace", side_effect=replace_owner_before_write):
            with self.assertRaises(learning.CaptureError):
                self.store.apply(plan)
        self.assertFalse((self.root / learning.BASE).exists())
        self.assertFalse((self.root / ".git/omaros-learning").exists())
        self.root.rename(replacement)
        original.rename(self.root)
        self.assertEqual(self.store.status()["status"], "pending")
        self.assertEqual(self.store.recover()["status"], "applied")
        self.assertTrue(self.topic_path().is_file())

    def test_private_query_rejects_linked_external_inode(self) -> None:
        external = self.base / "external.md"
        external.write_text("---\ntitle: FICTITIOUS OUTSIDE NOTE\n---\n")
        topic = self.topic_path()
        topic.parent.mkdir(parents=True)
        for link in ("hard", "symbolic"):
            with self.subTest(link=link):
                if link == "hard":
                    os.link(external, topic)
                else:
                    topic.symlink_to(external)
                try:
                    with self.assertRaises(learning.CaptureError):
                        self.store.query()
                finally:
                    topic.unlink()
        self.assertEqual(external.read_text(), "---\ntitle: FICTITIOUS OUTSIDE NOTE\n---\n")
        self.assertFalse(self.store.state.exists())

    def test_fictitious_onboarding_and_hedging_share_a_descriptive_day(self) -> None:
        first = self.capture()
        second = self.capture(topics=["hedging_pricer"], hour=12)
        self.assertEqual("applied", self.save(first)["status"])
        self.assertEqual("applied", self.save(second)["status"])
        day = self.daily_path().read_text()
        data = learning.metadata(day)
        self.assertIn("Onboarding ficticio", data["title"])
        self.assertIn("hedging", data["title"])
        self.assertEqual(1, len(list(self.daily_path().parent.glob("*.md"))))
        self.assertEqual(2, day.count("<!-- LEARNING:BEGIN"))
        self.assertNotIn(first["topics"][0]["body"], day)
        self.assertNotIn(second["topics"][0]["body"], day)
        self.assertIn("PRICER-TEST-001", self.topic_path().read_text())
        self.assertIn(self.antecedent, self.topic_path("hedging_pricer").read_text())
        self.assertFalse(data["publish"])
        self.assertEqual("restricted", data["classification"])
        self.assertTrue(data["latex_pending"])

    def test_multitopic_event_and_replay_after_later_topic_changes(self) -> None:
        first = self.capture(topics=["onboarding_pricer", "hedging_pricer"])
        self.save(first)
        later = self.capture(topics=["hedging_pricer"], hour=16)
        later["topics"][0]["title"] = "Hedging ficticio con límites de volumen"
        later["topics"][0]["body"] += " Se comprueba además un límite ficticio de volumen."
        self.save(later)
        before = {p: p.read_bytes() for p in (self.topic_path(), self.topic_path("hedging_pricer"), self.daily_path())}
        replay = self.store.prepare(first)
        self.assertEqual("already_applied", replay["status"])
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.assertEqual(2, self.topic_path("hedging_pricer").read_text().count("<!-- LEARNING:BEGIN"))
        self.assertIn("límites de volumen", learning.metadata(self.daily_path().read_text())["title"])
        self.assertFalse(list((self.root / learning.BASE).rglob("*.swap")))

    def test_same_concept_different_day_is_another_learning_event(self) -> None:
        first = self.capture()
        second = self.capture(date="2026-10-27")
        second["captured_at"] = "2026-10-27T10:00:00+00:00"
        second["topics"][0]["body"] = "EJEMPLO FICTICIO. Revisión del procedimiento ya integrado, sin nueva afirmación."
        self.save(first)
        self.save(second)
        self.assertTrue(self.daily_path("2026-10-26").exists())
        self.assertTrue(self.daily_path("2026-10-27").exists())
        self.assertEqual(1, len(list(self.topic_path().parent.glob("*.md"))))
        self.assertEqual(2, self.topic_path().read_text().count("<!-- LEARNING:BEGIN"))

    def test_historical_and_unknown_dates_never_come_from_mtime(self) -> None:
        past = self.capture(date="2025-02-03")
        unknown = self.capture(topics=["hedging_pricer"], date=None)
        self.save(past)
        self.save(unknown)
        past_data = learning.metadata(self.daily_path("2025-02-03").read_text())
        self.assertEqual("2025-02-03", str(past_data["learned_on"]))
        self.assertEqual("2026-10-26T10:00:00+00:00", past_data["captured_at"])
        self.assertEqual(dt.datetime.now(dt.timezone.utc).date().isoformat(), str(past_data["created"]))
        self.assertIsNone(learning.metadata(self.daily_path(None).read_text())["learned_on"])
        os.utime(self.daily_path(None), (1, 1))
        self.assertEqual(1, len(self.store.query(date="unknown")["results"]))
        self.assertFalse(self.store.query(date="1970-01-01")["results"])

    def test_questions_contradiction_and_distinct_provenance_remain_visible(self) -> None:
        capture = self.capture(topics=["hedging_pricer"])
        topic = capture["topics"][0]
        topic["questions"] = ["¿Quién valida el paso ficticio de aprobación?"]
        topic["contradictions"] = ["El relato ficticio indica T+1, el antecedente ficticio indica T+2; sin resolver."]
        topic["provenance"] += [
            {"kind": "source", "reference": "Nota de pruebas ficticia, versión 1"},
            {"kind": "ai_proposal", "reference": "Propuesta ficticia de comprobar un control adicional"},
        ]
        self.save(capture)
        body = self.topic_path("hedging_pricer").read_text()
        day = self.daily_path().read_text()
        for value in topic["questions"] + topic["contradictions"]:
            self.assertIn(value, body)
            self.assertIn(value, day)
        for label in ("Aportado por Omar", "Respaldado por fuente", "Propuesta de IA pendiente de validar"):
            self.assertIn(label, body)

    def test_explicit_correction_keeps_prior_text_and_manual_additions(self) -> None:
        first = self.capture()
        self.save(first)
        path = self.topic_path()
        original = path.read_text()
        original_block = learning.block(original, first["event_id"])
        manual = "\n## Comentario manual\nConservar esta observación ficticia y [[nota_ficticia#ancla|su enlace]].\n"
        path.write_text(original + manual)
        correction = self.capture(hour=18)
        correction["correction_of"] = first["event_id"]
        correction["topics"][0]["title"] = "Onboarding ficticio: aprobación antes de simulación"
        correction["topics"][0]["body"] = "EJEMPLO FICTICIO. Corrección: la aprobación simulada precede a la simulación."
        self.save(correction)
        current = path.read_text()
        self.assertIn(original_block, current)
        self.assertIn(manual, current)
        self.assertIn("Corrección explícita del evento", current)
        self.assertIn(first["event_id"], current)
        self.assertIn("<!-- LEARNING-CURRENT: " + correction["event_id"], current)
        self.assertEqual(first["captured_at"], learning.metadata(current)["captured_at"])
        self.assertEqual("already_applied", self.store.prepare(first)["status"])

    def test_changed_same_event_requires_explicit_correction(self) -> None:
        capture = self.capture()
        self.save(capture)
        changed = copy.deepcopy(capture)
        changed["summary"] += " Cambio ficticio."
        self.assert_code("event_conflict", self.store.prepare, changed)
        orphan = self.capture()
        orphan["correction_of"] = str(uuid.uuid4())
        self.assert_code("unknown_event", self.store.prepare, orphan)

    def test_prepare_is_read_only_and_conflict_preserves_manual_edit(self) -> None:
        first = self.capture()
        self.save(first)
        second = self.capture(hour=15)
        plan = self.store.prepare(second)
        path = self.topic_path()
        manual = path.read_bytes() + b"\nComentario manual ficticio antes de aplicar.\n"
        path.write_bytes(manual)
        self.assert_code("edit_conflict", self.store.apply, plan)
        self.assertEqual(manual, path.read_bytes())
        self.assertEqual("ready", self.store.status()["status"])
        self.assertEqual("applied", self.save(second)["status"])
        self.assertIn(b"Comentario manual ficticio", path.read_bytes())

    def test_status_and_prepare_do_not_create_private_state(self) -> None:
        self.assertEqual("ready", self.store.status()["status"])
        self.assertEqual("prepared", self.store.prepare(self.capture())["status"])
        self.assertFalse(self.store.state.exists())
        self.assertFalse((self.root / learning.BASE).exists())

    def test_mid_transaction_failure_is_observable_and_recoverable(self) -> None:
        capture = self.capture(topics=["onboarding_pricer", "hedging_pricer"])
        plan = self.store.prepare(capture)
        replace = self.store._replace
        calls = 0

        def fail_second(change, observed):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("Fallo ficticio de disco durante la segunda escritura")
            return replace(change, observed)

        with patch.object(self.store, "_replace", side_effect=fail_second):
            with self.assertRaises((OSError, learning.CaptureError)):
                self.store.apply(plan)
        self.assertEqual("pending", self.store.status()["status"])
        self.assertFalse(self.store.receipt(capture["event_id"]))
        partial_query = self.store.query()
        self.assertEqual("pending", partial_query["status"])
        self.assertTrue(partial_query["partial"])
        self.assertEqual(capture["event_id"], partial_query["pending_event"])
        self.assertEqual("applied", self.store.recover()["status"])
        self.assertEqual("ready", self.store.status()["status"])
        self.assertEqual("already_applied", self.store.prepare(capture)["status"])
        self.assertEqual(1, self.daily_path().read_text().count("<!-- LEARNING:BEGIN"))
        self.assertEqual(1, self.topic_path().read_text().count("<!-- LEARNING:BEGIN"))

    def test_recovery_conflict_does_not_replace_an_external_edit(self) -> None:
        capture = self.capture()
        plan = self.store.prepare(capture)
        with patch.object(self.store, "_replace", side_effect=OSError("Fallo ficticio antes de escribir")):
            with self.assertRaises((OSError, learning.CaptureError)):
                self.store.apply(plan)
        path = self.topic_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        manual = "# Creación manual ficticia durante la recuperación\n"
        path.write_text(manual)
        self.assert_code("recovery_conflict", self.store.recover)
        self.assertEqual(manual, path.read_text())
        self.assertEqual("pending", self.store.status()["status"])
        abandoned = self.store.recover(abandon=True)
        self.assertEqual("abandoned_partial", abandoned["status"])
        self.assertFalse(abandoned["persisted"])
        self.assertTrue(Path(abandoned["recovery"]).exists())
        self.assertEqual(manual, path.read_text())

    def test_interruption_after_candidate_fsync_can_resume_without_losing_edits(self) -> None:
        self.save(self.capture())
        next_capture = self.capture(hour=14)
        before = self.topic_path().read_bytes()
        plan = self.store.prepare(next_capture)
        with patch.object(learning, "exchange", side_effect=OSError("Interrupción ficticia antes del intercambio")):
            with self.assertRaises((OSError, learning.CaptureError)):
                self.store.apply(plan)
        self.assertEqual(before, self.topic_path().read_bytes())
        self.assertEqual("pending", self.store.status()["status"])
        self.assertEqual("applied", self.store.recover()["status"])
        self.assertEqual("already_applied", self.store.prepare(next_capture)["status"])
        self.assertFalse(list(self.topic_path().parent.glob(".*.swap")))

    def test_recovery_recognises_only_journaled_link_pair_after_interruption(self) -> None:
        capture = self.capture()
        plan = self.store.prepare(capture)
        link = os.link

        def interrupt_after_link(*args, **kwargs):
            link(*args, **kwargs)
            raise OSError("Synthetic interruption after publishing the candidate link")

        with patch.object(learning.os, "link", side_effect=interrupt_after_link):
            with self.assertRaises((OSError, learning.CaptureError)):
                self.store.apply(plan)
        pending = self.store.json_read("omaros-learning/pending.json")
        change = pending["changes"][0]
        destination = self.root / change["path"]
        candidate = destination.with_name(change["candidate"])
        self.assertTrue(os.path.samefile(candidate, destination))
        self.assertEqual(destination.stat().st_nlink, 2)
        outside = self.base / "external-alias.md"
        os.link(destination, outside)
        expected = outside.read_bytes()
        with self.assertRaises(learning.CaptureError):
            self.store.recover()
        self.assertEqual(outside.read_bytes(), expected)
        self.assertEqual(destination.stat().st_nlink, 3)
        outside.unlink()
        self.assertEqual(self.store.recover()["status"], "applied")
        self.assertFalse(candidate.exists())
        self.assertEqual(destination.stat().st_nlink, 1)
        self.assertEqual(self.store.prepare(capture)["status"], "already_applied")

    def test_cooperating_writers_use_a_nonblocking_shared_lock(self) -> None:
        plan = self.store.prepare(self.capture())
        other = learning.Store(self.root, device_home=self.device_home)
        with self.store.lock():
            self.assert_code("busy", other.apply, plan)
        self.assertEqual("ready", self.store.status()["status"])
        self.assertEqual("applied", other.apply(plan)["status"])

    def test_markdown_event_identity_survives_missing_receipts(self) -> None:
        first = self.capture()
        self.save(first)
        later = self.capture(hour=17)
        later["topics"][0]["title"] = "Onboarding ficticio ampliado y revisado"
        later["topics"][0]["body"] += " Ampliación ficticia posterior."
        self.save(later)
        (self.store.state / "receipts" / (first["event_id"] + ".json")).unlink()
        topic_before, daily_before = self.topic_path().read_bytes(), self.daily_path().read_bytes()
        replay = self.store.prepare(first)
        self.assertEqual("already_applied", replay["status"])
        self.assertEqual(topic_before, self.topic_path().read_bytes())
        self.assertEqual(daily_before, self.daily_path().read_bytes())
        self.assertIn("<!-- LEARNING-CURRENT: " + later["event_id"], self.topic_path().read_text())
        changes = []
        summary = copy.deepcopy(first)
        summary["summary"] += " Reintento ficticio alterado."
        changes.append(summary)
        body = copy.deepcopy(first)
        body["topics"][0]["body"] += " Otro contenido ficticio."
        changes.append(body)
        date = copy.deepcopy(first)
        date["learned_on"] = "2026-10-25"
        changes.append(date)
        slug = copy.deepcopy(first)
        slug["topics"][0]["slug"] = "other_fictitious_topic"
        changes.append(slug)
        for changed in changes:
            with self.subTest(changed=changed["learned_on"], slug=changed["topics"][0]["slug"]):
                self.assert_code("event_conflict", self.store.prepare, changed)

    def test_file_dates_describe_creation_even_for_a_historical_capture(self) -> None:
        capture = self.capture(date="2020-02-03")
        capture["captured_at"] = "2021-04-05T11:30:00+00:00"
        self.save(capture)
        data = learning.metadata(self.daily_path("2020-02-03").read_text())
        self.assertEqual("2021-04-05T11:30:00+00:00", data["captured_at"])
        self.assertEqual("2020-02-03", str(data["learned_on"]))
        today_utc = dt.datetime.now(dt.timezone.utc).date().isoformat()
        self.assertEqual(today_utc, str(data["created"]))
        self.assertEqual(today_utc, str(data["updated"]))

    def test_external_editor_race_preserves_displaced_manual_bytes(self) -> None:
        self.save(self.capture())
        next_capture = self.capture(hour=13)
        plan = self.store.prepare(next_capture)
        exchange = learning.exchange
        manual = b"Edicion concurrente ficticia entre comprobacion e intercambio.\n"
        raced = False

        def concurrent_exchange(fd, candidate, target):
            nonlocal raced
            if not raced:
                raced = True
                handle = os.open(target, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    os.write(handle, manual)
                    os.fsync(handle)
                finally:
                    os.close(handle)
            return exchange(fd, candidate, target)

        with patch.object(learning, "exchange", side_effect=concurrent_exchange):
            self.assert_code("external_race", self.store.apply, plan)
        retained = list(self.topic_path().parent.glob(".*.swap"))
        self.assertEqual(1, len(retained))
        self.assertEqual(manual, retained[0].read_bytes())
        self.assertEqual("pending", self.store.status()["status"])
        self.assert_code("external_race", self.store.recover)
        self.assertEqual(manual, retained[0].read_bytes())

    def test_last_daily_file_race_cannot_be_confirmed_by_markdown_replay(self) -> None:
        self.save(self.capture())
        next_capture = self.capture(hour=15)
        plan = self.store.prepare(next_capture)
        exchange = learning.exchange
        manual = b"Edicion manual ficticia del diario durante el ultimo intercambio.\n"

        def concurrent_daily_exchange(fd, candidate, target):
            if target == self.daily_path().name:
                handle = os.open(target, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    os.write(handle, manual)
                    os.fsync(handle)
                finally:
                    os.close(handle)
            return exchange(fd, candidate, target)

        with patch.object(learning, "exchange", side_effect=concurrent_daily_exchange):
            self.assert_code("external_race", self.store.apply, plan)
        retained = list(self.daily_path().parent.glob(".*.swap"))
        self.assertEqual(1, len(retained))
        self.assertEqual(manual, retained[0].read_bytes())
        self.assertFalse(self.store.receipt(next_capture["event_id"]))
        self.assert_code("pending", self.store.prepare, next_capture)
        self.assertEqual("pending", self.store.status()["status"])
        pending_query = self.store.query()
        self.assertEqual("pending", pending_query["status"])
        self.assertTrue(pending_query["partial"])
        self.assertEqual(manual, retained[0].read_bytes())
        self.assert_code("external_race", self.store.recover, abandon=True)
        self.assert_code("pending", self.store.prepare, next_capture)
        self.assertNotEqual("ready", self.store.status()["status"])
        self.assertTrue(self.store.query()["partial"])
        self.assertEqual(manual, retained[0].read_bytes())

    def test_body_related_notes_headings_cannot_nest_or_rewrite_an_event(self) -> None:
        first = self.capture()
        first["topics"][0]["body"] += "\n\n## Related notes\n\nEncabezado legítimo dentro de la explicación ficticia.\n\n```markdown\n## Related notes\nUn ejemplo ficticio de Markdown.\n```\n"
        self.save(first)
        original_block = learning.block(self.topic_path().read_text(), first["event_id"])
        second = self.capture(hour=16)
        second["topics"][0]["body"] += " Segunda revisión ficticia del mismo tema."
        self.save(second)
        current = self.topic_path().read_text()
        self.assertEqual(original_block, learning.block(current, first["event_id"]))
        self.assertEqual("already_applied", self.store.prepare(first)["status"])
        self.assertEqual("already_applied", self.store.prepare(second)["status"])
        self.assertIn("<!-- LEARNING-CURRENT: " + second["event_id"], current)
        self.assertLess(current.index("<!-- LEARNING:BEGIN " + first["event_id"]), current.index("<!-- LEARNING:END " + first["event_id"]))
        self.assertLess(current.index("<!-- LEARNING:END " + first["event_id"]), current.index("<!-- LEARNING:BEGIN " + second["event_id"]))
        self.assertLess(current.index("<!-- LEARNING:BEGIN " + second["event_id"]), current.index("<!-- LEARNING:END " + second["event_id"]))

    def test_missing_reserved_insertion_marker_preserves_a_manual_note(self) -> None:
        capture = self.capture()
        target = self.topic_path()
        target.parent.mkdir(parents=True)
        content = "---\ntitle: Nota manual ficticia\nclassification: restricted\n---\n\n# Nota manual ficticia\n\nContenido manual que conserva autoridad.\n\n## Related notes\n\n- [[nota_manual_ficticia|Referencia]]\n"
        target.write_text(content)
        self.assert_code("invalid_note", self.store.prepare, capture)
        self.assertEqual(content, target.read_text())
        self.assertFalse(self.store.state.exists())

    def test_nested_git_owners_are_not_treated_as_root_ignored_untracked_notes(self) -> None:
        for nested_area in ("private", "topics"):
            for child_tracked in (False, True):
                with self.subTest(nested_area=nested_area, child_tracked=child_tracked):
                    directory = tempfile.TemporaryDirectory(prefix="omaros_fictitious_nested_owner_")
                    self.addCleanup(directory.cleanup)
                    root = Path(directory.name)
                    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True, capture_output=True)
                    (root / ".gitignore").write_text("/" + learning.BASE + "/\n")
                    target = root / learning.BASE / "Topics/onboarding_pricer.md"
                    target.parent.mkdir(parents=True)
                    nested_root = root / learning.BASE if nested_area == "private" else target.parent
                    subprocess.run(["git", "-C", str(nested_root), "init", "-q"], check=True, capture_output=True)
                    capture = self.capture()
                    original = learning.new_note("Nota ficticia de otro dueño Git", "evergreen", capture["captured_at"], learned_on=None)
                    target.write_text(original)
                    if child_tracked:
                        subprocess.run(["git", "-C", str(nested_root), "add", "--", str(target.relative_to(nested_root))], check=True, capture_output=True)

                    def entries(owner: Path) -> bytes:
                        return subprocess.run(["git", "-C", str(owner), "ls-files", "--stage", "-z"], check=True, capture_output=True).stdout

                    root_before, nested_before = entries(root), entries(nested_root)
                    self.assertEqual(b"", root_before)
                    subprocess.run(["git", "-C", str(root), "check-ignore", "--no-index", "-q", "--", str(target.relative_to(root))], check=True, capture_output=True)
                    mark_fixture_vault(root)
                    store = self.alternate_store(root)
                    with self.assertRaises(learning.CaptureError) as rejected:
                        store.prepare(capture)
                    self.assertIn("owner", rejected.exception.code)
                    self.assertEqual(original, target.read_text())
                    self.assertEqual(root_before, entries(root))
                    self.assertEqual(nested_before, entries(nested_root))
                    self.assertFalse(store.state.exists())

    def test_query_by_date_topic_title_and_relations(self) -> None:
        self.save(self.capture(topics=["onboarding_pricer", "hedging_pricer"]))
        by_date = self.store.query(date="2026-10-26")
        self.assertEqual([str(self.daily_path().relative_to(self.root))], [r["path"] for r in by_date["results"]])
        by_topic = self.store.query(topic="hedging_pricer")
        self.assertEqual(2, len(by_topic["results"]))
        self.assertEqual(2, len(self.store.query("onboarding ficticio")["results"]))
        related = self.store.query(related=self.antecedent)
        self.assertEqual([str(self.topic_path("hedging_pricer").relative_to(self.root))], [r["path"] for r in related["results"]])
        self.assertFalse(by_date["partial"])
        self.assertEqual(3, by_date["scanned"])

    def test_invalid_capture_metadata_provenance_paths_and_reserved_markers(self) -> None:
        cases = []
        missing_date = self.capture()
        del missing_date["learned_on"]
        cases.append(missing_date)
        timezone = self.capture()
        timezone["captured_at"] = "2026-10-26T10:00:00"
        cases.append(timezone)
        traversal = self.capture()
        traversal["topics"][0]["slug"] = "../../outside"
        cases.append(traversal)
        no_provenance = self.capture()
        no_provenance["topics"][0]["provenance"] = []
        cases.append(no_provenance)
        unknown_kind = self.capture()
        unknown_kind["topics"][0]["provenance"][0]["kind"] = "confirmed_without_source"
        cases.append(unknown_kind)
        malformed_kind = self.capture()
        malformed_kind["topics"][0]["provenance"][0]["kind"] = ["user"]
        cases.append(malformed_kind)
        marker = self.capture()
        marker["topics"][0]["body"] = "<!-- LEARNING:BEGIN forged -->"
        cases.append(marker)
        transcript = self.capture()
        transcript["raw_prompt"] = "No debe aceptarse este campo ficticio."
        cases.append(transcript)
        for payload in cases:
            with self.subTest(payload=payload["event_id"]):
                with self.assertRaises(learning.CaptureError):
                    self.store.prepare(payload)
        self.assertFalse((self.root / learning.BASE).exists())

    def test_unignored_and_tracked_private_targets_are_rejected(self) -> None:
        (self.root / ".gitignore").write_text("")
        self.assert_code("unprotected_private", self.store.prepare, self.capture())
        (self.root / ".gitignore").write_text("/" + learning.BASE + "/\n")
        target = self.topic_path()
        target.parent.mkdir(parents=True)
        target.write_text("Contenido ficticio ya preparado en Git.\n")
        self.git("add", "-f", "--", str(target.relative_to(self.root)))
        self.assert_code("tracked_private", self.store.prepare, self.capture())
        self.assertIn("Contenido ficticio", target.read_text())

    def test_parent_and_leaf_symlinks_cannot_escape_private_scope(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        private = self.root / learning.BASE
        private.parent.mkdir(parents=True, exist_ok=True)
        private.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(learning.CaptureError) as rejected:
            self.store.prepare(self.capture())
        self.assertIn(rejected.exception.code, {"unsafe_path", "unprotected_private"})
        self.assertFalse(list(outside.iterdir()))
        private.unlink()
        target = self.topic_path()
        target.parent.mkdir(parents=True)
        original = outside / "original.md"
        original.write_text("Fuente ficticia que debe conservarse.\n")
        target.symlink_to(original)
        self.assert_code("unsafe_path", self.store.prepare, self.capture())
        self.assertEqual("Fuente ficticia que debe conservarse.\n", original.read_text())

    def test_existing_daily_authority_is_not_silently_reclassified(self) -> None:
        capture = self.capture()
        target = self.daily_path()
        target.parent.mkdir(parents=True)
        original = learning.new_note("Nota diaria manual ficticia", "daily", capture["captured_at"], learned_on=capture["learned_on"])
        original = original.replace("classification: restricted", "classification: canonical")
        target.write_text(original)
        self.assert_code("authority_conflict", self.store.prepare, capture)
        self.assertEqual(original, target.read_text())

    def test_edited_managed_block_is_not_confirmed_as_a_successful_retry(self) -> None:
        capture = self.capture()
        self.save(capture)
        target = self.topic_path()
        target.write_text(target.read_text().replace("La configuración simulada", "La edición manual ficticia"))
        self.assert_code("diverged", self.store.prepare, capture)

    def test_cli_prepare_apply_and_query_use_real_files(self) -> None:
        def run(command: list[str], payload=None) -> tuple[int, dict]:
            result = subprocess.run([sys.executable, "-I", "-B", str(self.skill_caller()), "--root", str(self.root), *command], input=json.dumps(payload) if payload is not None else None, text=True, capture_output=True, check=False)
            return result.returncode, json.loads(result.stdout)

        code, prepared = run(["prepare"], self.capture())
        self.assertEqual(0, code)
        self.assertEqual("prepared", prepared["status"])
        code, applied = run(["apply"], prepared)
        self.assertEqual(0, code)
        self.assertEqual("applied", applied["status"])
        self.assertTrue(self.topic_path().exists())
        code, found = run(["query", "onboarding ficticio", "--date", "2026-10-26"])
        self.assertEqual(0, code)
        self.assertEqual(1, len(found["results"]))
        code, invalid = run(["prepare"], {"raw_prompt": "Ejemplo ficticio de entrada inválida"})
        self.assertEqual(2, code)
        self.assertFalse(invalid["persisted"])

    def test_git_environment_cannot_hide_a_tracked_private_destination(self) -> None:
        target = self.topic_path()
        target.parent.mkdir(parents=True)
        original = learning.new_note("Nota ficticia ya preparada en el índice real", "evergreen", "2026-10-26T10:00:00+00:00", learned_on=None)
        target.write_text(original)
        self.git("add", "-f", "--", str(target.relative_to(self.root)))
        alternate_index = self.root / "fictitious_empty_index"
        clean_environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        subprocess.run(["git", "-C", str(self.root), "read-tree", "--empty"], env={**clean_environment, "GIT_INDEX_FILE": str(alternate_index)}, check=True, capture_output=True)
        foreign = self.root / "fictitious_foreign_owner"
        foreign.mkdir()
        subprocess.run(["git", "-C", str(foreign), "init", "-q"], env=clean_environment, check=True, capture_output=True)
        root_before = self.git("ls-files", "--stage", "-z").stdout
        alternate_before = alternate_index.read_bytes()
        scenarios = [
            {"GIT_INDEX_FILE": str(alternate_index)},
            {"GIT_INDEX_FILE": str(alternate_index), "GIT_DIR": str(foreign / ".git"), "GIT_WORK_TREE": str(foreign)},
        ]
        for overrides in scenarios:
            with self.subTest(overrides=tuple(overrides)), patch.dict(os.environ, overrides):
                store = learning.Store(self.root, device_home=self.device_home)
                self.assertEqual(self.root.resolve(), store.root)
                self.assert_code("tracked_private", store.prepare, self.capture())
        self.assertEqual(original, target.read_text())
        self.assertEqual(root_before, self.git("ls-files", "--stage", "-z").stdout)
        self.assertEqual(alternate_before, alternate_index.read_bytes())
        self.assertFalse((foreign / ".git/index").exists())

    def test_recovery_across_utc_midnight_preserves_actual_file_dates(self) -> None:
        real_datetime = dt.datetime

        class FrozenClock(real_datetime):
            current = real_datetime(2026, 10, 26, 23, 59, tzinfo=dt.timezone.utc)

            @classmethod
            def now(cls, tz=None):
                return cls.current.astimezone(tz) if tz else cls.current.replace(tzinfo=None)

        for phase in ("before_first_write", "after_first_destination", "candidate_before_exchange"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory(prefix="omaros_fictitious_midnight_") as directory:
                root = Path(directory)
                subprocess.run(["git", "-C", str(root), "init", "-q"], check=True, capture_output=True)
                (root / ".gitignore").write_text("/" + learning.BASE + "/\n")
                mark_fixture_vault(root)
                store = self.alternate_store(root)
                topic = root / learning.BASE / "Topics/onboarding_pricer.md"
                daily = root / learning.BASE / "Daily/2020/2020-06-02.md"
                capture = self.capture(date="2020-06-02")
                capture["captured_at"] = "2026-10-26T23:59:00+00:00"
                with patch.object(learning.dt, "datetime", FrozenClock):
                    if phase == "candidate_before_exchange":
                        FrozenClock.current = real_datetime(2026, 10, 25, 12, 0, tzinfo=dt.timezone.utc)
                        seed = self.capture(date="2020-06-02")
                        seed["captured_at"] = "2026-10-25T12:00:00+00:00"
                        store.apply(store.prepare(seed))
                    FrozenClock.current = real_datetime(2026, 10, 26, 23, 59, tzinfo=dt.timezone.utc)
                    plan = store.prepare(capture)
                    if phase == "before_first_write":
                        interrupted = patch.object(store, "_replace", side_effect=OSError("Interrupción ficticia antes de escribir"))
                    elif phase == "after_first_destination":
                        replace = store._replace
                        calls = 0

                        def fail_after_first(change, observed):
                            nonlocal calls
                            calls += 1
                            replace(change, observed)
                            if calls == 1:
                                raise OSError("Interrupción ficticia después del primer destino")

                        interrupted = patch.object(store, "_replace", side_effect=fail_after_first)
                    else:
                        interrupted = patch.object(learning, "exchange", side_effect=OSError("Interrupción ficticia tras fsync del candidato"))
                    with interrupted, self.assertRaises((OSError, learning.CaptureError)):
                        store.apply(plan)
                    self.assertEqual("pending", store.status()["status"])
                    FrozenClock.current = real_datetime(2026, 10, 27, 0, 1, tzinfo=dt.timezone.utc)
                    self.assertEqual("applied", store.recover()["status"])
                topic_data, daily_data = learning.metadata(topic.read_text()), learning.metadata(daily.read_text())
                expected_topic_created = "2026-10-25" if phase == "candidate_before_exchange" else ("2026-10-26" if phase == "after_first_destination" else "2026-10-27")
                expected_daily_created = "2026-10-25" if phase == "candidate_before_exchange" else "2026-10-27"
                self.assertEqual(expected_topic_created, str(topic_data["created"]))
                self.assertEqual(expected_daily_created, str(daily_data["created"]))
                self.assertEqual("2026-10-26" if phase == "after_first_destination" else "2026-10-27", str(topic_data["updated"]))
                self.assertEqual("2026-10-27", str(daily_data["updated"]))
                self.assertEqual("2020-06-02", str(daily_data["learned_on"]))
                self.assertIn(capture["captured_at"], topic.read_text())
                self.assertEqual("already_applied", store.prepare(capture)["status"])
                self.assertFalse(list((root / learning.BASE).rglob("*.swap")))

    def test_missing_top_heading_does_not_rewrite_a_heading_in_an_old_block(self) -> None:
        first = self.capture()
        first["topics"][0]["body"] += "\n\n# Encabezado legítimo de una explicación ficticia\n\n```markdown\n# Ejemplo ficticio dentro de código\n```\n"
        self.save(first)
        path = self.topic_path()
        original = path.read_text()
        old_block = learning.block(original, first["event_id"])
        without_top_heading = original.replace("# " + first["topics"][0]["title"] + "\n", "", 1)
        self.assertNotEqual(original, without_top_heading)
        path.write_text(without_top_heading)
        second = self.capture(hour=16)
        second["topics"][0]["title"] = "Onboarding ficticio revisado después de una edición manual"
        self.save(second)
        self.assertEqual(old_block, learning.block(path.read_text(), first["event_id"]))
        self.assertEqual("already_applied", self.store.prepare(first)["status"])
        self.assertEqual("already_applied", self.store.prepare(second)["status"])

    def test_near_limit_capture_plan_and_aggregate_recovery_are_usable(self) -> None:
        capture = self.capture(topics=[f"fictitious_capacity_{number}" for number in range(12)])
        for topic in capture["topics"]:
            topic["body"] = "EJEMPLO FICTICIO DE CAPACIDAD.\n" + "x" * 61900
            topic["questions"] = ["Duda ficticia de capacidad: " + "q" * 19900]
        remaining = learning.LIMIT - 256 - len(learning.serialized(capture))
        self.assertGreater(remaining, 0)
        capture["summary"] += "s" * remaining
        self.assertLessEqual(len(capture["summary"].encode()), 65536)
        raw = json.dumps(capture, ensure_ascii=False, separators=(",", ":")).encode()
        self.assertLess(len(raw), learning.LIMIT)

        def command(name: str, payload: bytes) -> subprocess.CompletedProcess[bytes]:
            return subprocess.run([sys.executable, "-I", "-B", str(self.skill_caller()), "--root", str(self.root), name], input=payload, capture_output=True, check=False)

        prepared = command("prepare", raw)
        self.assertEqual(0, prepared.returncode)
        self.assertGreater(len(prepared.stdout), learning.LIMIT)
        applied = command("apply", prepared.stdout)
        self.assertEqual(0, applied.returncode)
        self.assertEqual("applied", json.loads(applied.stdout)["status"])
        second = copy.deepcopy(capture)
        second["event_id"] = str(uuid.uuid4())
        second["captured_at"] = "2026-10-26T11:00:00+00:00"
        plan = self.store.prepare(second)
        with patch.object(self.store, "_replace", side_effect=OSError("Interrupción ficticia de una transacción grande")):
            with self.assertRaises((OSError, learning.CaptureError)):
                self.store.apply(plan)
        pending_path = self.store.state / "pending.json"
        self.assertGreater(pending_path.stat().st_size, learning.LIMIT)
        self.assertLess(pending_path.stat().st_size, learning.STATE_LIMIT)
        self.assertEqual("pending", self.store.status()["status"])
        self.assertEqual("applied", self.store.recover()["status"])
        self.assertEqual("already_applied", self.store.prepare(second)["status"])


if __name__ == "__main__":
    unittest.main()
