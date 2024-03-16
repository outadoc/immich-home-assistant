"""Config flow for Immich integration."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from url_normalize import url_normalize
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import CONF_WATCHED_ALBUMS, DOMAIN
from .hub import CannotConnect, ImmichHub, InvalidAuth

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_API_KEY): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    url = url_normalize(data[CONF_HOST])
    api_key = data[CONF_API_KEY]

    hub = ImmichHub(host=url, api_key=api_key)

    if not await hub.authenticate():
        raise InvalidAuth

    user_info = await hub.get_my_user_info()
    username = user_info["name"]
    clean_hostname = urlparse(url).hostname

    # Return info that you want to store in the config entry.
    return {
        "title": f"{username} @ {clean_hostname}",
        "data": {CONF_HOST: url, CONF_API_KEY: api_key},
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for immich."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Immich options flow handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get a connection to the hub in order to list the available albums
        url = url_normalize(self.config_entry.data[CONF_HOST])
        api_key = self.config_entry.data[CONF_API_KEY]
        hub = ImmichHub(host=url, api_key=api_key)

        if not await hub.authenticate():
            raise InvalidAuth

        # Get the list of albums and create a mapping of album id to album name
        albums = await hub.list_all_albums()
        album_map = {album["id"]: album["albumName"] for album in albums}

        # Filter out any album ids that are no longer returned by the API
        current_albums_value = [
            album
            for album in self.config_entry.options.get(CONF_WATCHED_ALBUMS, [])
            if album in album_map
        ]

        # Allow the user to select which albums they want to create entities for
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_WATCHED_ALBUMS,
                        default=current_albums_value,
                    ): cv.multi_select(album_map)
                }
            ),
        )
