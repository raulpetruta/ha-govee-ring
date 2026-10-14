"""Diagnostics redact the host."""

from homeassistant.core import HomeAssistant

from custom_components.govee_ring.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics(hass: HomeAssistant, entry, sent) -> None:
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["entry"]["data"]["host"] == "**REDACTED**"
    assert diag["streamer"]["streaming"] is False
