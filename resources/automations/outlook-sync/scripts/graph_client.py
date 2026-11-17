from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Iterator

import httpx
import msal

from config import (
    AUTHORITY_TEMPLATE,
    GRAPH_BASE,
    SCOPES,
    TOKEN_CACHE_PATH,
    OutlookConfig,
    load_config,
)

WELL_KNOWN_NAMES = {
    "inbox",
    "junkemail",
    "archive",
    "deleteditems",
    "sentitems",
    "drafts",
    "outbox",
}

MESSAGE_SELECT = (
    "id,internetMessageId,subject,from,sender,toRecipients,"
    "receivedDateTime,bodyPreview,categories,parentFolderId,isRead"
)

# PidTagTransportMessageHeaders (0x007D) carries the full raw internet headers
# (incl. List-Unsubscribe) and, unlike internetMessageHeaders, IS returnable on
# message collections via $expand. Graph rejects $expand on delta queries, so the
# delta (incremental) path goes without it and relies on subject/LLM signals.
TRANSPORT_HEADERS_PROP = "String 0x007D"
MESSAGE_EXPAND = (
    "singleValueExtendedProperties($filter=id eq '" + TRANSPORT_HEADERS_PROP + "')"
)


class GraphError(Exception):
    """Raised on unrecoverable Microsoft Graph API failures."""


@dataclass
class Folder:
    id: str
    display_name: str
    parent_id: str | None
    total_item_count: int
    well_known_name: str | None


