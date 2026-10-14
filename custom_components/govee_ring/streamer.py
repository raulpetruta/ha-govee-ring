"""Keeps the colour of every ring zone and streams it to the light as DreamView frames.

Zone 19 drives the centre panel's RGB LEDs, so it is always sent black and only the
ring lights up. The light drops out of streaming ~60 s after the last frame, so a
keepalive re-sends the current frame every 25 s.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
import contextlib
from datetime import timedelta

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_interval

from . import protocol
from .const import DOMAIN, RING_ZONES, ZONES

KEEPALIVE = timedelta(seconds=25)
GRADIENT = 1  # blend between zones; gives the most even ring


class RingStreamer:
    """Streaming state for one light."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        self.hass = hass
        self.host = host
        self.ring = RING_ZONES
        self.rgb: list[protocol.RGB] = [(255, 255, 255)] * ZONES
        self.bri = [255] * ZONES
        self.on = [False] * ZONES
        self.streaming = False
        self.mode_dirty = False  # True once the light was forced into black RGB mode
        self._unsub: CALLBACK_TYPE | None = None
        self._listeners: list[Callable[[], None]] = []
        self._lock = asyncio.Lock()

    @callback
    def add_listener(self, cb: Callable[[], None]) -> CALLBACK_TYPE:
        """Register a state callback; returns an unsubscribe function."""
        self._listeners.append(cb)
        return lambda: self._listeners.remove(cb)

    @callback
    def notify(self) -> None:
        for cb in list(self._listeners):
            cb()

    def frame(self) -> bytes:
        cols = [
            tuple(round(c * self.bri[i] / 255) for c in self.rgb[i]) if self.on[i] else (0, 0, 0)
            for i in range(self.ring)
        ]
        return protocol.razer_frame([*cols, (0, 0, 0)], gradient=GRADIENT)  # panel zone dark

    async def _send(self, payload: bytes) -> None:
        try:
            await protocol.send(self.host, payload)
        except OSError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="send_failed",
                translation_placeholders={"host": self.host, "error": str(err)},
            ) from err

    async def update(
        self,
        idxs: Iterable[int],
        rgb: protocol.RGB | None = None,
        bri: int | None = None,
        on: bool | None = None,
    ) -> None:
        for i in idxs:
            if rgb is not None:
                self.rgb[i] = tuple(rgb)
            if bri is not None:
                self.bri[i] = bri
            if on is not None:
                self.on[i] = on
        await self.push()
        self.notify()

    async def push(self) -> None:
        async with self._lock:
            if not any(self.on) and not self.streaming:
                return
            if not self.streaming:
                # black RGB mode first (switches the warm-white panel off), then power on;
                # the other order makes the panel flash in its previous mode
                await self._send(protocol.colorwc_msg(0, 0, 0, 0))
                self.mode_dirty = True
                await asyncio.sleep(0.4)
                await self._send(protocol.turn_msg(True))
                await asyncio.sleep(0.4)
                await self._send(protocol.razer_enable())
                await asyncio.sleep(0.3)
                self.streaming = True
                self._unsub = async_track_time_interval(self.hass, self._keepalive, KEEPALIVE)
            await self._send(self.frame())

    async def _keepalive(self, _now) -> None:
        with contextlib.suppress(HomeAssistantError):  # next tick retries
            await self._send(self.frame())

    async def stop(self) -> None:
        async with self._lock:
            if self._unsub:
                self._unsub()
                self._unsub = None
            self.on = [False] * ZONES
            if self.streaming:
                self.streaming = False
                with contextlib.suppress(HomeAssistantError):
                    await self._send(protocol.razer_disable())
        self.notify()
