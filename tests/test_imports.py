"""Guard against import-time breakage from Home Assistant API removals."""

from custom_components.dyson_local import (
    binary_sensor,
    button,
    camera,
    climate,
    config_flow,
    fan,
    humidifier,
    select,
    sensor,
    switch,
    utils,
    vacuum,
)

MODULES = [
    binary_sensor,
    button,
    camera,
    climate,
    config_flow,
    fan,
    humidifier,
    select,
    sensor,
    switch,
    utils,
    vacuum,
]


def test_platform_modules_import() -> None:
    """Every platform module must import against the installed HA version."""
    for module in MODULES:
        assert module.__name__.startswith("custom_components.dyson_local.")
