# ELD Monitor

Factor ELD + Leader ELD → Telegram alertlar + Asana sync

## Fayllar tuzilmasi

```
eld_monitor/
├── main.py           — FastAPI app + scheduler + dashboard
├── monitor.py        — Monitoring logikasi
├── factor_client.py  — Factor ELD API
├── leader_client.py  — Leader ELD API
├── asana_client.py   — Asana sync
├── telegram_client.py— Telegram (Telethon)
├── database.py       — SQLite (driver, cooldown, alert log)
├── config.py         — .env dan sozlamalar
├── requirements.txt
├── render.yaml       — Render deploy
└── .env              — Credentials (git ga qo'shma!)
```

## 1-qadam: .env to'ldirish

```env
ASANA_TOKEN=2/1213271238071310/...
ASANA_PROJECT_ID=           # app.asana.com URL'dan: .../0/XXXXXXX/...
TELEGRAM_API_ID=35507477
TELEGRAM_API_HASH=201ab47b2a808cc66c3ef61529dba649
TELEGRAM_PHONE=+1XXXXXXXXXX
TELEGRAM_SESSION=           # quyidagi 2-qadamdan keyin
FACTOR_API_TOKEN=           # Factor dashboard → Settings → API
LEADER_API_TOKEN=           # Leader dashboard → API
```

## 2-qadam: Telegram session olish

```bash
pip install -r requirements.txt
python -c "
import asyncio
from telegram_client import get_session_string
print(asyncio.run(get_session_string()))
"
```
Qaytgan stringni `.env` → `TELEGRAM_SESSION=` ga qo'ying.

## 3-qadam: Local ishga tushirish

```bash
pip install -r requirements.txt
python main.py
# http://localhost:8000/dashboard
```

## 4-qadam: Driver → Telegram group ulash

Driverlar avtomatik import qilinadi. Har bir driverga TG group ID qo'shish:

```bash
# Driverlar ro'yxati
GET /drivers

# TG group ID qo'shish
PATCH /drivers/factor_12345
{ "tg_group_id": "-1001234567890" }

# Asana task ID qo'shish
PATCH /drivers/factor_12345
{ "asana_task_id": "1234567890" }
```

### Telegram group ID topish:
@userinfobot ga guruh ichidan `/start` yubor → ID ko'rsatadi

## 5-qadam: Render deploy

1. GitHub'ga push qiling
2. Render → New Web Service → repo tanlang
3. Environment variables → hammani kiriting
4. Deploy

## Endpoints

| Endpoint | Vazifa |
|---|---|
| `GET /dashboard` | HTML dashboard |
| `GET /drivers` | Driverlar ro'yxati |
| `POST /drivers/sync` | ELD'dan driverlarni import |
| `PATCH /drivers/{id}` | TG group / Asana task qo'shish |
| `POST /check-now` | Qo'lda monitoring ishga tushirish |
| `GET /alerts` | Alert tarixi |
| `GET /asana/tasks` | Asana tasklari |
| `POST /test-telegram` | Test xabar yuborish |
| `GET /setup-telegram` | Session string olish |

## Alert shartlari

| Alert | Shart |
|---|---|
| Drive Low | < 60 min qolsa |
| Shift Low | < 60 min qolsa |
| Break Needed | < 30 min qolsa |
| Cycle Low | < 5 soat qolsa |
| Disconnect | ELD uzilib qolsa |

Har bir driver uchun **5 daqiqa cooldown** — spamdan himoya.
