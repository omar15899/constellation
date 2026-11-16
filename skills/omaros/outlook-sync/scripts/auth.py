from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import msal

from config import (
    AUTHORITY_TEMPLATE,
    SCOPES,
    TOKEN_CACHE_PATH,
    OutlookConfig,
    load_config,
    save_config,
)


def _load_cache() -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    if TOKEN_CACHE_PATH.exists():
        cache.deserialize(TOKEN_CACHE_PATH.read_text(encoding="utf-8"))
    return cache


def _persist_cache(cache: msal.SerializableTokenCache) -> None:
    if not cache.has_state_changed:
        return
    TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE_PATH.write_text(cache.serialize(), encoding="utf-8")
    os.chmod(TOKEN_CACHE_PATH, 0o600)


def _build_app(cfg: OutlookConfig, cache: msal.SerializableTokenCache) -> msal.PublicClientApplication:
    return msal.PublicClientApplication(
        cfg.client_id,
        authority=AUTHORITY_TEMPLATE.format(tenant=cfg.tenant),
        token_cache=cache,
    )


def _username_from_result(result: dict) -> str | None:
    claims = result.get("id_token_claims") or {}
    for key in ("preferred_username", "email", "upn"):
        value = claims.get(key)
        if value:
            return value
    return None


def _login(cfg: OutlookConfig) -> int:
    cache = _load_cache()
    app = _build_app(cfg, cache)

    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError(
            f"Failed to initiate device flow: {flow.get('error_description', flow)}"
        )

    print(flow["message"], flush=True)

    result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        error = result.get("error_description") or result.get("error") or result
        print(f"Authentication failed: {error}", file=sys.stderr)
        return 1

    _persist_cache(cache)

    username = _username_from_result(result)
    if username:
        cfg.username = username
    save_config(cfg)

    account_label = username or "(unknown account)"
    print(f"Authentication succeeded for {account_label}.")
    print(f"Token cache written to {TOKEN_CACHE_PATH}.")
    return 0


def _status(cfg: OutlookConfig) -> int:
    cache = _load_cache()
    app = _build_app(cfg, cache)

    accounts = app.get_accounts()
    if not accounts:
        print("No cached Microsoft accounts. Run auth.py to log in.")
        return 1

    print(f"Cached account(s): {len(accounts)}")
    for account in accounts:
        print(f"  - {account.get('username', '(unknown)')}")

    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    _persist_cache(cache)

    if result and "access_token" in result:
        print("A silent token is available; sync can run without prompting.")
        return 0

    print("No silent token available; re-run auth.py to refresh.")
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Authenticate the OmarOS outlook-sync skill against a personal "
            "Microsoft account via the OAuth2 device-code flow, persisting a "
            "token cache for later silent token acquisition."
        )
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Report cached accounts and whether a silent token is available; do not prompt.",
    )
    args = parser.parse_args()

    cfg = load_config()

    if args.status:
        sys.exit(_status(cfg))

    sys.exit(_login(cfg))


if __name__ == "__main__":
    main()
