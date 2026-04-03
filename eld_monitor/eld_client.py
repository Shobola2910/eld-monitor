"""
ELD API Client
Supports Factor ELD and Leader ELD

NOTE: ELD API endpoints are based on common patterns.
      If you get 404 errors, check the API documentation
      for Factor ELD: https://developer.factorhq.com
      for Leader ELD: contact their support for API docs.
"""

import aiohttp
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class ELDDriver:
    """Represents a driver with their current HOS data."""
    def __init__(self, data: dict, account_name: str):
        self.id = data.get("id") or data.get("driver_id", "")
        self.full_name = self._extract_name(data)
        self.status = data.get("current_duty_status", data.get("duty_status", "unknown"))
        self.status_since = data.get("current_status_since") or data.get("duty_status_start_time")
        self.connected = data.get("eld_connection_status", "connected") != "disconnected"
        self.account_name = account_name

        # HOS clocks (in seconds, will be converted to hours)
        hos = data.get("hos_clocks") or data.get("hos") or {}
        self.drive_remaining_sec = hos.get("drive", {}).get("time_remaining") or \
                                    data.get("drive_remaining_seconds", 0)
        self.shift_remaining_sec = hos.get("shift", {}).get("time_remaining") or \
                                    data.get("shift_remaining_seconds", 0)
        self.break_remaining_sec = hos.get("break", {}).get("time_remaining") or \
                                    data.get("break_remaining_seconds", 0)
        self.cycle_remaining_sec = hos.get("cycle", {}).get("time_remaining") or \
                                    data.get("cycle_remaining_seconds", 0)

        # Violation flags
        self.drive_violation = data.get("drive_violation", False)
        self.has_pti = data.get("has_pti", True)

        # Profile/certification
        self.last_profile_update = data.get("last_profile_updated_at") or \
                                    data.get("form_updated_at")
        self.logs_certified = data.get("logs_certified", True)
        self.uncertified_days = data.get("uncertified_log_days", 0)

        # Raw data for debugging
        self._raw = data

    def _extract_name(self, data: dict) -> str:
        if data.get("full_name"):
            return data["full_name"]
        first = data.get("first_name", "")
        last = data.get("last_name", "")
        if first or last:
            return f"{first} {last}".strip()
        return data.get("name", data.get("username", "Unknown Driver"))

    @property
    def drive_remaining_hours(self) -> float:
        return self.drive_remaining_sec / 3600

    @property
    def shift_remaining_hours(self) -> float:
        return self.shift_remaining_sec / 3600

    @property
    def break_remaining_hours(self) -> float:
        return self.break_remaining_sec / 3600

    @property
    def cycle_remaining_hours(self) -> float:
        return self.cycle_remaining_sec / 3600

    def status_duration_minutes(self) -> Optional[float]:
        """Returns how many minutes the driver has been in the current status."""
        if not self.status_since:
            return None
        try:
            if isinstance(self.status_since, str):
                since = datetime.fromisoformat(self.status_since.replace("Z", "+00:00"))
            else:
                since = datetime.fromtimestamp(self.status_since, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            return (now - since).total_seconds() / 60
        except Exception:
            return None

    def __repr__(self):
        return f"<Driver {self.full_name} | {self.status} | drive:{self.drive_remaining_hours:.1f}h>"


class FactorELDClient:
    """
    Factor ELD (factorhq.com) API client.
    API base: https://api.factorhq.com
    Auth: Bearer token in Authorization header
    
    NOTE: Adjust endpoint paths based on the actual Factor ELD API docs.
    """

    BASE_URL = "https://api.factorhq.com"
    # Alternative base URLs to try if the above doesn't work:
    # "https://app.factorhq.com/api"
    # "https://mobile.factorhq.com/v1"

    def __init__(self, token: str, base_url: Optional[str] = None, account_name: str = "Factor ELD"):
        self.token = token
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.account_name = account_name
        self._session: Optional[aiohttp.ClientSession] = None

    def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "ELDMonitor/1.0",
                }
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get(self, path: str) -> dict:
        session = self._get_session()
        url = f"{self.base_url}{path}"
        try:
            async with session.get(url) as resp:
                if resp.status == 401:
                    raise PermissionError(f"Token expired or invalid for {self.account_name}")
                if resp.status == 404:
                    logger.warning(f"Endpoint not found: {url} — check API docs")
                    return {}
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as e:
            logger.error(f"[{self.account_name}] API request failed: {url} — {e}")
            raise

    async def get_drivers(self) -> list[ELDDriver]:
        """
        Fetch all drivers from Factor ELD.
        Tries multiple endpoint patterns.
        """
        endpoints_to_try = [
            "/v1/company/drivers",
            "/v2/drivers",
            "/v1/drivers",
            "/api/v1/drivers",
        ]
        
        for endpoint in endpoints_to_try:
            try:
                data = await self._get(endpoint)
                if data:
                    # Factor ELD typically returns { "data": [ ...drivers ] }
                    drivers_raw = data.get("data", data) if isinstance(data, dict) else data
                    if isinstance(drivers_raw, list):
                        logger.info(f"[{self.account_name}] Fetched {len(drivers_raw)} drivers via {endpoint}")
                        return [ELDDriver(d, self.account_name) for d in drivers_raw]
            except Exception as e:
                logger.debug(f"[{self.account_name}] Endpoint {endpoint} failed: {e}")
                continue
        
        logger.error(f"[{self.account_name}] Could not fetch drivers — check API endpoint config")
        return []

    async def get_driver_hos(self, driver_id: str) -> dict:
        """Get HOS clocks for a specific driver."""
        endpoints_to_try = [
            f"/v1/drivers/{driver_id}/hos_clocks",
            f"/v2/drivers/{driver_id}/hos",
            f"/v1/hos_logs?driver_id={driver_id}&latest=true",
        ]
        for endpoint in endpoints_to_try:
            try:
                data = await self._get(endpoint)
                if data:
                    return data
            except Exception:
                continue
        return {}

    async def get_driver_status(self, driver_id: str) -> dict:
        """Get current duty status for a driver."""
        try:
            return await self._get(f"/v1/drivers/{driver_id}/duty_status")
        except Exception:
            return {}

    async def get_all_driver_data(self) -> list[ELDDriver]:
        """
        Fetch drivers with their HOS data.
        Some ELD APIs include HOS in the driver list endpoint; 
        others require separate calls.
        """
        drivers = await self.get_drivers()
        
        # If HOS data wasn't included, fetch separately
        for driver in drivers:
            if driver.drive_remaining_sec == 0 and driver.shift_remaining_sec == 0:
                try:
                    hos_data = await self.get_driver_hos(driver.id)
                    if hos_data:
                        hos = hos_data.get("data", hos_data)
                        driver.drive_remaining_sec = hos.get("drive_remaining_seconds", 0)
                        driver.shift_remaining_sec = hos.get("shift_remaining_seconds", 0)
                        driver.break_remaining_sec = hos.get("break_remaining_seconds", 0)
                        driver.cycle_remaining_sec = hos.get("cycle_remaining_seconds", 0)
                except Exception as e:
                    logger.debug(f"Could not fetch HOS for driver {driver.full_name}: {e}")
        
        return drivers


