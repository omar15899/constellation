"""Run the public OmarOS helper entrypoints from the locked device distribution."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from ecosystem.hooks import HookError, check_vault_registration

# A requested script name, a test helper and a neighboring project file each
# have different authority. Only these public operations can select code.
RUNNERS = {
    ("fast-finder", "search"): "search.py",
    ("fast-finder", "query"): "query.py",
    ("engie-learning", "learning"): "learning.py",
    ("brainteasers-quant-notes", "context"): "context.py",
    ("brainteasers-quant", "production"): "production.py",
    ("brainteasers-quant", "engine"): "course_engine.py",
}
VAULT_SKILLS = {"fast-finder", "engie-learning"}
ISOLATED_ENTRY = (
    "import runpy, sys; from pathlib import Path; package, script, home, skill = sys.argv[1:5]; "
    "sys.path.insert(0, package); sys.argv = [script, *sys.argv[5:]]; "
    "main = runpy.run_path(script, run_name='_constellation_installed_helper')['main']; "
    "raise SystemExit(main(sys.argv[1:], device_home=Path(home)) if skill == 'engie-learning' else main())"
)


def _environment(home: Path, python: str) -> dict[str, str]:
    """Retain locale and user file locations, with device-owned executable lookup."""
    env = {key: value for key, value in os.environ.items()
           if key in {"HOME", "TMPDIR", "TMP", "TEMP", "LANG", "TZ"} or key.startswith("LC_")}
    paths = [str(Path(python).parent), "/usr/local/bin", *os.defpath.split(os.pathsep)]
    if sys.platform == "darwin":
        paths[1:1] = ["/opt/homebrew/bin", "/Library/TeX/texbin"]
    env.update(CODEX_HOME=str(home), PATH=os.pathsep.join(dict.fromkeys(paths)))
    return env


def _root_option(args: list[str]) -> tuple[str | None, list[str]]:
    """Consume one full --root option, keeping positional arguments and '--' intact."""
    result: list[str] = []
    root = None
    options = iter(args)
    for token in options:
        if token == "--":
            result.extend((token, *options))
            break
        key, equal, inline = token.partition("=")
        if key != "--root":
            if len(key) > 2 and "--root".startswith(key):
                raise ValueError("Spell the vault option --root in full.")
            result.append(token)
            continue
        value = inline if equal else next(options, "")
        if root is not None or not value or value.startswith("--"):
            raise ValueError("Supply --root once with the enrolled vault.")
        root = value
    return root, result


def _vault_arguments(home: Path, args: list[str], env: dict[str, str]) -> list[str]:
    selected, rest = _root_option(args)
    requested = Path(selected).absolute() if selected is not None else Path.cwd()
    if not requested.is_dir() or any(p.is_symlink() for p in (requested, *requested.parents)):
        raise ValueError("The selected vault directory must be a physical directory.")
    git = shutil.which("git", path=os.defpath)
    if git is None:
        raise ValueError("A system Git executable is required to identify the vault.")
    probe = subprocess.run([git, "--no-replace-objects", "-C", str(requested), "rev-parse", "--show-toplevel"],
                           env=env, text=True, capture_output=True, timeout=15)
    if probe.returncode:
        raise ValueError("Select the enrolled vault with --root.")
    owner = Path(probe.stdout.strip())
    if selected is not None and not requested.samefile(owner):
        raise ValueError("--root must select the enrolled Git owner.")
    binding = check_vault_registration(home, str(owner), require_bound=True)
    return ["--root", str(binding["root"]), *rest]


def entrypoint(home: Path, arguments: list[str]) -> int:
    """Dispatch a fixed installed helper while the parent holds the release lock."""
    if arguments == ["--help"]:
        print("Usage: run cli skill-run SKILL HELPER [arguments]")
        for skill, runner in sorted(RUNNERS):
            print(f"  {skill} {runner}")
        return 0
    try:
        if len(arguments) < 2 or tuple(arguments[:2]) not in RUNNERS:
            raise ValueError("Select an installed skill and its named public helper.")
        skill, runner, *args = arguments
        package = Path(__file__).resolve().parents[2]
        relative = f"skills/{skill}/scripts/{RUNNERS[skill, runner]}"
        inventory = json.loads((package / "bundle.json").read_text(encoding="utf-8"))
        if "omaros" not in inventory["modules"] or relative not in inventory["files"]:
            raise ValueError("The selected helper is unavailable in this installation.")
        script = package / relative
        receipt = json.loads((home / "constellation/receipt.json").read_text(encoding="utf-8"))
        python = receipt["python"]
        if receipt.get("schema") != 4 or not isinstance(python, str) or not Path(python).is_absolute():
            raise ValueError("The device interpreter is unavailable in the registered release.")
        env = _environment(home, python)
        if skill in VAULT_SKILLS:
            args = _vault_arguments(home, args, env)
        command = [python, "-I", "-B", "-c", ISOLATED_ENTRY, str(package), str(script), str(home), skill, *args]
        return subprocess.run(command, env=env).returncode
    except (OSError, KeyError, TypeError, ValueError, RuntimeError, HookError, subprocess.SubprocessError) as exc:
        print(f"Constellation skill helper: {exc}", file=sys.stderr)
        return 2
