from homeassistant.components.button import ButtonEntity, ButtonDeviceClass, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client = hass.data[DOMAIN][config_entry.entry_id]["client"]
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    async_add_entities([RebootButton(coordinator, client)])

class RebootButton(ButtonEntity):
    def __init__(self, coordinator, client):
        device_info = coordinator.data.get("device_info", {})
        device_name = device_info.get("model", "").lower().replace(" ", "_")
        self._client = client
        self._coordinator = coordinator
        self._attr_device_class = ButtonDeviceClass.RESTART
        self._attr_entity_category = EntityCategory.CONFIG
        self.entity_id = f"button.{device_name}_reboot"
        self._attr_name = "Reboot"
        self._attr_unique_id = f"{device_name}_reboot"

    @property
    def device_info(self):
        device_info = self._coordinator.data.get("device_info", {})
        return {
            "identifiers": {(DOMAIN, "tplink_mr200")},
            "name": "TP-Link MR200",
            "manufacturer": device_info.get("manufacturer"),
            "model": device_info.get("model"),
            "hw_version": device_info.get("hw_version"),
            "sw_version": device_info.get("sw_version"),
            "configuration_url": device_info.get("device_url", "https://example.com")
        }

    async def async_press(self) -> None:
        await self.hass.async_add_executor_job(self._client.reboot)
