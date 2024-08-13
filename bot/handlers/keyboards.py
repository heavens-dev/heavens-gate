from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.db.model_serializer import ConnectionPeer
from bot.utils.callback_data import ConnectionPeerCallbackData


def build_peer_configs_keyboard(peers: list[ConnectionPeer]):
    builder = InlineKeyboardBuilder()

    builder.button(
        text="Получить все конфиги", 
        callback_data=ConnectionPeerCallbackData(peer_id=-1)
    )
    builder.adjust(1)

    for peer in peers:
        builder.button(
            text=f"{peer.peer_name or peer.id}_wg.conf",
            callback_data=ConnectionPeerCallbackData(peer_id=peer.id)
        )
        builder.adjust(1)

    return builder.as_markup()
