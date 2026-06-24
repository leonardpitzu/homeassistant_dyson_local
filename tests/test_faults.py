"""Tests for the Dyson fault-message parsing (filter replacement + water tank).

These exercise the vendored libdyson fault handling that backs the
``binary_sensor`` entities and the filter-reset ``button``.
"""

import pytest

from custom_components.dyson_local.libdyson import MessageType
from custom_components.dyson_local.libdyson.const import DEVICE_TYPE_PURE_HUMIDIFY_COOL
from custom_components.dyson_local.libdyson.dyson_pure_humidify_cool import (
    DysonPurifierHumidifyCool,
)

SERIAL = "XXX-EU-TEST0000"
CREDENTIAL = "credential"


@pytest.fixture
def device() -> DysonPurifierHumidifyCool:
    """Return a humidifier device instance (not connected)."""
    return DysonPurifierHumidifyCool(SERIAL, CREDENTIAL, DEVICE_TYPE_PURE_HUMIDIFY_COOL)


def test_unknown_before_any_message(device: DysonPurifierHumidifyCool) -> None:
    """Faults are unknown (None) until the device reports them."""
    assert device.water_tank_empty is None
    assert device.filter_replacement_required is None


def test_faults_topic(device: DysonPurifierHumidifyCool) -> None:
    """The faults subscription topic is derived from type and serial."""
    assert device._faults_topic == f"{DEVICE_TYPE_PURE_HUMIDIFY_COOL}/{SERIAL}/status/faults"


def test_current_faults_all_ok(device: DysonPurifierHumidifyCool) -> None:
    """An OK CURRENT-FAULTS message clears every fault."""
    device._handle_message(
        {"msg": "CURRENT-FAULTS", "product-warnings": {"tnke": "OK", "fltr": "OK"}}
    )
    assert device.water_tank_empty is False
    assert device.filter_replacement_required is False


def test_current_faults_water_tank_empty(device: DysonPurifierHumidifyCool) -> None:
    """A FAIL on tnke marks the water tank empty without affecting the filter."""
    device._handle_message(
        {"msg": "CURRENT-FAULTS", "product-warnings": {"tnke": "FAIL", "fltr": "OK"}}
    )
    assert device.water_tank_empty is True
    assert device.filter_replacement_required is False


def test_faults_change_list_form(device: DysonPurifierHumidifyCool) -> None:
    """FAULTS-CHANGE carries [old, new] pairs; the new value wins."""
    device._handle_message({"msg": "CURRENT-FAULTS", "product-warnings": {"fltr": "OK"}})
    assert device.filter_replacement_required is False

    device._handle_message(
        {"msg": "FAULTS-CHANGE", "product-warnings": {"fltr": ["OK", "FAIL"]}}
    )
    assert device.filter_replacement_required is True


def test_faults_persist_across_partial_updates(device: DysonPurifierHumidifyCool) -> None:
    """A later message that omits a field leaves its prior value intact."""
    device._handle_message(
        {"msg": "CURRENT-FAULTS", "product-warnings": {"tnke": "FAIL", "fltr": "OK"}}
    )
    device._handle_message({"msg": "FAULTS-CHANGE", "product-warnings": {"fltr": ["OK", "FAIL"]}})
    assert device.water_tank_empty is True
    assert device.filter_replacement_required is True


def test_fault_message_fires_callback(device: DysonPurifierHumidifyCool) -> None:
    """A faults message dispatches a MessageType.FAULT callback."""
    received: list[MessageType] = []
    device.add_message_listener(received.append)
    device._handle_message({"msg": "CURRENT-FAULTS", "product-warnings": {"tnke": "FAIL"}})
    assert MessageType.FAULT in received
