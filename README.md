# AlphaMaster — Telegram Booking Bot

[![tests](https://github.com/Psheno-7/alphamaster-bot/actions/workflows/tests.yml/badge.svg)](https://github.com/Psheno-7/alphamaster-bot/actions)

A Telegram bot that lets clients book appointments with a master — hair stylist,
nail artist, tutor, massage therapist — and lets the owner run the whole schedule
from inside Telegram, with no code and no web admin.

**Live demo:** [@alphamasterbot](https://t.me/alphamasterbot) — the owner panel is open to everyone in demo mode.

## Features

**For clients**
- Book in a few taps: **service → day → time**, no typing
- Only free slots are shown; days off and past hours are hidden; double booking is impossible
- View and cancel own bookings
- Automatic reminders **24 hours** and **2 hours** before the appointment
- Three languages: 🇷🇺 Russian, 🇮🇹 Italian, 🇬🇧 English (auto-detected, switchable)

**For the owner** (`/admin`)
- Bookings by day; cancel a booking and the client is notified automatically
- Add and remove services with prices
- Set working hours, days off and how far ahead clients can book
- Rename the business
- Statistics: bookings and revenue for 7 / 30 days, most popular service
- Instant notification on every new booking and cancellation

## Tech

- Python 3.12, [python-telegram-bot](https://python-telegram-bot.org) 21 (async, JobQueue)
- SQLite — no external database needed
- Stateless booking flow: the whole state lives in button data, so it survives restarts
- Timezone-aware scheduling (`TIMEZONE`, default `Europe/Rome`)
- Unit tests with pytest, run on every push by GitHub Actions
- Docker image for deployment

```
alphamaster/
  main.py       app setup, handlers, reminder job
  client.py     client booking flow
  admin.py      owner panel
  schedule.py   free days / time slots logic
  reminders.py  reminder job
  db.py         SQLite storage
  texts.py      translations (ru / it / en)
  common.py     shared helpers
tests/          unit tests
```

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env            # fill in BOT_TOKEN and ADMIN_ID
python -m alphamaster
```

Run tests: `pip install pytest && pytest`

## Run with Docker

```bash
docker build -t alphamaster .
docker run -d --env-file .env -v alphamaster-data:/data alphamaster
```
