from aiogram import Router
from aiogram.filters import Command
from aiogram.types.input_media_document import InputMediaDocument
from aiogram.types import Message, BufferedInputFile, CallbackQuery
from aiogram.utils.media_group import MediaGroupBuilder

from bot.handlers.keyboards import build_peer_configs_keyboard
from bot.utils.callback_data import ConnectionPeerCallbackData
from core.wg.wgconfig_helper import get_peer_config_str
from bot.utils.user_helper import get_user_data_string
from core.db.db_works import ClientFactory
from config.loader import bot_instance


user_router = Router()


@user_router.message(Command("me"))
async def me(message: Message):
    client = ClientFactory(tg_id=message.chat.id).get_client()

    await message.answer(get_user_data_string(client))

@user_router.message(Command("config"))
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

@user_router.callback_query(ConnectionPeerCallbackData.filter())
async def select_peer_callback(callback: CallbackQuery, callback_data: ConnectionPeerCallbackData):
    callback.message.delete()

    client = ClientFactory(tg_id=callback.from_user.id).get_client()

    peers = client.get_peers()

    media_group = MediaGroupBuilder()

    for peer in peers:
        if callback_data.peer_id == -1:
            media_group.add_document(
                media=BufferedInputFile(
                    file=bytes(get_peer_config_str(peer), encoding="utf-8"),
                    filename=f"{peer.peer_name or peer.id}_wg.conf"
                )
            )
        elif peer.id == callback_data.peer_id:
            media_group.add_document(
                BufferedInputFile(
                    file=bytes(get_peer_config_str(peer), encoding="utf-8"),
                    filename=f"{peer.peer_name or peer.id}_wg.conf"
                )
            )
            break


    await bot_instance.send_media_group(callback.from_user.id, media=media_group.build())
    await callback.answer()
