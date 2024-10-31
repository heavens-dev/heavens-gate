from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from bot.handlers.keyboards import build_peer_configs_keyboard
from bot.utils.user_helper import get_user_data_string
from config.loader import wghub
from core.db.db_works import ClientFactory
from core.db.enums import PeerStatusChoices
from core.wg.wgconfig_helper import get_peer_config_str

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
        keyboard = build_peer_configs_keyboard(message.from_user.id, peers)
        await message.answer(
            text="Выбери конфиг, который ты хочешь получить из клавиатуры: ",
            reply_markup=keyboard)
    else:
        config = BufferedInputFile(
            file=bytes(get_peer_config_str(peers[0]), encoding="utf-8"),
            filename=f"{peers[0].peer_name or peers[0].id}_wg.conf")
        await message.answer_document(config, caption="Вот твой конфиг. Не распространяй его куда попало.")

@router.message(Command("unblock"))
async def unblock_timeout_connections(message: Message):
    client = ClientFactory(tg_id=message.from_user.id).get_client()
    peers = client.get_peers()
    for peer in peers:
        if peer.peer_status != PeerStatusChoices.STATUS_TIME_EXPIRED:
            continue
        wghub.enable_peer(peer)
        client.set_peer_status(peer.id, PeerStatusChoices.STATUS_DISCONNECTED)
    await message.answer("✅ Соединения были разблокированы/обновлены. Можешь продолжать пользоваться VPN!")
