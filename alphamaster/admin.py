"""Owner panel: bookings by day, services, schedule, business name, statistics."""
from datetime import timedelta

from . import client, db
from .common import booking_kw, chunk, dispatcher, is_admin, kb, send, show, user_lang
from .schedule import now, now_str, parse_slots
from .texts import WEEKDAYS, fmt_day, t


def back(lang, to="a_menu"):
    return [(t(lang, "btn_back"), to)]


async def ask(update, context, lang, state, key, cancel_to):
    """Wait for the owner to type a value; on_text() handles the answer."""
    context.user_data["await"] = state
    await show(update, t(lang, key), kb([(t(lang, "btn_cancel"), cancel_to)]))


async def open_panel(update, context):
    user = update.effective_user
    if is_admin(user.id):
        context.user_data.pop("await", None)
        await panel(update, context, user_lang(user), "")


async def panel(update, context, lang, arg, note=""):
    text = t(lang, "a_title", name=db.get_setting("business_name"))
    rows = [
        [(t(lang, "a_bookings"), "a_list"), (t(lang, "a_services"), "a_svc")],
        [(t(lang, "a_schedule"), "a_sched"), (t(lang, "a_stats_btn"), "a_stats")],
        [(t(lang, "a_rename"), "a_name")],
        back(lang, "menu"),
    ]
    await show(update, f"{note}\n\n{text}" if note else text, kb(*rows))


# --- Bookings ---

async def booking_days(update, context, lang, arg):
    today = now().date()
    days = [(today + timedelta(days=i)).isoformat() for i in range(int(db.get_setting("days_ahead")))]
    counts = db.booking_counts(days[0], days[-1])
    rows = chunk([(f"{fmt_day(d, lang)} ({counts.get(d, 0)})", f"a_day:{d}") for d in days], 2)
    await show(update, t(lang, "a_choose_day"), kb(*rows, back(lang)))


async def day_bookings(update, context, lang, arg, note=""):
    day = arg
    bookings = db.bookings_on(day)
    if bookings:
        lines = "\n".join(t(lang, "a_line", **booking_kw(b, lang)) for b in bookings)
        text = t(lang, "a_day_title", day=fmt_day(day, lang)) + "\n\n" + lines
    else:
        text = t(lang, "a_day_empty", day=fmt_day(day, lang))
    current = now_str()
    rows = [[(f"❌ {b['time']} {b['user_name']}", f"a_delq:{b['id']}")]
            for b in bookings if f"{b['day']} {b['time']}" > current]
    await show(update, f"{note}\n\n{text}" if note else text, kb(*rows, back(lang, "a_list")))


async def cancel_question(update, context, lang, arg):
    booking = db.get_booking(int(arg))
    if not booking:
        await booking_days(update, context, lang, "")
        return
    kw = booking_kw(booking, lang)
    text = t(lang, "a_cancel_q", day=kw["day"], line=t(lang, "a_line", **kw))
    await show(update, text, kb([(t(lang, "btn_yes_cancel"), f"a_del:{booking['id']}")],
                                back(lang, f"a_day:{booking['day']}")))


async def cancel_booking(update, context, lang, arg):
    booking = db.get_booking(int(arg))
    if not booking or not db.delete_booking(booking["id"]):
        await booking_days(update, context, lang, "")
        return
    client_lang = db.get_lang(booking["user_id"]) or "en"
    await send(context, booking["user_id"],
               t(client_lang, "cancelled_by_owner", **booking_kw(booking, client_lang)))
    await day_bookings(update, context, lang, booking["day"], note=t(lang, "a_cancel_done"))


# --- Services ---

async def services(update, context, lang, arg, note=""):
    items = db.list_services()
    lines = "\n".join(f"• {s['name']} — €{s['price']}" for s in items) or t(lang, "a_services_empty")
    text = f"{t(lang, 'a_services_title')}\n\n{lines}"
    rows = [[(f"❌ {s['name']}", f"a_svc_del:{s['id']}")] for s in items]
    rows += [[(t(lang, "a_add_service"), "a_svc_add")], back(lang)]
    await show(update, f"{note}\n\n{text}" if note else text, kb(*rows))


async def delete_service(update, context, lang, arg):
    db.delete_service(int(arg))
    await services(update, context, lang, "", note=t(lang, "a_saved"))


