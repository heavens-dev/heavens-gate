import argparse
import asyncio
import os
import random
import signal
import sys

from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.commands import (get_admin_commands, get_default_commands,
                          set_admin_commands, set_user_commands)
from bot.handlers import get_handlers_router
from config.loader import (bot_cfg, bot_dispatcher, bot_instance, cfg,
                           connections_observer, db_instance,
                           interval_observer, prometheus_monitor, wghub)
from core.db.db_works import ClientFactory
from core.logs import bot_logger
from core.monitoring.metrics import SERVER_UP


def graceful_shutdown(sig, frame):
    bot_logger.critical("Recieved SIGINT signal, shutting down...")
    if prometheus_monitor is not None:
        prometheus_monitor.stop_server()
    SERVER_UP.set(0)
    sys.exit(0)

@bot_dispatcher.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if message.chat.id in bot_cfg.admins:
        await set_admin_commands(message.chat.id)
    else:
        await set_user_commands(message.chat.id)

    with db_instance.atomic():
        # just in case.
        client, created = ClientFactory(user_id=message.chat.id).get_or_create_client(
            name=message.chat.username
        )

        if created:
            if cfg.is_canary:
                ...

    keyboard = None
    faq_str = ""
    if bot_cfg.faq_url is not None:
        faq_button = InlineKeyboardButton(text="FAQ", url=bot_cfg.faq_url)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[faq_button]])
        faq_str = "\nПрежде чем приступить к работе с ботом, ознакомься с FAQ, нажав на кнопку ниже." \

    if cfg.is_canary:
        msg = f"""Привет. Это Canary версия Heaven's Gate.
Если тебе нужна стабильная версия, то, пожалуйста, используй <a href="https://t.me/heavens_gate_vpn_bot">основного бота</a>.
Здесь обкатываются новые возможности как бота, так и ядра всего сервиса, которые ещё не были добавлены в основную ветку, однако имей в виду, что здесь <i>всё может сломаться</i>.
Если бот не ответил на команду или выдал ошибку, то, пожалуйста, напиши нам об этом через команду /contact или создай issue на <a href="https://github.com/heavens-dev/heavens-gate/issues">GitHub</a>.

На текущий момент стабильная версия Heaven's Gate и Canary одинаковы, и никакого тестового функционала нет. Однако в любой момент всё может измениться, о чём мы тебя предупредим.
Конфиги из основного бота не будут экспортированы в Canary, как и наоборот.

Чтобы узнать, что было добавлено в Heaven's Gate, используй команду /whats_new.

Мы не несём ответственности за стабильность сервиса Canary, и если от нашего VPN будет зависить, уволят ли тебя с работы/умрёшь ли ты завтра/отчислят ли тебя из универа, то мы настоятельно рекомендуем использовать основного бота.
"""
    else:
        msg = f"""👋 Привет!
{faq_str}
Если у тебя будут вопросы к администрации, воспользуйся командой /contact или кнопкой в меню /me.

Основные команды (также доступны в меню):
/help -- Получить помощь по командам
/me -- Отобразить информацию о себе
/config -- Получить конфиги для подключения
/contact -- Связаться с администрацией
/unblock -- Разблокировать/продлить доступ
/change_peer_name -- Изменить имя конфига (пира)
"""
    await message.answer(text=msg, reply_markup=keyboard)

@bot_dispatcher.message(Command("help"))
async def cmd_help(message: Message) -> None:
    text = "🛟 Помощь в командах:\n"
    default_commands = get_default_commands()
    for command in default_commands:
        text += f"{command.command} -> {command.description}\n"

    if message.chat.id in bot_cfg.admins:
        text += "\n\n🛠️ Список команд администратора:\n"
        for command in get_admin_commands()[len(default_commands)::]:
            text += f"{command.command} -> {command.description}\n"

    await message.answer(text)

@bot_dispatcher.startup()
async def on_startup(*args):
    if os.path.exists(".reboot"):
        with open(".reboot", encoding="utf-8") as f:
            chat_id = int(f.read())
            stickerset = await bot_instance.get_sticker_set("chunkytext")
            await bot_instance.send_sticker(chat_id, random.choice(stickerset.stickers).file_id)
            await bot_instance.send_message(chat_id, "Бот перезапущен.")
        os.remove(".reboot")
    bot_logger.info("Bot is running!")

async def main() -> None:
    bot_dispatcher.include_router(get_handlers_router())

    signal.signal(signal.SIGINT, graceful_shutdown)

    async with asyncio.TaskGroup() as group:
        group.create_task(connections_observer.listen_events())
        group.create_task(interval_observer.run_checkers())
        group.create_task(bot_dispatcher.start_polling(bot_instance, handle_signals=False))
        if prometheus_monitor is not None:
            group.create_task(prometheus_monitor.update_metrics_task(connections_observer, interval=20))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="heavens-gate", description="Run bot with core service.")
    parser.add_argument("-awg", "--amnezia",
                        help="Enable amnezia-wg functionality.",
                        action="store_true")

    args = parser.parse_args()

    if args.amnezia:
        wghub.change_command_mode(is_amnezia=True)

    asyncio.run(main())
