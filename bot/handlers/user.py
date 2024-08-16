from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile

from bot.handlers.keyboards import build_peer_configs_keyboard
from core.wg.wgconfig_helper import get_peer_config_str
from bot.utils.user_helper import get_user_data_string
from core.db.db_works import ClientFactory

router = Router(name="user")


@router.message(Command("me"))
async def me(message: Message):
    client = ClientFactory(tg_id=message.chat.id).get_client()

    await message.answer(get_user_data_string(client))

@router.message(Command("config"))
async def get_config(message: Message):
    client = ClientFactory(tg_id=message.from_user.id).get_client()
    peers = client.get_peers()

    if not peers:
        await message.answer("❌ У тебя нет активных пиров.")
        return

    if len(peers) >= 2:
        keyboard = build_peer_configs_keyboard(peers)
        await message.answer(
            text="Выбери конфиг из клавиатуры, который ты хочешь получить: ",
            reply_markup=keyboard)
    else:
        config = BufferedInputFile(
            file=bytes(get_peer_config_str(peers[0]), encoding="utf-8"), 
            filename=f"{peers[0].peer_name or peers[0].id}_wg.conf")
        await message.answer_document(config, caption="Вот твой конфиг. Не распространяй его куда попало.")
