"""Two lights per device: the streamed Ring and a proxy for the existing Main light."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.const import CONF_NAME, STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

from . import GoveeRingConfigEntry
from .config_flow import main_entity
from .const import DOMAIN
from .streamer import RingStreamer

DEFAULT_KELVIN = 4000


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GoveeRingConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    streamer = entry.runtime_data
    info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data[CONF_NAME],
        manufacturer="Govee",
        model="H60A4",
        model_id="H60A4",
    )
    entities: list[LightEntity] = [GoveeRing(entry, streamer, info)]
    if target := main_entity(entry):
        entities.append(GoveeMain(entry, target, streamer, info))
    else:
        # Main light was removed in the options: drop its registry entry too
        reg = er.async_get(hass)
        if stale := reg.async_get_entity_id("light", DOMAIN, f"{entry.entry_id}_main"):
            reg.async_remove(stale)
    async_add_entities(entities)


class GoveeRing(LightEntity, RestoreEntity):
    """The whole ring as one light (assumed state: the light never reports it)."""

    _attr_has_entity_name = True
    _attr_translation_key = "ring"
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_assumed_state = True
    _attr_should_poll = False

    def __init__(self, entry: GoveeRingConfigEntry, streamer: RingStreamer, info: DeviceInfo) -> None:
        self._s = streamer
        self._attr_unique_id = f"{entry.entry_id}_ring"
        self._attr_device_info = info
        self._attr_is_on = False
        self._attr_rgb_color = (255, 255, 255)
        self._attr_brightness = 255

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._s.add_listener(self._refresh))
        if (last := await self.async_get_last_state()) is not None:
            if rgb := last.attributes.get(ATTR_RGB_COLOR):
                self._attr_rgb_color = tuple(rgb)
            if bri := last.attributes.get(ATTR_BRIGHTNESS):
                self._attr_brightness = bri

    @callback
    def _refresh(self) -> None:
        self._attr_is_on = any(self._s.on[: self._s.ring])
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_rgb_color = kwargs.get(ATTR_RGB_COLOR, self._attr_rgb_color)
        self._attr_brightness = kwargs.get(ATTR_BRIGHTNESS, self._attr_brightness)
        await self._s.update(range(self._s.ring), self._attr_rgb_color, self._attr_brightness, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._s.update(range(self._s.ring), on=False)

    async def async_set_segments(
        self,
        segments: list[int] | None = None,
        rgb_color: tuple[int, int, int] | None = None,
        brightness_pct: int | None = None,
        gradient: list[tuple[int, int, int]] | None = None,
    ) -> None:
        s = self._s
        segs = list(range(s.ring)) if segments is None else segments
        if bad := [i for i in segs if not 0 <= i < s.ring]:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_segments",
                translation_placeholders={"segments": ", ".join(map(str, bad)), "max": str(s.ring - 1)},
            )
        for k, i in enumerate(segs):
            if gradient:
                s.rgb[i] = gradient[round(k * (len(gradient) - 1) / max(1, len(segs) - 1))]
            elif rgb_color:
                s.rgb[i] = rgb_color
            if brightness_pct is not None:
                s.bri[i] = round(brightness_pct * 255 / 100)
                s.on[i] = brightness_pct != 0
            else:
                s.on[i] = True
        await s.push()
        s.notify()


class GoveeMain(LightEntity):
    """Mirror of the existing whole-light entity (e.g. from govee_light_local)."""

    _attr_has_entity_name = True
    _attr_translation_key = "main"
    _attr_should_poll = False

    def __init__(
        self, entry: GoveeRingConfigEntry, target: str, streamer: RingStreamer, info: DeviceInfo
    ) -> None:
        self._t = target
        self._s = streamer
        self._last_kelvin = DEFAULT_KELVIN
        self._attr_unique_id = f"{entry.entry_id}_main"
        self._attr_device_info = info

    def _st(self) -> State | None:
        return self.hass.states.get(self._t)

    def _attr(self, key: str, default: Any = None) -> Any:
        st = self._st()
        return st.attributes.get(key, default) if st else default

    async def async_added_to_hass(self) -> None:
        if kelvin := self._attr(ATTR_COLOR_TEMP_KELVIN):
            self._last_kelvin = kelvin
        self.async_on_remove(async_track_state_change_event(self.hass, [self._t], self._changed))

    @callback
    def _changed(self, event: Event[EventStateChangedData]) -> None:
        new = event.data["new_state"]
        if new is not None:
            if kelvin := new.attributes.get(ATTR_COLOR_TEMP_KELVIN):
                self._last_kelvin = kelvin
            if new.state == STATE_OFF:
                # the light was powered off elsewhere: end ring streaming too
                self.hass.async_create_task(self._s.stop())
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        st = self._st()
        return st is not None and st.state != STATE_UNAVAILABLE

    @property
    def is_on(self) -> bool:
        st = self._st()
        return st is not None and st.state == STATE_ON

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        return {ColorMode(m) for m in self._attr("supported_color_modes", [ColorMode.ONOFF])}

    @property
    def color_mode(self) -> ColorMode | None:
        if m := self._attr("color_mode"):
            return ColorMode(m)
        # the target is on but reports no mode: fall back to one it supports
        return next(iter(self.supported_color_modes)) if self.is_on else None

    @property
    def brightness(self) -> int | None:
        return self._attr(ATTR_BRIGHTNESS)

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        return self._attr(ATTR_RGB_COLOR)

    @property
    def color_temp_kelvin(self) -> int | None:
        return self._attr(ATTR_COLOR_TEMP_KELVIN)

    @property
    def min_color_temp_kelvin(self) -> int:
        return self._attr("min_color_temp_kelvin", 2000)

    @property
    def max_color_temp_kelvin(self) -> int:
        return self._attr("max_color_temp_kelvin", 6500)

    async def async_turn_on(self, **kwargs: Any) -> None:
        keys = (ATTR_BRIGHTNESS, ATTR_RGB_COLOR, ATTR_COLOR_TEMP_KELVIN)
        data = {k: kwargs[k] for k in keys if k in kwargs}
        colour_given = bool(data.keys() - {ATTR_BRIGHTNESS})
        rgb = self._attr(ATTR_RGB_COLOR)
        stuck_black = bool(rgb) and tuple(rgb) == (0, 0, 0)  # left in black RGB by a ring session
        if colour_given:
            await self._s.stop()  # a whole-light colour would be hidden under the stream
            self._s.mode_dirty = False
        elif self._s.mode_dirty or stuck_black:
            await self._s.stop()
            data[ATTR_COLOR_TEMP_KELVIN] = self._last_kelvin  # bring back white
            self._s.mode_dirty = False
        await self.hass.services.async_call(
            "light", "turn_on", {"entity_id": self._t, **data}, blocking=True, context=self._context
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        # power off first; ending the stream first would flash the panel
        await self.hass.services.async_call(
            "light", "turn_off", {"entity_id": self._t}, blocking=True, context=self._context
        )
        await self._s.stop()

    async def async_set_segments(self, **kwargs: Any) -> None:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_ring")
