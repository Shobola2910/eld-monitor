import os
from dotenv import load_dotenv

load_dotenv()

# Asana
ASANA_TOKEN       = os.getenv("ASANA_TOKEN", "")
ASANA_PROJECT_ID  = os.getenv("ASANA_PROJECT_ID", "")

# Telegram
TG_API_ID         = int(os.getenv("TELEGRAM_API_ID", "0"))
TG_API_HASH       = os.getenv("TELEGRAM_API_HASH", "")
TG_PHONE          = os.getenv("TELEGRAM_PHONE", "")
TG_SESSION        = os.getenv("TELEGRAM_SESSION", "")

# Factor ELD
FACTOR_TOKEN      = os.getenv("FACTOR_API_TOKEN", "")
FACTOR_BASE       = "https://app.factorhq.com/api/v1"

# Leader ELD
LEADER_TOKEN      = os.getenv("LEADER_API_TOKEN", "")
LEADER_COMPANY_ID = os.getenv("LEADER_COMPANY_ID", "")
LEADER_BASE       = "https://api.eldleader.com/v1"

# Monitoring thresholds (minutes)
CHECK_INTERVAL    = int(os.getenv("CHECK_INTERVAL_MINUTES", "5"))
DRIVE_THRESHOLD   = int(os.getenv("DRIVE_ALERT_THRESHOLD_MIN", "60"))
SHIFT_THRESHOLD   = int(os.getenv("SHIFT_ALERT_THRESHOLD_MIN", "60"))
BREAK_THRESHOLD   = int(os.getenv("BREAK_ALERT_THRESHOLD_MIN", "30"))
CYCLE_THRESHOLD   = int(os.getenv("CYCLE_ALERT_THRESHOLD_HOURS", "5")) * 60

DB_PATH           = "eld_monitor.db"
