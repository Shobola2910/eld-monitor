"""
ELD Monitor — asosiy monitoring logikasi
Har CHECK_INTERVAL daqiqada ishga tushadi
"""
import asyncio
import logging
from datetime import datetime, timezone

import factor_client
import leader_client
import asana_client
import telegram_client
import database as db
from config import (
    DRIVE_THRESHOLD, SHIFT_THRESHOLD,
    BREAK_THRESHOLD, CYCLE_THRESHOLD
)

log = logging.getLogger("monitor")

# Driver oxirgi connection holati (disconnect alertini bir marta yuborish uchun)
_prev_connected: dict[str, bool] = {}


async def process_driver(driver: dict):
    """
    Bitta driver uchun:
    1. HOS tekshirish → Telegram alert
    2. Asana task yangilash
    """
    driver_id = driver["id"]
    name      = driver["name"]
    hos       = driver.get("hos", {})
    tg_group  = driver.get("tg_group_id")
    task_gid  = driver.get("asana_task_id")

    if "error" in hos:
        log.warning(f"[{name}] HOS xatosi: {hos['error']}")
        return

    connected = hos.get("connected", True)
    prev_conn = _prev_connected.get(driver_id, True)

    alerts = []

    # ─── Disconnect alert ───────────────────────────────────────────────
    if not connected and prev_conn:
        alerts.append(("disconnect", telegram_client.msg_disconnected(name)))
    elif connected and not prev_conn:
        alerts.append(("reconnect", telegram_client.msg_reconnected(name)))

    _prev_connected[driver_id] = connected

    if connected:
        # ─── HOS alertlar ───────────────────────────────────────────────
        drive = hos.get("drive_remaining_min")
        shift = hos.get("shift_remaining_min")
        brk   = hos.get("break_remaining_min")
        cycle = hos.get("cycle_remaining_min")

        if drive is not None and 0 < drive <= DRIVE_THRESHOLD:
            alerts.append(("hos_drive", telegram_client.msg_drive_low(name, drive)))

        if shift is not None and 0 < shift <= SHIFT_THRESHOLD:
            alerts.append(("hos_shift", telegram_client.msg_shift_low(name, shift)))

        if brk is not None and 0 < brk <= BREAK_THRESHOLD:
            alerts.append(("hos_break", telegram_client.msg_break_needed(name, brk)))

        if cycle is not None and 0 < cycle <= CYCLE_THRESHOLD:
            alerts.append(("hos_cycle", telegram_client.msg_cycle_low(name, cycle / 60)))

    # ─── Telegram yuborish (cooldown tekshirib) ─────────────────────────
    last_note = None
    for alert_type, message in alerts:
        if tg_group and await db.can_send_alert(driver_id):
            try:
                await telegram_client.send_message(tg_group, message)
                await db.mark_sent(driver_id)
                await db.log_alert(driver_id, alert_type, message)
                last_note = message[:80]  # Asana note uchun qisqaroq
                log.info(f"[{name}] Alert yuborildi: {alert_type}")
            except Exception as e:
                log.error(f"[{name}] Telegram xatosi: {e}")
        elif not tg_group:
            log.warning(f"[{name}] Telegram group ID yo'q — alert yuborilmadi")

    # ─── Asana sync ─────────────────────────────────────────────────────
    if task_gid:
        try:
            update = {
                "status":    hos.get("status", ""),
                "connected": connected,
            }
            if last_note:
                update["note"] = last_note
            await asana_client.update_driver_task(task_gid, update)
        except Exception as e:
            log.error(f"[{name}] Asana sync xatosi: {e}")


async def sync_drivers_from_eld():
    """
    Factor va Leader'dan driverlar ro'yxatini olib,
    DB ga qo'shish (yangi driverlar uchun)
    """
    platforms = []

    try:
        factor_drivers = await factor_client.get_drivers()
        platforms.extend(factor_drivers)
        log.info(f"Factor: {len(factor_drivers)} driver topildi")
    except Exception as e:
        log.error(f"Factor drivers xatosi: {e}")

    try:
        leader_drivers = await leader_client.get_drivers()
        platforms.extend(leader_drivers)
        log.info(f"Leader: {len(leader_drivers)} driver topildi")
    except Exception as e:
        log.error(f"Leader drivers xatosi: {e}")

    for d in platforms:
        existing = await db.get_driver(d["id"])
        if not existing:
            await db.upsert_driver({
                "id":           d["id"],
                "name":         d["name"],
                "platform":     d["platform"],
                "company":      d.get("company", ""),
                "tg_group_id":  None,
                "asana_task_id": None,
            })
            log.info(f"Yangi driver qo'shildi: {d['name']} ({d['platform']})")

    return platforms


async def run_monitoring_cycle():
    """Asosiy monitoring sikli — scheduler tomonidan chaqiriladi"""
    log.info("=== Monitoring sikli boshlandi ===")
    start = datetime.now(timezone.utc)

    # 1. Driverlarni yangilash
    await sync_drivers_from_eld()

    # 2. DB'dan barcha aktiv driverlarni olish
    drivers_db = await db.get_all_drivers()
    if not drivers_db:
        log.info("Hech qanday driver topilmadi")
        return

    # 3. Har bir driver uchun HOS olish va tekshirish
    # Factor driverlar
    factor_ids = {d["id"]: d for d in drivers_db if d["platform"] == "factor"}
    leader_ids = {d["id"]: d for d in drivers_db if d["platform"] == "leader"}

    factor_hos_data = {}
    leader_hos_data = {}

    try:
        for d in await factor_client.get_all_drivers_with_hos():
            if d["id"] in factor_ids:
                factor_hos_data[d["id"]] = d.get("hos", {})
    except Exception as e:
        log.error(f"Factor HOS xatosi: {e}")

    try:
        for d in await leader_client.get_all_drivers_with_hos():
            if d["id"] in leader_ids:
                leader_hos_data[d["id"]] = d.get("hos", {})
    except Exception as e:
        log.error(f"Leader HOS xatosi: {e}")

    # 4. Har bir driverni qayta ishlash
    tasks = []
    for d in drivers_db:
        hos = factor_hos_data.get(d["id"]) or leader_hos_data.get(d["id"]) or {}
        d["hos"] = hos
        tasks.append(process_driver(d))

    await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    log.info(f"=== Monitoring sikli tugadi ({elapsed:.1f}s, {len(drivers_db)} driver) ===")
