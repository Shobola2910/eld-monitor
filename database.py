import aiosqlite
from config import DB_PATH

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS drivers (
    id          TEXT PRIMARY KEY,
    name        TEXT,
    platform    TEXT,          -- 'factor' | 'leader'
    company     TEXT,
    tg_group_id TEXT,          -- Telegram group/chat ID for this driver
    asana_task_id TEXT,
    is_active   INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS alert_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id   TEXT,
    alert_type  TEXT,          -- 'hos_drive'|'hos_shift'|'hos_break'|'hos_cycle'|'disconnect'
    message     TEXT,
    sent_at     TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (driver_id) REFERENCES drivers(id)
);

CREATE TABLE IF NOT EXISTS cooldowns (
    driver_id   TEXT PRIMARY KEY,
    last_sent   TEXT           -- ISO datetime of last Telegram message
);
"""

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        for stmt in CREATE_SQL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                await db.execute(stmt)
        await db.commit()

async def get_all_drivers():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM drivers WHERE is_active=1") as cur:
            return [dict(r) for r in await cur.fetchall()]

async def get_driver(driver_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM drivers WHERE id=?", (driver_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def upsert_driver(d: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO drivers (id, name, platform, company, tg_group_id, asana_task_id)
            VALUES (:id, :name, :platform, :company, :tg_group_id, :asana_task_id)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                platform=excluded.platform,
                company=excluded.company
        """, d)
        await db.commit()

async def set_tg_group(driver_id: str, group_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE drivers SET tg_group_id=? WHERE id=?", (group_id, driver_id))
        await db.commit()

async def set_asana_task(driver_id: str, task_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE drivers SET asana_task_id=? WHERE id=?", (task_id, driver_id))
        await db.commit()

async def can_send_alert(driver_id: str, cooldown_minutes: int = 5) -> bool:
    """5 daqiqa cooldown — spamdan himoya"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT last_sent FROM cooldowns WHERE driver_id=?
        """, (driver_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return True
        from datetime import datetime, timezone
        last = datetime.fromisoformat(row[0]).replace(tzinfo=timezone.utc)
        now  = datetime.now(timezone.utc)
        return (now - last).total_seconds() >= cooldown_minutes * 60

async def mark_sent(driver_id: str):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO cooldowns (driver_id, last_sent) VALUES (?,?)
            ON CONFLICT(driver_id) DO UPDATE SET last_sent=excluded.last_sent
        """, (driver_id, now))
        await db.commit()

async def log_alert(driver_id: str, alert_type: str, message: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO alert_log (driver_id, alert_type, message) VALUES (?,?,?)",
            (driver_id, alert_type, message)
        )
        await db.commit()

async def get_recent_alerts(limit: int = 50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT a.*, d.name as driver_name, d.platform
            FROM alert_log a LEFT JOIN drivers d ON a.driver_id=d.id
            ORDER BY a.sent_at DESC LIMIT ?
        """, (limit,)) as cur:
            return [dict(r) for r in await cur.fetchall()]
