import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID") or 0)
DB_PATH = os.getenv("DB_PATH", "alphamaster.db")
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Europe/Rome"))
# In demo mode every user can open the owner panel (useful for a public portfolio demo).
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in ("1", "true", "yes")
