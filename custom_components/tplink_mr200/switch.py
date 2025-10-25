from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import logging

from .const import DOMAIN, DEFAULT_USERNAME

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    client = hass.data[DOMAIN][config_entry.entry_id]["client"]

    switches = [
        DataFetchSwitch(coordinator, config_entry),
        # WiFiSwitch(coordinator, config_entry, client, 1, False),  # WiFi 2.4GHz
        # WiFiSwitch(coordinator, config_entry, client, 2, False),  # WiFi 5GHz
        # WiFiSwitch(coordinator, config_entry, client, 1, True),   # Guest 2.4GHz
        # WiFiSwitch(coordinator, config_entry, client, 2, True),   # Guest 5GHz
    ]

    async_add_entities(switches)

class DataFetchSwitch(SwitchEntity):
    def __init__(self, coordinator, config_entry):
        device_info = coordinator.data.get("device_info", {})
        device_name = device_info.get("model", "").lower().replace(" ", "_")
        self._coordinator = coordinator
        self._config_entry = config_entry
        self._attr_entity_category = EntityCategory.CONFIG
        self.entity_id = f"switch.{device_name}_data_fetch"
        self._attr_name = "Router data fetching"
        self._attr_unique_id = f"{device_name}_data_fetch"
        self._attr_icon = "mdi:connection"

    @property
    def device_info(self):
        device_info = self._coordinator.data.get("device_info", {})
        mac = device_info.get("mac_address")
        return {
            "identifiers": {(DOMAIN, mac)},
            "connections": {(dr.CONNECTION_NETWORK_MAC, mac)},
            "name": "TP-Link MR200",
            "manufacturer": device_info.get("manufacturer"),
            "model": device_info.get("model"),
            "hw_version": device_info.get("hw_version"),
            "sw_version": device_info.get("sw_version"),
            "configuration_url": device_info.get("device_url", "https://example.com")
        }

    @property
    def is_on(self) -> bool:
        return self.hass.data[DOMAIN].get(f"{self._config_entry.entry_id}_fetch_enabled", True)

    async def async_turn_on(self, **kwargs) -> None:
        self.hass.data[DOMAIN][f"{self._config_entry.entry_id}_fetch_enabled"] = True
        self.async_write_ha_state()
        await self._coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        self.hass.data[DOMAIN][f"{self._config_entry.entry_id}_fetch_enabled"] = False
        self.async_write_ha_state()


# class WiFiSwitch(CoordinatorEntity, SwitchEntity):

#     def __init__(self, coordinator, config_entry, client, band, is_guest):
#         super().__init__(coordinator)
#         self._client = client
#         self._config_entry = config_entry
#         self._band = band
#         self._is_guest = is_guest
#         self._attr_is_on = False
#         self._attr_entity_category = EntityCategory.CONFIG
        
#         device_info = coordinator.data.get("device_info", {})
#         device_name = device_info.get("model", "").lower().replace(" ", "_")
        
#         band_name = "2_4ghz" if band == 1 else "5ghz"
#         network_type = "guest" if is_guest else "wifi"
        
#         self._attr_name = f"WiFi {band_name.replace('_', '.')} {'Guest' if is_guest else ''}"
#         self._attr_unique_id = f"{device_name}_{network_type}_{band_name}"
#         self.entity_id = f"switch.{device_name}_{network_type}_{band_name}"
#         self._attr_icon = "mdi:wifi"

#     @property
#     def device_info(self):
#         device_info = self.coordinator.data.get("device_info", {})
#         mac = device_info.get("mac_address")
#         return {
#             "identifiers": {(DOMAIN, mac)},
#             "connections": {(dr.CONNECTION_NETWORK_MAC, mac)},
#             "name": "TP-Link MR200",
#             "manufacturer": device_info.get("manufacturer"),
#             "model": device_info.get("model"),
#             "hw_version": device_info.get("hw_version"),
#             "sw_version": device_info.get("sw_version"),
#             "configuration_url": device_info.get("device_url", "https://example.com")
#         }

#     @property
#     def available(self) -> bool:
#         return self.coordinator.last_update_success

#     async def async_added_to_hass(self):
#         await super().async_added_to_hass()
#         await self._async_update_state()

#     async def _async_update_state(self):
#         is_on = await self.hass.async_add_executor_job(
#             self._client.get_wifi_state, self._band, self._is_guest
#         )
#         self._attr_is_on = is_on
#         self.async_write_ha_state()

#     async def async_turn_on(self, **kwargs) -> None:
#         await self.hass.async_add_executor_job(
#             self._client.set_wifi_state, self._band, True, self._is_guest
#         )
#         await self._async_update_state()

#     async def async_turn_off(self, **kwargs) -> None:
#         await self.hass.async_add_executor_job(
#             self._client.set_wifi_state, self._band, False, self._is_guest
#         )
#         await self._async_update_state()

#     async def async_update(self):
#         await self._async_update_state()