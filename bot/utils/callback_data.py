from enum import StrEnum

from aiogram.filters.callback_data import CallbackData

from core.db.enums import ProtocolType


class UserActionsEnum(StrEnum):
    BAN_USER = "ban"
    PARDON_USER = "pardon"
    GET_CONFIGS = "configs"
    UPDATE_DATA = "update"
    CHANGE_PEER_NAME = "change_peer_name"
    CONTACT_ADMIN = "contact_admin"
    EXTEND_USAGE_TIME = "extend_usage_time"
    WHISPER_USER = "whisper"
    ADD_PEER = "add_peer"


class YesOrNoEnum(StrEnum):
    ANSWER_YES = "yes"
    ANSWER_NO = "no"


class PeerCallbackData(CallbackData, prefix="peer"):
    """Peer callback data for keyboards.

    Args:
        peer_id (int): integer if we want to get a single peer. Set to -1 to get ALL peers that are related to some user
    """
    peer_id: int
    user_id: int

class TimeExtenderCallbackData(CallbackData, prefix="time_extender"):
    """Time extender callback data for keyboards.

    Args:
        user_id (int): user id
        extend_for (str): time to extend for. Example: 1d, 1w, 1M, 3M, 6M, 1Y
    """
    user_id: int
    extend_for: str

class UserActionsCallbackData(CallbackData, prefix="user_action"):
    user_id: int
    action: UserActionsEnum
    is_admin: bool

class PreviewMessageCallbackData(CallbackData, prefix="preview"):
    answer: YesOrNoEnum

class GetUserCallbackData(CallbackData, prefix="get_user"):
    user_id: int

class ProtocolChoiceCallbackData(CallbackData, prefix="protocol_choice"):
    protocol: ProtocolType
