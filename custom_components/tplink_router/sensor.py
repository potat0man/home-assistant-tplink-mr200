from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    entities = [
        Sensor(coordinator, "connection_type", "Connection Type", None),
        Sensor(coordinator, "total_clients", "Total Clients", None),
        Sensor(coordinator, "unread_sms", "Unread SMS", None, "total"),
        Sensor(coordinator, "lte_signal_level", "LTE Signal Level", "%"),
        Sensor(coordinator, "lte_enabled", "LTE Enabled", None),
        Sensor(coordinator, "lte_isp_name", "LTE ISP Name", None),
        Sensor(coordinator, "lte_network_type_info", "LTE Network Type Info", None),
        Sensor(coordinator, "lte_network_type", "LTE Network Type", None),
        Sensor(coordinator, "lte_sim_status_info", "LTE SIM Status Info", None),
        Sensor(coordinator, "lte_sim_status", "LTE SIM Status", None),
        Sensor(coordinator, "lte_connect_status", "LTE Connection Status", None),
        Sensor(coordinator, "lte_rx_speed", "LTE Current RX Speed", "B/s"),
        Sensor(coordinator, "lte_tx_speed", "LTE Current TX Speed", "B/s"),
        Sensor(coordinator, "lte_total_statistics", "LTE Total Statistics", "B", "total"),
    ]
    
    async_add_entities(entities)

class Sensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, key, name, unit, state_class=None):
        super().__init__(coordinator)
        device_info = coordinator.data.get("device_info", {})
        device_name = device_info.get("model", "").lower().replace(" ", "_")
        self._key = key
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"{device_name}_{key}"
        self.entity_id = f"sensor.{device_name}_{key}"

        if state_class:
            self._attr_state_class = state_class
        elif key in ["lte_rx_speed", "lte_tx_speed", "lte_signal_level", "total_clients", "unread_sms"]:
            self._attr_state_class = SensorStateClass.MEASUREMENT
            
        if key in ["lte_rx_speed", "lte_tx_speed"]:
            self._attr_device_class = SensorDeviceClass.DATA_RATE
        elif key == "lte_total_statistics":
            self._attr_device_class = SensorDeviceClass.DATA_SIZE

    @property
    def device_info(self):
        device_info = self.coordinator.data.get("device_info", {})
        return {
            "identifiers": {(DOMAIN, "tplink_mr200")},
            "name": "TP-Link MR200",
            "manufacturer": device_info.get("manufacturer"),
            "model": device_info.get("model"),
            "hw_version": device_info.get("hw_version"),
            "sw_version": device_info.get("sw_version"),
            "configuration_url": device_info.get("device_url", "https://example.com")
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key, 0)
