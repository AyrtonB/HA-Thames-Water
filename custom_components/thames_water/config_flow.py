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
            # Validate the Selenium URL
            selenium_url = user_input.get("selenium_url")
            if not await self._test_selenium_url(selenium_url):
                errors["selenium_url"] = "Cannot connect to Selenium URL"

            if not errors:
                return self.async_create_entry(title="Thames Water", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(
                    "username", description={"suggested_value": "email@email.com"}
                ): str,
                vol.Required("password"): str,
                vol.Required(
                    "selenium_url",
                    description={"suggested_value": "http://localhost:4444/wd/hub"},
                ): str,
                vol.Required("account_number"): str,
                vol.Required("meter_id"): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def _test_selenium_url(self, selenium_url):
        """Test if the Selenium URL is accessible."""
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(selenium_url) as response,
            ):
                return response.status == 200
        except (aiohttp.ClientError, TimeoutError):
            return False
