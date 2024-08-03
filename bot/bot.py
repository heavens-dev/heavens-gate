import os

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart

from bot.handlers.admin_commands import admin_commands_router


def get_bot(token: str) -> Bot:
    return Bot(token)

def prepare_bot(bot: Bot):
    dp = Dispatcher()

    dp.include_routers(admin_commands_router)

    @dp.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        await message.answer("go fuck yourself nigger")

    @dp.startup()
    async def on_startup(*args):
        if os.path.exists(".reboot"):
            with open(".reboot", encoding="utf-8") as f:
                chat_id = int(f.read())
                await bot.send_message(chat_id, "Бот перезапущен.")
            os.remove(".reboot")

        print("started.")

    return dp