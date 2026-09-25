from enum import StrEnum


class BroadcastEnum(StrEnum):
    SEND_TO_ALL = "send_to_all"
    SEND_TO_ACTIVE_USERS = "send_to_active"
    SEND_TO_CLEAR_USERS = "send_to_clear"
