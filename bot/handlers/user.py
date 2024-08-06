from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from config.loader import bot_cfg
from core.db.db_works import Client
from core.db.enums import StatusChoices


user_router = Router()


@user_router.message(Command("me"))
async def me(message: Message):
    client = Client(message.chat.id)

    info = client.get_client()

    await message.answer(f"""ℹ️ Информация об аккаунте:
ID: {info.telegram_id}
Текущий статус: {StatusChoices.to_string(info.status)}
""")