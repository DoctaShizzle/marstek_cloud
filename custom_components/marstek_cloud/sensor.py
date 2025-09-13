from datetime import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPower,
    UnitOfTime,
    UnitOfEnergy,
    CURRENCY_EURO,
)
from .const import DOMAIN, DEFAULT_CAPACITY_KWH
import logging

# Main battery data sensors
SENSOR_TYPES = {
    "soc": {"name": "State of Charge", "unit": PERCENTAGE},
    "charge": {"name": "Charge Power", "unit": UnitOfPower.WATT},
    "discharge": {"name": "Discharge Power", "unit": UnitOfPower.WATT},
    "load": {"name": "Load", "unit": UnitOfPower.WATT},
    "profit": {"name": "Profit", "unit": CURRENCY_EURO},
    "version": {"name": "Firmware Version", "unit": None},
    "sn": {"name": "Serial Number", "unit": None},
    "report_time": {"name": "Report Time", "unit": UnitOfTime.SECONDS}
}

# Diagnostic sensors for integration health
DIAGNOSTIC_SENSORS = {
    "last_update": {"name": "Last Update", "unit": None},
    "api_latency": {"name": "API Latency", "unit": "ms"},
    "connection_status": {"name": "Connection Status", "unit": None},
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Marstek sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    existing_entities = hass.states.async_entity_ids()  # Get existing entity IDs

    # Defensive check for coordinator data
    if coordinator.data:
        for device in coordinator.data:
            # Add main battery data sensors
            for key, meta in SENSOR_TYPES.items():
                unique_id = f"{device['devid']}_{key}"
                if unique_id not in existing_entities:  # Check if entity already exists
                    entities.append(MarstekSensor(coordinator, device, key, meta))

            # Add diagnostic sensors
            for key, meta in DIAGNOSTIC_SENSORS.items():
                unique_id = f"{device['devid']}_{key}"
                if unique_id not in existing_entities:  # Check if entity already exists
                    entities.append(MarstekDiagnosticSensor(coordinator, device, key, meta))

            # Add total charge per device sensor
            unique_id = f"{device['devid']}_total_charge"
            if unique_id not in existing_entities:  # Check if entity already exists
                entities.append(MarstekDeviceTotalChargeSensor(coordinator, device, "total_charge", {"name": "Total Charge", "unit": UnitOfEnergy.KILO_WATT_HOUR}))

    # Add total charge across all devices sensor
    unique_id = f"total_charge_all_devices_{entry.entry_id}"
    if unique_id not in existing_entities:  # Check if entity already exists
        entities.append(MarstekTotalChargeSensor(coordinator, entry.entry_id))

    # Add total power across all devices sensor
    unique_id = f"total_power_all_devices_{entry.entry_id}"
    if unique_id not in existing_entities:  # Check if entity already exists
        entities.append(MarstekTotalPowerSensor(coordinator, entry.entry_id))

    async_add_entities(entities)


class MarstekBaseSensor(SensorEntity):
    """Base class for Marstek sensors with shared device info."""

    def __init__(self, coordinator, device, key, meta):
        self.coordinator = coordinator
        self.devid = device["devid"]
        self.device_data = device
        self.key = key
        self._attr_name = f"{device['name']} {meta['name']}"
        self._attr_unique_id = f"{self.devid}_{self.key}"  # Ensure unique ID includes device ID and sensor key
        self._attr_native_unit_of_measurement = meta["unit"]

    @property
    def device_info(self):
        """Return metadata for the device registry."""
        return {
            "identifiers": {(DOMAIN, self.devid)},
            "name": self.device_data["name"],
            "manufacturer": "Marstek",
            "model": self.device_data.get("type", "Unknown"),
            "sw_version": str(self.device_data.get("version", "")),
            "serial_number": self.device_data.get("sn", ""),
        }


class MarstekSensor(MarstekBaseSensor):
    """Sensor for actual battery data."""

    @property
    def native_value(self):
        """Return the current value of the sensor."""
        # Defensive check for coordinator data
        if not self.coordinator.data:
            return None
            
        for dev in self.coordinator.data:
            if dev["devid"] == self.devid:
                return dev.get(self.key)
        return None

    async def async_update(self):
        """Manually trigger an update."""
        await self.coordinator.async_request_refresh()


class MarstekDiagnosticSensor(MarstekBaseSensor):
    """Sensor for integration diagnostics."""

    @property
    def native_value(self):
        """Return the diagnostic value."""
        if self.key == "last_update":
            if self.coordinator.last_update_success:
                return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return None

        elif self.key == "api_latency":
            return getattr(self.coordinator, "last_latency", None)

        elif self.key == "connection_status":
            return "online" if self.coordinator.last_update_success else "offline"

        return None


class MarstekTotalChargeSensor(SensorEntity):
    """Sensor to calculate the total charge across all devices."""

    def __init__(self, coordinator, entry_id):
        self.coordinator = coordinator
        self._attr_name = "Total Charge Across Devices"
        # Use entry_id for a stable unique ID
        self._attr_unique_id = f"total_charge_all_devices_{entry_id}"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    @property
    def native_value(self):
        """Return the total charge across all devices."""
        # Defensive check for coordinator data
        if not self.coordinator.data:
            return None
            
        total_charge = 0
        for device in self.coordinator.data:
            soc = device.get("soc", 0)
            capacity_kwh = device.get("capacity_kwh", DEFAULT_CAPACITY_KWH)
            total_charge += (soc / 100) * capacity_kwh
        return round(total_charge, 2)

    @property
    def extra_state_attributes(self):
        # Defensive check for coordinator data
        if not self.coordinator.data:
            return {"device_count": 0}
            
        return {
            "device_count": len(self.coordinator.data),
        }


class MarstekTotalPowerSensor(SensorEntity):
    """Sensor to calculate the total charge and discharge power across all devices."""

    def __init__(self, coordinator, entry_id):
        self.coordinator = coordinator
        self._attr_name = "Total Power Across Devices"
        # Use entry_id for a stable unique ID
        self._attr_unique_id = f"total_power_all_devices_{entry_id}"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    @property
    def native_value(self):
        """Return the total power (charge - discharge) across all devices."""
        # Defensive check for coordinator data
        if not self.coordinator.data:
            return None
            
        total_power = 0
        for device in self.coordinator.data:
            charge_power = device.get("charge", 0)
            discharge_power = device.get("discharge", 0)
            total_power += charge_power - discharge_power
        return round(total_power, 2)

    @property
    def extra_state_attributes(self):
        # Defensive check for coordinator data
        if not self.coordinator.data:
            return {"device_count": 0}
            
        return {
            "device_count": len(self.coordinator.data),
        }


class MarstekDeviceTotalChargeSensor(MarstekBaseSensor):
    """Sensor to calculate the total charge for a specific device."""

    @property
    def native_value(self):
        """Return the total charge for the device."""
        # Defensive check for coordinator data
        if not self.coordinator.data:
            return None
            
        # Find current device data from coordinator instead of using stale device_data
        for dev in self.coordinator.data:
            if dev["devid"] == self.devid:
                soc = dev.get("soc", 0)
                capacity_kwh = dev.get("capacity_kwh", DEFAULT_CAPACITY_KWH)
                return round((soc / 100) * capacity_kwh, 2)
        return None

    @property
    def extra_state_attributes(self):
        # Defensive check for coordinator data
        if not self.coordinator.data:
            return {
                "device_name": self.device_data.get("name"),
                "capacity_kwh": self.device_data.get("capacity_kwh", DEFAULT_CAPACITY_KWH),
            }
            
        # Find current device data from coordinator for attributes too
        for dev in self.coordinator.data:
            if dev["devid"] == self.devid:
                return {
                    "device_name": dev.get("name"),
                    "capacity_kwh": dev.get("capacity_kwh", DEFAULT_CAPACITY_KWH),
                }
        return {
            "device_name": self.device_data.get("name"),
            "capacity_kwh": self.device_data.get("capacity_kwh", DEFAULT_CAPACITY_KWH),
        }