async def add_service(update, context, lang, arg):
    await ask(update, context, lang, "service_name", "a_ask_service", "a_svc")


# --- Schedule ---

async def schedule(update, context, lang, arg, note=""):
    names = WEEKDAYS[lang]
    ahead = db.get_setting("days_ahead")
    text = t(lang, "a_schedule_text",
             slots=", ".join(db.get_slots()) or t(lang, "none"),
             days_off=", ".join(names[d] for d in sorted(db.get_days_off())) or t(lang, "none"),
             ahead=ahead)
    ahead_row = [(("✓ " if str(n) == ahead else "") + t(lang, "a_ahead", n=n), f"a_ahead:{n}") for n in (7, 14, 30)]
    rows = [[(t(lang, "a_edit_slots"), "a_slots")], [(t(lang, "a_edit_days_off"), "a_offs")], ahead_row, back(lang)]
    await show(update, f"{note}\n\n{text}" if note else text, kb(*rows))


async def set_ahead(update, context, lang, arg):
    if arg in ("7", "14", "30"):
        db.set_setting("days_ahead", arg)
    await schedule(update, context, lang, "", note=t(lang, "a_saved"))


async def edit_slots(update, context, lang, arg):
    await ask(update, context, lang, "slots", "a_ask_slots", "a_sched")


async def days_off(update, context, lang, arg):
    off = db.get_days_off()
    if arg:
        day = int(arg)
        off ^= {day}
        if len(off) < 7:  # keep at least one working day
            db.set_days_off(off)
        off = db.get_days_off()
    buttons = [(("🚫 " if i in off else "✅ ") + name, f"a_offs:{i}") for i, name in enumerate(WEEKDAYS[lang])]
    await show(update, t(lang, "a_days_off_text"), kb(*chunk(buttons, 4), back(lang, "a_sched")))


# --- Name and statistics ---

async def rename(update, context, lang, arg):
    await ask(update, context, lang, "name", "a_ask_name", "a_menu")


async def stats(update, context, lang, arg):
    s = db.stats(now().date(), now_str())
    s["top"] = s["top"] or t(lang, "none")
    await show(update, t(lang, "a_stats", **s), kb(back(lang)))


# --- Typed answers ---

async def on_text(update, context):
    user = update.effective_user
    state = context.user_data.get("await")
    if not state or not is_admin(user.id):
        await client.show_menu(update, context)
        return
    lang = user_lang(user)
    text = update.message.text.strip()

    if state == "service_name":
        if not 1 <= len(text) <= 50:
            await update.message.reply_text(t(lang, "a_bad_service"))
            return
        context.user_data.update({"await": "service_price", "service_name": text})
        await update.message.reply_text(t(lang, "a_ask_price", service=text),
                                        reply_markup=kb([(t(lang, "btn_cancel"), "a_svc")]))

    elif state == "service_price":
        if not text.isdigit() or int(text) > 100000:
            await update.message.reply_text(t(lang, "a_bad_price"))
            return
        name = context.user_data.pop("service_name")
        context.user_data.pop("await")
        db.add_service(name, int(text))
        await services(update, context, lang, "", note=t(lang, "a_service_added", service=name))

    elif state == "slots":
        slots = parse_slots(text)
        if not slots:
            await update.message.reply_text(t(lang, "a_bad_slots"))
            return
        context.user_data.pop("await")
        db.set_setting("slots", ",".join(slots))
        await schedule(update, context, lang, "", note=t(lang, "a_saved"))

    elif state == "name":
        if not 1 <= len(text) <= 60:
            await update.message.reply_text(t(lang, "a_bad_name"))
            return
        context.user_data.pop("await")
        db.set_setting("business_name", text)
        await panel(update, context, lang, "", note=t(lang, "a_saved"))


on_callback = dispatcher({
    "a_menu": panel,
    "a_list": booking_days,
    "a_day": day_bookings,
    "a_delq": cancel_question,
    "a_del": cancel_booking,
    "a_svc": services,
    "a_svc_del": delete_service,
    "a_svc_add": add_service,
    "a_sched": schedule,
    "a_ahead": set_ahead,
    "a_slots": edit_slots,
    "a_offs": days_off,
    "a_name": rename,
    "a_stats": stats,
}, guard=is_admin)
