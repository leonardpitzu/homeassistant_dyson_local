"""Camera platform for Dyson cloud."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.components.camera import Camera
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DysonCloudConfigEntry
from .const import DOMAIN
from .libdyson.cloud import DysonDeviceInfo
from .libdyson.cloud.cloud_360_eye import DysonCloud360Eye
from .libdyson.const import DEVICE_TYPE_360_EYE

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=30)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DysonCloudConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Dyson cleaning map cameras from a config entry."""
    data = config_entry.runtime_data
    entities = [
        DysonCleaningMapEntity(DysonCloud360Eye(data.account, device.serial), device)
        for device in data.devices
        if device.product_type == DEVICE_TYPE_360_EYE
    ]
    async_add_entities(entities, True)


class DysonCleaningMapEntity(Camera):
    """Dyson vacuum cleaning map entity."""

    _attr_icon = "mdi:map"

    def __init__(self, device: DysonCloud360Eye, device_info: DysonDeviceInfo) -> None:
        """Initialize the entity."""
        super().__init__()
        self._device = device
        self._device_info = device_info
        self._last_cleaning_task = None
        self._image = None
        self._attr_name = f"{device_info.name} Cleaning Map"
        self._attr_unique_id = device_info.serial
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_info.serial)},
            manufacturer="Dyson",
            model=device_info.product_type,
            name=device_info.name,
            serial_number=device_info.serial,
            sw_version=device_info.version,
        )

    def camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        """Return cleaning map. Width and height are ignored."""
        return self._image

    def update(self) -> None:
        """Check for map update."""
        _LOGGER.debug("Running cleaning map update for %s", self._device_info.name)
        cleaning_tasks = self._device.get_cleaning_history()

        last_task = None
        for task in cleaning_tasks:
            if task.area > 0.0:
                # Skip cleaning tasks with 0 area, map not available
                last_task = task
                break
        if last_task is None:
            _LOGGER.debug("No cleaning history found.")
            self._last_cleaning_task = None
            return

        if last_task == self._last_cleaning_task:
            _LOGGER.debug("Cleaning task not changed. Skip update.")
            return
        self._last_cleaning_task = last_task
        self._image = self._device.get_cleaning_map(self._last_cleaning_task.cleaning_id)

