"""Working schedule: which days and times are free for booking."""
import re
from datetime import datetime, timedelta

from . import config, db

SLOT_RE = re.compile(r"^(\d{1,2})[:.](\d{2})$")


def now():
    """Current local time of the business (naive datetime)."""
    return datetime.now(config.TIMEZONE).replace(tzinfo=None)


def now_str():
    return now().strftime("%Y-%m-%d %H:%M")


def free_times(day):
    if datetime.fromisoformat(day).weekday() in db.get_days_off():
        return []
    taken = db.taken_times(day)
    current = now_str()
    return [t for t in db.get_slots() if t not in taken and f"{day} {t}" > current]


def available_days():
    today = now().date()
    ahead = int(db.get_setting("days_ahead"))
    days = [(today + timedelta(days=i)).isoformat() for i in range(ahead)]
    return [d for d in days if free_times(d)]


def parse_slots(text):
    """'9:00 10.30, 15:00' -> ['09:00', '10:30', '15:00']; None if the format is wrong."""
    slots = set()
    for part in text.replace(",", " ").split():
        match = SLOT_RE.match(part)
        if not match:
            return None
        hour, minute = int(match[1]), int(match[2])
        if hour > 23 or minute > 59:
            return None
        slots.add(f"{hour:02d}:{minute:02d}")
    return sorted(slots) or None
