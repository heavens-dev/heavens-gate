from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from config.loader import bot_cfg
from core.db.db_works import Users
import sys
import os


admin_router = Router()
admin_router.message.filter(
    F.from_user.id.in_(bot_cfg.admins)
)

@admin_router.message(Command("admin_help"))
async def admin_help(message: Message):
    await message.answer("Сам справишься.")

@admin_router.message(Command("reboot"))
async def reboot(message: Message) -> None:
    await message.answer("Бот перезапускается...")

    await message.chat.do("choose_sticker")

    with open(".reboot", "w", encoding="utf-8") as f:
        f.write(str(message.chat.id))

    os.execv(sys.executable, ['python'] + sys.argv)

@admin_router.message(Command("broadcast"))
async def broadcast(message: Message):
    """Broadcast message to ALL registered users"""
    if len(message.text.split()) <= 1:
        await message.answer("Сообщение должно содержать хотя бы какой-то текст для отправки.")
        return
    all_users = Users.get_users()
    text = "✉️ <b>Рассылка от администрации</b>:\n\n"
    text += " ".join(message.text.split()[1::])
    # ? sooo we can get rate limited probably. fixme? maybe later.
    for user in all_users:
        if message.chat.id == user.telegram_id:
            continue
        await message.bot.send_message(user.telegram_id, text, parse_mode="HTML")
    await message.answer("Сообщение транслировано всем пользователям.")
