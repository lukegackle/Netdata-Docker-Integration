"""Config flow for Netdata Docker integration."""
from __future__ import annotations

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_URL, CONF_SCAN_INTERVAL, DEFAULT_POLL_INTERVAL


class NetdataDockerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Netdata Docker."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            url = user_input[CONF_URL].rstrip("/")
            if not url.startswith(("http://", "https://")):
                errors["base"] = "invalid_url"
            else:
                # Ensure URL ends with the allmetrics endpoint
                if "/api/v1/allmetrics" not in url:
                    url = f"{url}/api/v1/allmetrics?format=json"

                # Test the connection
                try:
                    session = async_get_clientsession(self.hass)
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        resp.raise_for_status()
                        data = await resp.json()
                        if not isinstance(data, dict) or len(data) == 0:
                            errors["base"] = "no_data"
                except Exception:
                    errors["base"] = "cannot_connect"

                if not errors:
                    # Store the validated URL
                    user_input[CONF_URL] = url
                    return self.async_create_entry(
                        title="Netdata Docker", data=user_input
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_URL): cv.string,
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=DEFAULT_POLL_INTERVAL
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
                }
            ),
            errors=errors,
        )
