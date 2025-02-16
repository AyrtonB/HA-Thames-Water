"""Config flow for Thames Water integration."""

import aiohttp
import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN


class ThamesWaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Thames Water."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:

            if not errors:
                return self.async_create_entry(title="Thames Water", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(
                    "username", description={"suggested_value": "email@email.com"}
                ): str,
                vol.Required("password"): str,
                vol.Required("account_number"): str,
                vol.Required("meter_id"): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
