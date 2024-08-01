import asyncio
import sys
import os

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command, CommandStart

from config.settings import Config


dp = Dispatcher()
cfg = Config("config.conf").BotConfig
bot = Bot(cfg.token)


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer("go fuck yourself nigger")

@dp.message(Command("reboot"))
async def reboot(message: Message) -> None:
    with open(".reboot", "w", encoding="utf-8") as f:
        f.write(str(message.chat.id))

    os.execv(sys.executable, ['python'] + sys.argv)

@dp.startup()
async def on_startup(*args):
    if os.path.exists(".reboot"):
        with open(".reboot", encoding="utf-8") as f:
            chat_id = int(f.read())
            await bot.send_message(chat_id, "Бот перезапущен.")
        os.remove(".reboot")

    print("started.")

async def main() -> None:
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
