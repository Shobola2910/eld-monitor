"""
ELD Monitor — FastAPI + token login
"""
import asyncio
import hashlib
import logging
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Cookie, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

import database as db
import monitor
import asana_client
import telegram_client
from config import CHECK_INTERVAL, ASANA_PROJECT_ID, ASANA_TOKEN

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
log = logging.getLogger("main")
scheduler = AsyncIOScheduler()

def get_valid_tokens() -> set:
    tokens = set()
    if ASANA_TOKEN:
        tokens.add(ASANA_TOKEN.strip())
    for t in os.getenv("ADMIN_TOKENS", "").split(","):
        t = t.strip()
        if t:
            tokens.add(t)
    return tokens

_sessions: dict = {}

def create_session(api_token: str) -> str:
    sess = hashlib.sha256(api_token.encode()).hexdigest() + secrets.token_hex(8)
    _sessions[sess] = api_token
    return sess

def get_session_user(session):
    if not session:
        return None
    return _sessions.get(session)

def require_auth(session):
    if not get_session_user(session):
        raise HTTPException(status_code=401, detail="Login kerak")
    return True

@asynccontextmanager
async def lifespan(app):
    await db.init_db()
    log.info("DB ishga tushdi")
    try:
        await telegram_client.start_client()
        log.info("Telegram ulandi")
    except Exception as e:
        log.warning(f"Telegram ulanmadi: {e}")
    scheduler.add_job(monitor.run_monitoring_cycle, "interval", minutes=CHECK_INTERVAL,
                      id="eld_monitor", next_run_time=datetime.now(timezone.utc))
    scheduler.start()
    log.info(f"Scheduler ishga tushdi — har {CHECK_INTERVAL} daqiqada")
    yield
    scheduler.shutdown()
    client = telegram_client.get_client()
    if client.is_connected():
        await client.disconnect()

app = FastAPI(title="ELD Monitor", lifespan=lifespan)

@app.get("/", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
async def login_page(eld_session: str = Cookie(default=None)):
    if get_session_user(eld_session):
        return RedirectResponse("/dashboard")
    return HTMLResponse(LOGIN_HTML)

class LoginBody(BaseModel):
    token: str

@app.post("/auth")
async def auth(body: LoginBody):
    token = body.token.strip()
    if token not in get_valid_tokens():
        raise HTTPException(401, "Token noto'g'ri")
    sess = create_session(token)
    r = JSONResponse({"ok": True})
    r.set_cookie("eld_session", sess, httponly=True, samesite="lax", max_age=86400 * 7)
    return r

@app.get("/logout")
async def logout():
    r = RedirectResponse("/login")
    r.delete_cookie("eld_session")
    return r

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/setup-telegram")
async def setup_telegram(eld_session: str = Cookie(default=None)):
    require_auth(eld_session)
    try:
        session_str = await telegram_client.get_session_string()
        return {"session_string": session_str}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/drivers")
async def list_drivers(eld_session: str = Cookie(default=None)):
    require_auth(eld_session)
    return await db.get_all_drivers()

class DriverUpdate(BaseModel):
    tg_group_id: str = None
    asana_task_id: str = None

@app.patch("/drivers/{driver_id}")
async def update_driver(driver_id: str, body: DriverUpdate, eld_session: str = Cookie(default=None)):
    require_auth(eld_session)
    driver = await db.get_driver(driver_id)
    if not driver:
        raise HTTPException(404, "Driver topilmadi")
    if body.tg_group_id is not None:
        await db.set_tg_group(driver_id, body.tg_group_id)
    if body.asana_task_id is not None:
        await db.set_asana_task(driver_id, body.asana_task_id)
    return await db.get_driver(driver_id)

@app.post("/drivers/sync")
async def sync_drivers(eld_session: str = Cookie(default=None)):
    require_auth(eld_session)
    drivers = await monitor.sync_drivers_from_eld()
    return {"synced": len(drivers)}

@app.post("/check-now")
async def check_now(eld_session: str = Cookie(default=None)):
    require_auth(eld_session)
    asyncio.create_task(monitor.run_monitoring_cycle())
    return {"message": "Boshlandi"}

@app.get("/alerts")
async def get_alerts(limit: int = 50, eld_session: str = Cookie(default=None)):
    require_auth(eld_session)
    return await db.get_recent_alerts(limit)

@app.get("/asana/tasks")
async def asana_tasks(eld_session: str = Cookie(default=None)):
    require_auth(eld_session)
    return await asana_client.get_tasks()

class TgTestBody(BaseModel):
    chat_id: str
    message: str = "ELD Monitor test"

@app.post("/test-telegram")
async def test_telegram(body: TgTestBody, eld_session: str = Cookie(default=None)):
    require_auth(eld_session)
    try:
        await telegram_client.send_message(body.chat_id, body.message)
        return {"sent": True}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(eld_session: str = Cookie(default=None)):
    if not get_session_user(eld_session):
        return RedirectResponse("/login")
    drivers = await db.get_all_drivers()
    alerts  = await db.get_recent_alerts(20)
    rows = ""
    for d in drivers:
        rows += f"<tr><td>{d['name']}</td><td><span class='badge {d['platform']}'>{d['platform']}</span></td><td>{d['company'] or '—'}</td><td>{d['tg_group_id'] or '—'}</td><td>{d['asana_task_id'] or '—'}</td></tr>"
    alert_rows = ""
    for a in alerts:
        alert_rows += f"<tr><td>{a['sent_at'][:16]}</td><td>{a.get('driver_name','—')}</td><td><span class='badge {a['alert_type'].split('_')[0]}'>{a['alert_type']}</span></td><td style='max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap'>{a['message']}</td></tr>"
    return HTMLResponse(DASHBOARD_HTML.replace("{{ROWS}}", rows or "<tr><td colspan=5 class='empty'>Driver yo'q — Sync bosing</td></tr>").replace("{{ALERT_ROWS}}", alert_rows or "<tr><td colspan=4 class='empty'>Hali alert yo'q</td></tr>").replace("{{COUNT}}", str(len(drivers))))

LOGIN_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>ELD Monitor</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui;background:#f0f0ee;min-height:100vh;display:flex;align-items:center;justify-content:center}
.card{background:#fff;border:1px solid #e5e5e2;border-radius:14px;padding:2rem;width:100%;max-width:380px}
.logo{width:48px;height:48px;border-radius:12px;background:#f0f0ee;display:flex;align-items:center;justify-content:center;font-size:24px;margin:0 auto 14px}
h1{font-size:18px;font-weight:600;text-align:center;color:#111}
.sub{font-size:13px;color:#888;text-align:center;margin-top:4px;margin-bottom:1.5rem}
.tabs{display:flex;background:#f0f0ee;border-radius:8px;padding:3px;gap:3px;margin-bottom:1.25rem}
.tab{flex:1;text-align:center;padding:7px;font-size:13px;color:#888;border-radius:6px;cursor:pointer;border:none;background:none}
.tab.active{background:#fff;border:1px solid #e5e5e2;color:#111;font-weight:500}
label{font-size:11px;color:#888;font-weight:500;letter-spacing:.05em;text-transform:uppercase;display:block;margin-bottom:5px}
.wrap{position:relative;margin-bottom:1rem}
input{width:100%;padding:10px 40px 10px 12px;border:1px solid #e5e5e2;border-radius:8px;font-family:monospace;font-size:13px;outline:none;color:#111;background:#fafaf8}
input:focus{border-color:#999;background:#fff}
.eye{position:absolute;right:10px;top:50%;transform:translateY(-50%);background:none;border:none;cursor:pointer;color:#aaa;padding:0;font-size:16px}
button.go{width:100%;padding:11px;background:#111;color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:500;cursor:pointer}
button.go:hover{background:#333}
.err{color:#c00;font-size:12px;margin-bottom:10px;padding:8px 10px;background:#fff0f0;border-radius:6px;border:1px solid #fcc;display:none}
.hint{font-size:12px;color:#bbb;text-align:center;margin-top:12px}
</style></head>
<body>
<div class="card">
  <div class="logo">◈</div>
  <h1>ELD Monitor</h1>
  <p class="sub">Token orqali kiring</p>
  <div class="tabs">
    <button class="tab active" onclick="setTab(this,'Asana token')">Asana token</button>
    <button class="tab" onclick="setTab(this,'API key')">API key</button>
  </div>
  <label id="lbl">Asana token</label>
  <div class="wrap">
    <input type="password" id="tok" placeholder="Tokeningizni kiriting..." />
    <button class="eye" onclick="toggle()" title="Ko'rish">👁</button>
  </div>
  <div class="err" id="err">Token noto'g'ri — qayta urinib ko'ring</div>
  <button class="go" onclick="login()">Kirish →</button>
  <p class="hint">Faqat ruxsat etilgan tokenlar</p>
</div>
<script>
function setTab(el,lbl){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('lbl').textContent=lbl;
}
function toggle(){
  const i=document.getElementById('tok');
  i.type=i.type==='password'?'text':'password';
}
document.getElementById('tok').addEventListener('keydown',e=>{if(e.key==='Enter')login()});
async function login(){
  const token=document.getElementById('tok').value.trim();
  const err=document.getElementById('err');
  err.style.display='none';
  if(!token)return;
  try{
    const r=await fetch('/auth',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token})});
    if(r.ok){window.location.href='/dashboard';}
    else{err.style.display='block';}
  }catch{err.style.display='block';}
}
</script>
</body></html>"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>ELD Monitor</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui;background:#f0f0ee;color:#111;padding:24px}
.hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px}
h1{font-size:18px;font-weight:600}
.acts{display:flex;gap:8px;flex-wrap:wrap}
a.btn,button.btn{padding:7px 14px;background:#fff;color:#111;border:1px solid #e5e5e2;border-radius:8px;font-size:13px;cursor:pointer;text-decoration:none}
a.btn:hover,button.btn:hover{background:#f5f5f3}
.danger{color:#c00;border-color:#fcc}
h2{font-size:13px;font-weight:500;color:#888;margin:20px 0 8px;text-transform:uppercase;letter-spacing:.04em}
table{width:100%;background:#fff;border-radius:10px;border-collapse:collapse;font-size:13px;border:1px solid #e5e5e2}
th,td{padding:10px 14px;border-bottom:1px solid #f5f5f3;text-align:left}
th{background:#fafaf8;font-weight:500;color:#aaa;font-size:11px;text-transform:uppercase;letter-spacing:.04em}
tr:last-child td{border-bottom:none}
.badge{padding:2px 8px;border-radius:20px;font-size:11px;font-weight:500}
.factor{background:#dbeafe;color:#1e40af}
.leader{background:#dcfce7;color:#166534}
.hos{background:#fef3c7;color:#92400e}
.disconnect{background:#fee2e2;color:#991b1b}
.empty{text-align:center;color:#ccc;padding:24px}
</style></head>
<body>
<div class="hdr">
  <div>
    <h1>◈ ELD Monitor</h1>
    <div style="font-size:12px;color:#888;margin-top:3px">{{COUNT}} driver · har 5 daqiqada tekshiriladi</div>
  </div>
  <div class="acts">
    <button class="btn" onclick="fetch('/check-now',{method:'POST'}).then(()=>location.reload())">▶ Check now</button>
    <button class="btn" onclick="fetch('/drivers/sync',{method:'POST'}).then(()=>location.reload())">⟳ Sync</button>
    <a class="btn danger" href="/logout">Chiqish</a>
  </div>
</div>
<h2>Driverlar ({{COUNT}})</h2>
<table>
  <tr><th>Ism</th><th>Platform</th><th>Company</th><th>TG Group</th><th>Asana Task</th></tr>
  {{ROWS}}
</table>
<h2>Oxirgi alertlar</h2>
<table>
  <tr><th>Vaqt</th><th>Driver</th><th>Tur</th><th>Xabar</th></tr>
  {{ALERT_ROWS}}
</table>
</body></html>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)
