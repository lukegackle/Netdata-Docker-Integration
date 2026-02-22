"""Sensor platform for Netdata Docker."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    LOGGER,
    ATTR_MAP,
)
from .metrics_parser import ContainerMetrics
from . import NetdataDockerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Netdata Docker sensors from a config entry."""
    coordinator: NetdataDockerCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Track which containers we've already registered
    registered: set[str] = set()

    @callback
    def _async_discover() -> None:
        """Discover and register new container entities."""
        if not coordinator.data:
            return

        new_entities: list[NetdataDockerSensor] = []

        for container_name in coordinator.data:
            if container_name in registered:
                continue
            registered.add(container_name)

            new_entities.append(
                NetdataDockerSensor(
                    coordinator=coordinator,
                    container_name=container_name,
                )
            )

        if new_entities:
            LOGGER.info(
                "Registering %d new container entities",
                len(new_entities),
            )
            async_add_entities(new_entities)

    # Initial discovery
    _async_discover()

    # Re-discover on every coordinator update (picks up new containers)
    entry.async_on_unload(coordinator.async_add_listener(_async_discover))


class NetdataDockerSensor(CoordinatorEntity[NetdataDockerCoordinator], SensorEntity):
    """A single sensor representing a Docker container."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:docker"

    def __init__(
        self,
        coordinator: NetdataDockerCoordinator,
        container_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.container_name = container_name

        # Build a filesystem-safe name slug
        safe_name = container_name.lower().replace("-", "_").replace(" ", "_")

        # Unique ID for config entry matching
        self._attr_unique_id = f"nd_docker_{safe_name}"
        
        # Set name to None so it perfectly inherits the Device name
        # This prevents "Docker: name name" duplication in the UI
        self._attr_name = None
        
        # Ensure the entity_id follows the requested pattern sensor.netdata_docker_<name>
        self.entity_id = f"sensor.netdata_docker_{safe_name}"

        # Group all sensors (if we ever add more) for the same container under one device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"container_{safe_name}")},
            name=f"Docker: {container_name}",
            manufacturer="Docker",
            model="Container",
            sw_version=None,
        )

    @property
    def available(self) -> bool:
        """Return True if coordinator data has this container."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.container_name in self.coordinator.data
        )

    @property
    def native_value(self) -> str | None:
        """Return the current status of the container."""
        if not self.coordinator.data:
            return None

        cm: ContainerMetrics | None = self.coordinator.data.get(self.container_name)
        if cm is None:
            return None

        return cm.state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra performance metrics as attributes."""
        if not self.coordinator.data:
            return {}

        cm: ContainerMetrics | None = self.coordinator.data.get(self.container_name)
        if cm is None:
            return {}

        attrs = {
            "Name": self.container_name,
        }
        
        # Basic ID
        if cm.container_id:
            attrs["container_id"] = cm.container_id

        for field_name, attr_name in ATTR_MAP.items():
            val = getattr(cm, field_name, None)
            if val is not None and val != "unknown":
                # Cast pids to int for cleaner display
                if field_name == "pids":
                    try:
                        val = int(val)
                    except (ValueError, TypeError):
                        pass
                attrs[attr_name] = val

        return attrs
