"""
Factor ELD API client
Docs: https://app.factorhq.com/api/docs
"""
import httpx
from config import FACTOR_TOKEN, FACTOR_BASE

HEADERS = {
    "X-Api-Key": FACTOR_TOKEN,
    "Accept": "application/json",
    "Content-Type": "application/json",
}

async def get_drivers() -> list[dict]:
    """Barcha driverlarni olish"""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{FACTOR_BASE}/assets", headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        # Factor API response: { "data": [ { "id", "attributes": { "name", "status", ... } } ] }
        drivers = []
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            drivers.append({
                "id": f"factor_{item['id']}",
                "raw_id": item["id"],
                "name": attrs.get("name", "Unknown"),
                "platform": "factor",
                "company": attrs.get("company_name", ""),
                "status": attrs.get("status", "unknown"),  # online/offline
            })
        return drivers

async def get_driver_hos(raw_driver_id: str) -> dict | None:
    """Driver HOS ma'lumotlarini olish"""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{FACTOR_BASE}/assets/{raw_driver_id}/hos",
            headers=HEADERS
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
        hos = data.get("data", {}).get("attributes", {})

        # Minutlarga o'girish (Factor seconds qaytarishi mumkin)
        def to_min(val):
            if val is None:
                return None
            return round(val / 60) if val > 1000 else val  # seconds vs minutes

        return {
            "drive_remaining_min":  to_min(hos.get("drive_remaining")),
            "shift_remaining_min":  to_min(hos.get("shift_remaining")),
            "break_remaining_min":  to_min(hos.get("break_remaining")),
            "cycle_remaining_min":  to_min(hos.get("cycle_remaining")),
            "status": hos.get("duty_status", "unknown"),  # D/ON/OFF/SB
            "last_update": hos.get("updated_at"),
            "connected": hos.get("connection_status") == "connected",
        }

async def get_all_drivers_with_hos() -> list[dict]:
    """Driver + HOS ma'lumotlarini birgalikda olish"""
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
