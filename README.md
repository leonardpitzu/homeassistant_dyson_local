# Dyson Local for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A custom [Home Assistant](https://www.home-assistant.io/) integration for **local control of Dyson devices** over their on-device MQTT API — fans, purifiers, heaters, humidifiers, and robot vacuums — with no cloud polling once set up.

This is a personal fork of [libdyson-wg/ha-dyson](https://github.com/libdyson-wg/ha-dyson) that **vendors the [libdyson-neon](https://github.com/libdyson-wg/libdyson-neon) library inside the integration** (one self-contained HACS install, no separate PyPI dependency) and adds **humidifier water-tank and filter fault sensors** on top.

## Features

Everything the upstream integration provides — `fan`, `humidifier`, `climate`, `sensor`, `binary_sensor`, `switch`, `select`, `button`, `vacuum`, and `camera` entities depending on your model — plus the additions below.

### Fault sensors (new in this fork)

The integration now subscribes to each fan-family device's `status/faults` MQTT topic and surfaces the fault flags Home Assistant could not see before:

| Entity | Devices | Description |
|---|---|---|
| `binary_sensor.<name>_water_tank_empty` | Humidify+Cool (PH0x) | On when the water tank runs empty (`tnke` warning). Device class **problem**. |
| `binary_sensor.<name>_filter_replacement` | All fans / purifiers | On when the device raises a filter fault (`fltr` warning). Device class **problem**. |

Both are diagnostic entities. Because faults are event-driven, an entity reads **unknown** until the device first reports its fault state (on connect, and whenever a fault changes).

This closes [ha-dyson #34](https://github.com/libdyson-wg/ha-dyson/issues/34) — automate a refill notification the moment your humidifier runs dry:

```yaml
automation:
  - alias: Dyson humidifier needs water
    triggers:
      - trigger: state
        entity_id: binary_sensor.bedroom_dyson_water_tank_empty
        to: "on"
    actions:
      - action: notify.mobile_app_phone
        data:
          message: The Dyson humidifier water tank is empty.
```

## Installation

### HACS (recommended)

1. Open HACS in your Home Assistant instance.
2. Go to **Integrations** → **⋮** → **Custom repositories**.
3. Add `https://github.com/leonardpitzu/homeassistant_dyson_local` as an **Integration**.
4. Search for **Dyson** and install it.
5. Restart Home Assistant.

### Manual

1. Copy the `custom_components/dyson_local` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

> The vendored `libdyson` library lives inside `custom_components/dyson_local/libdyson/`, so there is nothing else to install.

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**.
2. Search for **Dyson**.
3. Choose to set the device up via your **Dyson account** (to fetch credentials automatically) or **manually** with the device's serial, credential, and host.

The integration keeps the `dyson_local` domain, so it is a drop-in replacement for the upstream integration — existing entity IDs are preserved.

## Credits

- [libdyson-wg/ha-dyson](https://github.com/libdyson-wg/ha-dyson) — the upstream Home Assistant integration this fork is based on.
- [libdyson-wg/libdyson-neon](https://github.com/libdyson-wg/libdyson-neon) — the Dyson protocol library vendored here.
- The contributors to [ha-dyson #34](https://github.com/libdyson-wg/ha-dyson/issues/34) who reverse-engineered the `status/faults` topic and the `tnke` water-tank flag.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
