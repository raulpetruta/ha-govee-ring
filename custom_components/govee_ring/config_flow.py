"""Config flow for Govee Ring."""

from __future__ import annotations

import ipaddress
import re
from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector
import voluptuous as vol

from .const import CONF_MAIN_ENTITY, DOMAIN

_HOSTNAME = re.compile(r"^(?=.{1,253}$)([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.?)+$")
_MAIN_SELECTOR = selector.EntitySelector(selector.EntitySelectorConfig(domain="light"))


def valid_host(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return bool(_HOSTNAME.match(host))
    return True


def main_entity(entry: ConfigEntry) -> str | None:
    """Main light entity: options win over the value set at creation."""
    if CONF_MAIN_ENTITY in entry.options:
        return entry.options[CONF_MAIN_ENTITY]
    return entry.data.get(CONF_MAIN_ENTITY)


class GoveeRingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a light by IP address.

    There is no connection test: replies arrive on UDP 4002, which the
    govee_light_local integration already listens on.
    """

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            if not valid_host(host):
                errors[CONF_HOST] = "invalid_host"
            else:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data={**user_input, CONF_HOST: host}
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_HOST): str,
                        vol.Required(CONF_NAME): str,
                        vol.Optional(CONF_MAIN_ENTITY): _MAIN_SELECTOR,
                    }
                ),
                user_input,
            ),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            if not valid_host(host):
                errors[CONF_HOST] = "invalid_host"
            else:
                if host != entry.unique_id:
                    await self.async_set_unique_id(host)
                    self._abort_if_unique_id_configured()
                return self.async_update_reload_and_abort(
                    entry, unique_id=host, data_updates={CONF_HOST: host}
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({vol.Required(CONF_HOST, default=entry.data[CONF_HOST]): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> GoveeRingOptionsFlow:
        return GoveeRingOptionsFlow()


class GoveeRingOptionsFlow(OptionsFlowWithReload):
    """Change (or remove) the linked main light entity."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data={CONF_MAIN_ENTITY: user_input.get(CONF_MAIN_ENTITY)})
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({vol.Optional(CONF_MAIN_ENTITY): _MAIN_SELECTOR}),
                {CONF_MAIN_ENTITY: main_entity(self.config_entry)},
            ),
        )
