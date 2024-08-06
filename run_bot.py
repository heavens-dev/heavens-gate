import asyncio
import random
import os
from aiogram.filters import CommandStart
from aiogram.types import Message

from config.loader import bot_instance, bot_dispatcher
from bot.handlers import admin_router



@bot_dispatcher.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer("Привет. Не знаю, как ты здесь оказался, но...")

@bot_dispatcher.startup()
async def on_startup(*args):
    if os.path.exists(".reboot"):
        with open(".reboot", encoding="utf-8") as f:
            chat_id = int(f.read())
            stickerset = await bot_instance.get_sticker_set("chunkytext")
            await bot_instance.send_sticker(chat_id, random.choice(stickerset.stickers).file_id)   
            await bot_instance.send_message(chat_id, "Бот перезапущен.")
        os.remove(".reboot")

    print("started.")

def main() -> None:
    bot_dispatcher.include_routers(admin_router)

    asyncio.run(bot_dispatcher.run_polling(bot_instance))

if __name__ == "__main__":
    main()
