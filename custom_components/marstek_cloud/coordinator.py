import hashlib
import aiohttp
import asyncio
import async_timeout
import time
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed
from .const import API_LOGIN, API_DEVICES

_LOGGER = logging.getLogger(__name__)


class MarstekAuthError(Exception):
    """Authentication error for Marstek API."""
    pass


class MarstekAPIError(Exception):
    """General API error for Marstek."""
    pass

class MarstekAPI:
    def __init__(self, session: aiohttp.ClientSession, email: str, password: str):
        self._session = session
        self._email = email
        self._password = password
        self._token: Optional[str] = None

    async def _get_token(self) -> None:
        """Get authentication token from Marstek API."""
        try:
            md5_pwd = hashlib.md5(self._password.encode()).hexdigest()
            params = {"pwd": md5_pwd, "mailbox": self._email}
            
            async with async_timeout.timeout(10):
                async with self._session.post(API_LOGIN, params=params) as resp:
                    if resp.status != 200:
                        raise MarstekAPIError(f"API returned status {resp.status}")
                    
                    data = await resp.json()
                    if "token" not in data:
                        error_msg = data.get("msg", "Unknown login error")
                        raise MarstekAuthError(f"Login failed: {error_msg}")
                    
                    self._token = data["token"]
                    _LOGGER.info("Marstek: Obtained new API token")
                    
        except asyncio.TimeoutError as err:
            raise MarstekAPIError("Timeout during login") from err
        except aiohttp.ClientError as err:
            raise MarstekAPIError(f"Network error during login: {err}") from err

    async def get_devices(self) -> List[Dict[str, Any]]:
        """Get device list from Marstek API."""
        if not self._token:
            await self._get_token()

        try:
            params = {"token": self._token}
            async with async_timeout.timeout(10):
                async with self._session.get(API_DEVICES, params=params) as resp:
                    if resp.status != 200:
                        raise MarstekAPIError(f"API returned status {resp.status}")
                    
                    data = await resp.json()

                    # Handle token expiration or invalid token
                    if str(data.get("code")) in ("-1", "401", "403") or "token" in str(data).lower():
                        _LOGGER.warning("Marstek: Token expired or invalid, refreshing...")
                        await self._get_token()
                        params["token"] = self._token
                        async with self._session.get(API_DEVICES, params=params) as retry_resp:
                            if retry_resp.status != 200:
                                raise MarstekAPIError(f"API returned status {retry_resp.status} on retry")
                            data = await retry_resp.json()

                    # Handle specific error code 8 (no access permission)
                    if str(data.get("code")) == "8":
                        _LOGGER.error("Marstek: No access permission (code 8). Clearing token and will retry on next update.")
                        self._token = None  # Clear the token so a new one will be obtained on next attempt
                        raise MarstekAuthError(f"Access denied (code 8): {data.get('msg', 'Unknown error')}")

                    if "data" not in data:
                        error_msg = data.get("msg", f"Unknown error, response: {data}")
                        raise MarstekAPIError(f"Device fetch failed: {error_msg}")

                    return data["data"]
                    
        except asyncio.TimeoutError as err:
            raise MarstekAPIError("Timeout during device fetch") from err
        except aiohttp.ClientError as err:
            raise MarstekAPIError(f"Network error during device fetch: {err}") from err

class MarstekCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api: MarstekAPI, scan_interval: int):
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Marstek Cloud",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self.last_latency: Optional[float] = None

    async def _async_update_data(self) -> List[Dict[str, Any]]:
        """Fetch data from API endpoint."""
        try:
            start = time.perf_counter()
            devices = await self.api.get_devices()
            self.last_latency = round((time.perf_counter() - start) * 1000, 1)
            
            # Log successful recovery if we had previous failures
            if not self.last_update_success:
                _LOGGER.info("Marstek: Successfully recovered from connection issues")
            
            _LOGGER.debug(f"Marstek: Fetched {len(devices)} devices, latency: {self.last_latency}ms")
            return devices
        except MarstekAuthError as err:
            # Convert auth errors to ConfigEntryAuthFailed to trigger reauth flow
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except MarstekAPIError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
