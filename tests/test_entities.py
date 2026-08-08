"""Entity identity and vacuum state mapping regression tests."""

from unittest.mock import MagicMock

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.vacuum import VacuumEntityFeature
from homeassistant.const import PERCENTAGE

from custom_components.dyson_local.binary_sensor import DysonFilterReplacementSensor
from custom_components.dyson_local.fan import DysonPureCoolEntity
from custom_components.dyson_local.libdyson import VacuumState
from custom_components.dyson_local.sensor import (
    DysonBatterySensor,
    DysonPM25Sensor,
    DysonTemperatureSensor,
)
from custom_components.dyson_local.vacuum import (
    DYSON_ACTIVITIES,
    DYSON_STATUS,
    SUPPORTED_FEATURES,
)

SERIAL = "NK6-EU-ABC1234A"
DEVICE_NAME = "Living Room"


@pytest.fixture
def device() -> MagicMock:
    """Return a stand-in Dyson device."""
    mock = MagicMock()
    mock.serial = SERIAL
    mock.device_type = "438"
    return mock


def test_sub_entity_identity(device: MagicMock) -> None:
    """A sub entity keeps the serial-prefixed unique id and its own name."""
    entity = DysonFilterReplacementSensor(device, DEVICE_NAME)
    assert entity.unique_id == f"{SERIAL}-filter_replacement"
    assert entity.name == "Filter Replacement"
    assert entity.has_entity_name is True
    assert entity.device_info["name"] == DEVICE_NAME
    assert entity.device_info["identifiers"] == {("dyson_local", SERIAL)}


def test_main_entity_identity(device: MagicMock) -> None:
    """The main entity uses the bare serial and inherits the device name."""
    entity = DysonPureCoolEntity(device, DEVICE_NAME)
    assert entity.unique_id == SERIAL
    assert entity.name is None
    assert entity.has_entity_name is True


def test_environmental_sensor_reads_its_device_attribute(device: MagicMock) -> None:
    """Environmental sensors resolve their value through _device_attr."""
    coordinator = MagicMock()
    device.particulate_matter_2_5 = 12
    assert DysonPM25Sensor(coordinator, device, DEVICE_NAME).native_value == 12

    device.particulate_matter_2_5 = -1
    assert DysonPM25Sensor(coordinator, device, DEVICE_NAME).native_value is None


def test_temperature_sensor_converts_from_kelvin(device: MagicMock) -> None:
    """Temperature is reported by the device in Kelvin."""
    coordinator = MagicMock()
    device.temperature = 294.15
    assert DysonTemperatureSensor(coordinator, device, DEVICE_NAME).native_value == pytest.approx(21.0)

    device.temperature = -2
    assert DysonTemperatureSensor(coordinator, device, DEVICE_NAME).native_value is None


def test_every_vacuum_state_is_mapped() -> None:
    """No device state may fall through the activity or status lookup."""
    for state in VacuumState:
        assert state in DYSON_ACTIVITIES
        assert state in DYSON_STATUS


def test_vacuum_battery_lives_on_the_sensor(device: MagicMock) -> None:
    """Battery moved off the vacuum entity; the sensor is the replacement."""
    assert VacuumEntityFeature.BATTERY not in SUPPORTED_FEATURES

    device.battery_level = 55
    sensor = DysonBatterySensor(device, DEVICE_NAME)
    assert sensor.unique_id == f"{SERIAL}-battery_level"
    assert sensor.device_class is SensorDeviceClass.BATTERY
    assert sensor.native_unit_of_measurement == PERCENTAGE
    assert sensor.native_value == 55
