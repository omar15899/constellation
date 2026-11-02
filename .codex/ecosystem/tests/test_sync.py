"""Release synchronization resolves immutable published Git bytes before execution."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from helpers import CODEX_DIR  # Place the tested package root on sys.path.
from ecosystem import sync


class ReleaseSyncTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name).resolve()
        self.upstream = self.work / "published"
        self.upstream.mkdir()
        self.git("init", "-q", "-b", "main")
        for folder in (".codex/ecosystem", ".codex/skills", "notes"):
            (self.upstream / folder).mkdir(parents=True)
        (self.upstream / "notes/context.md").write_text("out of package scope")
        (self.upstream / ".codex/skills/example.md").write_text("published method")
        (self.upstream / ".codex/ecosystem/build.py").write_text(
            "import sys,shutil\nfrom pathlib import Path\n"
            "dest=Path(sys.argv[sys.argv.index('--output')+1]);dest.mkdir()\n"
            "(dest/'bundle.json').write_bytes((Path(__file__).parents[1]/'skills/example.md').read_bytes())\n"
            "shutil.copytree(Path(__file__).parents[1]/'skills',dest/'skills')\n"
            "shutil.copytree(Path(__file__).parent,dest/'ecosystem')\n")
        (self.upstream / ".codex/ecosystem/install.py").write_text(
            "import json,hashlib,sys\nfrom pathlib import Path\n"
            "home=Path(sys.argv[sys.argv.index('--codex-home')+1])\n"
            "managed=home/'constellation'; receipt=managed/'receipt.json'\n"
            "bundle=Path(sys.argv[sys.argv.index('--bundle')+1])\n"
            "if '--check' not in sys.argv:\n"
            " expected=sys.argv[sys.argv.index('--expected-receipt-sha256')+1]\n"
            " current=hashlib.sha256(receipt.read_bytes()).hexdigest() if receipt.is_file() else 'absent'\n"
            " if expected!=current: raise SystemExit('stale receipt fixture')\n"
            " managed.mkdir(parents=True,exist_ok=True);(managed/'.install.lock').touch()\n"
            " digest=hashlib.sha256((bundle/'bundle.json').read_bytes()).hexdigest()\n"
            " mods=['coding','mathematics','quant-research','writter']\n"
            " if (bundle/'ecosystem/hook_entry.py').is_file():mods.append('omaros')\n"
            " launcher=managed/'run';launcher.write_bytes(b'fixture-launcher');launcher.chmod(0o700)\n"
            " rec={'mode':0o700,'sha256':hashlib.sha256(launcher.read_bytes()).hexdigest()}\n"
            " receipt.write_text(json.dumps({'schema':4,'python':sys.executable,'launcher':rec,"
            "'modules':mods,'cache':{'bundle.json':{'sha256':digest}}}))\n"
            "print(json.dumps({'status':'checked' if '--check' in sys.argv else 'installed'}))\n")
        (self.upstream / ".codex/ecosystem/native.py").write_text(
            "import sys,json\nfrom pathlib import Path\n"
            "cwd=Path(sys.argv[sys.argv.index('--cwd')+1])\n"
            "assert Path(sys.argv[sys.argv.index('--exclude-source-root')+1])==cwd/'.codex'\n"
            "protected=[sys.argv[i+1] for i,v in enumerate(sys.argv) if v=='--protect-exclusion']\n"
            "if '--check-protected-only' in sys.argv:\n"
            " if (cwd/'operator-reenabled').exists(): raise SystemExit('protected preference was re-enabled')\n"
            " print(json.dumps({'status':'protected'}))\n"
            "else:\n"
            " digest=sys.argv[sys.argv.index('--expected-bundle-sha256')+1]\n"
            " print(json.dumps({'status':'excluded','source_root':str(cwd/'.codex'),"
            "'bundle_sha256':digest,'fixture_protected':protected}))\n")
        self.git("add", ".codex", "notes")
        self.revision = self.commit()

    def git(self, *args):
        return subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@localhost", *args],
                              cwd=self.upstream, check=True, capture_output=True, text=True).stdout.strip()

    def commit(self):
        self.git("commit", "-qm", "fixture release")
        return self.git("rev-parse", "HEAD")

    def fixture_transport(self):
        # Only the private inject point provides file://. The CLI always uses HTTPS.
        git = ["git", "-c", f"url.{self.upstream.as_uri()}.insteadOf={sync.UPSTREAM}",
               "-c", "protocol.file.allow=always"]
        return git, {**os.environ, "GIT_ALLOW_PROTOCOL": "file", "GIT_TERMINAL_PROMPT": "0"}

    def run_release(self, revision, *, check=True, vault_root=None, codex="codex", workspace_root=None, protect_exclusions=()):
        with patch.object(sync, "_transport", return_value=self.fixture_transport()):
            return sync.synchronize(revision, self.work / "home", vault_root=vault_root,
                                    check=check, language="es", codex=codex, workspace_root=workspace_root,
                                    protect_exclusions=protect_exclusions)

    def test_canonical_probe_rejects_config_rewrite_or_injected_repository_without_connecting(self):
        work = self.work / "probe"
        work.mkdir()
        alternate = self.work / "alternate-home"
        alternate.mkdir()
        env = {"HOME": str(alternate), "XDG_CONFIG_HOME": str(alternate), "PATH": os.defpath}
        marker = self.work / "transport-executed"
        with patch.dict(os.environ, env, clear=True):
            for rewrite in (self.upstream.as_uri(), f"ext::touch {marker}"):
                config = alternate / ".gitconfig"
                config.write_text(f'[url "{rewrite}"]\n\tinsteadOf = {sync.UPSTREAM}\n'
                                  '[protocol "ext"]\n\tallow = always\n')
                with self.assertRaisesRegex(sync.SyncError, "rewrites the canonical"):
                    sync._transport(work)
                self.assertFalse(marker.exists())
            config.unlink()
            for key, value in (("GIT_DIR", str(self.upstream / ".git")), ("GIT_CONFIG_COUNT", "1")):
                with patch.dict(os.environ, {key: value}), self.assertRaisesRegex(sync.SyncError, "inherited Git"):
                    sync._transport(work)

    def test_install_receipt_changed_during_fetch_rejects_stale_promotion(self):
        published = sync._published_source
        managed = self.work / "home/constellation"
        captured_receipt = b'{"version":"newer"}'

        def competing_promotion(work, revision):
            result = published(work, revision)
            managed.mkdir(parents=True)
            (managed / "receipt.json").write_bytes(captured_receipt)
            return result

        with patch.object(sync, "_published_source", side_effect=competing_promotion), self.assertRaisesRegex(
            sync.SyncError, "stale receipt fixture"
        ):
            self.run_release(self.revision, check=False)
        self.assertEqual((managed / "receipt.json").read_bytes(), captured_receipt)

    def test_final_receipt_verification_rejects_release_changed_during_setup(self):
        managed = self.work / "device/constellation"
        managed.mkdir(parents=True)
        (managed / ".install.lock").touch()
        (managed / "receipt.json").write_text('{"modules":["coding"],"cache":{"bundle.json":{"sha256":"new"}}}')
        with self.assertRaisesRegex(sync.SyncError, "active release changed"):
            sync._confirm_active(managed.parent, "old", ("coding",))

    def test_frozen_https_transport_ignores_later_rewrite_and_dangerous_environment(self):
        work = self.work / "probe"
        work.mkdir()
        home = self.work / "device"
        home.mkdir()
        with patch.dict(os.environ, {"HOME": str(home), "PATH": os.defpath,
                                     "HTTPS_PROXY": "invalid.invalid:8080", "CURL_CA_BUNDLE": "unused"}, clear=True):
            git, env = sync._transport(work)
            config = home / ".gitconfig"
            config.write_text(f'[url "{self.upstream.as_uri()}"]\n    insteadOf = {sync.UPSTREAM}\n')
            self.assertEqual(sync._run([*git, "ls-remote", "--get-url", sync.UPSTREAM],
                                       cwd=work, env=env).strip(), sync.UPSTREAM)
            self.assertEqual(env["GIT_ALLOW_PROTOCOL"], "https")
            self.assertNotIn("HTTPS_PROXY", env)
            self.assertNotIn("CURL_CA_BUNDLE", env)

    def test_published_head_uses_same_frozen_transport(self):
        with patch.object(sync, "_transport", return_value=self.fixture_transport()) as checkout:
            self.assertEqual(sync.published_head(), self.revision)
        self.assertEqual(checkout.call_count, 1)

    def test_clean_snapshot_and_check_only(self):
        (self.upstream / ".codex/skills/example.md").write_text("unpublished work")
        result = self.run_release(self.revision)
        self.assertEqual(result["bundle_sha256"], hashlib.sha256(b"published method").hexdigest())
        self.assertEqual(result["revision"], self.revision)
        self.assertEqual(result["status"], "checked")
        self.assertFalse((self.work / "home").exists())
        result = self.run_release(self.revision, check=False)
        self.assertEqual(result["status"], "installed")
        self.assertTrue((self.work / "home").is_dir())
        self.assertEqual(result["receipt_schema"], 4)
        self.assertEqual(result["python"], os.path.abspath(sync.sys.executable))
        self.assertEqual(result["launcher_sha256"], hashlib.sha256(b"fixture-launcher").hexdigest())

    def test_final_confirmation_rejects_modified_or_linked_launcher(self):
        result = self.run_release(self.revision, check=False)
        launcher = Path(result["launcher"])
        launcher.write_bytes(b"foreign-launcher")
        with self.assertRaisesRegex(sync.SyncError, "stable launcher differs"):
            sync._confirm_active(self.work / "home", result["bundle_sha256"], sync.METHODS)
        launcher.unlink()
        launcher.symlink_to(self.upstream / "notes/context.md")
        with self.assertRaises(OSError):
            sync._confirm_active(self.work / "home", result["bundle_sha256"], sync.METHODS)

    def test_moved_main_rejected_before_install(self):
        (self.upstream / ".codex/skills/example.md").write_text("new release")
        self.git("add", ".codex/skills/example.md")
        self.commit()
        with self.assertRaisesRegex(sync.SyncError, "Published main"):
            self.run_release(self.revision, check=False)
        self.assertFalse((self.work / "home").exists())

    def test_latest_freezes_one_published_commit_and_reports_it(self):
        (self.upstream / ".codex/skills/example.md").write_text("next method")
        self.git("add", ".codex/skills/example.md")
        latest = self.commit()
        result = self.run_release(None)
        self.assertEqual(result["revision"], latest)
        self.assertEqual(result["bundle_sha256"], hashlib.sha256(b"next method").hexdigest())
        self.assertFalse((self.work / "home").exists())

    def test_link_in_release_rejected_before_build(self):
        (self.upstream / ".codex/skills/linked").symlink_to("../../notes")
        self.git("add", ".codex/skills/linked")
        revision = self.commit()
        with self.assertRaisesRegex(sync.SyncError, "regular files"):
            self.run_release(revision, check=False)
        self.assertFalse((self.work / "home").exists())

    def test_vault_setup_uses_selected_native_executable_and_project_root(self):
        executable = self.work / "custom-codex"
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
        entry = self.upstream / ".codex/ecosystem/hook_entry.py"
        entry.write_text(
            "import json,os\n"
            "def dispatch_installed(home, mode, args):\n"
            " assert mode=='install-vault' and args[0]=='--project-root'\n"
            " assert args[2]=='--codex' and os.access(args[3],os.X_OK)\n"
            " assert args[4]=='--expected-bundle-sha256' and len(args[5])==64\n"
            " print(json.dumps({'registered':True,'root':args[1],'codex':args[3]}))\n"
            " return 0\n")
        installer = self.upstream / ".codex/ecosystem/install.py"
        with installer.open("a") as file:
            file.write("if '--check' not in sys.argv:\n"
                       " (home/'constellation').mkdir(exist_ok=True)\n"
                       " (home/'constellation/hook.py').write_bytes(Path(__file__).with_name('hook_entry.py').read_bytes())\n")
        self.git("add", ".codex/ecosystem")
        revision = self.commit()
        with patch("importlib.util.find_spec", return_value=object()):
            result = self.run_release(revision, check=False, vault_root=self.upstream, codex=str(executable))
        self.assertEqual(result["binding"], {"registered": True, "root": str(self.upstream),
                                             "codex": str(executable)})

    def test_explicit_workspace_uses_actual_checkout_and_check_only_skips_exclusion(self):
        preview = self.run_release(self.revision, workspace_root=self.upstream)
        self.assertNotIn("workspace", preview)
        result = self.run_release(self.revision, check=False, workspace_root=self.upstream)
        self.assertEqual(result["workspace"], {"status": "excluded", "source_root": str(self.upstream / ".codex"),
                                               "bundle_sha256": result["bundle_sha256"], "fixture_protected": []})

    def test_candidate_protects_retained_names_before_install_and_filters_retired_names(self):
        skill = self.upstream / ".codex/skills/coding/SKILL.md"
        skill.parent.mkdir()
        skill.write_text("published candidate method")
        self.git("add", ".codex/skills/coding/SKILL.md")
        candidate = self.commit()
        marker = self.upstream / "operator-reenabled"
        marker.touch()
        request = dict(check=False, workspace_root=self.upstream, protect_exclusions=("removed", "coding"))
        with self.assertRaisesRegex(sync.SyncError, "protected preference was re-enabled"):
            self.run_release(candidate, **request)
        self.assertFalse((self.work / "home").exists())
        marker.unlink()
        result = self.run_release(candidate, **request)
        self.assertEqual(result["workspace"]["fixture_protected"], ["coding"])
        self.assertEqual(result["workspace"]["bundle_sha256"], result["bundle_sha256"])

    def test_invalid_protection_fails_before_fetch(self):
        for names in (["../private"], ["coding", "coding"], "coding", [f"a{i}" for i in range(129)]):
            with self.subTest(names=names), self.assertRaisesRegex(sync.SyncError, "Protected exclusions"):
                self.run_release(self.revision, workspace_root=self.upstream, protect_exclusions=names)
        self.assertFalse((self.work / "home").exists())

    def test_missing_workspace_reports_prior_install(self):
        with self.assertRaisesRegex(sync.SyncError, "installed. Workspace source exclusion remains pending"):
            self.run_release(self.revision, check=False, workspace_root=self.work / "missing")
        self.assertTrue((self.work / "home").is_dir())

    def test_setup_failure_distinguishes_completed_install(self):
        with patch("importlib.util.find_spec", return_value=object()):
            with self.assertRaisesRegex(sync.SyncError, "installed. Vault setup failed"):
                self.run_release(self.revision, check=False, vault_root=self.upstream)
        self.assertTrue((self.work / "home").is_dir())


if __name__ == "__main__":
    unittest.main()
