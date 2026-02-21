"""The Netdata Docker integration."""
from __future__ import annotations

from datetime import timedelta
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER, CONF_URL, CONF_SCAN_INTERVAL, DEFAULT_POLL_INTERVAL
from .metrics_parser import ContainerMetrics, discover_containers

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Netdata Docker from a config entry."""
    coordinator = NetdataDockerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class NetdataDockerCoordinator(DataUpdateCoordinator[dict[str, ContainerMetrics]]):
    """Coordinator that fetches Netdata allmetrics and parses container data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.api_url = entry.data[CONF_URL]
        interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_POLL_INTERVAL)
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )

    async def _async_update_data(self) -> dict[str, ContainerMetrics]:
        """Fetch allmetrics JSON and parse container data."""
        try:
            session = async_get_clientsession(self.hass)
            async with async_timeout.timeout(15):
                response = await session.get(self.api_url)
                response.raise_for_status()
                raw_data = await response.json()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Netdata API: {err}") from err

        containers = discover_containers(raw_data)

        if not containers:
            LOGGER.warning(
                "No Docker containers discovered from Netdata. "
                "Verify docker/cgroup monitoring is enabled in Netdata."
            )
        else:
            LOGGER.debug(
                "Discovered %d container(s): %s",
                len(containers),
                list(containers.keys()),
            )

        return containers
