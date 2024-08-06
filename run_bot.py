import asyncio
import random
import os
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from config.loader import bot_instance, bot_dispatcher, bot_cfg
from bot.commands import (get_admin_commands, 
                          get_default_commands, 
                          set_admin_commands, 
                          set_user_commands)
from bot.handlers import admin_router


@bot_dispatcher.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if message.chat.id in bot_cfg.admins:
        await set_admin_commands(message.chat.id)
    else:
        await set_user_commands(message.chat.id)
    await message.answer("Привет. Не знаю, как ты здесь оказался.")

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
    print("started.")

def main() -> None:
    bot_dispatcher.include_routers(admin_router)

    asyncio.run(bot_dispatcher.run_polling(bot_instance))

if __name__ == "__main__":
    main()
