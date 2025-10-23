"""Config flow for TP-Link MR200."""
import voluptuous as vol
import logging
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from .const import DOMAIN, DEFAULT_HOST, DEFAULT_USERNAME, CONF_HOST, CONF_PASSWORD
from .mr200 import MR200Client, ConnectionFailedException, LoginFailedException

_LOGGER = logging.getLogger(__name__)

class ArcherMR200ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a TP-Link MR200 config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            password = user_input[CONF_PASSWORD]
            
            try:
                client = MR200Client(host)
                await self.hass.async_add_executor_job(
                    client.login, DEFAULT_USERNAME, password
                )
                # Test device info retrieval
                device_info = await self.hass.async_add_executor_job(client.get_device_info)
                await self.hass.async_add_executor_job(client.logout)

                # Set unique ID based on MAC address for device uniqueness
                mac_address = device_info.get("macAddress", host.replace(".", ""))
                await self.async_set_unique_id(mac_address)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"TP-Link MR200 ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_PASSWORD: password,
                        "username": DEFAULT_USERNAME,
                    }
                )

            except ConnectionFailedException:
                errors["base"] = "cannot_connect"
                _LOGGER.error(f"Connection failed to {host}")
            except LoginFailedException:
                errors["base"] = "invalid_auth"
                _LOGGER.error(f"Login failed for {host}")
            except Exception as err:
                errors["base"] = "unknown"
                _LOGGER.error(f"Unexpected error during setup for {host}: %s", err)

        # Modern UI schema with selectors
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=DEFAULT_HOST): selector.TextSelector(),
                vol.Required(CONF_PASSWORD): selector.TextSelector(
                    type=selector.TextSelectorType.PASSWORD
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input=None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Current options
        current = self.config_entry.options
        scan_interval = current.get("scan_interval", 30)

        schema = vol.Schema(
            {
                vol.Optional(
                    "scan_interval",
                    default=scan_interval,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=10,
                        max=300,
                        step=5,
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )