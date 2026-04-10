"""
Asana API client — driver task sync
"""
import httpx
from datetime import datetime, timezone
from config import ASANA_TOKEN, ASANA_PROJECT_ID

BASE = "https://app.asana.com/api/1.0"
HEADERS = {
    "Authorization": f"Bearer {ASANA_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# ─── Custom field GIDs ─────────────────────────────────────────────────────
# Asana custom field GID larni /setup endpoint orqali ko'rish mumkin
# Yoki: GET /projects/{id}/custom_field_settings
FIELD_STATUS         = None  # "Status" custom field GID
FIELD_CONNECT        = None  # "Connected" custom field GID  
FIELD_NOTE           = None  # "Last Note" custom field GID
FIELD_PROFILE_DATE   = None  # "Profile Form Updated" custom field GID


async def get_project_fields():
    """Project custom field GID larini olish"""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{BASE}/projects/{ASANA_PROJECT_ID}/custom_field_settings",
            headers=HEADERS
        )
        r.raise_for_status()
        fields = {}
        for item in r.json().get("data", []):
            cf = item.get("custom_field", {})
            fields[cf.get("name", "")] = cf.get("gid", "")
        return fields


async def get_tasks() -> list[dict]:
    """Project'dagi barcha tasklar"""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{BASE}/projects/{ASANA_PROJECT_ID}/tasks",
            headers=HEADERS,
            params={"opt_fields": "gid,name,custom_fields,notes"}
        )
        r.raise_for_status()
        return r.json().get("data", [])


async def find_task_by_name(driver_name: str) -> str | None:
    """Driver nomiga qarab task topish"""
    tasks = await get_tasks()
    for t in tasks:
        if driver_name.lower() in t.get("name", "").lower():
            return t["gid"]
    return None


async def create_driver_task(driver_name: str, platform: str, company: str) -> str:
    """Yangi driver task yaratish"""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{BASE}/tasks",
            headers=HEADERS,
            json={"data": {
                "name": driver_name,
                "projects": [ASANA_PROJECT_ID],
                "notes": f"Platform: {platform} | Company: {company}\nCreated by ELD Monitor"
            }}
        )
        r.raise_for_status()
        return r.json()["data"]["gid"]


async def update_driver_task(task_gid: str, fields: dict):
    """
    Driver task ni yangilash
    fields = {
        "status": "D" | "ON" | "OFF" | "SB",
        "connected": True/False,
        "note": "Last message text",
        "profile_date": "2024-01-15",
    }
    """
    if not task_gid:
        return

    # Notes ni update qilish (simple, har doim ishlaydi)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    note_lines = [f"🕐 Last sync: {now}"]

    if "status" in fields:
        note_lines.append(f"📍 Status: {fields['status']}")
    if "connected" in fields:
        icon = "🟢" if fields["connected"] else "🔴"
        note_lines.append(f"{icon} ELD: {'Connected' if fields['connected'] else 'Disconnected'}")
    if "note" in fields:
        note_lines.append(f"💬 Last TG: {fields['note']}")
    if "profile_date" in fields:
        note_lines.append(f"📋 Profile updated: {fields['profile_date']}")

    async with httpx.AsyncClient(timeout=15) as client:
        await client.put(
            f"{BASE}/tasks/{task_gid}",
            headers=HEADERS,
            json={"data": {"notes": "\n".join(note_lines)}}
        )


async def add_task_comment(task_gid: str, text: str):
    """Task ga comment qo'shish"""
    if not task_gid:
        return
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(
            f"{BASE}/tasks/{task_gid}/stories",
            headers=HEADERS,
            json={"data": {"text": text}}
        )
