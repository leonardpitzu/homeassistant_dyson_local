"""Support for Dyson devices."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from functools import partial
from threading import Event

from homeassistant.components.zeroconf import async_get_instance
from homeassistant.config_entries import SOURCE_DISCOVERY, ConfigEntry
from homeassistant.const import CONF_HOST, EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .cloud.const import CONF_AUTH, CONF_REGION
from .const import (
    CONF_CREDENTIAL,
    CONF_DEVICE_TYPE,
    CONF_SERIAL,
    DATA_DISCOVERY,
    DOMAIN,
)
from .libdyson import (
    Dyson360Eye,
    Dyson360Heurist,
    Dyson360VisNav,
    DysonPureHotCool,
    DysonPureHotCoolLink,
    DysonPurifierHumidifyCool,
    MessageType,
    get_device,
)
from .libdyson.cloud import DysonAccount, DysonAccountCN, DysonDeviceInfo
from .libdyson.discovery import DysonDiscovery
from .libdyson.dyson_device import DysonDevice
from .libdyson.exceptions import (
    DysonException,
    DysonInvalidAuth,
    DysonNetworkError,
)

_LOGGER = logging.getLogger(__name__)

ENVIRONMENTAL_DATA_UPDATE_INTERVAL = timedelta(seconds=30)
DISCOVERY_TIMEOUT = 10

CLOUD_PLATFORMS = [Platform.CAMERA]
VACUUM_TYPES = (Dyson360Eye, Dyson360Heurist, Dyson360VisNav)


@dataclass
class DysonLocalData:
    """Runtime data for a locally connected Dyson device."""

    device: DysonDevice
    coordinator: DataUpdateCoordinator[None] | None


@dataclass
class DysonCloudData:
    """Runtime data for a MyDyson account entry."""

    account: DysonAccount
    devices: list[DysonDeviceInfo]


type DysonLocalConfigEntry = ConfigEntry[DysonLocalData]
type DysonCloudConfigEntry = ConfigEntry[DysonCloudData]


async def _async_get_discovery(hass: HomeAssistant) -> DysonDiscovery:
    """Return the zeroconf discovery shared by all entries, starting it on first use."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if (discovery := domain_data.get(DATA_DISCOVERY)) is None:
        discovery = domain_data[DATA_DISCOVERY] = DysonDiscovery()
        discovery.start_discovery(await async_get_instance(hass))

        @callback
        def _stop_discovery(_event) -> None:
            discovery.stop_discovery()
            domain_data[DATA_DISCOVERY] = None

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _stop_discovery)
    return discovery


async def _async_discover_host(hass: HomeAssistant, device: DysonDevice) -> str:
    """Wait for the device to announce itself over zeroconf."""
    discovery = await _async_get_discovery(hass)
    found = Event()
    host = None

    def _found(address: str) -> None:
        nonlocal host
        host = address
        found.set()

    # Fires immediately if the device was already seen by the shared browser.
    await hass.async_add_executor_job(discovery.register_device, device, _found)
    if not await hass.async_add_executor_job(found.wait, DISCOVERY_TIMEOUT):
        raise ConfigEntryNotReady(f"Timed out discovering device {device.serial}")
    return host


