"""
Leader ELD API client
"""
import httpx
from config import LEADER_TOKEN, LEADER_BASE, LEADER_COMPANY_ID

HEADERS = {
    "Authorization": f"Bearer {LEADER_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

async def get_drivers() -> list[dict]:
    """Barcha driverlarni olish"""
    async with httpx.AsyncClient(timeout=15) as client:
        params = {}
        if LEADER_COMPANY_ID:
            params["company_id"] = LEADER_COMPANY_ID
        r = await client.get(f"{LEADER_BASE}/drivers", headers=HEADERS, params=params)
        r.raise_for_status()
        data = r.json()
        drivers = []
        for item in data.get("drivers", data if isinstance(data, list) else []):
            drivers.append({
                "id": f"leader_{item.get('id', item.get('driver_id'))}",
                "raw_id": item.get("id", item.get("driver_id")),
                "name": item.get("name", item.get("full_name", "Unknown")),
                "platform": "leader",
                "company": item.get("company", item.get("carrier_name", "")),
                "status": item.get("status", "unknown"),
            })
        return drivers

async def get_driver_hos(raw_driver_id: str) -> dict | None:
    """Driver HOS ma'lumotlarini olish"""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{LEADER_BASE}/drivers/{raw_driver_id}/hos",
            headers=HEADERS
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        hos = r.json()

        def to_min(val):
            if val is None:
                return None
            return round(val / 60) if val > 1000 else val

        return {
            "drive_remaining_min":  to_min(hos.get("drive_time_remaining", hos.get("driveRemaining"))),
            "shift_remaining_min":  to_min(hos.get("shift_time_remaining", hos.get("shiftRemaining"))),
            "break_remaining_min":  to_min(hos.get("break_time_remaining", hos.get("breakRemaining"))),
            "cycle_remaining_min":  to_min(hos.get("cycle_time_remaining", hos.get("cycleRemaining"))),
            "status": hos.get("duty_status", hos.get("dutyStatus", "unknown")),
            "last_update": hos.get("updated_at", hos.get("updatedAt")),
            "connected": hos.get("is_connected", hos.get("connected", True)),
        }

async def get_all_drivers_with_hos() -> list[dict]:
    drivers = await get_drivers()
    result = []
    for d in drivers:
        try:
            hos = await get_driver_hos(d["raw_id"])
            d["hos"] = hos or {}
        except Exception as e:
            d["hos"] = {"error": str(e)}
        result.append(d)
    return result