class GraphClient:
    def __init__(self, config: OutlookConfig) -> None:
        self.config = config
        self._app: msal.PublicClientApplication | None = None
        self._cache: msal.SerializableTokenCache | None = None
        self._client: httpx.Client | None = None
        self._folder_id_cache: dict[str, str] = {}
        self._well_known_cache: dict[str, str] = {}

    @classmethod
    def from_config(cls) -> GraphClient:
        return cls(load_config())

    def _load_cache(self) -> msal.SerializableTokenCache:
        if self._cache is None:
            cache = msal.SerializableTokenCache()
            if TOKEN_CACHE_PATH.exists():
                cache.deserialize(TOKEN_CACHE_PATH.read_text(encoding="utf-8"))
            self._cache = cache
        return self._cache

    def _build_app(self) -> msal.PublicClientApplication:
        if self._app is None:
            authority = AUTHORITY_TEMPLATE.format(tenant=self.config.tenant)
            self._app = msal.PublicClientApplication(
                self.config.client_id,
                authority=authority,
                token_cache=self._load_cache(),
            )
        return self._app

    def _persist_cache(self) -> None:
        cache = self._load_cache()
        if cache.has_state_changed:
            TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            # The refresh token is long-lived: lock the file down to the owner
            # before any unattended (daemon) silent-refresh path writes it.
            os.chmod(TOKEN_CACHE_PATH.parent, 0o700)
            TOKEN_CACHE_PATH.write_text(cache.serialize(), encoding="utf-8")
            os.chmod(TOKEN_CACHE_PATH, 0o600)

    def _token(self) -> str:
        app = self._build_app()
        accounts = app.get_accounts()
        result = (
            app.acquire_token_silent(SCOPES, account=accounts[0])
            if accounts
            else None
        )
        if not result or "access_token" not in result:
            raise GraphError("No cached Microsoft token. Run auth.py first.")
        self._persist_cache()
        return result["access_token"]

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=60.0)
        return self._client

    def _request(
        self,
        method: str,
        url_or_path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict | None:
        url = (
            GRAPH_BASE + url_or_path
            if url_or_path.startswith("/")
            else url_or_path
        )
        backoff = [2, 4, 8, 16]
        max_tries = 6
        client = self._http()
        for attempt in range(max_tries):
            headers = {
                "Authorization": f"Bearer {self._token()}",
                "Accept": "application/json",
            }
            if json is not None:
                headers["Content-Type"] = "application/json"
            try:
                response = client.request(
                    method,
                    url,
                    json=json,
                    params=params,
                    headers=headers,
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                # Transient network blips (read timeouts, dropped connections)
                # must not abort a long backfill — retry with backoff.
                if attempt < max_tries - 1:
                    time.sleep(float(backoff[min(attempt, len(backoff) - 1)]))
                    continue
                raise GraphError(
                    f"Graph request network error after retries: "
                    f"{method} {url}: {exc!r}"
                ) from exc
            status = response.status_code
            if status in (429, 503) and attempt < max_tries - 1:
                retry_after = response.headers.get("Retry-After")
                if retry_after is not None:
                    try:
                        delay = float(retry_after)
                    except ValueError:
                        delay = float(backoff[min(attempt, len(backoff) - 1)])
                else:
                    delay = float(backoff[min(attempt, len(backoff) - 1)])
                time.sleep(delay)
                continue
            if status == 204:
                return None
            if status >= 400:
                raise GraphError(
                    f"Graph request failed: {method} {url} -> "
                    f"{status}: {response.text}"
                )
            if not response.content:
                return None
            return response.json()
        raise GraphError(
            f"Graph request exhausted retries: {method} {url}"
        )

    def _paged(
        self, path: str, params: dict | None = None
    ) -> Iterator[dict]:
        next_url: str | None = None
        first = True
        while True:
            if first:
                data = self._request("GET", path, params=params)
                first = False
            else:
                if next_url is None:
                    break
                data = self._request("GET", next_url)
            if data is None:
                break
            for item in data.get("value", []):
                yield item
            next_url = data.get("@odata.nextLink")
            if not next_url:
                break

    def list_folders(self) -> list[Folder]:
        folders: list[Folder] = []
        # wellKnownName is NOT selectable on consumer (personal) mailboxes — it
        # 400s there — so we omit it and tag well-known folders by id afterwards.
        select = "id,displayName,parentFolderId,totalItemCount"

        def to_folder(raw: dict) -> Folder:
            return Folder(
                id=raw.get("id", ""),
                display_name=raw.get("displayName", ""),
                parent_id=raw.get("parentFolderId"),
                total_item_count=raw.get("totalItemCount", 0) or 0,
                well_known_name=None,
            )

        def recurse(folder_id: str) -> None:
            for raw in self._paged(
                f"/me/mailFolders/{folder_id}/childFolders",
                params={"$top": 100, "$select": select},
            ):
                folder = to_folder(raw)
                folders.append(folder)
                recurse(folder.id)

        for raw in self._paged(
            "/me/mailFolders",
            params={"$top": 100, "$select": select},
        ):
            folder = to_folder(raw)
            folders.append(folder)
            recurse(folder.id)

        # Resolve well-known folders by id (the /me/mailFolders/{name} shortcut
        # works on consumer mailboxes) and tag them, so junk/inbox detection in
        # sync.py and backfill.py keeps working without wellKnownName.
        id_to_known: dict[str, str] = {}
        for name in WELL_KNOWN_NAMES:
            try:
                id_to_known[self.well_known_folder_id(name)] = name
            except GraphError:
                continue
        for folder in folders:
            if folder.id in id_to_known:
                folder.well_known_name = id_to_known[folder.id]

        return folders

    def well_known_folder_id(self, name: str) -> str:
        if name in self._well_known_cache:
            return self._well_known_cache[name]
        data = self._request("GET", f"/me/mailFolders/{name}")
        if data is None or "id" not in data:
            raise GraphError(f"Could not resolve well-known folder: {name}")
        folder_id = data["id"]
        self._well_known_cache[name] = folder_id
        return folder_id

    def iter_messages(
        self, folder_id: str, page_size: int = 50
    ) -> Iterator[dict]:
        yield from self._paged(
            f"/me/mailFolders/{folder_id}/messages",
            params={
                "$select": MESSAGE_SELECT,
                "$expand": MESSAGE_EXPAND,
                "$top": page_size,
            },
        )

    def delta(
        self, folder_id: str, delta_link: str | None
    ) -> tuple[list[dict], str]:
        messages: list[dict] = []
        if delta_link:
            data = self._request("GET", delta_link)
        else:
            data = self._request(
                "GET",
                f"/me/mailFolders/{folder_id}/messages/delta",
                params={"$select": MESSAGE_SELECT},
            )
        new_delta_link = ""
        while True:
            if data is None:
                break
            messages.extend(data.get("value", []))
            next_link = data.get("@odata.nextLink")
            final_link = data.get("@odata.deltaLink")
            if final_link:
                new_delta_link = final_link
                break
            if not next_link:
                break
            data = self._request("GET", next_link)
        # If the stream ended without a fresh deltaLink, keep the prior cursor
        # rather than dropping it and forcing a full re-enumeration next run.
        return messages, new_delta_link or (delta_link or "")

    def get_message(self, message_id: str) -> dict:
        data = self._request("GET", f"/me/messages/{message_id}")
        if data is None:
            raise GraphError(f"Message not found: {message_id}")
        return data

    def move_message(self, message_id: str, dest_folder_id: str) -> dict:
        data = self._request(
            "POST",
            f"/me/messages/{message_id}/move",
            json={"destinationId": dest_folder_id},
        )
        if data is None:
            raise GraphError(
                f"Move returned no resource: {message_id} -> {dest_folder_id}"
            )
        return data

    def list_master_categories(self) -> list[dict]:
        data = self._request("GET", "/me/outlook/masterCategories")
        if data is None:
            return []
        return data.get("value", [])

    def ensure_master_category(
        self, name: str, color: str = "preset0"
    ) -> None:
        existing = {
            c.get("displayName") for c in self.list_master_categories()
        }
        if name in existing:
            return
        self._request(
            "POST",
            "/me/outlook/masterCategories",
            json={"displayName": name, "color": color},
        )

    def set_categories(
        self, message_id: str, categories: list[str]
    ) -> dict:
        data = self._request(
            "PATCH",
            f"/me/messages/{message_id}",
            json={"categories": categories},
        )
        if data is None:
            raise GraphError(
                f"Setting categories returned no resource: {message_id}"
            )
        return data

    def ensure_folder(
        self, display_name: str, parent_id: str | None = None
    ) -> str:
        cache_key = f"{parent_id or 'root'}::{display_name}"
        if cache_key in self._folder_id_cache:
            return self._folder_id_cache[cache_key]

        if parent_id is None:
            list_path = "/me/mailFolders"
            create_path = "/me/mailFolders"
        else:
            list_path = f"/me/mailFolders/{parent_id}/childFolders"
            create_path = f"/me/mailFolders/{parent_id}/childFolders"

        for raw in self._paged(
            list_path,
            params={"$top": 100, "$select": "id,displayName"},
        ):
            if raw.get("displayName") == display_name:
                folder_id = raw.get("id", "")
                self._folder_id_cache[cache_key] = folder_id
                return folder_id

        data = self._request(
            "POST",
            create_path,
            json={"displayName": display_name},
        )
        if data is None or "id" not in data:
            raise GraphError(
                f"Could not create folder: {display_name} (parent={parent_id})"
            )
        folder_id = data["id"]
        self._folder_id_cache[cache_key] = folder_id
        return folder_id

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
