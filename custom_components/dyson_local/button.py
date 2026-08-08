"""Button platform for dyson."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DysonEntity, DysonLocalConfigEntry
from .libdyson.dyson_device import DysonFanDevice


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DysonLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Dyson button from a config entry."""
    device = config_entry.runtime_data.device
    name = config_entry.data[CONF_NAME]

    entities = []
    if isinstance(device, DysonFanDevice):
        entities.append(DysonFilterResetButton(device, name))

    async_add_entities(entities)


class DysonFilterResetButton(DysonEntity, ButtonEntity):
    """Dyson filter life reset button."""

    _attr_entity_category = EntityCategory.CONFIG
    _sub_name = "Reset Filter Life"
    _sub_unique_id = "reset-filter"

    def press(self) -> None:
        """Reset the filter life counter."""
        self._device.reset_filter()

