"""SQLite storage: users, services, settings and bookings."""
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT,
    lang TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    user_name TEXT NOT NULL,
    service TEXT NOT NULL,
    price INTEGER NOT NULL,
    day TEXT NOT NULL,
    time TEXT NOT NULL,
    created_at TEXT NOT NULL,
    reminded_day INTEGER NOT NULL DEFAULT 0,
    reminded_hour INTEGER NOT NULL DEFAULT 0,
    UNIQUE(day, time)
);
"""

DEFAULT_SETTINGS = {
    "business_name": "AlphaMaster",
    "slots": "10:00,11:00,12:00,14:00,15:00,16:00,17:00",
    "days_off": "6",
    "days_ahead": "14",
}
DEFAULT_SERVICES = [
    ("Диагностика ПК / Diagnosi PC", 20),
    ("Настройка Wi-Fi и роутера / Wi-Fi e router", 30),
    ("Установка Windows / Installazione Windows", 40),
]


def connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def fetch(sql, params=()):
    with closing(connect()) as conn:
        return conn.execute(sql, params).fetchall()


def fetch_one(sql, params=()):
    rows = fetch(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    """Run a write query in a transaction and return the number of affected rows."""
    with closing(connect()) as conn, conn:
        return conn.execute(sql, params).rowcount


def init_db():
    with closing(connect()) as conn, conn:
        conn.executescript(SCHEMA)
        first_run = conn.execute("SELECT 1 FROM settings LIMIT 1").fetchone() is None
        if first_run:
            conn.executemany("INSERT INTO settings VALUES (?, ?)", DEFAULT_SETTINGS.items())
            conn.executemany("INSERT INTO services (name, price) VALUES (?, ?)", DEFAULT_SERVICES)


# --- Settings ---

def get_setting(key):
    return fetch_one("SELECT value FROM settings WHERE key = ?", (key,))["value"]


def set_setting(key, value):
    execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (key, str(value)))


def get_slots():
    value = get_setting("slots")
    return value.split(",") if value else []


def get_days_off():
    return {int(d) for d in get_setting("days_off").split(",") if d}


def set_days_off(days):
    set_setting("days_off", ",".join(str(d) for d in sorted(days)))


# --- Users ---

def get_lang(user_id):
    row = fetch_one("SELECT lang FROM users WHERE id = ?", (user_id,))
    return row["lang"] if row else None


def save_user(user_id, name, lang):
    execute(
        "INSERT INTO users (id, name, lang) VALUES (?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET name = excluded.name, lang = excluded.lang",
        (user_id, name, lang),
    )


# --- Services ---

def list_services():
    return fetch("SELECT * FROM services ORDER BY id")


def get_service(service_id):
    return fetch_one("SELECT * FROM services WHERE id = ?", (service_id,))


def add_service(name, price):
    execute("INSERT INTO services (name, price) VALUES (?, ?)", (name, price))


def delete_service(service_id):
    execute("DELETE FROM services WHERE id = ?", (service_id,))


# --- Bookings ---

def create_booking(user_id, user_name, service, price, day, time, now):
    """Raises sqlite3.IntegrityError if the slot is already taken."""
    left = datetime.fromisoformat(f"{day} {time}") - now
    execute(
        "INSERT INTO bookings (user_id, user_name, service, price, day, time, created_at, "
        "reminded_day, reminded_hour) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, user_name, service, price, day, time, now.strftime("%Y-%m-%d %H:%M"),
         # Don't send a "tomorrow" reminder for a booking made a few hours ahead.
         int(left <= timedelta(hours=24)), int(left <= timedelta(hours=2))),
    )


def taken_times(day):
    return {r["time"] for r in fetch("SELECT time FROM bookings WHERE day = ?", (day,))}


def get_booking(booking_id):
    return fetch_one("SELECT * FROM bookings WHERE id = ?", (booking_id,))


def delete_booking(booking_id):
    return execute("DELETE FROM bookings WHERE id = ?", (booking_id,))


def upcoming_for_user(user_id, now_s):
    return fetch(
        "SELECT * FROM bookings WHERE user_id = ? AND day || ' ' || time >= ? ORDER BY day, time",
        (user_id, now_s),
    )


def bookings_on(day):
    return fetch("SELECT * FROM bookings WHERE day = ? ORDER BY time", (day,))


def booking_counts(first_day, last_day):
    rows = fetch(
        "SELECT day, COUNT(*) AS n FROM bookings WHERE day BETWEEN ? AND ? GROUP BY day",
        (first_day, last_day),
    )
    return {r["day"]: r["n"] for r in rows}


def pending_reminders(now_s):
    return fetch("SELECT * FROM bookings WHERE reminded_hour = 0 AND day || ' ' || time > ?", (now_s,))


def mark_reminded(booking_id, hour):
    if hour:
        execute("UPDATE bookings SET reminded_day = 1, reminded_hour = 1 WHERE id = ?", (booking_id,))
    else:
        execute("UPDATE bookings SET reminded_day = 1 WHERE id = ?", (booking_id,))


def stats(today, now_s):
    def period(days):
        first = (today - timedelta(days=days - 1)).isoformat()
        row = fetch_one(
            "SELECT COUNT(*) AS n, COALESCE(SUM(price), 0) AS total FROM bookings WHERE day BETWEEN ? AND ?",
            (first, today.isoformat()),
        )
        return row["n"], row["total"]

    week_n, week_sum = period(7)
    month_n, month_sum = period(30)
    upcoming = fetch_one("SELECT COUNT(*) AS n FROM bookings WHERE day || ' ' || time >= ?", (now_s,))["n"]
    top = fetch_one("SELECT service, COUNT(*) AS n FROM bookings GROUP BY service ORDER BY n DESC LIMIT 1")
    return {
        "week_n": week_n, "week_sum": week_sum,
        "month_n": month_n, "month_sum": month_sum,
        "upcoming": upcoming, "top": top["service"] if top else None,
    }
