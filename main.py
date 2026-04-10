"""
ELD Monitor — FastAPI asosiy dastur
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import database as db
import monitor
import asana_client
import telegram_client
from config import CHECK_INTERVAL, ASANA_PROJECT_ID

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
log = logging.getLogger("main")

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.init_db()
    log.info("DB ishga tushdi")

    # Telegram client ulanish
    try:
        await telegram_client.start_client()
        log.info("Telegram ulandi")
    except Exception as e:
        log.warning(f"Telegram ulanmadi: {e}")

    # Scheduler boshlash
    scheduler.add_job(
        monitor.run_monitoring_cycle,
        "interval",
        minutes=CHECK_INTERVAL,
        id="eld_monitor",
        next_run_time=datetime.now(timezone.utc)  # darhol birinchi marta ishga tushirish
    )
    scheduler.start()
    log.info(f"Scheduler ishga tushdi — har {CHECK_INTERVAL} daqiqada tekshiradi")

    yield

    # Shutdown
    scheduler.shutdown()
    client = telegram_client.get_client()
    if client.is_connected():
        await client.disconnect()


app = FastAPI(title="ELD Monitor", lifespan=lifespan)


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "status": "running",
        "time": datetime.now(timezone.utc).isoformat(),
        "check_interval_minutes": CHECK_INTERVAL,
    }


@app.get("/health")
async def health():
    return {"ok": True}


# ─────────────────────────────────────────────────────────────────────────────
# Telegram setup (bir martayna)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/setup-telegram")
async def setup_telegram():
    """
    Telegram session string olish uchun.
    Faqat birinchi marta ishlatiladi.
    Qaytgan string ni .env faylidagi TELEGRAM_SESSION ga qo'ying.
    """
    try:
        session_str = await telegram_client.get_session_string()
        return {
            "session_string": session_str,
            "instruction": ".env faylida TELEGRAM_SESSION= ga bu qiymatni yozing"
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Driverlar
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/drivers")
async def list_drivers():
    return await db.get_all_drivers()


class DriverUpdate(BaseModel):
    tg_group_id:   str | None = None
    asana_task_id: str | None = None


@app.patch("/drivers/{driver_id}")
async def update_driver(driver_id: str, body: DriverUpdate):
    """Driver Telegram group yoki Asana task ID ni qo'shish"""
    driver = await db.get_driver(driver_id)
    if not driver:
        raise HTTPException(404, "Driver topilmadi")

    if body.tg_group_id is not None:
        await db.set_tg_group(driver_id, body.tg_group_id)
    if body.asana_task_id is not None:
        await db.set_asana_task(driver_id, body.asana_task_id)

    return await db.get_driver(driver_id)


@app.post("/drivers/sync")
async def sync_drivers():
    """Factor va Leader'dan driverlarni DB ga sinxronlashtirish"""
    drivers = await monitor.sync_drivers_from_eld()
    return {"synced": len(drivers), "drivers": drivers}


# ─────────────────────────────────────────────────────────────────────────────
# Manual monitoring trigger
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/check-now")
async def check_now():
    """Monitoring siklini qo'lda ishga tushirish"""
    asyncio.create_task(monitor.run_monitoring_cycle())
    return {"message": "Monitoring boshlandi"}


# ─────────────────────────────────────────────────────────────────────────────
# Alert log
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/alerts")
async def get_alerts(limit: int = 50):
    return await db.get_recent_alerts(limit)


# ─────────────────────────────────────────────────────────────────────────────
# Asana
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/asana/fields")
async def asana_fields():
    """Asana project custom field GID larini ko'rish"""
    if not ASANA_PROJECT_ID:
        raise HTTPException(400, "ASANA_PROJECT_ID .env da yo'q")
    return await asana_client.get_project_fields()


@app.get("/asana/tasks")
async def asana_tasks():
    """Asana project tasklarini ko'rish"""
    if not ASANA_PROJECT_ID:
        raise HTTPException(400, "ASANA_PROJECT_ID .env da yo'q")
    return await asana_client.get_tasks()


# ─────────────────────────────────────────────────────────────────────────────
# Manual Telegram test
# ─────────────────────────────────────────────────────────────────────────────

class TgTestBody(BaseModel):
    chat_id: str
    message: str = "ELD Monitor test xabari ✅"


@app.post("/test-telegram")
async def test_telegram(body: TgTestBody):
    """Telegram ga test xabar yuborish"""
    try:
        await telegram_client.send_message(body.chat_id, body.message)
        return {"sent": True}
    except Exception as e:
        raise HTTPException(500, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard (oddiy HTML)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    drivers = await db.get_all_drivers()
    alerts  = await db.get_recent_alerts(20)

    rows = ""
    for d in drivers:
        tg  = d["tg_group_id"] or "—"
        asn = d["asana_task_id"] or "—"
        rows += f"""
        <tr>
          <td>{d['name']}</td>
          <td><span class="badge {'factor' if d['platform']=='factor' else 'leader'}">{d['platform']}</span></td>
          <td>{d['company'] or '—'}</td>
          <td>{tg}</td>
          <td>{asn}</td>
        </tr>"""

    alert_rows = ""
    for a in alerts:
        alert_rows += f"""
        <tr>
          <td>{a['sent_at'][:16]}</td>
          <td>{a.get('driver_name','—')}</td>
          <td><span class="badge {a['alert_type'].split('_')[0]}">{a['alert_type']}</span></td>
          <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{a['message']}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>ELD Monitor</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:system-ui;background:#f5f5f5;color:#222;padding:24px}}
  h1{{font-size:20px;font-weight:600;margin-bottom:24px}}
  h2{{font-size:15px;font-weight:600;margin:24px 0 12px}}
  table{{width:100%;background:#fff;border-radius:8px;border-collapse:collapse;font-size:13px}}
  th,td{{padding:10px 14px;border-bottom:1px solid #eee;text-align:left}}
  th{{background:#fafafa;font-weight:500;color:#666}}
  .badge{{padding:2px 8px;border-radius:20px;font-size:11px;font-weight:500}}
  .factor{{background:#dbeafe;color:#1e40af}}
  .leader{{background:#dcfce7;color:#166534}}
  .hos{{background:#fef3c7;color:#92400e}}
  .disconnect{{background:#fee2e2;color:#991b1b}}
  .reconnect{{background:#d1fae5;color:#065f46}}
  .btn{{display:inline-block;padding:8px 16px;background:#222;color:#fff;border-radius:6px;font-size:13px;cursor:pointer;border:none;text-decoration:none}}
</style></head>
<body>
<h1>◈ ELD Monitor Dashboard</h1>
<a class="btn" href="#" onclick="fetch('/check-now',{{method:'POST'}}).then(()=>location.reload())">▶ Check Now</a>
&nbsp;
<a class="btn" href="/alerts">📋 Full Alerts</a>
&nbsp;
<a class="btn" href="/drivers">👥 Drivers JSON</a>

<h2>Driverlar ({len(drivers)})</h2>
<table>
  <tr><th>Ism</th><th>Platform</th><th>Company</th><th>TG Group</th><th>Asana Task</th></tr>
  {rows or '<tr><td colspan=5 style="text-align:center;color:#999">Hech qanday driver yo\'q — /drivers/sync ni bosing</td></tr>'}
</table>

<h2>Oxirgi alertlar (20)</h2>
<table>
  <tr><th>Vaqt</th><th>Driver</th><th>Tur</th><th>Xabar</th></tr>
  {alert_rows or '<tr><td colspan=4 style="text-align:center;color:#999">Hali hech qanday alert yo\'q</td></tr>'}
</table>
</body></html>"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)
