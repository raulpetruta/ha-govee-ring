"""Diagnostics for Govee Ring."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from . import GoveeRingConfigEntry

TO_REDACT = {CONF_HOST}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: GoveeRingConfigEntry
) -> dict[str, Any]:
    s = entry.runtime_data
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "streamer": {
            "streaming": s.streaming,
            "mode_dirty": s.mode_dirty,
            "on": s.on,
            "rgb": s.rgb,
            "bri": s.bri,
        },
    }
