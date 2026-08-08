"""Sensor platform for dyson."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import (
    CONF_NAME,
    PERCENTAGE,
    EntityCategory,
    UnitOfDensity,
    UnitOfRatio,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import DysonEntity, DysonLocalConfigEntry
from .libdyson import (
    Dyson360Eye,
    Dyson360Heurist,
    Dyson360VisNav,
    DysonBigQuiet,
    DysonDevice,
    DysonPureCoolLink,
    DysonPurifierHumidifyCool,
)
from .libdyson.const import MessageType

VACUUM_TYPES = (Dyson360Eye, Dyson360Heurist, Dyson360VisNav)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DysonLocalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Dyson sensor from a config entry."""
    data = config_entry.runtime_data
    device = data.device
    name = config_entry.data[CONF_NAME]
    if isinstance(device, VACUUM_TYPES):
        entities = [DysonBatterySensor(device, name)]
    else:
        coordinator = data.coordinator
        entities = [
            DysonHumiditySensor(coordinator, device, name),
            DysonTemperatureSensor(coordinator, device, name),
            DysonVOCSensor(coordinator, device, name),
        ]

        if isinstance(device, DysonPureCoolLink):
            entities.extend(
                [
                    DysonFilterLifeSensor(device, name),
                    DysonFilterLifeSensorPercentage(device, name),
                    DysonParticulatesSensor(coordinator, device, name),
                ]
            )
        else:
            if isinstance(device, DysonBigQuiet):
                if getattr(device, "carbon_dioxide", None) is not None:
                    entities.append(DysonCarbonDioxideSensor(coordinator, device, name))

            entities.extend(
                [
                    DysonPM25Sensor(coordinator, device, name),
                    DysonPM10Sensor(coordinator, device, name),
                    DysonNO2Sensor(coordinator, device, name),
                ]
            )
            if device.carbon_filter_life is None:
                entities.append(DysonCombinedFilterLifeSensor(device, name))
            else:
                entities.extend(
                    [
                        DysonCarbonFilterLifeSensor(device, name),
                        DysonHEPAFilterLifeSensor(device, name),
                    ]
                )
        if isinstance(device, DysonPurifierHumidifyCool):
            entities.append(DysonNextDeepCleanSensor(device, name))
        if getattr(device, "formaldehyde", None) is not None:
            entities.append(DysonHCHOSensor(coordinator, device, name))
    async_add_entities(entities)


class DysonSensor(SensorEntity, DysonEntity):
    """Base class for a Dyson sensor."""

    _MESSAGE_TYPE = MessageType.STATE


class DysonSensorEnvironmental(CoordinatorEntity, DysonSensor):
    """Dyson environmental sensor.

    Reads a single libdyson device attribute, which reports negative sentinels
    (ENVIRONMENTAL_OFF/INIT/FAIL) instead of a reading.
    """

    _MESSAGE_TYPE = MessageType.ENVIRONMENTAL
    _device_attr: str

    def __init__(self, coordinator: DataUpdateCoordinator[None], device: DysonDevice, name: str) -> None:
        """Initialize the environmental sensor."""
        CoordinatorEntity.__init__(self, coordinator)
        DysonSensor.__init__(self, device, name)

    @property
    def _raw_value(self):
        """Return the unfiltered device reading."""
        return getattr(self._device, self._device_attr)

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if (value := self._raw_value) >= 0:
            return value
        return None

    @property
    def available(self) -> bool:
        """Return available only if device not in off, init or failed states."""
        return isinstance(self._raw_value, (int, float))


class DysonBatterySensor(DysonSensor):
    """Dyson battery sensor."""

    _sub_unique_id = "battery_level"
    _sub_name = "Battery Level"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self._device.battery_level


class DysonFilterLifeSensor(DysonSensor):
    """Dyson filter life sensor (in hours) for Pure Cool Link."""

    _sub_unique_id = "filter_life"
    _sub_name = "Filter Life"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:filter-outline"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self._device.filter_life


class DysonFilterLifeSensorPercentage(DysonSensor):
    """Dyson filter life sensor (in percentage) for Pure Cool Link."""

    _sub_unique_id = "filter_life_percentage"
    _sub_name = "Filter Life Percentage"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:filter-outline"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 0

    @property
    def native_value(self) -> float:
        """Return the state of the sensor calculated to a %."""
        return (self._device.filter_life / 4300) * 100


class DysonCarbonFilterLifeSensor(DysonSensor):
    """Dyson carbon filter life sensor (in percentage) for Pure Cool."""

    _sub_unique_id = "carbon_filter_life"
    _sub_name = "Carbon Filter Life"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:filter-outline"
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self._device.carbon_filter_life


