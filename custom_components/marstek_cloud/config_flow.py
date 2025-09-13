import voluptuous as vol
from typing import Any, Dict, Optional
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, DEFAULT_CAPACITY_KWH
from .coordinator import MarstekAPI, MarstekAuthError, MarstekAPIError

DATA_SCHEMA = vol.Schema({
    vol.Required("email"): str,
    vol.Required("password"): str,
    vol.Required(
        "scan_interval",
        default=DEFAULT_SCAN_INTERVAL
    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
    vol.Optional("default_capacity_kwh", default=5.12): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=100))  # Rename capacity_kwh to default_capacity_kwh
})

class MarstekConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            # Test the connection before saving
            try:
                await self._test_connection(user_input["email"], user_input["password"])
            except MarstekAuthError:
                errors["base"] = "invalid_auth"
            except MarstekAPIError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="Marstek Cloud",
                    data={
                        "email": user_input["email"],
                        "password": user_input["password"],
                        "scan_interval": user_input["scan_interval"],
                        "default_capacity_kwh": user_input.get("default_capacity_kwh", DEFAULT_CAPACITY_KWH)
                    }
                )
        
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors
        )

    async def _test_connection(self, email: str, password: str) -> None:
        """Test if we can authenticate with the given credentials."""
        session = async_get_clientsession(self.hass)
        api = MarstekAPI(session, email, password)
        # This will raise MarstekAuthError or MarstekAPIError if there's an issue
        await api.get_devices()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return MarstekOptionsFlow(config_entry)


class MarstekOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Marstek integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry  # Use a private attribute to avoid deprecation warnings

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None):
        """Manage the options for the integration."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Generate a schema for editing capacity_kwh for each battery with descriptions
        options = self._config_entry.options
        data_schema = {}
        
        # Handle missing devices key gracefully
        devices = self._config_entry.data.get("devices", [])
        if not devices:
            # Instead of aborting, show a message and allow scan interval configuration
            data_schema[vol.Optional(
                "scan_interval",
                default=options.get("scan_interval", DEFAULT_SCAN_INTERVAL),
                description={"suggested_value": DEFAULT_SCAN_INTERVAL}
            )] = vol.All(vol.Coerce(int), vol.Range(min=10, max=3600))
            
            return self.async_show_form(
                step_id="init", 
                data_schema=vol.Schema(data_schema),
                description_placeholders={
                    "note": "No devices found. You can still configure the scan interval. Devices will appear after the integration connects successfully."
                }
            )

        # Add scan interval option
        data_schema[vol.Optional(
            "scan_interval",
            default=options.get("scan_interval", DEFAULT_SCAN_INTERVAL),
            description={"suggested_value": DEFAULT_SCAN_INTERVAL}
        )] = vol.All(vol.Coerce(int), vol.Range(min=10, max=3600))

        # Add capacity options for each device
        for device in devices:
            devid = device["devid"]
            name = device["name"]
            description = f"Set the capacity (in kWh) for {name}"
            data_schema[vol.Optional(
                f"{devid}_capacity_kwh",
                default=options.get(f"{devid}_capacity_kwh", DEFAULT_CAPACITY_KWH),
                description={"suggested_value": DEFAULT_CAPACITY_KWH, "description": description}
            )] = vol.All(vol.Coerce(float), vol.Range(min=0.1, max=100))

        return self.async_show_form(step_id="init", data_schema=vol.Schema(data_schema))
