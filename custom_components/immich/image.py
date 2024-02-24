"""Image device for Immich integration."""
from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.core import HomeAssistant

from .hub import ImmichHub
from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Immich image platform."""

    hub = ImmichHub(
        host=config_entry.data[CONF_HOST], api_key=config_entry.data[CONF_API_KEY]
    )

    async_add_entities([ImmichImage(hass, hub)])


class ImmichImage(ImageEntity):
    """A class to let you visualize the map."""

    _attr_unique_id = "favorite_image"
    _attr_has_entity_name = True
    _attr_has_entity_name = True
    _attr_name = None

    # We want to get a new image every so often, as defined by the refresh interval
    _attr_should_poll = True

    _cached_bytes = None

    def __init__(self, hass: HomeAssistant, hub: ImmichHub) -> None:
        """Initialize the Immich image entity."""
        super().__init__(hass=hass, verify_ssl=True)
        self.hub = hub
        self.hass = hass

    async def async_update(self) -> None:
        """Update the image entity data."""
        await self._load_and_cache_image()

    async def async_image(self) -> bytes | None:
        """Return a random image from the Immich API."""
        if not self._cached_bytes:
            await self._load_and_cache_image()

        return self._cached_bytes

    async def _load_and_cache_image(self) -> None:
        random_asset = await self.hub.get_random_picture()

        if random_asset:
            asset_bytes = await self.hub.download_asset(random_asset["id"])
            self._cached_bytes = asset_bytes
            self._attr_image_last_updated = datetime.now()
