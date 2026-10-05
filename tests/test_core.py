import sqlite3
from datetime import date, datetime, timedelta

import pytest

from alphamaster import config, db, schedule


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


def workday(offset=2):
    d = schedule.now().date() + timedelta(days=offset)
    while d.weekday() in db.get_days_off():
        d += timedelta(days=1)
    return d.isoformat()


def book(day, time="10:00", now=None):
    db.create_booking(user_id=1, user_name="Test", service="Cut", price=25, day=day, time=time,
                      now=now or schedule.now())


def test_defaults_are_seeded_once():
    assert len(db.list_services()) == 3
    for s in db.list_services():
        db.delete_service(s["id"])
    db.init_db()
    assert db.list_services() == []


def test_booked_time_disappears():
    day = workday()
    assert "10:00" in schedule.free_times(day)
    book(day)
    assert "10:00" not in schedule.free_times(day)


def test_double_booking_is_blocked():
    day = workday()
    book(day)
    with pytest.raises(sqlite3.IntegrityError):
        book(day)


def test_day_off_has_no_slots():
    day = workday()
    db.set_days_off({date.fromisoformat(day).weekday()})
    assert schedule.free_times(day) == []
    assert day not in schedule.available_days()


def test_past_days_have_no_slots():
    yesterday = (schedule.now().date() - timedelta(days=1)).isoformat()
    assert schedule.free_times(yesterday) == []


def test_parse_slots():
    assert schedule.parse_slots("9:00 10.30, 9:00") == ["09:00", "10:30"]
    assert schedule.parse_slots("25:00") is None
    assert schedule.parse_slots("hello") is None
    assert schedule.parse_slots("") is None


def test_reminder_flags_for_near_booking():
    day = workday()
    book(day, "10:00", now=datetime.fromisoformat(f"{day} 09:00"))
    b = db.bookings_on(day)[0]
    assert (b["reminded_day"], b["reminded_hour"]) == (1, 1)


def test_reminder_flags_for_far_booking():
    day = workday(5)
    book(day, "10:00", now=datetime.fromisoformat(day) - timedelta(days=3))
    b = db.bookings_on(day)[0]
    assert (b["reminded_day"], b["reminded_hour"]) == (0, 0)
    assert b["id"] in [r["id"] for r in db.pending_reminders(schedule.now_str())]


def test_stats():
    today = schedule.now().date()
    book(today.isoformat(), "23:59")
    s = db.stats(today, schedule.now_str())
    assert (s["week_n"], s["week_sum"], s["top"]) == (1, 25, "Cut")
