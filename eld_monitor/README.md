# ELD Telegram Monitor

Har daqiqada ELD ma'lumotlarini tekshirib, Telegram guruhlariga ogohlantirish xabarlar yuboradi.

## O'rnatish

### 1. Python o'rnatish
Python 3.11+ talab qilinadi.

```bash
pip install -r requirements.txt
```

### 2. Birinchi ishga tushirish (Telegram login)

```bash
python main.py
```

Birinchi marta telefon raqamingizga SMS kod keladi. Terminalda shu kodni kiriting.
Keyin session file saqlanadi va keyingi safar kod so'ralmaydi.

### 3. Config sozlamalari

`config.json` faylini tahrirlang:

```json
{
  "eld_accounts": [
    {
      "id": "factor_main",
      "name": "Factor ELD",
      "type": "factor",
      "token": "YOUR_JWT_TOKEN_HERE",
      "base_url": "https://api.factorhq.com",
      "enabled": true
    }
  ],
  "telegram_accounts": [
    {
      "id": "main_account",
      "name": "Main Account",
      "api_id": YOUR_API_ID,
      "api_hash": "YOUR_API_HASH",
      "phone": "+1XXXXXXXXXX",
      "session_name": "eld_session_main",
      "enabled": true
    }
  ],
  "settings": {
    "poll_interval_seconds": 60,
    "alert_repeat_interval_minutes": 30,
    "hos_shift_warning_hours": 2,
    "hos_drive_warning_hours": 2,
    "hos_break_warning_hours": 2,
    "hos_cycle_warning_hours": 30,
    "on_duty_stuck_hours": 2,
    "profile_stale_days": 3
  }
}
```

## Telegram guruhlari

Driver nomi bilan guruh topiladi. Masalan, driver "John Smith" uchun:
- "John Smith" — to'liq mos
- "John Smith Dispatch" — mos
- "John Smith - Fleet" — mos

Guruh nomida driver ismi va familiyasi bo'lishi kerak.

## Alert turlari

| Alert | Tavsif | Takrorlanish |
|-------|---------|--------------|
| `violation_overtime` | Drive time oshib ketgan | 30 daqiqada bir |
| `violation_no_pti` | PTI qilinmagan | 30 daqiqada bir |
| `hos_shift_low` | Shift vaqti < 2 soat | 30 daqiqada bir |
| `hos_drive_low` | Drive vaqti < 2 soat | 30 daqiqada bir |
| `hos_break_low` | Break vaqti < 2 soat | 30 daqiqada bir |
| `hos_cycle_low` | Cycle vaqti < 30 soat | 30 daqiqada bir |
| `driver_disconnect` | ELD ulanmagan | 30 daqiqada bir |
| `status_stuck_on_duty` | On Duty > 2 soat | 30 daqiqada bir |
| `profile_stale` | Profil 3 kunda yangilanmagan | 30 daqiqada bir |
| `certification_missing` | Logs sertifikatsiyalanmagan | 30 daqiqada bir |

Har bir alert turi uchun **15 xil xabar varianti** mavjud (spam oldini olish uchun).

## Bir nechta Telegram akkaunt

`telegram_accounts` massiviga ko'proq akkaunt qo'shish mumkin:

```json
"telegram_accounts": [
  { "id": "acc1", "phone": "+1XXX", "api_id": ..., "api_hash": "...", "session_name": "session1" },
  { "id": "acc2", "phone": "+1YYY", "api_id": ..., "api_hash": "...", "session_name": "session2" }
]
```

Xabarlar round-robin usulida yuboriladi.

## ELD API muammolari

Agar API endpoint topilmasa, `eld_client.py` faylidagi `endpoints_to_try` ro'yxatini
Factor ELD yoki Leader ELD API dokumentatsiyasiga qarab yangilang.

## Log fayli

Barcha harakatlar `eld_monitor.log` faylida saqlanadi.

## Fon jarayon sifatida ishlatish (Linux server)

```bash
# systemd service yoki screen/tmux bilan:
screen -S eld_monitor
python main.py

# Ctrl+A, D — fon rejimiga
```

Yoki `systemd` service sifatida:

```ini
# /etc/systemd/system/eld-monitor.service
[Unit]
Description=ELD Telegram Monitor
After=network.target

[Service]
User=youruser
WorkingDirectory=/path/to/eld_monitor
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```
