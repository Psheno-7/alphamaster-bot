"""Helpers shared by client and owner handlers."""
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, Forbidden

from . import config, db
from .texts import LANGUAGES, fmt_day, t

log = logging.getLogger(__name__)


def kb(*rows):
    """kb([("Text", "callback"), ...], ...) -> inline keyboard."""
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=data) for text, data in row]
                                 for row in rows])


def chunk(items, size):
    return [items[i:i + size] for i in range(0, len(items), size)]


def is_admin(user_id):
    return config.DEMO_MODE or user_id == config.ADMIN_ID


def display_name(user):
    return user.full_name + (f" (@{user.username})" if user.username else "")


def user_lang(user):
    lang = db.get_lang(user.id)
    if not lang:
        code = (user.language_code or "")[:2]
        lang = code if code in LANGUAGES else "en"
        db.save_user(user.id, user.full_name, lang)
    return lang


def booking_kw(booking, lang):
    return {
        "service": booking["service"], "price": booking["price"],
        "day": fmt_day(booking["day"], lang), "time": booking["time"], "client": booking["user_name"],
    }


async def show(update, text, markup=None):
    """Edit the message with the pressed button, or reply to a text message."""
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=markup)
        except BadRequest as e:
            if "not modified" not in str(e):
                raise
    else:
        await update.effective_message.reply_text(text, reply_markup=markup)


async def send(context, chat_id, text):
    try:
        await context.bot.send_message(chat_id, text)
    except (Forbidden, BadRequest) as e:
        log.warning("Could not send message to %s: %s", chat_id, e)


async def notify_owner(context, actor_id, key, booking):
    if config.ADMIN_ID:
        lang = db.get_lang(config.ADMIN_ID) or "ru"
        await send(context, config.ADMIN_ID, t(lang, key, **booking_kw(booking, lang)))
    if config.DEMO_MODE and actor_id != config.ADMIN_ID:
        lang = db.get_lang(actor_id) or "en"
        await send(context, actor_id, t(lang, "demo_note") + "\n\n" + t(lang, key, **booking_kw(booking, lang)))


def dispatcher(actions, guard=None):
    """Build a callback handler that routes 'action:arg' button data to actions[action](update, context, lang, arg)."""
    async def on_callback(update, context):
        await update.callback_query.answer()
        user = update.effective_user
        if guard and not guard(user.id):
            return
        context.user_data.pop("await", None)
        action, _, arg = update.callback_query.data.partition(":")
        handler = actions.get(action)
        if handler:
            await handler(update, context, user_lang(user), arg)
    return on_callback
