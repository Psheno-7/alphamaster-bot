"""Client side: booking flow, own bookings, language choice.

Button data carries the whole booking state (e.g. "time:3:2026-10-06:10:00"),
so the flow keeps working after a bot restart.
"""
import sqlite3

from . import db
from .common import booking_kw, chunk, dispatcher, display_name, is_admin, kb, notify_owner, show, user_lang
from .schedule import available_days, free_times, now, now_str
from .texts import LANGUAGES, fmt_day, t


async def show_menu(update, context, note=""):
    user = update.effective_user
    lang = user_lang(user)
    rows = [[(t(lang, "btn_book"), "book")], [(t(lang, "btn_my"), "my")], [(t(lang, "btn_lang"), "lang")]]
    if is_admin(user.id):
        rows.append([(t(lang, "btn_admin"), "a_menu")])
    text = t(lang, "welcome", name=db.get_setting("business_name"))
    await show(update, f"{note}\n\n{text}" if note else text, kb(*rows))


async def start(update, context):
    context.user_data.clear()
    await show_menu(update, context)


async def menu(update, context, lang, arg):
    await show_menu(update, context)


async def choose_service(update, context, lang, arg):
    services = db.list_services()
    back = [(t(lang, "btn_back"), "menu")]
    if not services:
        await show(update, t(lang, "no_services"), kb(back))
        return
    rows = [[(f"{s['name']} — €{s['price']}", f"svc:{s['id']}")] for s in services]
    await show(update, t(lang, "choose_service"), kb(*rows, back))


async def choose_day(update, context, lang, arg):
    if not db.get_service(int(arg)):
        await choose_service(update, context, lang, "")
        return
    back = [(t(lang, "btn_back"), "book")]
    days = available_days()
    if not days:
        await show(update, t(lang, "no_days"), kb(back))
        return
    rows = chunk([(fmt_day(d, lang), f"day:{arg}:{d}") for d in days], 3)
    await show(update, t(lang, "choose_day"), kb(*rows, back))


async def choose_time(update, context, lang, arg):
    service_id, day = arg.split(":", 1)
    back = [(t(lang, "btn_back"), f"svc:{service_id}")]
    times = free_times(day)
    if not times:
        await show(update, t(lang, "day_full"), kb(back))
        return
    rows = chunk([(tm, f"time:{service_id}:{day}:{tm}") for tm in times], 4)
    await show(update, t(lang, "choose_time", day=fmt_day(day, lang)), kb(*rows, back))


async def check(update, context, lang, arg):
    service_id, day, time = arg.split(":", 2)
    service = db.get_service(int(service_id))
    if not service:
        await choose_service(update, context, lang, "")
        return
    text = t(lang, "check", service=service["name"], price=service["price"], day=fmt_day(day, lang), time=time)
    await show(update, text, kb([(t(lang, "btn_confirm"), f"confirm:{arg}")],
                                [(t(lang, "btn_back"), f"day:{service_id}:{day}")]))


async def confirm(update, context, lang, arg):
    service_id, day, time = arg.split(":", 2)
    service = db.get_service(int(service_id))
    if not service:
        await choose_service(update, context, lang, "")
        return
    taken = kb([(t(lang, "btn_back"), f"day:{service_id}:{day}")])
    if time not in free_times(day):
        await show(update, t(lang, "slot_taken"), taken)
        return
    user = update.effective_user
    booking = {"user_id": user.id, "user_name": display_name(user), "service": service["name"],
               "price": service["price"], "day": day, "time": time}
    try:
        db.create_booking(**booking, now=now())
    except sqlite3.IntegrityError:
        await show(update, t(lang, "slot_taken"), taken)
        return
    await show_menu(update, context, note=t(lang, "booked", **booking_kw(booking, lang)))
    await notify_owner(context, user.id, "notify_new", booking)


async def my_bookings(update, context, lang, arg):
    back = [(t(lang, "btn_back"), "menu")]
    bookings = db.upcoming_for_user(update.effective_user.id, now_str())
    if not bookings:
        await show(update, t(lang, "no_bookings"), kb(back))
        return
    lines = "\n".join(t(lang, "booking_line", **booking_kw(b, lang)) for b in bookings)
    rows = [[(f"❌ {fmt_day(b['day'], lang)} {b['time']}", f"delq:{b['id']}")] for b in bookings]
    await show(update, f"{t(lang, 'your_bookings')}\n\n{lines}", kb(*rows, back))


def own_booking(update, booking_id):
    booking = db.get_booking(int(booking_id))
    return booking if booking and booking["user_id"] == update.effective_user.id else None


async def cancel_question(update, context, lang, arg):
    booking = own_booking(update, arg)
    if not booking:
        await show_menu(update, context, note=t(lang, "not_found"))
        return
    text = t(lang, "cancel_q") + "\n\n" + t(lang, "booking_line", **booking_kw(booking, lang))
    await show(update, text, kb([(t(lang, "btn_yes_cancel"), f"del:{booking['id']}")],
                                [(t(lang, "btn_back"), "my")]))


async def cancel_booking(update, context, lang, arg):
    booking = own_booking(update, arg)
    if not booking or not db.delete_booking(booking["id"]):
        await show_menu(update, context, note=t(lang, "not_found"))
        return
    await show_menu(update, context, note=t(lang, "cancelled"))
    await notify_owner(context, update.effective_user.id, "notify_cancel", booking)


async def language(update, context, lang, arg):
    user = update.effective_user
    if arg in LANGUAGES:
        db.save_user(user.id, user.full_name, arg)
        await show_menu(update, context)
        return
    rows = [[(label, f"lang:{code}")] for code, label in LANGUAGES.items()]
    await show(update, t(lang, "choose_lang"), kb(*rows, [(t(lang, "btn_back"), "menu")]))


on_callback = dispatcher({
    "menu": menu,
    "book": choose_service,
    "svc": choose_day,
    "day": choose_time,
    "time": check,
    "confirm": confirm,
    "my": my_bookings,
    "delq": cancel_question,
    "del": cancel_booking,
    "lang": language,
})
