"""Packet encoders."""

import base64
import json

from custom_components.govee_ring import protocol as p


def _pt(msg: bytes) -> bytes:
    return base64.b64decode(json.loads(msg)["msg"]["data"]["pt"])


def test_enable_disable():
    assert json.loads(p.razer_enable())["msg"]["data"]["pt"] == "uwABsQEK"
    assert json.loads(p.razer_disable())["msg"]["data"]["pt"] == "uwABsQAL"


def test_frame_layout_and_checksum():
    raw = _pt(p.razer_frame([(160, 0, 255)] * 19 + [(0, 0, 0)], gradient=1))
    assert base64.b64encode(raw).decode().startswith("uwA+sAEU")
    assert raw[:6] == bytes([0xBB, 0x00, 2 + 3 * 20, 0xB0, 1, 20])
    assert len(raw) == 6 + 60 + 1
    x = 0
    for b in raw[:-1]:
        x ^= b
    assert raw[-1] == x


def test_colorwc_and_turn():
    assert json.loads(p.colorwc_msg(0, 0, 0, 0))["msg"] == {
        "cmd": "colorwc",
        "data": {"color": {"r": 0, "g": 0, "b": 0}, "colorTemInKelvin": 0},
    }
    assert json.loads(p.turn_msg(True))["msg"]["data"] == {"value": 1}
