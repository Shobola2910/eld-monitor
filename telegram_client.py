"""
Telegram client — Telethon orqali xabar yuborish
"""
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from config import TG_API_ID, TG_API_HASH, TG_PHONE, TG_SESSION

_client: TelegramClient | None = None


def get_client() -> TelegramClient:
    global _client
    if _client is None:
        session = StringSession(TG_SESSION) if TG_SESSION else StringSession()
        _client = TelegramClient(session, TG_API_ID, TG_API_HASH)
    return _client


async def start_client():
    client = get_client()
    if not client.is_connected():
        await client.connect()
    if not await client.is_user_authorized():
        print("⚠️  Telegram autentifikatsiya kerak — /setup-telegram endpointini ishlat")
    return client


async def send_message(chat_id: str | int, text: str):
    """Telegram group/chat ga xabar yuborish"""
    client = get_client()
    if not client.is_connected():
        await client.connect()
    await client.send_message(int(chat_id), text, parse_mode="md")


async def get_session_string() -> str:
    """StringSession olish (bir martayna kerak)"""
    client = TelegramClient(StringSession(), TG_API_ID, TG_API_HASH)
    await client.start(phone=TG_PHONE)
    session_str = client.session.save()
    await client.disconnect()
    return session_str


# ─── HOS xabar shablonlari ────────────────────────────────────────────────

def msg_drive_low(name: str, mins: int) -> str:
    h, m = divmod(mins, 60)
    time_str = f"{h}h {m}min" if h else f"{m}min"
    return f"⚠️ *{name}* — Drive vaqti kam qoldi: *{time_str}*\nIloji boricha to'xtang yoki log yangilang."

def msg_shift_low(name: str, mins: int) -> str:
    h, m = divmod(mins, 60)
    time_str = f"{h}h {m}min" if h else f"{m}min"
    return f"⏰ *{name}* — Shift vaqti yaqinlashdi: *{time_str}* qoldi.\nMajburiy dam olishni boshlang."

def msg_break_needed(name: str, mins: int) -> str:
    return f"☕ *{name}* — 30 daqiqalik break kerak. Qolgan: *{mins} min*"

def msg_cycle_low(name: str, hours: float) -> str:
    return f"📅 *{name}* — Haftalik cycle: *{hours:.1f} soat* qoldi.\nDispatcher bilan bog'laning."

def msg_disconnected(name: str) -> str:
    return f"🔴 *{name}* — ELD disconnect bo'ldi!\nIloji boricha reconnect qiling yoki muammo haqida xabar bering."

def msg_reconnected(name: str) -> str:
    return f"🟢 *{name}* — ELD qayta ulandi ✓"
