#!/usr/bin/env python3
"""Install a portable bundle through Codex, preserving independently owned files."""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager, nullcontext
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import sys
import tempfile
import tomllib
from typing import Iterable, Iterator

sys.dont_write_bytecode = True
if __package__:
    from .build import (AVAILABLE_MODULES, BUNDLE_MANIFEST, PLUGIN_MANIFEST, BundleError, allowed_files,
                        build_bundle, check_profile, file_record, regular_file, select_modules,
                       verify_bundle)
    from .native import NativeClient, NativeError, PLUGIN_ID
    from . import platform_support as platform
    from . import install_recovery as recovery
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build import (AVAILABLE_MODULES, BUNDLE_MANIFEST, PLUGIN_MANIFEST, BundleError, allowed_files,
                       build_bundle, check_profile, file_record, regular_file, select_modules,
                       verify_bundle)
    from native import NativeClient, NativeError, PLUGIN_ID
    import platform_support as platform
    import install_recovery as recovery

CATALOG_MANIFEST = ".agents/plugins/marketplace.json"
PLUGIN_DIRECTORY = "plugins/constellation"


# Published, reproducible POSIX distributions eligible for *replacement*.
# Each digest binds the entire canonical bundle.json: modules, exact paths,
# modes and every file digest. These pins cannot authorize a fresh install
# or execute a prior bundle. Unknown historical variants need explicit
# recovery; never infer ownership from a version string or an untrusted list.
_PUBLISHED_PREDECESSORS = {
    "1.3.1": frozenset({
        # fad8261 (es); all nonempty subsets in canonical module order.
        "fafb4893d0f1456c02a9112075b8c216875d2417d84166df7202b2e9b4a96adb",
        "1dbef40be6cca941f47000a2c40d736748a3ac83fca7166e9c72c3bc26485245",
        "9ea095e68e0688c07a8b4f5d17595275cc670ac24bcc3bb3105cfabd80f8289a",
        "c3bddabae4bb18ae661b7c7c3eca5319e2cc4b080e542c6e33294dd30f8a30a8",
        "ccf00a3ebf3e3ac0d6e0ebccf25d8fa48ad55ac4c9b093ea1b5368e629cbf11e",
        "6e483e9b45e596d5752a1050ee6fbd87a7c3da9c3a7e0fa0953a04c63393b117",
        "c5cc807d76d762cf2edb9250530fd862685c5ac151aa7606588eb9672a9aea2c",
        "dcbca40105e409721393842fed2216755dfec395eb511ad0159967ee2d070067",
        "61b8edf7950dbb4301dce28420637de132d3f3c3d8fdfe1e430446b69a8cfbb4",
        "914b434ec24f71e09288315abdc4cec3bfcbf8a560e3d0f5c83cb70d3e8340fa",
        "2b572424ae4e0e17046da7ac590d7edb9e2cd7c591d17b2e097ac6897a3a1b25",
        "10aa09c6e5760cf1d648b552ad3039b63c2f8d59b93b8664abae0df5def142f7",
        "9cdc1f1c1bfa724f4b0a7db3fed90f9fc6fa4555321a7035c963bec7c460d5d2",
        "eabfd9f9a88410128d1273a73b89a862497fe0f63e098e77163841bfe37f53ea",
        "59b7ea06fef6086002a143938359443f257d054a3f9eb14a46b036170b504eb6",
        # 32ed58f (es); all nonempty subsets in canonical module order.
        "8cb74c1bce4de6001035a956f900c3daec6df5c72fa02d7cd99102bd2f64f89f",
        "ed7f908348de21488624988d97854b7e89a74a4c8533673b9447990db640f462",
        "7b03e4231a6958804c3553dd45833948a31092632cface84f0fc729ab54d8fd4",
        "6186c9dfa3c1d97012a9431936a916d3d20b7076344183b88ad8253e7acf5ca4",
        "6321897200ec8535d2f767f1649d47674ee64fc3845f8396b12a318f7ed19bdc",
        "d33b671ff79233672c306f90218e97a681c9c5973bf28c6fdaf787360b8aa2fb",
        "74ec08c4360b488040b996e5da4b45b19045b394f24d3ed002219710d644e1c4",
        "49e1aa10c01354bd2f40a340e40a273c5fa32607fe7e266b9ee5b92d1500c593",
        "67c6165ab929e943768dce862171489d515a9e55997c40ad5de9608074f853f6",
        "3df77b41cdc410e0da109c68921e84434d18abe3cde32feab63c44bbf9de67d4",
        "a53cdb7626be6ded1f74b7844ba136e3611ccb0d47a40155f5356bd9879c7f2d",
        "b1c9d8bcc66259f27fec8814bdd0602f8aec95adafad61e3fe7d758a81bc668c",
        "d186c46b628ecde3225566e91d3a242b85f019e609948975f3db496bef49d871",
        "4cd2d016dc916d242a4c22436d0f0160da50c2e79890901ed3277123c33bba2c",
        "e7b1df80d09a983d3e9d21e0292725da9c6686b9888a7ae9356146b95053ee1f",
    }),
    "1.4.0-rc.1": frozenset({
        # fd82492 (es); all nonempty subsets in canonical module order.
        "cedc8a430764b6b948a36a361e8eb91d5f75377d4e1ec5f050300b078419c512",
        "d84fc332d9940b4691337b5dab80c871ed38d4361d199ff07d815c0ef22bc64e",
        "20182c1337d54c8a79a0bbce90a1de138d1e4da4a9f7de58835213a8af1d57b5",
        "7164b314f9d3e94adc848c58a299f54a963475125394cea17a672eade6d38131",
        "dc87e4b6fee2478200ca297551c154f165f9ae4aceb6c65f01ee7428e7b197e6",
        "c1159c4f1338482aa4b0aca724d4fa955f652473115a3f4adae3d86248b6043a",
        "d665383275d78950dc2abcf47587df15ed48d54865380aa0911d36a8d324c2fd",
        "04d3509de2f5264010aef6ba2dbc842332bf1f89ceb62a9a0f4258ca99ebc8d2",
        "38d441e06bf54e6b4a8747b3c166e314be5879f38f9443fa3b4d7fd86ffc06b1",
        "2927e1ad84abcc4c18a43a395742fe50c2fbe5c1904b915b0742ccc30fd8ec63",
        "e8dd5febf1ad4766f7ef4dd5c76440afc22321878df09a5278a535f398b8e484",
        "ebb2e482bae1549ba3e447ee9e40ad5e5aaddf355e781501558e6a3c22b01425",
        "33fcff732a49e0abcbae8c048e7a13a4a496ea4300d77c384aca0cd17771596f",
        "09b701d20c0dc7fe81c4a7cf3242fefbabde071fca5527353960272ea9f9e941",
        "6e9f784c8fe7fe4f1e96f7369435c5e437d60f88b70dbbde321285afd6542999",
        # fd82492 (en); all nonempty subsets in canonical module order.
        "88169814ac15b4b1a707c4951201efc9fdda6496eec9d984f888306d418734bd",
        "06179a26ed739765d822c85a2c2f90da720c3c03d07e4cbb01e0e036ba513150",
        "b4aa7642eb4e7831a846bc2580094e64c7fe4f5318f4b548e488d1c6cda223c7",
        "fa98cb177a748ed9a9f4c57e022e09a45ec4327dc353adb1b4b6846e49436bb4",
        "2692b3dd568eb404e2af2a38036c40bde41b6e536686aaf3658b0858ec4a15f8",
        "7e458077a12c75146e458820bd7d3171bbec638c53712f268410aed806a0fd2d",
        "5e2a98c856ecc073a463172ca231adf878e0bbc56ec9ded34efaf51e4bde7a2b",
        "84c0c45a73996366062a739a9ec31315b0612ba18afc106c787ecd77d2769779",
        "d96c547ea1e05acabf11f085c77e6711ab928f0c80902822238f1fcc2aef6dbb",
        "b9cafca87788a3c4dd50bcace809b53f3fefe0a36b1524647e0e3f7b2384fdb3",
        "67b379337ccfe1bc8ebe1fd387fc661a76fc7057242c5682843a0440b4bde148",
        "eed96211419bb0d00ad6d91aa013a6684c897f210c6a29934096868c684d364c",
        "73553ec5f37dfd56263b62fcaf925673a1c2ce23d705c815cda75a70cd507699",
        "5fb709f124408565a0d5eac4ba0caea7f0f7360e8b10d482cc69c25df9f3f36b",
        "dd368712b45f7ac48b89cfc6ba5ed8ea1c327f357589c12529d2662926a090b3",
        # 68b96ba (es); all nonempty subsets in canonical module order.
        "192aa38946948dacc2e0ca530222e50ecad5533dd18fa82653da311a5018a25c",
        "fc793be4fa77d000f7ae943dbc3d2153fc6c2649aed61f1eb3521706e0023753",
        "fc45b9df28d247a9e77aa7a4941c90b9513cd38364ea0df5bcfabba1eb8ce0ed",
        "e4c674e37ae746e9e41fe4b61f52f35fd70dd9f29971e03d63d729a6e6d8b630",
        "72df4346386f36d78ba104efca40c4961eea3d150b4146aa1e2884164e88c80b",
        "6d26419599d160184649be37773591c8f71b459066254e17202217ced8526da8",
        "7616453d9806753011f8b6efe05f09bc158cc91f3f16321d9b292aa74be9bb2a",
        "806c0fe3c6b308138d4bfb48f8b82dbfdde94fcc2e64a223d3f065ea20b4a454",
        "501225297fc74b0f927dc2d1653946306c93e6aa1fa7ed47a2f23d1db6bcb0ac",
        "ec75972554501a010bb189718815dd8e5a09b95fd46d0c21de67f2270649758a",
        "a30df73d78094f92843043ce20bf4bc5321780f68d895c22508eb506726cc21e",
        "6ad544af18481fb74d6b3b42bbc0ace89531766a65d5ede1b6edf92b5c1242f7",
        "9f64cb2e394aceac179684c3d7b4abfaf0434672aaeeb1e58f70992775713c03",
        "c6f546d4f2dd5a840d7f7c8a3e7ac1719f70694c551e90f87c68805397beeefc",
        "37298dd6d4404ae5cf0a1f9cd30e9d89e4285114abc8315e16782354217f2c5c",
        # 68b96ba (en); all nonempty subsets in canonical module order.
        "7c2fe007fb4659cbb2449c215c46edf6f1d8bcb7c858e61b320f73ab107eb521",
        "8575d90dd56e5b1280a3cddc4a5c53164297b49cdcce0d53cba403c1d625ba74",
        "d44233d2cd3c5c47887cdb8b3b43638463454b4ecbe403bd4770939e9e90bd2c",
        "9678a846028e7b1c74a3a0b4b857bd2c871ec25d566be362edc9d2787d8c0e62",
        "49002c9d3183e52788e14a650f0ab200aecc5d3078b8e389de534476c4ed7971",
        "ec1d6b8f193952df95ff33b570cba24c492e998942d045f3b563b57a95eb1af7",
        "677a9aca928cb3f3a732a9ec6ba8816ce41052d728f06d161171602c5eddfec9",
        "dd4b56ff2fb8f0d9036fd50653bb3974f636f57c5b70e31871e1b32737ae214c",
        "5a8a8e83eec324a4644aa185aea6d33e38c404ed03513982c13fd37a8317cc13",
        "e85d81302078fa61c6801a2dcb614b0b7d5efbe576e32ac80049e274d2636a34",
        "5a9db0fa60165388762e02141ff611b8ec5915216e1ef611b7ec617f15615793",
        "8921bb5fcef09c9dc2ef59212d4e5da9342c65eec948e5652b34aabf692d9cd5",
        "e1759d729a601b5cb8c14041abc080a377cc0c3e6178ff417f0c69cfa8753d1e",
        "0c5232505d6a678448195211c6be89abbb53704f1525eaaaa0a4579c39fbc82b",
        "1edde3665eb7e8e49838d68fae1c247a7b79e434ba4ad4672b8a8c717db414c1",
    }),
}


