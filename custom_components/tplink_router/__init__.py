from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers import device_registry as dr
import async_timeout
import logging
from datetime import timedelta

# Import exceptions for error handling in the service
from .mr200 import MR200Client, LoginFailedException, ConnectionFailedException
from .const import DOMAIN, DEFAULT_USERNAME

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: Home Assistant, entry: ConfigEntry) -> bool:
    client = MR200Client(entry.data["host"])
    
    # Create device registry entry BEFORE first refresh to ensure linkage
    device_registry = dr.async_get(hass)
    
    # Get initial device info (basic info available without full login)
    try:
        basic_device_info = await hass.async_add_executor_job(client.get_device_info)
        mac_address_data = await hass.async_add_executor_job(client.get_wan_ip_connection)
        mac = mac_address_data.get("MACAddress", "")
        
        device_info = {
            "manufacturer": basic_device_info.get("manufacturer", "TP-Link"),
            "model": basic_device_info.get("modelName", "MR200"),
            "hw_version": basic_device_info.get("hardwareVersion", ""),
            "sw_version": basic_device_info.get("softwareVersion", ""),
            "device_url": f"http://{entry.data['host']}",
            "mac_address": mac,
        }
        
        if mac:
            device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,  # This links the device to the config entry
                identifiers={(DOMAIN, mac)},
                connections={(dr.CONNECTION_NETWORK_MAC, mac)},
                name="TP-Link MR200",
                manufacturer=device_info["manufacturer"],
                model=device_info["model"],
                hw_version=device_info["hw_version"],
                sw_version=device_info["sw_version"],
                configuration_url=device_info["device_url"],
            )
            _LOGGER.info(f"Created/Updated device registry entry for {mac}")
            
    except Exception as e:
        _LOGGER.warning(f"Could not create device registry entry: {e}")
    
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
                device_info_full = await hass.async_add_executor_job(client.get_device_info)
                wan_ip_conn = await hass.async_add_executor_job(client.get_wan_ip_connection)

                data["device_info"] = {
                    "manufacturer": device_info_full.get("manufacturer", ""),
                    "model": device_info_full.get("modelName", ""),
                    "hw_version": device_info_full.get("hardwareVersion", ""),
                    "sw_version": device_info_full.get("softwareVersion", ""),
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

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # --- START: IMPROVED SEND SMS SERVICE ---

    async def async_send_sms(service_call):
        """Handle the send_sms service call."""
        number = service_call.data.get("number")
        text = service_call.data.get("text")

        if not number or not text:
            _LOGGER.error("Send SMS service called without 'number' or 'text'")
            return

        # Get the device registry
        device_reg = dr.async_get(hass)
        
        # Get the device ID from the service call
        device_id = service_call.data.get("device")
        
        if not device_id:
            _LOGGER.error("Send SMS service called without 'device' parameter")
            return
        
        # Get the device entry
        device_entry = device_reg.async_get(device_id)
        if not device_entry:
            _LOGGER.error(f"Device ID {device_id} not found in device registry")
            return
        
        _LOGGER.debug(f"Found device: {device_entry.name} (ID: {device_id})")
        _LOGGER.debug(f"Device config entries: {list(device_entry.config_entries)}")
        
        # Find config entry IDs for this device that belong to our domain
        target_entry_ids = set()
        for config_entry_id in device_entry.config_entries:
            if config_entry_id in hass.data.get(DOMAIN, {}):
                target_entry_ids.add(config_entry_id)
        
        if not target_entry_ids:
            _LOGGER.warning(f"No TP-Link MR200 config entry found for device {device_id}")
            _LOGGER.info(f"Available config entries for this domain: {list(hass.data.get(DOMAIN, {}).keys())}")
            return

        # Send SMS from each targeted router
        for entry_id in target_entry_ids:
            entry_data = hass.data[DOMAIN][entry_id]
            client_instance = entry_data["client"]
            config = hass.config_entries.async_get_entry(entry_id).data
            username = config.get("username", DEFAULT_USERNAME)
            password = config["password"]

            try:
                _LOGGER.debug(f"Sending SMS via router {config['host']}")
                await hass.async_add_executor_job(client_instance.login, username, password)
                await hass.async_add_executor_job(client_instance.send_sms, number, text)
                await hass.async_add_executor_job(client_instance.logout)
                _LOGGER.info(f"Successfully sent SMS to {number} via {config['host']}")
            
            except (LoginFailedException, ConnectionFailedException) as err:
                _LOGGER.error(f"Failed to send SMS via {config['host']}: {err}")
            except Exception as err:
                _LOGGER.error(f"Unexpected error sending SMS via {config['host']}: {err}")
                # Attempt to logout even if send_sms failed
                try:
                    await hass.async_add_executor_job(client_instance.logout)
                except Exception:
                    pass

    # Register the service if it doesn't exist yet
    if not hass.services.has_service(DOMAIN, "send_sms"):
        _LOGGER.debug("Registering send_sms service")
        hass.services.async_register(DOMAIN, "send_sms", async_send_sms)
        
    # --- END: IMPROVED SEND SMS SERVICE ---

    return True

async def async_unload_entry(hass: Home Assistant, entry: ConfigEntry) -> bool:
    try:
        client = hass.data[DOMAIN][entry.entry_id]["client"]
        await hass.async_add_executor_job(client.logout)
    except Exception as err:
        _LOGGER.warning("Error during logout: %s", err)
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

        # If this was the last entry, unregister the service
        if not hass.data[DOMAIN]:
            _LOGGER.debug("Unregistering send_sms service")
            hass.services.async_remove(DOMAIN, "send_sms")

    return unload_okfrom homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers import device_registry as dr
import async_timeout
import logging
from datetime import timedelta

# Import exceptions for error handling in the service
from .mr200 import MR200Client, LoginFailedException, ConnectionFailedException
from .const import DOMAIN, DEFAULT_USERNAME

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: Home Assistant, entry: ConfigEntry) -> bool:
    client = MR200Client(entry.data["host"])
    
    # Create device registry entry BEFORE first refresh to ensure linkage
    device_registry = dr.async_get(hass)
    
    # Get initial device info (basic info available without full login)
    try:
        basic_device_info = await hass.async_add_executor_job(client.get_device_info)
        mac_address_data = await hass.async_add_executor_job(client.get_wan_ip_connection)
        mac = mac_address_data.get("MACAddress", "")
        
        device_info = {
            "manufacturer": basic_device_info.get("manufacturer", "TP-Link"),
            "model": basic_device_info.get("modelName", "MR200"),
            "hw_version": basic_device_info.get("hardwareVersion", ""),
            "sw_version": basic_device_info.get("softwareVersion", ""),
            "device_url": f"http://{entry.data['host']}",
            "mac_address": mac,
        }
        
        if mac:
            device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,  # This links the device to the config entry
                identifiers={(DOMAIN, mac)},
                connections={(dr.CONNECTION_NETWORK_MAC, mac)},
                name="TP-Link MR200",
                manufacturer=device_info["manufacturer"],
                model=device_info["model"],
                hw_version=device_info["hw_version"],
                sw_version=device_info["sw_version"],
                configuration_url=device_info["device_url"],
            )
            _LOGGER.info(f"Created/Updated device registry entry for {mac}")
            
    except Exception as e:
        _LOGGER.warning(f"Could not create device registry entry: {e}")
    
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
                device_info_full = await hass.async_add_executor_job(client.get_device_info)
                wan_ip_conn = await hass.async_add_executor_job(client.get_wan_ip_connection)

                data["device_info"] = {
                    "manufacturer": device_info_full.get("manufacturer", ""),
                    "model": device_info_full.get("modelName", ""),
                    "hw_version": device_info_full.get("hardwareVersion", ""),
                    "sw_version": device_info_full.get("softwareVersion", ""),
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

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # --- START: IMPROVED SEND SMS SERVICE ---

    async def async_send_sms(service_call):
        """Handle the send_sms service call."""
        number = service_call.data.get("number")
        text = service_call.data.get("text")

        if not number or not text:
            _LOGGER.error("Send SMS service called without 'number' or 'text'")
            return

        # Get the device registry
        device_reg = dr.async_get(hass)
        
        # Get the device ID from the service call
        device_id = service_call.data.get("device")
        
        if not device_id:
            _LOGGER.error("Send SMS service called without 'device' parameter")
            return
        
        # Get the device entry
        device_entry = device_reg.async_get(device_id)
        if not device_entry:
            _LOGGER.error(f"Device ID {device_id} not found in device registry")
            return
        
        _LOGGER.debug(f"Found device: {device_entry.name} (ID: {device_id})")
        _LOGGER.debug(f"Device config entries: {list(device_entry.config_entries)}")
        
        # Find config entry IDs for this device that belong to our domain
        target_entry_ids = set()
        for config_entry_id in device_entry.config_entries:
            if config_entry_id in hass.data.get(DOMAIN, {}):
                target_entry_ids.add(config_entry_id)
        
        if not target_entry_ids:
            _LOGGER.warning(f"No TP-Link MR200 config entry found for device {device_id}")
            _LOGGER.info(f"Available config entries for this domain: {list(hass.data.get(DOMAIN, {}).keys())}")
            return

        # Send SMS from each targeted router
        for entry_id in target_entry_ids:
            entry_data = hass.data[DOMAIN][entry_id]
            client_instance = entry_data["client"]
            config = hass.config_entries.async_get_entry(entry_id).data
            username = config.get("username", DEFAULT_USERNAME)
            password = config["password"]

            try:
                _LOGGER.debug(f"Sending SMS via router {config['host']}")
                await hass.async_add_executor_job(client_instance.login, username, password)
                await hass.async_add_executor_job(client_instance.send_sms, number, text)
                await hass.async_add_executor_job(client_instance.logout)
                _LOGGER.info(f"Successfully sent SMS to {number} via {config['host']}")
            
            except (LoginFailedException, ConnectionFailedException) as err:
                _LOGGER.error(f"Failed to send SMS via {config['host']}: {err}")
            except Exception as err:
                _LOGGER.error(f"Unexpected error sending SMS via {config['host']}: {err}")
                # Attempt to logout even if send_sms failed
                try:
                    await hass.async_add_executor_job(client_instance.logout)
                except Exception:
                    pass

    # Register the service if it doesn't exist yet
    if not hass.services.has_service(DOMAIN, "send_sms"):
        _LOGGER.debug("Registering send_sms service")
        hass.services.async_register(DOMAIN, "send_sms", async_send_sms)
        
    # --- END: IMPROVED SEND SMS SERVICE ---

    return True

async def async_unload_entry(hass: Home Assistant, entry: ConfigEntry) -> bool:
    try:
        client = hass.data[DOMAIN][entry.entry_id]["client"]
        await hass.async_add_executor_job(client.logout)
    except Exception as err:
        _LOGGER.warning("Error during logout: %s", err)
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

        # If this was the last entry, unregister the service
        if not hass.data[DOMAIN]:
            _LOGGER.debug("Unregistering send_sms service")
            hass.services.async_remove(DOMAIN, "send_sms")

    return unload_ok