"""Govee Ring: control the ring of a Govee H60A4 ceiling light separately from its panel."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr, service
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import DOMAIN, SERVICE_SET_SEGMENTS
from .streamer import RingStreamer

PLATFORMS = [Platform.LIGHT]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type GoveeRingConfigEntry = ConfigEntry[RingStreamer]

_RGB = vol.All(vol.ExactSequence((cv.byte,) * 3), vol.Coerce(tuple))
SET_SEGMENTS_SCHEMA = {
    vol.Optional("segments"): vol.All(cv.ensure_list, [vol.Coerce(int)]),
    vol.Optional("rgb_color"): _RGB,
    vol.Optional("brightness_pct"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    vol.Optional("gradient"): vol.All(cv.ensure_list, [_RGB]),
}


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_SET_SEGMENTS,
        entity_domain="light",
        func="async_set_segments",
        schema=SET_SEGMENTS_SCHEMA,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GoveeRingConfigEntry) -> bool:
    host = entry.data[CONF_HOST]
    streamer = RingStreamer(hass, host)
    entry.runtime_data = streamer

    # 0.1.x keyed the device by IP; key it by entry so a new IP keeps the same device
    reg = dr.async_get(hass)
    for dev in dr.async_entries_for_config_entry(reg, entry.entry_id):
        if (DOMAIN, host) in dev.identifiers:
            reg.async_update_device(dev.id, new_identifiers={(DOMAIN, entry.entry_id)})

    async def _on_stop(_event: Event) -> None:
        await streamer.stop()

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _on_stop))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GoveeRingConfigEntry) -> bool:
    await entry.runtime_data.stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
