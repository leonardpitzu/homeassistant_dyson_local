"""Utilities for Dyson Local."""

from __future__ import annotations

from typing import Any

from homeassistant.const import STATE_OFF

from .libdyson.const import ENVIRONMENTAL_FAIL, ENVIRONMENTAL_INIT, ENVIRONMENTAL_OFF

STATE_INIT = "init"
STATE_FAIL = "fail"


class environmental_property(property):
    """Environmental status property."""

    def __get__(self, obj: Any, type: type | None = ...) -> Any:
        """Get environmental property value."""
        value = super().__get__(obj, type)
        if value == ENVIRONMENTAL_OFF:
            return STATE_OFF
        if value == ENVIRONMENTAL_INIT:
            return STATE_INIT
        if value == ENVIRONMENTAL_FAIL:
            return STATE_FAIL
        return value
