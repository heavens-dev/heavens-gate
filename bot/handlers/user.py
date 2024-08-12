from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from bot.utils.user_helper import get_user_data_string
from core.db.db_works import ClientFactory


user_router = Router()


@user_router.message(Command("me"))
async def me(message: Message):
    client = ClientFactory(tg_id=message.chat.id).get_client()

    await message.answer(get_user_data_string(client))
