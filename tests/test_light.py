"""Ring streaming and the Main light proxy."""

from datetime import timedelta

from homeassistant.components.light import DATA_COMPONENT as LIGHT_COMPONENT
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed, async_mock_service

from custom_components.govee_ring.const import DOMAIN

from .conftest import HOST

RING = "light.living_room_ring"
MAIN = "light.living_room_main_light"


async def _setup(hass, entry):
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_ring_on_sequence_and_keepalive(hass: HomeAssistant, entry, sent) -> None:
    await _setup(hass, entry)
    await hass.services.async_call(
        "light", "turn_on", {"entity_id": RING, "rgb_color": [255, 0, 0]}, blocking=True
    )
    cmds = [c for _, c, _ in sent]
    assert cmds == ["colorwc", "turn", "razer", "razer"]
    assert sent[0][2]["color"] == {"r": 0, "g": 0, "b": 0}
    assert all(h == HOST for h, _, _ in sent)
    assert hass.states.get(RING).state == "on"

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=26))
    await hass.async_block_till_done()
    assert [c for _, c, _ in sent][-1] == "razer" and len(sent) == 5

    await hass.services.async_call("light", "turn_off", {"entity_id": RING}, blocking=True)
    assert hass.states.get(RING).state == "off"


async def test_set_segments(hass: HomeAssistant, entry, sent) -> None:
    await _setup(hass, entry)
    await hass.services.async_call(
        DOMAIN,
        "set_segments",
        {"entity_id": RING, "segments": [0, 1], "rgb_color": [0, 255, 0]},
        blocking=True,
    )
    s = entry.runtime_data
    assert s.on[:3] == [True, True, False]
    assert s.rgb[0] == (0, 255, 0)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "set_segments", {"entity_id": RING, "segments": [19]}, blocking=True
        )


async def test_main_restores_white(hass: HomeAssistant, entry, sent) -> None:
    hass.states.async_set(
        "light.panel", "on", {"color_temp_kelvin": 3000, "supported_color_modes": ["color_temp", "rgb"]}
    )
    await _setup(hass, entry)
    calls: list[ServiceCall] = async_mock_service(hass, "light", "turn_on")
    await entry.runtime_data.update([0], on=True)  # a ring session leaves the lamp in black RGB
    assert entry.runtime_data.mode_dirty
    await hass.data[LIGHT_COMPONENT].get_entity(MAIN).async_turn_on()
    panel_calls = [c for c in calls if c.data.get("entity_id") == "light.panel"]
    assert panel_calls[-1].data["color_temp_kelvin"] == 3000
    assert entry.runtime_data.streaming is False


async def test_unload_stops_stream(hass: HomeAssistant, entry, sent) -> None:
    await _setup(hass, entry)
    await hass.services.async_call("light", "turn_on", {"entity_id": RING}, blocking=True)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert sent[-1][2]["pt"] == "uwABsQAL"
