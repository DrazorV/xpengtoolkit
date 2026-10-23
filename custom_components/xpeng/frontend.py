"""Serve and register the bundled dashboard card without touching dashboards."""
from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)
_DATA_KEY = "xpeng_vehicle_card"
CARD_PATH = Path(__file__).parent / "www" / "xpeng-vehicle-card.js"
CARD_URL = "/xpeng/xpeng-vehicle-card.js"
_LEGACY_URL = "/local/xpeng-vehicle-card/xpeng-vehicle-card.js"


def _card_url() -> str:
    """Invalidate browser caches whenever the shipped JavaScript changes."""
    digest = hashlib.sha256(CARD_PATH.read_bytes()).hexdigest()[:12]
    return f"{CARD_URL}?v={digest}"


def _is_card_resource(url: str) -> bool:
    """Recognize only our local resource paths, never similarly named cards."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return not (parts.scheme or parts.netloc) and parts.path in {
        CARD_URL, _LEGACY_URL
    }


async def async_setup_card(hass: HomeAssistant) -> None:
    """Register once per instance; optional frontend failures must not stop cars."""
    lovelace = hass.data.get("lovelace")
    if lovelace is None or getattr(hass, "http", None) is None:
        return

    state = hass.data.setdefault(_DATA_KEY, {})
    lock = state.setdefault("lock", asyncio.Lock())
    async with lock:
        if state.get("ready"):
            return
        try:
            from homeassistant.components.frontend import add_extra_js_url
            from homeassistant.components.http import StaticPathConfig
            from homeassistant.components.lovelace.resources import (
                ResourceStorageCollection,
            )

            url = await hass.async_add_executor_job(_card_url)
            if not state.get("static_registered"):
                await hass.http.async_register_static_paths([
                    StaticPathConfig(CARD_URL, str(CARD_PATH), False)
                ])
                state["static_registered"] = True

            # Lovelace used a dict before HA 2025.2 and now uses a dataclass.
            resources = (
                lovelace["resources"] if isinstance(lovelace, dict)
                else lovelace.resources
            )
            if isinstance(resources, ResourceStorageCollection):
                # This public API loads storage before it can be changed.
                await resources.async_get_info()
                matches = [
                    item for item in resources.async_items()
                    if _is_card_resource(item.get("url", ""))
                ]
                if matches:
                    # Keep one ID so existing installations migrate in place.
                    keep = matches[0]
                    if keep["url"] != url or keep.get("type") != "module":
                        await resources.async_update_item(
                            keep["id"], {"url": url, "res_type": "module"}
                        )
                    for duplicate in matches[1:]:
                        await resources.async_delete_item(duplicate["id"])
                else:
                    await resources.async_create_item({
                        "url": url, "res_type": "module"
                    })
            else:
                # YAML resource lists are user-owned. Load our module through
                # the frontend API, which also survives YAML resource reloads.
                add_extra_js_url(hass, url)

            state["ready"] = True
        except Exception:  # noqa: BLE001 - the card must not break vehicle setup
            _LOGGER.exception("Unable to register the bundled XPENG Vehicle card")