class DysonHEPAFilterLifeSensor(DysonSensor):
    """Dyson HEPA filter life sensor (in percentage) for Pure Cool."""

    _sub_unique_id = "hepa_filter_life"
    _sub_name = "HEPA Filter Life"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:filter-outline"
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self._device.hepa_filter_life


class DysonCombinedFilterLifeSensor(DysonSensor):
    """Dyson combined filter life sensor (in percentage) for Pure Cool."""

    _sub_unique_id = "combined_filter_life"
    _sub_name = "Filter Life"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:filter-outline"
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self._device.hepa_filter_life


class DysonNextDeepCleanSensor(DysonSensor):
    """Sensor of time until next deep clean (in hours) for Dyson Pure Humidify+Cool."""

    _sub_unique_id = "next_deep_clean"
    _sub_name = "Next Deep Clean"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:filter-outline"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        if (value := self._device.time_until_next_clean) >= 0:
            return value
        return None

    @property
    def available(self) -> bool:
        """Return available only if device not in off, init or failed states."""
        return isinstance(self._device.time_until_next_clean, (int, float))


class DysonHumiditySensor(DysonSensorEnvironmental):
    """Dyson humidity sensor."""

    _sub_unique_id = "humidity"
    _sub_name = "Humidity"
    _device_attr = "humidity"
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT


class DysonTemperatureSensor(DysonSensorEnvironmental):
    """Dyson temperature sensor."""

    _sub_unique_id = "temperature"
    _sub_name = "Temperature"
    _device_attr = "temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the temperature in Celsius; the device reports Kelvin."""
        if (value := self._raw_value) >= 0:
            return value - 273.15
        return None


class DysonPM25Sensor(DysonSensorEnvironmental):
    """Dyson sensor for PM 2.5 fine particulate matters."""

    _sub_unique_id = "pm25"
    _sub_name = "PM 2.5"
    _device_attr = "particulate_matter_2_5"
    _attr_device_class = SensorDeviceClass.PM25
    _attr_native_unit_of_measurement = UnitOfDensity.MICROGRAMS_PER_CUBIC_METER
    _attr_state_class = SensorStateClass.MEASUREMENT


class DysonPM10Sensor(DysonSensorEnvironmental):
    """Dyson sensor for PM 10 particulate matters."""

    _sub_unique_id = "pm10"
    _sub_name = "PM 10"
    _device_attr = "particulate_matter_10"
    _attr_device_class = SensorDeviceClass.PM10
    _attr_native_unit_of_measurement = UnitOfDensity.MICROGRAMS_PER_CUBIC_METER
    _attr_state_class = SensorStateClass.MEASUREMENT


class DysonParticulatesSensor(DysonSensorEnvironmental):
    """Dyson sensor for particulate matters for "Link" devices."""

    _sub_unique_id = "aqi"
    _sub_name = "Air Quality Index"
    _device_attr = "particulates"
    _attr_device_class = SensorDeviceClass.AQI
    _attr_state_class = SensorStateClass.MEASUREMENT


class DysonVOCSensor(DysonSensorEnvironmental):
    """Dyson sensor for volatile organic compounds."""

    _sub_unique_id = "voc-index"
    _sub_name = "Volatile Organic Compounds Index"
    _device_attr = "volatile_organic_compounds"
    _attr_device_class = SensorDeviceClass.AQI
    _attr_state_class = SensorStateClass.MEASUREMENT


class DysonNO2Sensor(DysonSensorEnvironmental):
    """Dyson sensor for Nitrogen Dioxide."""

    _sub_unique_id = "no2-index"
    _sub_name = "Nitrogen Dioxide Index"
    _device_attr = "nitrogen_dioxide"
    _attr_device_class = SensorDeviceClass.AQI
    _attr_state_class = SensorStateClass.MEASUREMENT


class DysonHCHOSensor(DysonSensorEnvironmental):
    """Dyson sensor for Formaldehyde."""

    _sub_unique_id = "hcho-mg"
    _sub_name = "HCHO"
    _device_attr = "formaldehyde"
    _attr_native_unit_of_measurement = UnitOfDensity.MILLIGRAMS_PER_CUBIC_METER
    _attr_state_class = SensorStateClass.MEASUREMENT


class DysonCarbonDioxideSensor(DysonSensorEnvironmental):
    """Dyson sensor for Carbon Dioxide."""

    _sub_unique_id = "c02"
    _sub_name = "Carbon Dioxide"
    _device_attr = "carbon_dioxide"
    _attr_device_class = SensorDeviceClass.CO2
    _attr_native_unit_of_measurement = UnitOfRatio.PARTS_PER_MILLION
    _attr_state_class = SensorStateClass.MEASUREMENT
