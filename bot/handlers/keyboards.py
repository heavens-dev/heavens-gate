from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.utils.callback_data import (PeerCallbackData,
                                     PreviewMessageCallbackData,
                                     TimeExtenderCallbackData,
                                     UserActionsCallbackData, UserActionsEnum,
                                     YesOrNoEnum)
from core.db.db_works import Client
from core.db.enums import ClientStatusChoices, ProtocolType
from core.db.model_serializer import BasePeer


def build_peer_configs_keyboard(user_id: int, peers: list[BasePeer], display_all=True):
    """
    Build an inline keyboard markup for peer configurations.
    This function creates a telegram inline keyboard with buttons for WireGuard peer configurations.
    Each peer is represented by a button that shows either the peer's name or ID.
    If display_all is True, an additional button to get all configurations is included at the top.
    Args:
        user_id (int): The ID of the user requesting the configurations
        peers (list[BasePeer]): List of peer objects containing peer information
        display_all (bool, optional): Whether to include a button for getting all configurations. Defaults to True.
    Returns:
        InlineKeyboardMarkup: A markup object containing the configured inline keyboard
    Example:
        >>> peers = [peer1, peer2]
        >>> keyboard = build_peer_configs_keyboard(123, peers)
    """
    builder = InlineKeyboardBuilder()

    if display_all:
        builder.button(
            text="Получить все конфиги",
            callback_data=PeerCallbackData(user_id=user_id, peer_id=-1)
        )
        builder.adjust(1)

    for peer in peers:
        text = ""
        if peer.peer_type in [ProtocolType.WIREGUARD, ProtocolType.AMNEZIA_WIREGUARD]:
            text = f"[Wireguard] {peer.peer_name or peer.id}.conf"
        elif peer.peer_type == ProtocolType.XRAY:
            text = f"[XRay] {peer.peer_name or peer.id}"
        builder.button(
            text=text,
            callback_data=PeerCallbackData(user_id=user_id, peer_id=peer.id)
        )
        builder.adjust(1)

    return builder.as_markup()

def build_user_actions_keyboard(client: Client, is_admin=True):
    builder = InlineKeyboardBuilder()

    if is_admin:
        if client.userdata.status == ClientStatusChoices.STATUS_ACCOUNT_BLOCKED:
            builder.button(
                text="🔓 Разблокировать",
                callback_data=UserActionsCallbackData(
                    action=UserActionsEnum.PARDON_USER,
                    user_id=client.userdata.user_id,
                    is_admin=is_admin
                )
            )

        else:
            builder.button(
                text="🚫 Заблокировать",
                callback_data=UserActionsCallbackData(
                    action=UserActionsEnum.BAN_USER,
                    user_id=client.userdata.user_id,
                    is_admin=is_admin
                )
            )

        builder.button(
            text="📅 Продлить время",
            callback_data=UserActionsCallbackData(
                action=UserActionsEnum.EXTEND_USAGE_TIME,
                user_id=client.userdata.user_id,
                is_admin=is_admin
            )
        )

        builder.button(
            text="➕ Добавить пир",
            callback_data=UserActionsCallbackData(
                action=UserActionsEnum.ADD_PEER,
                user_id=client.userdata.user_id,
                is_admin=is_admin
            )
        )
        builder.button(
            text="✉️ Отправить сообщение",
            callback_data=UserActionsCallbackData(
                action=UserActionsEnum.WHISPER_USER,
                user_id=client.userdata.user_id,
                is_admin=is_admin
            )
        )

    if not is_admin:
        builder.button(
            text="✏️ Переименовать конфиги",
            callback_data=UserActionsCallbackData(
                action=UserActionsEnum.CHANGE_PEER_NAME,
                user_id=client.userdata.user_id,
                is_admin=is_admin
            )
        )
        builder.button(
            text="📞 Связаться с администрацией",
            callback_data=UserActionsCallbackData(
                action=UserActionsEnum.CONTACT_ADMIN,
                user_id=client.userdata.user_id,
                is_admin=is_admin
            )
        )

    builder.button(
        text="📒 Получить конфиги",
        callback_data=UserActionsCallbackData(
            action=UserActionsEnum.GET_CONFIGS,
            user_id=client.userdata.user_id,
            is_admin=is_admin
        )
    )

    builder.button(
        text="🔄 Обновить данные",
        callback_data=UserActionsCallbackData(
            action=UserActionsEnum.UPDATE_DATA,
            user_id=client.userdata.user_id,
            is_admin=is_admin
        )
    )

    builder.adjust(2, repeat=True)

    return builder.as_markup()

def preview_keyboard():
    builder = InlineKeyboardBuilder()

    builder.button(
        text="✅ Да",
        callback_data=PreviewMessageCallbackData(
            answer=YesOrNoEnum.ANSWER_YES,
        )
    )

    builder.adjust(1)

    builder.button(
        text="❌ Нет",
        callback_data=PreviewMessageCallbackData(
            answer=YesOrNoEnum.ANSWER_NO,
        )
    )

    return builder.as_markup()

def cancel_keyboard():
    builder = InlineKeyboardBuilder()

    builder.button(
        text="❌ Отмена",
        callback_data="cancel_action"
    )

    return builder.as_markup()

def extend_time_keyboard(user_id: int):
    builder = InlineKeyboardBuilder()

    builder.button(
        text="Продлить на 1 день",
        callback_data=TimeExtenderCallbackData(user_id=user_id, extend_for="1d")
    )
    builder.button(
        text="Продлить на 1 неделю",
        callback_data=TimeExtenderCallbackData(user_id=user_id, extend_for="1w")
    )
    builder.button(
        text="Продлить на 1 месяц",
        callback_data=TimeExtenderCallbackData(user_id=user_id, extend_for="1M")
    )
    builder.button(
        text="Продлить на 3 месяца",
        callback_data=TimeExtenderCallbackData(user_id=user_id, extend_for="3M")
    )
    builder.button(
        text="Продлить на 6 месяцев",
        callback_data=TimeExtenderCallbackData(user_id=user_id, extend_for="6M")
    )
    builder.button(
        text="Ввести время",
        callback_data=TimeExtenderCallbackData(user_id=user_id, extend_for="custom")
    )

    builder.adjust(1, repeat=True)

    return builder.as_markup()

def build_protocols_keyboard():
    builder = InlineKeyboardBuilder()

    for protocol in ProtocolType:
        builder.button(text="")
