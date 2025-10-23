from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers import device_registry as dr
import async_timeout
import logging
from datetime import timedelta

from .mr200 import MR200Client
from .const import DOMAIN, DEFAULT_USERNAME

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = MR200Client(entry.data["host"])
    
    async def async_update_data():
        try:
            async with async_timeout.timeout(10):
                username = entry.data.get("username", DEFAULT_USERNAME)
                password = entry.data["password"]
                
                await hass.async_add_executor_job(client.login, username, password)
                data = {}
                
                lte_link = await hass.async_add_executor_job(client.get_wan_lte_link_cfg)
                lte_intf = await hass.async_add_executor_job(client.get_wan_lte_intf_cfg)
                lte_wan = await hass.async_add_executor_job(client.get_lte_wan_cfg)
                wan_common = await hass.async_add_executor_job(client.get_wan_common_intf_cfg)
                clients = await hass.async_add_executor_job(client.get_clients)
                sms = await hass.async_add_executor_job(client.get_sms)
                device_info = await hass.async_add_executor_job(client.get_device_info)

                wan_ip_conn = await hass.async_add_executor_job(client.get_wan_ip_connection)

                data["device_info"] = {
                    "manufacturer": device_info.get("manufacturer", ""),
                    "model": device_info.get("modelName", ""),
                    "hw_version": device_info.get("hardwareVersion", ""),
                    "sw_version": device_info.get("softwareVersion", ""),
                    "device_url": f"http://{entry.data['host']}",
                    "mac_address": wan_ip_conn.get("MACAddress", ""),
                }

                if lte_link and len(lte_link) > 0:
                    link_data = lte_link[0]
                    signal = link_data.get("signalStrength", "0")
                    signal_map = {"1": 25, "2": 50, "3": 75, "4": 100}
                    
                    data["lte_signal_level"] = signal_map.get(signal, 0)
                    data["lte_enabled"] = link_data.get("enable", "0")
                    
                    network_types = {
                        "0": "No Service",
                        "1": "GSM",
                        "2": "WCDMA",
                        "3": "4G LTE",
                        "4": "TD-SCDMA",
                        "5": "CDMA 1x",
                        "6": "CDMA 1x Ev-Do",
                        "7": "4G+ LTE"
                    }
                    data["lte_network_type"] = link_data.get("networkType", "0")
                    data["lte_network_type_info"] = network_types.get(link_data.get("networkType"), "Unknown")
                    
                    sim_status = {
                        "0": "No SIM card detected or SIM card error.",
                        "1": "No SIM card detected.",
                        "2": "SIM card error.",
                        "3": "SIM card prepared.",
                        "4": "SIM locked.",
                        "5": "SIM unlocked. Authentication succeeded.",
                        "6": "PIN locked.",
                        "7": "SIM card is locked permanently.",
                        "8": "suspension of transmission",
                        "9": "Unopened"
                    }
                    data["lte_sim_status"] = link_data.get("simStatus", "0")
                    data["lte_sim_status_info"] = sim_status.get(link_data.get("simStatus"), "Unknown")
                    data["lte_connect_status"] = link_data.get("connectStatus", "0")
                
                if lte_intf:
                    data["lte_current_rx_speed"] = int(lte_intf.get("curRxSpeed", "0"))
                    data["lte_current_tx_speed"] = int(lte_intf.get("curTxSpeed", "0"))
                    data["lte_total_statistics"] = float(lte_intf.get("totalStatistics", "0"))
                
                data["lte_isp_name"] = lte_wan.get("profileName", "Unknown")
                data["connection_type"] = wan_common.get("WANAccessType", "Unknown")
                data["total_clients"] = len(clients) if clients else 0
                data["unread_sms"] = sum(1 for msg in sms if msg.get("unread") == "1") if sms else 0
                
                await hass.async_add_executor_job(client.logout)
                return data
        except Exception as err:
            _LOGGER.error("Error updating data: %s", err)
            raise

    coordinator = DataUpdateCoordinator(
        hass,
        logger=_LOGGER,
        name="TP-Link MR200",
        update_method=async_update_data,
        update_interval=timedelta(seconds=30)
    )

    await coordinator.async_config_entry_first_refresh()

    # Force update device registry using data from coordinator
    device_registry = dr.async_get(hass)
    device_info = coordinator.data.get("device_info", {})
    mac = device_info.get("mac_address", "")
    
    _LOGGER.debug(f"Device info: {device_info}")
    _LOGGER.debug(f"MAC address: {mac}")
    
    if mac:
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, mac)},
            name="TP-Link MR200",
            manufacturer=device_info.get("manufacturer", "TP-Link"),
            model=device_info.get("model", "MR200"),
            hw_version=device_info.get("hw_version"),
            sw_version=device_info.get("sw_version"),
            configuration_url=device_info.get("device_url"),
        )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    try:
        client = hass.data[DOMAIN][entry.entry_id]["client"]
        await hass.async_add_executor_job(client.logout)
    except Exception as err:
        _LOGGER.warning("Error during logout: %s", err)
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok