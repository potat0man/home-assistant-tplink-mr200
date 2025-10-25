from homeassistant import config_entries
import voluptuous as vol

from .const import DOMAIN, DEFAULT_HOST, DEFAULT_USERNAME, CONF_HOST, CONF_PASSWORD
from .mr200 import MR200Client, ConnectionFailedException, LoginFailedException

class MR200ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            try:
                client = MR200Client(user_input[CONF_HOST])
                await self.hass.async_add_executor_job(
                    client.login,
                    DEFAULT_USERNAME,
                    user_input[CONF_PASSWORD]
                )
                await self.hass.async_add_executor_job(client.logout)

                return self.async_create_entry(
                    title=f"TP-Link MR200 ({user_input[CONF_HOST]})",
                    data=user_input
                )
            except ConnectionFailedException:
                errors["base"] = "cannot_connect"
            except LoginFailedException:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )
