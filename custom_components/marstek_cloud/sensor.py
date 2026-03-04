from datetime import datetime
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
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
    "soc": {
        "name": "State of Charge",
        "unit": PERCENTAGE,
        "device_class": SensorDeviceClass.BATTERY,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "charge": {
        "name": "Charge Power",
        "unit": UnitOfPower.WATT,
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "discharge": {
        "name": "Discharge Power",
        "unit": UnitOfPower.WATT,
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "load": {
        "name": "Load",
        "unit": UnitOfPower.WATT,
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "profit": {
        "name": "Profit",
        "unit": CURRENCY_EURO,
        "device_class": SensorDeviceClass.MONETARY,
        "state_class": SensorStateClass.TOTAL,
    },
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
        self._attr_device_class = meta.get("device_class")
        self._attr_state_class = meta.get("state_class")

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
        self._attr_device_class = SensorDeviceClass.ENERGY_STORAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the total charge across all devices."""
        total_charge = 0
        for device in self.coordinator.data:
            soc = device.get("soc", 0)
            capacity_kwh = device.get("capacity_kwh", DEFAULT_CAPACITY_KWH)
            total_charge += (soc / 100) * capacity_kwh
        return round(total_charge, 2)

    @property
    def extra_state_attributes(self):
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
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the total power (charge - discharge) across all devices."""
        total_power = 0
        for device in self.coordinator.data:
            charge_power = device.get("charge", 0)
            discharge_power = device.get("discharge", 0)
            total_power += charge_power - discharge_power
        return round(total_power, 2)

    @property
    def extra_state_attributes(self):
        return {
            "device_count": len(self.coordinator.data),
        }


class MarstekDeviceTotalChargeSensor(MarstekBaseSensor):
    """Sensor to calculate the total charge for a specific device."""

    def __init__(self, coordinator, device, key, meta):
        super().__init__(coordinator, device, key, meta)
        self._attr_device_class = SensorDeviceClass.ENERGY_STORAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the total charge for the device."""
        soc = self.device_data.get("soc", 0)
        capacity_kwh = self.device_data.get("capacity_kwh", DEFAULT_CAPACITY_KWH)
        return round((soc / 100) * capacity_kwh, 2)

    @property
    def extra_state_attributes(self):
        return {
            "device_name": self.device_data.get("name"),
            "capacity_kwh": self.device_data.get("capacity_kwh", DEFAULT_CAPACITY_KWH),
        }