class LeaderELDClient:
    """
    Leader ELD API client.
    API base: https://api.leadereld.com (adjust if needed)
    Auth: Bearer token
    """

    BASE_URL = "https://api.leadereld.com"

    def __init__(self, token: str, base_url: Optional[str] = None, account_name: str = "Leader ELD"):
        self.token = token
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.account_name = account_name
        self._session: Optional[aiohttp.ClientSession] = None

    def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "ELDMonitor/1.0",
                }
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get(self, path: str) -> dict:
        session = self._get_session()
        url = f"{self.base_url}{path}"
        try:
            async with session.get(url) as resp:
                if resp.status == 401:
                    raise PermissionError(f"Token expired or invalid for {self.account_name}")
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as e:
            logger.error(f"[{self.account_name}] API request failed: {url} — {e}")
            raise

    async def get_all_driver_data(self) -> list[ELDDriver]:
        """
        Fetch all drivers with HOS data from Leader ELD.
        Adjust endpoints based on Leader ELD API documentation.
        """
        endpoints_to_try = [
            "/v1/drivers",
            "/api/drivers",
            "/api/v1/company/drivers",
            "/v2/drivers",
        ]
        
        for endpoint in endpoints_to_try:
            try:
                data = await self._get(endpoint)
                if data:
                    drivers_raw = data.get("data", data) if isinstance(data, dict) else data
                    if isinstance(drivers_raw, list):
                        logger.info(f"[{self.account_name}] Fetched {len(drivers_raw)} drivers via {endpoint}")
                        return [ELDDriver(d, self.account_name) for d in drivers_raw]
            except Exception as e:
                logger.debug(f"[{self.account_name}] Endpoint {endpoint} failed: {e}")
                continue
        
        return []


def create_eld_client(account_config: dict):
    """Factory function — creates the correct ELD client based on config."""
    eld_type = account_config.get("type", "factor").lower()
    token = account_config["token"]
    base_url = account_config.get("base_url")
    name = account_config.get("name", "ELD Account")

    if eld_type == "factor":
        return FactorELDClient(token=token, base_url=base_url, account_name=name)
    elif eld_type == "leader":
        return LeaderELDClient(token=token, base_url=base_url, account_name=name)
    else:
        raise ValueError(f"Unknown ELD type: {eld_type}")
