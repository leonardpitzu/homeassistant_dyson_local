"""Switch platform for dyson."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DysonEntity, DysonLocalConfigEntry
from .libdyson import DysonPureHotCoolLink


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DysonLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Dyson switch from a config entry."""
    device = config_entry.runtime_data.device
    name = config_entry.data[CONF_NAME]
    entities = [
        DysonNightModeSwitchEntity(device, name),
        DysonContinuousMonitoringSwitchEntity(device, name),
    ]
    if isinstance(device, DysonPureHotCoolLink):
        entities.append(DysonFocusModeSwitchEntity(device, name))
    async_add_entities(entities)


class DysonNightModeSwitchEntity(DysonEntity, SwitchEntity):
    """Dyson fan night mode switch."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:power-sleep"
    _sub_name = "Night Mode"
    _sub_unique_id = "night_mode"

    @property
    def is_on(self) -> bool:
        """Return if night mode is on."""
        return self._device.night_mode

    def turn_on(self, **kwargs) -> None:
        """Turn on night mode."""
        self._device.enable_night_mode()

    def turn_off(self, **kwargs) -> None:
        """Turn off night mode."""
        self._device.disable_night_mode()


class DysonContinuousMonitoringSwitchEntity(DysonEntity, SwitchEntity):
    """Dyson fan continuous monitoring."""

    _attr_entity_category = EntityCategory.CONFIG
    _sub_name = "Continuous Monitoring"
    _sub_unique_id = "continuous_monitoring"

    @property
    def icon(self) -> str:
        """Return the icon of the entity."""
        return "mdi:eye" if self.is_on else "mdi:eye-off"

    @property
    def is_on(self) -> bool:
        """Return if continuous monitoring is on."""
        return self._device.continuous_monitoring

    def turn_on(self, **kwargs) -> None:
        """Turn on continuous monitoring."""
        self._device.enable_continuous_monitoring()

    def turn_off(self, **kwargs) -> None:
        """Turn off continuous monitoring."""
        self._device.disable_continuous_monitoring()


class DysonFocusModeSwitchEntity(DysonEntity, SwitchEntity):
    """Dyson Pure Hot+Cool Link focus mode switch."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:image-filter-center-focus"
    _sub_name = "Focus Mode"
    _sub_unique_id = "focus_mode"

    @property
    def is_on(self) -> bool:
        """Return if switch is on."""
        return self._device.focus_mode

    def turn_on(self, **kwargs) -> None:
        """Turn on switch."""
        self._device.enable_focus_mode()

    def turn_off(self, **kwargs) -> None:
        """Turn off switch."""
        self._device.disable_focus_mode()

