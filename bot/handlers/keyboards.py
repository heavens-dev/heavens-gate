from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.utils.callback_data import (ConnectionPeerCallbackData,
                                     UserActionsCallbackData, UserActionsEnum)
from core.db.db_works import Client
from core.db.enums import StatusChoices
from core.db.model_serializer import ConnectionPeer


def build_peer_configs_keyboard(user_id: int, peers: list[ConnectionPeer]):
    builder = InlineKeyboardBuilder()

    builder.button(
        text="Получить все конфиги",
        callback_data=ConnectionPeerCallbackData(user_id=user_id, peer_id=-1)
    )
    builder.adjust(1)

    for peer in peers:
        builder.button(
            text=f"{peer.peer_name or peer.id}_wg.conf",
            callback_data=ConnectionPeerCallbackData(user_id=user_id, peer_id=peer.id)
        )
        builder.adjust(1)

    return builder.as_markup()

def build_user_actions_keyboard(client: Client):
    builder = InlineKeyboardBuilder()

    if client.userdata.status == StatusChoices.STATUS_ACCOUNT_BLOCKED:
        builder.button(
            text="🔓 Разблокировать",
            callback_data=UserActionsCallbackData(
                action=UserActionsEnum.PARDON_USER,
                user_id=client.userdata.telegram_id
            )
        )
    else:
        builder.button(
            text="🚫 Заблокировать",
            callback_data=UserActionsCallbackData(
                action=UserActionsEnum.BAN_USER,
                user_id=client.userdata.telegram_id
            )
        )


    builder.button(
        text="📒 Получить конфиги",
        callback_data=UserActionsCallbackData(
            action=UserActionsEnum.GET_CONFIGS,
            user_id=client.userdata.telegram_id
        )
    )

    builder.button(
        text="🔄 Обновить данные",
        callback_data=UserActionsCallbackData(
            action=UserActionsEnum.UPDATE_DATA,
            user_id=client.userdata.telegram_id
        )
    )

    builder.adjust(2, repeat=1)

    return builder.as_markup()