def _historical_receipt(receipt: dict, records: dict) -> bool:
    """Recognize only intact, published prior ownership manifests."""
    pins = _PUBLISHED_PREDECESSORS.get(receipt["version"])
    if pins is None:
        return False
    recorded = receipt["cache"].get(BUNDLE_MANIFEST, {})
    if recorded.get("sha256") not in pins or recorded.get("mode") != 0o644:
        raise ValueError("unrecognized historical distribution")
    manifest = {"schema": 1, "modules": receipt["modules"], "files": records}
    serialized = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if hashlib.sha256(serialized).hexdigest() != recorded["sha256"]:
        raise ValueError("recorded historical resources differ from published distribution")
    return True


def _marketplace() -> dict:
    """One local plugin entry, also required before restoring a registration."""
    return {"name": "constellation", "plugins": [{
        "name": "constellation", "source": {"source": "local", "path": "./plugins/constellation"},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Productivity"}]}


class InstallError(ValueError):
    """Installation is unsafe, conflicted or could not be verified."""


def _safe_anchor(path: Path) -> Path:
    if platform.is_reparse(path):
        raise InstallError(f"Managed path is a symlink: {path.name}")
    return path.resolve()


def _no_links(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise InstallError("Invalid managed path")
    current = root
    for part in path.parts:
        current /= part
        if platform.is_reparse(current):
            raise InstallError(f"Managed path is a symlink: {relative}")
    return current


def _inventory(root: Path) -> dict:
    if platform.is_reparse(root) or not root.is_dir():
        raise InstallError("Managed directory is missing or linked")
    files = {}
    for directory, subdirs, names in os.walk(root, followlinks=False):
        for name in subdirs + names:
            if platform.is_reparse(Path(directory) / name):
                raise InstallError("Managed directory contains a symlink")
        for name in names:
            path = Path(directory) / name
            if not stat.S_ISREG(path.stat().st_mode):
                raise InstallError("Managed directory contains a non-regular file")
            files[path.relative_to(root).as_posix()] = file_record(path)
    return dict(sorted(files.items()))


def _require_observed_receipt(home: Path, expected: str | None) -> None:
    """Refuse a proposal made against a different installed release.

    The sync command records this digest before selecting or fetching a
    candidate. Install compares it again while owning the exclusive device
    lock, so a slow sync cannot replace another sync's newer selection.
    """
    if expected is None:
        return
    if not isinstance(expected, str) or not (expected == "absent" or re.fullmatch(r"[0-9a-f]{64}", expected)):
        raise InstallError("Expected receipt must be 'absent' or a lowercase SHA-256 digest")
    path = _no_links(home, "constellation/receipt.json")
    try:
        descriptor = platform.open_regular(path, os.O_RDONLY | os.O_NONBLOCK, private=True)
    except FileNotFoundError:
        actual = "absent"
    else:
        with os.fdopen(descriptor, "rb") as receipt:
            actual = hashlib.file_digest(receipt, "sha256").hexdigest()
    if actual != expected:
        raise InstallError("Installation receipt changed since the release was selected. Run sync again.")


def _load_receipt(path: Path, *, home: Path | None = None) -> dict | None:
    """Accept the current device receipt or an attested pre-launcher installation."""
    if platform.is_reparse(path):
        raise InstallError("Installation receipt cannot be a symlink")
    if not path.exists():
        return None
    if not path.is_file():
        raise InstallError("Installation receipt must be a regular file")
    try:
        platform.verify_access(path, private=True)
        value = _read_object(path)
        fields = {"schema", "modules", "version", "catalog", "cache", "agents", "hook"}
        if value.get("schema") == 4:
            fields.update(("launcher", "python", "python_target"))
        if (set(value) != fields or type(value.get("schema")) is not int
                or value["schema"] not in (3, 4)):
            raise ValueError("unsupported ownership schema")
        if (not isinstance(value["modules"], list)
                or not all(isinstance(module, str) for module in value["modules"])):
            raise ValueError("modules")
        modules = select_modules(value["modules"])
        if (not isinstance(value["version"], str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", value["version"])):
            raise ValueError("version")
        for group in ("catalog", "cache", "agents"):
            _check_records(value[group])
        _check_records({"hook.py": value["hook"]})
        if (value["hook"]["mode"] != 0o644
                or value["hook"]["sha256"] !=
                value["cache"].get("ecosystem/hook_entry.py", {}).get("sha256")):
            raise ValueError("stable hook and catalog differ")
        resources = {p: r for p, r in value["cache"].items() if p != BUNDLE_MANIFEST}
        if value["schema"] == 3:
            if not _historical_receipt(value, resources):
                raise ValueError("unrecognized pre-launcher installation")
            files = set(resources)
        else:
            if value["version"] in _PUBLISHED_PREDECESSORS:
                raise ValueError("published predecessor requires its original ownership schema")
            launcher = _launcher_content(value["python"], home or path.parent.parent, value["python_target"],
                                        value["hook"]["sha256"])
            if (not isinstance(value["launcher"], dict) or type(value["launcher"].get("mode")) is not int
                    or value["launcher"] != _launcher_record(launcher)):
                raise ValueError("launcher record differs from the recorded interpreter and home")
            files = allowed_files(modules)
        if set(value["cache"]) != files | {BUNDLE_MANIFEST}:
            raise ValueError("recorded release resources")
        expected_catalog = {f"{PLUGIN_DIRECTORY}/{p}" for p in files | {BUNDLE_MANIFEST}}
        expected_catalog.add(CATALOG_MANIFEST)
        if set(value["catalog"]) != expected_catalog:
            raise ValueError("catalog")
        expected_agents = {"constellation-" + Path(p).name for p in files
                           if p.startswith("ecosystem/agents/")}
        if set(value["agents"]) != expected_agents:
            raise ValueError("agents")
        if any(record != value["catalog"][f"{PLUGIN_DIRECTORY}/{relative}"]
               for relative, record in value["cache"].items()):
            raise ValueError("cache and catalog differ")
        # Native profiles have one normalized projection, independently of the
        # executable flag carried by their packaged source.
        if any(record["mode"] != 0o644 or record["sha256"] !=
               value["cache"]["ecosystem/agents/" + name.removeprefix("constellation-")]["sha256"]
               for name, record in value["agents"].items()):
            raise ValueError("agent and catalog differ")
        return value
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise InstallError("Invalid installation receipt; no files were changed") from exc



def _read_object(path: Path) -> dict:
    def unique(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate mapping key")
            result[key] = value
        return result

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError("expected mapping")
    return value


def _check_records(value: object) -> None:
    if not isinstance(value, dict):
        raise ValueError("expected file records")
    for relative, record in value.items():
        if (not isinstance(relative, str) or not isinstance(record, dict)
                or set(record) != {"sha256", "mode"}
                or not isinstance(record["sha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
                or type(record["mode"]) is not int or record["mode"] not in (0o644, 0o755)):
            raise ValueError("invalid file record")


def _verify_recorded_bundle(root: Path, receipt: dict) -> None:
    """Bind the owned inventory to the previous release's declared metadata."""
    try:
        manifest = _read_object(root / BUNDLE_MANIFEST)
        expected = {p: record for p, record in receipt["cache"].items() if p != BUNDLE_MANIFEST}
        if (set(manifest) != {"schema", "modules", "files"}
                or type(manifest.get("schema")) is not int or manifest["schema"] != 1
                or manifest.get("modules") != receipt["modules"] or manifest.get("files") != expected):
            raise ValueError("bundle manifest differs from receipt")
        plugin = _read_object(root / PLUGIN_MANIFEST)
        if plugin.get("name") != "constellation" or plugin.get("version") != receipt["version"]:
            raise ValueError("plugin manifest differs from receipt")
        if _historical_receipt(receipt, expected):
            # _preflight already bound catalog and cache bytes and modes to
            # this receipt. Check physical access and links before replacement.
            for directory, _, _ in os.walk(root, followlinks=False):
                platform.verify_access(Path(directory), private=False)
            for relative in receipt["cache"]:
                regular_file(root, relative)
        else:
            verify_bundle(root)
    except (OSError, ValueError, TypeError) as exc:
        raise InstallError("Owned bundle metadata differs from the installation receipt") from exc


def _cache_root(home: Path, version: str) -> Path:
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", version):
        raise InstallError("Native plugin has an invalid version")
    return _no_links(home, f"plugins/cache/constellation/constellation/{version}")


def _disabled_in_config(home: Path) -> bool:
    path = _no_links(home, "config.toml")
    if not path.exists():
        return False
    try:
        with path.open("rb") as stream:
            config = tomllib.load(stream)
        plugin = config.get("plugins", {}).get(PLUGIN_ID, {})
        return plugin.get("enabled") is False
    except (OSError, ValueError, AttributeError) as exc:
        raise InstallError("Cannot safely read the native plugin enablement setting") from exc


def _registered(client: NativeClient, catalog: Path) -> tuple[bool, dict | None]:
    markets = [row for row in client.marketplaces() if row.get("name") == "constellation"]
    if len(markets) > 1:
        raise InstallError("Native marketplace registration is ambiguous")
    if markets:
        origin = markets[0].get("marketplaceSource", {})
        if (origin.get("sourceType") != "local" or not isinstance(origin.get("source"), str)
                or Path(origin["source"]).resolve() != catalog):
            raise InstallError("Marketplace constellation belongs to another source")
    plugins = [row for row in client.plugins(marketplace="constellation") if row.get("pluginId") == PLUGIN_ID]
    if len(plugins) > 1:
        raise InstallError("Native plugin registration is ambiguous")
    plugin = plugins[0] if plugins else None
    if plugin is not None and plugin.get("enabled") is not True:
        raise InstallError("The plugin is disabled; preserve that decision and enable it explicitly in Codex")
    return bool(markets), plugin


def _preflight(home: Path, selected: tuple[str, ...], client: NativeClient,
               *, query_native: bool = True) -> tuple[dict | None, bool, dict | None]:
    binding = home / "constellation-vault.json"
    if "omaros" not in selected and (platform.is_reparse(binding) or binding.exists()):
        raise InstallError("This device has an OmarOS vault registration. Select the personal profile "
                           "including omaros to preserve its Git guards.")
    managed = _no_links(home, "constellation")
    catalog = _no_links(home, "constellation/catalog")
    receipt = _load_receipt(_no_links(home, "constellation/receipt.json"))
    if managed.exists():
        if not managed.is_dir():
            raise InstallError("Installation directory is not a directory")
        # The runtime owns state independently; installation never traverses it.
        if any(p.name not in {"catalog", "receipt.json", ".install.lock", "state", "hook.py", "run", ".transition"}
               for p in managed.iterdir()):
            raise InstallError("Installation directory contains independently owned files")
    entry = _no_links(home, "constellation/hook.py")
    if receipt is not None:
        if not entry.is_file() or file_record(entry) != receipt["hook"]:
            raise InstallError("Stable hook entry was modified or is missing")
    elif entry.exists():
        raise InstallError("Stable hook entry belongs to another owner")
    launcher = _no_links(home, "constellation/run")
    if receipt and receipt["schema"] == 4:
        if (not launcher.is_file() or
                file_record(regular_file(managed, "run")) != receipt["launcher"]):
            raise InstallError("Installed native launcher was modified or is missing")
    elif launcher.exists():
        raise InstallError("Native launcher belongs to another owner")
    if _disabled_in_config(home):
        raise InstallError("The plugin is disabled; preserve that decision and enable it explicitly in Codex")
    cache_parent = _no_links(home, "plugins/cache/constellation/constellation")
    if cache_parent.exists():
        if not cache_parent.is_dir():
            raise InstallError("Native cache destination is not a directory")
        expected_versions = {receipt["version"]} if receipt else set()
        if {p.name for p in cache_parent.iterdir()} != expected_versions:
            raise InstallError("Native cache contains files outside the installation receipt")
    registered, plugin = _registered(client, catalog) if query_native else (False, None)
    if receipt is None:
        if catalog.exists() or registered or plugin is not None:
            raise InstallError("Existing installation has no ownership receipt")
    else:
        if not registered or plugin is None or plugin.get("version") != receipt["version"]:
            raise InstallError("Native registration differs from the installation receipt")
        if _inventory(catalog) != receipt["catalog"]:
            raise InstallError("Catalog was modified; preserve its files before updating")
        if _inventory(_cache_root(home, receipt["version"])) != receipt["cache"]:
            raise InstallError("Native cache was modified; preserve its files before updating")
        if _read_object(regular_file(catalog, CATALOG_MANIFEST)) != _marketplace():
            raise InstallError("Managed marketplace no longer points at the owned local bundle")
        _verify_recorded_bundle(catalog / PLUGIN_DIRECTORY, receipt)
        for name, record in receipt["agents"].items():
            path = _no_links(home, "agents/" + name)
            if not path.is_file() or file_record(path) != record:
                raise InstallError(f"Installed agent was modified: {name}")
    existing_agents = set(receipt["agents"]) if receipt else set()
    agents_dir = _no_links(home, "agents")
    if agents_dir.exists() and not agents_dir.is_dir():
        raise InstallError("Agent destination is not a directory")
    for relative in allowed_files(selected):
        if relative.startswith("ecosystem/agents/"):
            name = "constellation-" + Path(relative).name
            target = _no_links(home, "agents/" + name)
            if target.exists() and name not in existing_agents:
                raise InstallError(f"Agent destination belongs to another owner: {name}")
    return receipt, registered, plugin


@contextmanager
def _lock(home: Path) -> Iterator[int]:
    managed = _no_links(home, "constellation")
    platform.secure_mkdir(managed, mode=0o700, parents=True, exist_ok=True)
    path = _no_links(home, "constellation/.install.lock")
    descriptor = platform.open_regular(path, os.O_CREAT | os.O_RDWR, 0o600, private=True)
    try:
        with ExitStack() as acquired:
            try:
                acquired.enter_context(platform.file_lock(descriptor, exclusive=True, blocking=False))
            except BlockingIOError as exc:
                raise InstallError("A Constellation installation or hook is running; retry after it finishes") from exc
            try:
                yield descriptor
            except recovery.RecoveryError as exc:
                raise InstallError(f"Device transition needs attention. {exc}") from exc
    finally:
        os.close(descriptor)


def _replace_bytes(path: Path, content: bytes, mode: int) -> None:
    """Atomically replace one owned entry without following its old inode.

    The temporary file is created with its final privacy policy, including a
    protected DACL on Windows. The old entry remains intact until the new bytes
    and metadata have been flushed.
    """
    temporary = path.parent / (".constellation-" + secrets.token_hex(16))
    descriptor = platform.open_regular(
        temporary, os.O_CREAT | os.O_EXCL | os.O_RDWR, mode,
        private=not bool(mode & 0o077))
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            platform.set_access(temporary, mode)
            stream.flush()
            platform.sync_file(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _launcher_content(python: str, home: Path, python_target: str, hook_sha256: str) -> bytes:
    # The stable bootstrap and installer use exactly one shell representation.
    # This POSIX bootstrap imports fcntl; the Windows Codex installer rejects
    # before this point, and the separate Claude installer has its own contract.
    if __package__:
        from .hook_entry import launcher_bytes
    else:
        from hook_entry import launcher_bytes
    return launcher_bytes(python, home, python_target, hook_sha256)


def _launcher_record(content: bytes) -> dict:
    return {"sha256": hashlib.sha256(content).hexdigest(), "mode": 0o700}


class LauncherConflict(InstallError):
    """Launcher ownership changed during promotion; preserve data for recovery."""


def _generation_position(path: Path, known_ids: set[tuple[int, int]], *, allow_linked: bool):
    """Identify a generation without reading an independently placed file."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    identity = info.st_dev, info.st_ino
    if identity not in known_ids:
        return identity, None
    if not stat.S_ISREG(info.st_mode) or (not allow_linked and info.st_nlink != 1):
        raise LauncherConflict(f"Preserve linked or non-regular device generation at {path}")
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        opened = os.fstat(fd)
        if not os.path.samestat(info, opened):
            raise LauncherConflict(f"Device generation changed before hashing {path}")
        record = {"mode": stat.S_IMODE(opened.st_mode), "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}
        if not os.path.samestat(opened, path.lstat()):
            raise LauncherConflict(f"Device generation changed during validation at {path}")
    return identity, record


def _switch_generations(live: Path, image: Path, old_pos, new_pos, *, forward: bool | None,
                        allow_linked: bool = False) -> None:
    """Switch journaled inodes without overwriting a foreign winner.

    An exchange leaves both inodes at known names even on process death. The
    first generation uses an exclusive move. Either direction is idempotent,
    and any unknown state retains the journal and displaced entries.
    """
    before = (old_pos, new_pos)
    same_record = old_pos and new_pos and old_pos[1] == new_pos[1]
    after = before if same_record else (new_pos, old_pos)
    source, target = (before, after) if forward else (after, before)
    ids = {pos[0] for pos in before if pos is not None}

    def positions():
        return (_generation_position(live, ids, allow_linked=allow_linked),
                _generation_position(image, ids, allow_linked=allow_linked))

    def flush():
        platform.sync_directory(live.parent)
        platform.sync_directory(image.parent)

    actual = positions()
    if forward is None:
        if actual not in (before, after):
            raise LauncherConflict(f"Device generation differs from journaled identities. Preserve {image.parent}")
        return
    if actual == target:
        return
    if actual != source:
        raise LauncherConflict(f"Device generation differs from journaled identities. Preserve {image.parent}")
    exchange = old_pos is not None and new_pos is not None
    if exchange:
        platform.exchange_files(image, live)
    else:
        stage, destination = (live, image) if source[0] is not None else (image, live)
        platform.promote_file(stage, destination)
    flush()
    actual = positions()
    if actual != target:
        # If a writer raced the kernel operation, put the displaced generation
        # back when its counterpart is still ours. Every move keeps all bytes,
        # and the transaction is retained even if a further writer intervenes.
        if exchange and actual[0] == target[0] and actual[1] is not None:
            platform.exchange_files(image, live)
            flush()
        elif not exchange and not stage.exists() and not stage.is_symlink():
            platform.promote_file(destination, stage)
            flush()
        raise LauncherConflict(f"Generation changed during atomic promotion. Preserve {image.parent}")


def _publish_receipt(home: Path, txn: Path, old: dict | None, new: dict,
                     old_receipt_id, new_receipt_id, *, forward: bool) -> None:
    """Switch the receipt itself with the same ownership rules as the launcher."""
    old_pos = None
    if old is not None:
        record = file_record(regular_file(txn, "old-receipt.json"))
        old_pos = (tuple(old_receipt_id), record)
    new_pos = (tuple(new_receipt_id), file_record(regular_file(txn, "new-receipt.json")))
    _switch_generations(home / "constellation/receipt.json", txn / "receipt-image", old_pos, new_pos, forward=forward)


def _activate_device(home: Path, txn: Path, old: dict | None, new: dict, old_id, new_id,
                     old_receipt_id, new_receipt_id, *, forward: bool) -> None:
    old_pos = (tuple(old_id), old["launcher"]) if old_id is not None else None
    new_pos = (tuple(new_id), new["launcher"])
    _switch_generations(home / "constellation/run", txn / "launcher-image", old_pos, new_pos, forward=forward)
    _publish_receipt(home, txn, old, new, old_receipt_id, new_receipt_id, forward=forward)


def commit_launcher(home: Path, path: Path, old: dict | None, new: dict,
                    old_id, new_id, old_receipt_id, new_receipt_id) -> None:
    _activate_device(home, path, old, new, old_id, new_id, old_receipt_id, new_receipt_id, forward=True)


def restore_launcher(home: Path, path: Path, old: dict | None, new: dict,
                     old_id, new_id, old_receipt_id, new_receipt_id) -> None:
    _activate_device(home, path, old, new, old_id, new_id, old_receipt_id, new_receipt_id, forward=False)


def install_bundle(bundle: Path, codex_home: Path, modules: Iterable[str] | None = None,
                   check: bool = False, client: NativeClient | None = None, *,
                   expected_receipt_sha256: str | None = None) -> dict:
    """Install or update one plugin; compensate failures through native commands.

    ``check`` performs validation and conflict detection without staging files.
    The injected client permits filesystem-realistic tests without Codex.
    An optional expected receipt hash (or "absent") binds a proposal to
    the installed state observed before fetching the candidate. A mismatch
    requires a fresh selection. Native caches and trust settings are never written directly.
    """
    if platform.IS_WINDOWS:
        raise InstallError("Native Windows installation is supported by the Claude installer only; "
                           "Codex Windows is outside this release's acceptance.")
    bundle = Path(bundle)
    manifest = verify_bundle(bundle)
    bundle = bundle.resolve()
    selected = select_modules(manifest["modules"] if modules is None else modules)
    check_profile(selected, "posix")
    if not set(selected) <= set(manifest["modules"]):
        raise InstallError("Requested modules are absent from this bundle")
    home = _safe_anchor(Path(codex_home))
    managed = home / "constellation"
    python = sys.executable
    if not Path(python).is_absolute() or not Path(python).is_file() or not os.access(python, os.X_OK):
        raise InstallError("The installing Python executable must be a usable regular file")
    python_target = str(Path(python).resolve(strict=True))
    try:
        launcher_content = _launcher_content(python, home, python_target,
                                             manifest["files"]["ecosystem/hook_entry.py"]["sha256"])
    except ValueError as exc:
        raise InstallError("Cannot bind the native launcher to this Python interpreter") from exc
    if bundle == managed or managed in bundle.parents or bundle in managed.parents:
        raise InstallError("Bundle and installation directory must not overlap")
    backend = client or NativeClient(home, cwd=home if home.exists() else bundle)
    if check and recovery.pending(home):
        return {"status": "recovery_required", "modules": list(selected), "update": True,
                "catalog": str(managed / "catalog")}
    if not recovery.pending(home):
        _require_observed_receipt(home, expected_receipt_sha256)
        _preflight(home, selected, backend, query_native=home.exists())
        if check:
            receipt = _load_receipt(managed / "receipt.json")
            return {"status": "checked", "modules": list(selected), "update": receipt is not None,
                    "catalog": str(managed / "catalog")}
    if check:  # Another installation may have started during inspection.
        return {"status": "recovery_required", "modules": list(selected), "update": True,
                "catalog": str(managed / "catalog")}
    with _lock(home) as lock_fd, (backend.inherit_install_lock(lock_fd)
                                  if isinstance(backend, NativeClient) else nullcontext()):
        if recovery.pending(home):
            tx = recovery.load(home, validate_receipt=_receipt_at, switch_file=_switch_generations)
            tx.settle(backend, preflight=_preflight, restore_launcher=restore_launcher,
                      registered=_registered, disabled=_disabled_in_config)
        _require_observed_receipt(home, expected_receipt_sha256)
        receipt, registered, _ = _preflight(home, selected, backend)
        with tempfile.TemporaryDirectory(prefix="constellation-install-") as temporary:
            work = Path(temporary).resolve()
            catalog = work / "catalog"
            payload = catalog / PLUGIN_DIRECTORY
            payload.parent.mkdir(parents=True)
            build_bundle(payload, selected, bundle)
            market = catalog / CATALOG_MANIFEST
            market.parent.mkdir(parents=True)
            market.write_text(json.dumps(_marketplace(), sort_keys=True, indent=2) + "\n", encoding="utf-8")
            market.chmod(0o644)
            cache = _inventory(payload)
            agents = {"constellation-" + Path(relative).name: {"mode": 0o644, "sha256": record["sha256"]}
                      for relative, record in cache.items() if relative.startswith("ecosystem/agents/")}
            desired = {"schema": 4, "modules": list(selected),
                       "version": _read_object(payload / PLUGIN_MANIFEST)["version"],
                       "catalog": _inventory(catalog), "cache": cache, "agents": agents,
                       "hook": {"mode": 0o644, "sha256": cache["ecosystem/hook_entry.py"]["sha256"]},
                       "python": python, "python_target": python_target, "launcher": _launcher_record(launcher_content)}
            def result(status: str) -> dict:
                return {"status": status, "modules": list(selected), "version": desired["version"],
                        "agents": sorted(agents), "catalog": str(managed / "catalog"),
                        "hook_entry": str(managed / "hook.py"), "launcher": str(managed / "run"),
                        "hooks": "Native hook trust is managed by Codex."}
            if receipt == desired:
                return result("current")
            _preflight(home, selected, backend)
            tx = recovery.prepare(home, receipt, desired, catalog, launcher_content,
                                  validate_receipt=_receipt_at, switch_file=_switch_generations)
            try:
                if receipt is None or receipt["catalog"] != desired["catalog"]:
                    tx.publish_catalog()
                    if not registered:
                        backend.add_marketplace(managed / "catalog")
                    backend.add_plugin()
                    _, installed = _registered(backend, managed / "catalog")
                    if installed is None or installed.get("version") != desired["version"]:
                        raise InstallError("Native installation did not confirm the expected version")
                    if _inventory(_cache_root(home, desired["version"])) != cache:
                        raise InstallError("Native cache differs from the verified bundle")
                    tx.publish_files()
                commit_launcher(home, tx.path, tx.old, tx.new, tx.old_id, tx.new_id,
                                tx.old_receipt_id, tx.new_receipt_id)
                _preflight(home, selected, backend)
            except Exception as failure:
                try:
                    tx.rollback(backend, preflight=_preflight, restore_launcher=restore_launcher,
                                registered=_registered, disabled=_disabled_in_config)
                except Exception as repair:
                    raise InstallError("Installation failed; rollback needs attention. "
                                       f"Preserve device transition at {tx.path}: {repair}") from failure
                raise InstallError("Installation failed; previous owned files and registration restored") from failure
            tx.close()
            return result("updated" if receipt else "installed")


def _receipt_at(path: Path, home: Path) -> dict | None:
    receipt = _load_receipt(path, home=home)
    if receipt is not None:
        side = {"old-receipt.json": "old", "new-receipt.json": "new"}.get(path.name)
        if side is None:
            raise InstallError("Unrecognized journal receipt path")
        catalog = path.parent / f"{side}-catalog"
        if _read_object(regular_file(catalog, CATALOG_MANIFEST)) != _marketplace():
            raise InstallError("Journal marketplace differs from the owned local source")
        _verify_recorded_bundle(catalog / PLUGIN_DIRECTORY, receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--codex-home", type=Path, required=True)
    parser.add_argument("--modules", nargs="+", choices=AVAILABLE_MODULES)
    parser.add_argument("--expected-receipt-sha256", metavar="DIGEST_OR_ABSENT",
                        help="Require this pre-fetch installation receipt under the exclusive lock")
    parser.add_argument("--check", "--dry-run", action="store_true")
    parser.add_argument("--codex", default="codex")
    args = parser.parse_args(argv)
    try:
        home = args.codex_home.resolve()
        client = NativeClient(home, args.codex, cwd=home if home.exists() else args.bundle.resolve())
        result = install_bundle(args.bundle, args.codex_home, args.modules, args.check, client,
                                expected_receipt_sha256=args.expected_receipt_sha256)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (InstallError, BundleError, NativeError, OSError) as exc:
        parser.exit(1, f"Installation rejected: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
