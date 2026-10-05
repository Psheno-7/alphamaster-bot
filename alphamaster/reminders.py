"""Periodic job: remind clients 24 hours and 2 hours before the appointment."""
from datetime import datetime, timedelta

from . import db
from .common import booking_kw, send
from .schedule import now
from .texts import t


async def send_reminders(context):
    current = now()
    for booking in db.pending_reminders(current.strftime("%Y-%m-%d %H:%M")):
        left = datetime.fromisoformat(f"{booking['day']} {booking['time']}") - current
        if left <= timedelta(hours=2):
            hour = True
        elif left <= timedelta(hours=24) and not booking["reminded_day"]:
            hour = False
        else:
            continue
        lang = db.get_lang(booking["user_id"]) or "en"
        await send(context, booking["user_id"], t(lang, "reminder", **booking_kw(booking, lang)))
        db.mark_reminded(booking["id"], hour)
