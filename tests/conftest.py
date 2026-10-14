"""Shared fixtures."""

from __future__ import annotations

import json
from unittest.mock import patch

from homeassistant.const import CONF_HOST, CONF_NAME
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.govee_ring.const import CONF_MAIN_ENTITY, DOMAIN

HOST = "192.168.1.50"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("custom_components.govee_ring.streamer.asyncio.sleep"):
        yield


@pytest.fixture
def sent():
    """Every payload sent to a light, decoded: list of (host, cmd, data)."""
    log: list[tuple[str, str, dict]] = []

    async def fake_send(host, payload):
        msg = json.loads(payload)["msg"]
        log.append((host, msg["cmd"], msg["data"]))

    with patch("custom_components.govee_ring.protocol.send", side_effect=fake_send):
        yield log


@pytest.fixture
def entry():
    return MockConfigEntry(
        domain=DOMAIN,
        title="Living Room",
        unique_id=HOST,
        data={CONF_HOST: HOST, CONF_NAME: "Living Room", CONF_MAIN_ENTITY: "light.panel"},
    )