async def _async_setup_account(hass: HomeAssistant, entry: DysonCloudConfigEntry) -> bool:
    """Set up a MyDyson Account."""
    region = entry.data[CONF_REGION]
    if region == "CN":
        account = DysonAccountCN(entry.data[CONF_AUTH])
    else:
        account = DysonAccount(entry.data[CONF_AUTH])

    try:
        devices = await hass.async_add_executor_job(account.devices)
    except DysonNetworkError as err:
        raise ConfigEntryNotReady("Cannot connect to the Dyson cloud service") from err
    except DysonInvalidAuth as err:
        raise ConfigEntryNotReady("Invalid MyDyson credentials") from err

    _LOGGER.debug("Retrieved %d devices from the %s cloud region", len(devices), region)
    for device in devices:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_DISCOVERY},
                data=device,
            )
        )

    entry.runtime_data = DysonCloudData(account=account, devices=devices)
    await hass.config_entries.async_forward_entry_setups(entry, CLOUD_PLATFORMS)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dyson from a config entry."""
    if CONF_REGION in entry.data:
        return await _async_setup_account(hass, entry)

    device = get_device(
        entry.data[CONF_SERIAL],
        entry.data[CONF_CREDENTIAL],
        entry.data[CONF_DEVICE_TYPE],
    )
    if device is None:
        raise ConfigEntryNotReady(f"Unsupported device type {entry.data[CONF_DEVICE_TYPE]}")

    host = entry.data.get(CONF_HOST) or await _async_discover_host(hass, device)
    try:
        await hass.async_add_executor_job(device.connect, host)
    except DysonException as err:
        raise ConfigEntryNotReady(f"Cannot connect to {device.serial} at {host}") from err

    coordinator = None
    if not isinstance(device, VACUUM_TYPES):

        async def _async_update_data() -> None:
            """Ask the device to push fresh environmental data."""
            try:
                await hass.async_add_executor_job(device.request_environmental_data)
            except DysonException as err:
                raise UpdateFailed("Failed to request environmental data") from err

        coordinator = DataUpdateCoordinator[None](
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"environmental_{device.serial}",
            update_method=_async_update_data,
            update_interval=ENVIRONMENTAL_DATA_UPDATE_INTERVAL,
        )

    entry.runtime_data = DysonLocalData(device=device, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, _async_get_platforms(device))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Dyson local."""
    if CONF_REGION in entry.data:
        return await hass.config_entries.async_unload_platforms(entry, CLOUD_PLATFORMS)

    device = entry.runtime_data.device
    if not await hass.config_entries.async_unload_platforms(entry, _async_get_platforms(device)):
        return False

    await hass.async_add_executor_job(device.disconnect)
    return True


@callback
def _async_get_platforms(device: DysonDevice) -> list[Platform]:
    """Return the platforms supported by a device."""
    if isinstance(device, VACUUM_TYPES):
        return [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.VACUUM]

    platforms = [
        Platform.BINARY_SENSOR,
        Platform.FAN,
        Platform.SELECT,
        Platform.SENSOR,
        Platform.SWITCH,
    ]
    if isinstance(device, (DysonPureHotCool, DysonPureHotCoolLink)):
        platforms.append(Platform.CLIMATE)
    if isinstance(device, DysonPurifierHumidifyCool):
        platforms.append(Platform.HUMIDIFIER)
    if hasattr(device, "filter_life") or hasattr(device, "carbon_filter_life") or hasattr(device, "hepa_filter_life"):
        platforms.append(Platform.BUTTON)
    return platforms


class DysonEntity(Entity):
    """Dyson entity base class."""

    _MESSAGE_TYPE = MessageType.STATE
    _attr_has_entity_name = True
    _attr_should_poll = False

    # Name and unique id suffix within the device; None marks the main entity.
    _sub_name: str | None = None
    _sub_unique_id: str | None = None

    def __init__(self, device: DysonDevice, name: str) -> None:
        """Initialize the entity."""
        self._device = device
        self._attr_name = self._sub_name
        self._attr_unique_id = device.serial
        if self._sub_unique_id is not None:
            self._attr_unique_id = f"{device.serial}-{self._sub_unique_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.serial)},
            manufacturer="Dyson",
            model=device.device_type,
            name=name,
            serial_number=device.serial,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to device messages."""
        await super().async_added_to_hass()
        self._device.add_message_listener(self._on_message)
        self.async_on_remove(partial(self._device.remove_message_listener, self._on_message))

    def _on_message(self, message_type: MessageType) -> None:
        """Handle a device message from the MQTT thread."""
        if self._MESSAGE_TYPE is None or message_type == self._MESSAGE_TYPE:
            self.schedule_update_ha_state()
