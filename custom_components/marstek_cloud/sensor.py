from datetime import datetime
from typing import Any, Dict, List, Optional
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPower,
    UnitOfTime,
    UnitOfEnergy,
    CURRENCY_EURO,
)
from .const import DOMAIN, DEFAULT_CAPACITY_KWH
from .coordinator import MarstekCoordinator
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


async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Marstek sensors from a config entry."""
    coordinator: MarstekCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: List[SensorEntity] = []

    # Defensive check for coordinator data
    if coordinator.data:
        for device in coordinator.data:
            # Add main battery data sensors
            for key, meta in SENSOR_TYPES.items():
                entities.append(MarstekSensor(coordinator, device, key, meta))

            # Add diagnostic sensors
            for key, meta in DIAGNOSTIC_SENSORS.items():
                entities.append(MarstekDiagnosticSensor(coordinator, device, key, meta))

            # Add total charge per device sensor
            entities.append(MarstekDeviceTotalChargeSensor(
                coordinator, 
                device, 
                "total_charge", 
                {"name": "Total Charge", "unit": UnitOfEnergy.KILO_WATT_HOUR}
            ))

    # Add total charge across all devices sensor
    entities.append(MarstekTotalChargeSensor(coordinator, entry.entry_id))

    # Add total power across all devices sensor
    entities.append(MarstekTotalPowerSensor(coordinator, entry.entry_id))

    async_add_entities(entities)


class MarstekBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Marstek sensors with shared device info."""

    def __init__(
        self, 
        coordinator: MarstekCoordinator, 
        device: Dict[str, Any], 
        key: str, 
        meta: Dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self.devid: str = device["devid"]
        self.device_data: Dict[str, Any] = device
        self.key = key
        self._attr_name = f"{device['name']} {meta['name']}"
        self._attr_unique_id = f"{self.devid}_{self.key}"  # Ensure unique ID includes device ID and sensor key
        self._attr_native_unit_of_measurement = meta["unit"]

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    async def async_added_to_hass(self) -> None:
        """Connect to dispatcher when added to hass."""
        await super().async_added_to_hass()

    @property
    def device_info(self) -> Dict[str, Any]:
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
    def native_value(self) -> Optional[Any]:
        """Return the current value of the sensor."""
        # Defensive check for coordinator data
        if not self.coordinator.data:
            _LOGGER.debug(f"Marstek sensor {self._attr_unique_id}: No coordinator data available")
            return None
        
        _LOGGER.debug(f"Marstek sensor {self._attr_unique_id}: Checking {len(self.coordinator.data)} devices for devid {self.devid}")
        for dev in self.coordinator.data:
            if dev["devid"] == self.devid:
                value = dev.get(self.key)
                _LOGGER.debug(f"Marstek sensor {self._attr_unique_id}: Found device, key {self.key} = {value}")
                return value
        
        _LOGGER.debug(f"Marstek sensor {self._attr_unique_id}: Device {self.devid} not found in coordinator data")
        return None


class MarstekDiagnosticSensor(MarstekBaseSensor):
    """Sensor for integration diagnostics."""

    @property
    def native_value(self) -> Optional[Any]:
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


class MarstekTotalChargeSensor(CoordinatorEntity, SensorEntity):
    """Sensor to calculate the total charge across all devices."""

    def __init__(self, coordinator: MarstekCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_name = "Total Charge Across Devices"
        # Use entry_id for a stable unique ID
        self._attr_unique_id = f"total_charge_all_devices_{entry_id}"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        """Connect to dispatcher when added to hass."""
        await super().async_added_to_hass()

    @property
    def native_value(self) -> Optional[float]:
        """Return the total charge across all devices."""
        # Defensive check for coordinator data
        if not self.coordinator.data:
            _LOGGER.debug("Marstek total charge sensor: No coordinator data available")
            return None
        
        _LOGGER.debug(f"Marstek total charge sensor: Processing {len(self.coordinator.data)} devices")
        total_charge = 0.0
        for device in self.coordinator.data:
            soc = device.get("soc")
            capacity_kwh = device.get("capacity_kwh", DEFAULT_CAPACITY_KWH)
            if soc is not None and capacity_kwh is not None:
                device_charge = (soc / 100.0) * capacity_kwh
                total_charge += device_charge
                _LOGGER.debug(f"Marstek total charge sensor: Device {device.get('devid')} SOC={soc}% capacity={capacity_kwh}kWh charge={device_charge}kWh")
        
        result = round(total_charge, 2)
        _LOGGER.debug(f"Marstek total charge sensor: Total charge = {result}kWh")
        return result

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {"device_count": 0}
            
        return {
            "device_count": len(self.coordinator.data),
        }


class MarstekTotalPowerSensor(CoordinatorEntity, SensorEntity):
    """Sensor to calculate the total charge and discharge power across all devices."""

    def __init__(self, coordinator: MarstekCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_name = "Total Power Across Devices"
        # Use entry_id for a stable unique ID
        self._attr_unique_id = f"total_power_all_devices_{entry_id}"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        """Connect to dispatcher when added to hass."""
        await super().async_added_to_hass()

    @property
    def native_value(self) -> Optional[float]:
        """Return the total power (charge - discharge) across all devices."""
        # Defensive check for coordinator data
        if not self.coordinator.data:
            return None
            
        total_power = 0.0
        for device in self.coordinator.data:
            charge_power = device.get("charge", 0) or 0
            discharge_power = device.get("discharge", 0) or 0
            total_power += charge_power - discharge_power
        return round(total_power, 2)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {"device_count": 0}
            
        return {
            "device_count": len(self.coordinator.data),
        }


class MarstekDeviceTotalChargeSensor(MarstekBaseSensor):
    """Sensor to calculate the total charge for a specific device."""

    @property
    def native_value(self) -> Optional[float]:
        """Return the total charge for the device."""
        # Defensive check for coordinator data
        if not self.coordinator.data:
            return None
            
        # Find current device data from coordinator instead of using stale device_data
        for dev in self.coordinator.data:
            if dev["devid"] == self.devid:
                soc = dev.get("soc")
                capacity_kwh = dev.get("capacity_kwh", DEFAULT_CAPACITY_KWH)
                if soc is not None and capacity_kwh is not None:
                    return round((soc / 100.0) * capacity_kwh, 2)
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
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
