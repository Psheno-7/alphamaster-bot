import logging

from telegram import BotCommand
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from . import admin, client, config, db
from .reminders import send_reminders
from .texts import LANGUAGES, t

log = logging.getLogger(__name__)


async def post_init(app):
    for lang in LANGUAGES:
        commands = [BotCommand("start", t(lang, "cmd_start")), BotCommand("admin", t(lang, "cmd_admin"))]
        await app.bot.set_my_commands(commands, language_code=None if lang == "en" else lang)


async def on_error(update, context):
    log.error("Error while handling an update", exc_info=context.error)


def main():
    logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is missing: copy .env.example to .env and fill it in.")

    db.init_db()
    app = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", client.start))
    app.add_handler(CommandHandler("admin", admin.open_panel))
    app.add_handler(CallbackQueryHandler(admin.on_callback, pattern=r"^a_"))
    app.add_handler(CallbackQueryHandler(client.on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin.on_text))
    app.add_error_handler(on_error)
    app.job_queue.run_repeating(send_reminders, interval=300, first=10)

    log.info("AlphaMaster started (demo mode: %s)", config.DEMO_MODE)
    app.run_polling()
