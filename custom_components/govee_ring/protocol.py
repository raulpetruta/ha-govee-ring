"""Govee LAN protocol helpers (UDP port 4003). Pure functions plus a tiny sender."""

from __future__ import annotations

import asyncio
import base64
import json

from .const import PORT_CMD

RGB = tuple[int, int, int]


def _msg(cmd: str, data: dict) -> bytes:
    return json.dumps({"msg": {"cmd": cmd, "data": data}}).encode()


def _xor(data: list[int]) -> int:
    x = 0
    for v in data:
        x ^= v
    return x


def turn_msg(on: bool) -> bytes:
    """Power the light on or off."""
    return _msg("turn", {"value": int(on)})


def colorwc_msg(r: int, g: int, b: int, kelvin: int = 0) -> bytes:
    """Set a whole-light RGB colour (kelvin=0) or colour temperature."""
    return _msg("colorwc", {"color": {"r": r, "g": g, "b": b}, "colorTemInKelvin": kelvin})


def razer_msg(raw: bytes) -> bytes:
    """Wrap a raw DreamView/'razer' packet."""
    return _msg("razer", {"pt": base64.b64encode(raw).decode()})


def razer_enable() -> bytes:
    """Enter streaming mode."""
    return razer_msg(bytes([0xBB, 0x00, 0x01, 0xB1, 0x01, 0x0A]))


def razer_disable() -> bytes:
    """Leave streaming mode; the light returns to its previous state."""
    return razer_msg(bytes([0xBB, 0x00, 0x01, 0xB1, 0x00, 0x0B]))


def razer_frame(colors: list[RGB], gradient: int = 0) -> bytes:
    """One frame: BB lenHi lenLo B0 gradient N (R G B)*N xor."""
    length = 2 + 3 * len(colors)
    body = [0xBB, length >> 8, length & 0xFF, 0xB0, gradient, len(colors)]
    body += [c for rgb in colors for c in rgb]
    return razer_msg(bytes([*body, _xor(body)]))


class _Proto(asyncio.DatagramProtocol):
    pass


async def send(host: str, payload: bytes) -> None:
    """Fire-and-forget one UDP datagram to the light's command port."""
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(_Proto, remote_addr=(host, PORT_CMD))
    try:
        transport.sendto(payload)
    finally:
        transport.close()
