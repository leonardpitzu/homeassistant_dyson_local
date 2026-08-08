"""Binary sensor platform for dyson."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import CONF_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DysonEntity, DysonLocalConfigEntry
from .libdyson import (
    Dyson360Eye,
    Dyson360Heurist,
    Dyson360VisNav,
    DysonPureHotCoolLink,
    DysonPurifierHumidifyCool,
    MessageType,
)
from .libdyson.dyson_device import DysonFanDevice

ICON_BIN_FULL = "mdi:delete-variant"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DysonLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Dyson binary sensor from a config entry."""
    device = config_entry.runtime_data.device
    name = config_entry.data[CONF_NAME]
    entities = []
    if isinstance(device, Dyson360Eye):
        entities.append(DysonVacuumBatteryChargingSensor(device, name))
    if isinstance(device, Dyson360Heurist):
        entities.extend(
            [
                DysonVacuumBatteryChargingSensor(device, name),
                Dyson360VisNavBinFullSensor(device, name),
            ]
        )
    if isinstance(device, Dyson360VisNav):
        entities.extend(
            [
                DysonVacuumBatteryChargingSensor(device, name),
                Dyson360HeuristBinFullSensor(device, name),
            ]
        )
    if isinstance(device, DysonPureHotCoolLink):
        entities.extend([DysonPureHotCoolLinkTiltSensor(device, name)])
    if isinstance(device, DysonFanDevice):
        entities.append(DysonFilterReplacementSensor(device, name))
    if isinstance(device, DysonPurifierHumidifyCool):
        entities.append(DysonWaterTankEmptySensor(device, name))
    async_add_entities(entities)


class DysonVacuumBatteryChargingSensor(DysonEntity, BinarySensorEntity):
    """Dyson vacuum battery charging sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
    _sub_name = "Battery Charging"
    _sub_unique_id = "battery_charging"

    @property
    def is_on(self) -> bool:
        """Return if the sensor is on."""
        return self._device.is_charging


class Dyson360HeuristBinFullSensor(DysonEntity, BinarySensorEntity):
    """Dyson 360 Heurist bin full sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = ICON_BIN_FULL
    _sub_name = "Bin Full"
    _sub_unique_id = "bin_full"

    @property
    def is_on(self) -> bool:
        """Return if the sensor is on."""
        return self._device.is_bin_full


class Dyson360VisNavBinFullSensor(DysonEntity, BinarySensorEntity):
    """Dyson 360 VisNav bin full sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = ICON_BIN_FULL
    _sub_name = "Bin Full"
    _sub_unique_id = "bin_full"

    @property
    def is_on(self) -> bool:
        """Return if the sensor is on."""
        return self._device.is_bin_full


class DysonPureHotCoolLinkTiltSensor(DysonEntity, BinarySensorEntity):
    """Dyson Pure Hot+Cool Link tilt sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:angle-acute"
    _sub_name = "Tilt"
    _sub_unique_id = "tilt"

    @property
    def is_on(self) -> bool:
        """Return if the sensor is on."""
        return self._device.tilt


class DysonFilterReplacementSensor(DysonEntity, BinarySensorEntity):
    """Dyson filter replacement fault sensor."""

    _MESSAGE_TYPE = MessageType.FAULT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:air-filter"
    _sub_name = "Filter Replacement"
    _sub_unique_id = "filter_replacement"

    @property
    def is_on(self) -> bool | None:
        """Return if the filter needs replacing."""
        return self._device.filter_replacement_required


class DysonWaterTankEmptySensor(DysonEntity, BinarySensorEntity):
    """Dyson humidifier water tank empty sensor."""

    _MESSAGE_TYPE = MessageType.FAULT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:water-alert"
    _sub_name = "Water Tank Empty"
    _sub_unique_id = "water_tank_empty"

    @property
    def is_on(self) -> bool | None:
        """Return if the water tank is empty."""
        return self._device.water_tank_empty
