"""Release timers operate on a single installation and advance only after success."""
import importlib.util
import io
import json
import os
import plistlib
import stat
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


def module():
    path = Path(__file__).resolve().parents[1] / "updates.py"
    spec = importlib.util.spec_from_file_location("test_device_updates", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@unittest.skipUnless(os.name == "posix", "POSIX device release timer")
class ReleaseTimers(unittest.TestCase):
    def setUp(self):
        self.u = module()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.temp = Path(temporary.name).resolve()
        self.home = self.temp / "Codex Home"
        (self.home / "constellation" / "state").mkdir(parents=True, mode=0o700)
        self.receipt = self.home / "constellation/receipt.json"
        self.receipt.write_text(json.dumps({"cache": {"bundle.json": {"sha256": "d" * 64}}}))
        self.profile = {"vault_root": None, "workspace_root": None, "language": "es", "codex": "/bin/echo"}
        self.revision = "a" * 40
        self.sync = b"""
def published_head(): return "CURRENT_FIXTURE_REV"
class SyncError(Exception): pass
def synchronize(revision, home, **kwargs):
    import json
    root = kwargs["workspace_root"]
    workspace = None
    bundle_hash = json.loads((home / "constellation/receipt.json").read_text())["cache"]["bundle.json"]["sha256"]
    if root is not None:
        source = root / ".codex/skills"
        rows = [{"name":p.parent.name,"path":str(p),"verified":True,"enabled":False}
                for p in source.glob("*/SKILL.md")]
        selected = {r["name"] for r in rows}
        config = home / "config.toml"
        preferences = set(config.read_text().splitlines()) if config.exists() else set()
        if set(kwargs["protect_exclusions"]) & selected - preferences:
            raise SyncError("explicit preferences")
        if selected - preferences:
            config.write_text("".join(n + chr(10) for n in sorted(preferences | selected)))
        workspace = {"source_root":str(root / ".codex"),"status":"excluded",
                     "paths":rows,"bundle_sha256":bundle_hash}
    with (home / 'calls').open('a') as stream: stream.write(revision + '\\n')
    return {'revision': revision, 'bundle_sha256': bundle_hash, 'workspace': workspace}
"""
        self.marker = self.home / "constellation/state/release-updates/last.json"

    def tick(self, source=None):
        selected = self.sync if source is None else source
        return self.u.tick(self.home, selected.replace(b"CURRENT_FIXTURE_REV", self.revision.encode()), self.profile)

    def test_new_main_syncs_once_per_profile_and_installation(self):
        self.assertEqual(self.tick()["status"], "synchronized")
        self.assertEqual(self.tick()["status"], "current")
        self.assertEqual((self.home / "calls").read_text().splitlines(), [self.revision])
        self.revision = "b"*40
        self.assertEqual(self.tick()["revision"], self.revision)
        self.profile["language"] = "en"
        self.assertEqual(self.tick()["status"], "synchronized")
        self.receipt.write_text(self.receipt.read_text() + "\n")
        self.assertEqual(self.tick()["status"], "synchronized")
        self.assertEqual(self.tick()["status"], "current")
        self.assertEqual(self.marker.stat().st_mode & 0o777, 0o600)

    def test_unfinished_binding_or_mismatched_bundle_retries(self):
        self.tick()
        previous = self.marker.read_bytes()
        self.revision = "b"*40
        failing = self.sync.replace(b"return {'revision'", b"raise SyncError('binding incomplete'); return {'revision'")
        with self.assertRaisesRegex(self.u.UpdateError, "binding incomplete"):
            self.tick(failing)
        self.assertEqual(previous, self.marker.read_bytes())
        with self.assertRaisesRegex(self.u.UpdateError, "differs"):
            self.tick(self.sync.replace(b"'bundle_sha256': bundle_hash", b"'bundle_sha256': 'e' * 64"))
        self.assertEqual(previous, self.marker.read_bytes())
        self.assertEqual(self.tick()["status"], "synchronized")

    def test_busy_duplicate_never_contacts_remote_or_executes_sync(self):
        base=self.marker.parent; self.u._directory(base)
        with self.u._timer_lock(base / "lock"):
            self.assertEqual(self.tick(b"raise AssertionError"), {"status": "busy"})

    def test_local_checkout_and_explicit_config_drift_reconcile_without_reinstall(self):
        root = self.temp / "hub"
        source = root / ".codex" / "skills"
        names = [f"method-{i}" for i in range(11)]
        def add(name):
            file = source / name / "SKILL.md"
            file.parent.mkdir(parents=True)
            file.write_text("method")
        for name in names[:4]:
            add(name)
        record = json.loads(self.receipt.read_text())
        record["cache"].update({f"skills/{name}/SKILL.md": {} for name in names})
        self.receipt.write_text(json.dumps(record))
        self.profile["workspace_root"] = str(root)
        def verify(home, profile, bundle, protect, verifier):
            rows = [{"name":p.parent.name,"path":str(p),"verified":True,"enabled":False}
                    for p in source.glob("*/SKILL.md")]
            return {"status":"excluded","source_root":str(source.parent),"paths":rows,"bundle_sha256":bundle}
        with patch.object(self.u, "_reconcile", side_effect=verify) as reconcile:
            self.assertEqual(self.tick()["status"], "synchronized")
            self.assertEqual(self.tick()["status"], "reconciled")
            self.assertEqual(self.tick()["status"], "current")
            reconcile.assert_called_once()
            for name in names[4:]:
                add(name)
            self.assertEqual(self.tick()["status"], "reconciled")
            self.assertEqual(self.tick()["status"], "current")
            (self.home / "config.toml").write_text("[features]\n")
            self.assertEqual(self.tick()["status"], "reconciled")
            self.assertEqual(self.tick()["status"], "current")
            self.assertEqual(reconcile.call_count, 3)
            self.assertEqual((self.home / "calls").read_text().splitlines(), [self.revision])
            self.assertEqual(self.tick()["status"], "current")

    def test_config_conflict_preserves_marker_and_avoids_reinstall(self):
        root = self.temp / "hub"
        root.mkdir()
        self.profile["workspace_root"] = str(root)
        with patch.object(self.u, "_reconcile", return_value=set()):
            self.tick()
        old = self.marker.read_bytes()
        (self.home / "config.toml").write_text("explicitly re-enabled fixture")
        with patch.object(self.u, "_reconcile", side_effect=self.u.UpdateError("explicit preference")):
            with self.assertRaisesRegex(self.u.UpdateError, "explicit preference"):
                self.tick()
        self.assertEqual(self.marker.read_bytes(), old)
        self.assertEqual((self.home / "calls").read_text().splitlines(), [self.revision])
        self.assertEqual((self.home / "config.toml").read_text(), "explicitly re-enabled fixture")

    def test_successful_native_suppressions_protect_reenabled_missing_row(self):
        root = self.temp / "hub"
        source = root / ".codex/skills"
        self.profile["workspace_root"] = str(root)
        record = json.loads(self.receipt.read_text())
        for name in ("old", "new"):
            record["cache"][f"skills/{name}/SKILL.md"] = {}
        self.receipt.write_text(json.dumps(record))
        initial = source / "old/SKILL.md"
        initial.parent.mkdir(parents=True)
        initial.write_text("old")
        verifier = b"""
import json
def dispatch_installed(home, mode, args):
    root = args[args.index("--cwd") + 1]; source = __import__('pathlib').Path(root) / '.codex/skills'
    preferences = home / 'config.toml'
    old = set(preferences.read_text().splitlines()) if preferences.exists() else set()
    protect = {args[i+1] for i,x in enumerate(args) if x == '--protect-exclusion'}
    paths = [(p.parent.name, p) for p in source.glob('*/SKILL.md')]
    if any(name in protect and name not in old for name,p in paths):
        return 1
    enabled = {name for name,p in paths} | old
    if enabled != old:
        preferences.write_text(''.join(x + chr(10) for x in sorted(enabled)))
    rows = [{'name':name,'path':str(p),'verified':True,'enabled':False} for name,p in paths]
    print(json.dumps({'source_root':str(source.parent),'status':'excluded','bundle_sha256':'d'*64,'paths':rows}))
    return 0
"""
        sync = self.sync.replace(b"CURRENT_FIXTURE_REV", self.revision.encode())
        def invoke():
            return self.u.tick(self.home, sync, self.profile, verifier_source=verifier)
        # The timer has already been admitted by the verified bootstrap. A
        # mutable path reopened inside that operation cannot supply more code.
        launcher = self.home / "constellation/run"
        unexpected = self.home / "unverified-executed"
        launcher.write_text(f'#!/bin/sh\n/usr/bin/touch "{unexpected}"\nexit 1\n')
        launcher.chmod(0o700)
        self.assertEqual(invoke()["status"], "synchronized")
        self.assertFalse(unexpected.exists())
        stored = self.marker.read_bytes()
        self.assertEqual(json.loads(stored)["managed"]["names"], ["old"])
        # Native enable(true) removes its prior exact false setting. The timer
        # must distinguish that restored source from a path first seen later.
        config = self.home / "config.toml"
        config.write_text("")
        new = source / "new/SKILL.md"
        new.parent.mkdir()
        new.write_text("new")
        with self.assertRaisesRegex(self.u.UpdateError, "preferences"):
            invoke()
        self.assertEqual(config.read_text(), "")
        self.assertEqual(self.marker.read_bytes(), stored)
        self.assertEqual((self.home / "calls").read_text().splitlines(), [self.revision])
        self.assertFalse(unexpected.exists())
        # A device receipt drift cannot erase this history before the new
        # choice is checked, including when a publication arrived meanwhile.
        self.receipt.write_text(self.receipt.read_text() + "\n")
        with self.assertRaisesRegex(self.u.UpdateError, "preferences"):
            invoke()
        self.assertEqual((self.home / "calls").read_text().splitlines(), [self.revision])

    def test_promotion_checks_new_candidate_once_across_changed_inventory(self):
        root = self.temp / "hub"
        source = root / ".codex/skills"
        self.profile["workspace_root"] = str(root)
        def add(name):
            path = source / name / "SKILL.md"
            path.parent.mkdir(parents=True)
            path.write_text("fixture")
        add("old")
        record = json.loads(self.receipt.read_text())
        record["cache"]["skills/old/SKILL.md"] = {}
        self.receipt.write_text(json.dumps(record))
        self.tick()
        self.assertEqual(json.loads(self.marker.read_bytes())["managed"]["names"], ["old"])
        self.revision = "b" * 40
        add("new")
        # B has a different receipt inventory and bundle digest. An A-only
        # verifier would reject it. Only the B native result may attest this.
        incoming = self.sync.replace(b'    root = kwargs', b"""
    record=json.loads((home / "constellation/receipt.json").read_text())
    record["cache"]["skills/new/SKILL.md"]={}
    record["cache"]["bundle.json"]["sha256"]="e"*64
    (home / "constellation/receipt.json").write_text(json.dumps(record))
    root = kwargs""")
        with patch.object(self.u, "_reconcile", side_effect=AssertionError("stale verifier")):
            self.assertEqual(self.tick(incoming)["status"], "synchronized")
        stored = json.loads(self.marker.read_text())
        self.assertEqual(stored["revision"], self.revision)
        self.assertEqual(stored["managed"]["names"], ["new","old"])
        self.assertEqual((self.home / "calls").read_text().splitlines(), ["a"*40, "b"*40])

    def test_enrollment_uses_stable_launcher_across_interpreter_rotations(self):
        output = io.StringIO()
        with redirect_stdout(output), patch.object(self.u.sys, "platform", "darwin"):
            self.assertEqual(0, self.u.run(["plan", "--general", "--codex", sys.executable],
                                           home=self.home, sync_source=b""))
        proposal = json.loads(output.getvalue())
        definition = plistlib.loads(next(iter(proposal["definitions"].values())).encode())
        self.assertEqual(definition["ProgramArguments"][:3],
                         [str(self.home / "constellation/run"), "updates", "tick"])

    def test_enrolled_path_rejects_retargeted_ancestor_before_running_sync(self):
        target = self.temp / "replacement" / "hub"
        target.mkdir(parents=True)
        ancestor = self.temp / "previous"
        ancestor.symlink_to(target.parent, target_is_directory=True)
        error = io.StringIO()
        with redirect_stderr(error):
            result = self.u.run(["tick", "--general", "--workspace-root", str(ancestor / "hub"),
                                 "--codex", sys.executable], home=self.home,
                                sync_source=b"raise AssertionError('must remain unexecuted')")
        self.assertEqual(result, 1)
        self.assertIn("canonical", error.getvalue())
        self.assertFalse(self.marker.exists())

    def test_foreign_marker_link_is_not_followed(self):
        base=self.marker.parent; self.u._directory(base)
        external=self.temp / "foreign"; external.write_text("outside")
        self.marker.symlink_to(external)
        with self.assertRaises(OSError):
            self.tick()
        self.assertEqual("outside", external.read_text())
        self.assertFalse((self.home / "calls").exists())

    def test_current_is_quiet_and_remote_failures_do_not_replace_marker(self):
        self.profile["codex"] = str(Path(sys.executable).absolute())
        self.tick()
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(0, self.u.run(["tick","--general","--codex",sys.executable],home=self.home,sync_source=self.sync.replace(b"CURRENT_FIXTURE_REV",self.revision.encode())))
        self.assertEqual("", stdout.getvalue())
        previous=self.marker.read_bytes()
        unavailable = self.sync.replace(b'return "CURRENT_FIXTURE_REV"', b'raise SyncError("timeout")')
        with self.assertRaisesRegex(self.u.UpdateError, "timeout"):
            self.u.tick(self.home, unavailable, self.profile)
        self.assertEqual(previous, self.marker.read_bytes())


updates = module()


class ScheduleTest(unittest.TestCase):
    def test_native_plist_preserves_literals_and_never_activates(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            args = [str(base / 'py $ with% space'), '-I', '--path', '/vault/a & b']
            with patch.dict(os.environ, HOME=str(base)), patch.object(sys, "platform", "darwin"):
                first = updates.schedule(base / ".codex", args, install=False)
                name, body = next(iter(first["definitions"].items()))
                self.assertEqual(plistlib.loads(body.encode())["ProgramArguments"], args)
                self.assertFalse(Path(name).exists())
                enrolled = updates.schedule(base / ".codex", args, install=True)
                self.assertEqual(enrolled['activate'][0][1], 'bootstrap')
                before = Path(name).stat()
                updates.schedule(base / ".codex", args, install=True)
                after = Path(name).stat()
                self.assertEqual((before.st_ino, before.st_mtime_ns),
                                 (after.st_ino, after.st_mtime_ns))
                self.assertEqual(stat.S_IMODE(after.st_mode), 0o600)

    def test_collision_preflight_and_literal_systemd_argv(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            home = base / 'c$% home'
            args = [str(base / 'py$% space'), '/a"b', '/literal%$']
            with patch.dict(os.environ, HOME=str(base), XDG_CONFIG_HOME=str(base / '.config')), \
                    patch.object(sys, 'platform', 'linux'):
                plan = updates.schedule(home, args, install=False)
                service, timer = [Path(x) for x in plan['definitions']]
                self.assertIn('":' + str(base) + '/py$%% space" "/a\\"b" "/literal%%$"',
                              plan['definitions'][str(service)])
                timer.parent.mkdir(parents=True)
                timer.write_text("other schedule")
                with self.assertRaises(ValueError):
                    updates.schedule(home, args, install=True)
                self.assertFalse(service.exists())
                self.assertEqual(timer.read_text(), "other schedule")

    def test_unsafe_definition_or_parent_is_never_followed(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            foreign = base / "foreign"
            foreign.mkdir()
            (base / ".config").symlink_to(foreign, target_is_directory=True)
            with patch.dict(os.environ, HOME=str(base), XDG_CONFIG_HOME=str(base / ".config")), \
                    patch.object(sys, 'platform', 'linux'):
                with self.assertRaises(OSError):
                    updates.schedule(base / ".codex", ["/python"], install=True)
            self.assertEqual(list(foreign.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
