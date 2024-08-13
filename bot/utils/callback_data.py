from aiogram.filters.callback_data import CallbackData
from enum import StrEnum


class UserActionsEnum(StrEnum):
    BAN_USER = "ban"
    PARDON_USER = "pardon"


class ConnectionPeerCallbackData(CallbackData, prefix="peer"):
    """Peer callback data for keyboards.

    Args:
        peer_id (int): integer if we want to get single peer. Set to -1 to get ALL peers that related to some user
    """
    peer_id: int


class UserActionsCallbackData(CallbackData, prefix="user_action"):
    user_id: int
    action: UserActionsEnum
